"""Tests for RS threshold study helpers."""

from __future__ import annotations

import pandas as pd

from sepa.rs_threshold_study import compare_adjacent, jaccard, slice_at_threshold


def test_jaccard_and_adjacent():
    assert jaccard({"A", "B"}, {"A", "B"}) == 1.0
    assert jaccard({"A"}, {"B"}) == 0.0
    slices = [
        {"rs_min": 70, "fund_tickers": {"A", "B", "C"}},
        {"rs_min": 80, "fund_tickers": {"A", "B"}},
    ]
    adj = compare_adjacent(slices, "fund_tickers")
    assert len(adj) == 1
    assert adj.iloc[0]["band"] == "70→80"
    assert adj.iloc[0]["removed_n"] == 1
    assert adj.iloc[0]["removed"] == "C"


def test_slice_at_threshold_applies_filters():
    scored = pd.DataFrame({
        "ticker": ["AAA", "BBB", "CCC", "DDD"],
        "rs_rank": [85, 75, 90, 82],
        "fund_score": [40.0, 50.0, 0.0, 30.0],
        "market_cap": [2e9, 2e9, 2e9, 5e8],  # DDD too small
    })
    sl = slice_at_threshold(scored, 80)
    assert sl["n_stage2"] == 3  # AAA, CCC, DDD
    assert sl["fund_tickers"] == {"AAA"}  # CCC fund0, DDD mcap
    assert "BBB" not in sl["stage2_tickers"]
