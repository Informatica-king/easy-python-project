"""정량 펀더멘털 점수 CLI — Stage 2 · RS≥80 → fund_score 내림차순.

Usage:
    python -m sepa.fundamental [--config config/params.yaml]
                               [--full | --from-stage2 reports/stage2_YYYYMMDD.csv]
                               [--as-of YYYY-MM-DD] [--no-update] [--refresh-fundamentals]
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from sepa import screener
from sepa.analyze import enrich_with_sectors
from sepa.candidates import apply_candidate_filters, summarize_drops
from sepa.config import Params, load_params, load_universe
from sepa.data import fundamentals as fund_data
from sepa.data import store, universe
from sepa.fundamental_score import DEFAULT_WEIGHTS, FundamentalWeights, score_ticker

logger = logging.getLogger(__name__)


def _weights_from_params(params: Params) -> FundamentalWeights:
    w = params.fundamental
    return FundamentalWeights(
        eps_yoy=w.eps_yoy,
        eps_accel=w.eps_accel,
        sales_yoy=w.sales_yoy,
        sales_accel=w.sales_accel,
        margin_improve=w.margin_improve,
        roe=w.roe,
    )


def load_stage2_candidates(
    params: Params,
    *,
    full: bool,
    universe_path: str,
    from_stage2: str | None,
    as_of: str | None,
    update: bool,
) -> pd.DataFrame:
    """Return Stage 2 rows with columns ticker, name, close, rs_rank (RS≥ min)."""
    rs_min = params.fundamental.rs_min

    if from_stage2:
        stage2 = pd.read_csv(from_stage2)
        if "rs_rank" not in stage2.columns or "ticker" not in stage2.columns:
            raise ValueError(f"{from_stage2} must contain ticker, rs_rank columns")
        if "name" not in stage2.columns:
            stage2["name"] = ""
        out = stage2[stage2["rs_rank"] >= rs_min].copy()
        return out.sort_values("rs_rank", ascending=False).reset_index(drop=True)

    try:
        names = universe.security_names(cache_dir=params.data.cache_dir)
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not load company names: %s", exc)
        names = {}

    if full:
        listed = universe.fetch_nasdaq_listed(cache_dir=params.data.cache_dir)
        tickers = universe.common_stock_tickers(listed)
        logger.info("full Nasdaq universe: %d tickers", len(tickers))
        if update:
            tickers, failed = store.bulk_update(
                tickers, params.data.cache_dir, params.data.lookback_years
            )
            logger.info("bulk update done: ok=%d failed=%d", len(tickers), len(failed))
            update = False
    else:
        tickers = load_universe(universe_path)

    stage2, _ = screener.screen_stage2(
        params, tickers, as_of=as_of, update=update, names=names
    )
    if stage2.empty:
        return stage2
    return stage2[stage2["rs_rank"] >= rs_min].reset_index(drop=True)


def score_universe(
    candidates: pd.DataFrame,
    params: Params,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    fund_dir = fund_data.cache_dir(params.data.cache_dir)
    cik_map = fund_data.load_cik_map(fund_dir)
    weights = _weights_from_params(params)

    rows = []
    n = len(candidates)
    for i, row in enumerate(candidates.itertuples(index=False), start=1):
        ticker = str(row.ticker).upper()
        if i == 1 or i % 10 == 0 or i == n:
            logger.info("fundamentals %d/%d %s", i, n, ticker)
        quarterly, roe, source = fund_data.load_quarterly(
            ticker, fund_dir, cik_map, refresh=refresh
        )
        br = score_ticker(
            ticker,
            quarterly,
            roe,
            source=source,
            weights=weights,
            roe_target=params.fundamental.roe_target,
        )
        d = br.as_dict()
        d["name"] = getattr(row, "name", "") or ""
        d["close"] = getattr(row, "close", None)
        d["rs_rank"] = getattr(row, "rs_rank", None)
        rows.append(d)

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(
        ["fund_score", "rs_rank"], ascending=[False, False]
    ).reset_index(drop=True)


def print_fundamental_list(df: pd.DataFrame) -> None:
    if df.empty:
        print("(none)")
        return
    for _, row in df.iterrows():
        name = row.get("name") or row["ticker"]
        rs = row["rs_rank"]
        fund = row["fund_score"]
        rs_s = f"{rs:.1f}" if rs is not None and not pd.isna(rs) else "n/a"
        print(f"  {name}-{row['ticker']}  (RS {rs_s} | Fund {fund:.1f})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SEPA quantitative fundamental scorer")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--universe", default="config/universe.yaml")
    parser.add_argument(
        "--full", action="store_true",
        help="screen full Nasdaq then score RS≥80 Stage 2 names",
    )
    parser.add_argument(
        "--from-stage2", default=None,
        help="skip rescreen; use an existing stage2_*.csv",
    )
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--no-update", action="store_true")
    parser.add_argument(
        "--refresh-fundamentals", action="store_true",
        help="ignore fundamentals cache and re-fetch SEC/yfinance",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    params = load_params(args.config)
    rs_min = params.fundamental.rs_min

    candidates = load_stage2_candidates(
        params,
        full=bool(args.full),
        universe_path=args.universe,
        from_stage2=args.from_stage2,
        as_of=args.as_of,
        update=not args.no_update,
    )

    logger.info("candidates (Stage 2 & RS>=%.0f): %d", rs_min, len(candidates))
    scored = score_universe(
        candidates, params, refresh=args.refresh_fundamentals
    )

    # Attach market cap then drop Fund=0 / sub-$1B names from the candidate list
    if not scored.empty:
        scored = enrich_with_sectors(
            scored, params.data.cache_dir, refresh=False
        )
        before_n = len(scored)
        scored, dropped = apply_candidate_filters(scored)
        print(
            f"\n후보 필터: {before_n} → {len(scored)}  "
            f"({summarize_drops(dropped)}; Fund=0 또는 시총 <$1B 제외)"
        )

    stamp = (args.as_of or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
    out_dir = Path(params.report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"fundamental_{stamp}.csv"
    scored.to_csv(out_path, index=False)

    print(
        f"\n=== SEPA Fundamental scores "
        f"(Stage 2 · RS≥{rs_min:.0f} · 후보필터 적용, n={len(scored)}) "
        f"— fund_score desc ===\n"
    )
    print_fundamental_list(scored)
    print(f"\nreport: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
