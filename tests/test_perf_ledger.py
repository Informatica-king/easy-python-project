"""Tests for performance ledger / basket assignment."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sepa.perf_ledger import (
    BASKET_FUND_POOL,
    BASKET_MEDIAN_PLUS,
    BASKET_SOFT_DROP,
    assign_baskets,
    basket_members_rows,
    daily_pool_row,
    summarize_basket_forward,
    update_perf_ledger,
)


def _fund_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D"],
            "name": ["a", "b", "c", "d"],
            "fund_score": [10.0, 20.0, 30.0, 40.0],
            "rs_rank": [75.0, 85.0, 92.0, 95.0],
            "market_cap": [2e9] * 4,
        }
    )


def test_assign_baskets_median_and_rs90():
    baskets = assign_baskets(_fund_df())
    assert set(baskets[BASKET_FUND_POOL]["ticker"]) == {"A", "B", "C", "D"}
    # median=25 → C,D
    assert set(baskets[BASKET_MEDIAN_PLUS]["ticker"]) == {"C", "D"}
    assert set(baskets["rs90_ok"]["ticker"]) == {"C", "D"}


def test_assign_soft_drop_basket():
    soft = pd.DataFrame({"ticker": ["X"], "fund_score": [5.0], "rs_rank": [91.0]})
    baskets = assign_baskets(_fund_df(), soft)
    assert set(baskets[BASKET_SOFT_DROP]["ticker"]) == {"X"}


def test_update_perf_ledger_writes_panels(tmp_path: Path):
    report = tmp_path / "reports"
    report.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    fund = _fund_df()
    pack = update_perf_ledger(
        report_dir=report,
        cache_dir=cache,
        stamp="20260804",
        fund_df=fund,
        soft_drops=None,
        n_stage2=10,
        publish=False,
        backfill_all_history=True,
    )
    assert pack["ok"]
    assert (report / "perf" / "daily_pool_log.csv").exists()
    assert (report / "perf" / "basket_members_panel.csv").exists()
    members = pd.read_csv(report / "perf" / "basket_members_panel.csv")
    assert "median_plus" in set(members["basket"])
    assert pack["n_baskets"][BASKET_MEDIAN_PLUS] == 2

    # second day upsert
    fund2 = fund.copy()
    fund2.loc[fund2["ticker"] == "A", "fund_score"] = 50.0
    update_perf_ledger(
        report_dir=report,
        cache_dir=cache,
        stamp="20260805",
        fund_df=fund2,
        publish=False,
        backfill_all_history=True,
    )
    pool = pd.read_csv(report / "perf" / "daily_pool_log.csv")
    assert set(pool["stamp"].astype(str)) == {"20260804", "20260805"}


def test_daily_pool_row_and_members():
    baskets = assign_baskets(_fund_df())
    row = daily_pool_row(
        stamp="20260804",
        as_of="2026-08-04",
        n_stage2=12,
        fund_df=_fund_df(),
        baskets=baskets,
    )
    assert row["n_median_plus"] == 2
    members = basket_members_rows(baskets, stamp="20260804", as_of="2026-08-04")
    assert len(members) == sum(len(v) for v in baskets.values() if len(v))


def test_summarize_basket_forward_empty():
    assert summarize_basket_forward(pd.DataFrame(), stamp="20260804").empty
