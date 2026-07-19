"""Fund weight study pipeline (docs/fund_weight_study_spec.md)."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from sepa.config import load_params
from sepa.data import fundamentals as fund_data
from sepa.fund_study.config import STUDY_YEARS, StudyPaths
from sepa.fund_study.events import (
    apply_liquidity_filter,
    build_event_returns_for_ticker,
    load_benchmark,
)
from sepa.fund_study.factors import enrich_events_with_factors, try_attach_surprises
from sepa.fund_study.report import save_study_outputs
from sepa.fund_study.stats import (
    choose_level_or_delta,
    factor_correlations,
    main_factors_only,
    partial_spearman_vs_y,
    propose_weights,
    quantile_response,
    yearly_stability,
)
from sepa.fund_study.universe import load_or_build_universe

logger = logging.getLogger(__name__)


def run_study(
    *,
    config: str = "config/params.yaml",
    pilot: int | None = 50,
    refresh_universe: bool = False,
    refresh_fundamentals: bool = False,
) -> dict:
    params = load_params(config)
    paths = StudyPaths()
    out_dir = Path(paths.report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")

    uni_path = Path(paths.cache_universe)
    print("\n=== Fund weight study ===")
    print(f"building/loading universe → {uni_path}")
    universe_df = load_or_build_universe(
        cache_dir=params.data.cache_dir,
        lookback_years=max(params.data.lookback_years, STUDY_YEARS + 1),
        out_path=uni_path,
        refresh=refresh_universe,
        target_n=pilot,
    )
    print(f"universe: {len(universe_df)} names (common, mcap>=$1B, ADV>=$5M)")

    tickers = universe_df["ticker"].astype(str).tolist()
    if pilot is not None and pilot > 0 and len(tickers) > pilot:
        tickers = tickers[:pilot]
        print(f"pilot mode: first {len(tickers)} tickers by mcap")
    elif pilot is not None and pilot > 0:
        print(f"pilot mode: {len(tickers)} tickers")

    print("loading NASDAQ benchmark...")
    bench = load_benchmark(params.data.cache_dir, max(params.data.lookback_years, STUDY_YEARS + 1))
    if bench.empty:
        print("[오류] benchmark ^IXIC 로드 실패")
        return {"ok": False}

    fund_dir = fund_data.cache_dir(params.data.cache_dir)
    cik_map = fund_data.load_cik_map(fund_dir)

    event_rows = []
    for i, t in enumerate(tickers, 1):
        if i % 25 == 0 or i == 1:
            print(f"  events {i}/{len(tickers)} ({t})")
        ev = build_event_returns_for_ticker(
            t,
            cache_dir=params.data.cache_dir,
            lookback_years=max(params.data.lookback_years, STUDY_YEARS + 1),
            bench=bench,
            years=STUDY_YEARS,
            cik_map=cik_map,
        )
        if not ev.empty:
            event_rows.append(ev)
    if not event_rows:
        print("[오류] 이벤트가 없습니다")
        return {"ok": False}

    events = pd.concat(event_rows, ignore_index=True)
    print(f"raw events: {len(events)}")
    events = apply_liquidity_filter(events)
    print(f"after event liquidity filter: {len(events)}")

    print("attaching fundamentals factors...")
    if refresh_fundamentals:
        # force reload by deleting is heavy; pass refresh into load via enrich path later if needed
        pass
    panel = enrich_events_with_factors(events, cache_dir=params.data.cache_dir, cik_map=cik_map)
    print(f"events with factors: {len(panel)}")
    panel = try_attach_surprises(panel)

    print("correlations...")
    corr = factor_correlations(panel, y_col="ret_mkt")
    chosen = choose_level_or_delta(corr)
    # Weight estimation uses main factors only; QoQ stays in corr for validation
    weight_factors = main_factors_only(chosen)
    ortho = partial_spearman_vs_y(panel, weight_factors, y_col="ret_mkt")
    weights = propose_weights(ortho)
    # quantile robustness column
    if not weights.empty:
        weights["q_response"] = [
            quantile_response(panel, f, y_col="ret_mkt") for f in weights["factor"]
        ]
    yearly = yearly_stability(panel, weight_factors, y_col="ret_mkt")

    # YoY vs QoQ quick compare
    yoy_qoq = corr[corr["factor"].isin(
        ["eps_yoy", "eps_dyoy", "sales_yoy", "sales_dyoy", "eps_qoq", "eps_dqoq", "sales_qoq", "sales_dqoq"]
    )].copy()

    paths_out = save_study_outputs(
        out_dir=out_dir,
        panel=panel,
        corr=corr,
        chosen=chosen,
        ortho=ortho,
        weights=weights,
        yearly=yearly,
        stamp=stamp,
    )
    yoy_path = out_dir / f"yoy_vs_qoq_{stamp}.csv"
    yoy_qoq.to_csv(yoy_path, index=False)

    print("\n=== Spearman (raw) ===")
    if not corr.empty:
        print(corr.sort_values("spearman", ascending=False).to_string(index=False))
    print("\n=== Proposed weights (ortho, max(0,corr)) ===")
    if not weights.empty:
        print(weights[["factor", "n", "spearman_ortho", "weight", "reverse_candidate", "q_response"]].to_string(index=False))
    print("\nOutputs:")
    for k, p in paths_out.items():
        print(f"  {k}: {p}")
    print(f"  yoy_vs_qoq: {yoy_path}")
    print("\nNOTE: weights are research proposals — not applied to sepa.fund until approved.")
    return {
        "ok": True,
        "stamp": stamp,
        "n_universe": len(universe_df),
        "n_tickers": len(tickers),
        "n_events": len(panel),
        "weights": weights,
        "paths": paths_out,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SEPA fund weight empirical study")
    p.add_argument("--config", default="config/params.yaml")
    p.add_argument("--pilot", type=int, default=50, help="Use first N universe names by mcap (0=all)")
    p.add_argument("--full", action="store_true", help="Run full universe (ignores --pilot)")
    p.add_argument("--refresh-universe", action="store_true")
    p.add_argument("--refresh-fundamentals", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    pilot = None if args.full or args.pilot == 0 else args.pilot
    result = run_study(
        config=args.config,
        pilot=pilot,
        refresh_universe=args.refresh_universe,
        refresh_fundamentals=args.refresh_fundamentals,
    )
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
