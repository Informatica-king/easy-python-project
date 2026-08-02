#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""포폴() — Portfolio ops PDF (weights, events, buy filter, week plan)."""

from __future__ import annotations

import base64
import html
import sys
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from weasyprint import HTML

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sepa.portfolio_ops import (  # noqa: E402
    BENCH,
    BuyIdea,
    PortfolioBook,
    build_ops_plan,
    enrich_marks,
    fetch_bench_series,
    filter_buy_ideas,
    freshness_warning,
    load_book,
    load_buy_scenarios,
    load_chase,
    normalize_series,
    portfolio_index,
    week_plan_mode,
)

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
CHART_DIR = Path("/workspace/reports/charts/portfolio_ops")
PORTFOLIO_YAML = Path("/workspace/config/portfolio_watch.yaml")


def _fonts():
    fm.fontManager.addfont(FONT_REG)
    fm.fontManager.addfont(FONT_BOLD)
    prop = fm.FontProperties(fname=FONT_REG)
    prop_b = fm.FontProperties(fname=FONT_BOLD)
    plt.rcParams["font.family"] = prop.get_name()
    plt.rcParams["axes.unicode_minus"] = False
    return prop, prop_b


def img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def esc(s: object) -> str:
    return html.escape("" if s is None else str(s))


def fmt_usd(x: float | None) -> str:
    if x is None:
        return "—"
    return f"${x:,.2f}"


def fmt_pct(x: float | None, signed: bool = True) -> str:
    if x is None:
        return "—"
    return f"{x*100:+.1f}%" if signed else f"{x*100:.1f}%"


def chart_pies(book: PortfolioBook, prop, prop_b) -> tuple[Path, Path]:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    labels = [h.ticker for h in book.holdings if h.value]
    sizes = [h.value for h in book.holdings if h.value]
    colors = ["#1e3a5f", "#0d5c4d", "#b8860b", "#334155", "#9f1239", "#2c5282", "#57534e", "#166534"]

    fig, ax = plt.subplots(figsize=(5.2, 4.0))
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors[: len(labels)], startangle=90, textprops={"fontproperties": prop, "fontsize": 8})
    ax.set_title("주식만 비중", fontproperties=prop_b, fontsize=11)
    p1 = CHART_DIR / "pie_stock.png"
    fig.savefig(p1, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    labels2 = labels + ["CASH"]
    sizes2 = sizes + [book.cash_usd]
    fig, ax = plt.subplots(figsize=(5.2, 4.0))
    cols = colors[: len(labels)] + ["#a8a29e"]
    ax.pie(sizes2, labels=labels2, autopct="%1.1f%%", colors=cols, startangle=90, textprops={"fontproperties": prop, "fontsize": 8})
    ax.set_title(f"주식+현금 (바닥 ${book.cash_floor_usd:.0f})", fontproperties=prop_b, fontsize=11)
    p2 = CHART_DIR / "pie_liquid.png"
    fig.savefig(p2, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p1, p2


def chart_vs_bench(book: PortfolioBook, prop, prop_b) -> Path | None:
    start = book.as_of - timedelta(days=90)
    tickers = [h.ticker for h in book.holdings] + list(BENCH)
    series = fetch_bench_series(tickers, start)
    pidx = portfolio_index(book, series)
    if not pidx:
        return None
    start_norm = pidx[0][0]
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    ax.plot([d for d, _ in pidx], [v for _, v in pidx], label="내 포폴(주식)", color="#1e3a5f", lw=2.0)
    for b, color in zip(BENCH, ["#0d5c4d", "#9f1239"]):
        if b not in series:
            continue
        norm = normalize_series(series[b], start_norm)
        if not norm:
            continue
        ax.plot([d for d, _ in norm], [v for _, v in norm], label=b, lw=1.5, color=color)
    ax.axhline(100, color="#94a3b8", lw=0.8, ls="--")
    ax.set_title("포폴 바스켓 vs QQQ·SPY (스냅 구간 시작=100)", fontproperties=prop_b, fontsize=11)
    ax.legend(prop=prop, fontsize=8)
    ax.set_ylabel("지수", fontproperties=prop)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontproperties(prop)
    fig.tight_layout()
    out = CHART_DIR / "vs_bench.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def build_css() -> str:
    return f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:12mm 11mm 14mm 11mm;
      @bottom-center {{ content:"포폴() 운영브리프 — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }}
    }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.2pt; line-height:1.4; color:#1c1917; }}
    h1 {{ font-size:20pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:12pt; margin:12px 0 6px; border-bottom:2px solid #1e3a5f; padding-bottom:2px; }}
    .sub {{ color:#57534e; margin:0 0 8px; }}
    .box {{ border:1px solid #d6d3d1; padding:8px 10px; margin:6px 0; background:#fafaf9; }}
    .risk {{ border-color:#9f1239; background:#fff1f2; }}
    .forbid {{ border-color:#b45309; background:#fffbeb; }}
    .ok {{ border-color:#166534; background:#ecfdf5; }}
    table {{ width:100%; border-collapse:collapse; margin:6px 0 10px; font-size:8.5pt; }}
    th, td {{ border:1px solid #e7e5e4; padding:3px 5px; text-align:left; vertical-align:top; }}
    th {{ background:#eef2f7; }}
    .r {{ text-align:right; }}
    .small {{ font-size:7.5pt; color:#57534e; }}
    .charts {{ display:flex; gap:8px; justify-content:space-between; }}
    .charts img {{ width:48%; }}
    img.wide {{ width:100%; max-height:220px; object-fit:contain; }}
    .bucket-run {{ color:#166534; font-weight:bold; }}
    .bucket-watch {{ color:#b45309; }}
    .bucket-ban {{ color:#9f1239; }}
    """


def snap_table(book: PortfolioBook) -> str:
    rows = []
    for h in sorted(book.holdings, key=lambda x: -(x.value or 0)):
        rows.append(
            "<tr>"
            f"<td><b>{esc(h.ticker)}</b><br/><span class='small'>{esc(h.sleeve)}</span></td>"
            f"<td class='r'>{h.shares:g}</td>"
            f"<td class='r'>{fmt_usd(h.cost)}</td>"
            f"<td class='r'>{fmt_usd(h.px)}</td>"
            f"<td class='r'>{fmt_usd(h.value)}</td>"
            f"<td class='r'>{fmt_pct(h.w_stock, False)}</td>"
            f"<td class='r'>{fmt_pct(h.w_liquid, False)}</td>"
            f"<td class='r'>{fmt_pct(h.pnl_pct)}</td>"
            f"<td class='small'>{esc(h.stance)}</td>"
            "</tr>"
        )
    return (
        "<table><tr><th>종목</th><th>수량</th><th>평단</th><th>종가</th><th>평가</th>"
        "<th>주식%</th><th>유동%</th><th>손익</th><th>스텐스</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def event_table(book: PortfolioBook) -> str:
    rows = []
    for h in sorted(book.holdings, key=lambda x: x.earn_date or date(2099, 1, 1)):
        d5 = "Y" if h.earn_d5 else "—"
        d5s = h.d5_start.isoformat() if h.d5_start else "—"
        earn = h.earn_date.isoformat() if h.earn_date else "—"
        stop = f"${h.stop:g}" if h.stop is not None else "—"
        tp = f"${h.tp1:g}" if h.tp1 is not None else "—"
        inv = f"${h.invalidation:g}" if h.invalidation is not None else "—"
        rows.append(
            f"<tr><td><b>{esc(h.ticker)}</b></td><td>{earn}</td><td>{d5s}</td>"
            f"<td>{d5}</td><td>{stop}</td><td>{tp}</td><td>{inv}</td></tr>"
        )
    return (
        "<table><tr><th>종목</th><th>실적</th><th>D-5시작</th><th>D5</th><th>stop</th><th>tp1</th><th>무효</th></tr>"
        + "".join(rows)
        + "</table>"
        + "<p class='small'>포트 공통: 월적립 10일 · 현금바닥 $150 · 물타기 금지</p>"
    )


def buy_table(ideas: list[BuyIdea]) -> str:
    if not ideas:
        return "<p class='small'>매수시나리오 파일 없음.</p>"
    rows = []
    for i in ideas:
        cls = {"실행후보": "bucket-run", "워치": "bucket-watch", "금지": "bucket-ban"}.get(i.bucket, "")
        rows.append(
            f"<tr><td class='{cls}'>{esc(i.bucket)}</td><td><b>{esc(i.ticker)}</b></td>"
            f"<td>{esc(i.scenario)}</td><td class='r'>{fmt_usd(i.px)}</td>"
            f"<td class='r'>{fmt_pct(i.upside)}</td><td>{esc(i.earn_date)}</td>"
            f"<td class='small'>{esc(i.reason)}</td></tr>"
        )
    return (
        "<table><tr><th>구분</th><th>티커</th><th>게이트</th><th>가격</th><th>업사이드</th><th>실적</th><th>근거</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def build_html(
    book: PortfolioBook,
    ideas: list[BuyIdea],
    pie_stock: Path,
    pie_liq: Path,
    bench: Path | None,
    plan_lines: list[str],
    fresh_warn: str | None,
    scen_path: Path | None,
) -> str:
    mode = week_plan_mode(book.as_of)
    plan_title = "차주 운영계획" if mode == "next_week" else "향후 5영업일 브리프"
    risk_html = "".join(f"<li>{esc(r)}</li>" for r in book.risks) or "<li>특이 리스크 스트립 없음</li>"
    forbid_html = "".join(f"<li>{esc(r)}</li>" for r in book.forbid)
    actions_html = "".join(f"<li>{esc(a)}</li>" for a in book.actions)
    plan_html = "".join(f"<li>{esc(l)}</li>" for l in plan_lines)
    bench_block = ""
    if bench and bench.exists():
        bench_block = f"<h2>0-B. 포폴 vs QQQ·SPY</h2><img class='wide' src='data:image/png;base64,{img_b64(bench)}'/>" \
                      f"<p class='small'>현금·중간매매 미반영 근사 · 수량 고정 바스켓 · 투자권유 아님</p>"
    warn = f"<div class='box risk'><b>freshness</b> {esc(fresh_warn)}</div>" if fresh_warn else ""
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"/>
<title>포폴() {book.as_of.isoformat()}</title><style>{build_css()}</style></head><body>
<h1>포폴() 운영브리프</h1>
<p class="sub">기준 {esc(book.as_of.isoformat())} · 출처 {esc(book.source)} · 심층연동 {esc(scen_path.name if scen_path else '—')}</p>
<div class="box ok">
  <b>북 요약</b> 주식 {fmt_usd(book.equity_usd)} · 현금 {fmt_usd(book.cash_usd)}
  ({fmt_pct(book.cash_pct, False)}) · 유동 {fmt_usd(book.liquid_usd)} · 바닥 ${book.cash_floor_usd:.0f}
</div>
{warn}
<div class="box risk"><b>리스크 스트립</b><ul>{risk_html}</ul></div>
<div class="box forbid"><b>금지 / 홀드</b><ul>{forbid_html}</ul></div>
<div class="box"><b>액션 3줄</b><ul>{actions_html}</ul></div>

<h2>0. 시각화</h2>
<div class="charts">
  <img src="data:image/png;base64,{img_b64(pie_stock)}"/>
  <img src="data:image/png;base64,{img_b64(pie_liq)}"/>
</div>
{bench_block}

<h2>1. 현재 스냅</h2>
{snap_table(book)}
<p class="small">{esc(book.note)}</p>

<h2>2. 이벤트 캘린더</h2>
{event_table(book)}

<h2>3. 매수고려 (심층 ∩ 포폴필터)</h2>
{buy_table(ideas)}

<h2>4. {esc(plan_title)}</h2>
<ul>{plan_html}</ul>
<p class="small">생성: 포폴() · sepa.portfolio_ops · WeasyPrint · NanumGothic</p>
</body></html>"""


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    snap = PORTFOLIO_YAML
    if "--snap" in argv:
        i = argv.index("--snap")
        snap = Path(argv[i + 1])
    book = load_book(snap)
    book = enrich_marks(book)
    prop, prop_b = _fonts()
    pie_s, pie_l = chart_pies(book, prop, prop_b)
    bench = chart_vs_bench(book, prop, prop_b)

    scenarios, scen_path = load_buy_scenarios("reports")
    chase, _ = load_chase("reports")
    as_of_s = (scenarios or {}).get("as_of") or (chase or {}).get("as_of")
    fresh = freshness_warning(as_of_s, book.as_of)
    ideas = filter_buy_ideas(book, scenarios, chase)
    plan = build_ops_plan(book, ideas)

    html_doc = build_html(book, ideas, pie_s, pie_l, bench, plan, fresh, scen_path)
    tag = book.as_of.isoformat()
    html_path = Path(f"/workspace/reports/Portfolio_Ops_{tag}.html")
    pdfs = [
        Path(f"/opt/cursor/artifacts/Portfolio_Ops_{tag}.pdf"),
        Path(f"/workspace/reports/Portfolio_Ops_{tag}.pdf"),
        Path(f"/workspace/assets/Portfolio_Ops_{tag}.pdf"),
    ]
    html_path.write_text(html_doc, encoding="utf-8")
    print(f"HTML {html_path} {html_path.stat().st_size}")
    pdf_bytes = HTML(filename=str(html_path)).write_pdf()
    for p in pdfs:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf_bytes)
        print(f"PDF {p} {p.stat().st_size}")
    print(
        f"포폴 equity={book.equity_usd:.2f} cash={book.cash_usd:.2f} "
        f"ideas_run={sum(1 for i in ideas if i.bucket=='실행후보')} mode={week_plan_mode(book.as_of)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
