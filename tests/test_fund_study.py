"""Unit tests for fund weight study helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from sepa.data import store
from sepa.fund_study.backfill import history_span_years, partition_backfill_targets
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


def test_partition_backfill_targets(tmp_path: Path):
    short = pd.DataFrame(
        {"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
        index=pd.bdate_range("2024-01-01", periods=50),
    )
    long = pd.DataFrame(
        {"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
        index=pd.bdate_range("2015-01-01", periods=2600),
    )
    short.to_parquet(tmp_path / "AAA.parquet")
    long.to_parquet(tmp_path / "BBB.parquet")
    need, ok = partition_backfill_targets(
        ["AAA", "BBB", "CCC"],
        cache_dir=tmp_path,
        min_span_years=9.5,
    )
    assert set(need) == {"AAA", "CCC"}
    assert ok == ["BBB"]
    assert history_span_years(tmp_path, "BBB") >= 9.5


def test_backfill_history_merges_older_bars(tmp_path: Path):
    # Existing short cache
    old = pd.DataFrame(
        {"open": 10.0, "high": 10.0, "low": 10.0, "close": 10.0, "volume": 100.0},
        index=pd.bdate_range("2024-06-01", periods=5),
    )
    old.index.name = "date"
    old.to_parquet(tmp_path / "TEST.parquet")

    # Fake download returns longer history ending at same period
    new = pd.DataFrame(
        {"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 50.0},
        index=pd.bdate_range("2016-01-01", periods=20),
    )
    # Make MultiIndex like yfinance group_by=ticker
    new.columns = pd.MultiIndex.from_product([["TEST"], new.columns])

    with patch("yfinance.download", return_value=new):
        ok, failed = store.backfill_history(
            ["TEST"],
            tmp_path,
            lookback_years=11,
            chunk_size=10,
            pause_sec=0,
        )
    assert ok == ["TEST"]
    assert failed == []
    df = pd.read_parquet(tmp_path / "TEST.parquet")
    assert df.index.min() <= pd.Timestamp("2016-01-15")
    assert history_span_years(tmp_path, "TEST") is not None

