"""Tests for candidate exclusion filters."""

import pandas as pd

from sepa.candidates import MIN_MARKET_CAP_USD, apply_candidate_filters


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
