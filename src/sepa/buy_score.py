"""실행후보 3레이어 점수표 (L1 RS · L2 점유·마진 · L3 가이드 등급).

Applied to ``실행후보`` after pick_pool ∩ timing GO
(see ``sepa.pick_pool`` / ``sepa.timing_gate`` / ``reports/BUY_SCORE_LAYERS_PLAN.md``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from sepa.share_gain import MIN_DELTA_PP, assess_share_gain

logger = logging.getLogger(__name__)

# L1 windows (trading days approx via calendar lookback)
LOOKBACK_1M_CAL = 35
LOOKBACK_3M_CAL = 100
BARS_1M = 21
BARS_3M = 63

# Sector ETF map (coarse; unknown → SPY only)
SECTOR_ETF: dict[str, str] = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Financials": "XLF",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
    "Utilities": "XLU",
}

GRADE_PATH_DEFAULT = Path("data/earn_guide_grades.yaml")


@dataclass
class BuyScore:
    ticker: str
    l1: int  # 0–2
    l2: int  # 0–2
    l3: int  # 0–1
    total: int
    recommend: str  # 1순위 | 극소/워치 | 패스 | 축소후보
    l1_note: str = ""
    l2_note: str = ""
    l3_note: str = ""
    l3_grade: str = "N/A"  # A|B|C|N/A
    pass_forced: bool = False
    rs_1m: float | None = None
    rs_3m: float | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def score_label(self) -> str:
        return f"L1={self.l1} L2={self.l2} L3={self.l3} Σ{self.total}"


def _ret(closes: list[float], bars: int) -> float | None:
    if len(closes) < bars + 1:
        return None
    a, b = closes[-(bars + 1)], closes[-1]
    if a <= 0:
        return None
    return b / a - 1.0


def _yf_closes(ticker: str, start: date, end: date) -> list[float]:
    import yfinance as yf

    df = yf.download(
        ticker,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        progress=False,
        auto_adjust=True,
    )
    if df is None or df.empty:
        return []
    close = df["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    vals = [float(x) for x in close.dropna().tolist()]
    return vals


def relative_strength(
    ticker: str,
    *,
    as_of: date,
    sector: str | None = None,
    fetch_closes=_yf_closes,
) -> tuple[float | None, float | None, str]:
    """Return (rs_1m, rs_3m, note). On failure both None."""
    start = as_of - timedelta(days=LOOKBACK_3M_CAL)
    try:
        t_closes = fetch_closes(ticker, start, as_of)
        spy_closes = fetch_closes("SPY", start, as_of)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RS fetch fail %s: %s", ticker, exc)
        return None, None, f"RS데이터실패({exc.__class__.__name__})"

    if len(t_closes) < BARS_3M + 1 or len(spy_closes) < BARS_3M + 1:
        return None, None, "RS데이터부족"

    def rs_vs(bench_closes: list[float], bars: int) -> float | None:
        tr = _ret(t_closes, bars)
        br = _ret(bench_closes, bars)
        if tr is None or br is None:
            return None
        return tr - br

    rs1 = rs_vs(spy_closes, BARS_1M)
    rs3 = rs_vs(spy_closes, BARS_3M)
    note = "vs SPY"
    etf = SECTOR_ETF.get((sector or "").strip())
    if etf:
        try:
            sec_closes = fetch_closes(etf, start, as_of)
            if len(sec_closes) >= BARS_3M + 1:
                s1 = rs_vs(sec_closes, BARS_1M)
                s3 = rs_vs(sec_closes, BARS_3M)
                # blend: average SPY-RS and sector-RS when available
                if s1 is not None and rs1 is not None:
                    rs1 = (rs1 + s1) / 2.0
                if s3 is not None and rs3 is not None:
                    rs3 = (rs3 + s3) / 2.0
                note = f"vs SPY+{etf}"
        except Exception as exc:  # noqa: BLE001
            logger.warning("sector RS fail %s %s: %s", ticker, etf, exc)
    return rs1, rs3, note


def score_l1(rs_1m: float | None, rs_3m: float | None, *, fail_neutral: bool = True) -> tuple[int, str]:
    """L1 0–2. Data failure → 1 (neutral) if fail_neutral."""
    if rs_1m is None or rs_3m is None:
        if fail_neutral:
            return 1, "RS실패→중립1"
        return 0, "RS실패→0"
    pos1 = rs_1m > 0
    pos3 = rs_3m > 0
    if pos1 and pos3:
        return 2, f"RS1M{rs_1m*100:+.1f}%·3M{rs_3m*100:+.1f}%"
    if pos1 or pos3:
        return 1, f"RS혼조 1M{rs_1m*100:+.1f}%·3M{rs_3m*100:+.1f}%"
    return 0, f"RS약세 1M{rs_1m*100:+.1f}%·3M{rs_3m*100:+.1f}%"


def score_l2(ticker: str, *, margin_delta_pp: float | None = None) -> tuple[int, str, bool]:
    """Return (score 0–2, note, exclude_exec)."""
    a = assess_share_gain(ticker, margin_delta_pp=margin_delta_pp)
    if a.cancelled_margin:
        return 0, a.strat_note or "점유↑·마진악화→실행제외", True
    if not a.rising or a.delta_pp is None:
        if get_profile_missing(ticker):
            return 0, "점유프로필없음", False
        return 0, f"점유Δ{a.delta_pp:+.1f}pp" if a.delta_pp is not None else "점유비가산", False
    if a.margin_hold is True:
        return 2, f"점유+{a.delta_pp:.1f}pp·마진유지", False
    # rising, margin unknown
    return 1, f"점유+{a.delta_pp:.1f}pp·마진미상", False


def get_profile_missing(ticker: str) -> bool:
    from sepa.rev_compete import get_profile

    return get_profile(ticker) is None


def load_guide_grades(path: str | Path = GRADE_PATH_DEFAULT) -> dict[str, dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return {}
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    grades = raw.get("grades") or {}
    out: dict[str, dict[str, Any]] = {}
    for k, v in grades.items():
        if isinstance(v, str):
            out[str(k).upper()] = {"grade": v.upper(), "note": ""}
        elif isinstance(v, dict):
            out[str(k).upper()] = {
                "grade": str(v.get("grade") or "N/A").upper(),
                "note": str(v.get("note") or ""),
                "graded_on": v.get("graded_on"),
                "earn_date": v.get("earn_date"),
            }
    return out


def score_l3(
    ticker: str,
    *,
    as_of: date,
    earn_date: date | None,
    grades: dict[str, dict[str, Any]],
) -> tuple[int, str, str, bool]:
    """Return (score 0–1, note, grade, shrink_track).

    Only applies D+1..D+3 after earn_date. Otherwise N/A → 0 neutral.
    Grade C → shrink track (not an exec add).
    """
    g = grades.get(ticker.upper())
    if earn_date is None:
        return 0, "L3 N/A(실적일없음)", "N/A", False
    d1 = earn_date + timedelta(days=1)
    d3 = earn_date + timedelta(days=3)
    in_window = d1 <= as_of <= d3
    if not g:
        if in_window:
            return 0, "L3 등급미입력(D+1~3)", "N/A", False
        return 0, "L3 N/A", "N/A", False
    grade = str(g.get("grade") or "N/A").upper()
    note = str(g.get("note") or "")
    if grade == "C":
        return 0, f"가이드C·축소후보 {note}".strip(), "C", True
    if not in_window and grade in ("A", "B", "C"):
        # grade exists but outside window → still show, limited score only in window
        return 0, f"L3 {grade}(창밖) {note}".strip(), grade, grade == "C"
    if grade == "A":
        return 1, f"가이드A {note}".strip(), "A", False
    if grade == "B":
        return 0, f"가이드B {note}".strip(), "B", False
    return 0, f"L3 {grade}", grade, False


def recommend_from_scores(
    *,
    l1: int,
    l2: int,
    total: int,
    pass_forced: bool,
    shrink: bool,
) -> str:
    if shrink:
        return "축소후보"
    if pass_forced or l1 == 0:
        return "패스"
    if total >= 4:
        return "1순위"
    if total >= 2:
        return "극소/워치"
    return "패스"


def score_ticker(
    ticker: str,
    *,
    as_of: date,
    sector: str | None = None,
    earn_date: date | str | None = None,
    margin_delta_pp: float | None = None,
    grades: dict[str, dict[str, Any]] | None = None,
    fetch_closes=None,
    fail_neutral: bool = True,
) -> BuyScore:
    t = ticker.upper()
    ed: date | None
    if isinstance(earn_date, date):
        ed = earn_date
    elif earn_date:
        ed = date.fromisoformat(str(earn_date)[:10])
    else:
        ed = None

    if fetch_closes is None:
        rs1, rs3, rs_note = relative_strength(t, as_of=as_of, sector=sector)
    else:
        rs1, rs3, rs_note = relative_strength(
            t, as_of=as_of, sector=sector, fetch_closes=fetch_closes
        )
    l1, l1_note = score_l1(rs1, rs3, fail_neutral=fail_neutral)
    if rs_note and "실패" not in l1_note and "부족" not in (rs_note or ""):
        l1_note = f"{l1_note}·{rs_note}"
    elif rs1 is None:
        l1_note = f"{l1_note}·{rs_note}"

    l2, l2_note, excl = score_l2(t, margin_delta_pp=margin_delta_pp)
    l3, l3_note, grade, shrink = score_l3(
        t, as_of=as_of, earn_date=ed, grades=grades or {}
    )
    pass_forced = bool(excl or l1 == 0)
    if excl:
        total = 0
    else:
        total = int(l1 + l2 + l3)
    rec = recommend_from_scores(
        l1=l1, l2=l2, total=total, pass_forced=pass_forced or excl, shrink=shrink
    )
    return BuyScore(
        ticker=t,
        l1=l1,
        l2=l2,
        l3=l3,
        total=total if not excl else 0,
        recommend=rec,
        l1_note=l1_note,
        l2_note=l2_note,
        l3_note=l3_note,
        l3_grade=grade,
        pass_forced=pass_forced or excl,
        rs_1m=rs1,
        rs_3m=rs3,
    )


def score_buy_ideas(
    ideas: list[Any],
    *,
    as_of: date,
    sectors: dict[str, str] | None = None,
    grades_path: str | Path = GRADE_PATH_DEFAULT,
    fetch_closes=None,
    margin_by_ticker: dict[str, float] | None = None,
) -> list[tuple[Any, BuyScore | None]]:
    """Attach BuyScore to 실행후보; others get None. Re-sort 실행후보 by total."""
    grades = load_guide_grades(grades_path)
    sectors = sectors or {}
    margin_by_ticker = margin_by_ticker or {}
    scored: list[tuple[Any, BuyScore | None]] = []
    exec_rows: list[tuple[Any, BuyScore]] = []
    other: list[tuple[Any, BuyScore | None]] = []

    for idea in ideas:
        bucket = getattr(idea, "bucket", None) or (idea.get("bucket") if isinstance(idea, dict) else None)
        ticker = getattr(idea, "ticker", None) or (idea.get("ticker") if isinstance(idea, dict) else "")
        ticker = str(ticker).upper()
        if bucket != "실행후보":
            other.append((idea, None))
            continue
        earn = getattr(idea, "earn_date", None) or (
            idea.get("earn_date") if isinstance(idea, dict) else None
        )
        sc = score_ticker(
            ticker,
            as_of=as_of,
            sector=sectors.get(ticker),
            earn_date=earn,
            margin_delta_pp=margin_by_ticker.get(ticker),
            grades=grades,
            fetch_closes=fetch_closes,
        )
        # demote display bucket suggestion via recommend
        exec_rows.append((idea, sc))

    exec_rows.sort(
        key=lambda pair: (
            -(pair[1].total),
            -(getattr(pair[0], "upside", None) or (pair[0].get("upside") if isinstance(pair[0], dict) else 0) or 0),
            0 if str(getattr(pair[0], "scenario", "") or "").upper().startswith("A") else 1,
            pair[1].ticker,
        )
    )
    scored.extend(exec_rows)
    # keep watch/ban order stable
    order = {"워치": 0, "금지": 1}
    other.sort(
        key=lambda pair: (
            order.get(getattr(pair[0], "bucket", "") or "", 9),
            getattr(pair[0], "ticker", "") or "",
        )
    )
    scored.extend(other)
    return scored


def top_exec_recommendation(scored: list[tuple[Any, BuyScore | None]]) -> BuyScore | None:
    for _idea, sc in scored:
        if sc is None:
            continue
        if sc.recommend == "1순위":
            return sc
    # else first non-pass exec
    for _idea, sc in scored:
        if sc is None:
            continue
        if sc.recommend in ("1순위", "극소/워치"):
            return sc
    return None
