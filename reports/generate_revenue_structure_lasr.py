#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(LASR) — 고출력 레이저(A&D·산업) 매출구조 + 초보용 설명 + WeasyPrint PDF."""

from __future__ import annotations

import base64
from pathlib import Path
import sys

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sepa.rev_price_chart import build_and_insert_price  # noqa: E402


import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from weasyprint import HTML

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
ASOF = "2026-07-25"
OUT_PDF = [
    Path("/opt/cursor/artifacts/LASR_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/LASR_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/LASR_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/LASR_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/lasr")
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
    "laser": "#7c3aed",
    "def_": "#1d4ed8",
}


def img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def save_fig(fig, name: str) -> Path:
    p = CHART_DIR / name
    fig.savefig(p, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def chart_business_flow() -> Path:
    fig, ax = plt.subplots(figsize=(9.2, 3.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    boxes = [
        (0.1, 0.7, 1.75, 1.6, "국방·산업\n레이저 수요", C["sand"]),
        (2.05, 0.7, 1.8, 1.6, "반도체·광섬유\n레이저 IP", C["gold"]),
        (4.05, 0.7, 1.8, 1.6, "Products\n양산 레이저", C["laser"]),
        (6.05, 0.7, 1.75, 1.6, "Advanced\nDevelopment", C["def_"]),
        (8.0, 0.7, 1.75, 1.6, "A&D·산업\n매출", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("비즈니스 한눈에 — 고출력 레이저를 국방·제조에 판다", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_end_market() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    # Q1'26 end market
    sizes = [55.1, 12.0, 13.0]
    labels = ["A&D\n$55.1M (69%)", "Industrial\n$12.0M (15%)", "Microfab\n$13.0M (16%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["def_"], C["teal"], C["gold"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("최종시장 (Q1'26, 총 $80.2M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["A&D", "Industrial", "Microfab"]
    yoy = [69, 36, 29]
    bars = ax.bar(cats, yoy, color=[C["def_"], C["teal"], C["gold"]], width=0.55)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("최종시장 YoY (Q1'26)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, yoy):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"+{v}%", ha="center", fontproperties=PROP_B, fontsize=10)
    ax.set_ylim(0, 90)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "02_end_market.png")


def chart_segment() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    # Q1 Products 58.2, Dev ~22.0
    cats = ["Products", "Adv.\nDevelopment"]
    vals = [58.2, 22.0]
    bars = ax.bar(cats, vals, color=[C["laser"], C["def_"]], width=0.5)
    ax.set_ylabel("백만 USD (Q1'26)", fontproperties=PROP)
    ax.set_title("보고 세그먼트 매출", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}", ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 75)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    cats = ["Products\nnGAAP GM", "Dev\nnGAAP GM", "전사\nnGAAP GM"]
    vals = [44.6, 7.2, 34.4]
    bars = ax.bar(cats, vals, color=[C["laser"], C["slate"], C["navy"]], width=0.5)
    ax.set_ylabel("%", fontproperties=PROP)
    ax.set_title("Q1'26 Non-GAAP 마진", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v}%", ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 55)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "03_segment.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    qs = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26", "Q2'26g"]
    rev = [51.7, 61.7, 66.7, 81.2, 80.2, 78.0]
    colors = [C["slate"]] * 4 + [C["laser"], C["teal2"]]
    bars = ax.bar(qs, rev, color=colors, width=0.55)
    ax.set_ylabel("매출 (백만 USD)", fontproperties=PROP)
    ax.set_title("분기 매출 — Q1 기록 $80.2M · Q2 가이드 mid $78M", fontproperties=PROP_B, fontsize=12)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    ax.errorbar(5, 78, yerr=3, fmt="none", ecolor=C["teal"], capsize=4, lw=1.2)
    ax.set_ylim(0, 100)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "04_quarterly.png")


def chart_ad_growth() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    cats = ["전사\nQ1'26", "A&D\n합계", "A&D\nProducts", "Development"]
    vals = [80.2, 55.1, 33.1, 22.0]
    colors = [C["slate"], C["def_"], C["laser"], C["navy"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("성장 엔진 — Aerospace & Defense (Q1'26)", fontproperties=PROP_B, fontsize=12)
    notes = ["+55% YoY", "+69% YoY", "+98% YoY", "+38% YoY"]
    for b, v, n in zip(bars, vals, notes):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.0f}\n{n}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 100)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "05_ad_growth.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    rows = [
        (0.4, 3.9, 9.2, 0.85, C["sand"], C["ink"], "고출력 레이저 TAM (Directed Energy · Sensing · 제조)"),
        (0.9, 2.85, 8.2, 0.85, C["gold"], C["ink"], "미 국방·프라임 프로그램 + 산업/마이크로팹 상용"),
        (1.5, 1.8, 7.0, 0.85, C["laser"], "white", "nLIGHT Products (양산) + Advanced Development (R&D계약)"),
        (2.2, 0.75, 5.6, 0.85, C["navy"], "white", "백로그·수주 → 분기 매출 (Top10 ~75%)"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=1.5,
            )
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("수요 깔때기 — 국방 DE/센싱이 성장을 끌어올림", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "06_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    shocks = ["A&D -20%", "A&D -10%", "기준", "A&D +10%", "A&D +20%"]
    # Q1 A&D 55.1 as base index for quarterly A&D
    base = 55.1
    vals = [base * x for x in (0.8, 0.9, 1.0, 1.1, 1.2)]
    colors = [C["red"], "#ea580c", C["slate"], C["teal"], C["navy"]]
    bars = ax.bar(shocks, vals, color=colors, width=0.55)
    ax.set_ylabel("A&D 분기 매출 근사 (M)", fontproperties=PROP)
    ax.set_title("민감도 — A&D 수요 충격 (Q1 런레이트 선형 예시)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 75)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "07_sensitivity.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [40, 70, 90]
    highs = [60, 95, 120]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    ax.axvline(70.02, color=C["gold"], ls="--", lw=1.5)
    ax.text(72, 2.35, "현재 ~70", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.axvline(90.7, color="#2563eb", ls=":", lw=1.2)
    ax.text(92, -0.55, "PT평균 ~91", fontproperties=PROP, fontsize=7.5, color="#2563eb")
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        mid = (lo + hi) / 2
        ax.text(mid, i, f"{lo}–{hi}", ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(25, 135)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear (12M 관점)", fontproperties=PROP_B, fontsize=11)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP_B)
    fig.tight_layout()
    return save_fig(fig, "08_scenarios.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    qs = ["Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    # clip display for extreme Q3; show actual labels
    surp = [100, 100, 27.3, 100]  # visual cap; annotate true
    true = [166.7, 409.2, 27.3, 136.9]
    bars = ax.bar(qs, [min(v, 120) for v in true], color=C["green"], width=0.55)
    ax.set_ylabel("EPS 서프라이즈 % (표시 상한)", fontproperties=PROP)
    ax.set_title("최근 4분기 Non-GAAP EPS 서프라이즈 (연속 Beat)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, true):
        lab = f"+{v:.0f}%" if v < 200 else f"+{v:.0f}%*"
        ax.text(b.get_x() + b.get_width() / 2, min(v, 120) + 3, lab, ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 145)
    ax.text(0.02, -0.18, "* 작은 컨센 분모로 서프라이즈% 극단 — Beat 방향이 핵심", transform=ax.transAxes,
            fontproperties=PROP, fontsize=7.5, color=C["muted"])
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "09_eps_surprise.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    rows = [
        (0.3, 2.6, 9.4, 1.0, C["navy"], "white", "포트 역할: 미보유 워치 · Chase #1 (상·08-06) · NEO 이후 후보"),
        (0.3, 1.4, 4.5, 0.95, C["teal"], "white", "관심 금액\n$60–80 (위성)"),
        (5.0, 1.4, 4.7, 0.95, C["gold"], C["ink"], "타이밍\n08-06 실적 전후"),
        (0.3, 0.25, 9.4, 0.95, C["sand"], C["ink"], "지금: NEO 07-28·현금 우선 · LASR 추격 금지 · TA 분할OK는 ‘후보’일 뿐"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=1.5,
            )
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9, color=tc)
    ax.set_title("실행 포지션 맵 (사용자 계좌 기준)", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "10_position.png")


def gloss(items: list[tuple[str, str]]) -> str:
    lis = "".join(f"<li><span class='term'>{a}</span> — {b}</li>" for a, b in items)
    return f"<div class='gloss'><div class='gloss-title'>이 블록 용어 주석</div><ul>{lis}</ul></div>"


def fig_block(path: Path, caption: str) -> str:
    return (
        f"<figure><img src='data:image/png;base64,{img_b64(path)}'/>"
        f"<figcaption>{caption}</figcaption></figure>"
    )


def build_html(charts: dict[str, Path]) -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"LASR 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #7c3aed; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#7c3aed; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#f5f3ff 0%,#e8eef5 55%,#f0fdfa 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#ddd6fe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#f5f3ff; border-left:4px solid #7c3aed; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#7c3aed; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#7c3aed; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>LASR 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>LASR 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">nLIGHT · 고출력 반도체·광섬유 레이저 · Aerospace &amp; Defense</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1 FY2026 + Q2 가이드 · 실적 ~08-06</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~$70</div><div class="s">시총 ~$3.9B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~$91</div><div class="s">업사이드 ~+30%</div></span>
    <span class="kpi"><div class="l">Q1 매출</div><div class="v">$80.2M</div><div class="s">+55% YoY</div></span>
    <span class="kpi"><div class="l">A&amp;D 비중</div><div class="v">69%</div><div class="s">Q1 · +69% YoY</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">Chase #1 · 상·08-06</span>
    <span class="tag">EPS 4/4 Beat</span>
    <span class="tag warn">GAAP 적자 · Top10 ~75%</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>방산 Directed Energy·레이저 센싱으로 다시 그린 고출력 레이저 회사.</b>
Q1'26 매출 <b>$80.2M (+55%)</b>, A&amp;D가 <b>69%</b>. Products 마진은 높고 Development는 낮음.
심층분석 Chase <b>#1</b>이나, 당신 계좌에서는 <b>NEO(07-28) 이후 위성 후보</b> — 지금은 추격 금지.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> ‘강한 레이저’를 만듦. 예전엔 공장 절삭이 메인이었고,
지금은 <b>미사일 방어·감지용 레이저(국방)</b>가 매출의 엔진.</div>
{gloss([
    ("Directed Energy (DE)", "고에너지 레이저로 위협을 요격·무력화하는 국방 응용."),
    ("Fiber / Semiconductor laser", "광섬유·반도체 기반 고출력 레이저 광원."),
    ("Products vs Development", "양산 제품 매출 vs 국방 R&D·프로토타입 계약 매출."),
])}

<h2>1. 어디서 돈이 오나 — 최종시장 · 세그먼트</h2>
{fig_block(charts['02'], '최종시장 믹스')}
{fig_block(charts['03'], 'Products vs Development')}
<table>
  <tr><th>최종시장 (Q1'26)</th><th>매출</th><th>비중</th><th>YoY</th></tr>
  <tr><td>Aerospace &amp; Defense</td><td>$55.1M</td><td>69%</td><td>+69%</td></tr>
  <tr><td>Industrial</td><td>$12.0M</td><td>15%</td><td>+36%</td></tr>
  <tr><td>Microfabrication</td><td>$13.0M</td><td>16%</td><td>+29%</td></tr>
  <tr><td><b>합계</b></td><td><b>$80.2M</b></td><td>100%</td><td><b>+55%</b></td></tr>
</table>
<table>
  <tr><th>보고 세그먼트 (Q1'26)</th><th>매출</th><th>nGAAP GM</th><th>메모</th></tr>
  <tr><td>Laser Products</td><td>$58.2M</td><td>44.6%</td><td>A&amp;D 제품 기록 · 마진 엔진</td></tr>
  <tr><td>Advanced Development</td><td>~$22.0M</td><td>7.2%</td><td>DE·센싱 프로그램 · 낮은 마진</td></tr>
  <tr><td><b>전사</b></td><td><b>$80.2M</b></td><td><b>34.4%</b></td><td>가이드 상회</td></tr>
</table>
<p class="small">FY2025: 매출 <b>$261M (+32%)</b> · A&amp;D ~$175M(+60%) · GAAP NI 여전히 적자(−$23.5M).
백로그 YE'25 <b>$161.6M</b> (+ 미자금 정부계약 가치 ~$184M 언급). Top 10 고객 ~<b>75%</b>.</p>
<div class="easy"><b>쉽게:</b> 같은 ‘레이저’라도 <b>양산 제품</b>은 마진이 좋고,
<b>국방 R&amp;D 계약</b>은 매출은 나와도 마진이 얇다. 성장 스토리의 질을 보려면 Products/A&amp;D 제품 비중을 보라.</div>
{gloss([
    ("Microfabrication", "전자·의료·정밀 가공용 미세 레이저."),
    ("Industrial", "절삭·용접·적층제조(additive) 등 상용 제조."),
    ("고객 집중", "Top10 ~75% — 국방 프라임·정부 편중 리스크."),
])}

<h2>2. 성장 엔진 — A&amp;D · DE 파이프라인</h2>
{fig_block(charts['05'], 'A&D 성장')}
{fig_block(charts['06'], '수요 깔때기')}
<ul>
  <li>A&amp;D Products Q1 <b>+98% YoY</b> — 성장의 핵심</li>
  <li>경영진: DE follow-on 생산·플랫폼 업그레이드·신규 프로토타입 파이프라인</li>
  <li>Industrial: 절삭/용접은 last-time buy 언급, <b>additive manufacturing</b>이 상대 밝은 점</li>
  <li>Q2 가이드: 매출 <b>$75–81M</b> (mid $78 = Products ~$58 + Dev ~$20), 전사 GM 29–33%, Adj.EBITDA $8–12M</li>
</ul>
<div class="easy"><b>쉽게:</b> ‘국방 레이저가 양산으로 넘어가는가’가 핵심 질문.
개발 계약만 늘고 제품이 안 늘면 마진이 안 좋아짐.</div>
{gloss([
    ("HEL", "High Energy Laser — 고에너지 레이저 시스템."),
    ("Beam combining", "여러 레이저 빔을 합쳐 출력을 올리는 기술."),
    ("Adj. EBITDA", "주식보상 등 조정 후 영업 현금성 이익 지표."),
])}

<h2>3. 분기 · Beat · 수익성</h2>
{fig_block(charts['04'], '분기 매출')}
{fig_block(charts['09'], 'EPS 서프라이즈')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>Q1'26 매출 / YoY</td><td>$80.2M / +55%</td></tr>
  <tr><td>GAAP</td><td>아직 영업·순이익 적자 구간 (성장 투자·SBC)</td></tr>
  <tr><td>Non-GAAP EPS</td><td>연속 Beat (분모 작아 %는 극단적일 수 있음)</td></tr>
  <tr><td>다음 실적</td><td>~<b>2026-08-06</b> · Rev 컨센 ~$78.6M · EPS ~$0.14</td></tr>
  <tr><td>Fwd P/E</td><td>~104 — 이익 회복 가정 반영, 비싸 보임</td></tr>
</table>
<div class="box"><b>해석:</b> 모멘텀·Beat·PT 업사이드(~+30%)는 Chase 1위 정합.
다만 <b>GAAP 적자 + 고 Fwd배수 + 고객집중 + beta~2.3</b>이라 소액 위성만 맞음.</div>

<h2>4. 민감도 · 시나리오</h2>
{fig_block(charts['07'], 'A&D 민감도')}
{fig_block(charts['08'], '주가 시나리오')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>90–120</td><td>DE 양산 확대·가이던스 상향·PT 달성+</td></tr>
  <tr><td>Base</td><td>70–95</td><td>PT(~91) 수렴 · A&amp;D 성장 지속</td></tr>
  <tr><td>Bear</td><td>40–60</td><td>국방 예산/프로그램 지연 · 제품 믹스 악화 · 희석</td></tr>
</table>
<p><b>Breaker:</b> 대형 DE 프로그램 취소·지연 · Products 마진 급락 · Top 고객 발주 공백 · 대규모 주식보상/희석</p>
{gloss([
    ("프로그램 리스크", "국방 수주는 예산·일정·프라임 하청 구조에 묶임."),
    ("희석", "적자·SBC로 주식 수가 늘면 EPS 회복이 느려짐."),
])}

<h2>5. 포트폴리오 위치</h2>
{fig_block(charts['10'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>역할</td><td>미보유 <b>워치</b> · Chase #1 · TA 분할OK는 ‘후보’</td></tr>
  <tr><td>금액</td><td>관심 시 <b>$60–80</b> 위성 (CRDO와 택1 감각)</td></tr>
  <tr><td>타이밍</td><td><b>NEO 07-28 이후</b> · 이상적으로 <b>08-06 실적</b> 확인 후</td></tr>
  <tr><td>하지 말 것</td><td>지금 추격 · NEO 이벤트 예산 잠식 · 과열 고점 풀베팅</td></tr>
</table>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>A&amp;D 제품 양산</u>이 성장·마진의 열쇠.
스토리는 강하지만 계좌에는 <b>NEO·현금 다음</b>의 위성. 08-06 전까지는 관망이 기본.</div>

<h2>부록 · 출처</h2>
<p class="small">
nLIGHT Q1 FY2026 earnings release (2026-05-07) · FY2025 10-K (백로그·Top10) ·
yfinance 가격·PT·EPS surprise ({ASOF}).
민감도는 A&amp;D 선형 예시(공식 가이던스 아님). 투자 권유 아님.
</p>
<p class="small">생성: 수익구조분석() · 티커 LASR · 기준 {ASOF} · WeasyPrint + NanumGothic</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_end_market(),
        "03": chart_segment(),
        "04": chart_quarterly(),
        "05": chart_ad_growth(),
        "06": chart_tam_funnel(),
        "07": chart_sensitivity(),
        "08": chart_scenarios(),
        "09": chart_eps_surprise(),
        "10": chart_position(),
    }
    html = build_html(charts)
    html, _px = build_and_insert_price("LASR", CHART_DIR, html)
    if _px.ok:
        print(f"price-charts {_px.candle_path} {_px.momentum_path}")
    else:
        print(f"price-charts SKIP {_px.error}")
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    doc = HTML(filename=str(OUT_HTML))
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        doc.write_pdf(str(p))
        print(f"PDF {p} {p.stat().st_size}")


if __name__ == "__main__":
    main()
