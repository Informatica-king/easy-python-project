"""Tests for portfolio growth P1 (NAV history · bench summary · goal gauge)."""

from datetime import date, timedelta
from pathlib import Path

from sepa.portfolio_ops import (
    BenchSummary,
    HoldingRow,
    NavPoint,
    PortfolioBook,
    bench_summary_from_series,
    goal_progress,
    load_book,
    load_nav_history,
    nav_delta_summary,
    parse_nav_from_portfolio_html,
    portfolio_index,
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


def _daily_series(start: date, end: date, p0: float, daily: float) -> list[tuple[date, float]]:
    out = []
    px = p0
    d = start
    while d <= end:
        out.append((d, px))
        px += daily
        d += timedelta(days=1)
    return out


def test_portfolio_index_lookback_1m_vs_2w_vs_3m():
    """0-B default is 30 calendar days; 14d is a shorter window; 90d is no longer used."""
    as_of = date(2026, 10, 5)
    book = PortfolioBook(
        as_of=as_of,
        source="t",
        cash_usd=100,
        cash_floor_usd=150,
        cash_krw=0,
        note="",
        holdings=[HoldingRow("AAA", 1, 10.0)],
    )
    series = {
        "AAA": _daily_series(date(2026, 7, 1), as_of, 10.0, 0.01),
        "QQQ": _daily_series(date(2026, 7, 1), as_of, 100.0, 0.02),
    }
    idx_1m = portfolio_index(book, series, lookback_days=30)
    idx_2w = portfolio_index(book, series, lookback_days=14)
    idx_3m = portfolio_index(book, series, lookback_days=90)
    default = portfolio_index(book, series)
    assert idx_1m and idx_2w and idx_3m
    assert default[0][0] == idx_1m[0][0]
    assert idx_1m[0][0] == as_of - timedelta(days=30)
    assert idx_2w[0][0] == as_of - timedelta(days=14)
    assert idx_3m[0][0] == as_of - timedelta(days=90)
    assert idx_2w[0][0] > idx_1m[0][0] > idx_3m[0][0]
    assert len(idx_2w) < len(idx_1m) < len(idx_3m)

    sm_1m = bench_summary_from_series(book, series, lookback_days=30)
    sm_2w = bench_summary_from_series(book, series, lookback_days=14)
    assert sm_1m is not None and sm_2w is not None
    assert sm_1m.start == idx_1m[0][0]
    assert sm_2w.start == idx_2w[0][0]


def test_build_html_stacks_1m_then_2w_bench_charts(tmp_path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "generate_portfolio_ops",
        Path("reports/generate_portfolio_ops.py"),
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    pie = tmp_path / "pie.png"
    one_m = tmp_path / "vs_bench.png"
    two_w = tmp_path / "vs_bench_2w.png"
    for p in (pie, one_m, two_w):
        p.write_bytes(png)

    book = PortfolioBook(
        as_of=date(2026, 10, 5),
        source="t",
        cash_usd=201.05,
        cash_floor_usd=150,
        cash_krw=0,
        note="",
        holdings=[],
    )
    html_doc = mod.build_html(
        book,
        [],
        pie,
        pie,
        one_m,
        ["no-op"],
        None,
        None,
        bench_2w=two_w,
    )
    assert "0-B. 포폴 vs QQQ·SPY" in html_doc
    assert html_doc.count("data:image/png;base64,") >= 4  # pies + 1m + 2w
    pos_1m = html_doc.find(mod.img_b64(one_m))
    pos_2w = html_doc.find(mod.img_b64(two_w))
    assert 0 <= pos_1m < pos_2w
    assert "위=최근 1개월 · 아래=최근 2주" in html_doc
    assert "3개월" not in html_doc
