"""Longitudinal performance ledger — auto-updated on each ``!sepa.go``.

Builds growing panels under ``reports/perf/`` so months/years of runs can
feed ``sepa.perf_study`` without redefining schemas.

See ``docs/perf_study_framework.md``.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd

from sepa.analyze import fund_median_threshold, fund_median_tickers
from sepa.artifacts import publish_many
from sepa.model_metrics import _ensure_benchmark, _load_close_series
from sepa.result_ledger import EVENT_FWD_HORIZONS, _stamp_as_of, append_log_row
from sepa.rs_fund_region_study import forward_return

logger = logging.getLogger(__name__)

PERF_DIRNAME = "perf"
LEDGER_VERSION = "v1"

BASKET_FUND_POOL = "fund_pool"
BASKET_MEDIAN_PLUS = "median_plus"
BASKET_FUND_Q4 = "fund_q4"
BASKET_RS90_OK = "rs90_ok"
BASKET_SOFT_DROP = "soft_drop"


def perf_dir(report_dir: str | Path) -> Path:
    out = Path(report_dir) / PERF_DIRNAME
    out.mkdir(parents=True, exist_ok=True)
    return out


def _upsert_panel(path: Path, new_rows: pd.DataFrame, *, key_cols: list[str]) -> pd.DataFrame:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if new_rows is None or new_rows.empty:
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame(columns=list(new_rows.columns) if new_rows is not None else key_cols)

    work = new_rows.copy()
    for c in key_cols:
        if c in work.columns:
            work[c] = work[c].astype(str)

    if path.exists():
        try:
            hist = pd.read_csv(path)
            for c in key_cols:
                if c in hist.columns:
                    hist[c] = hist[c].astype(str)
            # drop overlapping keys then concat
            if all(c in hist.columns for c in key_cols):
                merge_keys = work[key_cols].drop_duplicates()
                hist = hist.merge(merge_keys.assign(_drop=1), on=key_cols, how="left")
                hist = hist.loc[hist["_drop"].isna()].drop(columns=["_drop"])
            out = pd.concat([hist, work], ignore_index=True)
        except Exception:  # noqa: BLE001
            logger.warning("rebuild perf panel from new rows: %s", path)
            out = work
    else:
        out = work

    out.to_csv(path, index=False)
    return out


def assign_baskets(fund_df: pd.DataFrame, soft_drops: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """Return mapping basket_name → member frame (subset of fund_df or soft_drops)."""
    out: dict[str, pd.DataFrame] = {}
    if fund_df is None or fund_df.empty:
        return out

    work = fund_df.copy()
    work["ticker"] = work["ticker"].astype(str).str.upper()
    work["fund_score"] = pd.to_numeric(work.get("fund_score"), errors="coerce")
    work["rs_rank"] = pd.to_numeric(work.get("rs_rank"), errors="coerce")

    out[BASKET_FUND_POOL] = work

    med_tickers, med = fund_median_tickers(work)
    med_set = set(med_tickers)
    out[BASKET_MEDIAN_PLUS] = work.loc[work["ticker"].isin(med_set)].copy()
    out[BASKET_MEDIAN_PLUS].attrs["fund_median"] = med

    # Q4: top quartile by fund_score
    scored = work.dropna(subset=["fund_score"])
    if len(scored) >= 4:
        try:
            q = pd.qcut(scored["fund_score"], 4, labels=False, duplicates="drop")
            q4 = scored.loc[q == q.max()].copy()
            out[BASKET_FUND_Q4] = q4
        except ValueError:
            thr = float(scored["fund_score"].quantile(0.75))
            out[BASKET_FUND_Q4] = scored.loc[scored["fund_score"] >= thr].copy()
    else:
        out[BASKET_FUND_Q4] = scored.copy()

    out[BASKET_RS90_OK] = work.loc[work["rs_rank"] >= 90].copy()

    if soft_drops is not None and not soft_drops.empty:
        sd = soft_drops.copy()
        sd["ticker"] = sd["ticker"].astype(str).str.upper()
        out[BASKET_SOFT_DROP] = sd
    else:
        out[BASKET_SOFT_DROP] = work.iloc[0:0].copy()

    return out


def basket_members_rows(
    baskets: dict[str, pd.DataFrame],
    *,
    stamp: str,
    as_of: str,
) -> pd.DataFrame:
    rows = []
    for basket, df in baskets.items():
        if df is None or df.empty:
            continue
        for _, r in df.iterrows():
            rows.append(
                {
                    "stamp": stamp,
                    "as_of": as_of,
                    "basket": basket,
                    "ledger_version": LEDGER_VERSION,
                    "ticker": str(r.get("ticker", "")).upper(),
                    "fund_score": r.get("fund_score", np.nan),
                    "rs_rank": r.get("rs_rank", np.nan),
                    "market_cap": r.get("market_cap", np.nan),
                    "name": r.get("name", ""),
                }
            )
    cols = [
        "stamp", "as_of", "basket", "ledger_version", "ticker",
        "fund_score", "rs_rank", "market_cap", "name",
    ]
    return pd.DataFrame(rows, columns=cols)


def daily_pool_row(
    *,
    stamp: str,
    as_of: str,
    n_stage2: int | None,
    fund_df: pd.DataFrame,
    baskets: dict[str, pd.DataFrame],
    params_sha: str | None = None,
) -> dict:
    med = fund_median_threshold(fund_df) if fund_df is not None and not fund_df.empty else float("nan")
    rs = pd.to_numeric(fund_df.get("rs_rank"), errors="coerce") if fund_df is not None and not fund_df.empty else pd.Series(dtype=float)
    fund = pd.to_numeric(fund_df.get("fund_score"), errors="coerce") if fund_df is not None and not fund_df.empty else pd.Series(dtype=float)
    return {
        "stamp": stamp,
        "as_of": as_of,
        "ledger_version": LEDGER_VERSION,
        "n_stage2": n_stage2 if n_stage2 is not None else np.nan,
        "n_fund_pool": int(len(baskets.get(BASKET_FUND_POOL, []))),
        "n_median_plus": int(len(baskets.get(BASKET_MEDIAN_PLUS, []))),
        "n_fund_q4": int(len(baskets.get(BASKET_FUND_Q4, []))),
        "n_rs90_ok": int(len(baskets.get(BASKET_RS90_OK, []))),
        "n_soft_drop": int(len(baskets.get(BASKET_SOFT_DROP, []))),
        "fund_median": med,
        "fund_mean": float(fund.mean()) if len(fund) else np.nan,
        "rs_median": float(rs.median()) if len(rs) else np.nan,
        "params_sha256_short": (params_sha or "")[:12],
    }


def backfill_security_forward(
    members: pd.DataFrame,
    *,
    cache_dir: str | Path,
    benchmark: str = "^GSPC",
    horizons: tuple[tuple[str, int], ...] = EVENT_FWD_HORIZONS,
) -> pd.DataFrame:
    """One row per stamp×basket×ticker with fwd/excess columns (NaN until ready)."""
    if members is None or members.empty:
        cols = ["stamp", "as_of", "basket", "ticker"]
        for lab, _ in horizons:
            cols += [f"fwd_{lab}", f"bench_{lab}", f"excess_{lab}", f"ready_{lab}"]
        return pd.DataFrame(columns=cols)

    bench = _ensure_benchmark(cache_dir, benchmark)
    if bench.empty:
        bench = _ensure_benchmark(cache_dir, "SPY")
    px_cache: dict[str, pd.Series] = {}
    rows = []
    for _, r in members.iterrows():
        stamp = str(r["stamp"])
        as_of_s = str(r.get("as_of") or _stamp_as_of(stamp))
        try:
            as_of = pd.Timestamp(as_of_s)
        except Exception:  # noqa: BLE001
            continue
        ticker = str(r["ticker"]).upper()
        series = _load_close_series(ticker, cache_dir, px_cache)
        row = {
            "stamp": stamp,
            "as_of": as_of_s,
            "basket": r.get("basket", ""),
            "ticker": ticker,
            "fund_score": r.get("fund_score", np.nan),
            "rs_rank": r.get("rs_rank", np.nan),
            "ledger_version": r.get("ledger_version", LEDGER_VERSION),
        }
        for lab, h in horizons:
            ret = forward_return(series, as_of, h) if not series.empty else None
            bret = forward_return(bench, as_of, h) if not bench.empty else None
            ready = ret is not None
            row[f"fwd_{lab}"] = ret if ready else np.nan
            row[f"bench_{lab}"] = bret if bret is not None else np.nan
            row[f"excess_{lab}"] = (
                float(ret) - float(bret) if ready and bret is not None else np.nan
            )
            row[f"ready_{lab}"] = bool(ready)
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_basket_forward(fwd: pd.DataFrame, *, stamp: str) -> pd.DataFrame:
    """Per-basket × horizon mean excess among ready rows (for today's log)."""
    if fwd is None or fwd.empty:
        return pd.DataFrame()
    rows = []
    as_of = str(fwd["as_of"].iloc[0]) if "as_of" in fwd.columns else _stamp_as_of(stamp)
    for basket, g in fwd.groupby("basket"):
        for lab, _ in EVENT_FWD_HORIZONS:
            ready_col = f"ready_{lab}"
            exc_col = f"excess_{lab}"
            if ready_col not in g.columns or exc_col not in g.columns:
                continue
            ready = g.loc[g[ready_col].astype(bool)]
            n = int(len(ready))
            rows.append(
                {
                    "stamp": stamp,
                    "as_of": as_of,
                    "basket": basket,
                    "horizon": lab,
                    "n_members": int(len(g)),
                    "n_ready": n,
                    "mean_excess": float(ready[exc_col].mean()) if n else np.nan,
                    "median_excess": float(ready[exc_col].median()) if n else np.nan,
                    "win_rate": float((ready[exc_col] > 0).mean()) if n else np.nan,
                }
            )
    return pd.DataFrame(rows)


def ingest_missing_fundamental_stamps(
    report_dir: str | Path,
    cache_dir: str | Path,
    *,
    publish: bool = False,
) -> list[str]:
    """Ingest any ``fundamental_YYYYMMDD.csv`` not yet in daily_pool_log."""
    report_dir = Path(report_dir)
    out = perf_dir(report_dir)
    pool_path = out / "daily_pool_log.csv"
    have: set[str] = set()
    if pool_path.exists():
        try:
            have = set(pd.read_csv(pool_path)["stamp"].astype(str))
        except Exception:  # noqa: BLE001
            have = set()

    ingested: list[str] = []
    for path in sorted(report_dir.glob("fundamental_*.csv")):
        m = re.search(r"fundamental_(\d{8})", path.name)
        if not m:
            continue
        stamp = m.group(1)
        if stamp in have:
            continue
        try:
            fund_df = pd.read_csv(path)
        except Exception:  # noqa: BLE001
            continue
        soft_path = report_dir / f"rs_soft_drops_{stamp}.csv"
        soft = pd.read_csv(soft_path) if soft_path.exists() else None
        stage2 = report_dir / f"stage2_{stamp}.csv"
        n_stage2 = len(pd.read_csv(stage2)) if stage2.exists() else None
        update_perf_ledger(
            report_dir=report_dir,
            cache_dir=cache_dir,
            stamp=stamp,
            fund_df=fund_df,
            soft_drops=soft,
            n_stage2=n_stage2,
            publish=publish,
            backfill_all_history=False,
        )
        ingested.append(stamp)
        have.add(stamp)
    return ingested


def update_perf_ledger(
    *,
    report_dir: str | Path,
    cache_dir: str | Path,
    stamp: str,
    fund_df: pd.DataFrame,
    soft_drops: pd.DataFrame | None = None,
    n_stage2: int | None = None,
    params_sha: str | None = None,
    publish: bool = True,
    backfill_all_history: bool = True,
) -> dict:
    """Append today's baskets and backfill forward panels. Safe for small N."""
    report_dir = Path(report_dir)
    out = perf_dir(report_dir)
    as_of = _stamp_as_of(stamp)

    baskets = assign_baskets(fund_df, soft_drops)
    members = basket_members_rows(baskets, stamp=stamp, as_of=as_of)
    members_path = out / "basket_members_panel.csv"
    _upsert_panel(members_path, members, key_cols=["stamp", "basket", "ticker"])

    pool_row = daily_pool_row(
        stamp=stamp,
        as_of=as_of,
        n_stage2=n_stage2,
        fund_df=fund_df,
        baskets=baskets,
        params_sha=params_sha,
    )
    pool_path = out / "daily_pool_log.csv"
    append_log_row(pool_path, pool_row)

    # Forward panel: today's members always; optionally rebuild full history backfill
    if backfill_all_history and members_path.exists():
        all_members = pd.read_csv(members_path)
    else:
        all_members = members
    fwd = backfill_security_forward(all_members, cache_dir=cache_dir)
    fwd_path = out / "security_forward_panel.csv"
    fwd.to_csv(fwd_path, index=False)

    # Today's slice summary into growing log
    today_fwd = fwd.loc[fwd["stamp"].astype(str) == str(stamp)] if not fwd.empty else fwd
    summary = summarize_basket_forward(today_fwd, stamp=stamp)
    summary_path = out / "basket_forward_summary_log.csv"
    if not summary.empty:
        # replace same stamp rows
        if summary_path.exists():
            try:
                hist = pd.read_csv(summary_path)
                hist = hist.loc[hist["stamp"].astype(str) != str(stamp)]
                summary = pd.concat([hist, summary], ignore_index=True)
            except Exception:  # noqa: BLE001
                pass
        summary.to_csv(summary_path, index=False)

    # readiness snapshot for console
    ready_counts = {}
    for lab, _ in EVENT_FWD_HORIZONS:
        col = f"ready_{lab}"
        ready_counts[lab] = int(fwd[col].sum()) if not fwd.empty and col in fwd.columns else 0

    published: list[Path] = []
    paths = [pool_path, members_path, fwd_path, summary_path]
    if publish:
        published = publish_many([p for p in paths if p.exists()])

    return {
        "ok": True,
        "dir": out,
        "pool_log": pool_path,
        "members": members_path,
        "forward": fwd_path,
        "summary_log": summary_path,
        "n_baskets": {k: len(v) for k, v in baskets.items()},
        "n_forward_rows": int(len(fwd)),
        "ready_counts": ready_counts,
        "published": published,
        "pool_row": pool_row,
    }
