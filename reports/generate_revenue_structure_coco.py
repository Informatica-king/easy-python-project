#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(COCO) — 시각자료 + 초보용 설명 + 전문용어 주석 + WeasyPrint PDF."""

from __future__ import annotations

import base64
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from weasyprint import HTML

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
ASOF = "2026-07-22"
OUT_PDF = [
    Path("/opt/cursor/artifacts/COCO_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/COCO_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/COCO_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/COCO_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/coco")
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
    fig, ax = plt.subplots(figsize=(9.2, 3.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    boxes = [
        (0.1, 0.7, 1.8, 1.6, "코코넛\n원액·물류", C["sand"]),
        (2.1, 0.7, 1.85, 1.6, "브랜드\nVita Coco\n코코넛워터", C["gold"]),
        (4.15, 0.7, 1.75, 1.6, "Private Label\n리테일 PB", C["teal2"]),
        (6.1, 0.7, 1.75, 1.6, "클럽·마트\n·편의·이커머스", C["teal"]),
        (8.05, 0.7, 1.7, 1.6, "순매출\n·총이익", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("비즈니스 한눈에 — 코코넛워터를 브랜드·PB로 판다", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [140.6, 33.2, 6.0]
    labels = ["Coconut Water\n140.6M (78%)", "Private Label\n33.2M (18%)", "Other\n6.0M (3%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["navy"], C["teal"], C["gold"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("제품별 매출 (Q1'26, 총 179.8M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["Coconut\nWater", "Private\nLabel", "Other"]
    yoy = [42, 28, 5]
    bars = ax.bar(cats, yoy, color=[C["navy"], C["teal"], C["gold"]], width=0.55)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("제품별 YoY 성장 (Q1'26)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, yoy):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"+{v}%", ha="center", fontproperties=PROP_B, fontsize=9)
    ax.set_ylim(0, 55)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("COCO 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_geo_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    sizes = [148.2, 31.6]
    labels = ["Americas\n148.2M (82%)", "International\n31.6M (18%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["teal"], C["gold"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("지역 매출 (Q1'26)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["Americas", "International"]
    yoy = [32, 72]
    gm = [41.1, 34.4]
    x = range(len(cats))
    bars = ax.bar([i - 0.18 for i in x], yoy, 0.35, label="YoY %", color=C["navy"])
    bars2 = ax.bar([i + 0.18 for i in x], gm, 0.35, label="GM %", color=C["teal2"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(cats, fontproperties=PROP)
    ax.set_ylabel("%", fontproperties=PROP)
    ax.set_title("지역 성장 vs 총이익률", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, yoy):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"+{v}%", ha="center", fontproperties=PROP, fontsize=8)
    for b, v in zip(bars2, gm):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v}%", ha="center", fontproperties=PROP, fontsize=8)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.set_ylim(0, 90)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "03_geo_mix.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    rows = [
        (0.5, 3.6, 9.0, 1.0, "TAM — 글로벌 수분·기능성 음료 (매우 큼)", C["sand"]),
        (1.2, 2.4, 7.6, 1.0, "SAM — 코코넛워터·식물성 워터 카테고리", C["gold"]),
        (2.0, 1.2, 6.0, 1.0, "SOM — Vita Coco + PL (FY26 가이던스 720–735M)", C["teal"]),
    ]
    for x, y, w, h, t, c in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9.5, color=tc)
    ax.set_title("시장 깔때기 — 카테고리 침투가 성장 엔진", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "04_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    boxes = [
        (0.15, 0.7, 1.4, 1.6, "① 카테고리\n수요·침투", C["sand"]),
        (1.7, 0.7, 1.4, 1.6, "② 브랜드\n볼륨·CE", C["gold"]),
        (3.25, 0.7, 1.4, 1.6, "③ 순가격\n·프로모", C["teal2"]),
        (4.8, 0.7, 1.4, 1.6, "④ 해상운임\n·원가·관세", C["teal"]),
        (6.35, 0.7, 1.4, 1.6, "⑤ 총이익\n·GM%", C["navy"]),
        (7.9, 0.7, 1.7, 1.6, "⑥ Adj.EBITDA\n·EPS", C["slate"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8, color=tc)
    ax.set_title("민감도 사슬 — 무엇이 이익을 흔드나", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "05_sensitivity.png")


def chart_scenarios() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    labels = ["Bear", "Base", "Bull"]
    rev = [680, 728, 780]
    ebitda = [115, 135, 155]
    colors = [C["red"], C["teal"], C["gold"]]

    ax = axes[0]
    bars = ax.bar(labels, rev, color=colors, width=0.55)
    ax.set_title("시나리오별 매출 (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 8, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 900)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    bars = ax.bar(labels, ebitda, color=colors, width=0.55)
    ax.set_title("시나리오별 Adj.EBITDA (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, ebitda):
        ax.text(b.get_x() + b.get_width() / 2, v + 3, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 190)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("Bear / Base / Bull — FY26 가이던스 중심", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "06_scenarios.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [130.9, 168.8, 182.3, 127.8, 179.8]
    oi = [19.3, 25.1, 27.9, 10.2, 33.6]
    x = range(len(labels))
    ax.bar(x, rev, color=C["teal"], alpha=0.85, label="매출 (백만 USD)", width=0.55)
    ax2 = ax.twinx()
    ax2.plot(x, oi, "o-", color=C["gold"], lw=2.2, ms=8, label="영업이익 (백만 USD)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("매출 (백만 USD)", fontproperties=PROP, color=C["teal"])
    ax2.set_ylabel("영업이익 (백만 USD)", fontproperties=PROP, color=C["gold"])
    ax.set_title("분기 추이 — 여름·프로모 계절성 vs 마진 개선", fontproperties=PROP_B, fontsize=12)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    return save_fig(fig, "07_quarterly.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    actual = [0.31, 0.42, 0.40, 0.14, 0.53]
    est = [0.22, 0.36, 0.33, 0.12, 0.33]
    surprise = [42, 15, 23, 17, 62]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], est, w, label="예상 EPS", color=C["sand"])
    ax.bar([i + w / 2 for i in x], actual, w, label="실제 EPS", color=C["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("EPS (USD)", fontproperties=PROP)
    ax.set_title("실적 서프라이즈 — 연속 EPS Beat", fontproperties=PROP_B, fontsize=12)
    for i, s in enumerate(surprise):
        ax.text(i + w / 2, actual[i] + 0.015, f"+{s}%", ha="center", fontsize=8, fontproperties=PROP, color=C["green"])
    ax.legend(prop=PROP, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "08_eps_surprise.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 2.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.3, 0.55, 2.2, 1.7, "코어\nECPG/ASTH", C["navy"]),
        (2.7, 0.55, 2.0, 1.7, "NEO≫AMRX\n예비금", C["teal"]),
        (4.9, 0.55, 2.3, 1.7, "COCO\n워치\n(실적 전)", C["gold"]),
        (7.5, 0.55, 2.1, 1.7, "현금\n버퍼", C["sand"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=tc)
    ax.set_title("포지션 맥락 — 워치 · 07-23 실적 전 추격 금지", fontproperties=PROP_B, fontsize=12, pad=6)
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
        content: "수익구조분석(COCO) · {ASOF} · " counter(page) " / " counter(pages);
        font-family: NanumGothic; font-size: 8.5pt; color: #78716c;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: NanumGothic, sans-serif; color: #1c1917; font-size: 10pt; line-height: 1.55; }}
    h1 {{ font-size: 20pt; font-weight: 700; margin: 0 0 4px; color: #1e3a5f; }}
    h2 {{ font-size: 13.5pt; font-weight: 700; margin: 22px 0 8px; padding-bottom: 4px;
         border-bottom: 2px solid #1e3a5f; color: #1e3a5f; page-break-after: avoid; }}
    h3 {{ font-size: 11pt; font-weight: 700; margin: 12px 0 6px; color: #0f766e; }}
    .hero {{
      background: linear-gradient(135deg, #1e3a5f 0%, #0f766e 55%, #b8860b 125%);
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
    th {{ background: #1e3a5f; color: #fff; font-weight: 700; }}
    tr:nth-child(even) td {{ background: #f0fdfa; }}
    .viz {{ margin: 8px 0 12px; text-align: center; }}
    .viz img {{ max-width: 100%; height: auto; }}
    .viz figcaption {{ font-size: 8.5pt; color: #57534e; margin-top: 4px; }}
    .callout {{ background: #f7f3eb; border-left: 4px solid #b8860b; padding: 8px 12px; margin: 8px 0 12px; font-size: 9.5pt; }}
    .gloss {{ background: #fafaf9; border: 1px solid #e7e5e4; padding: 8px 12px; margin: 6px 0 14px; font-size: 8.5pt; color: #44403c; }}
    .gloss-title {{ font-weight: 700; color: #0f766e; margin-bottom: 4px; font-size: 9pt; }}
    .gloss ul {{ margin: 0 0 0 14px; }}
    .gloss .term {{ font-weight: 700; color: #1e3a5f; }}
    .plain {{ background: #eff6ff; border: 1px solid #bfdbfe; padding: 8px 12px; margin: 6px 0 10px; font-size: 9.5pt; }}
    .plain strong {{ color: #1e3a5f; }}
    .warn {{ background: #fff1f2; border-left: 4px solid #9f1239; padding: 8px 12px; margin: 8px 0; font-size: 9.5pt; }}
    .footer-note {{ font-size: 8pt; color: #78716c; margin-top: 18px; border-top: 1px solid #e7e5e4; padding-top: 8px; }}
    """

    c0 = fig_block(charts["flow"], "그림 0. 비즈니스 흐름 — 브랜드·PB·유통 채널")
    c1 = fig_block(charts["mix"], "그림 1. 제품 믹스와 성장률")
    c2 = fig_block(charts["geo"], "그림 2. 지역 믹스·마진")
    c3 = fig_block(charts["funnel"], "그림 3. TAM→SAM→SOM 깔때기")
    c4 = fig_block(charts["sens"], "그림 4. 민감도 사슬")
    c5 = fig_block(charts["scen"], "그림 5. Bear/Base/Bull")
    c6 = fig_block(charts["qtr"], "그림 6. 최근 5분기 매출·영업이익")
    c7 = fig_block(charts["eps"], "그림 7. EPS 서프라이즈")
    c8 = fig_block(charts["pos"], "그림 8. 포트폴리오에서의 COCO")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"/><title>수익구조분석 — COCO (Vita Coco)</title>
<style>{css}</style></head>
<body>

<div class="hero">
  <h1>수익구조분석 · COCO</h1>
  <div>The Vita Coco Company, Inc. · 나스닥 · 코코넛워터·식물성 음료</div>
  <div class="oneline">
    <strong>한 줄 구조:</strong> 매출의 약 <em>78%</em>가 브랜드 Vita Coco 코코넛워터이고,
    <em>Private Label(~18%)</em>이 리테일 PB로 볼륨을 받치며,
    Americas(~82%)가 본진·마진, International(~18%)이 고성장 보조입니다.
    성장 엔진은 <strong>카테고리 침투 + 브랜드 볼륨 + 순가격</strong>, 마진은 해상운임·원가·관세에 민감합니다.
  </div>
  <div class="kpi">
    <span>종가 ~$75.89</span>
    <span>시총 ~$4.3B</span>
    <span>PT $65 / $76.7 / $85</span>
    <span>Q1'26 매출 $180M (+37%)</span>
    <span>CW $141 · PL $33 · Other $6</span>
    <span>GM 39.9% · EPS $0.50 (+62% Beat)</span>
    <span>FY26 매출 $720–735M</span>
    <span>실적 07-23</span>
    <span>기준일 {ASOF}</span>
  </div>
</div>

<div class="plain">
  <strong>이 보고서를 읽는 법 (비전공자용):</strong>
  “어디서 돈을 받는지 → 시장 크기 → 무엇이 흔들리는지 → 좋은/나쁜 숫자 →
  경쟁 → 미리 볼 신호 → 얼마나 살지” 순서입니다.
  각 블록 끝 용어 주석은 처음 나온 말만 설명합니다.
</div>

{c0}

<div class="block">
<h2>1. 수익 구조 — 제품·지역·마진</h2>
<div class="plain">
  <strong>쉽게:</strong> 편의점·코스트코 선반의
  (1) <em>Vita Coco 브랜드 코코넛워터</em>,
  (2) 마트 자체 브랜드(PB) 코코넛워터/오일,
  (3) 코코넛 밀크·오일·PWR LIFT 등 <em>기타</em>가 한 회사 안에 있습니다.
  지역으로는 미주가 대부분, 유럽·중동 등이 빠르게 붙는 구조입니다.
</div>
{c1}
{c2}

<h3>1-1. Q1'26 제품 × 지역 (백만 USD)</h3>
<table>
  <tr><th>구분</th><th>Americas</th><th>International</th><th>합계</th><th>쉬운 설명</th></tr>
  <tr>
    <td>Vita Coco Coconut Water</td>
    <td>$118.0</td>
    <td>$22.5</td>
    <td><strong>$140.6 (78%)</strong></td>
    <td>브랜드 핵심. CE 볼륨 +32%, 순매출 +42%</td>
  </tr>
  <tr>
    <td>Private Label</td>
    <td>$24.4</td>
    <td>$8.8</td>
    <td>$33.2 (18%)</td>
    <td>리테일 PB. 국제 +86%, 미주 +15%. Q2부터 신규 Tetra Pak 계정 출하 예정</td>
  </tr>
  <tr>
    <td>Other</td>
    <td>$5.7</td>
    <td>$0.2</td>
    <td>$6.0 (3%)</td>
    <td>코코넛 밀크·오일·PWR LIFT 등</td>
  </tr>
  <tr>
    <td><strong>합계</strong></td>
    <td><strong>$148.2 (82%)</strong></td>
    <td><strong>$31.6 (18%)</strong></td>
    <td><strong>$179.8</strong></td>
    <td>YoY +37% · Americas GM 41.1% · Int'l GM 34.4% · 연결 GM 39.9%</td>
  </tr>
</table>

<p>
핵심 메시지: <strong>탑라인(+37%)과 마진(+320bp)이 같이 개선</strong>.
가격↑ + 해상운임↓가 GM을 밀고, 브랜드 볼륨이 성장을 끌었습니다.
단, 경영진은 Q1에 대형 리테일 프로모가 작년 Q2에서 Q1로 당겨진 효과가 있다고 언급 — <strong>Q2 비교 시 기저·타이밍</strong>을 봐야 합니다.
</p>

{c6}

<h3>1-2. 연간 추이</h3>
<table>
  <tr><th>연도</th><th>매출</th><th>매출총이익</th><th>영업이익</th><th>순이익</th></tr>
  <tr><td>FY2022</td><td>$428M</td><td>$103M</td><td>$3M</td><td>$8M</td></tr>
  <tr><td>FY2023</td><td>$494M</td><td>$181M</td><td>$56M</td><td>$47M</td></tr>
  <tr><td>FY2024</td><td>$516M</td><td>$199M</td><td>$74M</td><td>$56M</td></tr>
  <tr><td>FY2025</td><td>$610M</td><td>$223M</td><td>$83M</td><td>$71M</td></tr>
</table>

<p>
FY22 이후 매출·이익이 계단식으로 개선. FY25 매출 ~$610M(+18% vs FY24).
대차: <strong>부채 거의 없음 · 현금 ~$202M</strong>(Q1'26 말). 재고는 강한 출하로 $111M→$86M 감소.
자사주: 프로그램 한도 $65M, YTD ~$20M 매입·잔여 ~$21M(4/28 기준).
</p>

<div class="callout">
  <strong>FY26 가이던스 (Q1 후 상향):</strong>
  순매출 <strong>$720–735M</strong>(직전 $680–700M) ·
  Adj.EBITDA <strong>$132–138M</strong>.
  드라이버: 브랜드 중고티어 성장 + Private Label 신규·회복 계정.
</div>

{gloss([
    ("Coconut Water / CE", "코코넛워터. CE(Case Equivalent)는 케이스 환산 물량 단위."),
    ("Private Label (PB)", "마트·클럽의 자체 브랜드 상품. 마진은 브랜드보다 얇은 편."),
    ("Americas / International", "미주(미·캐나다 중심) vs 그 외(영국·독일 등)."),
    ("GM / bp", "총이익률. 1bp=0.01%p. +320bp ≈ +3.2%p."),
    ("Adj.EBITDA", "일회성·비현금 항목을 조정한 영업현금성 이익 지표."),
    ("PWR LIFT", "단백질 주입 피트니스 음료. Americas 전용."),
])}
</div>

<div class="block">
<h2>2. 시장 깔때기 — TAM → SAM → SOM</h2>
<div class="plain">
  <strong>쉽게:</strong> “모든 음료”가 아니라,
  사람들이 수분 보충을 코카콜라 대신 <em>코코넛워터</em>로 바꾸는 구간이 COCO의 놀이터입니다.
</div>
{c3}

<table>
  <tr><th>단계</th><th>대략</th><th>정의</th><th>헷갈리기 쉬운 점</th></tr>
  <tr>
    <td>TAM</td>
    <td>수분·기능성 음료 전체</td>
    <td>물·스포츠드링크·기능성</td>
    <td>TAM ≠ COCO 매출</td>
  </tr>
  <tr>
    <td>SAM</td>
    <td>코코넛·식물성 워터</td>
    <td>카테고리 침투·가구 침투율</td>
    <td>카테고리 성장이 브랜드 성장의 상한</td>
  </tr>
  <tr>
    <td>SOM</td>
    <td>FY26 $720–735M</td>
    <td>Vita Coco + PL + Other</td>
    <td>시총~$4.3B와 혼동 금지</td>
  </tr>
  <tr>
    <td>전환 스토리</td>
    <td>침투↑ · 가격↑ · GM↑</td>
    <td>리더로서 카테고리 투자</td>
    <td>프로모 타이밍이 분기 왜곡</td>
  </tr>
</table>

{gloss([
    ("TAM / SAM / SOM", "전체 시장 / 팔 수 있는 시장 / 실제로 가져가는 규모."),
    ("가구 침투 (HH penetration)", "한 번이라도 산 가구 비율. 늘수록 신규 수요↑."),
])}
</div>

<div class="block">
<h2>3. 민감도 사슬 — 무엇이 이익을 흔드나</h2>
<div class="plain">
  <strong>쉽게:</strong> 사람들이 코코넛워터를 더 마시면 볼륨이 늘고,
  할인·프로모가 세면 순가격이 깎이며,
  배·원재료·관세가 비싸면 원가가 올라 GM이 흔들립니다.
</div>
{c4}

<table>
  <tr><th>단계</th><th>좋게 나오면</th><th>나쁘게 나오면</th></tr>
  <tr><td>① 카테고리 수요</td><td>침투·소비 횟수↑</td><td>패션성 수요 둔화</td></tr>
  <tr><td>② 브랜드 CE</td><td>미주·유럽 동시 성장</td><td>프로모 기저로 QoQ/YoY 왜곡</td></tr>
  <tr><td>③ 순가격</td><td>가격↑·믹스 개선</td><td>과한 인센티브·채널 할인</td></tr>
  <tr><td>④ 원가·운임·관세</td><td>해상운임↓ 지속</td><td>고원가 재고 소진·관세↑</td></tr>
  <tr><td>⑤ GM</td><td>40% 전후 유지/확대</td><td>믹스 악화로 재축소</td></tr>
  <tr><td>⑥ Adj.EBITDA·EPS</td><td>가이던스 재상향</td><td>SG&A(마케팅) 과투자로 레버리지↓</td></tr>
</table>

<p>
과거 패턴: <strong>EPS 연속 Beat</strong>(최근 5분기).
07-23(Q2)은 컨센서스 EPS ~$0.55 · 매출 ~$210M.
Q1에 프로모가 앞당겨졌으므로 <strong>매출 YoY는 좋아도 QoQ/가이던스 톤</strong>을 같이 봐야 합니다.
</p>

{gloss([
    ("순가격 (Net pricing)", "할인·리베이트·프로모 차감 후 실제 받는 가격."),
    ("해상운임 (Ocean freight)", "해외 원액·완제품 선박 운송비. GM에 직접 영향."),
    ("SG&A", "판매·일반관리비. 마케팅·인건비·유통 수수료 포함."),
])}
</div>

<div class="block">
<h2>4. Bear / Base / Bull — 숫자 시나리오</h2>
<div class="plain">
  <strong>쉽게:</strong> 회사 FY26 매출 가이던스 $720–735M을 Base로 두고,
  브랜드 둔화 vs 침투 가속을 갈라 작업용 시나리오를 잡았습니다.
</div>
{c5}

<table>
  <tr><th>시나리오</th><th>가정</th><th>매출</th><th>Adj.EBITDA</th><th>주가 함의</th></tr>
  <tr>
    <td>Bear</td>
    <td>프로모 기저·PL 실망·원가/관세 재악화, 가이던스 하향</td>
    <td>~$680M</td>
    <td>~$115M</td>
    <td>$55–65 (PT 저점권)</td>
  </tr>
  <tr>
    <td>Base</td>
    <td>가이던스 달성, GM ~중후반 30%대, 브랜드 중고성장</td>
    <td>~$728M</td>
    <td>~$135M</td>
    <td>$72–80 (PT 평균~$77)</td>
  </tr>
  <tr>
    <td>Bull</td>
    <td>침투 가속·국제 고성장·PL 회복, 가이던스 재상향</td>
    <td>~$780M+</td>
    <td>~$155M+</td>
    <td>$82–90 (PT 고점 $85+)</td>
  </tr>
</table>

<p>
현재가 <strong>~$75.89</strong> vs PT 평균 <strong>~$76.7</strong>(거의 평형) · 저점 $65 · 고점 $85.
시총/매출 배수·성장 스토리가 이미 상당 반영 → <strong>실적·가이던스 서프라이즈가 추가 상승의 열쇠</strong>.
</p>

{c7}

{gloss([
    ("Bear / Base / Bull", "비관·기본·낙관."),
    ("Beat / Miss", "예상보다 좋음 / 나쁨."),
])}
</div>

<div class="block">
<h2>5. 경쟁·포지션</h2>
<div class="plain">
  <strong>쉽게:</strong> 코카콜라·펩시 같은 거대 음료사와 “수분” 예산으로 경쟁하고,
  같은 선반에서는 다른 코코넛워터·스포츠드링크와 싸웁니다.
</div>
<table>
  <tr><th>전선</th><th>COCO</th><th>압력</th><th>관찰</th></tr>
  <tr>
    <td>브랜드 코코넛워터</td>
    <td>미주 카테고리 리더</td>
    <td>후발 브랜드·PL 가격</td>
    <td>점유·가구 침투·순가격</td>
  </tr>
  <tr>
    <td>Private Label</td>
    <td>대형 리테일 공급</td>
    <td>계정 상실·지역 축소(과거 이력)</td>
    <td>신규 Tetra Pak·회복 출하</td>
  </tr>
  <tr>
    <td>대체 수분</td>
    <td>기능성·자연 수분 포지션</td>
    <td>생수·전해질·에너지드링크</td>
    <td>소비 횟수·시즌성</td>
  </tr>
</table>
{gloss([
    ("Tetra Pak", "종이팩 음료 포장. 신규 PL 계정이 Q2부터 출하 예정으로 언급."),
])}
</div>

<div class="block">
<h2>6. 선행 지표</h2>
<ul>
  <li><strong>07-23 Q2 실적</strong> — 컨센서스 EPS ~$0.55, 매출 ~$210M · 가이던스 유지/상향 톤</li>
  <li><strong>브랜드 CE·순가격</strong> (프로모 타이밍 코멘트)</li>
  <li><strong>Private Label</strong> — 신규 계정 출하·미주 회복 여부</li>
  <li><strong>연결 GM%</strong> — 40% 전후 유지 여부 (운임·관세·믹스)</li>
  <li><strong>Adj.EBITDA vs $132–138M 가이던스</strong></li>
  <li><strong>현금·자사주·재고·매출채권</strong></li>
</ul>
{gloss([
    ("선행 지표", "실적 전후 방향성을 가늠하는 신호."),
])}
</div>

<div class="block">
<h2>7. 비중 상한 · Thesis Breakers</h2>
{c8}
<div class="plain">
  <strong>쉽게:</strong> 미보유·워치. 예비금 우선순위는 <strong>NEO ≫ AMRX</strong>가 앞.
  PT 여유가 얇고 <strong>07-23 실적 직전</strong>이라 추격 매수 비권고.
</div>
<table>
  <tr><th>항목</th><th>권고</th><th>이유</th></tr>
  <tr><td>실적 전 (지금)</td><td><strong>신규 매수 금지</strong></td><td>이벤트·PT평형·고성장 기대 반영</td></tr>
  <tr><td>실적 후</td><td>가이던스↑·GM 유지 시 워치→소량</td><td>NEO/AMRX 다음 순위</td></tr>
  <tr><td>비중 상한</td><td>총자산 ~5–8%</td><td>소액 포트·변동성</td></tr>
  <tr><td>$80+ 추격</td><td>스킵</td><td>RR·여유 악화</td></tr>
</table>

<div class="warn">
  <strong>Thesis Breakers:</strong>
  <ul>
    <li>브랜드 볼륨 급감·카테고리 침투 정체</li>
    <li>GM 재악화(운임·관세·프로모 과다)</li>
    <li>FY26 매출·Adj.EBITDA 가이던스 하향</li>
    <li>주요 PL 계정 재상실</li>
    <li>연속 Beat가 Miss로 전환 + 가이던스 톤 악화</li>
  </ul>
</div>

{gloss([
    ("워치", "보유는 아니지만 관심 목록에 두고 실적·가격을 추적."),
    ("Thesis Breaker", "매수 논리를 깨는 사건."),
])}
</div>

<div class="block">
<h2>8. 한계 · 출처</h2>
<ul>
  <li>시가·PT·연간 재무: Yahoo Finance / yfinance.</li>
  <li>세그먼트·제품·마진·가이던스: Vita Coco Q1'26 8-K/보도자료·10-Q·콜 (2026-04-29).</li>
  <li>시나리오는 작업용. 투자 권고 아님.</li>
</ul>
<div class="footer-note">
  생성: 수익구조분석() · 티커 COCO · 기준 {ASOF} · WeasyPrint + NanumGothic
</div>
</div>

</body></html>
"""
    return html


def main() -> None:
    charts = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "geo": chart_geo_mix(),
        "funnel": chart_tam_funnel(),
        "sens": chart_sensitivity(),
        "scen": chart_scenarios(),
        "qtr": chart_quarterly(),
        "eps": chart_eps_surprise(),
        "pos": chart_position(),
    }
    html = build_html(charts)
    OUT_HTML.write_text(html, encoding="utf-8")
    print("HTML", OUT_HTML, OUT_HTML.stat().st_size)
    for out in OUT_PDF:
        out.parent.mkdir(parents=True, exist_ok=True)
        HTML(string=html, base_url=str(CHART_DIR)).write_pdf(out)
        print("PDF", out, out.stat().st_size)


if __name__ == "__main__":
    main()
