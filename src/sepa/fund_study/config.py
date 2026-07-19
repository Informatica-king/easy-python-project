"""Fund weight study — locked constants (docs/fund_weight_study_spec.md)."""

from __future__ import annotations

from dataclasses import dataclass

MIN_MARKET_CAP = 1_000_000_000.0  # $1B
MIN_ADV = 5_000_000.0  # $5M / day
ADV_LOOKBACK_DAYS = 60
STUDY_YEARS = 10

# Return window: close(day0-1) -> close(day0+3)
RET_PRE_OFFSET = 1   # trading days before day0
RET_POST_OFFSET = 3  # trading days after day0

EVENT_DOLLAR_VOL_WINDOW = 3  # ±3 trading days around event
EVENT_DOLLAR_VOL_BOTTOM_PCT = 0.30  # drop bottom 30%

# Explosive growth filter: |yoy| or |qoq| above this → drop
EXPLOSION_ABS_MAX = 5.0  # 500%

BENCHMARK = "^IXIC"

MAIN_FACTORS = (
    "eps_yoy",
    "eps_dyoy",
    "sales_yoy",
    "sales_dyoy",
    "npm_d",
    "opm_d",
    "eps_surprise",
    "sales_surprise",
)

SPEED_FACTORS = (
    "eps_qoq",
    "eps_dqoq",
    "sales_qoq",
    "sales_dqoq",
)

LEVEL_FACTORS = ("eps_yoy", "sales_yoy", "eps_qoq", "sales_qoq")
DELTA_FACTORS = ("eps_dyoy", "sales_dyoy", "npm_d", "opm_d", "eps_dqoq", "sales_dqoq")


@dataclass(frozen=True)
class StudyPaths:
    report_dir: str = "reports/fund_study"
    cache_universe: str = "data/fund_study/universe.parquet"
    cache_events: str = "data/fund_study/events"
