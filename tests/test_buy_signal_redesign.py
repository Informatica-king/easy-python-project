"""Tests for earn_calendar + timing_gate + pick_pool + redesigned filter_buy_ideas."""

from datetime import date

from sepa.earn_calendar import EarnDateInfo, earn_info_from_row
from sepa.pick_pool import build_pick_pool
from sepa.portfolio_ops import BuyIdea, HoldingRow, PortfolioBook, filter_buy_ideas
from sepa.timing_gate import ALLOW_GO_B_EXEC, timing_from_scenario_row


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
