"""분기 재무 데이터 수집 — SEC EDGAR(1순위) + yfinance 폴백.

캐시: data/fundamentals/{TICKER}.parquet, data/fundamentals/_sec_tickers.json

OPM 폴백 순서 (Fund v2.1 / A1):
  SEC operating income → yfinance Operating Income → (scorer) NPM with penalty → none
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

SEC_UA = "SEPA-Screener personal-noncommercial research (sepa-bot@localhost)"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

FRAME_RE = re.compile(r"^CY(\d{4})Q([1-4])$")

# Preferred US-GAAP tags (first hit wins per metric family)
EPS_TAGS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")
REVENUE_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
)
NET_INCOME_TAGS = ("NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic")
OP_INCOME_TAGS = (
    "OperatingIncomeLoss",
    "OperatingIncomeLossAvailableToCommonStockholdersBasic",
    "OperatingIncomeLossBeforeIncomeTaxes",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
)

# Absurd margin ratios → drop (bad scale / wrong unit merges)
MARGIN_ABS_MAX = 2.0


def _headers() -> dict[str, str]:
    return {"User-Agent": SEC_UA, "Accept-Encoding": "gzip, deflate"}


def cache_dir(root: str | Path) -> Path:
    """Return fundamentals cache dir (sibling of price cache when root is data/raw)."""
    root = Path(root)
    # params.data.cache_dir is typically data/raw → store fundamentals in data/fundamentals
    if root.name == "raw":
        return root.parent / "fundamentals"
    return root / "fundamentals"


def load_cik_map(fund_dir: Path, refresh: bool = False) -> dict[str, str]:
    """Ticker -> zero-padded CIK."""
    fund_dir.mkdir(parents=True, exist_ok=True)
    path = fund_dir / "_sec_tickers.json"
    if path.exists() and not refresh:
        raw = json.loads(path.read_text())
        return {k.upper(): v for k, v in raw.items()}

    logger.info("downloading SEC ticker→CIK map")
    r = requests.get(SEC_TICKERS_URL, headers=_headers(), timeout=60)
    r.raise_for_status()
    mapping = {
        str(v["ticker"]).upper(): str(v["cik_str"]).zfill(10)
        for v in r.json().values()
    }
    path.write_text(json.dumps(mapping, indent=0))
    return mapping


def _frames_from_tag(usgaap: dict, tags: tuple[str, ...]) -> dict[str, float]:
    """Extract CY####Qn -> value from the first available tag."""
    for tag in tags:
        node = usgaap.get(tag)
        if not node:
            continue
        best: dict[str, tuple[str, float]] = {}
        for _unit, rows in node.get("units", {}).items():
            for row in rows:
                frame = row.get("frame")
                if not frame or not FRAME_RE.match(frame):
                    continue
                if len(frame) != 8:  # drop dimensional frames like CY2024Q1I...
                    continue
                val = row.get("val")
                if val is None:
                    continue
                filed = row.get("filed") or ""
                prev = best.get(frame)
                if prev is None or filed >= prev[0]:
                    best[frame] = (filed, float(val))
        if best:
            return {f: v for f, (_filed, v) in best.items()}
    return {}


def _frames_to_series(frames: dict[str, float]) -> pd.Series:
    if not frames:
        return pd.Series(dtype=float)
    items = sorted(frames.items(), key=lambda kv: (int(kv[0][2:6]), int(kv[0][7])))
    idx = pd.Index([k for k, _ in items], name="frame")
    return pd.Series([v for _, v in items], index=idx, dtype=float)


def sanitize_margins(df: pd.DataFrame, *, abs_max: float = MARGIN_ABS_MAX) -> pd.DataFrame:
    """Drop absurd margin ratios (wrong units / divide noise)."""
    if df is None or df.empty:
        return df
    out = df.copy()
    for col in ("opm", "npm"):
        if col not in out.columns:
            continue
        s = pd.to_numeric(out[col], errors="coerce")
        bad = s.abs() > abs_max
        if bad.any():
            s = s.mask(bad)
        out[col] = s
    return out


def _recompute_margins(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "revenue" not in df.columns:
        return df
    out = df.copy()
    rev_nz = out["revenue"].replace(0, pd.NA)
    if "net_income" in out.columns:
        out["npm"] = out["net_income"] / rev_nz
    if "op_income" in out.columns:
        out["opm"] = out["op_income"] / rev_nz
    return sanitize_margins(out)


def opm_coverage_ok(df: pd.DataFrame, *, min_points: int = 2) -> bool:
    if df is None or df.empty or "opm" not in df.columns:
        return False
    return int(pd.to_numeric(df["opm"], errors="coerce").notna().sum()) >= min_points


def fetch_sec_quarterly(cik: str) -> pd.DataFrame:
    """Return DataFrame indexed by frame with eps, revenue, net_income, npm, opm."""
    url = SEC_FACTS_URL.format(cik=cik)
    r = requests.get(url, headers=_headers(), timeout=90)
    if r.status_code == 404:
        return pd.DataFrame()
    r.raise_for_status()
    usgaap = r.json().get("facts", {}).get("us-gaap", {})

    eps = _frames_to_series(_frames_from_tag(usgaap, EPS_TAGS))
    rev = _frames_to_series(_frames_from_tag(usgaap, REVENUE_TAGS))
    ni = _frames_to_series(_frames_from_tag(usgaap, NET_INCOME_TAGS))
    oi = _frames_to_series(_frames_from_tag(usgaap, OP_INCOME_TAGS))

    df = pd.DataFrame({"eps": eps, "revenue": rev, "net_income": ni, "op_income": oi})
    df = df.dropna(how="all")
    return _recompute_margins(df)


def fetch_yfinance_quarterly(ticker: str) -> pd.DataFrame:
    """Fallback: up to ~5 quarters from yfinance income statement."""
    import yfinance as yf

    t = yf.Ticker(ticker)
    qi = t.quarterly_income_stmt
    if qi is None or qi.empty:
        return pd.DataFrame()

    def row(*names: str) -> pd.Series | None:
        for n in names:
            if n in qi.index:
                s = qi.loc[n].astype(float)
                s.index = pd.to_datetime(s.index)
                return s.sort_index()
        return None

    eps = row("Diluted EPS", "Basic EPS")
    rev = row("Total Revenue", "Operating Revenue")
    ni = row("Net Income", "Net Income Common Stockholders")
    oi = row(
        "Operating Income",
        "Operating Income Loss",
        "Total Operating Income As Reported",
    )
    parts = {}
    if eps is not None:
        parts["eps"] = eps
    if rev is not None:
        parts["revenue"] = rev
    if ni is not None:
        parts["net_income"] = ni
    if oi is not None:
        parts["op_income"] = oi
    if not parts:
        return pd.DataFrame()
    df = pd.DataFrame(parts).sort_index()
    # Synthesize pseudo-frames from quarter-end dates for YoY pairing
    frames = []
    for ts in df.index:
        q = (ts.month - 1) // 3 + 1
        frames.append(f"CY{ts.year}Q{q}")
    df.index = pd.Index(frames, name="frame")
    df = df[~df.index.duplicated(keep="last")]
    return _recompute_margins(df)


def fetch_roe(ticker: str) -> float | None:
    """Trailing ROE as a fraction (e.g. 0.17 = 17%)."""
    import yfinance as yf

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:  # noqa: BLE001
        logger.debug("ROE fetch failed for %s: %s", ticker, exc)
        return None
    roe = info.get("returnOnEquity")
    if roe is None:
        return None
    return float(roe)


def overlay_operating_income(
    base: pd.DataFrame,
    donor: pd.DataFrame,
) -> pd.DataFrame:
    """Copy op_income/opm from donor onto base frames (fill gaps only)."""
    if base is None or base.empty:
        return sanitize_margins(donor.copy()) if donor is not None and not donor.empty else base
    out = base.copy()
    if donor is None or donor.empty:
        return _recompute_margins(out)
    for col in ("op_income", "opm"):
        if col not in donor.columns:
            continue
        donor_s = pd.to_numeric(donor[col], errors="coerce")
        if col not in out.columns:
            out[col] = donor_s.reindex(out.index)
        else:
            existing = pd.to_numeric(out[col], errors="coerce")
            filled = existing.copy()
            add = donor_s.reindex(out.index)
            need = filled.isna() & add.notna()
            filled = filled.where(~need, add)
            out[col] = filled
    # If we gained op_income but not opm, recompute
    return _recompute_margins(out)


def backfill_operating_margin(
    df: pd.DataFrame,
    ticker: str,
    cik_map: dict[str, str],
    *,
    sleep_s: float = 0.12,
) -> tuple[pd.DataFrame, str]:
    """Ensure OPM via SEC then yfinance. Returns (df, note)."""
    if opm_coverage_ok(df):
        return sanitize_margins(df), "ok"
    work = df.copy() if df is not None else pd.DataFrame()
    note = "none"

    cik = cik_map.get(ticker.upper())
    if cik:
        try:
            time.sleep(sleep_s)
            sec = fetch_sec_quarterly(cik)
            if not sec.empty and "op_income" in sec.columns and sec["op_income"].notna().any():
                if work.empty:
                    work = sec
                else:
                    work = overlay_operating_income(work, sec)
                if opm_coverage_ok(work):
                    return work, "sec_opm"
                note = "sec_partial"
        except Exception as exc:  # noqa: BLE001
            logger.warning("SEC OPM backfill failed %s: %s", ticker, exc)
            note = "sec_fail"

    try:
        yf_df = fetch_yfinance_quarterly(ticker)
        if not yf_df.empty and "op_income" in yf_df.columns and yf_df["op_income"].notna().any():
            if work.empty:
                work = yf_df
            else:
                work = overlay_operating_income(work, yf_df)
            if opm_coverage_ok(work):
                return work, "yfinance_opm"
            note = f"{note}+yf_partial" if note != "none" else "yf_partial"
    except Exception as exc:  # noqa: BLE001
        logger.warning("yfinance OPM backfill failed %s: %s", ticker, exc)

    return sanitize_margins(work), note


def load_quarterly(
    ticker: str,
    fund_dir: Path,
    cik_map: dict[str, str],
    *,
    refresh: bool = False,
    sleep_s: float = 0.12,
    backfill_opm: bool = True,
) -> tuple[pd.DataFrame, float | None, str]:
    """Load quarterly fundamentals + ROE. Returns (df, roe, source).

    If a cache exists but lacks usable OPM, backfill from SEC/yfinance (A1)
    and rewrite the parquet so subsequent loads see opm.
    """
    fund_dir.mkdir(parents=True, exist_ok=True)
    path = fund_dir / f"{ticker.upper()}.parquet"
    meta_path = fund_dir / f"{ticker.upper()}.meta.json"

    if path.exists() and meta_path.exists() and not refresh:
        df = pd.read_parquet(path)
        meta = json.loads(meta_path.read_text())
        source = meta.get("source", "cache")
        if backfill_opm and not opm_coverage_ok(df):
            df2, note = backfill_operating_margin(df, ticker, cik_map, sleep_s=sleep_s)
            if opm_coverage_ok(df2) or ("op_income" in df2.columns and df2["op_income"].notna().any()):
                df = df2
                source = f"{source}+opm:{note}"
                df.to_parquet(path)
                meta = {
                    **meta,
                    "source": source,
                    "opm_backfill": note,
                    "ticker": ticker.upper(),
                }
                meta_path.write_text(json.dumps(meta))
                logger.info("OPM backfill %s → %s (opm_n=%s)", ticker, note,
                            int(df["opm"].notna().sum()) if "opm" in df.columns else 0)
        return sanitize_margins(df), meta.get("roe"), source

    source = "none"
    df = pd.DataFrame()
    cik = cik_map.get(ticker.upper())
    if cik:
        try:
            time.sleep(sleep_s)
            df = fetch_sec_quarterly(cik)
            if not df.empty:
                source = "sec"
        except Exception as exc:  # noqa: BLE001
            logger.warning("SEC fetch failed for %s (CIK %s): %s", ticker, cik, exc)

    if df.empty or df.dropna(how="all").empty:
        try:
            df = fetch_yfinance_quarterly(ticker)
            if not df.empty:
                source = "yfinance"
        except Exception as exc:  # noqa: BLE001
            logger.warning("yfinance fundamentals failed for %s: %s", ticker, exc)

    # If SEC lacked OI but we have a frame skeleton, try OPM-only backfill
    if backfill_opm and not opm_coverage_ok(df):
        df2, note = backfill_operating_margin(df, ticker, cik_map, sleep_s=sleep_s)
        if not df2.empty:
            df = df2
            if note.startswith("sec") and source == "yfinance":
                source = f"yfinance+opm:{note}"
            elif note != "none" and source == "none":
                source = f"opm:{note}"

    roe = None
    try:
        roe = fetch_roe(ticker)
    except Exception as exc:  # noqa: BLE001
        logger.debug("ROE failed for %s: %s", ticker, exc)

    df = sanitize_margins(df)
    if not df.empty:
        df.to_parquet(path)
    meta_path.write_text(json.dumps({"roe": roe, "source": source, "ticker": ticker.upper()}))
    return df, roe, source


def audit_opm_coverage(
    tickers: list[str],
    fund_dir: Path,
    cik_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Snapshot OPM/NPM coverage for cached fundamentals (no network)."""
    rows = []
    for t in tickers:
        t = str(t).upper()
        path = fund_dir / f"{t}.parquet"
        if not path.exists():
            rows.append({"ticker": t, "cached": False, "opm_n": 0, "npm_n": 0, "rows": 0})
            continue
        df = pd.read_parquet(path)
        opm_n = int(df["opm"].notna().sum()) if "opm" in df.columns else 0
        npm_n = int(df["npm"].notna().sum()) if "npm" in df.columns else 0
        rows.append(
            {
                "ticker": t,
                "cached": True,
                "opm_n": opm_n,
                "npm_n": npm_n,
                "rows": len(df),
                "opm_ok": opm_n >= 2,
                "has_cik": bool(cik_map and t in cik_map) if cik_map else None,
            }
        )
    return pd.DataFrame(rows)
