"""Unit tests for quantitative fundamental scoring (no network)."""

import pandas as pd
import pytest

from sepa.fundamental_score import (
    DEFAULT_WEIGHTS,
    accel_points,
    count_accel_quarters,
    count_margin_improve_quarters,
    delta_points,
    growth_points,
    is_next_quarter,
    latest_delta,
    latest_margin_yoy_delta,
    margin_delta_points,
    prior_year_frame,
    roe_points,
    score_ticker,
    surprise_points,
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


def test_surprise_and_delta_curves():
    assert surprise_points(None, 47) == 0.0
    assert surprise_points(-0.05, 47) == 0.0
    assert surprise_points(0.10, 47) == pytest.approx(47 * 0.5)
    assert surprise_points(0.20, 47) == pytest.approx(47.0)
    assert surprise_points(0.50, 47) == pytest.approx(47.0)

    assert delta_points(None, 14) == 0.0
    assert delta_points(-0.01, 14) == 0.0
    assert delta_points(0.125, 14) == pytest.approx(7.0)
    assert delta_points(0.25, 14) == pytest.approx(14.0)

    assert margin_delta_points(0.025, 25) == pytest.approx(12.5)
    assert margin_delta_points(0.05, 25) == pytest.approx(25.0)


def test_yoy_and_accel_count():
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
    assert count_accel_quarters(yoy) == 2
    assert latest_delta(yoy) == pytest.approx(0.25)


def test_accel_breaks_on_gap():
    yoy = {"CY2025Q1": 0.1, "CY2025Q2": 0.2, "CY2025Q4": 0.5}
    assert count_accel_quarters(yoy) == 0  # Q4 not adjacent to Q2
    # latest valid adjacent pair is still Q2−Q1
    assert latest_delta(yoy) == pytest.approx(0.1)


def test_margin_improve_count():
    npm = pd.Series(
        {
            "CY2024Q1": 0.10,
            "CY2024Q2": 0.10,
            "CY2024Q3": 0.10,
            "CY2025Q1": 0.12,
            "CY2025Q2": 0.13,
            "CY2025Q3": 0.11,
        }
    )
    assert count_margin_improve_quarters(npm) == 3
    assert latest_margin_yoy_delta(npm) == pytest.approx(0.01)


def test_default_weights_sum_100():
    assert DEFAULT_WEIGHTS.total == pytest.approx(100.0)


def test_score_ticker_happy_path():
    frames = [
        "CY2024Q1", "CY2024Q2", "CY2024Q3", "CY2024Q4",
        "CY2025Q1", "CY2025Q2", "CY2025Q3", "CY2025Q4",
    ]
    eps = [1.0, 1.0, 1.0, 1.0, 1.2, 1.5, 2.0, 2.8]
    rev = [100, 100, 100, 100, 120, 150, 190, 250]
    oi = [10, 10, 10, 10, 18, 30, 48, 75]
    ni = [8, 8, 8, 8, 14, 24, 40, 60]
    df = pd.DataFrame(
        {"eps": eps, "revenue": rev, "op_income": oi, "net_income": ni},
        index=pd.Index(frames, name="frame"),
    )
    df["npm"] = df["net_income"] / df["revenue"]
    df["opm"] = df["op_income"] / df["revenue"]

    br = score_ticker("TEST", df, roe=0.25, source="synthetic", eps_surprise=0.20)
    assert br.fund_score > 70
    assert br.s_surprise == pytest.approx(47.0)
    assert br.margin_source == "opm"
    assert br.eps_dyoy is not None and br.eps_dyoy > 0
    assert br.sales_dyoy is not None and br.sales_dyoy > 0
    assert br.opm_delta is not None and br.opm_delta > 0
