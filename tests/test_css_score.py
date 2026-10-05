"""Tests for Composite Success Score (CSS) A2."""

from __future__ import annotations

import pandas as pd

from sepa.css_score import (
    W_S1,
    W_S2,
    W_S3,
    W_S4,
    W_S5,
    W_S6,
    W_S7,
    W_S8,
    basket_median_plus,
    basket_sepa_top,
    compute_css,
    map_excess_to_score,
    map_tail_gap_to_score,
    score_s7_turnover,
    summarize_forward_grid,
)


def test_weights_sum_100():
    assert abs(W_S1 + W_S2 + W_S3 + W_S4 + W_S5 + W_S6 + W_S7 + W_S8 - 100.0) < 1e-9


def test_map_excess_zero_is_mid():
    assert abs(map_excess_to_score(0.0) - 50.0) < 1e-9
    assert map_excess_to_score(0.15) == 100.0
    assert map_excess_to_score(-0.15) == 0.0


def test_tail_gap_penalizes_lottery():
    tight = map_tail_gap_to_score(0.01)
    wide = map_tail_gap_to_score(0.20)
    assert tight > wide


def test_turnover_stable_membership_scores_high():
    a = {"A", "B", "C", "D"}
    b = {"A", "B", "C", "E"}
    c = {"A", "B", "C", "E"}
    score = score_s7_turnover([a, b, c])
    assert score > 70.0


def test_summarize_and_compute_css_baseline():
    rows = []
    for i, as_of in enumerate(["2025-01-31", "2025-02-28", "2025-03-31"]):
        for period, ew, med, spx, qqq, p10 in [
            ("1M", 0.02, 0.01, 0.01, 0.015, -0.05),
            ("3M", 0.04, 0.02, 0.03, 0.04, -0.08),
            ("6M", 0.08, 0.04, 0.07, 0.09, -0.12),
            ("1Y", 0.25, 0.12, 0.18, 0.22, -0.20),
        ]:
            rows.append(
                {
                    "as_of": as_of,
                    "period": period,
                    "n": 40,
                    "mean_ew": ew + i * 0.001,
                    "median": med,
                    "spx": spx,
                    "qqq": qqq,
                    "excess_ew_spx": (ew + i * 0.001) - spx,
                    "excess_med_spx": med - spx,
                    "excess_ew_qqq": (ew + i * 0.001) - qqq,
                    "excess_med_qqq": med - qqq,
                    "p10": p10,
                    "p90": ew + 0.3,
                }
            )
    summary = pd.DataFrame(rows)
    grid = summarize_forward_grid(summary)
    assert grid["n_asof"] == 3
    scored = compute_css(
        grid=grid,
        memberships=[{"A", "B"}, {"A", "B"}, {"A", "C"}],
        sector_top_shares=[0.30, 0.32, 0.28],
    )
    assert scored["sample_thin"] is True
    assert scored["sample_note"] == "자료 부족"
    assert scored["CSS"] == scored["CSS"]
    assert 0 <= scored["CSS"] <= 100


def test_baskets_median_subset_of_sepatop():
    fund = pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D"],
            "fund_score": [80.0, 60.0, 40.0, 0.0],
            "market_cap": [2e9, 2e9, 2e9, 2e9],
            "sector": ["Tech", "Tech", "Health", "Tech"],
        }
    )
    top = basket_sepa_top(fund)
    med = basket_median_plus(fund)
    assert set(med["ticker"]).issubset(set(top["ticker"]))
    assert "D" not in set(top["ticker"])
    assert len(med) <= len(top)
