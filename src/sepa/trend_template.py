"""Minervini Trend Template: 8 conditions identifying a Stage 2 uptrend.

See docs/strategy_spec.md §3. Input frame must already carry the columns
produced by sepa.indicators.add_indicators.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from sepa.config import TrendTemplateParams


@dataclass
class TrendTemplateResult:
    passed: bool
    conditions: dict[str, bool] = field(default_factory=dict)


def evaluate(
    df: pd.DataFrame,
    tp: TrendTemplateParams,
    rs_rank: float | None = None,
) -> TrendTemplateResult:
    """Evaluate the 8 Trend Template conditions on the last row of df."""
    last = df.iloc[-1]
    close = last["close"]
    sma_s = last[f"sma{tp.sma_short}"]
    sma_m = last[f"sma{tp.sma_mid}"]
    sma_l = last[f"sma{tp.sma_long}"]

    sma_long_col = df[f"sma{tp.sma_long}"]
    if len(sma_long_col.dropna()) > tp.trend_days:
        sma_long_past = sma_long_col.iloc[-1 - tp.trend_days]
        long_ma_rising = bool(sma_l > sma_long_past)
    else:
        long_ma_rising = False

    conds = {
        "1_above_mid_long_ma": bool(close > sma_m and close > sma_l),
        "2_mid_above_long": bool(sma_m > sma_l),
        "3_long_ma_rising": long_ma_rising,
        "4_ma_stack": bool(sma_s > sma_m > sma_l),
        "5_above_short_ma": bool(close > sma_s),
        "6_above_52w_low": bool(close >= last["low_52w"] * (1 + tp.low_52w_min_pct)),
        "7_near_52w_high": bool(close >= last["high_52w"] * (1 - tp.high_52w_max_pct)),
    }
    if tp.rs_enabled:
        conds["8_rs_rank"] = bool(rs_rank is not None and rs_rank >= tp.rs_rank_min)

    # NaN in any referenced indicator (short history) fails the template.
    if pd.isna([close, sma_s, sma_m, sma_l, last["low_52w"], last["high_52w"]]).any():
        return TrendTemplateResult(passed=False, conditions={k: False for k in conds})

    return TrendTemplateResult(passed=all(conds.values()), conditions=conds)
