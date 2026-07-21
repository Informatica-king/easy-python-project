#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(AMRX) — 시각자료 + 초보용 설명 + 전문용어 주석 + WeasyPrint PDF."""

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
ASOF = "2026-07-21"
OUT_PDF = [
    Path("/opt/cursor/artifacts/AMRX_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/AMRX_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/AMRX_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/amrx")
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
        (0.1, 0.65, 1.85, 1.55, "복제약\n(Generics)\n대량·저가", C["sand"]),
        (2.15, 0.65, 1.85, 1.55, "브랜드\nSpecialty\n신경·내분비", C["gold"]),
        (4.2, 0.65, 1.8, 1.55, "유통\nAvKARE\n정부·기관", C["teal2"]),
        (6.2, 0.65, 1.7, 1.55, "약국·병원\n·VA/DoD", C["teal"]),
        (8.1, 0.65, 1.65, 1.55, "매출\n·마진", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8, color=tc)
    ax.set_title("비즈니스 한눈에 — 싼 복제약 + 브랜드약 + 정부 유통", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [423, 133, 166]
    labels = ["Affordable\nMedicines\n423M (59%)", "Specialty\n133M (18%)", "AvKARE\n166M (23%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["teal"], C["gold"], C["navy"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("세그먼트 매출 (Q1'26, 총 723M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    # YoY growth by segment
    cats = ["Affordable\nMedicines", "Specialty", "AvKARE"]
    yoy = [2, 23, -4]
    colors = [C["teal"] if v >= 0 else C["red"] for v in yoy]
    ax.bar(cats, yoy, color=colors, width=0.55)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("세그먼트 성장률 (Q1'26)", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(yoy):
        ax.text(i, v + (1.2 if v >= 0 else -2.5), f"{v:+d}%", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("AMRX 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    return save_fig(fig, "02_segment_mix.png")


def chart_specialty_drivers() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    cats = ["CREXONT\n(파킨슨)", "BREKIYA\n(군발두통)", "기타 Specialty\n(추정)"]
    # CREXONT 21, BREKIYA 4.6, rest ~107 of 133
    vals = [21, 4.6, 107.4]
    colors = [C["navy"], C["gold"], C["sand"]]
    ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD (Q1'26)", fontproperties=PROP)
    ax.set_title("Specialty 안 성장 드라이버 (언급 수치)", fontproperties=PROP_B, fontsize=12)
    for i, v in enumerate(vals):
        ax.text(i, v + 2, f"{v}", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "03_specialty_drivers.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    layers = [
        (9.2, 8.3, "TAM — 미국 처방약·복제·브랜드", "제네릭+스페셜티+바이오시밀러 거대 풀", C["sand"]),
        (7.6, 6.2, "SAM — 복잡제형·신경/내분비", "주사·서방정·ADHD·파킨슨·편두통 등", C["gold"]),
        (5.8, 4.1, "SOM — AMRX ~$3B급 매출", "FY25 $3.02B · Q1 런레이트 + Specialty 가속", C["teal2"]),
        (4.2, 2.0, "마진 엔진 전환", "저마진 유통↓ · Specialty·복잡 제네릭↑", C["navy"]),
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
    ax.set_title("시장 깔때기 — 복제약 회사에서 브랜드 믹스로", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "04_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    steps = [
        "제네릭\n가격·점유",
        "론치\n파이프라인",
        "Specialty\n침투",
        "믹스\n(고마진)",
        "총이익률",
        "이자·부채",
        "EPS",
    ]
    xs = list(range(len(steps)))
    ys = [1.0, 0.93, 0.95, 0.90, 0.85, 0.72, 0.68]
    ax.plot(xs, ys, "o-", color=C["teal"], lw=2.5, ms=9)
    for i, (s, y) in enumerate(zip(steps, ys)):
        ax.annotate(s, (i, y), textcoords="offset points", xytext=(0, 14), ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0.55, 1.15)
    ax.set_xticks([])
    ax.set_ylabel("상대 기여(개념)", fontproperties=PROP)
    ax.set_title("민감도 사슬 — 가격압력 vs Specialty·믹스", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "05_sensitivity.png")


def chart_scenarios() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    labels = ["Bear", "Base", "Bull"]
    rev = [2900, 3200, 3500]
    eps = [0.70, 0.95, 1.15]
    colors = [C["red"], C["gold"], C["teal"]]
    ax = axes[0]
    bars = ax.bar(labels, rev, color=colors, width=0.55)
    ax.set_title("시나리오별 연간 매출 (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 40, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 4000)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    bars = ax.bar(labels, eps, color=colors, width=0.55)
    ax.set_title("시나리오별 Adj. EPS (USD, 개념)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("USD / 주", fontproperties=PROP)
    for b, v in zip(bars, eps):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.03, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 1.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("Bear / Base / Bull — 믹스·론치 시나리오", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "06_scenarios.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [695, 725, 785, 814, 723]
    oi = [101, 112, 70, 115, 148]
    x = range(len(labels))
    ax.bar(x, rev, color=C["teal"], alpha=0.85, label="매출 (백만 USD)", width=0.55)
    ax2 = ax.twinx()
    ax2.plot(x, oi, "o-", color=C["gold"], lw=2.2, ms=8, label="영업이익 (백만 USD)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("매출 (백만 USD)", fontproperties=PROP, color=C["teal"])
    ax2.set_ylabel("영업이익 (백만 USD)", fontproperties=PROP, color=C["gold"])
    ax.set_title("분기 추이 — 매출 계절성 vs 영업이익 개선", fontproperties=PROP_B, fontsize=12)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    return save_fig(fig, "07_quarterly.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["~4Q전", "~3Q전", "~2Q전", "최근(Q1'26)"]
    actual = [0.25, 0.17, 0.21, 0.27]
    est = [0.17, 0.14, 0.18, 0.17]
    surprise = [43, 23, 14, 60]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], est, w, label="예상 EPS", color=C["sand"])
    ax.bar([i + w / 2 for i in x], actual, w, label="실제 EPS", color=C["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("EPS (USD)", fontproperties=PROP)
    ax.set_title("실적 서프라이즈 — EPS 연속 Beat (매출은 약했던 이력)", fontproperties=PROP_B, fontsize=12)
    for i, s in enumerate(surprise):
        ax.text(i + w / 2, actual[i] + 0.01, f"+{s}%", ha="center", fontsize=8, fontproperties=PROP, color=C["green"])
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
        (2.7, 0.55, 2.1, 1.7, "NESR\n분할", C["teal"]),
        (5.0, 0.55, 2.4, 1.7, "AMRX\n07-30 반만\n(NEO 다음)", C["gold"]),
        (7.7, 0.55, 1.9, 1.7, "현금\n버퍼", C["sand"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=tc)
    ax.set_title("포지션 맥락 — 예비금 2순위 · 실적 전 추격 금지", fontproperties=PROP_B, fontsize=12, pad=6)
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
        content: "수익구조분석(AMRX) · {ASOF} · " counter(page) " / " counter(pages);
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

    c0 = fig_block(charts["flow"], "그림 0. 비즈니스 흐름 — 복제약 · 브랜드 · 정부유통")
    c1 = fig_block(charts["mix"], "그림 1. 세그먼트 파이와 성장률")
    c2 = fig_block(charts["spec"], "그림 2. Specialty 성장 드라이버")
    c3 = fig_block(charts["funnel"], "그림 3. TAM→SAM→SOM 깔때기")
    c4 = fig_block(charts["sens"], "그림 4. 민감도 사슬")
    c5 = fig_block(charts["scen"], "그림 5. Bear/Base/Bull")
    c6 = fig_block(charts["qtr"], "그림 6. 최근 5분기 매출·영업이익")
    c7 = fig_block(charts["eps"], "그림 7. EPS 서프라이즈")
    c8 = fig_block(charts["pos"], "그림 8. 포트폴리오에서의 AMRX")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"/><title>수익구조분석 — AMRX (Amneal)</title>
<style>{css}</style></head>
<body>

<div class="hero">
  <h1>수익구조분석 · AMRX</h1>
  <div>Amneal Pharmaceuticals, Inc. · 나스닥 · 복제약(제네릭) + 스페셜티 브랜드 + 정부 유통</div>
  <div class="oneline">
    <strong>한 줄 구조:</strong> 약국의 값싼 복제약(Affordable Medicines)이 매출의 약 60%이고,
    파킨슨·편두통 등 <em>브랜드 Specialty(~18%)</em>가 마진·성장을 끌어올리며,
    AvKARE(~23%)는 정부·기관에 약을 유통합니다. 전략은 “저마진 유통을 줄이고, 복잡 제네릭·브랜드 비중을 키워 마진을 올리는 것”입니다.
  </div>
  <div class="kpi">
    <span>종가 $17.50</span>
    <span>시총 ~$5.6B</span>
    <span>PT $16 / $18.3 / $23</span>
    <span>Q1'26 매출 $723M (+4%)</span>
    <span>Affordable $423 · Specialty $133 · AvKARE $166</span>
    <span>GM↑ +750bp · EPS Beat 연속</span>
    <span>실적 07-30</span>
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
<h2>1. 수익 구조 — 세그먼트·제품·마진</h2>
<div class="plain">
  <strong>쉽게:</strong> 슈퍼마켓으로 치면
  (1) PB 생수·라면처럼 <em>싸게 많이 파는 복제약</em>,
  (2) 프리미엄 건강기능식품처럼 <em>브랜드로 마진 내는 Specialty</em>,
  (3) 군부대·관공서에 납품하는 <em>유통(AvKARE)</em> 세 코너가 한 회사 안에 있습니다.
</div>
{c1}
{c2}

<h3>1-1. Q1'26 세그먼트</h3>
<table>
  <tr><th>세그먼트</th><th>매출</th><th>YoY</th><th>쉬운 설명</th></tr>
  <tr>
    <td>Affordable Medicines</td>
    <td>$423M (~59%)</td>
    <td>+2%</td>
    <td>리테일 제네릭·주사·바이오시밀러. 여성건강·ADHD 등 <strong>복잡 포트폴리오</strong>가 견인. 세그먼트 GM ~47.3%(+320bp)</td>
  </tr>
  <tr>
    <td>Specialty</td>
    <td>$133M (~18%)</td>
    <td>+23%</td>
    <td>브랜드. CREXONT(파킨슨) $21M, BREKIYA 오토인젝터(군발두통) $4.6M, UNITHROID 등</td>
  </tr>
  <tr>
    <td>AvKARE</td>
    <td>$166M (~23%)</td>
    <td>−4%</td>
    <td>연방·소매·기관 유통. 정부 채널↑, <strong>저마진 유통↓</strong>(의도적 정리)</td>
  </tr>
  <tr>
    <td><strong>합계</strong></td>
    <td><strong>$723M</strong></td>
    <td><strong>+4%</strong></td>
    <td>총이익률 +750bp · 조정총이익률 +510bp (믹스 개선)</td>
  </tr>
</table>

<p>
핵심 메시지: <strong>탑라인(+4%)보다 마진 개선이 더 큼</strong>.
저마진 AvKARE 유통을 줄이고 Specialty·복잡 제네릭 비중을 올리는 “포트폴리오 시프트”가 작동 중입니다.
회사는 Affordable Medicines 연간 성장 가이던스를 약 <strong>7–8%</strong>로 제시했고, FY26 가이던스를 재확인했습니다.
</p>

{c6}

<h3>1-2. 연간 추이</h3>
<table>
  <tr><th>연도</th><th>매출</th><th>매출총이익</th><th>영업이익</th><th>순이익</th></tr>
  <tr><td>FY2022</td><td>$2.21B</td><td>$785M</td><td>$189M</td><td>−$130M</td></tr>
  <tr><td>FY2023</td><td>$2.39B</td><td>$821M</td><td>$239M</td><td>−$84M</td></tr>
  <tr><td>FY2024</td><td>$2.79B</td><td>$1.02B</td><td>$348M</td><td>−$117M</td></tr>
  <tr><td>FY2025</td><td>$3.02B</td><td>$1.11B</td><td>$398M</td><td>$72M</td></tr>
</table>

<p>
매출·영업이익은 수년 개선, FY25에 순이익 흑자 전환.
부채 ~$2.7B로 레버리지는 여전하나, 경영진은 순레버리지가 Adj.EBITDA 대비 약 <strong>3.5x</strong>로 낮아졌다고 언급.
보고 GM ~39%, OM ~20%, PM ~4% — “싼 약” 이미지보다 Specialty 믹스 덕에 마진이 두꺼워지는 중.
</p>

<div class="callout">
  <strong>FY26 (회사 코멘트):</strong> 가이던스 재확인 · Affordable +7–8% 기대 · Specialty(CREXONT·BREKIYA) 가속 ·
  Kashiv 거래 등 파이프라인/BD. Q1 Adj.EPS $0.27(+29%대), Adj.EBITDA도 두 자릿수 성장 언급.
</div>

{gloss([
    ("제네릭 / Affordable Medicines", "특허 만료 후 나오는 복제약. 싸지만 경쟁·가격 압력이 심함. ‘복잡 제형’일수록 마진이 낫다."),
    ("Specialty (브랜드)", "처방 브랜드약. 파킨슨·편두통·내분비 등. 마케팅·임상으로 차별화, 마진↑."),
    ("AvKARE", "정부(국방·보훈 등)·기관·소매에 의약품·의료용품을 유통하는 세그먼트."),
    ("바이오시밀러", "생물의약품의 ‘복제’에 해당하는 유사 생물약. Affordable 포트에 포함."),
    ("CREXONT", "파킨슨병 치료 브랜드. Specialty 성장의 대표 제품."),
    ("BREKIYA", "군발두통용 오토인젝터(자동주사). 신규 론치 모멘텀."),
    ("bp (basis point)", "0.01%p. 750bp = 7.5%p 마진 상승."),
    ("레버리지", "부채/이익 배수. 낮아질수록 재무 부담↓."),
])}
</div>

<div class="block">
<h2>2. 시장 깔때기 — TAM → SAM → SOM</h2>
<div class="plain">
  <strong>쉽게:</strong> 미국 약 시장은 거대하지만, AMRX가 잘 파는 구역은
  “만들기 어려운 복제약 + 신경·내분비 브랜드 + 정부 납품”입니다.
</div>
{c3}

<table>
  <tr><th>단계</th><th>대략</th><th>정의</th><th>헷갈리기 쉬운 점</th></tr>
  <tr>
    <td>TAM</td>
    <td>미국 처방약 전체</td>
    <td>제네릭·브랜드·바이오시밀러</td>
    <td>TAM ≠ AMRX 매출</td>
  </tr>
  <tr>
    <td>SAM</td>
    <td>복잡 제형·CNS/내분비</td>
    <td>가격전쟁 덜한 니치 + 브랜드</td>
    <td>단순 정제 제네릭은 마진 얇음</td>
  </tr>
  <tr>
    <td>SOM</td>
    <td>~$3B+ 매출</td>
    <td>AMRX 포트폴리오(~300여 제품군)</td>
    <td>시총~$5.6B와 혼동 금지</td>
  </tr>
  <tr>
    <td>전환 스토리</td>
    <td>믹스 프리미엄화</td>
    <td>Specialty↑ · 저마진 유통↓</td>
    <td>매출 성장이 느려도 이익은 늘 수 있음</td>
  </tr>
</table>

{gloss([
    ("TAM / SAM / SOM", "전체 시장 / 팔 수 있는 시장 / 실제로 가져가는 규모."),
    ("CNS", "중추신경계. 파킨슨·편두통 등이 여기."),
    ("니치", "경쟁이 덜한 좁은 영역. 복잡 제네릭이 여기에 가깝다."),
])}
</div>

<div class="block">
<h2>3. 민감도 사슬 — 무엇이 이익을 흔드나</h2>
<div class="plain">
  <strong>쉽게:</strong> 복제약 코너에서는 경쟁사가 가격을 깎으면 마진이 바로 줄고,
  Specialty 코너에서는 처방 수가 늘면 이익이 빨리 붙습니다.
  회사는 일부러 싼 유통을 줄여 “남는 장사” 비중을 키우는 중입니다.
</div>
{c4}

<table>
  <tr><th>단계</th><th>좋게 나오면</th><th>나쁘게 나오면</th></tr>
  <tr><td>① 제네릭 가격·점유</td><td>복잡 제품 수요 유지</td><td>가격 전쟁·공급 과잉</td></tr>
  <tr><td>② 론치 파이프라인</td><td>신제품 출시·점유</td><td>승인 지연·실패</td></tr>
  <tr><td>③ Specialty 침투</td><td>CREXONT·BREKIYA 가속</td><td>처방 정체·경쟁 브랜드</td></tr>
  <tr><td>④ 믹스</td><td>GM·Adj.GM 지속 상승</td><td>저마진 비중 재확대</td></tr>
  <tr><td>⑤ 총이익</td><td>Q1처럼 bp 확대</td><td>원가·리베이트 악화</td></tr>
  <tr><td>⑥ 이자·부채</td><td>레버리지 3.5x→추가 하락</td><td>금리·리파이낸스 부담</td></tr>
  <tr><td>⑦ EPS</td><td>연속 Beat</td><td>매출 Miss + EPS Miss 동시</td></tr>
</table>

<p>
과거 패턴: <strong>EPS는 잘 맞추거나(4/4 Beat), 매출은 컨센서스를 종종 밑돈 이력</strong>이 있습니다.
07-30에는 EPS Beat만 보고 안심하지 말고 <strong>매출·Specialty·가이던스 톤</strong>을 같이 봐야 합니다.
</p>

{gloss([
    ("가격 침식 (Price erosion)", "복제약 경쟁으로 판매가가 계속 내려가는 현상."),
    ("론치 (Launch)", "신약·신제네릭 출시. 초반 처방이 성장 곡선."),
    ("리베이트", "보험·유통에 돌려주는 금액. 커지면 순매출↓."),
])}
</div>

<div class="block">
<h2>4. Bear / Base / Bull — 숫자 시나리오</h2>
<div class="plain">
  <strong>쉽게:</strong> FY25 매출 ~$3.0B를 기준으로, Specialty 가속 여부를 갈라 작업용 시나리오를 잡았습니다.
</div>
{c5}

<table>
  <tr><th>시나리오</th><th>가정</th><th>매출</th><th>Adj.EPS(개념)</th><th>주가 함의</th></tr>
  <tr>
    <td>Bear</td>
    <td>제네릭 가격전쟁, Specialty 둔화, 매출·가이던스 실망</td>
    <td>~$2.9B</td>
    <td>~$0.70</td>
    <td>$12–15</td>
  </tr>
  <tr>
    <td>Base</td>
    <td>Affordable +7–8%, Specialty 고성장 유지, 마진 개선</td>
    <td>~$3.2B</td>
    <td>~$0.95</td>
    <td>$17–20 (PT 평균~$18)</td>
  </tr>
  <tr>
    <td>Bull</td>
    <td>CREXONT·BREKIYA 초과, 론치 풍년, 레버리지↓</td>
    <td>~$3.5B+</td>
    <td>~$1.15</td>
    <td>$21–24 (PT 고점 $23)</td>
  </tr>
</table>

<p>
현재가 <strong>$17.50</strong> vs PT 평균 <strong>$18.3</strong>(+4%) · 저점 PT $16 · 고점 $23.
52주 고점 $18.39 근처라 <strong>업사이드가 얇고 고점권</strong>입니다.
Chase RR 오늘 12위 — NEO(1위)보다 우선순위가 낮은 이유입니다.
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
  <strong>쉽게:</strong> 복제약 선반은  crowded 합니다. AMRX는 “만들기 어려운 약 + 브랜드”로 빠져나가려 합니다.
</div>
<table>
  <tr><th>전선</th><th>AMRX</th><th>압력</th><th>관찰</th></tr>
  <tr>
    <td>Affordable / 제네릭</td>
    <td>복잡·주사·바이오시밀러</td>
    <td>Teva·Viatris 등 가격경쟁</td>
    <td>GM, 론치 수</td>
  </tr>
  <tr>
    <td>Specialty</td>
    <td>CREXONT·BREKIYA</td>
    <td>기존 파킨슨·두통 치료제</td>
    <td>처방·매출 런레이트</td>
  </tr>
  <tr>
    <td>AvKARE</td>
    <td>정부 채널</td>
    <td>계약·입찰</td>
    <td>저마진 유통 축소 지속?</td>
  </tr>
</table>
{gloss([
    ("오토인젝터", "환자가 스스로 주사하기 쉽게 만든 자동 주사 기기. BREKIYA."),
])}
</div>

<div class="block">
<h2>6. 선행 지표</h2>
<ul>
  <li><strong>Specialty 매출·CREXONT·BREKIYA 코멘트</strong></li>
  <li><strong>Affordable 성장 vs 가이던스 7–8%</strong></li>
  <li><strong>총이익률·조정총이익률 bp</strong></li>
  <li><strong>AvKARE 믹스</strong> (정부↑ 유통↓ 유지 여부)</li>
  <li><strong>순레버리지·이자</strong></li>
  <li><strong>07-30 실적</strong> — 컨센서스 EPS ~$0.23, 매출 ~$771M</li>
</ul>
{gloss([
    ("선행 지표", "실적 전 방향성을 가늠하는 신호."),
])}
</div>

<div class="block">
<h2>7. 비중 상한 · Thesis Breakers</h2>
{c8}
<div class="plain">
  <strong>쉽게:</strong> 미보유. 수요일 예비금에서 <strong>NEO 다음 순위</strong>.
  고점권·07-30이라 <strong>실적 전 추격 금지</strong>, 좋으면 <strong>반만</strong>만.
</div>
<table>
  <tr><th>항목</th><th>권고</th><th>이유</th></tr>
  <tr><td>실적 전</td><td><strong>매수 금지</strong></td><td>고점·이벤트·PT여유 얇음</td></tr>
  <tr><td>실적 후</td><td>톤 양호 시 <strong>반만</strong> ($16–17.5 선호)</td><td>NEO보다 후순위</td></tr>
  <tr><td>비중 상한</td><td>총자산 ~8–12%</td><td>소액 포트</td></tr>
  <tr><td>추격 $18+</td><td>스킵</td><td>RR 나쁨</td></tr>
</table>

<div class="warn">
  <strong>Thesis Breakers:</strong>
  <ul>
    <li>Specialty 성장 급락·주요 브랜드 처방 정체</li>
    <li>제네릭 가격전쟁으로 GM 재악화</li>
    <li>매출·Adj.EPS 가이던스 하향</li>
    <li>레버리지 재상승·유동성 이슈</li>
    <li>연속 EPS Beat가 Miss로 전환</li>
  </ul>
</div>

{gloss([
    ("반만", "의도 수량의 절반만 매수."),
    ("Thesis Breaker", "매수 논리를 깨는 사건."),
])}
</div>

<div class="block">
<h2>8. 한계 · 출처</h2>
<ul>
  <li>시가·PT·일부 재무: Yahoo Finance.</li>
  <li>세그먼트·제품·마진: Amneal IR / Q1'26 실적·콜.</li>
  <li>시나리오는 작업용. 투자 권고 아님.</li>
</ul>
<div class="footer-note">
  생성: 수익구조분석() · 티커 AMRX · 기준 {ASOF} · WeasyPrint + NanumGothic
</div>
</div>

</body></html>
"""
    return html


def main() -> None:
    charts = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "spec": chart_specialty_drivers(),
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
