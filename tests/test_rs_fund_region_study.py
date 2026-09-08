"""Tests for RS×Fund region return helpers."""

from __future__ import annotations

import pandas as pd

from sepa.rs_fund_region_study import (
    assign_r1,
    assign_r4_live,
    trailing_return,
    forward_return,
)


def test_trailing_and_forward_returns():
    idx = pd.bdate_range("2026-01-02", periods=30)
    s = pd.Series(range(1, 31), index=idx, dtype=float)  # +1 per day
    as_of = idx[20]
    # 5 bars back: price 16 → 21 => 21/16 - 1
    tr = trailing_return(s, as_of, 5)
    assert tr is not None
    assert abs(tr - (21 / 16 - 1)) < 1e-9
    fr = forward_return(s, as_of, 5)
    assert fr is not None
    assert abs(fr - (26 / 21 - 1)) < 1e-9


def test_assign_r1_and_r4():
    df = pd.DataFrame({
        "ticker": ["A", "B", "C", "D"],
        "rs_rank": [65, 75, 85, 95],
        "fund_score": [20, 40, 60, 30],
    })
    r1 = assign_r1(df)
    assert str(r1.loc[0, "rs_bin"]) == "RS0–69"
    assert "F25–49" in str(r1.loc[1, "fund_bin"])
    r4 = assign_r4_live(df, fund_median=40)
    assert r4.loc[1, "r4_band"] == "RS70–89"
    assert r4.loc[3, "r4_band"] == "RS90+ & Fund<med (soft-drop)"
