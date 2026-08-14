"""Tests for portfolio growth P1 (NAV history · bench summary · goal gauge)."""

from datetime import date
from pathlib import Path

from sepa.portfolio_ops import (
    BenchSummary,
    NavPoint,
    PortfolioBook,
    bench_summary_from_series,
    goal_progress,
    load_book,
    load_nav_history,
    nav_delta_summary,
    parse_nav_from_portfolio_html,
)


def test_parse_nav_from_existing_html():
    p = Path("reports/Portfolio_Ops_2026-08-12.html")
    assert p.exists()
    pt = parse_nav_from_portfolio_html(p)
    assert pt is not None
    assert pt.as_of == date(2026, 8, 12)
    assert abs(pt.equity_usd - 1100.10) < 0.05
    assert abs(pt.liquid_usd - 1647.69) < 0.05
    assert pt.cash_usd > 500


def test_load_nav_history_merges_and_sorts():
    pts = load_nav_history("reports")
    assert len(pts) >= 3
    assert pts == sorted(pts, key=lambda x: x.as_of)
    # unique dates
    assert len({p.as_of for p in pts}) == len(pts)


def test_nav_delta_summary():
    pts = [
        NavPoint(date(2026, 8, 8), 1221.0, 260.0, 1481.0),
        NavPoint(date(2026, 8, 14), 1200.0, 467.0, 1667.0),
    ]
    s = nav_delta_summary(pts)
    assert s is not None
    assert "1481" in s.replace(",", "") or "1,481" in s
    assert "+$" in s or "+$" in s.replace(" ", "")
    assert nav_delta_summary(pts[:1]) is None


def test_bench_summary_from_fake_series():
    book = PortfolioBook(
        as_of=date(2026, 8, 14),
        source="t",
        cash_usd=100,
        cash_floor_usd=150,
        cash_krw=0,
        note="",
        holdings=[],
    )
    # empty holdings → None
    assert bench_summary_from_series(book, {}) is None

    from sepa.portfolio_ops import HoldingRow

    book.holdings = [HoldingRow("AAA", 2, 10.0)]
    series = {
        "AAA": [(date(2026, 8, 1), 10.0), (date(2026, 8, 10), 11.0), (date(2026, 8, 14), 12.0)],
        "QQQ": [(date(2026, 8, 1), 100.0), (date(2026, 8, 10), 101.0), (date(2026, 8, 14), 102.0)],
        "SPY": [(date(2026, 8, 1), 200.0), (date(2026, 8, 10), 198.0), (date(2026, 8, 14), 204.0)],
    }
    # force as_of lookback to include Aug 1
    book.as_of = date(2026, 8, 14)
    sm = bench_summary_from_series(book, series)
    assert sm is not None
    assert isinstance(sm, BenchSummary)
    assert abs(sm.port_end - 120.0) < 1e-6  # 12/10*100
    assert sm.qqq_end is not None and abs(sm.qqq_end - 102.0) < 1e-6
    assert sm.vs_qqq_pct is not None and abs(sm.vs_qqq_pct - 18.0) < 1e-6


def test_goal_progress_from_live_book():
    book = load_book("config/portfolio_watch.yaml")
    book.equity_usd = 1200.49
    book.liquid_usd = 1667.20
    book.cash_krw_usd = 171.82
    g = goal_progress(book)
    assert g.target_krw == 100_000_000
    assert g.liquid_krw is not None
    assert abs(g.liquid_krw - 1667.20 * book.fx_krw_per_usd) < 1.0
    assert g.pct is not None and 0 < g.pct < 0.05  # far from 1억
    assert g.gap_krw is not None and g.gap_krw > 90_000_000
