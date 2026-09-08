"""Tests for Fund score 10-pt bucket 1y trend chart."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sepa.fund_score_trend import (
    BUCKET_LABELS,
    assign_fund_buckets,
    equal_weight_rebased_index,
    fund_bucket_label,
    plot_fund_score_trend,
    run_fund_score_trend,
)
from sepa.sepatop import BASE_LEVEL


def test_fund_bucket_half_open():
    assert fund_bucket_label(0) == "0-10"
    assert fund_bucket_label(9.9) == "0-10"
    assert fund_bucket_label(10) == "10-20"
    assert fund_bucket_label(47) == "40-50"
    assert fund_bucket_label(90) == "90-100"
    assert fund_bucket_label(99.9) == "90-100"
    assert fund_bucket_label(100) == "90-100"
    assert fund_bucket_label(float("nan")) is None
    assert fund_bucket_label(-1) is None


def test_assign_fund_buckets_categories():
    df = pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D"],
            "fund_score": [5, 10, 72, 100],
        }
    )
    out = assign_fund_buckets(df)
    assert list(out["fund_bucket"]) == ["0-10", "10-20", "70-80", "90-100"]
    assert list(out["fund_bucket"].cat.categories) == BUCKET_LABELS


def test_equal_weight_rebased_index():
    idx = pd.bdate_range("2025-01-02", periods=5)
    panel = pd.DataFrame(
        {
            "AAA": [10.0, 11.0, 12.0, 13.0, 14.0],
            "BBB": [20.0, 20.0, 22.0, 24.0, 26.0],
        },
        index=idx,
    )
    s = equal_weight_rebased_index(panel, ["AAA", "BBB"], base_date=idx[0])
    assert abs(float(s.iloc[0]) - BASE_LEVEL) < 1e-6
    # AAA: 1400, BBB: 1300 → mean 1350 at last day
    assert abs(float(s.iloc[-1]) - 1350.0) < 1e-6


def test_run_fund_score_trend_synthetic(tmp_path: Path):
    cache = tmp_path / "cache"
    cache.mkdir()
    idx = pd.bdate_range("2025-01-02", periods=60)
    # Write parquet caches
    for t, start, step in [("HI", 50.0, 0.5), ("LO", 50.0, -0.2), ("MID", 50.0, 0.1)]:
        prices = start + step * np.arange(len(idx))
        pd.DataFrame({"close": prices}, index=idx).to_parquet(cache / f"{t}.parquet")
    # Fake SPX
    pd.DataFrame({"close": 100 + 0.05 * np.arange(len(idx))}, index=idx).to_parquet(
        cache / "GSPC.parquet"
    )

    fund = pd.DataFrame(
        {
            "ticker": ["HI", "LO", "MID"],
            "fund_score": [85.0, 15.0, 45.0],
            "rs_rank": [90, 70, 80],
        }
    )
    charts = tmp_path / "charts"
    reports = tmp_path / "reports"
    pack = run_fund_score_trend(
        fund,
        chart_dir=charts,
        stamp="20260825",
        cache_dir=cache,
        report_dir=reports,
        lookback_days=60,
    )
    assert pack["ok"]
    assert Path(pack["chart"]).exists()
    assert pack["chart"].name == "analyze_fund_trend_20260825.png"
    assert Path(pack["csv"]).exists()
    assert pack["counts"]["80-90"] == 1
    assert pack["counts"]["10-20"] == 1
    assert pack["counts"]["40-50"] == 1
    # chart render helper with empty should return None
    assert plot_fund_score_trend(pd.DataFrame(), {}, charts / "empty.png", stamp="x") is None


def test_summarize_fund_trend_context():
    from sepa.fund_score_trend import summarize_fund_trend_context

    idx = pd.bdate_range("2025-01-02", periods=10)
    combined = pd.DataFrame(
        {
            "40-50": np.linspace(1000, 2000, 10),
            "70-80": np.linspace(1000, 1500, 10),
            "0-10": np.linspace(1000, 1800, 10),
            "S&P500": np.linspace(1000, 1100, 10),
        },
        index=idx,
    )
    counts = {"40-50": 10, "70-80": 5, "0-10": 4, "80-90": 0, "90-100": 0}
    ctx = summarize_fund_trend_context(combined, counts)
    assert ctx["ok"]
    assert ctx["strongest"] == "40-50"
    assert "80-90" in ctx["empty_high"]
    assert "본심판" in ctx["bullets"][-1]
    assert "40-50" in ctx["tip"]
