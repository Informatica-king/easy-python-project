"""Tests for earn_calendar + timing_gate + pick_pool + redesigned filter_buy_ideas."""

from datetime import date
from pathlib import Path

from sepa.buy_scenarios import resolve_earn
from sepa.earn_calendar import EarnDateInfo, earn_info_from_row, load_confirmed_earn_map
from sepa.pick_pool import build_pick_pool
from sepa.portfolio_ops import BuyIdea, HoldingRow, PortfolioBook, filter_buy_ideas
from sepa.timing_gate import (
    ALLOW_GO_B_EXEC,
    BREAKOUT_PCT,
    SWING_LOOKBACK,
    evaluate_timing_metrics,
    timing_from_scenario_row,
)


def test_earn_estimate_does_not_hard_block():
    info = EarnDateInfo(date(2026, 8, 12), "estimate")
    assert info.in_d5(date(2026, 8, 12)) is True
    assert info.blocks_new_buys(date(2026, 8, 12)) is False
    assert info.warn_estimate_window(date(2026, 8, 12)) is True


def test_earn_confirmed_hard_blocks():
    info = EarnDateInfo(date(2026, 8, 20), "confirmed")
    assert info.blocks_new_buys(date(2026, 8, 18)) is True
    assert info.blocks_new_buys(date(2026, 8, 10)) is False


def test_earn_info_from_row_default_estimate():
    e = earn_info_from_row({"earnDate": "2026-08-12"})
    assert e.source == "estimate"
    e2 = earn_info_from_row({"earnDate": "2026-08-12", "earn_source": "confirmed"})
    assert e2.source == "confirmed"


def test_timing_a_maps_to_go_a():
    tr = timing_from_scenario_row(
        {"t": "CMPR", "scenario": "A", "rsi": 52, "pct_hi": -0.05},
        as_of=date(2026, 8, 12),
    )
    assert tr.status == "GO_A"
    assert tr.is_go is True


def test_timing_soft_is_wait():
    tr = timing_from_scenario_row({"t": "ALKS", "scenario": "SOFT"}, as_of=date(2026, 8, 12))
    assert tr.status == "WAIT"
    assert tr.is_go is False


def test_timing_b_wait_when_go_b_disabled():
    assert ALLOW_GO_B_EXEC is False
    tr = timing_from_scenario_row({"t": "X", "scenario": "B"}, as_of=date(2026, 8, 12))
    assert tr.status == "WAIT"


def test_pick_pool_from_chase_excludes_jungha():
    chase = {
        "rows": [
            {"rank": 1, "ticker": "ANAB", "chase": "상", "px": 57.0},
            {"rank": 2, "ticker": "ZD", "chase": "중하", "px": 53.0},
            {"rank": 3, "ticker": "BCRX", "chase": "상", "px": 10.0},
        ]
    }
    picks = build_pick_pool(chase, None)
    tickers = [p.ticker for p in picks]
    assert "ANAB" in tickers and "BCRX" in tickers
    assert "ZD" not in tickers


def test_filter_legacy_scenario_fallback_buckets():
    """No chase → scenario fallback; A∩ups+ = 실행, SOFT = 워치."""
    book = PortfolioBook(
        as_of=date(2026, 8, 2),
        source="test",
        cash_usd=629.0,
        cash_floor_usd=150.0,
        cash_krw=0,
        note="",
        holdings=[
            HoldingRow(
                "NESR",
                4,
                27.0,
                grade="C",
                max_pct=0.06,
                quality_grade="C",
                quality_max_pct=0.06,
                no_add=True,
                earn_date=date(2026, 8, 18),
            ),
        ],
    )
    scenarios = {
        "as_of": "2026-08-01",
        "rows": [
            {"t": "CMPR", "scenario": "A", "upside": 0.12, "rsi": 52, "pct_hi": -0.07, "px": 98.7, "earnDate": "2026-10-28"},
            {"t": "FTNT", "scenario": "A", "upside": -0.05, "rsi": 60, "pct_hi": -0.05, "px": 161.0, "earnDate": "2026-07-29"},
            {"t": "NESR", "scenario": "SOFT", "upside": 0.22, "rsi": 50, "pct_hi": -0.10, "px": 27.0, "earnDate": "2026-08-18"},
            {"t": "ALKS", "scenario": "SOFT", "upside": 0.14, "rsi": 44, "pct_hi": -0.12, "px": 49.0, "earnDate": "2026-10-28"},
        ],
    }
    ideas = filter_buy_ideas(book, scenarios, None)
    by = {i.ticker: i for i in ideas}
    assert by["CMPR"].bucket == "실행후보"
    assert by["CMPR"].timing == "GO_A"
    assert by["CMPR"].limit_hint and "지정가" in by["CMPR"].limit_hint
    assert by["FTNT"].bucket == "금지"
    assert by["NESR"].bucket == "금지"
    assert by["ALKS"].bucket == "워치"
    assert by["ALKS"].timing == "WAIT"


def test_filter_chase_first_anab_wait_without_go():
    """Chase 상 without GO timing → 본선 워치 (not dropped)."""
    book = PortfolioBook(
        as_of=date(2026, 8, 12),
        source="test",
        cash_usd=300.0,
        cash_floor_usd=150.0,
        cash_krw=0,
        note="",
        holdings=[],
    )
    chase = {
        "rows": [
            {"rank": 1, "ticker": "ANAB", "chase": "상", "px": 57.87, "earn_date": "2026-08-12"},
            {"rank": 60, "ticker": "ZD", "chase": "중하", "px": 53.5},
        ]
    }
    scenarios = {
        "rows": [
            {"t": "ZD", "scenario": "A", "upside": 0.095, "px": 53.5, "rsi": 54, "pct_hi": -0.08},
        ]
    }
    ideas = filter_buy_ideas(book, scenarios, chase)
    by = {i.ticker: i for i in ideas}
    assert "ANAB" in by
    assert by["ANAB"].bucket == "워치"
    assert by["ANAB"].timing == "WAIT"
    # ZD is chase-excluded even if timing GO
    assert by["ZD"].bucket == "금지"


def test_load_confirmed_earn_map_from_ssot():
    m = load_confirmed_earn_map(Path("config/portfolio_watch.yaml"))
    assert m["SCSC"] == date(2026, 8, 20)
    assert m["CMPR"] == date(2026, 10, 28)
    assert "NESR" not in m  # exited


def test_resolve_earn_prefers_portfolio_confirmed():
    confirmed = {"SCSC": date(2026, 8, 20)}
    e = resolve_earn("SCSC", {"earnDate": "2026-09-01"}, confirmed_map=confirmed)
    assert e.source == "confirmed"
    assert e.earn_date == date(2026, 8, 20)
    e2 = resolve_earn("ANAB", {"earnDate": "2026-08-12"}, confirmed_map={})
    assert e2.source == "estimate"
    assert e2.earn_date == date(2026, 8, 12)


def test_timing_constants_exported():
    assert SWING_LOOKBACK == 20
    assert BREAKOUT_PCT == 0.0


def test_find_pick_go_hits_highlights_overlap():
    from sepa.pick_pool import find_pick_go_hits

    chase = {
        "rows": [
            {"rank": 1, "ticker": "ANAB", "chase": "상", "px": 57.0},
            {"rank": 2, "ticker": "ZD", "chase": "중하", "px": 53.0},
            {"rank": 3, "ticker": "BCRX", "chase": "상", "px": 10.0},
        ]
    }
    scenarios = {
        "rows": [
            {"t": "ANAB", "scenario": "A", "rsi": 50, "pct_hi": -0.05, "px": 57.0},
            {"t": "ZD", "scenario": "A", "rsi": 54, "pct_hi": -0.08, "px": 53.0},
            {"t": "BCRX", "scenario": "SOFT", "rsi": 55, "pct_hi": -0.10, "px": 10.0},
        ]
    }
    hits = find_pick_go_hits(chase, scenarios, as_of=date(2026, 8, 12))
    tickers = [h["ticker"] for h in hits]
    assert "ANAB" in tickers  # 본선 ∩ GO_A
    assert "ZD" not in tickers  # Chase 중하 → 비본선
    assert "BCRX" not in tickers  # 본선 but WAIT
    assert hits[0]["timing"] == "GO_A"


def test_evaluate_timing_go_a_and_block():
    go = evaluate_timing_metrics(
        ticker="X",
        above200=True,
        align=True,
        near_ma20=True,
        near_swing_l=False,
        rsi=50.0,
        pct_hi=-0.05,
        vol_ok=True,
        vol_hot=False,
        breakout=False,
        as_of=date(2026, 8, 12),
    )
    assert go.status == "GO_A"
    assert go.legacy_scenario == "A"
    blocked = evaluate_timing_metrics(
        ticker="SCSC",
        above200=True,
        align=True,
        near_ma20=True,
        near_swing_l=False,
        rsi=50.0,
        pct_hi=-0.05,
        vol_ok=True,
        vol_hot=False,
        breakout=False,
        earn=EarnDateInfo(date(2026, 8, 20), "confirmed"),
        as_of=date(2026, 8, 18),
    )
    assert blocked.status == "BLOCK"
    assert blocked.legacy_scenario == ""


def test_analyze_ticker_drops_trailing_nan_close():
    """Incomplete session bar (OHLC NaN) must not poison MA/vs20."""
    import numpy as np
    import pandas as pd

    from sepa.buy_scenarios import analyze_ticker

    rng = pd.bdate_range("2025-01-02", periods=220)
    close = np.linspace(10.0, 20.0, 220)
    hist = pd.DataFrame(
        {
            "Open": close,
            "High": close + 0.2,
            "Low": close - 0.2,
            "Close": close,
            "Volume": np.full(220, 1_000_000.0),
        },
        index=rng,
    )
    bad = rng[-1] + pd.Timedelta(days=1)
    hist.loc[bad] = [np.nan, np.nan, np.nan, np.nan, 0.0]
    row = analyze_ticker("TEST", {"rank": 1}, as_of=date(2026, 8, 18), history=hist)
    assert row is not None
    assert row["vs_ma20"] == row["vs_ma20"]  # not NaN
    assert abs(row["vs_ma20"]) < 50
