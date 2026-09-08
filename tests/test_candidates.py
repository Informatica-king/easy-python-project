"""Tests for candidate exclusion filters."""

import pandas as pd

from sepa.candidates import (
    MIN_MARKET_CAP_USD,
    apply_candidate_filters,
    apply_rs_soft_ceiling,
)


def test_drops_zero_fund_and_sub_1b():
    df = pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D", "E"],
            "fund_score": [50, 0, 40, 30, 55],
            "market_cap": [2e9, 5e9, 5e8, None, 1e9],
        }
    )
    kept, dropped = apply_candidate_filters(df)
    assert set(kept["ticker"]) == {"A", "E"}  # C small, B zero, D missing mcap
    assert len(dropped) == 3
    assert MIN_MARKET_CAP_USD == 1_000_000_000.0


def test_keeps_exactly_1b_with_positive_fund():
    df = pd.DataFrame(
        {"ticker": ["X"], "fund_score": [0.1], "market_cap": [1_000_000_000]}
    )
    kept, dropped = apply_candidate_filters(df)
    assert list(kept["ticker"]) == ["X"]
    assert dropped.empty


def test_rs_soft_ceiling_keeps_strong_high_rs_only():
    # median fund = 40; RS≥90 needs fund≥40
    df = pd.DataFrame(
        {
            "ticker": ["LOW", "MID", "HI_WEAK", "HI_STRONG"],
            "rs_rank": [75, 85, 92, 95],
            "fund_score": [30.0, 50.0, 20.0, 55.0],
        }
    )
    kept, dropped, med = apply_rs_soft_ceiling(df, rs_soft_max=90.0)
    assert med == 40.0
    assert set(kept["ticker"]) == {"LOW", "MID", "HI_STRONG"}
    assert list(dropped["ticker"]) == ["HI_WEAK"]


def test_rs_soft_ceiling_disabled():
    df = pd.DataFrame({"ticker": ["A"], "rs_rank": [99], "fund_score": [1.0]})
    kept, dropped, med = apply_rs_soft_ceiling(df, rs_soft_max=90.0, enabled=False)
    assert len(kept) == 1 and dropped.empty
    kept2, dropped2, _ = apply_rs_soft_ceiling(df, rs_soft_max=0)
    assert len(kept2) == 1 and dropped2.empty
