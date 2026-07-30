#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(BTSG) — 시각자료 + 초보용 설명 + 전문용어 주석 + WeasyPrint PDF."""

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
ASOF = "2026-07-20"
OUT_PDF = [
    Path("/opt/cursor/artifacts/BTSG_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/BTSG_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/BTSG_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/btsg")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "purple": "#5b21b6",  # avoid default AI purple-on-white; use deep plum as brand accent sparingly
    "ink": "#1c1917",
    "teal": "#0f766e",
    "navy": "#1e3a5f",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "rose": "#9f1239",
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
        (0.15, 0.65, 1.75, 1.55, "복잡·만성\n환자", C["sand"]),
        (2.1, 0.65, 1.85, 1.55, "보험 청구\n(Medicare 등)", C["gold"]),
        (4.15, 0.65, 1.9, 1.55, "약국\nSpecialty\nInfusion", C["navy"]),
        (6.25, 0.65, 1.75, 1.55, "가정·지역\n케어 제공", C["teal"]),
        (8.2, 0.65, 1.6, 1.55, "매출\n·EBITDA", C["slate"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("비즈니스 한눈에 — 집·지역사회에서 약 + 케어를 같이 판다", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    # Q1'26 Pharmacy 3171 / Provider 442
    sizes = [3171, 442]
    labels = ["Pharmacy\nSolutions\n3,171M (88%)", "Provider\nServices\n442M (12%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["navy"], C["teal"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("세그먼트 매출 (Q1'26, 총 3,614M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    # FY25 pharmacy internal: specialty/infusion 9.1B vs home/community 2.4B of 11.4B
    sizes = [9.1, 2.4]
    labels = ["Specialty·Infusion\n9.1B (FY25)", "Home·Community\nPharmacy 2.4B"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["slate"], C["gold"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("Pharmacy 내부 (FY25)", fontproperties=PROP_B, fontsize=11)
    fig.suptitle("BTSG 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    return save_fig(fig, "02_segment_mix.png")


def chart_payor_mix() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    # FY25 approx payor mix from research
    labels = ["Medicare D", "Commercial", "Medicare\nAdvantage", "Medicaid", "기타·Private"]
    vals = [31.7, 24.1, 17.6, 8.5, 18.1]
    colors = [C["navy"], C["teal"], C["slate"], C["gold"], C["sand"]]
    bars = ax.bar(labels, vals, color=colors, width=0.55)
    ax.set_ylabel("매출 비중 (%)", fontproperties=PROP)
    ax.set_title("지급자(Payor) 믹스 대략치 (FY25 언급 기준)", fontproperties=PROP_B, fontsize=12)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v}%", ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 40)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "03_payor_mix.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    layers = [
        (9.2, 8.3, "TAM — 미국 가정·특수 약국·홈케어", "Specialty pharmacy + home health/hospice 등 거대 풀", C["sand"]),
        (7.6, 6.2, "SAM — 복잡·만성 환자 채널", "SNF·호스피스·주입·퇴원 후 케어가 필요한 인구", C["gold"]),
        (5.8, 4.1, "SOM — BTSG 매출 가이던스", "FY26 매출 14.7–15.2B · 일 475k+ 고객/환자", C["teal"]),
        (4.2, 2.0, "이중 엔진", "Pharmacy(~88%) 성장 + Provider(중고20%대) 가속", C["navy"]),
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
    ax.set_title("시장 깔때기 — 집·지역사회 헬스케어에서 BTSG의 자리", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "04_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    steps = [
        "스크립트\n·이용량",
        "약가·리베이트\n·GTN",
        "페이여\n믹스",
        "Provider\n마진",
        "Adj.\nEBITDA",
        "이자·부채",
        "EPS",
    ]
    xs = list(range(len(steps)))
    ys = [1.0, 0.88, 0.90, 0.84, 0.78, 0.70, 0.65]
    ax.plot(xs, ys, "o-", color=C["navy"], lw=2.5, ms=9)
    for i, (s, y) in enumerate(zip(steps, ys)):
        ax.annotate(s, (i, y), textcoords="offset points", xytext=(0, 14), ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0.55, 1.15)
    ax.set_xticks([])
    ax.set_ylabel("상대 기여(개념)", fontproperties=PROP)
    ax.set_title("민감도 사슬 — 약 볼륨·단가와 홈케어 마진", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "05_sensitivity.png")


def chart_scenarios() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    labels = ["Bear", "Base", "Bull"]
    rev = [13500, 15000, 16200]
    ebitda = [700, 810, 900]
    colors = [C["red"], C["gold"], C["teal"]]
    ax = axes[0]
    bars = ax.bar(labels, rev, color=colors, width=0.55)
    ax.set_title("시나리오별 연간 매출 (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 200, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 18500)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    bars = ax.bar(labels, ebitda, color=colors, width=0.55)
    ax.set_title("시나리오별 Adj. EBITDA (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, ebitda):
        ax.text(b.get_x() + b.get_width() / 2, v + 15, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 1050)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("Bear / Base / Bull — FY26 가이던스 중심", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "06_scenarios.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [2878, 3148, 3334, 3551, 3614]
    oi = [51, 49, 88, 108, 121]
    x = range(len(labels))
    ax.bar(x, rev, color=C["navy"], alpha=0.85, label="매출 (백만 USD)", width=0.55)
    ax2 = ax.twinx()
    ax2.plot(x, oi, "o-", color=C["gold"], lw=2.2, ms=8, label="영업이익 (백만 USD)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("매출 (백만 USD)", fontproperties=PROP, color=C["navy"])
    ax2.set_ylabel("영업이익 (백만 USD)", fontproperties=PROP, color=C["gold"])
    ax.set_title("분기 추이 — 매출 성장과 영업이익 회복", fontproperties=PROP_B, fontsize=12)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    return save_fig(fig, "07_quarterly.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["~4Q전", "~3Q전", "~2Q전", "최근(Q1'26)"]
    actual = [0.22, 0.30, 0.33, 0.39]
    est = [0.19, 0.26, 0.35, 0.31]
    surprise = [18, 14, -5, 26]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], est, w, label="예상 EPS", color=C["sand"])
    ax.bar([i + w / 2 for i in x], actual, w, label="실제 EPS", color=C["navy"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("EPS (USD)", fontproperties=PROP)
    ax.set_title("실적 서프라이즈 — Beat 위주, 한 분기 Miss", fontproperties=PROP_B, fontsize=12)
    for i, s in enumerate(surprise):
        color = C["green"] if s >= 0 else C["red"]
        ax.text(i + w / 2, actual[i] + 0.015, f"{s:+d}%", ha="center", fontsize=8, fontproperties=PROP, color=color)
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
        (0.35, 0.55, 2.2, 1.7, "코어\nECPG/ASTH", C["teal"]),
        (2.8, 0.55, 2.5, 1.7, "BTSG\n보유 1주\n추가 금지", C["gold"]),
        (5.55, 0.55, 2.0, 1.7, "고점·실적\n07-31", C["navy"]),
        (7.8, 0.55, 1.9, 1.7, "현금\n버퍼", C["sand"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=tc)
    ax.set_title("포지션 맥락 — 고점·이벤트 앞 애드 금지", fontproperties=PROP_B, fontsize=12, pad=6)
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
        content: "수익구조분석(BTSG) · {ASOF} · " counter(page) " / " counter(pages);
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
    .gloss-title {{ font-weight: 700; color: #1e3a5f; margin-bottom: 4px; font-size: 9pt; }}
    .gloss ul {{ margin: 0 0 0 14px; }}
    .gloss .term {{ font-weight: 700; color: #0f766e; }}
    .plain {{ background: #eff6ff; border: 1px solid #bfdbfe; padding: 8px 12px; margin: 6px 0 10px; font-size: 9.5pt; }}
    .plain strong {{ color: #1e3a5f; }}
    .warn {{ background: #fff1f2; border-left: 4px solid #9f1239; padding: 8px 12px; margin: 8px 0; font-size: 9.5pt; }}
    .footer-note {{ font-size: 8pt; color: #78716c; margin-top: 18px; border-top: 1px solid #e7e5e4; padding-top: 8px; }}
    """

    c0 = fig_block(charts["flow"], "그림 0. 비즈니스 흐름 — 환자 → 보험 → 약국/홈케어 → 이익")
    c1 = fig_block(charts["mix"], "그림 1. 세그먼트·Pharmacy 내부 파이")
    c2 = fig_block(charts["payor"], "그림 2. 누가 돈을 내나 — Payor 믹스")
    c3 = fig_block(charts["funnel"], "그림 3. TAM→SAM→SOM 깔때기")
    c4 = fig_block(charts["sens"], "그림 4. 민감도 사슬")
    c5 = fig_block(charts["scen"], "그림 5. Bear/Base/Bull")
    c6 = fig_block(charts["qtr"], "그림 6. 최근 5분기 매출·영업이익")
    c7 = fig_block(charts["eps"], "그림 7. EPS 서프라이즈")
    c8 = fig_block(charts["pos"], "그림 8. 포트폴리오에서의 BTSG")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"/><title>수익구조분석 — BTSG (BrightSpring)</title>
<style>{css}</style></head>
<body>

<div class="hero">
  <h1>수익구조분석 · BTSG</h1>
  <div>BrightSpring Health Services, Inc. · 나스닥 · 가정·지역사회 기반 헬스케어 (약국 + 케어)</div>
  <div class="oneline">
    <strong>한 줄 구조:</strong> 복잡한 만성·특수 환자에게 <em>약(Pharmacy Solutions)</em>과
    <em>집·지역 케어(Provider Services)</em>를 같이 팝니다. 매출의 약 88%는 약국이고,
    그중에서도 Specialty·Infusion(고가·특수 약/정맥주사)이 성장을 끌어올립니다.
    Provider는 비중은 작지만 마진·성장률이 가속 구간입니다.
  </div>
  <div class="kpi">
    <span>종가 $70.69</span>
    <span>시총 ~$13.9B</span>
    <span>PT $49 / $76 / $90</span>
    <span>Q1'26 매출 $3.61B (+26%)</span>
    <span>Pharmacy $3.17B · Provider $0.44B</span>
    <span>FY26 매출 $14.7–15.2B · Adj.EBITDA $795–825M</span>
    <span>실적 07-31</span>
    <span>기준일 {ASOF}</span>
  </div>
</div>

<div class="plain">
  <strong>이 보고서를 읽는 법 (비전공자용):</strong>
  “어디서 돈을 받는지 → 시장 크기 → 무엇이 흔들리는지 → 좋은/나쁜 숫자 →
  경쟁 → 미리 볼 신호 → 얼마나 들고 있을지” 순서입니다.
  각 블록 끝 용어 주석은 중복 없이, 처음 나온 말만 설명합니다.
</div>

{c0}

<div class="block">
<h2>1. 수익 구조 — 세그먼트·페이여·마진</h2>
<div class="plain">
  <strong>쉽게:</strong> 동네 약국 + 방문 간호사·호스피스를 한데 합친 대기업이라고 보면 됩니다.
  다만 파는 약이 “감기약”이 아니라, 암·희귀·만성 등에 쓰는 <em>비싸고 관리가 필요한 약</em>과
  <em>정맥으로 넣는 약(Infusion)</em>이 중심입니다. 그래서 매출은 아주 큰데, 약 원가도 커서
  매출총이익률은 비교적 얇습니다(~12%).
</div>
{c1}
{c2}

<h3>1-1. Q1'26 세그먼트</h3>
<table>
  <tr><th>세그먼트</th><th>매출</th><th>YoY</th><th>쉬운 설명</th></tr>
  <tr><td>Pharmacy Solutions</td><td>$3,171M</td><td>+25%</td><td>특수·주입·시니어·호스피스·SNF·퇴원 후 약 공급·복약 관리. <strong>매출의 ~88%</strong></td></tr>
  <tr><td>Provider Services</td><td>$442M</td><td>+28%</td><td>가정간호, 호스피스, 재활, 가정 주치의, 일상생활 지원 등</td></tr>
  <tr><td><strong>합계</strong></td><td><strong>$3,614M</strong></td><td><strong>+26%</strong></td><td>연결 매출</td></tr>
</table>

<p>
FY25 기준 Pharmacy $11.4B(88.7%), Provider $1.5B(11.3%).
Pharmacy 안에서 Specialty·Infusion이 $9.1B로 Home·Community Pharmacy($2.4B)보다 훨씬 큽니다.
즉 “약 매출이 크다 = 이익도 약만큼 두껍다”가 아닙니다. 고가약은 매출원가도 커서
<strong>달러 매출 성장과 달러 이익 성장을 따로 봐야</strong> 합니다.
</p>

<h3>1-2. 누가 돈을 내나 (Payor)</h3>
<p>
FY25 언급 기준 대략: Medicare Part D ~31.7%, Medicare Advantage ~17.6%,
Commercial ~24.1%, Medicaid ~8.5% 등. 정부가 관련된 보험 비중이 높아
<strong>약가·급여·환급 정책</strong>이 실적에 직접 닿습니다.
</p>

{c6}

<h3>1-3. 연간 재무</h3>
<table>
  <tr><th>연도</th><th>매출</th><th>매출총이익</th><th>영업이익</th><th>순이익</th><th>이자</th></tr>
  <tr><td>FY2022</td><td>$7.72B</td><td>$1.35B</td><td>$229M</td><td>−$54M</td><td>$234M</td></tr>
  <tr><td>FY2023</td><td>$7.69B</td><td>$1.14B</td><td>$58M</td><td>−$155M</td><td>$272M</td></tr>
  <tr><td>FY2024</td><td>$10.07B</td><td>$1.27B</td><td>$108M</td><td>−$18M</td><td>$191M</td></tr>
  <tr><td>FY2025</td><td>$12.91B</td><td>$1.52B</td><td>$295M</td><td>$191M</td><td>$157M</td></tr>
</table>

<p>
매출·영업이익·순이익이 FY25에 뚜렷이 회복되었습니다. 이자비용도 FY23 고점 대비 줄었습니다
(부채 ~$2.7B, 현금 ~$0.89B로 레버리지는 여전히 큼).
보고 GM ~12.2%, OM ~3.4%, PM ~2.3% — <strong>얇은 마진 × 거대한 매출</strong> 구조입니다.
</p>

<div class="callout">
  <strong>FY26 가이던스(상향, Community Living 제외):</strong>
  매출 <strong>$14.725–15.225B</strong> (Pharmacy $12.85–13.30B, Provider $1.875–1.925B) ·
  Adj. EBITDA <strong>$795–825M</strong> (~+29–34%).
  Provider는 중고 20%대 성장 가이던스, Amedisys/LHC 관련 자산 등 인수가 가속 요인으로 언급.
</div>

{gloss([
    ("Pharmacy Solutions", "약 조제·배송·복약 관리 사업부. Specialty·Infusion이 핵심."),
    ("Specialty pharmacy", "고가·특수 질환 약을 관리·공급하는 약국. 일반 약국보다 절차·모니터링이 많음."),
    ("Infusion", "정맥(혈관)으로 약을 주입하는 치료. 병원 밖(가정·클리닉)에서도 이뤄짐."),
    ("Provider Services", "사람이 직접 케어를 제공하는 사업(가정간호·호스피스 등)."),
    ("Payor (지급자)", "진료·약값을 내는 쪽. 정부 보험, 민간보험, 본인 부담 등."),
    ("Medicare Part D", "메디케어 처방약 보험. BTSG 매출의 큰 축."),
    ("Medicare Advantage", "민간이 운영하는 메디케어 대안 플랜."),
    ("SNF", "Skilled Nursing Facility. 전문간호시설(요양·재활)."),
    ("Adj. EBITDA", "일회성 등을 조정한 영업 현금창출력 지표."),
    ("Community Living", "가이던스에서 제외한 매각/비계속 사업 영역."),
])}
</div>

<div class="block">
<h2>2. 시장 깔때기 — TAM → SAM → SOM</h2>
<div class="plain">
  <strong>쉽게:</strong> 미국 헬스케어에서 “집과 지역사회로 나오는” 약·간호 수요는 큽니다.
  BTSG는 그중 <em>복잡하고 만성적인 환자</em>에게 약+케어를 묶는 쪽을 노립니다.
</div>
{c3}

<table>
  <tr><th>단계</th><th>대략</th><th>정의</th><th>헷갈리기 쉬운 점</th></tr>
  <tr>
    <td>TAM</td>
    <td>매우 큼</td>
    <td>미국 specialty pharmacy + home health/hospice 등</td>
    <td>TAM ≠ BTSG 시총·매출</td>
  </tr>
  <tr>
    <td>SAM</td>
    <td>복잡·만성·다약제 환자 채널</td>
    <td>주입·호스피스·SNF·퇴원 후 케어가 필요한 인구</td>
    <td>정책·환급이 SAM 크기를 바꿈</td>
  </tr>
  <tr>
    <td>SOM</td>
    <td>FY26 매출 ~$15B 가이던스</td>
    <td>일 475k+ 고객/환자에게 서비스</td>
    <td>매출 성장이 이익 성장과 항상 같진 않음(약 원가)</td>
  </tr>
  <tr>
    <td>엔진</td>
    <td>Pharmacy 볼륨 + Provider 마진</td>
    <td>약국이 탑라인, 프로바이더가 믹스·시너지</td>
    <td>인수(홈헬스)는 성장과 통합 리스크를 동시에 가져옴</td>
  </tr>
</table>

{gloss([
    ("TAM / SAM / SOM", "전체 시장 / 팔 수 있는 시장 / 실제로 가져가는 규모."),
    ("다약제 (Polypharmacy)", "여러 약을 동시에 복용. 관리·상호작용 이슈가 커 specialty·케어 수요와 연결."),
    ("환급 (Reimbursement)", "보험이 약·서비스 비용을 얼마로 인정해 주느냐."),
])}
</div>

<div class="block">
<h2>3. 민감도 사슬 — 무엇이 이익을 흔드나</h2>
<div class="plain">
  <strong>쉽게:</strong> 슈퍼마켓처럼 “많이 팔아도 원가가 따라오면” 남는 게 적습니다.
  BTSG는 약 매출이 커서, <em>얼마나 팔았나</em>와 <em>얼마에/어떤 조건으로 남았나</em>를 같이 봐야 합니다.
</div>
{c4}

<table>
  <tr><th>단계</th><th>좋게 나오면</th><th>나쁘게 나오면</th></tr>
  <tr><td>① 스크립트·이용량</td><td>Specialty/Infusion 볼륨↑</td><td>이용 둔화, 경쟁 이탈</td></tr>
  <tr><td>② 약가·리베이트·GTN</td><td>순매출 품질 유지</td><td>약가 인하·환급 삭감·리베이트↑</td></tr>
  <tr><td>③ 페이여 믹스</td><td>유리한 구성</td><td>저마진 페이여 비중↑</td></tr>
  <tr><td>④ Provider 마진</td><td>홈헬스 통합·가동률↑</td><td>인력난·인수 통합 실패</td></tr>
  <tr><td>⑤ Adj. EBITDA</td><td>가이던스 $795–825M 달성</td><td>마진 압축</td></tr>
  <tr><td>⑥ 이자·부채</td><td>이자 하락 추세 유지</td><td>레버리지·금리 재상승</td></tr>
  <tr><td>⑦ EPS</td><td>연속 개선</td><td>Miss 반복 → 멀티플 압축</td></tr>
</table>

{gloss([
    ("스크립트 (Script)", "처방 건수. 약국 볼륨의 기본 단위."),
    ("GTN (Gross-to-Net)", "정가에서 리베이트·할인 등을 빼 순매출로 가는 과정."),
    ("리베이트", "보험·PBM 등에 돌려주는 금액. 커지면 순매출이 줄어듦."),
    ("PBM", "Pharmacy Benefit Manager. 약 보험 급부를 중개·관리하는 사업자."),
])}
</div>

<div class="block">
<h2>4. Bear / Base / Bull — 숫자 시나리오</h2>
<div class="plain">
  <strong>쉽게:</strong> FY26 가이던스(매출 ~$15B, Adj.EBITDA ~$810M 중심)를 Base로 두고 위아래를 잡았습니다.
</div>
{c5}

<table>
  <tr><th>시나리오</th><th>가정</th><th>매출</th><th>Adj.EBITDA</th><th>주가 함의(개념)</th></tr>
  <tr>
    <td>Bear</td>
    <td>환급·약가 압박, Provider 통합 차질, 가이던스 하단 이탈</td>
    <td>~$13.5B</td>
    <td>~$700M</td>
    <td>$45–55 (PT 저점 $49 근처·하회)</td>
  </tr>
  <tr>
    <td>Base</td>
    <td>가이던스 중간~상단, Pharmacy·Provider 동반</td>
    <td>~$15.0B</td>
    <td>~$810M</td>
    <td>$70–80 (현재~$71, PT 평균 $76)</td>
  </tr>
  <tr>
    <td>Bull</td>
    <td>볼륨·마진 동반, 추가 상향, 레버리지 개선</td>
    <td>~$16.2B+</td>
    <td>~$900M</td>
    <td>$85–95 (PT 고점 $90)</td>
  </tr>
</table>

<p>
현재가 <strong>$70.69</strong>는 52주 고점 <strong>$72.22</strong> 바로 아래입니다.
PT 평균 $76 대비 업사이드는 있으나, PT 저점 $49는 “애널리스트도 큰 하방을 열어 둔” 신호입니다.
시총 ~$14B로 포트 내 ECPG/ASTH/INDV보다 <strong>훨씬 큰 회사</strong>라, 같은 1주도 달러 익스포저가 큽니다.
</p>

{c7}
<p>
최근 4분기 EPS: +18%, +14%, <strong>−5%(Miss)</strong>, +26%.
“매번 대박 Beat” 유형은 아니고, <strong>혼합형</strong>입니다. 07-31 실적은 변동성 이벤트로 봅니다.
</p>

{gloss([
    ("Bear / Base / Bull", "비관·기본·낙관."),
    ("Beat / Miss", "예상보다 좋음 / 나쁨."),
    ("익스포저", "그 종목 가격 변동에 얼마나 노출되어 있는지(달러·비중)."),
])}
</div>

<div class="block">
<h2>5. 경쟁·포지션</h2>
<div class="plain">
  <strong>쉽게:</strong> 특수 약국·홈헬스는 대형 체인, 보험 직영, 지역 사업자와 경쟁합니다.
  BTSG의 포인트는 “약 + 집 케어”를 한 환자에게 이어서 팔 수 있다는 점입니다.
</div>
<table>
  <tr><th>전선</th><th>BTSG</th><th>압력</th><th>관찰</th></tr>
  <tr>
    <td>Specialty / Infusion</td>
    <td>규모·채널(호스피스·SNF 등)</td>
    <td>PBM·약가·경쟁 약국</td>
    <td>볼륨, GTN, 스크립트 성장</td>
  </tr>
  <tr>
    <td>Provider / Home health</td>
    <td>성장 가속·인수</td>
    <td>인력, 환급, 통합</td>
    <td>세그먼트 마진, 가이던스</td>
  </tr>
</table>
{gloss([
    ("시너지", "약과 케어를 같이 팔아 환자 유지·이용을 늘리는 효과. 기대한 만큼 안 나오면 할증만 남음."),
])}
</div>

<div class="block">
<h2>6. 선행 지표</h2>
<ul>
  <li><strong>Pharmacy / Provider 각 매출 성장률</strong></li>
  <li><strong>Adj. EBITDA 마진</strong> — 탑라인만 보고 착각하지 않기</li>
  <li><strong>페이여·정책 헤드라인</strong> (Part D, 약가)</li>
  <li><strong>인수 통합 코멘트</strong> (홈헬스 마진)</li>
  <li><strong>이자·순부채</strong></li>
  <li><strong>07-31 실적</strong> — 컨센서스 EPS ~$0.40, 매출 ~$3.66B</li>
</ul>
{gloss([
    ("선행 지표", "실적 전 방향성을 가늠하는 신호."),
    ("순부채", "총부채 − 현금."),
])}
</div>

<div class="block">
<h2>7. 비중 상한 · Thesis Breakers</h2>
{c8}
<div class="plain">
  <strong>쉽게:</strong> 이미 1주 보유 중이고, 주가는 고점권, 실적은 07-31입니다.
  전략 규칙상 <strong>추가 매수(애드) 금지</strong>가 기본값입니다.
</div>
<table>
  <tr><th>항목</th><th>권고</th><th>이유</th></tr>
  <tr><td>현재</td><td>Hold 1주</td><td>성장 스토리는 유효, 이미 편입</td></tr>
  <tr><td>추가 매수</td><td><strong>금지</strong></td><td>고점 + 실적 이벤트 + 시총 커서 달러 리스크</td></tr>
  <tr><td>비중 상한</td><td>총자산 ~10–15% (소액 포트)</td><td>코어(ECPG/ASTH)보다 낮은 한도</td></tr>
  <tr><td>재접근</td><td>실적 후 눌림 + 가이던스 유지 시만 검토</td><td>추격 매수 금지</td></tr>
</table>

<div class="warn">
  <strong>Thesis Breakers:</strong>
  <ul>
    <li>FY Adj.EBITDA 가이던스 하향</li>
    <li>Pharmacy 성장이 마진 붕괴를 동반 (볼륨만 늘고 남는 게 없음)</li>
    <li>Provider 인수 통합 실패·인력 위기로 세그먼트 적자</li>
    <li>주요 환급·약가 정책 충격</li>
    <li>연속 EPS Miss + 레버리지 재악화</li>
  </ul>
</div>

{gloss([
    ("애드", "기존 보유를 더 사는 것."),
    ("Thesis Breaker", "보유 논리를 깨는 사건."),
])}
</div>

<div class="block">
<h2>8. 한계 · 출처</h2>
<ul>
  <li>시가·PT·일부 재무: Yahoo Finance 집계.</li>
  <li>세그먼트·가이던스·페이여: BrightSpring IR / 실적자료(Q1'26, FY25).</li>
  <li>TAM·시나리오는 근사·작업용. 투자 권고 아님.</li>
</ul>
<div class="footer-note">
  생성: 수익구조분석() · 티커 BTSG · 기준 {ASOF} · WeasyPrint + NanumGothic
</div>
</div>

</body></html>
"""
    return html


def main() -> None:
    charts = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "payor": chart_payor_mix(),
        "funnel": chart_tam_funnel(),
        "sens": chart_sensitivity(),
        "scen": chart_scenarios(),
        "qtr": chart_quarterly(),
        "eps": chart_eps_surprise(),
        "pos": chart_position(),
    }
    html = build_html(charts)
    html, _px = build_and_insert_price("BTSG", CHART_DIR, html)
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
