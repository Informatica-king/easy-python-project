"""Daily result-data accumulation helpers for model analysis.

Persists compact longitudinal logs that survive as Cursor artifacts / release
assets (full diagnostics dumps stay on disk but are not the primary artifact).

1. params snapshot + hash log
2. Fund score quantile 1-row log
3. diagnostics condition pass-rate summary
4. sepaTop enter/exit forward-return panel (backfilled when prices allow)
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from sepa.artifacts import publish_many
from sepa.model_metrics import _ensure_benchmark, _load_close_series
from sepa.rs_fund_region_study import forward_return

logger = logging.getLogger(__name__)

# Trend Template condition keys (docs/strategy_spec.md §3)
TT_CONDITION_KEYS = (
    "1_above_mid_long_ma",
    "2_mid_above_long",
    "3_long_ma_rising",
    "4_ma_stack",
    "5_above_short_ma",
    "6_above_52w_low",
    "7_near_52w_high",
    "8_rs_rank",
)

EVENT_FWD_HORIZONS = (
    ("5d", 5),
    ("10d", 10),
    ("21d", 21),
)


def _stamp_as_of(stamp: str) -> str:
    if len(stamp) == 8 and stamp.isdigit():
        return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"
    return stamp


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def append_log_row(path: Path, row: dict, *, key_cols: tuple[str, ...] = ("stamp",)) -> pd.DataFrame:
    """Append one row to a CSV log, replacing any existing row with the same keys."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame([row])
    if path.exists():
        try:
            hist = pd.read_csv(path)
            for k in key_cols:
                if k in hist.columns and k in new.columns:
                    hist[k] = hist[k].astype(str)
                    new[k] = new[k].astype(str)
            mask = pd.Series(True, index=hist.index)
            for k in key_cols:
                if k in hist.columns:
                    mask &= hist[k].astype(str) == str(row.get(k, ""))
            hist = hist.loc[~mask]
            out = pd.concat([hist, new], ignore_index=True)
        except Exception:  # noqa: BLE001
            logger.warning("rebuild log from new row only: %s", path)
            out = new
    else:
        out = new
    out.to_csv(path, index=False)
    return out


# ---------------------------------------------------------------------------
# 1. params snapshot
# ---------------------------------------------------------------------------

def save_params_snapshot(
    config_path: str | Path,
    report_dir: str | Path,
    stamp: str,
    *,
    publish: bool = True,
) -> dict:
    """Copy params YAML + append hash/meta row. Returns path dict."""
    config_path = Path(config_path)
    report_dir = Path(report_dir)
    snap_dir = report_dir / "params_snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)

    digest = file_sha256(config_path) if config_path.exists() else ""
    yaml_out = snap_dir / f"params_{stamp}.yaml"
    if config_path.exists():
        shutil.copy2(config_path, yaml_out)

    meta = {
        "stamp": stamp,
        "as_of": _stamp_as_of(stamp),
        "config_path": str(config_path),
        "sha256": digest,
        "sha256_short": digest[:12] if digest else "",
        "bytes": int(config_path.stat().st_size) if config_path.exists() else 0,
    }
    # pull a few live knobs for quick scanning without opening YAML
    try:
        from sepa.config import load_params

        p = load_params(config_path)
        meta.update(
            {
                "rs_rank_min": p.trend_template.rs_rank_min,
                "rs_min": p.fundamental.rs_min,
                "rs_soft_max": p.fundamental.rs_soft_max,
                "rs_high_requires_fund_median": p.fundamental.rs_high_requires_fund_median,
                "quality_enabled": p.fundamental.quality_enabled,
                "fund_quality_min": p.fundamental.fund_quality_min,
                "w_surprise": p.fundamental.eps_surprise,
                "w_opm": p.fundamental.opm_delta,
                "w_eps_dyoy": p.fundamental.eps_dyoy,
                "w_sales_dyoy": p.fundamental.sales_dyoy,
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("params meta extract failed: %s", exc)

    log_path = report_dir / "params_hash_log.csv"
    append_log_row(log_path, meta)
    meta_path = snap_dir / f"params_meta_{stamp}.csv"
    pd.DataFrame([meta]).to_csv(meta_path, index=False)

    published: list[Path] = []
    if publish:
        published = publish_many([yaml_out, meta_path, log_path])
    return {
        "ok": True,
        "yaml": yaml_out,
        "meta": meta_path,
        "log": log_path,
        "sha256": digest,
        "published": published,
    }


# ---------------------------------------------------------------------------
# 2. Fund quantile log
# ---------------------------------------------------------------------------

def fund_quantile_row(df: pd.DataFrame, *, stamp: str, as_of: str | None = None) -> dict:
    fund = pd.to_numeric(df.get("fund_score"), errors="coerce").dropna()
    rs = pd.to_numeric(df.get("rs_rank"), errors="coerce").dropna() if "rs_rank" in df.columns else pd.Series(dtype=float)
    row: dict = {
        "stamp": stamp,
        "as_of": as_of or _stamp_as_of(stamp),
        "n": int(len(fund)),
        "fund_mean": float(fund.mean()) if len(fund) else np.nan,
        "fund_median": float(fund.median()) if len(fund) else np.nan,
        "fund_std": float(fund.std(ddof=0)) if len(fund) else np.nan,
        "fund_min": float(fund.min()) if len(fund) else np.nan,
        "fund_q10": float(fund.quantile(0.10)) if len(fund) else np.nan,
        "fund_q25": float(fund.quantile(0.25)) if len(fund) else np.nan,
        "fund_q75": float(fund.quantile(0.75)) if len(fund) else np.nan,
        "fund_q90": float(fund.quantile(0.90)) if len(fund) else np.nan,
        "fund_max": float(fund.max()) if len(fund) else np.nan,
        "rs_median": float(rs.median()) if len(rs) else np.nan,
        "rs_mean": float(rs.mean()) if len(rs) else np.nan,
        "n_rs90_plus": int((rs >= 90).sum()) if len(rs) else 0,
        "n_rs70_89": int(((rs >= 70) & (rs < 90)).sum()) if len(rs) else 0,
    }
    return row


def save_fund_quantile_log(
    df: pd.DataFrame,
    report_dir: str | Path,
    stamp: str,
    *,
    publish: bool = True,
) -> dict:
    report_dir = Path(report_dir)
    row = fund_quantile_row(df, stamp=stamp)
    daily = report_dir / f"fund_quantile_{stamp}.csv"
    pd.DataFrame([row]).to_csv(daily, index=False)
    log_path = report_dir / "fund_quantile_log.csv"
    append_log_row(log_path, row)
    published = publish_many([daily, log_path]) if publish else []
    return {"ok": True, "daily": daily, "log": log_path, "row": row, "published": published}


# ---------------------------------------------------------------------------
# 3. diagnostics pass-rate summary
# ---------------------------------------------------------------------------

def diagnostics_summary_row(
    diagnostics: pd.DataFrame,
    *,
    stamp: str,
    as_of: str | None = None,
    n_universe: int | None = None,
    n_history: int | None = None,
    n_liquidity: int | None = None,
) -> dict:
    """One-row pass-rate summary (avoids publishing the full diagnostics dump)."""
    as_of = as_of or _stamp_as_of(stamp)
    row: dict = {
        "stamp": stamp,
        "as_of": as_of,
        "n_universe": n_universe if n_universe is not None else np.nan,
        "n_history": n_history if n_history is not None else np.nan,
        "n_liquidity": n_liquidity if n_liquidity is not None else (len(diagnostics) if diagnostics is not None else 0),
        "n_screened": int(len(diagnostics)) if diagnostics is not None else 0,
        "n_stage2": 0,
        "stage2_rate": np.nan,
    }
    if diagnostics is None or diagnostics.empty:
        for k in TT_CONDITION_KEYS:
            row[f"pass_{k}"] = np.nan
        return row

    work = diagnostics.copy()
    if "stage2" in work.columns:
        stage2 = work["stage2"].astype(bool)
        row["n_stage2"] = int(stage2.sum())
        row["stage2_rate"] = float(stage2.mean())
    elif "failed_conditions" in work.columns:
        failed = work["failed_conditions"].fillna("").astype(str)
        row["n_stage2"] = int((failed.str.strip() == "").sum())
        row["stage2_rate"] = float(row["n_stage2"] / len(work)) if len(work) else np.nan

    failed_lists = (
        work["failed_conditions"].fillna("").astype(str).str.split(",")
        if "failed_conditions" in work.columns
        else pd.Series([[]] * len(work))
    )
    n = len(work)
    for key in TT_CONDITION_KEYS:
        fail_n = 0
        for parts in failed_lists:
            toks = {p.strip() for p in parts if p and str(p).strip()}
            if key in toks:
                fail_n += 1
        row[f"pass_{key}"] = float(1.0 - fail_n / n) if n else np.nan
    return row


def save_diagnostics_summary(
    diagnostics: pd.DataFrame,
    report_dir: str | Path,
    stamp: str,
    *,
    n_universe: int | None = None,
    n_history: int | None = None,
    n_liquidity: int | None = None,
    publish: bool = True,
) -> dict:
    report_dir = Path(report_dir)
    row = diagnostics_summary_row(
        diagnostics,
        stamp=stamp,
        n_universe=n_universe,
        n_history=n_history,
        n_liquidity=n_liquidity,
    )
    daily = report_dir / f"diagnostics_summary_{stamp}.csv"
    pd.DataFrame([row]).to_csv(daily, index=False)
    log_path = report_dir / "diagnostics_summary_log.csv"
    append_log_row(log_path, row)
    published = publish_many([daily, log_path]) if publish else []
    return {"ok": True, "daily": daily, "log": log_path, "row": row, "published": published}


# ---------------------------------------------------------------------------
# 4. enter/exit forward returns
# ---------------------------------------------------------------------------

def load_membership_change_events(sepatop_report: str | Path) -> pd.DataFrame:
    sepatop_report = Path(sepatop_report)
    frames = []
    for path in sorted(sepatop_report.glob("membership_changes_*.csv")):
        try:
            df = pd.read_csv(path)
        except Exception:  # noqa: BLE001
            continue
        if df.empty:
            continue
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["stamp", "as_of", "prev_stamp", "action", "ticker"])
    out = pd.concat(frames, ignore_index=True)
    out["ticker"] = out["ticker"].astype(str).str.upper()
    out["action"] = out["action"].astype(str).str.lower()
    out["stamp"] = out["stamp"].astype(str)
    return out.drop_duplicates(subset=["stamp", "action", "ticker"], keep="last")


def compute_membership_event_forward(
    events: pd.DataFrame,
    *,
    cache_dir: str | Path,
    benchmark: str = "^GSPC",
    horizons: tuple[tuple[str, int], ...] = EVENT_FWD_HORIZONS,
) -> pd.DataFrame:
    """Wide panel: one row per enter/exit event with fwd/excess columns when available."""
    if events is None or events.empty:
        cols = ["stamp", "as_of", "action", "ticker"]
        for lab, _ in horizons:
            cols += [f"fwd_{lab}", f"bench_{lab}", f"excess_{lab}", f"ready_{lab}"]
        return pd.DataFrame(columns=cols)

    bench = _ensure_benchmark(cache_dir, benchmark)
    if bench.empty:
        bench = _ensure_benchmark(cache_dir, "SPY")
    px_cache: dict[str, pd.Series] = {}
    rows = []
    for _, ev in events.iterrows():
        stamp = str(ev.get("stamp", ""))
        as_of_s = str(ev.get("as_of") or _stamp_as_of(stamp))
        try:
            as_of = pd.Timestamp(as_of_s)
        except Exception:  # noqa: BLE001
            continue
        ticker = str(ev.get("ticker", "")).upper()
        if not ticker:
            continue
        series = _load_close_series(ticker, cache_dir, px_cache)
        row = {
            "stamp": stamp,
            "as_of": as_of_s,
            "prev_stamp": ev.get("prev_stamp", ""),
            "action": str(ev.get("action", "")).lower(),
            "ticker": ticker,
        }
        for lab, h in horizons:
            ret = forward_return(series, as_of, h) if not series.empty else None
            bret = forward_return(bench, as_of, h) if not bench.empty else None
            ready = ret is not None
            row[f"fwd_{lab}"] = ret if ready else np.nan
            row[f"bench_{lab}"] = bret if bret is not None else np.nan
            if ready and bret is not None:
                row[f"excess_{lab}"] = float(ret) - float(bret)
            else:
                row[f"excess_{lab}"] = np.nan
            row[f"ready_{lab}"] = bool(ready)
        rows.append(row)
    return pd.DataFrame(rows)


def save_membership_event_forward(
    sepatop_report: str | Path,
    cache_dir: str | Path,
    stamp: str,
    *,
    publish: bool = True,
) -> dict:
    """Backfill forward returns for all known enter/exit events; publish panel."""
    sepatop_report = Path(sepatop_report)
    events = load_membership_change_events(sepatop_report)
    panel = compute_membership_event_forward(events, cache_dir=cache_dir)
    daily = sepatop_report / f"membership_event_fwd_{stamp}.csv"
    panel.to_csv(daily, index=False)
    log_path = sepatop_report / "membership_event_fwd_panel.csv"
    panel.to_csv(log_path, index=False)

    # compact ready-count summary for the console / md
    summary = {
        "stamp": stamp,
        "as_of": _stamp_as_of(stamp),
        "n_events": int(len(panel)),
        "n_enter": int((panel["action"] == "enter").sum()) if not panel.empty else 0,
        "n_exit": int((panel["action"] == "exit").sum()) if not panel.empty else 0,
    }
    for lab, _ in EVENT_FWD_HORIZONS:
        col = f"ready_{lab}"
        summary[f"ready_{lab}"] = int(panel[col].sum()) if not panel.empty and col in panel.columns else 0
        exc = f"excess_{lab}"
        if not panel.empty and exc in panel.columns and panel[exc].notna().any():
            summary[f"mean_excess_{lab}"] = float(panel[exc].mean(skipna=True))
        else:
            summary[f"mean_excess_{lab}"] = np.nan
    summary_path = sepatop_report / f"membership_event_fwd_summary_{stamp}.csv"
    pd.DataFrame([summary]).to_csv(summary_path, index=False)
    append_log_row(sepatop_report / "membership_event_fwd_summary_log.csv", summary)

    published = publish_many([daily, log_path, summary_path, sepatop_report / "membership_event_fwd_summary_log.csv"]) if publish else []
    return {
        "ok": True,
        "daily": daily,
        "panel": log_path,
        "summary": summary_path,
        "summary_row": summary,
        "published": published,
        "n_events": summary["n_events"],
    }
