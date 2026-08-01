#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(NEO) — 시각자료 + 초보용 설명 + 전문용어 주석 + WeasyPrint PDF."""

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
ASOF = "2026-07-21"
OUT_PDF = [
    Path("/opt/cursor/artifacts/NEO_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/NEO_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/NEO_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/neo")
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


def chart_business_flow() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.15, 0.65, 1.7, 1.55, "병원·종양\n의사 검체", C["sand"]),
        (2.05, 0.65, 1.8, 1.55, "암 진단\n검사 랩", C["gold"]),
        (4.05, 0.65, 1.85, 1.55, "병리·유전\n·NGS 결과", C["teal2"]),
        (6.1, 0.65, 1.75, 1.55, "보험 급여\n·청구", C["teal"]),
        (8.1, 0.65, 1.65, 1.55, "검사당\n매출", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("비즈니스 한눈에 — 암 조직·혈액을 검사해 결과를 판다", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [171.2, 15.5]
    labels = ["Clinical\n171M (92%)", "Non-clinical\n(Pharma 등)\n15.5M (8%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["teal"], C["gold"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("세그먼트 매출 (Q1'26, 총 187M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    # NGS ~1/3 of clinical
    sizes = [33, 67]
    labels = ["NGS\n~1/3 of Clinical", "비NGS\n임상검사\n~2/3"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["navy"], C["sand"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("Clinical 안 NGS 비중 (Q1'26)", fontproperties=PROP_B, fontsize=11)
    fig.suptitle("NEO 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    return save_fig(fig, "02_segment_mix.png")


def chart_volume_aup() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    ax = axes[0]
    labels = ["Q1'25", "Q1'26"]
    vol = [326, 346]  # thousands of tests
    ax.bar(labels, vol, color=[C["sand"], C["teal"]], width=0.5)
    ax.set_title("임상 검사 건수 (천 건)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("천 건", fontproperties=PROP)
    for i, v in enumerate(vol):
        ax.text(i, v + 3, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 400)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    aup = [459, 495]
    ax.bar(labels, aup, color=[C["sand"], C["navy"]], width=0.5)
    ax.set_title("검사당 평균 매출 AUP (USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("USD / 검사", fontproperties=PROP)
    for i, v in enumerate(aup):
        ax.text(i, v + 8, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 580)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("성장 분해 — 건수(+6%) × 단가(+8%)", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "03_volume_aup.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    layers = [
        (9.2, 8.3, "TAM — 미국 종양 진단·분자검사", "암 병리·유전·NGS·액체생검 전체 풀", C["sand"]),
        (7.6, 6.2, "SAM — 외래·병원 의뢰 랩 시장", "종양내과·병리과가 외부 랩에 맡기는 검사", C["gold"]),
        (5.8, 4.1, "SOM — NEO 매출 가이던스", "FY26 매출 797–803M · Clinical이 ~90%+", C["teal2"]),
        (4.2, 2.0, "핵심 엔진 NGS", "Clinical의 ~1/3 · YoY +26% · PanTracer 등", C["navy"]),
    ]
    for w, y, title, sub, c in layers:
        x0 = (10 - w) / 2
        ax.add_patch(
            FancyBboxPatch(
                (x0, y - 0.85), w, 1.55, boxstyle="round,pad=0.02,rounding_size=0.15",
                facecolor=c, edgecolor="white", linewidth=2, alpha=0.92,
            )
        )
        tc = "white" if c in (C["navy"], C["teal"], C["slate"]) else C["ink"]
        ax.text(5, y + 0.25, title, ha="center", va="center", fontproperties=PROP_B, fontsize=11, color=tc)
        ax.text(5, y - 0.35, sub, ha="center", va="center", fontproperties=PROP, fontsize=8.2, color=tc)
    ax.set_title("시장 깔때기 — 암 진단 랩에서 NEO의 자리", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "04_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    steps = [
        "검사\n볼륨",
        "믹스\n(NGS비중)",
        "AUP\n·급여",
        "매출원가\n·랩 효율",
        "Adj.\nEBITDA",
        "GAAP\n손실",
        "주가\n·멀티플",
    ]
    xs = list(range(len(steps)))
    ys = [1.0, 0.94, 0.90, 0.82, 0.76, 0.70, 0.65]
    ax.plot(xs, ys, "o-", color=C["teal"], lw=2.5, ms=9)
    for i, (s, y) in enumerate(zip(steps, ys)):
        ax.annotate(s, (i, y), textcoords="offset points", xytext=(0, 14), ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0.55, 1.15)
    ax.set_xticks([])
    ax.set_ylabel("상대 기여(개념)", fontproperties=PROP)
    ax.set_title("민감도 사슬 — 볼륨·단가·NGS가 이익을 흔든다", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "05_sensitivity.png")


def chart_scenarios() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    labels = ["Bear", "Base", "Bull"]
    rev = [740, 800, 860]
    ebitda = [40, 56, 70]
    colors = [C["red"], C["gold"], C["teal"]]
    ax = axes[0]
    bars = ax.bar(labels, rev, color=colors, width=0.55)
    ax.set_title("시나리오별 연간 매출 (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 15, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 1000)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    bars = ax.bar(labels, ebitda, color=colors, width=0.55)
    ax.set_title("시나리오별 Adj. EBITDA (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, ebitda):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 85)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("Bear / Base / Bull — FY26 가이던스 중심", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "06_scenarios.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [168, 181, 188, 190, 187]
    oi = [-28, -28, -20, -13, -18]
    x = range(len(labels))
    ax.bar(x, rev, color=C["teal"], alpha=0.85, label="매출 (백만 USD)", width=0.55)
    ax2 = ax.twinx()
    ax2.plot(x, oi, "o-", color=C["gold"], lw=2.2, ms=8, label="영업이익 (백만 USD)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("매출 (백만 USD)", fontproperties=PROP, color=C["teal"])
    ax2.set_ylabel("영업이익 (백만 USD)", fontproperties=PROP, color=C["gold"])
    ax.set_title("분기 추이 — 매출 성장 vs GAAP 영업손실 축소", fontproperties=PROP_B, fontsize=12)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    return save_fig(fig, "07_quarterly.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["~4Q전", "~3Q전", "~2Q전", "최근(Q1'26)"]
    # adjusted-ish small positive EPS beats - actuals 0.03,0.03,0.06,0.01 vs est
    actual = [0.03, 0.03, 0.06, 0.01]
    est = [0.025, 0.024, 0.04, 0.001]
    surprise = [22, 26, 50, 801]  # last one huge % on tiny base
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], est, w, label="예상 EPS", color=C["sand"])
    ax.bar([i + w / 2 for i in x], actual, w, label="실제 EPS", color=C["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("Adj./보고 EPS (USD)", fontproperties=PROP)
    ax.set_title("실적 서프라이즈 — 연속 Beat (소액 EPS 기준)", fontproperties=PROP_B, fontsize=12)
    for i, s in enumerate(surprise):
        ax.text(i + w / 2, actual[i] + 0.003, f"+{s}%", ha="center", fontsize=7, fontproperties=PROP, color=C["green"])
    ax.legend(prop=PROP, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(0.02, 0.02, "주의: 분모(예상)가 작아 %가 과장될 수 있음", transform=ax.transAxes, fontproperties=PROP, fontsize=7, color=C["muted"])
    return save_fig(fig, "08_eps_surprise.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 2.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.35, 0.55, 2.2, 1.7, "코어\nECPG/ASTH", C["navy"]),
        (2.8, 0.55, 2.3, 1.7, "NESR\n분할축", C["teal"]),
        (5.35, 0.55, 2.3, 1.7, "NEO\n예비 1순위\n07-28 관전", C["gold"]),
        (7.9, 0.55, 1.8, 1.7, "현금\n버퍼", C["sand"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=tc)
    ax.set_title("포지션 맥락 — Chase 1위 · 실적 전 추격 금지", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "09_position.png")


def gloss(items: list[tuple[str, str]]) -> str:
    if not items:
        return ""
    lis = "".join(f"<li><span class='term'>{t}</span> — {d}</li>" for t, d in items)
    return f"<div class='gloss'><div class='gloss-title'>이 블록 용어 주석</div><ul>{lis}</ul></div>"


def fig_block(path: Path, caption: str) -> str:
    return f"""
    <figure class="viz">
      <img src="data:image/png;base64,{img_b64(path)}" alt="{caption}"/>
      <figcaption>{caption}</figcaption>
    </figure>
    """


def build_html(charts: dict[str, Path]) -> str:
    css = f"""
    @font-face {{ font-family: 'NanumGothic'; src: url('file://{FONT_REG}'); font-weight: 400; }}
    @font-face {{ font-family: 'NanumGothic'; src: url('file://{FONT_BOLD}'); font-weight: 700; }}
    @page {{
      size: A4; margin: 16mm 14mm 18mm 14mm;
      @bottom-center {{
        content: "수익구조분석(NEO) · {ASOF} · " counter(page) " / " counter(pages);
        font-family: NanumGothic; font-size: 8.5pt; color: #78716c;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: NanumGothic, sans-serif; color: #1c1917; font-size: 10pt; line-height: 1.55; }}
    h1 {{ font-size: 20pt; font-weight: 700; margin: 0 0 4px; color: #0f766e; }}
    h2 {{ font-size: 13.5pt; font-weight: 700; margin: 22px 0 8px; padding-bottom: 4px;
         border-bottom: 2px solid #0f766e; color: #0f766e; page-break-after: avoid; }}
    h3 {{ font-size: 11pt; font-weight: 700; margin: 12px 0 6px; color: #1e3a5f; }}
    .hero {{
      background: linear-gradient(135deg, #0f766e 0%, #1e3a5f 55%, #b8860b 125%);
      color: #fff; padding: 18px; border-radius: 6px; margin-bottom: 16px;
    }}
    .hero h1 {{ color: #fff; }}
    .hero .oneline {{ font-size: 12pt; margin-top: 8px; line-height: 1.45; }}
    .kpi {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .kpi span {{ background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 4px; font-size: 8.5pt; }}
    .block {{ page-break-inside: avoid; margin-bottom: 6px; }}
    p {{ margin: 0 0 8px; }}
    ul {{ margin: 4px 0 10px 18px; padding: 0; }}
    li {{ margin-bottom: 3px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0 12px; font-size: 9pt; }}
    th, td {{ border: 1px solid #d6d3d1; padding: 5px 7px; text-align: left; vertical-align: top; }}
    th {{ background: #0f766e; color: #fff; font-weight: 700; }}
    tr:nth-child(even) td {{ background: #f0fdfa; }}
    .viz {{ margin: 8px 0 12px; text-align: center; }}
    .viz img {{ max-width: 100%; height: auto; }}
    .viz figcaption {{ font-size: 8.5pt; color: #57534e; margin-top: 4px; }}
    .callout {{ background: #f7f3eb; border-left: 4px solid #b8860b; padding: 8px 12px; margin: 8px 0 12px; font-size: 9.5pt; }}
    .gloss {{ background: #fafaf9; border: 1px solid #e7e5e4; padding: 8px 12px; margin: 6px 0 14px; font-size: 8.5pt; color: #44403c; }}
    .gloss-title {{ font-weight: 700; color: #1e3a5f; margin-bottom: 4px; font-size: 9pt; }}
    .gloss ul {{ margin: 0 0 0 14px; }}
    .gloss .term {{ font-weight: 700; color: #0f766e; }}
    .plain {{ background: #ecfdf5; border: 1px solid #a7f3d0; padding: 8px 12px; margin: 6px 0 10px; font-size: 9.5pt; }}
    .plain strong {{ color: #065f46; }}
    .warn {{ background: #fff1f2; border-left: 4px solid #9f1239; padding: 8px 12px; margin: 8px 0; font-size: 9.5pt; }}
    .footer-note {{ font-size: 8pt; color: #78716c; margin-top: 18px; border-top: 1px solid #e7e5e4; padding-top: 8px; }}
    """

    c0 = fig_block(charts["flow"], "그림 0. 비즈니스 흐름 — 검체 → 랩 검사 → 결과 → 보험 청구")
    c1 = fig_block(charts["mix"], "그림 1. Clinical vs Non-clinical · NGS 비중")
    c2 = fig_block(charts["vol"], "그림 2. 검사 건수와 검사당 단가(AUP)")
    c3 = fig_block(charts["funnel"], "그림 3. TAM→SAM→SOM 깔때기")
    c4 = fig_block(charts["sens"], "그림 4. 민감도 사슬")
    c5 = fig_block(charts["scen"], "그림 5. Bear/Base/Bull")
    c6 = fig_block(charts["qtr"], "그림 6. 최근 5분기 매출·영업이익")
    c7 = fig_block(charts["eps"], "그림 7. EPS 서프라이즈")
    c8 = fig_block(charts["pos"], "그림 8. 포트폴리오에서의 NEO")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"/><title>수익구조분석 — NEO (NeoGenomics)</title>
<style>{css}</style></head>
<body>

<div class="hero">
  <h1>수익구조분석 · NEO</h1>
  <div>NeoGenomics, Inc. · 나스닥 · 암(종양) 진단·유전 검사 랩</div>
  <div class="oneline">
    <strong>한 줄 구조:</strong> 병원·종양내과에서 보낸 조직·혈액 검체로
    <em>암 관련 검사를 하고 결과지를 팔아</em> 돈을 법니다. 매출의 약 92%는
    Clinical(임상 검사)이고, 그중 NGS(차세대 염기서열 분석)가 약 1/3을 차지하며
    가장 빨리 자랍니다. Pharma(제약 임상지원)는 작고 지금은 역풍입니다.
  </div>
  <div class="kpi">
    <span>종가 $14.24</span>
    <span>시총 ~$1.85B</span>
    <span>PT $11 / $16.2 / $25</span>
    <span>Q1'26 매출 $187M (+11%)</span>
    <span>Clinical $171M · NGS +26%</span>
    <span>FY26 매출 $797–803M · Adj.EBITDA $55–57M</span>
    <span>실적 07-28 · Chase RR 1위</span>
    <span>기준일 {ASOF}</span>
  </div>
</div>

<div class="plain">
  <strong>이 보고서를 읽는 법 (비전공자용):</strong>
  “어디서 돈을 받는지 → 시장 크기 → 무엇이 흔들리는지 → 좋은/나쁜 숫자 →
  경쟁 → 미리 볼 신호 → 얼마나 살지” 순서입니다.
  각 블록 끝 용어 주석은 중복 없이, 처음 나온 말만 설명합니다.
</div>

{c0}

<div class="block">
<h2>1. 수익 구조 — Clinical · NGS · Pharma</h2>
<div class="plain">
  <strong>쉽게:</strong> 동네 피검사 센터의 ‘암 전문·고급 버전’입니다.
  의사가 “이 종양이 어떤 유전자 변이인지, 어떤 약이 맞는지” 알고 싶을 때
  검체를 NEO 랩으로 보냅니다. NEO는 검사하고 보고서를 주고, 보험·병원에 청구합니다.
  <em>검사 건수 × 검사당 받는 돈(AUP)</em>이 매출의 뼈대입니다.
</div>
{c1}
{c2}

<h3>1-1. Q1'26 숫자</h3>
<table>
  <tr><th>항목</th><th>금액/수치</th><th>YoY</th><th>쉬운 설명</th></tr>
  <tr><td>연결 매출</td><td>$186.7M</td><td>+11%</td><td>가이던스 상회</td></tr>
  <tr><td>Clinical 매출</td><td>$171.2M (~92%)</td><td>+14%</td><td>성장 엔진 · 사실상 본업</td></tr>
  <tr><td> ㄴ 검사 건수</td><td>345,679건</td><td>+6%</td><td>볼륨</td></tr>
  <tr><td> ㄴ AUP</td><td>$495</td><td>+8%</td><td>건당 단가 (Pathline 제외 시 +9%)</td></tr>
  <tr><td> ㄴ NGS</td><td>Clinical의 ~1/3</td><td>+26%</td><td>고마진·고성장 축</td></tr>
  <tr><td>Non-clinical</td><td>$15.5M (~8%)</td><td>−15%</td><td>Pharma 부진, ODx는 일부 상쇄</td></tr>
  <tr><td>Adjusted EBITDA</td><td>~$9M</td><td>+27%</td><td>아직 작지만 개선 중</td></tr>
</table>

<p>
중요: <strong>GAAP로는 아직 적자</strong>입니다(Q1 영업손실 ~$18M, 연간도 순손실).
시장이 보는 스토리는 “적자 축소 + Adj.EBITDA 확대 + NGS 믹스 개선”입니다.
매출총이익률(보고) ~43%로, 제약(INDV)보다 낮고 케어플랫폼(ASTH)보다 높습니다 —
<strong>랩 인건·시약·장비가 원가</strong>인 구조입니다.
</p>

{c6}

<h3>1-2. 연간 추이</h3>
<table>
  <tr><th>연도</th><th>매출</th><th>매출총이익</th><th>영업이익</th><th>순이익</th></tr>
  <tr><td>FY2022</td><td>$510M</td><td>$188M</td><td>−$153M</td><td>−$144M</td></tr>
  <tr><td>FY2023</td><td>$592M</td><td>$245M</td><td>−$97M</td><td>−$88M</td></tr>
  <tr><td>FY2024</td><td>$661M</td><td>$290M</td><td>−$85M</td><td>−$79M</td></tr>
  <tr><td>FY2025</td><td>$727M</td><td>$314M</td><td>−$88M</td><td>−$108M</td></tr>
</table>

<div class="callout">
  <strong>FY26 가이던스(상향 후):</strong> 매출 <strong>$797–803M</strong>(~+10%) ·
  Adj. EBITDA <strong>$55–57M</strong>(+27–31%) · 순손실 <strong>$(63)–$(50)M</strong>(적자 축소).
  PanTracer LBx(액체생검)·RaDaR 등 신제품이 상반·하반 기여 변수.
</div>

{gloss([
    ("Clinical Services", "환자를 진료하는 의사·병원을 위한 진단 검사 사업. NEO 매출의 대부분."),
    ("Pharma / Non-clinical", "제약사 임상시험·동반진단 등을 지원하는 비임상 매출. 비중 작음."),
    ("AUP (Average Unit Price / Average revenue per test)", "검사 1건당 평균 매출. 볼륨과 함께 탑라인을 결정."),
    ("NGS (Next-Generation Sequencing)", "유전자를 대량·빠르게 읽는 차세대 염기서열 분석. 비싸고 정보량이 많음."),
    ("Pathline", "인수로 들어온 검사/볼륨. ‘동일점포(same-store)’ 성장과 구분해 봄."),
    ("Adjusted EBITDA", "일회성 등을 조정한 영업 현금창출력. GAAP 적자여도 이 지표는 흑자일 수 있음."),
    ("GAAP", "법정 회계 기준. NEO는 아직 순손실 구간."),
])}
</div>

<div class="block">
<h2>2. 시장 깔때기 — TAM → SAM → SOM</h2>
<div class="plain">
  <strong>쉽게:</strong> 암 환자가 늘고, 치료 전에 “유전자 지도”를 보는 검사가 늘면
  NEO 같은 랩의 파이도 커집니다. 다만 보험이 얼마를 인정해주느냐가 실제 매출을 가릅니다.
</div>
{c3}

<table>
  <tr><th>단계</th><th>대략</th><th>정의</th><th>헷갈리기 쉬운 점</th></tr>
  <tr>
    <td>TAM</td>
    <td>미국 종양 진단·분자검사</td>
    <td>병리·유전·NGS·액체생검 전체</td>
    <td>TAM ≠ NEO 매출</td>
  </tr>
  <tr>
    <td>SAM</td>
    <td>외부 의 랩이 가져가는 검사</td>
    <td>병원 자체 랩이 아닌 아웃소싱</td>
    <td>대형 병원 내재화와 경쟁</td>
  </tr>
  <tr>
    <td>SOM</td>
    <td>FY26 ~$0.8B 가이던스</td>
    <td>NEO가 실제로 청구하는 규모</td>
    <td>시총~$1.85B와 혼동 금지</td>
  </tr>
  <tr>
    <td>성장 스위치</td>
    <td>NGS 침투 + AUP</td>
    <td>같은 환자라도 NGS로 바꾸면 단가↑</td>
    <td>급여(MolDx 등) 지연 시 스위치 멈춤</td>
  </tr>
</table>

{gloss([
    ("TAM / SAM / SOM", "전체 시장 / 팔 수 있는 시장 / 실제로 가져가는 규모."),
    ("액체생검 (Liquid biopsy)", "조직 대신 혈액 등으로 암 신호를 보는 검사. PanTracer LBx 등이 여기."),
    ("MolDx", "메디케어 분자진단 급여 결정 프로그램. 새 검사의 ‘보험이 돈 주나’를 좌우."),
    ("침투율", "대상 검사 중 NGS 같은 고단가 검사가 차지하는 비율."),
])}
</div>

<div class="block">
<h2>3. 민감도 사슬 — 무엇이 이익을 흔드나</h2>
<div class="plain">
  <strong>쉽게:</strong> 식당으로 치면 “손님 수(볼륨) × 객단가(AUP)”이고,
  고급 메뉴(NGS) 비중이 늘면 객단가가 올라갑니다. 주방이 비효율이면 원가가 먹어치웁니다.
</div>
{c4}

<table>
  <tr><th>단계</th><th>좋게 나오면</th><th>나쁘게 나오면</th></tr>
  <tr><td>① 검사 볼륨</td><td>점유·영업 확장</td><td>의뢰 둔화, 경쟁 이탈</td></tr>
  <tr><td>② NGS 믹스</td><td>단가·마진↑</td><td>저단가 검사만 늘면 성장 밋밋</td></tr>
  <tr><td>③ AUP·급여</td><td>RCM·수가 개선</td><td>급여 삭감·거절·회수 지연</td></tr>
  <tr><td>④ 랩 원가</td><td>자동화·수율↑</td><td>시약·인건비 인플레</td></tr>
  <tr><td>⑤ Adj. EBITDA</td><td>가이던스 $55–57M</td><td>마진 정체</td></tr>
  <tr><td>⑥ GAAP 손실</td><td>적자 축소 스토리</td><td>손실 재확대 → 멀티플↓</td></tr>
  <tr><td>⑦ Pharma</td><td>하반 회복 시 보너스</td><td>추가 역풍은 이미 −15%</td></tr>
</table>

{gloss([
    ("RCM (Revenue Cycle Management)", "청구·심사·수납을 관리해 ‘검사했다’를 ‘돈으로’ 바꾸는 업무."),
    ("급여 / Reimbursement", "보험이 검사를 얼마로 인정해 주느냐."),
    ("믹스", "고단가·저단가 검사 구성 변화로 평균 단가가 바뀌는 효과."),
])}
</div>

<div class="block">
<h2>4. Bear / Base / Bull — 숫자 시나리오</h2>
<div class="plain">
  <strong>쉽게:</strong> FY26 가이던스(매출 ~$800M, Adj.EBITDA ~$56M)를 Base로 둡니다.
</div>
{c5}

<table>
  <tr><th>시나리오</th><th>가정</th><th>매출</th><th>Adj.EBITDA</th><th>주가 함의(개념)</th></tr>
  <tr>
    <td>Bear</td>
    <td>볼륨·AUP 둔화, Pharma 추가 약세, 가이던스 하회</td>
    <td>~$740M</td>
    <td>~$40M</td>
    <td>$9–12 (PT 저점 $11 근처)</td>
  </tr>
  <tr>
    <td>Base</td>
    <td>가이던스 달성, NGS 20%대 성장 유지</td>
    <td>~$800M</td>
    <td>~$56M</td>
    <td>$15–18 (PT 평균 $16.2)</td>
  </tr>
  <tr>
    <td>Bull</td>
    <td>NGS·LBx 가속, 추가 상향, 적자 축소 가속</td>
    <td>~$860M+</td>
    <td>~$70M</td>
    <td>$20–25 (PT 고점)</td>
  </tr>
</table>

<p>
현재가 <strong>$14.24</strong> vs PT 평균 <strong>$16.2</strong>(+14%) · 고점 PT $25.
저점 PT $11은 하방도 열려 있음. Chase RR 1위인 이유는
<strong>연속 Beat + PT 소폭 여유 + 아직 고점 과열이 덜함</strong> 조합입니다.
다만 GAAP 적자라 실적 톤이 조금만 나빠도 변동성이 큽니다.
</p>

{c7}
<p>
최근 분기 EPS는 연속 Beat이나, 절대 EPS가 매우 작아 <strong>% 서프라이즈가 과장</strong>될 수 있습니다.
07-28에는 Beat 여부보다 <strong>Clinical 성장·NGS·AUP·가이던스 톤</strong>이 중요합니다.
</p>

{gloss([
    ("Bear / Base / Bull", "비관·기본·낙관."),
    ("Beat", "실제 &gt; 컨센서스."),
])}
</div>

<div class="block">
<h2>5. 경쟁·포지션</h2>
<div class="plain">
  <strong>쉽게:</strong> 암 유전자 검사 시장에는 대형 진단사·전문 NGS 업체·병원 자체 랩이 있습니다.
  NEO는 “폭넓은 종양 메뉴 + NGS 가속”으로 점유를 뺏는 쪽입니다.
</div>
<table>
  <tr><th>전선</th><th>NEO</th><th>압력</th><th>관찰</th></tr>
  <tr>
    <td>Clinical / NGS</td>
    <td>점유 확대, PanTracer</td>
    <td>경쟁 랩, 병원 내재화</td>
    <td>볼륨, NGS %, AUP</td>
  </tr>
  <tr>
    <td>급여</td>
    <td>MolDx·수가</td>
    <td>삭감·지연</td>
    <td>신제품 급여 코멘트</td>
  </tr>
  <tr>
    <td>Pharma</td>
    <td>비중 小, 역풍</td>
    <td>제약 R&amp;D 사이클</td>
    <td>하반 회복 여부</td>
  </tr>
</table>
{gloss([
    ("동반진단", "특정 약이 환자에게 맞는지 가리는 검사. Pharma·Clinical 경계에 걸침."),
])}
</div>

<div class="block">
<h2>6. 선행 지표</h2>
<ul>
  <li><strong>Clinical 매출 성장 · 검사 건수 · AUP</strong></li>
  <li><strong>NGS 매출 성장률·Clinical 내 비중</strong></li>
  <li><strong>Adj. EBITDA 마진</strong></li>
  <li><strong>Pharma/Non-clinical 회복 여부</strong></li>
  <li><strong>신제품(PanTracer LBx, RaDaR) 기여</strong></li>
  <li><strong>07-28 실적</strong> — 컨센서스 EPS ~$0.03, 매출 ~$197M</li>
</ul>
{gloss([
    ("선행 지표", "실적 전 방향성을 가늠하는 신호."),
])}
</div>

<div class="block">
<h2>7. 비중 상한 · Thesis Breakers</h2>
{c8}
<div class="plain">
  <strong>쉽게:</strong> 오늘 Chase 1위지만, <strong>아직 보유 중이 아니고 07-28 실적 직전</strong>입니다.
  계획상 수요일 예비금의 우선 후보이나 <strong>실적 전 추격은 금지</strong>입니다.
</div>
<table>
  <tr><th>항목</th><th>권고</th><th>이유</th></tr>
  <tr><td>실적 전 (07-28)</td><td><strong>매수 금지</strong></td><td>이벤트 리스크 · GAAP 적자 변동성</td></tr>
  <tr><td>실적 후</td><td>톤 양호 시 <strong>반만~1주</strong></td><td>예비금 버킷, KNSA보다 우선</td></tr>
  <tr><td>진입 밴드(개념)</td><td>$12.5–14.5 눌림 선호</td><td>추격보다 조정 후</td></tr>
  <tr><td>비중 상한</td><td>총자산 ~8–12%</td><td>소액 포트·적자 기업 한도</td></tr>
</table>

<div class="warn">
  <strong>Thesis Breakers:</strong>
  <ul>
    <li>Clinical/NGS 성장 급락 또는 AUP 하락</li>
    <li>FY 매출·Adj.EBITDA 가이던스 하향</li>
    <li>급여·MolDx 악화로 신제품 기여 지연</li>
    <li>현금소진·희석(증자) 리스크 부각</li>
    <li>연속 Beat가 Miss로 전환</li>
  </ul>
</div>

{gloss([
    ("반만", "원래 사려던 수량의 절반만 먼저 사는 것."),
    ("Thesis Breaker", "매수·보유 논리를 깨는 사건."),
])}
</div>

<div class="block">
<h2>8. 한계 · 출처</h2>
<ul>
  <li>시가·PT·일부 재무: Yahoo Finance 집계.</li>
  <li>세그먼트·AUP·가이던스: NeoGenomics IR / Q1'26 실적자료.</li>
  <li>TAM·시나리오는 근사·작업용. 투자 권고 아님.</li>
</ul>
<div class="footer-note">
  생성: 수익구조분석() · 티커 NEO · 기준 {ASOF} · WeasyPrint + NanumGothic
</div>
</div>

</body></html>
"""
    return html


def main() -> None:
    charts = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "vol": chart_volume_aup(),
        "funnel": chart_tam_funnel(),
        "sens": chart_sensitivity(),
        "scen": chart_scenarios(),
        "qtr": chart_quarterly(),
        "eps": chart_eps_surprise(),
        "pos": chart_position(),
    }
    html = build_html(charts)
    html, _px = build_and_insert_price("NEO", CHART_DIR, html)
    if _px.ok:
        print(f"price-charts {_px.candle_path} {_px.momentum_path}")
    else:
        print(f"price-charts SKIP {_px.error}")
    OUT_HTML.write_text(html, encoding="utf-8")
    print("HTML", OUT_HTML, OUT_HTML.stat().st_size)
    for out in OUT_PDF:
        out.parent.mkdir(parents=True, exist_ok=True)
        HTML(string=html, base_url=str(CHART_DIR)).write_pdf(out)
        print("PDF", out, out.stat().st_size)


if __name__ == "__main__":
    main()
