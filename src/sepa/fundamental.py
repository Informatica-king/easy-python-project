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
from sepa.candidates import (
    apply_candidate_filters,
    apply_rs_soft_ceiling,
    summarize_drops,
)
from sepa.config import Params, load_params, load_universe
from sepa.data import fundamentals as fund_data
from sepa.data import store, universe
from sepa.fundamental_score import (
    DEFAULT_QUALITY,
    DEFAULT_WEIGHTS,
    FundamentalWeights,
    QualityParams,
    score_ticker,
)

logger = logging.getLogger(__name__)


def _weights_from_params(params: Params) -> FundamentalWeights:
    w = params.fundamental
    return FundamentalWeights(
        eps_surprise=w.eps_surprise,
        eps_dyoy=w.eps_dyoy,
        sales_dyoy=w.sales_dyoy,
        opm_delta=w.opm_delta,
    )


def _quality_from_params(params: Params) -> QualityParams:
    w = params.fundamental
    return QualityParams(
        enabled=bool(getattr(w, "quality_enabled", True)),
        npm_quality=float(getattr(w, "npm_quality", DEFAULT_QUALITY.npm_quality)),
        accel_min_n=int(getattr(w, "accel_min_n", DEFAULT_QUALITY.accel_min_n)),
        accel_full_n=int(getattr(w, "accel_full_n", DEFAULT_QUALITY.accel_full_n)),
        accel_partial=float(getattr(w, "accel_partial", DEFAULT_QUALITY.accel_partial)),
        surprise_winsor=float(getattr(w, "surprise_winsor", DEFAULT_QUALITY.surprise_winsor)),
    )


def fetch_latest_eps_surprise(ticker: str) -> float | None:
    """Best-effort latest reported EPS surprise as a fraction (0.05 = +5%)."""
    from pathlib import Path

    # Prefer fund-study earnings table cache when present
    sur_path = Path("data/fund_study/earnings_dates") / f"{ticker.upper()}_table.parquet"
    ed = None
    if sur_path.exists():
        try:
            ed = pd.read_parquet(sur_path)
        except Exception:  # noqa: BLE001
            ed = None
    if ed is None:
        try:
            import yfinance as yf

            ed = yf.Ticker(ticker).get_earnings_dates(limit=12)
        except Exception as exc:  # noqa: BLE001
            logger.debug("earnings surprise fetch failed %s: %s", ticker, exc)
            return None
    if ed is None or ed.empty:
        return None
    cols = {c.lower().replace(" ", "_"): c for c in ed.columns}
    est_c = cols.get("eps_estimate") or cols.get("estimate")
    act_c = cols.get("reported_eps") or cols.get("actual")
    sur_c = cols.get("surprise(%)") or cols.get("surprise%") or cols.get("surprise")
    work = ed.copy()
    work.index = pd.to_datetime(work.index)
    if getattr(work.index, "tz", None) is not None:
        work.index = work.index.tz_localize(None)
    work = work.sort_index(ascending=False)
    for _, row in work.iterrows():
        if sur_c and pd.notna(row.get(sur_c)):
            try:
                val = float(row.get(sur_c))
                # Yahoo Surprise(%) is typically in percent units (e.g. 5.8)
                return val / 100.0 if abs(val) > 2 else val
            except Exception:  # noqa: BLE001
                pass
        if est_c and act_c and pd.notna(row.get(est_c)) and pd.notna(row.get(act_c)):
            est = float(row.get(est_c))
            act = float(row.get(act_c))
            if est != 0:
                return act / est - 1.0
    return None


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


def apply_fund_quality_filter(
    df: pd.DataFrame,
    *,
    min_quality: float,
) -> tuple[pd.DataFrame, int]:
    """Phase C: drop rows whose mean(b,d,e quality) < min_quality. Returns (kept, n_dropped)."""
    if df is None or df.empty or min_quality <= 0:
        return df, 0
    work = df.copy()
    cols = [c for c in ("b_quality", "d_quality", "e_quality") if c in work.columns]
    if not cols:
        return work, 0
    qmean = work[cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    keep = qmean >= float(min_quality)
    return work.loc[keep].reset_index(drop=True), int((~keep).sum())


def score_universe(
    candidates: pd.DataFrame,
    params: Params,
    *,
    refresh: bool = False,
    compare_legacy: bool = False,
) -> pd.DataFrame:
    fund_dir = fund_data.cache_dir(params.data.cache_dir)
    cik_map = fund_data.load_cik_map(fund_dir)
    weights = _weights_from_params(params)
    quality = _quality_from_params(params)
    legacy_q = QualityParams(enabled=False)

    rows = []
    n = len(candidates)
    for i, row in enumerate(candidates.itertuples(index=False), start=1):
        ticker = str(row.ticker).upper()
        if i == 1 or i % 10 == 0 or i == n:
            logger.info("fundamentals %d/%d %s", i, n, ticker)
        quarterly, roe, source = fund_data.load_quarterly(
            ticker, fund_dir, cik_map, refresh=refresh
        )
        surprise = fetch_latest_eps_surprise(ticker)
        br = score_ticker(
            ticker,
            quarterly,
            roe,
            source=source,
            weights=weights,
            roe_target=params.fundamental.roe_target,
            eps_surprise=surprise,
            quality=quality,
        )
        d = br.as_dict()
        if compare_legacy:
            legacy = score_ticker(
                ticker,
                quarterly,
                roe,
                source=source,
                weights=weights,
                roe_target=params.fundamental.roe_target,
                eps_surprise=surprise,
                quality=legacy_q,
            )
            d["fund_score_v2"] = round(legacy.fund_score, 1)
            d["fund_score_delta"] = round(br.fund_score - legacy.fund_score, 1)
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
        help="screen full Nasdaq then score RS≥rs_min Stage 2 names",
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
    parser.add_argument(
        "--compare-legacy",
        action="store_true",
        help="also score with quality layer off; write fund_score_v2 / delta columns",
    )
    parser.add_argument(
        "--audit-opm",
        action="store_true",
        help="print OPM coverage for candidates then exit (no full score)",
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

    if args.audit_opm:
        fund_dir = fund_data.cache_dir(params.data.cache_dir)
        cik_map = fund_data.load_cik_map(fund_dir)
        cov = fund_data.audit_opm_coverage(
            candidates["ticker"].astype(str).tolist(), fund_dir, cik_map
        )
        stamp = (args.as_of or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
        out = Path(params.report_dir) / f"opm_coverage_{stamp}.csv"
        Path(params.report_dir).mkdir(parents=True, exist_ok=True)
        cov.to_csv(out, index=False)
        ok = int(cov["opm_ok"].sum()) if "opm_ok" in cov.columns else 0
        print(f"OPM coverage: {ok}/{len(cov)} tickers with opm_n≥2")
        print(f"report: {out}")
        return 0

    scored = score_universe(
        candidates,
        params,
        refresh=args.refresh_fundamentals,
        compare_legacy=bool(args.compare_legacy),
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
        soft_max = float(getattr(params.fundamental, "rs_soft_max", 0.0) or 0.0)
        soft_on = bool(getattr(params.fundamental, "rs_high_requires_fund_median", True))
        if soft_max > 0 and soft_on and not scored.empty:
            before_soft = len(scored)
            scored, soft_dropped, med = apply_rs_soft_ceiling(
                scored, rs_soft_max=soft_max, enabled=True
            )
            tickers = (
                ",".join(soft_dropped["ticker"].astype(str).str.upper().tolist())
                if not soft_dropped.empty else ""
            )
            print(
                f"RS soft ceiling: RS≥{soft_max:.0f} 은 Fund≥중앙값({med:.1f})만 유지  "
                f"{before_soft} → {len(scored)}"
                + (f"  탈락: {tickers}" if tickers else "  (탈락 0)")
            )
        qmin = float(getattr(params.fundamental, "fund_quality_min", 0.0) or 0.0)
        if qmin > 0:
            scored, qdrop = apply_fund_quality_filter(scored, min_quality=qmin)
            print(f"quality 필터 (mean b/d/e ≥ {qmin}): 추가 제외 {qdrop} → n={len(scored)}")

    stamp = (args.as_of or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
    out_dir = Path(params.report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"fundamental_{stamp}.csv"
    scored.to_csv(out_path, index=False)

    if args.compare_legacy and not scored.empty and "fund_score_v2" in scored.columns:
        cmp_path = out_dir / f"fundamental_v21_compare_{stamp}.csv"
        cols = [
            c for c in (
                "ticker", "name", "fund_score", "fund_score_v2", "fund_score_delta",
                "margin_source", "e_quality", "b_quality", "d_quality",
                "eps_accel_n", "sales_accel_n",
            ) if c in scored.columns
        ]
        scored[cols].to_csv(cmp_path, index=False)
        print(f"v2 vs v2.1 compare: {cmp_path}")

    soft_max = float(getattr(params.fundamental, "rs_soft_max", 0.0) or 0.0)
    soft_on = bool(getattr(params.fundamental, "rs_high_requires_fund_median", True))
    rs_note = f"RS≥{rs_min:.0f}"
    if soft_max > 0 and soft_on:
        rs_note += f" · RS≥{soft_max:.0f}→Fund≥중앙값"
    print(
        f"\n=== SEPA Fundamental scores "
        f"(Stage 2 · {rs_note} · 후보필터 적용, n={len(scored)}) "
        f"— fund_score desc ===\n"
    )
    print_fundamental_list(scored)
    print(f"\nreport: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
