"""Tests for sepa.portfolio_ops (offline where possible)."""

from datetime import date

from sepa.portfolio_ops import (
    HoldingRow,
    PortfolioBook,
    filter_buy_ideas,
    in_earn_d5,
    load_book,
    stance_for,
    week_plan_mode,
)


def test_load_book_snap_20260802():
    book = load_book("config/portfolio_watch.yaml")
    assert book.as_of == date(2026, 8, 2)
    assert abs(book.cash_usd - 629.05) < 1e-6
    tickers = {h.ticker for h in book.holdings}
    assert tickers == {"ECPG", "AMRX", "LASR", "SCHD", "NESR", "TXG", "RELY"}
    schd = next(h for h in book.holdings if h.ticker == "SCHD")
    assert schd.shares == 4
    nesr = next(h for h in book.holdings if h.ticker == "NESR")
    assert nesr.shares == 4
    txg = next(h for h in book.holdings if h.ticker == "TXG")
    assert txg.shares == 2
    assert txg.no_add is True


def test_earn_d5_window():
    assert in_earn_d5(date(2026, 8, 5), date(2026, 8, 2)) is True  # D-3
    assert in_earn_d5(date(2026, 8, 5), date(2026, 8, 5)) is True
    assert in_earn_d5(date(2026, 8, 5), date(2026, 7, 30)) is False
    assert in_earn_d5(date(2026, 8, 18), date(2026, 8, 2)) is False


def test_week_plan_mode():
    assert week_plan_mode(date(2026, 8, 2)) == "next_week"  # Sunday
    assert week_plan_mode(date(2026, 8, 1)) == "next_week"  # Saturday
    assert week_plan_mode(date(2026, 7, 31)) == "next_week"  # Friday
    assert week_plan_mode(date(2026, 8, 3)) == "next_5bd"  # Monday


def test_ops_date_overrides_plan_mode():
    book = load_book("config/portfolio_watch.yaml")
    # snap as_of is Sunday 8/2; ops Monday 8/3 → 5bd plan
    from sepa.portfolio_ops import build_ops_plan, enrich_marks

    book = enrich_marks(book, ops_date=date(2026, 8, 3), use_snap_marks=True)
    assert book.effective_date == date(2026, 8, 3)
    assert week_plan_mode(book.effective_date) == "next_5bd"
    plan = build_ops_plan(book, [])
    assert any("향후 5영업일" in p for p in plan)


def test_stance_earn_d5_no_add():
    h = HoldingRow(
        ticker="ECPG",
        shares=2,
        cost=92.32,
        sleeve="core",
        stop=80.0,
        no_add=True,
        earn_date=date(2026, 8, 5),
        px=94.08,
        value=188.16,
        w_stock=0.21,
    )
    s = stance_for(h, date(2026, 8, 2))
    assert "EARN_D5" in s
    assert "NO_ADD" in s


def test_filter_buy_ideas_buckets():
    book = PortfolioBook(
        as_of=date(2026, 8, 2),
        source="test",
        cash_usd=629.0,
        cash_floor_usd=150.0,
        cash_krw=0,
        note="",
        holdings=[
            HoldingRow("NESR", 4, 27.0, "satellite", no_add=True, earn_date=date(2026, 8, 18)),
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
    assert by["FTNT"].bucket == "금지"  # negative upside
    assert by["NESR"].bucket == "금지"  # held NO_ADD
    assert by["ALKS"].bucket == "워치"
