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
    rs_rank_min: float = 80.0


@dataclass(frozen=True)
class VCPParams:
    base_min_weeks: int = 5
    base_max_weeks: int = 26
    max_base_depth: float = 0.35
    swing_threshold: float = 0.03
    min_contractions: int = 2
    max_contractions: int = 6
    contraction_decay: float = 0.75
    contraction_min_retrace: float = 0.5
    final_contraction_max: float = 0.10
    dryup_days: int = 5
    dryup_ratio: float = 0.6
    pivot_buffer: float = 0.001
    breakout_vol_mult: float = 1.5
    watch_zone_pct: float = 0.05
    max_extension: float = 0.05


@dataclass(frozen=True)
class FundamentalParams:
    """Quantitative fundamental score weights (docs/fundamental_spec.md).

    Sum of weights is 90; displayed fund_score = raw/90*100.
    Annual EPS component (F) intentionally omitted — quarterly focus only.
    """

    rs_min: float = 80.0
    eps_yoy: float = 25.0
    eps_accel: float = 20.0
    sales_yoy: float = 15.0
    sales_accel: float = 10.0
    margin_improve: float = 15.0
    roe: float = 5.0
    roe_target: float = 0.17


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
