"""SEPA screener CLI.

Runs the full pipeline: load universe -> update price cache -> RS ranks ->
Trend Template filter -> VCP detection -> report.

Usage:
    python -m sepa.screener [--config config/params.yaml]
                            [--universe config/universe.yaml]
                            [--as-of YYYY-MM-DD] [--no-update]
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from sepa import indicators, trend_template, vcp
from sepa.config import Params, load_params, load_universe
from sepa.data import store

logger = logging.getLogger(__name__)

REPORT_COLUMNS = [
    "ticker", "signal", "close", "pivot", "dist_to_pivot_pct", "rs_rank",
    "base_weeks", "footprint", "final_depth_pct", "dryup_ratio", "volume_vs_avg", "note",
]

SIGNAL_ORDER = {s.value: i for i, s in enumerate(
    [vcp.Signal.BREAKOUT, vcp.Signal.WATCHLIST, vcp.Signal.FORMING, vcp.Signal.EXTENDED]
)}


def screen(
    params: Params,
    tickers: list[str],
    as_of: str | None = None,
    update: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the screen; returns (setups, diagnostics) DataFrames."""
    data, failed = store.load_universe_history(
        tickers, params.data.cache_dir, params.data.lookback_years, update
    )
    if failed:
        logger.warning("failed to load: %s", ", ".join(failed))

    if as_of:
        cutoff = pd.Timestamp(as_of)
        data = {t: df.loc[:cutoff] for t, df in data.items()}

    data = {t: df for t, df in data.items() if len(df) >= params.data.min_history_days}
    rs_ranks = indicators.compute_rs_ranks(data)

    setups, diagnostics = [], []
    for ticker, df in sorted(data.items()):
        enriched = indicators.add_indicators(df, params.trend_template)
        rs_rank = rs_ranks.get(ticker)
        tt = trend_template.evaluate(enriched, params.trend_template, rs_rank)

        diag = {
            "ticker": ticker,
            "close": round(float(df["close"].iloc[-1]), 2),
            "rs_rank": round(rs_rank, 1) if rs_rank is not None else None,
            "tt_passed": tt.passed,
            "tt_failed_conditions": ",".join(k for k, v in tt.conditions.items() if not v),
            "vcp_status": "",
        }

        if tt.passed:
            res = vcp.detect_vcp(enriched, params.vcp)
            diag["vcp_status"] = res.signal.value if res.valid else f"invalid: {res.reason}"
            if res.valid:
                setups.append({
                    "ticker": ticker,
                    "signal": res.signal.value,
                    "close": diag["close"],
                    "pivot": res.pivot,
                    "dist_to_pivot_pct": res.dist_to_pivot_pct,
                    "rs_rank": diag["rs_rank"],
                    "base_weeks": res.base_weeks,
                    "footprint": res.footprint,
                    "final_depth_pct": round(res.final_depth * 100, 1),
                    "dryup_ratio": res.dryup_ratio_actual,
                    "volume_vs_avg": res.volume_vs_avg,
                    "note": res.reason,
                })
        diagnostics.append(diag)

    setups_df = pd.DataFrame(setups, columns=REPORT_COLUMNS)
    if not setups_df.empty:
        setups_df = setups_df.sort_values(
            by="signal", key=lambda s: s.map(SIGNAL_ORDER)
        ).reset_index(drop=True)
    return setups_df, pd.DataFrame(diagnostics)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SEPA Stage2 + VCP screener")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--universe", default="config/universe.yaml")
    parser.add_argument("--as-of", default=None, help="screen as of date YYYY-MM-DD (for validation)")
    parser.add_argument("--no-update", action="store_true", help="use cache only, skip downloads")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    params = load_params(args.config)
    tickers = load_universe(args.universe)
    setups, diagnostics = screen(params, tickers, as_of=args.as_of, update=not args.no_update)

    stamp = (args.as_of or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
    out_dir = Path(params.report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    setups_path = out_dir / f"screen_{stamp}.csv"
    diag_path = out_dir / f"diagnostics_{stamp}.csv"
    setups.to_csv(setups_path, index=False)
    diagnostics.to_csv(diag_path, index=False)

    print(f"\n=== SEPA screen ({args.as_of or 'latest'}) — universe: {len(tickers)} tickers ===\n")
    print("--- Trend Template (Stage 2) ---")
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(diagnostics.to_string(index=False))
        print("\n--- VCP setups ---")
        if setups.empty:
            print("(no setups today)")
        else:
            print(setups.to_string(index=False))
    print(f"\nreports: {setups_path}, {diag_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
