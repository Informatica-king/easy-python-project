"""Configuration loading for the SEPA screener.

Parameter semantics are documented in docs/strategy_spec.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class DataParams:
    lookback_years: int = 3
    cache_dir: str = "data/raw"
    min_history_days: int = 280


@dataclass(frozen=True)
class UniverseFilterParams:
    """Liquidity pre-filter applied before screening (full-universe runs)."""

    min_price: float = 10.0
    min_avg_dollar_volume: float = 10_000_000.0  # 50-day average, USD


@dataclass(frozen=True)
class TrendTemplateParams:
    sma_short: int = 50
    sma_mid: int = 150
    sma_long: int = 200
    trend_days: int = 21
    low_52w_min_pct: float = 0.30
    high_52w_max_pct: float = 0.25
    rs_enabled: bool = True
    rs_rank_min: float = 70.0


@dataclass(frozen=True)
class VCPParams:
    base_min_weeks: int = 5
    base_max_weeks: int = 26
    max_base_depth: float = 0.35
    swing_threshold: float = 0.03
    # Phase-3: ZigZag mode — live default remains percent; "atr" is research option
    swing_mode: str = "pct"  # "pct" | "atr"
    atr_period: int = 14
    atr_multiplier: float = 1.5
    min_contractions: int = 2
    max_contractions: int = 6
    contraction_decay: float = 0.75
    contraction_min_retrace: float = 0.5
    final_contraction_max: float = 0.10
    # Phase-2 noise filters (tradermonty-style)
    min_contraction_days: int = 5  # each major contraction leg must span ≥ N bars
    t1_depth_min: float = 0.08  # first contraction depth must be ≥ 8%
    dryup_days: int = 5
    dryup_ratio: float = 0.6
    pivot_buffer: float = 0.001
    breakout_vol_mult: float = 1.5
    watch_zone_pct: float = 0.05
    max_extension: float = 0.05


@dataclass(frozen=True)
class FundamentalParams:
    """Quantitative fundamental score weights (docs/fundamental_spec.md).

    Empirical reweight (2026-07-19): S47 / E25 / D14 / B14 (sum 100).
    Level YoY and ROE dropped from phase-1 live scorer.

    v2.1 quality layer (docs/fund_score_improvement_plan.md): weights fixed;
    npm_quality / accel_* gate unreliable factors instead of reweighting.
    """

    rs_min: float = 70.0
    # Soft ceiling: RS >= rs_soft_max kept only if fund >= median (when enabled).
    # 0 disables the soft ceiling. Hard exclusion of high-RS leaders is intentional-off.
    rs_soft_max: float = 90.0
    rs_high_requires_fund_median: bool = True
    eps_surprise: float = 47.0
    eps_dyoy: float = 14.0
    sales_dyoy: float = 14.0
    opm_delta: float = 25.0
    # unused by scorer; kept so old YAML keys do not crash load_params
    eps_yoy: float = 0.0
    eps_accel: float = 0.0
    sales_yoy: float = 0.0
    sales_accel: float = 0.0
    margin_improve: float = 0.0
    roe: float = 0.0
    roe_target: float = 0.17
    # v2.1 quality
    quality_enabled: bool = True
    npm_quality: float = 0.6
    accel_min_n: int = 2
    accel_full_n: int = 3
    accel_partial: float = 0.7
    surprise_winsor: float = 1.0
    # optional daily filter (Phase C)
    fund_quality_min: float = 0.0  # min mean(b,d,e quality); 0 = off


@dataclass(frozen=True)
class Params:
    data: DataParams
    trend_template: TrendTemplateParams
    vcp: VCPParams
    universe_filter: UniverseFilterParams = UniverseFilterParams()
    fundamental: FundamentalParams = FundamentalParams()
    report_dir: str = "reports"


def load_params(path: str | Path) -> Params:
    raw = yaml.safe_load(Path(path).read_text())
    return Params(
        data=DataParams(**raw.get("data", {})),
        trend_template=TrendTemplateParams(**raw.get("trend_template", {})),
        vcp=VCPParams(**raw.get("vcp", {})),
        universe_filter=UniverseFilterParams(**raw.get("universe_filter", {})),
        fundamental=FundamentalParams(**raw.get("fundamental", {})),
        report_dir=raw.get("report", {}).get("output_dir", "reports"),
    )


def load_universe(path: str | Path) -> list[str]:
    raw = yaml.safe_load(Path(path).read_text())
    tickers = raw["tickers"]
    if not isinstance(tickers, list) or not tickers:
        raise ValueError(f"universe file {path} must contain a non-empty 'tickers' list")
    return [str(t).strip().upper() for t in tickers]
