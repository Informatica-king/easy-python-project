"""Composite Success Score (CSS) — D34 Phase A2.

Scores as-of forward baskets on S1–S8 (equal to approved A0 weights).
Fund formula is NOT modified. ECG comparison is Phase A3.

CSS factors (weights sum 100):
  S1 EW excess 20 · S2 Median excess 20 · S3 Win rate 15 · S4 Tail penalty 15
  S5 3M/6M stability 10 · S6 P10 downside 10 · S7 Turnover 5 · S8 Sector conc. 5

Primary comparison unit: one rule/basket across the as-of grid (not a single day).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from sepa.analyze import enrich_with_sectors, fund_median_threshold
from sepa.asof_forward_bt import (
    PERIODS,
    _load_calendar,
    ensure_asof_fundamental,
    evaluate_asof,
    load_benches,
    select_asofs,
)
from sepa.candidates import apply_candidate_filters
from sepa.config import load_params
from sepa.sepatop import load_price_panel

logger = logging.getLogger(__name__)

W_S1 = 20.0
W_S2 = 20.0
W_S3 = 15.0
W_S4 = 15.0
W_S5 = 10.0
W_S6 = 10.0
W_S7 = 5.0
W_S8 = 5.0

# Period blend for S1/S2/S3/S4/S6 (longer horizons weigh more)
PERIOD_W = {"1M": 0.10, "3M": 0.20, "6M": 0.30, "1Y": 0.40}

SAMPLE_GATE_MIN_ASOF = 10

RULE_SEPATOP = "sepaTop"
RULE_MEDIAN_PLUS = "median_plus"


def clamp01(x: float) -> float:
    if x != x:  # NaN
        return float("nan")
    return float(max(0.0, min(100.0, x)))


def map_excess_to_score(excess: float, lo: float = -0.15, hi: float = 0.15) -> float:
    """Map excess return (fraction) to 0–100; 0 excess → 50."""
    if excess is None or (isinstance(excess, float) and np.isnan(excess)):
        return float("nan")
    if hi <= lo:
        return 50.0
    t = (float(excess) - lo) / (hi - lo)
    return clamp01(t * 100.0)


def map_p10_to_score(p10: float, lo: float = -0.50, hi: float = 0.05) -> float:
    """Higher (less negative) P10 → higher score."""
    if p10 is None or (isinstance(p10, float) and np.isnan(p10)):
        return float("nan")
    if hi <= lo:
        return 50.0
    t = (float(p10) - lo) / (hi - lo)
    return clamp01(t * 100.0)


def map_tail_gap_to_score(gap: float, soft: float = 0.05, hard: float = 0.25) -> float:
    """|mean−median| gap: 0 → 100, soft → 70, hard+ → 0."""
    if gap is None or (isinstance(gap, float) and np.isnan(gap)):
        return float("nan")
    g = abs(float(gap))
    if g <= soft:
        # 0 → 100, soft → 70
        return clamp01(100.0 - (g / soft) * 30.0) if soft > 0 else 100.0
    if g >= hard:
        return 0.0
    # soft → 70, hard → 0
    return clamp01(70.0 * (1.0 - (g - soft) / (hard - soft)))


def _period_weight(period: str) -> float:
    return float(PERIOD_W.get(str(period), 0.0))


def _weighted_nanmean(values: list[float], weights: list[float]) -> float:
    pairs = [(v, w) for v, w in zip(values, weights) if v == v and w > 0]
    if not pairs:
        return float("nan")
    num = sum(v * w for v, w in pairs)
    den = sum(w for _, w in pairs)
    return float(num / den) if den else float("nan")


def summarize_forward_grid(summary: pd.DataFrame) -> dict[str, float]:
    """Collapse as-of×period forward rows into factor inputs."""
    if summary is None or summary.empty:
        return {}
    df = summary.copy()
    out: dict[str, float] = {"n_asof": float(df["as_of"].nunique())}

    for period, _ in PERIODS:
        sub = df[df["period"] == period]
        if sub.empty:
            continue
        out[f"{period}_n"] = float(len(sub))
        out[f"{period}_excess_ew_spx"] = float(sub["excess_ew_spx"].mean())
        out[f"{period}_excess_med_spx"] = float(sub["excess_med_spx"].mean())
        out[f"{period}_excess_ew_qqq"] = float(sub["excess_ew_qqq"].mean())
        out[f"{period}_excess_med_qqq"] = float(sub["excess_med_qqq"].mean())
        out[f"{period}_win_ew_spx"] = float((sub["mean_ew"] > sub["spx"]).mean())
        out[f"{period}_win_med_spx"] = float((sub["median"] > sub["spx"]).mean())
        out[f"{period}_win_ew_qqq"] = float((sub["mean_ew"] > sub["qqq"]).mean())
        out[f"{period}_tail_gap"] = float((sub["mean_ew"] - sub["median"]).abs().mean())
        out[f"{period}_p10"] = float(sub["p10"].mean())
        if "p90" in sub.columns:
            out[f"{period}_p90_p50"] = float((sub["p90"] - sub["median"]).mean())
    return out


def score_s1_ew_excess(grid: dict[str, float]) -> float:
    vals, ws = [], []
    for period in PERIOD_W:
        for key in (f"{period}_excess_ew_spx", f"{period}_excess_ew_qqq"):
            if key in grid:
                vals.append(map_excess_to_score(grid[key]))
                ws.append(_period_weight(period))
    return _weighted_nanmean(vals, ws)


def score_s2_median_excess(grid: dict[str, float]) -> float:
    vals, ws = [], []
    for period in PERIOD_W:
        for key in (f"{period}_excess_med_spx", f"{period}_excess_med_qqq"):
            if key in grid:
                vals.append(map_excess_to_score(grid[key]))
                ws.append(_period_weight(period))
    return _weighted_nanmean(vals, ws)


def score_s3_win_rate(grid: dict[str, float]) -> float:
    vals, ws = [], []
    for period in PERIOD_W:
        for key in (f"{period}_win_ew_spx", f"{period}_win_med_spx", f"{period}_win_ew_qqq"):
            if key in grid and grid[key] == grid[key]:
                vals.append(clamp01(float(grid[key]) * 100.0))
                ws.append(_period_weight(period))
    return _weighted_nanmean(vals, ws)


def score_s4_tail_penalty(grid: dict[str, float]) -> float:
    vals, ws = [], []
    for period in PERIOD_W:
        key = f"{period}_tail_gap"
        if key in grid:
            vals.append(map_tail_gap_to_score(grid[key]))
            ws.append(_period_weight(period))
    return _weighted_nanmean(vals, ws)


def score_s5_stability(grid: dict[str, float]) -> float:
    """3M/6M EW−SPX should not collapse vs 1Y picture."""
    e3 = grid.get("3M_excess_ew_spx", float("nan"))
    e6 = grid.get("6M_excess_ew_spx", float("nan"))
    e1y = grid.get("1Y_excess_ew_spx", float("nan"))
    parts = []
    if e3 == e3:
        parts.append(map_excess_to_score(e3))
    if e6 == e6:
        parts.append(map_excess_to_score(e6))
    if not parts:
        return float("nan")
    base = float(np.mean(parts))
    # mild bonus if 3M/6M not far below 1Y when 1Y is strong
    if e1y == e1y and e1y > 0:
        lag = []
        if e3 == e3:
            lag.append(e3 - e1y)
        if e6 == e6:
            lag.append(e6 - e1y)
        if lag:
            # lag of 0 → +5, lag of -0.20 → 0
            adj = float(np.mean([clamp01(50 + 50 * (1 + min(0.0, x) / 0.20)) - 50 for x in lag]))
            base = clamp01(base + adj * 0.2)
    return clamp01(base)


def score_s6_downside(grid: dict[str, float]) -> float:
    vals, ws = [], []
    for period in PERIOD_W:
        key = f"{period}_p10"
        if key in grid:
            vals.append(map_p10_to_score(grid[key]))
            ws.append(_period_weight(period))
    return _weighted_nanmean(vals, ws)


def score_s7_turnover(memberships: list[set[str]]) -> float:
    """Low average turnover → high score. turnover = 1 − Jaccard."""
    if len(memberships) < 2:
        return float("nan")
    turns = []
    for a, b in zip(memberships, memberships[1:]):
        if not a and not b:
            continue
        union = a | b
        inter = a & b
        jacc = len(inter) / len(union) if union else 1.0
        turns.append(1.0 - jacc)
    if not turns:
        return float("nan")
    avg_turn = float(np.mean(turns))
    # 0 turn → 100, 0.5 → 50, ≥1 → 0
    return clamp01(100.0 * (1.0 - avg_turn))


def score_s8_sector_concentration(sector_shares: list[float]) -> float:
    """Penalize top-sector share above ~35%."""
    if not sector_shares:
        return float("nan")
    top = float(np.mean(sector_shares))
    if top <= 0.35:
        return 100.0
    if top >= 0.70:
        return 0.0
    return clamp01(100.0 * (1.0 - (top - 0.35) / 0.35))


def compute_css(
    *,
    grid: dict[str, float],
    memberships: list[set[str]] | None = None,
    sector_top_shares: list[float] | None = None,
) -> dict[str, float | str | bool]:
    """Return factor scores + weighted CSS + sample gate flag."""
    s1 = score_s1_ew_excess(grid)
    s2 = score_s2_median_excess(grid)
    s3 = score_s3_win_rate(grid)
    s4 = score_s4_tail_penalty(grid)
    s5 = score_s5_stability(grid)
    s6 = score_s6_downside(grid)
    s7 = score_s7_turnover(memberships or [])
    s8 = score_s8_sector_concentration(sector_top_shares or [])

    parts = [
        (s1, W_S1),
        (s2, W_S2),
        (s3, W_S3),
        (s4, W_S4),
        (s5, W_S5),
        (s6, W_S6),
        (s7, W_S7),
        (s8, W_S8),
    ]
    present = [(v, w) for v, w in parts if v == v]
    if not present:
        css = float("nan")
    else:
        # renormalize if S7/S8 missing
        css = sum(v * w for v, w in present) / sum(w for _, w in present)

    n_asof = int(grid.get("n_asof", 0) or 0)
    thin = n_asof < SAMPLE_GATE_MIN_ASOF
    return {
        "n_asof": n_asof,
        "sample_thin": thin,
        "sample_note": "자료 부족" if thin else "ok",
        "S1_ew_excess": s1,
        "S2_median_excess": s2,
        "S3_win_rate": s3,
        "S4_tail_penalty": s4,
        "S5_stability": s5,
        "S6_downside": s6,
        "S7_turnover": s7,
        "S8_sector": s8,
        "CSS": float(css) if css == css else float("nan"),
        "W_S1": W_S1,
        "W_S2": W_S2,
        "W_S3": W_S3,
        "W_S4": W_S4,
        "W_S5": W_S5,
        "W_S6": W_S6,
        "W_S7": W_S7,
        "W_S8": W_S8,
        **{k: v for k, v in grid.items() if k.startswith(("1M_", "3M_", "6M_", "1Y_"))},
    }


def basket_sepa_top(fund: pd.DataFrame) -> pd.DataFrame:
    """sepaTop = candidate-filtered fund pool (Fund>0, mcap≥$1B). Soft already in CSV."""
    kept, _ = apply_candidate_filters(fund)
    return kept.reset_index(drop=True)


def basket_median_plus(fund: pd.DataFrame) -> pd.DataFrame:
    pool, _ = apply_candidate_filters(fund)
    if pool.empty:
        return pool
    med = fund_median_threshold(pool)
    fund_s = pd.to_numeric(pool["fund_score"], errors="coerce")
    return pool.loc[fund_s >= med].reset_index(drop=True)


BASKET_BUILDERS = {
    RULE_SEPATOP: basket_sepa_top,
    RULE_MEDIAN_PLUS: basket_median_plus,
}


def _top_sector_share(cons: pd.DataFrame) -> float:
    if cons.empty or "sector" not in cons.columns:
        return float("nan")
    sec = cons["sector"].fillna("Unknown").astype(str)
    if sec.empty:
        return float("nan")
    return float(sec.value_counts(normalize=True).iloc[0])


def evaluate_rule_grid(
    asofs: list[pd.Timestamp],
    *,
    rule: str,
    config: str,
    report_dir: Path,
    cache_dir: Path,
    skip_existing: bool,
    lookback_years: int,
) -> tuple[pd.DataFrame, list[set[str]], list[float]]:
    """Build forward summary + membership sets + top-sector shares for one rule."""
    builder = BASKET_BUILDERS[rule]
    benches = load_benches(asofs[0], asofs[-1] + pd.DateOffset(years=1))
    all_rows: list[dict] = []
    memberships: list[set[str]] = []
    sector_shares: list[float] = []

    for as_of in asofs:
        iso = as_of.date().isoformat()
        fund_path = ensure_asof_fundamental(
            iso, config=config, report_dir=report_dir, skip_existing=skip_existing
        )
        if fund_path is None:
            logger.error("no fund for %s", iso)
            continue
        fund = pd.read_csv(fund_path)
        if "market_cap" not in fund.columns or pd.to_numeric(
            fund.get("market_cap"), errors="coerce"
        ).isna().all():
            fund = enrich_with_sectors(fund, cache_dir, refresh=False)
        cons = builder(fund)
        tickers = cons["ticker"].astype(str).str.upper().tolist()
        memberships.append(set(tickers))
        sector_shares.append(_top_sector_share(cons))
        print(f"  [{rule}] {iso} n={len(cons)}")
        if not tickers:
            continue
        panel = load_price_panel(tickers, cache_dir, lookback_years=lookback_years)
        rows = evaluate_asof(as_of, cons, panel, benches)
        for r in rows:
            r["rule"] = rule
        all_rows.extend(rows)

    return pd.DataFrame(all_rows), memberships, sector_shares


def run(
    *,
    config: str = "config/params.yaml",
    freq: str = "month",
    horizon: str = "1y",
    skip_existing: bool = True,
    rules: list[str] | None = None,
) -> pd.DataFrame:
    params = load_params(config)
    report_dir = Path(params.report_dir)
    cache_dir = Path(params.data.cache_dir)
    out_dir = report_dir / "asof_forward_bt"
    out_dir.mkdir(parents=True, exist_ok=True)

    cal = _load_calendar(cache_dir)
    asofs = select_asofs(
        cal,
        cache_dir,
        freq=freq,
        horizon=horizon,
        min_hist=int(params.data.min_history_days),
    )
    print(f"CSS as-of grid ({freq}, ≥{horizon}): {len(asofs)} dates")
    for d in asofs:
        print(f"  - {d.date()}")

    rules = rules or [RULE_SEPATOP, RULE_MEDIAN_PLUS]
    roll_rows: list[dict] = []
    detail_frames: list[pd.DataFrame] = []

    lookback = max(3, int(params.data.lookback_years))
    for rule in rules:
        print(f"\n======== CSS rule: {rule} ========")
        summary, memberships, sector_shares = evaluate_rule_grid(
            asofs,
            rule=rule,
            config=config,
            report_dir=report_dir,
            cache_dir=cache_dir,
            skip_existing=skip_existing,
            lookback_years=lookback,
        )
        if summary.empty:
            logger.error("empty summary for %s", rule)
            continue
        summary.to_csv(out_dir / f"forward_summary_{rule}.csv", index=False)
        detail_frames.append(summary)
        grid = summarize_forward_grid(summary)
        scored = compute_css(
            grid=grid,
            memberships=memberships,
            sector_top_shares=[s for s in sector_shares if s == s],
        )
        scored["rule"] = rule
        roll_rows.append(scored)

    roll = pd.DataFrame(roll_rows)
    roll_path = out_dir / "css_rollup.csv"
    roll.to_csv(roll_path, index=False)

    if detail_frames:
        pd.concat(detail_frames, ignore_index=True).to_csv(
            out_dir / "forward_summary_css_rules.csv", index=False
        )

    print("\n=== CSS ROLLUP ===")
    cols = [
        "rule",
        "n_asof",
        "sample_note",
        "CSS",
        "S1_ew_excess",
        "S2_median_excess",
        "S3_win_rate",
        "S4_tail_penalty",
        "S5_stability",
        "S6_downside",
        "S7_turnover",
        "S8_sector",
    ]
    show = [c for c in cols if c in roll.columns]
    if not roll.empty:
        print(roll[show].to_string(index=False))
    print(f"\nrollup: {roll_path}")
    return roll


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Composite Success Score (CSS) A2")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--freq", choices=["month", "week"], default="month")
    parser.add_argument("--horizon", choices=["1m", "3m", "6m", "1y"], default="1y")
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="rebuild stage2/fund even if CSV exists",
    )
    parser.add_argument(
        "--rules",
        default="sepaTop,median_plus",
        help="comma-separated rules: sepaTop,median_plus",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    rules = [x.strip() for x in args.rules.split(",") if x.strip()]
    run(
        config=args.config,
        freq=args.freq,
        horizon=args.horizon,
        skip_existing=not args.no_skip_existing,
        rules=rules,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
