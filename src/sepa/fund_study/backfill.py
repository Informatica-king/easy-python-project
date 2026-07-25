"""Price-history backfill for the fund weight study (10y lookback)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from sepa.data import store, universe
from sepa.fund_study.config import ADV_LOOKBACK_DAYS, MIN_ADV, STUDY_YEARS
from sepa.fund_study.universe import _is_adr_name, compute_adv

logger = logging.getLogger(__name__)


def history_span_years(cache_dir: str | Path, ticker: str) -> float | None:
    path = store._cache_path(cache_dir, ticker)
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
    except Exception:  # noqa: BLE001
        return None
    if df is None or df.empty:
        return None
    span = (df.index.max() - df.index.min()).days / 365.25
    return float(span)


def list_adv_candidates(
    *,
    cache_dir: str | Path,
    lookback_years: int,
) -> list[str]:
    """Nasdaq common non-ADR with ADV >= $5M (from current price cache)."""
    listed = universe.fetch_nasdaq_listed(cache_dir=cache_dir)
    names = universe.security_names(listed, cache_dir=cache_dir)
    common = universe.common_stock_tickers(listed)
    out: list[str] = []
    for t in common:
        if _is_adr_name(names.get(t, "")):
            continue
        adv = compute_adv(t, cache_dir, lookback_years)
        if adv is not None and adv >= MIN_ADV:
            out.append(t)
    return out


def partition_backfill_targets(
    tickers: list[str],
    *,
    cache_dir: str | Path,
    min_span_years: float,
    force: bool = False,
) -> tuple[list[str], list[str]]:
    """Split into (need_backfill, already_ok)."""
    need: list[str] = []
    ok: list[str] = []
    for t in tickers:
        if force:
            need.append(t)
            continue
        span = history_span_years(cache_dir, t)
        if span is None or span < min_span_years:
            need.append(t)
        else:
            ok.append(t)
    return need, ok


def run_price_backfill(
    *,
    cache_dir: str | Path,
    lookback_years: int = STUDY_YEARS + 1,
    min_span_years: float = 9.5,
    chunk_size: int = 40,
    pause_sec: float = 1.5,
    force: bool = False,
    tickers: list[str] | None = None,
) -> dict:
    """Backfill OHLCV for ADV>=$5M candidates (or an explicit ticker list)."""
    if tickers is None:
        print(f"scanning ADV>=${MIN_ADV/1e6:.0f}M candidates (ADV window {ADV_LOOKBACK_DAYS}d)...")
        tickers = list_adv_candidates(cache_dir=cache_dir, lookback_years=max(3, lookback_years))
    print(f"candidates: {len(tickers)}")

    need, already = partition_backfill_targets(
        tickers,
        cache_dir=cache_dir,
        min_span_years=min_span_years,
        force=force,
    )
    print(
        f"already >= {min_span_years:.1f}y: {len(already)} | "
        f"to backfill: {len(need)} (lookback={lookback_years}y, chunk={chunk_size})"
    )
    if not need:
        return {
            "ok": True,
            "candidates": len(tickers),
            "skipped": len(already),
            "requested": 0,
            "ok_tickers": [],
            "failed": [],
        }

    ok_list, failed = store.backfill_history(
        need,
        cache_dir,
        lookback_years=lookback_years,
        chunk_size=chunk_size,
        pause_sec=pause_sec,
    )

    # Summarize spans after
    spans = []
    for t in ok_list:
        s = history_span_years(cache_dir, t)
        if s is not None:
            spans.append(s)
    span_s = pd.Series(spans) if spans else pd.Series(dtype=float)
    summary = {
        "ok": True,
        "candidates": len(tickers),
        "skipped": len(already),
        "requested": len(need),
        "ok_tickers": ok_list,
        "failed": failed,
        "span_min": float(span_s.min()) if len(span_s) else None,
        "span_median": float(span_s.median()) if len(span_s) else None,
        "span_ge_9_5": int((span_s >= 9.5).sum()) if len(span_s) else 0,
        "span_ge_7": int((span_s >= 7).sum()) if len(span_s) else 0,
    }
    print(
        f"backfill done: ok={len(ok_list)} failed={len(failed)} | "
        f"span median={summary['span_median']} "
        f">=9.5y={summary['span_ge_9_5']} >=7y={summary['span_ge_7']}"
    )
    if failed:
        print(f"  failed sample: {failed[:20]}")
    return summary
