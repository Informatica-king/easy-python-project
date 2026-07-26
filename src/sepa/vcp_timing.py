"""VCP entry-timing tool for a hand-picked shortlist.

Intended workflow: run `python -m sepa.screener` to get the Stage 2 list,
review fundamentals and rank manually, then feed the top names here to get
VCP setup status and pivot breakout timing per ticker.

Unlike the screener this tool does NOT gate on the Trend Template (the
shortlist is assumed to be already curated); it reports trend status for
reference only.

Usage:
    python -m sepa.vcp_timing --tickers NVDA,MSFT,AVGO
    python -m sepa.vcp_timing --tickers-file shortlist.txt [--as-of YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from sepa import indicators, trend_template, vcp
from sepa.config import Params, load_params
from sepa.data import store

logger = logging.getLogger(__name__)

REPORT_COLUMNS = [
    "ticker", "signal", "close", "pivot", "dist_to_pivot_pct", "trend_ok",
    "base_weeks", "footprint", "final_depth_pct", "dryup_ratio", "volume_vs_avg", "note",
]

SIGNAL_ORDER = {s.value: i for i, s in enumerate(
    [vcp.Signal.BREAKOUT, vcp.Signal.WATCHLIST, vcp.Signal.FORMING, vcp.Signal.EXTENDED, vcp.Signal.NONE]
)}


def analyze(
    params: Params,
    tickers: list[str],
    as_of: str | None = None,
    update: bool = True,
) -> pd.DataFrame:
    """Compute VCP timing signals for each ticker in the shortlist."""
    data, failed = store.load_universe_history(
        tickers, params.data.cache_dir, params.data.lookback_years, update
    )
    if failed:
        logger.warning("failed to load: %s", ", ".join(failed))

    if as_of:
        cutoff = pd.Timestamp(as_of)
        data = {t: df.loc[:cutoff] for t, df in data.items()}

    # RS rank needs a universe; on a small shortlist it is meaningless, so the
    # trend check here skips condition 8.
    tp_no_rs = dataclasses.replace(params.trend_template, rs_enabled=False)

    rows = []
    for ticker in tickers:
        df = data.get(ticker)
        if df is None or len(df) < params.data.min_history_days:
            rows.append({"ticker": ticker, "signal": "NO_DATA", "note": "가격 이력 부족"})
            continue
        enriched = indicators.add_indicators(df, params.trend_template)
        trend_ok = trend_template.evaluate(enriched, tp_no_rs).passed
        res = vcp.detect_vcp(enriched, params.vcp)
        rows.append({
            "ticker": ticker,
            "signal": res.signal.value if res.valid else "NONE",
            "close": round(float(df["close"].iloc[-1]), 2),
            "pivot": res.pivot,
            "dist_to_pivot_pct": res.dist_to_pivot_pct,
            "trend_ok": trend_ok,
            "base_weeks": res.base_weeks,
            "footprint": res.footprint,
            "final_depth_pct": round(res.final_depth * 100, 1) if res.final_depth is not None else None,
            "dryup_ratio": res.dryup_ratio_actual,
            "volume_vs_avg": res.volume_vs_avg,
            "note": res.reason,
        })

    report = pd.DataFrame(rows, columns=REPORT_COLUMNS)
    if not report.empty:
        report = report.sort_values(
            by="signal", key=lambda s: s.map(lambda v: SIGNAL_ORDER.get(v, len(SIGNAL_ORDER)))
        ).reset_index(drop=True)
    return report


def _parse_tickers(args: argparse.Namespace) -> list[str]:
    if args.tickers:
        return [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    lines = Path(args.tickers_file).read_text().splitlines()
    return [ln.strip().upper() for ln in lines if ln.strip() and not ln.startswith("#")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VCP entry timing for a shortlist")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tickers", help="comma-separated tickers, e.g. NVDA,MSFT")
    group.add_argument("--tickers-file", help="text file with one ticker per line")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--as-of", default=None, help="analyze as of date YYYY-MM-DD")
    parser.add_argument("--no-update", action="store_true", help="use cache only, skip downloads")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    params = load_params(args.config)
    tickers = _parse_tickers(args)
    report = analyze(params, tickers, as_of=args.as_of, update=not args.no_update)

    stamp = (args.as_of or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
    out_dir = Path(params.report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"vcp_{stamp}.csv"
    report.to_csv(report_path, index=False)

    print(f"\n=== VCP timing ({args.as_of or 'latest'}) — shortlist: {len(tickers)} tickers ===\n")
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(report.to_string(index=False))
    print(f"\nreport: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
