"""Tests for 3-layer buy score (offline; mocked price series)."""

from datetime import date

from sepa.buy_score import (
    load_guide_grades,
    recommend_from_scores,
    score_buy_ideas,
    score_l1,
    score_l2,
    score_l3,
    score_ticker,
)
from sepa.portfolio_ops import BuyIdea, apply_buy_scores, filter_buy_ideas, load_book


def _series(start: float, end: float, n: int = 80) -> list[float]:
    step = (end - start) / (n - 1)
    return [start + i * step for i in range(n)]


def test_score_l1_both_positive():
    s, note = score_l1(0.05, 0.10)
    assert s == 2
    assert "RS" in note


def test_score_l1_mixed():
    assert score_l1(0.05, -0.02)[0] == 1
    assert score_l1(-0.05, -0.02)[0] == 0


def test_score_l1_fail_neutral():
    s, note = score_l1(None, None, fail_neutral=True)
    assert s == 1
    assert "중립" in note


def test_score_l2_rising_unknown_margin():
    # ECPG rising +3pp, no margin passed → +1
    s, note, excl = score_l2("ECPG")
    assert excl is False
    assert s == 1
    assert "점유" in note


def test_score_l2_margin_cancel():
    s, note, excl = score_l2("ECPG", margin_delta_pp=-1.0)
    assert excl is True
    assert s == 0
    assert "마진" in note or "가산취소" in note or "실행제외" in note


def test_score_l2_no_profile():
    s, note, excl = score_l2("ZZZZ")
    assert s == 0 and excl is False


def test_score_l3_window_a():
    grades = {"ECPG": {"grade": "A", "note": "가이드↑"}}
    s, note, g, shrink = score_l3(
        "ECPG",
        as_of=date(2026, 8, 6),
        earn_date=date(2026, 8, 5),
        grades=grades,
    )
    assert s == 1 and g == "A" and shrink is False


def test_score_l3_grade_c_shrink():
    grades = {"LASR": {"grade": "C", "note": "컷"}}
    s, note, g, shrink = score_l3(
        "LASR",
        as_of=date(2026, 8, 7),
        earn_date=date(2026, 8, 6),
        grades=grades,
    )
    assert g == "C" and shrink is True
    assert recommend_from_scores(l1=2, l2=2, total=4, pass_forced=False, shrink=True) == "축소후보"


def test_score_ticker_mocked_rs_pass():
    # ticker up strongly, spy flat → RS>0 both windows
    def fetch(t, start, end):
        if t == "SPY":
            return _series(100, 100.5)
        return _series(50, 70)

    sc = score_ticker(
        "CMPR",
        as_of=date(2026, 8, 3),
        fetch_closes=fetch,
    )
    assert sc.l1 == 2
    assert sc.recommend in ("1순위", "극소/워치", "패스")


def test_score_ticker_l1_zero_forces_pass():
    def fetch(t, start, end):
        if t == "SPY":
            return _series(100, 120)
        return _series(50, 51)  # lagging

    sc = score_ticker("LAUR", as_of=date(2026, 8, 3), fetch_closes=fetch)
    assert sc.l1 == 0
    assert sc.recommend == "패스"
    assert sc.pass_forced is True


def test_score_buy_ideas_orders_exec():
    ideas = [
        BuyIdea("LAUR", "실행후보", "A", "x", upside=0.06),
        BuyIdea("CMPR", "실행후보", "A", "y", upside=0.12),
        BuyIdea("ALKS", "워치", "SOFT", "z", upside=0.14),
    ]

    def fetch(t, start, end):
        if t == "SPY":
            return _series(100, 101)
        if t == "CMPR":
            return _series(40, 55)
        return _series(40, 41)  # LAUR weak RS

    scored = score_buy_ideas(ideas, as_of=date(2026, 8, 3), fetch_closes=fetch)
    execs = [(i, s) for i, s in scored if s is not None]
    assert execs[0][0].ticker == "CMPR"
    assert execs[0][1].l1 >= execs[1][1].l1


def test_apply_buy_scores_integration():
    book = load_book("config/portfolio_watch.yaml")
    scenarios = {
        "rows": [
            {
                "t": "LAUR",
                "scenario": "A",
                "upside": 0.12,
                "rsi": 52,
                "pct_hi": -0.07,
                "px": 28.0,
                "earnDate": "2026-10-29",
                "sector": "Consumer Defensive",
            },
            {
                "t": "CMPR",
                "scenario": "A",
                "upside": 0.12,
                "rsi": 52,
                "pct_hi": -0.07,
                "px": 98.7,
                "earnDate": "2026-10-28",
            },
            {
                "t": "FTNT",
                "scenario": "A",
                "upside": -0.05,
                "px": 160,
                "earnDate": "2026-07-29",
            },
        ]
    }
    ideas = filter_buy_ideas(book, scenarios, None)

    def fetch(t, start, end):
        if t in ("SPY", "XLP"):
            return _series(100, 102)
        return _series(50, 65)

    out = apply_buy_scores(ideas, as_of=date(2026, 8, 3), fetch_closes=fetch)
    laur = next(i for i in out if i.ticker == "LAUR")
    assert laur.bucket == "실행후보"
    assert laur.buy_score is not None
    assert laur.buy_score.l1 >= 1
    cmpr = next(i for i in out if i.ticker == "CMPR")
    assert cmpr.bucket == "금지"  # held NO_ADD after 08-03 fill
    assert cmpr.buy_score is None
    ftnt = next(i for i in out if i.ticker == "FTNT")
    assert ftnt.bucket == "금지"
    assert ftnt.buy_score is None


def test_load_guide_grades_empty(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("as_of: '2026-08-03'\ngrades: {}\n", encoding="utf-8")
    assert load_guide_grades(p) == {}
