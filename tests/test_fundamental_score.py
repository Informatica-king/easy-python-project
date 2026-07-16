"""Unit tests for quantitative fundamental scoring (no network)."""

import pandas as pd
import pytest

from sepa.fundamental_score import (
    accel_points,
    count_accel_quarters,
    count_margin_improve_quarters,
    growth_points,
    is_next_quarter,
    prior_year_frame,
    roe_points,
    score_ticker,
    yoy_growth_map,
)


def test_prior_year_and_adjacency():
    assert prior_year_frame("CY2025Q1") == "CY2024Q1"
    assert is_next_quarter("CY2024Q4", "CY2025Q1")
    assert is_next_quarter("CY2025Q1", "CY2025Q2")
    assert not is_next_quarter("CY2025Q1", "CY2025Q3")


def test_growth_points_breakpoints():
    w = 25.0
    assert growth_points(-0.1, w) == 0.0
    assert growth_points(0.0, w) == 0.0
    assert growth_points(0.25, w) == pytest.approx(12.0)
    assert growth_points(0.50, w) == pytest.approx(20.0)
    assert growth_points(1.0, w) == pytest.approx(25.0)
    assert growth_points(2.0, w) == pytest.approx(25.0)


def test_accel_points_two_is_full():
    w = 20.0
    assert accel_points(0, w) == 0.0
    assert accel_points(1, w) == pytest.approx(10.0)
    assert accel_points(2, w) == pytest.approx(20.0)
    assert accel_points(3, w) == pytest.approx(20.0)


def test_roe_points():
    assert roe_points(None, 5) == 0.0
    assert roe_points(0.17, 5) == pytest.approx(5.0)
    assert roe_points(0.085, 5) == pytest.approx(2.5)
    assert roe_points(0.34, 5) == pytest.approx(5.0)


def test_yoy_and_accel_count():
    # Rising then accelerating EPS: YoY 10%, 30%, 55% over Q1-Q3
    eps = pd.Series(
        {
            "CY2024Q1": 1.0,
            "CY2024Q2": 1.0,
            "CY2024Q3": 1.0,
            "CY2025Q1": 1.1,
            "CY2025Q2": 1.3,
            "CY2025Q3": 1.55,
        }
    )
    yoy = yoy_growth_map(eps)
    assert yoy["CY2025Q1"] == pytest.approx(0.1)
    assert yoy["CY2025Q2"] == pytest.approx(0.3)
    assert yoy["CY2025Q3"] == pytest.approx(0.55)
    assert count_accel_quarters(yoy) == 2  # Q3>Q2 and Q2>Q1


def test_accel_breaks_on_gap():
    yoy = {"CY2025Q1": 0.1, "CY2025Q2": 0.2, "CY2025Q4": 0.5}  # Q3 missing
    # Latest Q4 cannot form adjacent pair with Q2 → 0
    assert count_accel_quarters(yoy) == 0


def test_margin_improve_count():
    npm = pd.Series(
        {
            "CY2024Q1": 0.10,
            "CY2024Q2": 0.10,
            "CY2024Q3": 0.10,
            "CY2025Q1": 0.12,
            "CY2025Q2": 0.13,
            "CY2025Q3": 0.11,  # still > year-ago 0.10
        }
    )
    assert count_margin_improve_quarters(npm) == 3


def test_score_ticker_happy_path():
    # Strong Code-33-ish synthetic: accelerating EPS & sales, rising margins, high ROE
    frames = [
        "CY2024Q1", "CY2024Q2", "CY2024Q3", "CY2024Q4",
        "CY2025Q1", "CY2025Q2", "CY2025Q3", "CY2025Q4",
    ]
    eps = [1.0, 1.0, 1.0, 1.0, 1.2, 1.5, 2.0, 2.8]
    rev = [100, 100, 100, 100, 120, 150, 190, 250]
    ni = [10, 10, 10, 10, 15, 22, 32, 45]
    df = pd.DataFrame(
        {"eps": eps, "revenue": rev, "net_income": ni},
        index=pd.Index(frames, name="frame"),
    )
    df["npm"] = df["net_income"] / df["revenue"]

    br = score_ticker("TEST", df, roe=0.25, source="synthetic")
    assert br.fund_score > 80
    assert br.eps_accel_n >= 2
    assert br.sales_accel_n >= 2
    assert br.margin_n >= 2
    assert br.g_roe == pytest.approx(5.0)
