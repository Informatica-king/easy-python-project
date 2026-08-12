"""포폴() — portfolio ops brief: weights, events, buy filter, week plan.

Buy filter (2026-08): pick_pool (Chase) x timing_gate (GO) -> 실행후보.
See ``reports/BUY_SIGNAL_REDESIGN.md``.

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
FRESH_DAYS = 5
BENCH = ("QQQ", "SPY")


@dataclass
class HoldingRow:
    ticker: str
    shares: float
    cost: float | None
    grade: str = "C"  # effective after enrich; yaml quality before
    max_pct: float = 0.06  # effective ADD cap (0 if 금지)
    quality_grade: str = "C"
    quality_max_pct: float = 0.06
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
    grade_reasons: list[str] = field(default_factory=list)

    @property
    def grade_label(self) -> str:
        """Display: quality→effective · structural max%."""
        q = self.quality_grade or self.grade
        if self.grade == "금지" and q != "금지":
            return f"{q}→금지·구조{self.quality_max_pct*100:.0f}%"
        return f"{self.grade}·맥스{self.max_pct*100:.0f}%"


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
    fx_krw_per_usd: float | None = None
    cash_krw_usd: float = 0.0  # KRW cash converted at snap FX
    risks: list[str] = field(default_factory=list)
    forbid: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    ops_date: date | None = None  # 실행일(스텐스·계획·D5). None이면 as_of
    identity: str = ""
    identity_short: str = ""

    @property
    def effective_date(self) -> date:
        return self.ops_date or self.as_of

    @property
    def cash_total_usd(self) -> float:
        """USD cash + KRW cash (FX-converted)."""
        return float(self.cash_usd or 0.0) + float(self.cash_krw_usd or 0.0)


@dataclass
class BuyIdea:
    ticker: str
    bucket: str  # 실행후보 | 워치 | 금지
    scenario: str  # legacy A|B|SOFT or timing status
    reason: str
    px: float | None = None
    upside: float | None = None
    earn_date: str | None = None
    chase: str | None = None
    sector: str | None = None
    # pick × timing (2026-08 redesign)
    pick_rank: int | None = None
    timing: str | None = None  # GO_A | GO_B | WAIT | BLOCK
    limit_hint: str | None = None  # soldier premkt execution card
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
    fx = raw.get("fx_krw_per_usd")
    fx_f = float(fx) if fx is not None else None
    cash_krw_usd = 0.0
    if cash_krw and fx_f and fx_f > 0:
        cash_krw_usd = float(cash_krw) / fx_f
    from sepa.position_grade import GRADE_MAX

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
        q_raw = str(h.get("grade") or h.get("quality_grade") or "C").strip()
        q = q_raw.upper() if q_raw != "금지" else "금지"
        if q not in ("A", "B", "C", "금지"):
            q = "C"
        if h.get("max_pct") is not None:
            q_max = float(h["max_pct"])
            if q_max > 1.0:  # yaml stores 18 not 0.18
                q_max /= 100.0
        else:
            q_max = GRADE_MAX.get(q if q != "금지" else "C", 0.06)
        holdings.append(
            HoldingRow(
                ticker=str(h["ticker"]).upper(),
                shares=float(h.get("shares") or 0),
                cost=float(h["cost_approx"]) if h.get("cost_approx") is not None else None,
                grade=q,
                max_pct=q_max,
                quality_grade=q if q != "금지" else "C",
                quality_max_pct=q_max if q != "금지" else GRADE_MAX["C"],
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
        fx_krw_per_usd=fx_f,
        cash_krw_usd=cash_krw_usd,
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
    cash_total = book.cash_total_usd
    liquid = equity + cash_total
    book.equity_usd = equity
    book.liquid_usd = liquid
    book.cash_pct = (cash_total / liquid) if liquid else 0.0
    for h in book.holdings:
        if h.value is not None and equity:
            h.w_stock = h.value / equity
            h.w_liquid = h.value / liquid if liquid else 0.0
        if h.earn_date:
            h.d5_start = h.earn_date - timedelta(days=D5_WINDOW_DAYS - 1)
            h.earn_d5 = h.d5_start <= asof <= h.earn_date
        apply_holding_grade(h)
        h.stance = stance_for(h, asof)
    book.risks = build_risks(book)
    book.forbid = build_forbid(book)
    book.actions = build_actions(book, ideas=None)
    return book


def apply_holding_grade(h: HoldingRow, sc: Any | None = None) -> HoldingRow:
    """Set effective grade from yaml quality + hard gates (+ optional BuyScore)."""
    from sepa.position_grade import GRADE_MAX, assign_from_buy_score, assign_position_grade

    has_stop = h.stop is not None or h.invalidation is not None
    if sc is not None:
        pg = assign_from_buy_score(
            sc,
            earn_d5=h.earn_d5,
            no_add=h.no_add,
            has_stop=has_stop,
            yaml_grade=h.quality_grade,
        )
    else:
        pg = assign_position_grade(
            earn_d5=h.earn_d5,
            no_add=h.no_add,
            has_stop=has_stop,
            yaml_grade=h.quality_grade,
        )
    h.quality_grade = pg.quality_grade
    h.quality_max_pct = GRADE_MAX.get(pg.quality_grade, h.quality_max_pct)
    h.grade = pg.grade
    h.max_pct = pg.max_pct
    h.grade_reasons = list(pg.reasons)
    return h


def in_earn_d5(earn: date | None, as_of: date) -> bool:
    if earn is None:
        return False
    start = earn - timedelta(days=D5_WINDOW_DAYS - 1)
    return start <= as_of <= earn


def stance_for(h: HoldingRow, as_of: date) -> str:
    from sepa.position_grade import weight_status

    bits: list[str] = []
    if h.px is not None and h.stop is not None and h.px <= h.stop:
        bits.append("STOP근접·축소검토")
    elif h.px is not None and h.stop is not None and h.px <= h.stop * 1.03:
        bits.append("stop경계")
    if in_earn_d5(h.earn_date, as_of):
        bits.append("EARN_D5·추가금지")
    if h.no_add:
        bits.append("NO_ADD")
    if h.grade == "금지":
        bits.append("유효금지")
    if h.w_stock is not None:
        # OVER vs structural (quality) cap — not the effective ADD=0 cap
        ws = weight_status(h.w_stock, h.quality_max_pct)
        if ws:
            bits.append(ws)
    if h.px is not None and h.tp1 is not None and h.px >= h.tp1:
        bits.append("TP1·익절검토")
    if not bits:
        bits.append("홀드")
    return " · ".join(bits)


def build_risks(book: PortfolioBook) -> list[str]:
    from sepa.position_grade import top3_over_cap, weight_status

    out: list[str] = []
    cash_tot = book.cash_total_usd
    if cash_tot < book.cash_floor_usd:
        out.append(f"현금 ${cash_tot:.0f} < 바닥 ${book.cash_floor_usd:.0f}")
    elif cash_tot < book.cash_floor_usd + 50:
        out.append(f"현금 여유 얇음 (바닥+50 미만)")
    for h in book.holdings:
        if h.earn_d5:
            out.append(f"{h.ticker} EARN_D5 (~{h.earn_date})")
        if h.px is not None and h.stop is not None and h.px <= h.stop * 1.03:
            out.append(f"{h.ticker} stop경계 (${h.stop:g})")
        if h.w_stock is not None:
            ws = weight_status(h.w_stock, h.quality_max_pct)
            if ws:
                out.append(
                    f"{h.ticker} {ws} {h.w_stock*100:.1f}% "
                    f"(품질{h.quality_grade}≤{h.quality_max_pct*100:.0f}%)"
                )
    weights = [h.w_stock for h in book.holdings if h.w_stock is not None]
    if top3_over_cap(weights):
        top3 = sorted(weights, reverse=True)[:3]
        out.append(f"Top3 합 {sum(top3)*100:.1f}% > 50%")
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
    exec_go = [i for i in (ideas or []) if i.bucket == "실행후보"]
    if top and top.recommend == "1순위":
        do_list.append(f"실행 1순위: {top.ticker} ({top.score_label})")
    elif top and top.recommend == "극소/워치":
        do_list.append(f"실행 약한후보: {top.ticker} ({top.score_label}) · 극소만")
    elif exec_go:
        do_list.append(f"본선∩GO: {exec_go[0].ticker}" + (f" · {exec_go[0].limit_hint}" if exec_go[0].limit_hint else ""))
    else:
        do_list.append("이번 주 실행 없음 (본선∩타이밍GO 공집합) → 현금 유지")

    # Soldier premkt card (KR 17:30–20:55 = US pre-market)
    if exec_go and exec_go[0].limit_hint:
        do_list.append(f"저녁창 주문: {exec_go[0].ticker} {exec_go[0].limit_hint}")

    dont.append("확정 EARN_D5·NO_ADD 추가/물타기 · 시장가·돌파추격")
    dont.append("L1=0·마진악화·과열·업사이드 음수 · 갭상한 초과(VOID)")
    if any(h.earn_date for h in book.holdings):
        nxt.append("실적 D+1~D+3: data/earn_guide_grades.yaml 등급 입력")
    nxt.append("본선(Chase)→타이밍GO→17:30~20:55 지정가 · 미체결 억지추격 금지")
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


def _limit_hint(px: float | None, *, ceiling_pct: float = 0.015) -> str | None:
    """Soldier premkt card: limit ≤ prior close × (1+ceiling), C-size 1sh."""
    if px is None or px <= 0:
        return None
    ceil = px * (1.0 + ceiling_pct)
    return f"지정가≤${ceil:.2f}(종가+{ceiling_pct*100:.1f}%) · 1주 · 시장가금지 · 갭+2% VOID"


def filter_buy_ideas(
    book: PortfolioBook,
    scenarios: dict[str, Any] | None,
    chase: dict[str, Any] | None,
) -> list[BuyIdea]:
    """Buy ideas = pick_pool (좋은 종목) ∩ timing (GO/WAIT/BLOCK).

    Pipeline (2026-08 redesign):
    1. Pick pool from Chase (fallback: scenario rows)
    2. Timing from buy_scenarios legacy A/B/SOFT → GO_A/GO_B/WAIT
    3. 실행후보 only if pick ∩ timing.is_go
    4. Confirmed EARN_D5 only hard-blocks (estimates warn)
    """
    from sepa.earn_calendar import earn_info_from_row
    from sepa.pick_pool import build_pick_pool, chase_label_blocks_pick
    from sepa.timing_gate import timing_from_scenario_row

    held = {h.ticker for h in book.holdings}
    no_add = {h.ticker for h in book.holdings if h.no_add}
    asof = book.effective_date

    scen_by: dict[str, dict[str, Any]] = {}
    for r in (scenarios or {}).get("rows") or []:
        t = str(r.get("t") or r.get("ticker") or "").upper()
        if t:
            scen_by[t] = r

    chase_map: dict[str, dict[str, Any]] = {}
    if chase:
        for r in chase.get("rows") or []:
            t = str(r.get("ticker") or r.get("t") or "").upper()
            if t:
                chase_map[t] = r

    picks = build_pick_pool(chase, scenarios)
    pick_tickers = {p.ticker for p in picks}

    # Also surface held NO_ADD / blocked scenario names for transparency
    extra_tickers: set[str] = set()
    for t in list(scen_by) + list(chase_map):
        if t in held and t in no_add:
            extra_tickers.add(t)
        lab = str((chase_map.get(t) or {}).get("chase") or "")
        if lab and chase_label_blocks_pick(lab) and t in scen_by:
            extra_tickers.add(t)
        row = scen_by.get(t) or {}
        if row.get("upside") is not None and float(row["upside"]) < 0 and t in scen_by:
            extra_tickers.add(t)

    from sepa.pick_pool import PickRow

    universe = list(picks)
    seen = set(pick_tickers)
    for t in sorted(extra_tickers):
        if t in seen:
            continue
        seen.add(t)
        cr = chase_map.get(t) or {}
        sr = scen_by.get(t) or {}
        px = sr.get("last") if sr.get("last") is not None else sr.get("px")
        if px is None:
            px = cr.get("px")
        universe.append(
            PickRow(
                ticker=t,
                rank=int(cr.get("rank") or 999),
                chase=str(cr.get("chase") or "—"),
                px=float(px) if px is not None else None,
                upside=float(sr["upside"]) if sr.get("upside") is not None else None,
                earn_date=(
                    str(sr.get("earnDate") or sr.get("earn_date") or cr.get("earn_date") or "")[:10]
                    or None
                ),
                sector=str(sr.get("sector") or "") or None,
                source="extra",
            )
        )

    ideas: list[BuyIdea] = []
    for p in universe:
        t = p.ticker
        sr = scen_by.get(t) or {}
        chase_lab = p.chase or str((chase_map.get(t) or {}).get("chase") or "")
        ups = p.upside if p.upside is not None else (
            float(sr["upside"]) if sr.get("upside") is not None else None
        )
        px = p.px
        if px is None and sr:
            px = sr.get("last") if sr.get("last") is not None else sr.get("px")
            px = float(px) if px is not None else None

        if sr:
            timing = timing_from_scenario_row(sr, as_of=asof)
        else:
            # Pick without timing row → WAIT (keep on watchlist)
            from sepa.timing_gate import TimingResult

            earn = earn_info_from_row(
                {"earnDate": p.earn_date, "earn_source": "estimate"},
                default_source="estimate",
            )
            if earn.blocks_new_buys(asof):
                timing = TimingResult(t, "BLOCK", "", f"EARN_D5 확정 · {earn.earn_date}", earn_d5_confirmed=True)
            else:
                timing = TimingResult(t, "WAIT", "", "타이밍 WAIT(시나리오없음·본선유지)")

        # Portfolio SSOT earn overrides to confirmed for held names
        held_row = next((h for h in book.holdings if h.ticker == t), None)
        if held_row and held_row.earn_date and in_earn_d5(held_row.earn_date, asof):
            from sepa.timing_gate import TimingResult

            timing = TimingResult(
                t, "BLOCK", timing.legacy_scenario,
                f"EARN_D5 확정(SSOT) · {held_row.earn_date}",
                earn_d5_confirmed=True,
            )

        reason_bits = [f"본선#{p.rank}" if p.source != "extra" else "비본선", timing.reason]
        if chase_lab and chase_lab != "—":
            reason_bits.append(f"Chase {chase_lab}")
        if ups is not None:
            reason_bits.append(f"업사이드 {float(ups)*100:+.1f}%")
        if timing.rsi is not None:
            reason_bits.append(f"RSI{timing.rsi:.0f}")
        if timing.pct_hi is not None:
            reason_bits.append(f"고점{timing.pct_hi*100:+.1f}%")

        in_pool = t in pick_tickers
        bucket = "워치"
        reason = " · ".join(reason_bits)

        if t in held and t in no_add:
            bucket = "금지"
            reason = f"보유·NO_ADD · {reason}"
        elif timing.status == "BLOCK" or timing.earn_d5_confirmed:
            bucket = "금지"
            reason = f"EARN_D5 · {reason}"
        elif chase_label_blocks_pick(chase_lab):
            bucket = "금지"
            reason = f"Chase 제외 · {reason}"
        elif ups is not None and float(ups) < 0:
            bucket = "금지"
            reason = f"업사이드 음수 · {reason}"
        elif in_pool and timing.is_go:
            bucket = "실행후보"
            reason = f"본선∩GO · {reason}"
        elif in_pool:
            bucket = "워치"
            reason = f"본선·자리대기 · {reason}"
        else:
            bucket = "워치"
            reason = f"비본선 · {reason}"

        ideas.append(
            BuyIdea(
                ticker=t,
                bucket=bucket,
                scenario=timing.legacy_scenario or timing.status,
                reason=reason,
                px=px,
                upside=float(ups) if ups is not None else None,
                earn_date=p.earn_date or (str(sr.get("earnDate") or "")[:10] or None),
                chase=chase_lab or None,
                sector=p.sector or (str(sr.get("sector") or "") or None),
                pick_rank=p.rank if in_pool else None,
                timing=timing.status,
                limit_hint=_limit_hint(px) if bucket == "실행후보" else None,
            )
        )

    order = {"실행후보": 0, "워치": 1, "금지": 2}
    ideas.sort(
        key=lambda x: (
            order.get(x.bucket, 9),
            x.pick_rank if x.pick_rank is not None else 999,
            x.ticker,
        )
    )
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
        lines.append("금: 본선∩GO 재점검 · 주간 마무리")
        lines.append("저녁창(17:30~20:55) 지정가 · 돌파추격 금지")
    else:
        lines.append("모드: 월~목 → 향후 5영업일 브리프")
        lines.append("보유 stop·확정 EARN_D5만 매일 확인 · 신규는 본선∩타이밍GO만")
        lines.append("저녁 17:30~20:55 지정가 실행 · 미체결 추격 금지")
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
    lines.append("금지: NO_ADD·유효금지 · 과열 · 업사이드 음수 · 현금바닥 파괴 · L1=0 · 등급한도 초과 추가")
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
