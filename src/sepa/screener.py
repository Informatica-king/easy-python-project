"""Stage 2 screener CLI.

Pipeline: load universe -> update price cache -> RS ranks -> Trend Template
(8 conditions) -> list of Stage 2 companies as "회사명-티커" strings.

VCP entry timing is intentionally NOT part of this screener: the workflow is
to review this Stage 2 list manually (fundamentals, ranking) and then run
`python -m sepa.vcp_timing` on the chosen shortlist.

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

from sepa import indicators, trend_template
from sepa.config import Params, UniverseFilterParams, load_params, load_universe
from sepa.data import store, universe

logger = logging.getLogger(__name__)


def passes_liquidity(df: pd.DataFrame, uf: UniverseFilterParams) -> bool:
    """Liquidity pre-filter: minimum price and 50-day average dollar volume."""
    if float(df["close"].iloc[-1]) < uf.min_price:
        return False
    dollar_volume = (df["close"] * df["volume"]).tail(50).mean()
    return float(dollar_volume) >= uf.min_avg_dollar_volume


def screen_stage2(
    params: Params,
    tickers: list[str],
    as_of: str | None = None,
    update: bool = True,
    names: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the Stage 2 screen.

    Returns (stage2, diagnostics):
      stage2      — rows for tickers passing all Trend Template conditions,
                    sorted by RS rank (desc), with company names attached.
      diagnostics — one row per screened ticker with failed conditions.
    """
    data, failed = store.load_universe_history(
        tickers, params.data.cache_dir, params.data.lookback_years, update
    )
    if failed:
        logger.warning("failed to load: %s", ", ".join(failed))

    if as_of:
        cutoff = pd.Timestamp(as_of)
        data = {t: df.loc[:cutoff] for t, df in data.items()}

    n_loaded = len(data)
    data = {t: df for t, df in data.items() if len(df) >= params.data.min_history_days}
    n_history = len(data)
    data = {t: df for t, df in data.items() if passes_liquidity(df, params.universe_filter)}
    n_liquidity = len(data)
    logger.info(
        "universe funnel: loaded=%d -> history>=%dd: %d -> liquidity: %d",
        n_loaded, params.data.min_history_days, n_history, n_liquidity,
    )
    rs_ranks = indicators.compute_rs_ranks(data)
    names = names or {}

    stage2_rows, diag_rows = [], []
    for ticker, df in sorted(data.items()):
        enriched = indicators.add_indicators(df, params.trend_template)
        rs_rank = rs_ranks.get(ticker)
        tt = trend_template.evaluate(enriched, params.trend_template, rs_rank)

        row = {
            "ticker": ticker,
            "name": names.get(ticker, ""),
            "close": round(float(df["close"].iloc[-1]), 2),
            "rs_rank": round(rs_rank, 1) if rs_rank is not None else None,
        }
        diag_rows.append({
            **row,
            "stage2": tt.passed,
            "failed_conditions": ",".join(k for k, v in tt.conditions.items() if not v),
        })
        if tt.passed:
            stage2_rows.append(row)

    stage2 = pd.DataFrame(stage2_rows, columns=["ticker", "name", "close", "rs_rank"])
    if not stage2.empty:
        stage2 = stage2.sort_values("rs_rank", ascending=False).reset_index(drop=True)
    diagnostics = pd.DataFrame(diag_rows)
    diagnostics.attrs["funnel"] = {
        "n_universe": len(tickers),
        "n_loaded": n_loaded,
        "n_history": n_history,
        "n_liquidity": n_liquidity,
    }
    return stage2, diagnostics


RS_HIGHLIGHT_MIN = 90.0  # 결과 제시 시 이 점수 이상은 항상 전부 나열 (사용자 지정 기준)


def format_stage2_list(stage2: pd.DataFrame, with_rs: bool = False) -> list[str]:
    """Format Stage 2 rows as '회사명-티커' strings (name falls back to ticker)."""
    out = []
    for _, row in stage2.iterrows():
        name = row["name"] or row["ticker"]
        entry = f"{name}-{row['ticker']}"
        if with_rs and row["rs_rank"] is not None and not pd.isna(row["rs_rank"]):
            entry += f"  (RS {row['rs_rank']:.1f})"
        out.append(entry)
    return out


def print_stage2_sections(stage2: pd.DataFrame) -> None:
    """RS 90+ 섹션(전부 나열) + 나머지 섹션, 모두 RS 점수 포함 내림차순."""
    if stage2.empty:
        print("(none)")
        return
    top = stage2[stage2["rs_rank"] >= RS_HIGHLIGHT_MIN]
    rest = stage2[stage2["rs_rank"] < RS_HIGHLIGHT_MIN]
    print(f"◆ RS {RS_HIGHLIGHT_MIN:.0f} 이상 ({len(top)})")
    for entry in format_stage2_list(top, with_rs=True):
        print(f"  {entry}")
    if not rest.empty:
        print(f"\n◆ 그 외 Stage 2 기업 ({len(rest)})")
        for entry in format_stage2_list(rest, with_rs=True):
            print(f"  {entry}")


def stage2_list(
    params: Params,
    tickers: list[str],
    as_of: str | None = None,
    update: bool = True,
    names: dict[str, str] | None = None,
) -> list[str]:
    """Convenience wrapper: Stage 2 companies as '회사명-티커' strings."""
    stage2, _ = screen_stage2(params, tickers, as_of=as_of, update=update, names=names)
    return format_stage2_list(stage2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SEPA Stage 2 screener")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--universe", default="config/universe.yaml")
    parser.add_argument(
        "--full", action="store_true",
        help="screen the full Nasdaq universe (ETFs excluded) instead of --universe",
    )
    parser.add_argument("--as-of", default=None, help="screen as of date YYYY-MM-DD (for validation)")
    parser.add_argument("--no-update", action="store_true", help="use cache only, skip downloads")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    params = load_params(args.config)

    try:
        names = universe.security_names(cache_dir=params.data.cache_dir)
    except Exception as exc:  # noqa: BLE001 - names are cosmetic, never fatal
        logger.warning("could not load company names: %s", exc)
        names = {}

    update = not args.no_update
    if args.full:
        listed = universe.fetch_nasdaq_listed(cache_dir=params.data.cache_dir)
        tickers = universe.common_stock_tickers(listed)
        logger.info("full Nasdaq universe: %d tickers", len(tickers))
        if update:
            tickers, failed = store.bulk_update(
                tickers, params.data.cache_dir, params.data.lookback_years
            )
            logger.info("bulk update done: ok=%d failed=%d", len(tickers), len(failed))
        update = False  # per-ticker fetch already covered by bulk_update
    else:
        tickers = load_universe(args.universe)

    stage2, diagnostics = screen_stage2(
        params, tickers, as_of=args.as_of, update=update, names=names
    )

    stamp = (args.as_of or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
    out_dir = Path(params.report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stage2_path = out_dir / f"stage2_{stamp}.csv"
    diag_path = out_dir / f"diagnostics_{stamp}.csv"
    stage2.to_csv(stage2_path, index=False)
    diagnostics.to_csv(diag_path, index=False)

    from sepa.artifacts import publish_many
    from sepa.result_ledger import save_diagnostics_summary

    funnel = getattr(diagnostics, "attrs", {}).get("funnel") or {}
    diag_sum = save_diagnostics_summary(
        diagnostics,
        out_dir,
        stamp,
        n_universe=funnel.get("n_universe", len(tickers)),
        n_history=funnel.get("n_history"),
        n_liquidity=funnel.get("n_liquidity", len(diagnostics)),
        publish=True,
    )
    publish_many([stage2_path])  # full diagnostics stay local; summary is the artifact

    print(f"\n=== SEPA Stage 2 screen ({args.as_of or 'latest'}) — universe: {len(tickers)} tickers ===\n")
    print(f"--- Stage 2 진입 기업 ({len(stage2)}) — RS 순위 내림차순 ---")
    print_stage2_sections(stage2)
    print(f"\nreports: {stage2_path}, {diag_path}")
    if diag_sum.get("daily"):
        row = diag_sum.get("row") or {}
        print(
            f"diagnostics summary: stage2={row.get('n_stage2')}/{row.get('n_screened')} "
            f"(rate={row.get('stage2_rate')}) → {diag_sum['daily']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
