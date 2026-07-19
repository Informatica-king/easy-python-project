"""Factor levels and deltas at earnings events."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from sepa.data import fundamentals as fund_data
from sepa.fundamental_score import (
    is_next_quarter,
    prior_year_frame,
    sorted_frames,
    yoy_growth_map,
)
from sepa.fund_study.config import EXPLOSION_ABS_MAX

logger = logging.getLogger(__name__)

OP_INCOME_TAGS = (
    "OperatingIncomeLoss",
    "OperatingIncomeLossAvailableToCommonStockholdersBasic",
)


def prior_quarter_frame(frame: str) -> str:
    y, q = int(frame[2:6]), int(frame[7])
    if q == 1:
        return f"CY{y - 1}Q4"
    return f"CY{y}Q{q - 1}"


def qoq_growth_map(series: pd.Series) -> dict[str, float]:
    if series is None or series.empty:
        return {}
    data = series.dropna().to_dict()
    out: dict[str, float] = {}
    for frame, val in data.items():
        prev_f = prior_quarter_frame(frame)
        prev = data.get(prev_f)
        if prev is None or prev == 0:
            continue
        if not is_next_quarter(prev_f, frame):
            # still allow if keys exist (calendar may skip)
            pass
        out[frame] = float(val) / float(prev) - 1.0
    return out


def delta_map(level: dict[str, float]) -> dict[str, float]:
    """Δ of a per-frame level vs previous adjacent frame in sorted order."""
    if len(level) < 2:
        return {}
    frames = sorted_frames(list(level.keys()))
    out: dict[str, float] = {}
    for i in range(1, len(frames)):
        newer, older = frames[i], frames[i - 1]
        if not is_next_quarter(older, newer):
            continue
        out[newer] = float(level[newer]) - float(level[older])
    return out


def margin_yoy_delta_map(margin: pd.Series) -> dict[str, float]:
    """NPM_t - NPM_{t-4} (YoY margin change)."""
    if margin is None or margin.empty:
        return {}
    data = margin.dropna().to_dict()
    out: dict[str, float] = {}
    for frame, val in data.items():
        prev = data.get(prior_year_frame(frame))
        if prev is None:
            continue
        out[frame] = float(val) - float(prev)
    return out


def attach_operating_margin(df: pd.DataFrame, ticker: str, cik_map: dict[str, str]) -> pd.DataFrame:
    """Add opm column from SEC operating income / revenue when possible."""
    work = df.copy()
    if "opm" in work.columns and work["opm"].notna().any():
        return work
    cik = cik_map.get(ticker.upper())
    if not cik or "revenue" not in work.columns:
        work["opm"] = np.nan
        return work
    try:
        import requests
        from sepa.data.fundamentals import SEC_FACTS_URL, _frames_from_tag, _headers

        r = requests.get(SEC_FACTS_URL.format(cik=cik), headers=_headers(), timeout=90)
        if r.status_code != 200:
            work["opm"] = np.nan
            return work
        usgaap = r.json().get("facts", {}).get("us-gaap", {})
        op = _frames_from_tag(usgaap, OP_INCOME_TAGS)
        if not op:
            work["opm"] = np.nan
            return work
        opm = {}
        for fr, oi in op.items():
            rev = work.loc[fr, "revenue"] if fr in work.index else None
            if rev is None or (isinstance(rev, float) and (not np.isfinite(rev) or rev == 0)):
                continue
            opm[fr] = float(oi) / float(rev)
        work["opm"] = pd.Series(opm)
    except Exception as exc:  # noqa: BLE001
        logger.debug("opm attach failed %s: %s", ticker, exc)
        work["opm"] = np.nan
    return work


def frame_asof_event(frames: list[str], day0: pd.Timestamp, frame_end_approx: dict[str, pd.Timestamp]) -> str | None:
    """Pick latest frame whose approximate period-end is before day0."""
    if not frames:
        return None
    day0 = pd.Timestamp(day0).normalize()
    eligible = [f for f in sorted_frames(frames) if frame_end_approx.get(f, day0) < day0]
    return eligible[-1] if eligible else sorted_frames(frames)[-1]


def approx_frame_end(frame: str) -> pd.Timestamp:
    """Calendar quarter end for CYyyyyQn."""
    y, q = int(frame[2:6]), int(frame[7])
    month = q * 3
    # last day of quarter month
    if month == 12:
        return pd.Timestamp(year=y, month=12, day=31)
    nxt = pd.Timestamp(year=y, month=month + 1, day=1)
    return nxt - pd.Timedelta(days=1)


def is_explosion(*vals: float | None) -> bool:
    for v in vals:
        if v is None or not np.isfinite(v):
            continue
        if abs(float(v)) > EXPLOSION_ABS_MAX:
            return True
    return False


def factors_for_frame(
    qdf: pd.DataFrame,
    frame: str,
) -> dict[str, float | None]:
    """Compute all study factors for a given quarter frame."""
    eps = qdf["eps"] if "eps" in qdf.columns else pd.Series(dtype=float)
    rev = qdf["revenue"] if "revenue" in qdf.columns else pd.Series(dtype=float)
    npm = qdf["npm"] if "npm" in qdf.columns else pd.Series(dtype=float)
    opm = qdf["opm"] if "opm" in qdf.columns else pd.Series(dtype=float)

    eps_yoy = yoy_growth_map(eps)
    sales_yoy = yoy_growth_map(rev)
    eps_qoq = qoq_growth_map(eps)
    sales_qoq = qoq_growth_map(rev)
    eps_dyoy = delta_map(eps_yoy)
    sales_dyoy = delta_map(sales_yoy)
    eps_dqoq = delta_map(eps_qoq)
    sales_dqoq = delta_map(sales_qoq)
    npm_d = margin_yoy_delta_map(npm)
    opm_d = margin_yoy_delta_map(opm)

    out = {
        "frame": frame,
        "eps_yoy": eps_yoy.get(frame),
        "eps_dyoy": eps_dyoy.get(frame),
        "sales_yoy": sales_yoy.get(frame),
        "sales_dyoy": sales_dyoy.get(frame),
        "npm_d": npm_d.get(frame),
        "opm_d": opm_d.get(frame),
        "eps_qoq": eps_qoq.get(frame),
        "eps_dqoq": eps_dqoq.get(frame),
        "sales_qoq": sales_qoq.get(frame),
        "sales_dqoq": sales_dqoq.get(frame),
        # surprise filled later if available
        "eps_surprise": None,
        "sales_surprise": None,
    }
    return out


def load_quarterly_for_study(
    ticker: str,
    *,
    cache_dir: str | Path,
    cik_map: dict[str, str],
    refresh: bool = False,
) -> pd.DataFrame:
    fund_dir = fund_data.cache_dir(cache_dir)
    qdf, _roe, _src = fund_data.load_quarterly(
        ticker, fund_dir, cik_map, refresh=refresh, sleep_s=0.05
    )
    if qdf is None or qdf.empty:
        return pd.DataFrame()
    return attach_operating_margin(qdf, ticker, cik_map)


def enrich_events_with_factors(
    events: pd.DataFrame,
    *,
    cache_dir: str | Path,
    cik_map: dict[str, str],
) -> pd.DataFrame:
    """Attach factor columns to event rows (one fundamentals load per ticker)."""
    if events.empty:
        return events
    pieces = []
    for ticker, g in events.groupby("ticker"):
        qdf = load_quarterly_for_study(str(ticker), cache_dir=cache_dir, cik_map=cik_map)
        if qdf.empty:
            continue
        frames = list(qdf.index.astype(str))
        ends = {f: approx_frame_end(f) for f in frames}
        rows = []
        for _, ev in g.iterrows():
            fr = frame_asof_event(frames, ev["day0"], ends)
            if fr is None:
                continue
            fac = factors_for_frame(qdf, fr)
            if is_explosion(fac.get("eps_yoy"), fac.get("sales_yoy"), fac.get("eps_qoq"), fac.get("sales_qoq")):
                continue
            row = {**ev.to_dict(), **fac}
            rows.append(row)
        if rows:
            pieces.append(pd.DataFrame(rows))
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True)


def try_attach_surprises(panel: pd.DataFrame) -> pd.DataFrame:
    """Best-effort EPS surprise from cached/yfinance earnings_dates."""
    if panel.empty:
        return panel
    from sepa.fund_study.config import EARNINGS_CACHE_DIR
    from sepa.fund_study.events import is_yahoo_rate_limited

    work = panel.copy()
    for ticker, g in work.groupby("ticker"):
        ed = None
        sur_path = Path(EARNINGS_CACHE_DIR) / f"{str(ticker).upper()}_table.parquet"
        if sur_path.exists():
            try:
                ed = pd.read_parquet(sur_path)
            except Exception:  # noqa: BLE001
                ed = None
        if ed is None:
            if is_yahoo_rate_limited():
                continue
            try:
                import yfinance as yf

                ed = yf.Ticker(str(ticker)).get_earnings_dates(limit=40)
            except Exception:  # noqa: BLE001
                continue
        if ed is None or ed.empty:
            continue
        cols = {c.lower().replace(" ", "_"): c for c in ed.columns}
        est_c = cols.get("eps_estimate") or cols.get("estimate")
        act_c = cols.get("reported_eps") or cols.get("actual")
        sur_c = cols.get("surprise(%)") or cols.get("surprise%") or cols.get("surprise")
        ed = ed.copy()
        ed.index = pd.to_datetime(ed.index)
        if getattr(ed.index, "tz", None) is not None:
            ed.index = ed.index.tz_localize(None)
        ed.index = ed.index.normalize()
        for i in g.index:
            day0 = pd.Timestamp(work.at[i, "day0"]).normalize()
            if day0 in ed.index:
                row = ed.loc[day0]
            else:
                deltas = (ed.index - day0).days
                near = ed.index[np.abs(deltas) <= 3]
                if len(near) == 0:
                    continue
                row = ed.loc[near[np.argmin(np.abs((near - day0).days))]]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            if sur_c and pd.notna(row.get(sur_c)):
                try:
                    val = float(row.get(sur_c))
                    work.at[i, "eps_surprise"] = val / 100.0 if abs(val) > 2 else val
                except Exception:  # noqa: BLE001
                    pass
            elif est_c and act_c and pd.notna(row.get(est_c)) and pd.notna(row.get(act_c)):
                est = float(row.get(est_c))
                act = float(row.get(act_c))
                if est != 0:
                    work.at[i, "eps_surprise"] = act / est - 1.0
    return work
