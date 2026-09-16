#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(TXG) — 공식 실적 YAML(SSOT) 기반 · WeasyPrint PDF.

Policy: ``sepa.rev_filing.require_filing("TXG")`` — YAML 없으면 중단.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from weasyprint import HTML

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sepa.rev_compete import build_compete_charts  # noqa: E402
from sepa.rev_filing import FilingRequiredError, require_filing  # noqa: E402
from sepa.rev_price_chart import build_and_insert_price  # noqa: E402

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

OUT_PDF = [
    Path("/opt/cursor/artifacts/TXG_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/TXG_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/TXG_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/TXG_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/txg")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "navy": "#1e3a5f",
    "teal": "#0f766e",
    "teal2": "#14b8a6",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "slate": "#334155",
}


def img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def save_fig(fig, name: str) -> Path:
    p = CHART_DIR / name
    fig.savefig(p, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def fig_block(path: Path, caption: str) -> str:
    return (
        f"<figure><img src='data:image/png;base64,{img_b64(path)}'/>"
        f"<figcaption>{caption}</figcaption></figure>"
    )


def gloss(items: list[tuple[str, str]]) -> str:
    lis = "".join(f"<li><span class='term'>{a}</span> — {b}</li>" for a, b in items)
    return f"<div class='gloss'><div class='gloss-title'>이 블록 용어 주석</div><ul>{lis}</ul></div>"


def _mix(doc, name: str) -> dict | None:
    for r in doc.mix_product:
        if r.get("name") == name:
            return r
    return None


def _geo(doc, name: str) -> dict | None:
    for r in doc.mix_geo:
        if r.get("name") == name:
            return r
    return None


def live_marks() -> dict:
    """Prefer latest chase rank snap; fallback yfinance."""
    rank = Path("/workspace/reports/rank_20260916.json")
    if rank.exists():
        import json

        rows = json.loads(rank.read_text(encoding="utf-8")).get("rows") or []
        for r in rows:
            if r.get("t") == "TXG":
                return {
                    "px": float(r["px"]),
                    "pt": float(r["ptA"]) if r.get("ptA") is not None else None,
                    "h52": float(r["h"]) if r.get("h") is not None else None,
                    "earn": str(r.get("earnDate") or "")[5:10].replace("-", "-")
                    if r.get("earnDate")
                    else "—",
                }
    try:
        import yfinance as yf

        info = yf.Ticker("TXG").info or {}
        px = info.get("currentPrice") or info.get("regularMarketPrice")
        return {
            "px": float(px) if px else None,
            "pt": float(info["targetMeanPrice"]) if info.get("targetMeanPrice") else None,
            "h52": float(info["fiftyTwoWeekHigh"]) if info.get("fiftyTwoWeekHigh") else None,
            "earn": "—",
        }
    except Exception:
        return {"px": None, "pt": None, "h52": None, "earn": "—"}


def chart_business_flow() -> Path:
    fig, ax = plt.subplots(figsize=(9.2, 3.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    boxes = [
        (0.1, 0.7, 1.75, 1.6, "연구소·바이오\n파마 고객", C["sand"]),
        (2.05, 0.7, 1.8, 1.6, "장비 설치\n(Instruments)", C["gold"]),
        (4.05, 0.7, 1.85, 1.6, "시약·칩\nConsumables", C["teal2"]),
        (6.1, 0.7, 1.75, 1.6, "단일세포\n·공간전사체", C["teal"]),
        (8.05, 0.7, 1.7, 1.6, "반복 매출\n+서비스", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(
            x + w / 2, y + h / 2, t, ha="center", va="center",
            fontproperties=PROP_B, fontsize=8.5, color=tc,
        )
    for x in (1.95, 3.95, 5.95, 7.9):
        ax.annotate(
            "", xy=(x + 0.08, 1.5), xytext=(x - 0.08, 1.5),
            arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6),
        )
    ax.set_title("비즈니스 한눈에 — 장비 깔고, 시약·칩을 반복 판매", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix(doc) -> Path:
    cons = _mix(doc, "Consumables total")
    inst = _mix(doc, "Instruments total")
    svc = _mix(doc, "Services")
    lic = _mix(doc, "License & royalty")
    sc_c = _mix(doc, "Consumables — Single Cell")
    sp_c = _mix(doc, "Consumables — Spatial")
    sc_i = _mix(doc, "Instruments — Single Cell")
    sp_i = _mix(doc, "Instruments — Spatial")

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [
        cons["amount_m"] if cons else 0,
        inst["amount_m"] if inst else 0,
        svc["amount_m"] if svc else 0,
        lic["amount_m"] if lic else 0,
    ]
    total = sum(sizes) or 1
    labels = [
        f"Consumables\n{sizes[0]:.1f}M ({100*sizes[0]/total:.0f}%)",
        f"Instruments\n{sizes[1]:.1f}M ({100*sizes[1]/total:.0f}%)",
        f"Services\n{sizes[2]:.1f}M ({100*sizes[2]/total:.0f}%)",
        f"License\n{sizes[3]:.1f}M",
    ]
    ax.pie(
        sizes, labels=labels,
        colors=[C["teal"], C["gold"], C["navy"], C["sand"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=7.5),
    )
    ax.set_title(
        f"매출 유형 (공식 Q · 총 ${doc.revenue_total_m:.1f}M)",
        fontproperties=PROP_B, fontsize=11,
    )

    ax = axes[1]
    cats = ["SC\nConsum.", "Spatial\nConsum.", "SC\nInstr.", "Spatial\nInstr."]
    vals = [
        sc_c["amount_m"] if sc_c else 0,
        sp_c["amount_m"] if sp_c else 0,
        sc_i["amount_m"] if sc_i else 0,
        sp_i["amount_m"] if sp_i else 0,
    ]
    bars = ax.bar(cats, vals, color=[C["navy"], C["teal"], C["gold"], C["sand"]], width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("제품 라인 상세 (공식)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v:.1f}", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_growth_bridge(doc) -> Path:
    keys = [
        ("Consumables total", "Consum.\nYoY"),
        ("Consumables — Single Cell", "SC Cons.\nYoY"),
        ("Consumables — Spatial", "Spatial\nCons. YoY"),
        ("Instruments total", "Instruments\nYoY"),
    ]
    cats, vals = [], []
    for name, label in keys:
        row = _mix(doc, name)
        cats.append(label)
        vals.append(row["yoy_pct"] if row and row.get("yoy_pct") is not None else 0)
    cats += ["Reported\nTotal YoY", "Ex-settlement\nYoY"]
    vals += [
        doc.yoy_reported_pct or 0,
        doc.yoy_ex_onetime_pct or 0,
    ]
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    colors = [C["green"] if v >= 0 else C["red"] for v in vals]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("성장 브리지 — 공식 표 기준 (일회성 분리)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2, v + (1.2 if v >= 0 else -3.2),
            f"{v:+.0f}%", ha="center", fontproperties=PROP, fontsize=8,
        )
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)
    fig.tight_layout()
    return save_fig(fig, "03_growth_bridge.png")


def chart_razor_blade() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.3, 0.6, 2.8, 1.8, "1. 장비 판매\n(낮은/마이너스 성장)", C["gold"]),
        (3.6, 0.6, 2.8, 1.8, "2. 설치 기반(IB)\n연구소에 기기 확보", C["teal2"]),
        (6.9, 0.6, 2.8, 1.8, "3. 소모품 반복\n=매출·마진 핵심", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["gold"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9, color=tc)
    ax.set_title("레이저-블레이드 모델 — 장비는 문, 소모품이 본업", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "04_razor_blade.png")


def chart_geo(doc) -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    names = ["United States", "EMEA", "China", "APAC ex-China"]
    vals, yoy = [], []
    for n in names:
        r = _geo(doc, n)
        vals.append(r["amount_m"] if r else 0)
        yoy.append(r.get("yoy_pct") if r else None)
    bars = ax.bar(names, vals, color=[C["navy"], C["teal"], C["red"], C["gold"]], width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("지역 매출 (공식)", fontproperties=PROP_B, fontsize=11)
    for b, v, y in zip(bars, vals, yoy):
        t = f"{v:.0f}" + (f"\n{y:+.0f}%" if y is not None else "")
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, t, ha="center", fontproperties=PROP, fontsize=7.5)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "05_geo.png")


def chart_guidance(doc) -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    lo = doc.guidance_fy_low_m or 0
    hi = doc.guidance_fy_high_m or 0
    mid = (lo + hi) / 2 if lo and hi else 0
    # Q2 run-rate approx from ex-onetime
    rr = (doc.revenue_ex_onetime_m or 0) * 4
    cats = ["가이드\n하단", "가이드\n중단", "가이드\n상단", "Q2ex×4\n런레이트"]
    vals = [lo, mid, hi, rr]
    bars = ax.bar(cats, vals, color=[C["slate"], C["teal"], C["navy"], C["gold"]], width=0.55)
    ax.set_ylabel("연간 매출 (백만 USD)", fontproperties=PROP)
    ax.set_title("FY 가이던스 (공식 상향) vs 분기 런레이트", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 3, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(min(vals) - 40, max(vals) + 40)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "06_guidance.png")


def chart_pnl(doc) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    cats = ["총이익률", "전년\n총이익률"]
    vals = [doc.gross_margin_pct or 0, doc.gross_margin_prior_pct or 0]
    ax.bar(cats, vals, color=[C["teal"], C["slate"]], width=0.5)
    ax.set_ylim(0, 100)
    ax.set_ylabel("%", fontproperties=PROP)
    ax.set_title("총이익률", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v:.0f}%", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    cats = ["영업손익", "순손익", "현금+단기"]
    vals = [doc.operating_income_m or 0, doc.net_income_m or 0, doc.cash_and_securities_m or 0]
    colors = [C["red"] if vals[0] < 0 else C["green"], C["red"] if vals[1] < 0 else C["green"], C["navy"]]
    # scale cash on secondary feel: show cash/10 for bar comparability? Better two groups.
    ax.bar(["영업", "순이익"], vals[:2], color=colors[:2], width=0.5)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title(f"손익 · 현금 ${vals[2]:.0f}M", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(vals[:2]):
        ax.text(i, v + (2 if v >= 0 else -5), f"{v:+.1f}", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "07_pnl.png")


def chart_scenarios(px: float, pt: float | None) -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [28, 42, 58]
    highs = [42, 58, 85]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    if px:
        ax.axvline(px, color=C["gold"], ls="--", lw=1.5)
        ax.text(px + 0.5, 2.35, f"현재 ~{px:.1f}", fontproperties=PROP, fontsize=8, color=C["gold"])
    if pt:
        ax.axvline(pt, color="#2563eb", ls=":", lw=1.2)
        ax.text(pt + 0.5, -0.55, f"PT평균 ~{pt:.1f}", fontproperties=PROP, fontsize=7.5, color="#2563eb")
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        ax.text((lo + hi) / 2, i, f"{lo}–{hi}", ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(20, 95)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear — 예시 밴드(권유 아님)", fontproperties=PROP_B, fontsize=11)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP_B)
    fig.tight_layout()
    return save_fig(fig, "08_scenarios.png")


def chart_catalysts(doc) -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, "실적", "공식Q", f"${doc.revenue_total_m:.0f}M\nex+{doc.yoy_ex_onetime_pct:.0f}%", C["teal"]),
        (0.28, "Atera", "촉매", "초기주문\n강세", C["navy"]),
        (0.52, "가이드", "상향", f"${doc.guidance_fy_low_m:.0f}–{doc.guidance_fy_high_m:.0f}M", C["gold"]),
        (0.76, "지역", "리스크", "US·중국\n약세", C["red"]),
    ]
    for x, tag, title, body, c in items:
        ax.add_patch(
            FancyBboxPatch(
                (x, 0.25), 0.2, 0.55, boxstyle="round,pad=0.02,rounding_size=0.04",
                facecolor=c, edgecolor="white", lw=1.5, transform=ax.transAxes,
            )
        )
        ax.text(x + 0.1, 0.68, tag, ha="center", transform=ax.transAxes, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + 0.1, 0.55, title, ha="center", transform=ax.transAxes, fontproperties=PROP_B, fontsize=10, color="white")
        ax.text(x + 0.1, 0.38, body, ha="center", transform=ax.transAxes, fontproperties=PROP, fontsize=7.5, color="white")
    ax.set_title("촉매 카드 — 공식 숫자 + 보도 하이라이트", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "09_catalysts.png")


def chart_position(px: float, upside: float | None) -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    ups = f"{upside*100:+.0f}%" if upside is not None else "—"
    rows = [
        (0.3, 2.6, 9.4, 1.0, C["red"], "white",
         f"포트: 보유 4주 · 품질C · 비중 OVER · NO_ADD · PT대비 {ups}"),
        (0.3, 1.4, 4.5, 0.95, C["gold"], C["ink"], "공식실적 반영\n소모품·가이드 확인"),
        (5.0, 1.4, 4.7, 0.95, C["slate"], "white", "추가매수 금지\n추격 금지"),
        (0.3, 0.25, 9.4, 0.95, C["sand"], C["ink"],
         "게이트: US/중국 회복 · 장비 저점 · Atera 기여 · stop $42"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1", facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9, color=tc)
    ax.set_title("실행 포지션 맵 (09-16 포폴 SSOT)", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "10_position.png")


def _compete_section(charts: dict[str, Path], bundle, doc) -> str:
    if bundle is None or "share" not in charts:
        return ""
    share_rows = "".join(
        f"<tr><td>{r.name}</td><td>{r.current:.1f}%</td><td>{r.prior:.1f}%</td>"
        f"<td>{r.delta_pp:+.1f}pp</td></tr>"
        for r in bundle.share_rows
    )
    mix_head = "".join(f"<th>{b}</th>" for b in bundle.mix_buckets)
    mix_body = []
    for r in bundle.mix_rows:
        cells = "".join(f"<td>{r['mix'].get(b, 0):.1f}%</td>" for b in bundle.mix_buckets)
        tag = " <b>(대상)</b>" if r.get("subject") else ""
        mix_body.append(
            f"<tr><td>{r['name']}{tag}</td>{cells}<td class='small'>{r.get('note', '')}</td></tr>"
        )
    cons = _mix(doc, "Consumables total")
    cons_pct = 100.0 * cons["amount_m"] / doc.revenue_total_m if cons and doc.revenue_total_m else 0
    ttm_fig = fig_block(charts["ttm"], "TTM 매출 규모") if "ttm" in charts else ""
    return f"""
<h2>1-B. 심층 섹터 경쟁 점유율 · 변화</h2>
<p><b>섹터</b> {bundle.sector_ko}</p>
<div class="easy"><b>쉽게:</b> TXG는 단일세포·공간 툴 피어셋에서 선두 성격.
아래 점유는 방향 비교용 추정(공식 PDF 밖).</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> 이번 공식 분기 기준 TXG 매출의 약 <b>{cons_pct:.0f}%가 소모품</b>.
장비는 ‘문’, 시약·칩이 본업.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
"""


def build_html(doc, charts, *, compete_html: str, marks: dict) -> str:
    px = marks.get("px") or 0.0
    pt = marks.get("pt")
    h52 = marks.get("h52")
    upside = (pt / px - 1.0) if pt and px else None
    asof = doc.report_date
    period = doc.period_end
    earn = marks.get("earn") or "—"

    cons = _mix(doc, "Consumables total")
    sc_c = _mix(doc, "Consumables — Single Cell")
    sp_c = _mix(doc, "Consumables — Spatial")
    inst = _mix(doc, "Instruments total")
    sc_i = _mix(doc, "Instruments — Single Cell")
    sp_i = _mix(doc, "Instruments — Spatial")
    svc = _mix(doc, "Services")
    lic = _mix(doc, "License & royalty")

    def row(r, label=None):
        if not r:
            return ""
        name = label or r["name"]
        yoy = f"{r['yoy_pct']:+.0f}%" if r.get("yoy_pct") is not None else "—"
        pct = f"{100*r['amount_m']/doc.revenue_total_m:.0f}%" if doc.revenue_total_m else "—"
        return f"<tr><td>{name}</td><td>{r['amount_m']:.1f}M</td><td>{pct}</td><td>{yoy}</td></tr>"

    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"TXG 수익구조분석 {asof} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0f766e; padding-bottom:3px; color:#1e3a5f; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#f0f7f6 0%,#e8eef5 55%,#f7f3e8 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#dbeafe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecaca; }}
    .tag.good {{ background:#bbf7d0; }}
    .tag.ssot {{ background:#0f766e; color:white; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#f0fdfa; border-left:4px solid #0f766e; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0f766e; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#0f766e; }}
    """

    ups_s = f"{upside*100:+.1f}%" if upside is not None else "—"
    thesis = (
        f"공식 실적(기간 {period}) 기준 매출 <b>${doc.revenue_total_m:.1f}M</b>. "
        f"특허합의 일회성 ${doc.onetime_items[0]['amount_m']:.1f}M 제외 시 "
        f"<b>${doc.revenue_ex_onetime_m:.1f}M · YoY +{doc.yoy_ex_onetime_pct:.0f}%</b>. "
        f"소모품이 본업(공식 표), 장비·미국·중국은 약함. "
        f"FY26 가이드 <b>${doc.guidance_fy_low_m:.0f}–{doc.guidance_fy_high_m:.0f}M</b> 상향. "
        f"보유 NO_ADD · 추격 금지."
    )

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>TXG 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>TXG 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">10x Genomics · 공식 실적 PDF SSOT</p>
  <p style="margin-top:14px;color:#555">보고일 {asof} · 기간종료 {period} · 다음실적 ~{earn}</p>
  <p style="margin-top:10px"><span class="tag ssot">근거: 공식 실적 PDF</span>
    <span class="tag good">일회성 분리</span>
    <span class="tag bad">보유 NO_ADD</span></p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${px:.2f}</div><div class="s">52주고 ${h52:.2f}</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${pt:.1f}</div><div class="s">{ups_s}</div></span>
    <span class="kpi"><div class="l">공식 분기매출</div><div class="v">${doc.revenue_total_m:.1f}M</div><div class="s">ex-합의 +{doc.yoy_ex_onetime_pct:.0f}%</div></span>
    <span class="kpi"><div class="l">FY 가이드</div><div class="v">${doc.guidance_fy_low_m:.0f}–{doc.guidance_fy_high_m:.0f}M</div><div class="s">{doc.guidance_note}</div></span>
  </p>
</section>

<!--PRICE_CHARTS-->

<h2>0. 한줄 Thesis</h2>
<p>{thesis}</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 연구소에 분석 기계를 팔고, 그 기계에 넣는 시약·칩을 계속 판다. 면도기·면도날 모델.</div>
{gloss([
    ("공식 PDF SSOT", "회사가 낸 실적 보도자료를 숫자 근거로 씀. 추정·뉴스보다 우선."),
    ("일회성(합의)", "특허 소송 합의로 들어온 돈 — 본업 성장과 따로 봐야 함."),
    ("Consumables", "실험마다 쓰는 칩·시약 — 반복 매출."),
])}

<h2>1. 어디서 돈이 오나 (공식 표)</h2>
{fig_block(charts['02'], '유형·제품 믹스')}
<table>
  <tr><th>구분 (공식)</th><th>매출</th><th>비중</th><th>YoY</th></tr>
  {row(sc_c)}{row(sp_c)}{row(cons, '<b>Consumables 합계</b>')}
  {row(sc_i)}{row(sp_i)}{row(inst, 'Instruments 합계')}
  {row(svc)}{row(lic)}
  <tr><td><b>총매출</b></td><td><b>{doc.revenue_total_m:.1f}M</b></td><td>100%</td>
      <td>{doc.yoy_reported_pct:+.0f}% / <b>ex-합의 +{doc.yoy_ex_onetime_pct:.0f}%</b></td></tr>
</table>
{fig_block(charts['04'], '레이저-블레이드')}
{fig_block(charts['03'], '성장 브리지')}
{fig_block(charts['05'], '지역 매출')}
<div class="easy"><b>쉽게:</b> 보고 매출은 작년보다 줄었지만, 합의금을 빼면 본업은 소폭 성장(+{doc.yoy_ex_onetime_pct:.0f}%).
미국·중국은 약하고 EMEA는 상대적 버팀목.</div>

{compete_html}

<h2>2. 수익성 · 현금 · 가이던스</h2>
{fig_block(charts['07'], '손익·마진')}
{fig_block(charts['06'], 'FY 가이던스')}
<table>
  <tr><th>항목</th><th>공식 수치</th></tr>
  <tr><td>총이익률</td><td>{doc.gross_margin_pct:.0f}% (전년 {doc.gross_margin_prior_pct:.0f}%)</td></tr>
  <tr><td>영업손익</td><td>{doc.operating_income_m:+.1f}M</td></tr>
  <tr><td>순손익</td><td>{doc.net_income_m:+.1f}M</td></tr>
  <tr><td>현금+단기투자</td><td><b>${doc.cash_and_securities_m:.0f}M</b></td></tr>
  <tr><td>FY26 가이드</td><td><b>${doc.guidance_fy_low_m:.0f}–{doc.guidance_fy_high_m:.0f}M</b> ({doc.guidance_note})</td></tr>
</table>

<h2>3. 촉매 · 리스크 · 시나리오</h2>
{fig_block(charts['09'], '촉매')}
{fig_block(charts['08'], '시나리오')}
<ul>
  {''.join(f'<li>{c}</li>' for c in doc.catalysts)}
</ul>
<p><b>리스크:</b> {' · '.join(doc.risks) if doc.risks else '—'}</p>
{(''.join(f'<blockquote class="small">“{q}”</blockquote>' for q in doc.quotes)) if doc.quotes else ''}

<h2>4. 포트폴리오 위치</h2>
{fig_block(charts['10'], '포지션 맵')}
<div class="box">
<b>포폴 인용</b><br/>{doc.portfolio_memo}<br/><br/>
보유 4주 · stop $42 · 품질C · 비중 OVER · <b>NO_ADD</b><br/>
가격 ~${px:.2f} · PT ~${pt:.1f} ({ups_s}) — 추격 금지 · 공식 숫자로 본업만 재확인.
</div>
<div class="easy"><b>한줄 결론:</b> 공식 PDF 기준으로 본업(소모품·ex-합의 성장·가이드 상향)은 버팀.
다만 장비·US/중국 약세와 고평가·NO_ADD가 겹쳐 <u>추가매수는 금지</u>.</div>

<h2>부록 · 출처</h2>
<p class="small">
{doc.source_label} · {doc.source_pdf} · report {doc.report_date} · period {doc.period_end}.<br/>
피어 점유/믹스는 추정. 가격·PT는 라이브/스냅. 투자 권유 아님.
</p>
<p class="small">생성: 수익구조분석() · TXG · 공식 YAML SSOT · WeasyPrint + NanumGothic</p>
</body></html>
"""


def main() -> int:
    try:
        doc = require_filing("TXG")
    except FilingRequiredError as e:
        print(e)
        return 2

    marks = live_marks()
    px = marks.get("px") or 0.0
    pt = marks.get("pt")
    upside = (pt / px - 1.0) if pt and px else None

    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(doc),
        "03": chart_growth_bridge(doc),
        "04": chart_razor_blade(),
        "05": chart_geo(doc),
        "06": chart_guidance(doc),
        "07": chart_pnl(doc),
        "08": chart_scenarios(px, pt),
        "09": chart_catalysts(doc),
        "10": chart_position(px, upside),
    }
    bundle, cpaths = build_compete_charts("TXG", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle, doc)
    html = build_html(doc, charts, compete_html=compete_html, marks=marks)
    html, _px = build_and_insert_price("TXG", CHART_DIR, html)
    if _px.ok:
        print(f"price-charts {_px.candle_path} {_px.momentum_path}")
    else:
        print(f"price-charts SKIP {_px.error}")

    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    pdf = HTML(filename=str(OUT_HTML)).write_pdf()
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf)
        print(f"PDF {p} {p.stat().st_size}")

    try:
        from sepa.artifacts import print_release_result, publish_github_release_asset

        notes = (
            f"## TXG 수익구조분석 ({doc.report_date}) · 공식 PDF SSOT\n\n"
            f"- 기간 {doc.period_end} · 매출 ${doc.revenue_total_m:.1f}M · ex-합의 +{doc.yoy_ex_onetime_pct:.0f}%\n"
            f"- FY 가이드 ${doc.guidance_fy_low_m:.0f}–{doc.guidance_fy_high_m:.0f}M\n"
            f"- 포폴: {doc.portfolio_memo}\n"
            f"- 출처: `{doc.source_pdf}`\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag="sepa-rev-txg",
            title="SEPA Revenue Structure — TXG (official filing)",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")

    print(f"TXG filing {doc.period_end} memo={doc.portfolio_memo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
