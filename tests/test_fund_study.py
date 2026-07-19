"""Unit tests for fund weight study helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from sepa.fund_study.events import event_return_pair, trading_day_offset
from sepa.fund_study.factors import delta_map, prior_quarter_frame, qoq_growth_map
from sepa.fund_study.stats import choose_level_or_delta, main_factors_only, propose_weights


def test_trading_day_offset_pre_post():
    idx = pd.bdate_range("2026-07-06", periods=10)  # Mon..
    # day0 = Wednesday 2026-07-08
    day0 = pd.Timestamp("2026-07-08")
    assert trading_day_offset(idx, day0, -1) == pd.Timestamp("2026-07-07")
    assert trading_day_offset(idx, day0, 1) == pd.Timestamp("2026-07-09")
    assert trading_day_offset(idx, day0, 3) == pd.Timestamp("2026-07-13")


def test_event_return_pair():
    idx = pd.bdate_range("2026-07-06", periods=10)
    px = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109], index=idx)
    # day0=Wed Jul 8 → start Tue Jul7 (101), end = 3rd session after Wed = Mon Jul13 (105)
    ret, start, end = event_return_pair(px, pd.Timestamp("2026-07-08"))
    assert start == pd.Timestamp("2026-07-07")
    assert end == pd.Timestamp("2026-07-13")
    assert ret == pytest.approx(105 / 101 - 1)


def test_qoq_and_delta():
    s = pd.Series({"CY2024Q1": 10.0, "CY2024Q2": 12.0, "CY2024Q3": 15.0})
    q = qoq_growth_map(s)
    assert q["CY2024Q2"] == pytest.approx(0.2)
    d = delta_map({"CY2024Q2": 0.2, "CY2024Q3": 0.25})
    assert d["CY2024Q3"] == pytest.approx(0.05)
    assert prior_quarter_frame("CY2025Q1") == "CY2024Q4"


def test_choose_and_weights():
    corr = pd.DataFrame(
        {
            "factor": ["eps_yoy", "eps_dyoy", "sales_yoy", "npm_d", "opm_d", "eps_qoq"],
            "n": [100, 100, 100, 100, 100, 100],
            "spearman": [0.1, 0.3, 0.2, 0.15, 0.05, 0.08],
            "pearson": [0.1, 0.3, 0.2, 0.15, 0.05, 0.08],
        }
    )
    chosen = choose_level_or_delta(corr)
    assert "eps_yoy" not in set(chosen["factor"])  # dyoy stronger
    assert "eps_dyoy" in set(chosen["factor"])
    assert "opm_d" not in set(chosen["factor"])  # npm_d stronger
    assert "npm_d" in set(chosen["factor"])
    assert set(main_factors_only(chosen)) == {"eps_dyoy", "sales_yoy", "npm_d"}
    ortho = pd.DataFrame(
        {
            "factor": ["eps_dyoy", "sales_yoy", "npm_d"],
            "n": [100, 100, 100],
            "spearman_ortho": [0.2, -0.1, 0.1],
            "pearson_ortho": [0.2, -0.1, 0.1],
        }
    )
    w = propose_weights(ortho, total=100)
    assert w.loc[w["factor"] == "sales_yoy", "reverse_candidate"].iloc[0]
    assert w["weight"].sum() == pytest.approx(100.0)
    assert w.loc[w["factor"] == "sales_yoy", "weight"].iloc[0] == 0.0
