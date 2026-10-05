"""Tests for Early-Confirmed Growth (ECG) A1."""

from __future__ import annotations

import numpy as np
import pandas as pd

from sepa.ecg import (
    W_E1,
    W_E2,
    W_E3,
    W_E4,
    compute_ecg_table,
    confirmed_mask,
    pool_fund_median,
    score_e1_rs_band,
    score_e2_52w_proximity,
    score_e3_accel_earliness,
    score_e4_sma200_turn,
)


def test_weights_sum_100():
    assert abs(W_E1 + W_E2 + W_E3 + W_E4 - 100.0) < 1e-9


def test_e1_prefers_mid_band():
    assert score_e1_rs_band(80) > score_e1_rs_band(72)
    assert score_e1_rs_band(80) > score_e1_rs_band(92)
    assert score_e1_rs_band(88) > score_e1_rs_band(97)
    assert score_e1_rs_band(65) == 0.0


def test_e2_sweet_spot_near_highs():
    # at highs
    assert score_e2_52w_proximity(100, 100) >= 95
    # mild pullback still good
    assert score_e2_52w_proximity(85, 100) >= 80
    # extended above highs weaker than at highs
    assert score_e2_52w_proximity(120, 100) < score_e2_52w_proximity(100, 100)
    # deep drawdown weak
    assert score_e2_52w_proximity(50, 100) < 40


def test_e3_shallow_accel_beats_deep():
    shallow = score_e3_accel_earliness(50, 0, eps_accel_n=1, sales_accel_n=0)
    deep = score_e3_accel_earliness(50, 0, eps_accel_n=4, sales_accel_n=0)
    none = score_e3_accel_earliness(0, 0, eps_accel_n=3, sales_accel_n=3)
    assert shallow == 100.0
    assert deep < shallow
    assert none == 0.0


def test_e4_recent_trough_scores_high():
    idx = pd.bdate_range("2024-01-01", periods=200)
    # decline then trough 10 days ago then rise
    vals = np.linspace(100, 80, 190).tolist() + np.linspace(80, 90, 10).tolist()
    s = pd.Series(vals, index=idx)
    score = score_e4_sma200_turn(s, trend_days=21, lookback=126)
    assert score >= 80.0


def test_confirmed_g3c_median_or_shallow_bd_with_floor():
    """G3c: path A = Fund≥med; path B = shallow B|D + Fund≥30. S-only does not pass."""
    df = pd.DataFrame(
        {
            # median = (35+32)/2 = 33.5
            "fund_score": [70.0, 40.0, 35.0, 32.0, 20.0, 15.0],
            "s_surprise": [0.0, 0.0, 0.0, 40.0, 0.0, 50.0],
            "b_raw": [0.0, 10.0, 10.0, 0.0, 10.0, 0.0],
            "d_raw": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "eps_accel_n": [0, 1, 1, 0, 1, 0],
            "sales_accel_n": [0, 0, 0, 0, 0, 0],
        }
    )
    med = pool_fund_median(df["fund_score"])
    assert abs(med - 33.5) < 1e-9
    m = confirmed_mask(df, med)
    # path A (70), path B shallow+floor (40), path B (35), S-only@32 fail,
    # shallow but Fund 20 < floor fail, S-only@15 fail
    assert list(m) == [True, True, True, False, False, False]


def test_confirmed_g3c_rejects_deep_accel_below_median():
    df = pd.DataFrame(
        {
            "fund_score": [60.0, 35.0],
            "s_surprise": [0.0, 0.0],
            "b_raw": [0.0, 12.0],
            "d_raw": [0.0, 0.0],
            "eps_accel_n": [0, 4],  # deep accel → not shallow
            "sales_accel_n": [0, 0],
        }
    )
    m = confirmed_mask(df, median=50.0)
    assert list(m) == [True, False]


def test_compute_ecg_zero_when_not_confirmed():
    fund = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "name": ["A", "B", "C"],
            "rs_rank": [85.0, 88.0, 80.0],
            "fund_score": [10.0, 12.0, 80.0],  # median 12; AAA below, no S/B/D
            "s_surprise": [0.0, 0.0, 0.0],
            "b_raw": [0.0, 0.0, 0.0],
            "d_raw": [0.0, 0.0, 0.0],
            "eps_accel_n": [0, 0, 0],
            "sales_accel_n": [0, 0, 0],
            "close": [100.0, 100.0, 100.0],
        }
    )
    px = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "px_close": [100.0, 100.0, 100.0],
            "high_52w": [105.0, 105.0, 105.0],
            "e4_sma200_turn": [80.0, 80.0, 80.0],
        }
    )
    out = compute_ecg_table(fund, price_features=px)
    assert not bool(out.loc[out.ticker == "AAA", "confirmed"].iloc[0])
    assert float(out.loc[out.ticker == "AAA", "ecg_score"].iloc[0]) == 0.0
    assert bool(out.loc[out.ticker == "CCC", "confirmed"].iloc[0])


def test_compute_ecg_ranks_confirmed_higher():
    fund = pd.DataFrame(
        {
            "ticker": ["HOT", "COLD"],
            "name": ["Hot", "Cold"],
            "rs_rank": [82.0, 98.0],
            "fund_score": [55.0, 10.0],
            "s_surprise": [20.0, 0.0],
            "b_raw": [30.0, 0.0],
            "d_raw": [0.0, 0.0],
            "eps_accel_n": [1, 0],
            "sales_accel_n": [0, 0],
            "close": [100.0, 150.0],
        }
    )
    px = pd.DataFrame(
        {
            "ticker": ["HOT", "COLD"],
            "px_close": [100.0, 150.0],
            "high_52w": [102.0, 100.0],  # COLD extended
            "e4_sma200_turn": [90.0, 20.0],
        }
    )
    out = compute_ecg_table(fund, price_features=px)
    assert bool(out.loc[out.ticker == "HOT", "confirmed"].iloc[0])
    assert out.iloc[0]["ticker"] == "HOT"
    assert out.loc[out.ticker == "HOT", "ecg_score"].iloc[0] > 0


def test_select_ecg_recommend_top_frac():
    from sepa.ecg import select_ecg_recommend

    rows = []
    for i in range(20):
        rows.append(
            {
                "ticker": f"T{i:02d}",
                "confirmed": True,
                "ecg_score": 100.0 - i,
                "fund_score": 60.0,
                "rs_rank": 80.0,
            }
        )
    rows.append(
        {"ticker": "XX", "confirmed": False, "ecg_score": 99.0, "fund_score": 70.0, "rs_rank": 90.0}
    )
    table = pd.DataFrame(rows)
    rec = select_ecg_recommend(table, top_frac=0.25, top_min=10, top_max=30)
    assert len(rec) == 10
    assert rec.iloc[0]["ticker"] == "T00"
    assert "XX" not in set(rec["ticker"])


def test_ecg_params_load_defaults():
    from sepa.config import load_params

    p = load_params("config/params.yaml")
    assert p.ecg.live_enabled is True
    assert abs(p.ecg.top_frac - 0.25) < 1e-9
    assert p.ecg.top_min == 10
    assert p.ecg.top_max == 30
