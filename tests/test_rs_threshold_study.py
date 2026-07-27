"""Tests for RS threshold study helpers."""

from __future__ import annotations

import pandas as pd

from sepa.rs_threshold_study import (
    compare_adjacent,
    exclusive_rs_edges,
    fund_dist_cumulative,
    fund_dist_exclusive,
    fund_dist_removed_on_raise,
    fund_score_stats,
    jaccard,
    slice_at_threshold,
)


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


def test_fund_score_stats_and_exclusive_edges():
    stats = fund_score_stats(pd.Series([10.0, 20.0, 30.0, 40.0, 50.0]))
    assert stats["n"] == 5
    assert stats["median"] == 30.0
    assert stats["share_ge_40"] == 0.4
    assert exclusive_rs_edges([50, 60, 70]) == [
        (50.0, 60.0, "50–59"),
        (60.0, 70.0, "60–69"),
        (70.0, 101.0, "70+"),
    ]


def test_fund_dist_helpers():
    scored = pd.DataFrame({
        "ticker": ["A", "B", "C", "D", "E"],
        "rs_rank": [55, 65, 75, 85, 95],
        "fund_score": [20.0, 30.0, 50.0, 40.0, 60.0],
        "market_cap": [2e9] * 5,
    })
    slices = [slice_at_threshold(scored, t) for t in (50, 70, 90)]
    cum = fund_dist_cumulative(slices)
    assert list(cum["n"]) == [5, 3, 1]
    assert cum.loc[cum["label"] == "RS≥70", "median"].iloc[0] == 50.0

    excl = fund_dist_exclusive(scored, (50, 70, 90))
    assert list(excl["n"]) == [2, 2, 1]  # 50–69, 70–89, 90+
    assert excl.loc[excl["label"] == "90+", "median"].iloc[0] == 60.0

    rem = fund_dist_removed_on_raise(slices)
    assert rem.iloc[0]["band"] == "50→70"
    assert rem.iloc[0]["removed_n"] == 2
    assert rem.iloc[0]["kept_n"] == 3
