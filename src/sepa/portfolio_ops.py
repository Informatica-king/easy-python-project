"""포폴() — portfolio ops brief: weights, events, buy filter, week plan.

Consumes ``config/portfolio_watch.yaml`` (SSOT) + latest deep-analysis artifacts.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

D5_WINDOW_DAYS = 5
CORE_TARGET = 0.20
CORE_OVER = 0.25
SAT_MAX = 0.10
SAT_SOFT = 0.12
SCHD_TARGET = 0.10
FRESH_DAYS = 5
BENCH = ("QQQ", "SPY")


@dataclass
class HoldingRow:
    ticker: str
    shares: float
    cost: float | None
    sleeve: str
    stop: float | None = None
    tp1: float | None = None
    tp2: float | None = None
    no_add: bool = False
    earn_date: date | None = None
    band: tuple[float, float] | None = None
    invalidation: float | None = None
    note: str = ""
    # filled at enrich
    px: float | None = None
    value: float | None = None
    w_stock: float | None = None
    w_liquid: float | None = None
    pnl_usd: float | None = None
    pnl_pct: float | None = None
    stance: str = ""
    earn_d5: bool = False
    d5_start: date | None = None


@dataclass
class PortfolioBook:
    as_of: date
    source: str
    cash_usd: float
    cash_floor_usd: float
    cash_krw: float | None
    note: str
    holdings: list[HoldingRow]
    pending_note: str = ""
    equity_usd: float = 0.0
    liquid_usd: float = 0.0
    cash_pct: float = 0.0
    risks: list[str] = field(default_factory=list)
    forbid: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    ops_date: date | None = None  # 실행일(스텐스·계획·D5). None이면 as_of
    identity: str = ""
    identity_short: str = ""

    @property
    def effective_date(self) -> date:
        return self.ops_date or self.as_of


@dataclass
class BuyIdea:
    ticker: str
    bucket: str  # 실행후보 | 워치 | 금지
    scenario: str
    reason: str
    px: float | None = None
    upside: float | None = None
    earn_date: str | None = None
    chase: str | None = None
    sector: str | None = None
    # filled by buy_score layer
    buy_score: Any = None
    score_recommend: str | None = None


def _parse_date(raw: Any) -> date | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(str(raw)[:10])


def load_portfolio_yaml(path: str | Path = "config/portfolio_watch.yaml") -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"portfolio snap missing: {p}")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def load_book(path: str | Path = "config/portfolio_watch.yaml") -> PortfolioBook:
    raw = load_portfolio_yaml(path)
    as_of = _parse_date(raw.get("as_of")) or date.today()
    cash_block = raw.get("cash") or {}
    book_block = (raw.get("strategy") or {}).get("book") or {}
    cash_usd = float(cash_block.get("usd") or book_block.get("cash_usd") or 0.0)
    floor = float(cash_block.get("floor_usd") or book_block.get("cash_floor_usd") or 150.0)
    cash_krw = cash_block.get("krw")
    if cash_krw is not None:
        cash_krw = float(cash_krw)
    holdings: list[HoldingRow] = []
    for h in raw.get("holdings") or []:
        if not h or h.get("role") == "exited":
            continue
        if h.get("pending_sell"):
            continue
        band = h.get("band")
        band_t = None
        if isinstance(band, (list, tuple)) and len(band) == 2:
            band_t = (float(band[0]), float(band[1]))
        holdings.append(
            HoldingRow(
                ticker=str(h["ticker"]).upper(),
                shares=float(h.get("shares") or 0),
                cost=float(h["cost_approx"]) if h.get("cost_approx") is not None else None,
                sleeve=str(h.get("sleeve") or "hold"),
                stop=float(h["stop"]) if h.get("stop") is not None else None,
                tp1=float(h["tp1"]) if h.get("tp1") is not None else None,
                tp2=float(h["tp2"]) if h.get("tp2") is not None else None,
                no_add=bool(h.get("no_add")),
                earn_date=_parse_date(h.get("earn_date")),
                band=band_t,
                invalidation=float(h["invalidation"]) if h.get("invalidation") is not None else None,
                note=str(h.get("note") or ""),
            )
        )
    pending = ""
    if book_block.get("pending_orders_note"):
        pending = str(book_block["pending_orders_note"])
    strat = raw.get("strategy") or {}
    return PortfolioBook(
        as_of=as_of,
        source=str(raw.get("source") or raw.get("as_of_note") or path),
        cash_usd=cash_usd,
        cash_floor_usd=floor,
        cash_krw=cash_krw,
        note=str(raw.get("as_of_note") or ""),
        holdings=holdings,
        pending_note=pending,
        identity=str(strat.get("identity") or ""),
        identity_short=str(strat.get("identity_short") or ""),
    )


def _last_close(ticker: str) -> float | None:
    try:
        import yfinance as yf

        tk = yf.Ticker(ticker)
        info = tk.info or {}
        px = info.get("currentPrice") or info.get("regularMarketPrice")
        if px is not None:
            return float(px)
        hist = tk.history(period="5d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as exc:  # noqa: BLE001
        logger.warning("price fail %s: %s", ticker, exc)
    return None


def enrich_marks(
    book: PortfolioBook,
    *,
    use_snap_marks: bool = True,
    ops_date: date | None = None,
) -> PortfolioBook:
    """Fill px/value/weights/pnl. Prefer live last; fall back to yaml mark via value/shares."""
    if ops_date is not None:
        book.ops_date = ops_date
    elif book.ops_date is None:
        book.ops_date = date.today()
    asof = book.effective_date
    raw = load_portfolio_yaml()
    snap_marks = {
        str(h["ticker"]).upper(): float(h["mark_approx"])
        for h in (raw.get("holdings") or [])
        if h.get("mark_approx") is not None
    }
    for h in book.holdings:
        live = _last_close(h.ticker)
        if live is not None:
            h.px = live
        elif use_snap_marks and h.ticker in snap_marks:
            h.px = snap_marks[h.ticker]
        if h.px is None:
            continue
        h.value = h.px * h.shares
        if h.cost is not None:
            basis = h.cost * h.shares
            h.pnl_usd = h.value - basis
            h.pnl_pct = h.value / basis - 1.0 if basis else None

    equity = sum(h.value or 0.0 for h in book.holdings)
    liquid = equity + book.cash_usd
    book.equity_usd = equity
    book.liquid_usd = liquid
    book.cash_pct = (book.cash_usd / liquid) if liquid else 0.0
    for h in book.holdings:
        if h.value is None:
            continue
        h.w_stock = h.value / equity if equity else 0.0
        h.w_liquid = h.value / liquid if liquid else 0.0
        h.stance = stance_for(h, asof)
        if h.earn_date:
            h.d5_start = h.earn_date - timedelta(days=D5_WINDOW_DAYS - 1)
            h.earn_d5 = h.d5_start <= asof <= h.earn_date
    book.risks = build_risks(book)
    book.forbid = build_forbid(book)
    book.actions = build_actions(book, ideas=None)
    return book


def in_earn_d5(earn: date | None, as_of: date) -> bool:
    if earn is None:
        return False
    start = earn - timedelta(days=D5_WINDOW_DAYS - 1)
    return start <= as_of <= earn


def stance_for(h: HoldingRow, as_of: date) -> str:
    bits: list[str] = []
    if h.px is not None and h.stop is not None and h.px <= h.stop:
        bits.append("STOP근접·축소검토")
    elif h.px is not None and h.stop is not None and h.px <= h.stop * 1.03:
        bits.append("stop경계")
    if in_earn_d5(h.earn_date, as_of):
        bits.append("EARN_D5·추가금지")
    if h.no_add:
        bits.append("NO_ADD")
    if h.w_stock is not None:
        if h.sleeve in ("core", "core_phase1") and h.w_stock >= CORE_OVER:
            bits.append("코어OVER")
        elif h.sleeve in ("core", "core_phase1") and h.w_stock > CORE_TARGET:
            bits.append("코어상단")
        elif h.sleeve == "satellite" and h.w_stock >= SAT_SOFT:
            bits.append("위성OVER")
        elif h.sleeve == "satellite" and h.w_stock > SAT_MAX:
            bits.append("위성상단")
        elif h.sleeve == "buffer" and h.w_stock > SCHD_TARGET + 0.03:
            bits.append("완충과다")
    if h.px is not None and h.tp1 is not None and h.px >= h.tp1:
        bits.append("TP1·익절검토")
    if not bits:
        bits.append("홀드")
    return " · ".join(bits)


def build_risks(book: PortfolioBook) -> list[str]:
    out: list[str] = []
    if book.cash_usd < book.cash_floor_usd:
        out.append(f"현금 ${book.cash_usd:.0f} < 바닥 ${book.cash_floor_usd:.0f}")
    elif book.cash_usd < book.cash_floor_usd + 50:
        out.append(f"현금 여유 얇음 (바닥+50 미만)")
    for h in book.holdings:
        if h.earn_d5:
            out.append(f"{h.ticker} EARN_D5 (~{h.earn_date})")
        if h.px is not None and h.stop is not None and h.px <= h.stop * 1.03:
            out.append(f"{h.ticker} stop경계 (${h.stop:g})")
        if h.w_stock and h.sleeve in ("core", "core_phase1") and h.w_stock >= CORE_OVER:
            out.append(f"{h.ticker} 코어과비중 {h.w_stock*100:.1f}%")
        if h.w_stock and h.sleeve == "satellite" and h.w_stock > SAT_MAX:
            out.append(f"{h.ticker} 위성한도 {h.w_stock*100:.1f}%")
    if book.pending_note:
        out.append(book.pending_note)
    return out


def build_forbid(book: PortfolioBook) -> list[str]:
    out = ["물타기 금지", "실적 갭 추격 금지", "현금바닥 $150 이하 매수 금지"]
    for h in book.holdings:
        if h.no_add or h.earn_d5:
            out.append(f"{h.ticker} 추가금지")
    return out


def build_actions(book: PortfolioBook, ideas: list[BuyIdea] | None = None) -> list[str]:
    do_list: list[str] = []
    dont: list[str] = []
    nxt: list[str] = []
    asof = book.effective_date
    earn_soon = [h for h in book.holdings if h.earn_date and 0 <= (h.earn_date - asof).days <= 7]
    if earn_soon:
        names = ", ".join(f"{h.ticker}({h.earn_date})" for h in sorted(earn_soon, key=lambda x: x.earn_date or asof))
        do_list.append(f"실적 임박 홀드·관망: {names}")
    else:
        do_list.append("보유 6~7종 stop·비중만 점검")

    top = None
    if ideas:
        from sepa.buy_score import top_exec_recommendation

        scored_pairs = [(i, i.buy_score) for i in ideas if i.buy_score is not None]
        top = top_exec_recommendation(scored_pairs) if scored_pairs else None
    if top and top.recommend == "1순위":
        do_list.append(f"실행 1순위: {top.ticker} ({top.score_label})")
    elif top and top.recommend == "극소/워치":
        do_list.append(f"실행 약한후보: {top.ticker} ({top.score_label}) · 극소만")
    else:
        do_list.append("이번 주 실행 1순위 없음 (점수·게이트)")

    dont.append("EARN_D5·NO_ADD 종목 추가/물타기")
    dont.append("L1=0·마진악화·과열·업사이드 음수 추격")
    if any(h.earn_date for h in book.holdings):
        nxt.append("실적 D+1~D+3: data/earn_guide_grades.yaml 등급 입력")
    nxt.append("A′ 실행은 total≥2·실적창 밖·위성한도·현금여유 확인 후")
    return [
        "할 일: " + " · ".join(do_list),
        "하지 말 일: " + " · ".join(dont),
        "다음 체크: " + " · ".join(nxt),
    ]


def latest_json(report_dir: str | Path, prefix: str) -> Path | None:
    d = Path(report_dir)
    files = sorted(d.glob(f"{prefix}*.json"), key=lambda p: p.name, reverse=True)
    return files[0] if files else None


def load_buy_scenarios(report_dir: str | Path = "reports") -> tuple[dict[str, Any] | None, Path | None]:
    path = latest_json(report_dir, "buy_scenarios_")
    if not path:
        return None, None
    return json.loads(path.read_text(encoding="utf-8")), path


def load_chase(report_dir: str | Path = "reports") -> tuple[dict[str, Any] | None, Path | None]:
    path = latest_json(report_dir, "chase_rr_")
    if not path:
        return None, None
    return json.loads(path.read_text(encoding="utf-8")), path


def freshness_warning(as_of_s: str | None, today: date, *, max_days: int = FRESH_DAYS) -> str | None:
    if not as_of_s:
        return "심층/매수시나리오 파일 없음 — 매수고려 신뢰↓"
    try:
        d = date.fromisoformat(str(as_of_s)[:10])
    except ValueError:
        return "심층 as_of 파싱 실패"
    delta = (today - d).days
    if delta > max_days:
        return f"심층 데이터 {delta}일 전({d}) — 매수고려 신뢰↓"
    return None


def filter_buy_ideas(
    book: PortfolioBook,
    scenarios: dict[str, Any] | None,
    chase: dict[str, Any] | None,
) -> list[BuyIdea]:
    held = {h.ticker for h in book.holdings}
    no_add = {h.ticker for h in book.holdings if h.no_add}
    chase_map = {}
    if chase:
        for r in chase.get("rows") or []:
            t = str(r.get("ticker") or r.get("t") or "").upper()
            if t:
                chase_map[t] = r

    ideas: list[BuyIdea] = []
    rows = (scenarios or {}).get("rows") or []
    for r in rows:
        t = str(r.get("t") or "").upper()
        if not t:
            continue
        scen = str(r.get("scenario") or "")
        ups = r.get("upside")
        earn = r.get("earnDate") or r.get("earn_date")
        chase_lab = (chase_map.get(t) or {}).get("chase") or ""
        px = r.get("last") or r.get("px")
        reason_bits = [f"{scen}"]
        if ups is not None:
            reason_bits.append(f"업사이드 {float(ups)*100:+.1f}%")
        if r.get("rsi") is not None:
            reason_bits.append(f"RSI{float(r['rsi']):.0f}")
        if r.get("pct_hi") is not None:
            reason_bits.append(f"고점{float(r['pct_hi'])*100:+.1f}%")

        bucket = "워치"
        reason = " · ".join(reason_bits)

        if t in held and t in no_add:
            bucket = "금지"
            reason = f"보유·NO_ADD · {reason}"
        elif in_earn_d5(_parse_date(earn), book.effective_date):
            bucket = "금지"
            reason = f"EARN_D5 · {reason}"
        elif any(x in str(chase_lab) for x in ("과열", "매도", "중하", "하·")):
            bucket = "금지"
            reason = f"Chase {chase_lab} · {reason}"
        elif ups is not None and float(ups) < 0:
            bucket = "금지"
            reason = f"업사이드 음수 · {reason}"
        elif scen in ("A", "A'", "B"):
            bucket = "실행후보"
            reason = f"게이트통과 · {reason}"
        elif scen == "SOFT":
            bucket = "워치"
            reason = f"SOFT 근접 · {reason}"
        else:
            bucket = "워치"

        ideas.append(
            BuyIdea(
                ticker=t,
                bucket=bucket,
                scenario=scen,
                reason=reason,
                px=float(px) if px is not None else None,
                upside=float(ups) if ups is not None else None,
                earn_date=str(earn)[:10] if earn else None,
                chase=str(chase_lab) if chase_lab else None,
                sector=str(r.get("sector") or "") or None,
            )
        )

    order = {"실행후보": 0, "워치": 1, "금지": 2}
    ideas.sort(key=lambda x: (order.get(x.bucket, 9), x.ticker))
    return ideas


def apply_buy_scores(
    ideas: list[BuyIdea],
    *,
    as_of: date,
    grades_path: str | Path = "data/earn_guide_grades.yaml",
    fetch_closes=None,
) -> list[BuyIdea]:
    """Score 실행후보 (L1/L2/L3) and re-order; attach score on each idea."""
    from sepa.buy_score import score_buy_ideas

    sectors = {i.ticker: (i.sector or "") for i in ideas if i.sector}
    scored = score_buy_ideas(
        ideas,
        as_of=as_of,
        sectors=sectors,
        grades_path=grades_path,
        fetch_closes=fetch_closes,
    )
    out: list[BuyIdea] = []
    for idea, sc in scored:
        if sc is not None:
            idea.buy_score = sc
            idea.score_recommend = sc.recommend
            if sc.recommend == "패스" and idea.bucket == "실행후보":
                idea.reason = f"{idea.reason} · 점수패스({sc.score_label})"
            elif sc.recommend == "1순위":
                idea.reason = f"{idea.reason} · 1순위({sc.score_label})"
            elif sc.recommend == "극소/워치":
                idea.reason = f"{idea.reason} · 극소({sc.score_label})"
            elif sc.recommend == "축소후보":
                idea.bucket = "워치"
                idea.reason = f"가이드C·축소 · {idea.reason}"
        out.append(idea)
    return out


def week_plan_mode(as_of: date) -> str:
    """fri/sat/sun → next_week; else → next_5bd."""
    if as_of.weekday() >= 4:  # Fri=4, Sat=5, Sun=6
        return "next_week"
    return "next_5bd"


def build_ops_plan(book: PortfolioBook, ideas: list[BuyIdea]) -> list[str]:
    asof = book.effective_date
    mode = week_plan_mode(asof)
    lines: list[str] = []
    if mode == "next_week":
        lines.append("모드: 금·토·일 → 차주(월~금) 운영계획")
        lines.append("월~화: 실적 임박 보유 관망 · 신규 기본 OFF")
        earn = sorted(
            [h for h in book.holdings if h.earn_date and asof <= h.earn_date <= asof + timedelta(days=7)],
            key=lambda h: h.earn_date or asof,
        )
        for h in earn:
            lines.append(f"  · {h.earn_date}: {h.ticker} 실적 — 홀드, 갭추격 금지")
        lines.append("수~목: 실적 숫자 확인 후 홀드/축소만 (추가·물타기 금지)")
        lines.append("금: A′ 재점검 · 주간 마무리")
    else:
        lines.append("모드: 월~목 → 향후 5영업일 브리프")
        lines.append("보유 stop·EARN_D5만 매일 확인 · 신규는 실행후보만")
        earn = sorted(
            [h for h in book.holdings if h.earn_date and asof <= h.earn_date <= asof + timedelta(days=5)],
            key=lambda h: h.earn_date or asof,
        )
        for h in earn:
            lines.append(f"  · {h.earn_date}: {h.ticker} — 홀드, 갭추격 금지")
    execs = [i for i in ideas if i.bucket == "실행후보"]
    ranked = [i for i in execs if i.buy_score and i.score_recommend in ("1순위", "극소/워치")]
    if ranked:
        top = ranked[0]
        sc = top.buy_score
        lines.append(
            f"매수 예외: {top.ticker}({top.scenario}) 권고={sc.recommend} Σ{sc.total} "
            f"— 실적창 밖·소액·추격금지"
        )
        others = [i.ticker for i in ranked[1:3]]
        if others:
            lines.append("차순위: " + ", ".join(others))
    elif execs:
        lines.append("매수 예외: 실행후보 있으나 점수 패스(L1=0/마진악화/Σ낮음) → 이번 주 신규 0")
    else:
        lines.append("매수 예외: 없음 (기본 신규 0)")
    lines.append("금지: 코어/위성 NO_ADD · 과열 · 업사이드 음수 · 현금바닥 파괴 · L1=0")
    return lines


def fetch_bench_series(
    tickers: list[str],
    start: date,
    end: date | None = None,
) -> dict[str, list[tuple[date, float]]]:
    """Daily close series for portfolio tickers + benches from start."""
    import yfinance as yf
    import pandas as pd

    end = end or date.today()
    out: dict[str, list[tuple[date, float]]] = {}
    for t in tickers:
        try:
            df = yf.download(t, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(), progress=False, auto_adjust=True)
            if df is None or df.empty:
                continue
            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            series = []
            for idx, val in close.items():
                d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
                if val == val:  # not NaN
                    series.append((d, float(val)))
            if series:
                out[t] = series
        except Exception as exc:  # noqa: BLE001
            logger.warning("bench series fail %s: %s", t, exc)
    return out


def portfolio_index(
    book: PortfolioBook,
    series: dict[str, list[tuple[date, float]]],
) -> list[tuple[date, float]]:
    """Buy&hold quantity-weighted index, start=100 at first common date ≥ as_of-lookback.
    Uses current shares; cash excluded.
    """
    # Use last ~60 trading days ending today; normalize at first date where all held names exist
    held = [h for h in book.holdings if h.ticker in series and h.shares > 0]
    if not held:
        return []
    # align dates
    date_sets = [set(d for d, _ in series[h.ticker]) for h in held]
    common = set.intersection(*date_sets) if date_sets else set()
    if not common:
        return []
    days = sorted(d for d in common if d >= (book.as_of - timedelta(days=90)))
    if len(days) < 2:
        days = sorted(common)[-60:]
    if not days:
        return []
    px0 = {h.ticker: dict(series[h.ticker])[days[0]] for h in held}
    base = sum(h.shares * px0[h.ticker] for h in held)
    if base <= 0:
        return []
    out = []
    for d in days:
        val = sum(h.shares * dict(series[h.ticker])[d] for h in held)
        out.append((d, 100.0 * val / base))
    return out


def normalize_series(series: list[tuple[date, float]], start: date) -> list[tuple[date, float]]:
    pts = [(d, v) for d, v in series if d >= start]
    if not pts:
        pts = list(series)
    if not pts:
        return []
    base = pts[0][1]
    if base <= 0:
        return []
    return [(d, 100.0 * v / base) for d, v in pts]
