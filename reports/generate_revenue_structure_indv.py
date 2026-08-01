#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(INDV) — 시각자료 + 초보용 설명 + 전문용어 주석 + WeasyPrint PDF."""

from __future__ import annotations

import base64
import io
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
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from weasyprint import HTML

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
ASOF = "2026-07-20"
OUT_PDF = [
    Path("/opt/cursor/artifacts/INDV_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/INDV_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/INDV_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/indv")
CHART_DIR.mkdir(parents=True, exist_ok=True)

# --- matplotlib Korean ---
fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

COLORS = {
    "teal": "#0d5c4d",
    "teal2": "#1a7a66",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "blue": "#1e3a5f",
    "light": "#f7f3eb",
    "green": "#166534",
}


def img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def save_fig(fig, name: str) -> Path:
    p = CHART_DIR / name
    fig.savefig(p, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def chart_product_mix() -> Path:
    """Q1'26 product / geo mix pie."""
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    # Product (of total NR $317M): SUBLOCADE 73%, Sublingual 25%, PERSERIS ~2%
    ax = axes[0]
    sizes = [232, 80, 5]  # approx total SUBLOCADE / film+other / PERSERIS of 317
    # more precise: US subloca 218 + RoW subloca 14 = 232; film 50; PERSERIS 5; RoW other in film/other mix
    # Use reported shares: 73% / 25% / 2%
    sizes = [73, 25, 2]
    labels = ["SUBLOCADE\n73%", "설하정·기타\n25%", "PERSERIS\n2%"]
    wedges, *_ = ax.pie(
        sizes,
        labels=labels,
        colors=[COLORS["teal"], COLORS["gold"], COLORS["sand"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("제품별 순매출 비중 (Q1'26)", fontproperties=PROP_B, fontsize=11, color=COLORS["ink"])

    ax = axes[1]
    sizes = [272, 45]
    labels = ["미국\n272M (86%)", "해외(RoW)\n45M (14%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[COLORS["blue"], COLORS["teal2"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("지역별 순매출 (Q1'26, 총 317M USD)", fontproperties=PROP_B, fontsize=11, color=COLORS["ink"])
    fig.suptitle("INDV 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    return save_fig(fig, "01_product_geo_mix.png")


def chart_us_sublocade_bridge() -> Path:
    """US product breakdown bar."""
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    cats = ["SUBLOCADE\n(미국)", "설하정·기타\n(미국)", "PERSERIS\n(미국)", "해외\n(RoW 합계)"]
    vals_26 = [218, 50, 5, 45]
    vals_25 = [163, 54, 4, 44]
    x = range(len(cats))
    w = 0.36
    ax.bar([i - w / 2 for i in x], vals_25, w, label="Q1'25", color=COLORS["sand"], edgecolor="white")
    ax.bar([i + w / 2 for i in x], vals_26, w, label="Q1'26", color=COLORS["teal"], edgecolor="white")
    ax.set_xticks(list(x))
    ax.set_xticklabels(cats, fontproperties=PROP, fontsize=9)
    ax.set_ylabel("순매출 (백만 USD)", fontproperties=PROP)
    ax.set_title("제품·지역별 순매출 비교 — Q1'25 vs Q1'26", fontproperties=PROP_B, fontsize=12)
    ax.legend(prop=PROP, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for i, (a, b) in enumerate(zip(vals_25, vals_26)):
        ch = (b - a) / a * 100 if a else 0
        ax.text(i + w / 2, b + 3, f"{ch:+.0f}%", ha="center", fontsize=8, fontproperties=PROP, color=COLORS["teal"])
    return save_fig(fig, "02_product_yoy.png")


def chart_tam_funnel() -> Path:
    """TAM → SAM → SOM funnel."""
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    layers = [
        (9.2, 8.2, "TAM ≈ 15–25B+ USD", "오피오이드 사용장애(OUD) 치료·관련 의료비 전체 시장", COLORS["sand"]),
        (7.4, 6.0, "SAM ≈ 4–7B USD", "약물보조치료(MAT/BMAT) · 부프레노르핀 계열 처방 시장", COLORS["gold"]),
        (5.6, 3.8, "SOM (현재) ≈ 1.2–1.3B USD", "INDV FY25 순매출 1.24B · FY26 가이던스 1.22–1.29B", COLORS["teal2"]),
        (4.0, 1.8, "핵심 SOM 엔진", "SUBLOCADE 장기주사: FY26 가이던스 0.95–0.99B USD", COLORS["teal"]),
    ]
    for w, y, title, sub, c in layers:
        x0 = (10 - w) / 2
        box = FancyBboxPatch(
            (x0, y - 0.85),
            w,
            1.55,
            boxstyle="round,pad=0.02,rounding_size=0.15",
            facecolor=c,
            edgecolor="white",
            linewidth=2,
            alpha=0.92,
        )
        ax.add_patch(box)
        tc = "white" if c in (COLORS["teal"], COLORS["teal2"], COLORS["blue"]) else COLORS["ink"]
        ax.text(5, y + 0.25, title, ha="center", va="center", fontproperties=PROP_B, fontsize=11, color=tc)
        ax.text(5, y - 0.35, sub, ha="center", va="center", fontproperties=PROP, fontsize=8.5, color=tc)
    ax.set_title("시장 깔때기(TAM→SAM→SOM) — INDV가 먹을 수 있는 파이", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "03_tam_funnel.png")


def chart_sensitivity() -> Path:
    """Sensitivity chain waterfall-ish."""
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    steps = [
        "신규환자\n시작 수",
        "투약\n지속률",
        "처방\n단가·믹스",
        "총→순\n조정(GTN)",
        "매출총이익\n마진",
        "영업비용\n레버리지",
        "순이익\n·EPS",
    ]
    xs = list(range(len(steps)))
    ys = [1.0, 0.92, 0.88, 0.78, 0.85, 0.72, 0.68]
    ax.plot(xs, ys, "o-", color=COLORS["teal"], lw=2.5, ms=9)
    for i, (s, y) in enumerate(zip(steps, ys)):
        ax.annotate(
            s,
            (i, y),
            textcoords="offset points",
            xytext=(0, 14),
            ha="center",
            fontproperties=PROP,
            fontsize=8,
            color=COLORS["ink"],
        )
    ax.set_ylim(0.55, 1.15)
    ax.set_xticks([])
    ax.set_ylabel("상대 기여(개념)", fontproperties=PROP)
    ax.set_title("민감도 사슬 — 무엇이 이익을 흔드나 (왼쪽→오른쪽)", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.axhline(0.75, color=COLORS["sand"], ls="--", lw=1)
    ax.text(6.1, 0.76, "이익 구간", fontproperties=PROP, fontsize=8, color=COLORS["muted"])
    return save_fig(fig, "04_sensitivity.png")


def chart_scenarios() -> Path:
    """Bear/Base/Bull revenue & EPS bars."""
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    labels = ["Bear", "Base", "Bull"]
    rev = [1100, 1250, 1380]  # $M FY26-ish scenarios
    eps = [3.2, 4.6, 5.8]
    colors = [COLORS["red"], COLORS["gold"], COLORS["teal"]]
    ax = axes[0]
    bars = ax.bar(labels, rev, color=colors, edgecolor="white", width=0.55)
    ax.set_title("시나리오별 연간 순매출 (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 20, f"{v}", ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 1600)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    bars = ax.bar(labels, eps, color=colors, edgecolor="white", width=0.55)
    ax.set_title("시나리오별 조정 EPS (USD/주)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("USD / 주", fontproperties=PROP)
    for b, v in zip(bars, eps):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.12, f"{v}", ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("Bear / Base / Bull — 숫자로 본 세 갈래 미래", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "05_scenarios.png")


def chart_quarterly_trend() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [266, 302, 314, 358, 317]
    oi = [67, 71, 44, 83, 137]
    x = range(len(labels))
    ax.bar(x, rev, color=COLORS["teal"], alpha=0.85, label="순매출 (백만 USD)", width=0.55)
    ax2 = ax.twinx()
    ax2.plot(x, oi, "o-", color=COLORS["gold"], lw=2.2, ms=8, label="영업이익 (백만 USD)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("순매출 (백만 USD)", fontproperties=PROP, color=COLORS["teal"])
    ax2.set_ylabel("영업이익 (백만 USD)", fontproperties=PROP, color=COLORS["gold"])
    ax.set_title("분기 추이 — 매출과 영업이익이 같이 가는가?", fontproperties=PROP_B, fontsize=12)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    return save_fig(fig, "06_quarterly.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["~4Q전", "~3Q전", "~2Q전", "최근(Q1'26)"]
    actual = [0.51, 0.72, 0.82, 0.96]
    est = [0.25, 0.41, 0.67, 0.66]
    surprise = [104, 75, 22, 45]  # %
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], est, w, label="예상 EPS", color=COLORS["sand"])
    ax.bar([i + w / 2 for i in x], actual, w, label="실제 EPS", color=COLORS["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("EPS (USD)", fontproperties=PROP)
    ax.set_title("실적 서프라이즈 — 예상보다 얼마나 잘했나", fontproperties=PROP_B, fontsize=12)
    for i, s in enumerate(surprise):
        ax.text(i + w / 2, actual[i] + 0.04, f"+{s}%", ha="center", fontsize=8, fontproperties=PROP, color=COLORS["green"])
    ax.legend(prop=PROP, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "07_eps_surprise.png")


def chart_position() -> Path:
    """Position sizing visual."""
    fig, ax = plt.subplots(figsize=(8.5, 2.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    # portfolio slots
    boxes = [
        (0.3, 0.6, 2.2, 1.6, "코어\nECPG", COLORS["teal"]),
        (2.8, 0.6, 2.2, 1.6, "코어\nASTH", COLORS["teal2"]),
        (5.3, 0.6, 2.2, 1.6, "INDV\n보유 1주\n추가 금지", COLORS["gold"]),
        (7.8, 0.6, 2.0, 1.6, "현금\n버퍼", COLORS["sand"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = COLORS["ink"] if c in (COLORS["sand"], COLORS["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=tc)
    ax.set_title("포지션 맥락 — 소액 집중 포트에서 INDV의 자리", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "08_position.png")


def gloss(items: list[tuple[str, str]]) -> str:
    """Render footnote glossary for a block."""
    if not items:
        return ""
    lis = "".join(f"<li><span class='term'>{t}</span> — {d}</li>" for t, d in items)
    return f"<div class='gloss'><div class='gloss-title'>이 블록 용어 주석</div><ul>{lis}</ul></div>"


def fig_block(path: Path, caption: str) -> str:
    b64 = img_b64(path)
    return f"""
    <figure class="viz">
      <img src="data:image/png;base64,{b64}" alt="{caption}"/>
      <figcaption>{caption}</figcaption>
    </figure>
    """


def build_html(charts: dict[str, Path]) -> str:
    css = f"""
    @font-face {{
      font-family: 'NanumGothic';
      src: url('file://{FONT_REG}');
      font-weight: 400;
    }}
    @font-face {{
      font-family: 'NanumGothic';
      src: url('file://{FONT_BOLD}');
      font-weight: 700;
    }}
    @page {{
      size: A4;
      margin: 16mm 14mm 18mm 14mm;
      @bottom-center {{
        content: "수익구조분석(INDV) · {ASOF} · " counter(page) " / " counter(pages);
        font-family: NanumGothic;
        font-size: 8.5pt;
        color: #78716c;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: NanumGothic, sans-serif;
      color: #1c1917;
      font-size: 10pt;
      line-height: 1.55;
      background: #fff;
    }}
    h1 {{
      font-size: 20pt;
      font-weight: 700;
      margin: 0 0 4px;
      color: #0d5c4d;
    }}
    h2 {{
      font-size: 13.5pt;
      font-weight: 700;
      margin: 22px 0 8px;
      padding-bottom: 4px;
      border-bottom: 2px solid #0d5c4d;
      color: #0d5c4d;
      page-break-after: avoid;
    }}
    h3 {{
      font-size: 11pt;
      font-weight: 700;
      margin: 12px 0 6px;
      color: #1e3a5f;
    }}
    .meta {{ color: #57534e; font-size: 9pt; margin-bottom: 14px; }}
    .hero {{
      background: linear-gradient(135deg, #0d5c4d 0%, #1a7a66 55%, #b8860b 130%);
      color: #fff;
      padding: 18px 18px 16px;
      border-radius: 6px;
      margin-bottom: 16px;
    }}
    .hero h1 {{ color: #fff; }}
    .hero .oneline {{
      font-size: 12pt;
      margin-top: 8px;
      line-height: 1.45;
    }}
    .kpi {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 10px 0 0;
    }}
    .kpi span {{
      background: rgba(255,255,255,0.15);
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 8.5pt;
    }}
    .block {{
      page-break-inside: avoid;
      margin-bottom: 6px;
    }}
    p {{ margin: 0 0 8px; }}
    ul {{ margin: 4px 0 10px 18px; padding: 0; }}
    li {{ margin-bottom: 3px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 8px 0 12px;
      font-size: 9pt;
    }}
    th, td {{
      border: 1px solid #d6d3d1;
      padding: 5px 7px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #0d5c4d;
      color: #fff;
      font-weight: 700;
    }}
    tr:nth-child(even) td {{ background: #f7f3eb; }}
    .viz {{
      margin: 8px 0 12px;
      text-align: center;
    }}
    .viz img {{
      max-width: 100%;
      height: auto;
    }}
    .viz figcaption {{
      font-size: 8.5pt;
      color: #57534e;
      margin-top: 4px;
    }}
    .callout {{
      background: #f7f3eb;
      border-left: 4px solid #b8860b;
      padding: 8px 12px;
      margin: 8px 0 12px;
      font-size: 9.5pt;
    }}
    .gloss {{
      background: #fafaf9;
      border: 1px solid #e7e5e4;
      padding: 8px 12px;
      margin: 6px 0 14px;
      font-size: 8.5pt;
      color: #44403c;
    }}
    .gloss-title {{
      font-weight: 700;
      color: #1e3a5f;
      margin-bottom: 4px;
      font-size: 9pt;
    }}
    .gloss ul {{ margin: 0 0 0 14px; }}
    .gloss .term {{
      font-weight: 700;
      color: #0d5c4d;
    }}
    .plain {{
      background: #ecfdf5;
      border: 1px solid #a7f3d0;
      padding: 8px 12px;
      margin: 6px 0 10px;
      font-size: 9.5pt;
    }}
    .plain strong {{ color: #065f46; }}
    .warn {{
      background: #fff1f2;
      border-left: 4px solid #9f1239;
      padding: 8px 12px;
      margin: 8px 0;
      font-size: 9.5pt;
    }}
    .footer-note {{
      font-size: 8pt;
      color: #78716c;
      margin-top: 18px;
      border-top: 1px solid #e7e5e4;
      padding-top: 8px;
    }}
    """

    # Charts
    c1 = fig_block(charts["mix"], "그림 1. 제품·지역 파이 — 한눈에 보는 돈의 출처")
    c2 = fig_block(charts["yoy"], "그림 2. 제품별 YoY — SUBLOCADE가 성장을 끌어올림")
    c3 = fig_block(charts["funnel"], "그림 3. TAM→SAM→SOM 깔때기 — 시장 크기와 INDV의 자리")
    c4 = fig_block(charts["sens"], "그림 4. 민감도 사슬 — 환자→투약→가격→마진→이익")
    c5 = fig_block(charts["scen"], "그림 5. Bear/Base/Bull 숫자 시나리오")
    c6 = fig_block(charts["qtr"], "그림 6. 최근 5분기 매출·영업이익")
    c7 = fig_block(charts["eps"], "그림 7. EPS 서프라이즈 이력 (4분기)")
    c8 = fig_block(charts["pos"], "그림 8. 포트폴리오 안에서의 INDV 비중 원칙")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<title>수익구조분석 — INDV (Indivior)</title>
<style>{css}</style>
</head>
<body>

<div class="hero">
  <h1>수익구조분석 · INDV</h1>
  <div>Indivior Pharmaceuticals, Inc. · 나스닥 · 오피오이드 사용장애(OUD) 치료 전문 제약</div>
  <div class="oneline">
    <strong>한 줄 구조:</strong> 미국에서 매달 맞는 장기 주사제 SUBLOCADE가 순매출의 약 73%를 만들고,
    나머지는 혀 밑에 녹여 먹는 설하정(SUBOXONE 등)과 소량의 PERSERIS·해외 매출입니다.
    즉 “중독 치료약을 팔아서, 그중에서도 주사제 침투율이 올라가면 이익이 커지는” 회사입니다.
  </div>
  <div class="kpi">
    <span>종가 ${40.54:.2f}</span>
    <span>시총 ~$4.8B</span>
    <span>PT ${46:.0f} / ${50.8:.1f} / ${59:.0f}</span>
    <span>Q1'26 매출 $317M (+19%)</span>
    <span>SUBLOCADE $232M (+32%)</span>
    <span>GM ~85% · OM ~46%</span>
    <span>실적일(차기 관전) 07-30 전후</span>
    <span>기준일 {ASOF}</span>
  </div>
</div>

<div class="plain">
  <strong>이 보고서를 읽는 법 (비전공자용):</strong>
  아래 블록은 “이 회사가 어디서 돈을 버는지 → 시장이 얼마나 큰지 → 무엇이 흔들리는지 →
  좋은/나쁜 경우 숫자 → 경쟁 → 미리 볼 신호 → 얼마나 살지” 순서로 이어집니다.
  각 블록 끝에 <em>용어 주석</em>이 있고, 이미 설명한 말은 다시 쓰지 않습니다.
</div>

<!-- ========== BLOCK 1 ========== -->
<div class="block">
<h2>1. 수익 구조 — 제품·지역·마진</h2>
<div class="plain">
  <strong>쉽게:</strong> 가게로 치면 “주력 메뉴(SUBLOCADE 주사)”가 손님의 대부분을 데려오고,
  “예전부터 팔던 알약(설하정)”은 아직 있지만 비중이 줄고 있습니다.
  미국이 전체의 약 86%라서, 미국 보험·처방 환경이 곧 회사 실적입니다.
</div>
{c1}
{c2}

<h3>1-1. Q1'26 숫자로 본 매출 분해</h3>
<table>
  <tr><th>구분</th><th>금액</th><th>전년동기</th><th>YoY</th><th>의미</th></tr>
  <tr><td>총 순매출</td><td>$317M</td><td>$266M</td><td>+19%</td><td>회사 전체 성장</td></tr>
  <tr><td>SUBLOCADE (전세계)</td><td>$232M</td><td>$176M</td><td>+32%</td><td>성장 엔진, 총매출의 73%</td></tr>
  <tr><td> ㄴ 미국 SUBLOCADE</td><td>$218M</td><td>$163M</td><td>+33%</td><td>투약량 +20% + 가격·믹스 유리</td></tr>
  <tr><td>미국 설하정·기타</td><td>$50M</td><td>$54M</td><td>−9%</td><td>점유율·카테고리 압력</td></tr>
  <tr><td>미국 PERSERIS</td><td>$5M</td><td>$4M</td><td>+11%</td><td>마케팅 축소 상태의 소량</td></tr>
  <tr><td>해외(Rest of World)</td><td>$45M</td><td>$44M</td><td>+2%</td><td>보조 축, 의존도 낮음</td></tr>
</table>

<p>
미국 SUBLOCADE만으로도 Q1에 <strong>$218M</strong>을 만들었고, 신규 환자 시작이 약 <strong>31,800명(분기 기록)</strong>이었습니다.
투약 단위(dispense unit)는 약 <strong>+20%</strong> 늘어났고, 여기에 가격·제품 구성(믹스)과
총매출→순매출 조정(리베이트·할인 반영)이 유리하게 작용해 매출 증가율이 볼륨보다 높았습니다.
</p>

<h3>1-2. 연간·분기 추이 (보고 재무)</h3>
<table>
  <tr><th>연도</th><th>매출</th><th>매출총이익</th><th>영업이익</th><th>순이익</th></tr>
  <tr><td>FY2022</td><td>$901M</td><td>$750M</td><td>$215M</td><td>−$44M</td></tr>
  <tr><td>FY2023</td><td>$1,093M</td><td>$919M</td><td>$247M</td><td>−$126M</td></tr>
  <tr><td>FY2024</td><td>$1,188M</td><td>$957M</td><td>$234M</td><td>$7M</td></tr>
  <tr><td>FY2025</td><td>$1,239M</td><td>$993M</td><td>$265M</td><td>$210M</td></tr>
</table>
{c6}
<p>
연간 매출은 4년 연속 증가했습니다. FY25 매출총이익률은 약 <strong>80%대 중반~후반</strong>(보고 GM ~85% 수준)으로
“약 원가 대비 판매가가 매우 높은” 전형적인 브랜드·스페셜티 제약 구조입니다.
Q1'26 영업이익 $137M은 전년 Q1 $67M 대비 크게 늘어, 매출보다 이익 레버리지가 더 세게 나왔습니다.
</p>

<div class="callout">
  FY26 가이던스(상향 후): 순매출 <strong>$1,215–1,285M</strong> · SUBLOCADE <strong>$950–990M</strong> ·
  조정 EBITDA <strong>$620–660M</strong>. 경영진이 “주사제 비중 확대 + 비용 통제”로 이익 가속을 공식화한 상태입니다.
</div>

{gloss([
    ("순매출(Net Revenue)", "약국·도매에 청구하는 정가에서 리베이트·할인·반품 등을 뺀 뒤, 회사가 실제로 장부에 올리는 매출."),
    ("SUBLOCADE", "부프레노르핀 성분 월 1회 피하 주사제. 매일 약을 챙겨 먹기 어려운 환자를 위해 ‘한 달치 효과를 주사로’ 주는 제품."),
    ("설하정(Sublingual)", "혀 밑에 녹여 먹는 알약/필름. SUBOXONE Film 등이 여기 속함. 매일 복용해야 해서 순응도(꾸준히 먹는 정도)가 과제."),
    ("PERSERIS", "조현병 등용 장기 주사제. INDV에서 마케팅을 줄여 매출 기여가 작음."),
    ("YoY (Year-over-Year)", "작년 같은 기간과 비교한 증감률."),
    ("매출총이익률(Gross Margin)", "(매출 − 매출원가) ÷ 매출. 약 제조·구매 원가 대비 남는 비율."),
    ("영업이익(Operating Income)", "매출총이익에서 판매·관리·연구비 등 영업비용을 뺀 본업 이익."),
    ("EBITDA", "이자·세금·감가상각 전 이익. 현금창출력의 대략적 지표로 자주 씀."),
    ("가이던스(Guidance)", "회사가 앞으로의 매출·이익 범위를 미리 알려주는 공식 전망."),
])}
</div>

<!-- ========== BLOCK 2 ========== -->
<div class="block">
<h2>2. 시장 깔때기 — TAM → SAM → SOM</h2>
<div class="plain">
  <strong>쉽게:</strong> 피자를 상상하세요. <em>TAM</em>은 동네 전체 피자 수요,
  <em>SAM</em>은 “배달 가능한 우리 메뉴와 겹치는 수요”,
  <em>SOM</em>은 “지금 우리가 실제로 받는 주문”입니다.
  INDV는 “중독 치료”라는 큰 판에서, “부프레노르핀 계열 약물치료”로 좁히고,
  그중 “우리 주사제·필름을 사는 환자”가 실제 매출입니다.
</div>
{c3}

<table>
  <tr><th>단계</th><th>대략 규모</th><th>정의(INDV 맥락)</th><th>헷갈리기 쉬운 점</th></tr>
  <tr>
    <td>TAM</td>
    <td>~$15–25B+</td>
    <td>오피오이드 사용장애 관련 치료·의료·사회비용이 얽힌 넓은 시장</td>
    <td>TAM이 커도 약값이 다 회사 매출이 되진 않음</td>
  </tr>
  <tr>
    <td>SAM</td>
    <td>~$4–7B</td>
    <td>약물보조치료(MAT), 특히 부프레노르핀 기반 처방 시장</td>
    <td>메사돈·행동치료만 받는 환자는 SAM 밖일 수 있음</td>
  </tr>
  <tr>
    <td>SOM (회사)</td>
    <td>~$1.2–1.3B</td>
    <td>INDV 순매출 (FY25 $1.24B, FY26 가이던스 상단 ~$1.29B)</td>
    <td>시총($4.8B)과 혼동 금지 — 시총은 ‘회사 가격’, SOM은 ‘연 매출’</td>
  </tr>
  <tr>
    <td>핵심 SOM</td>
    <td>~$0.95–0.99B</td>
    <td>SUBLOCADE FY26 가이던스</td>
    <td>침투율(주사로 갈아타는 환자 비율)이 여기의 성장 스위치</td>
  </tr>
</table>

<p>
미국 성인 중 오피오이드 사용장애를 겪는 인구는 수백만 명 규모로 추정되지만,
실제로 MAT를 꾸준히 받는 비율은 그보다 훨씬 낮습니다.
그래서 “환자 수 × 약가”를 바로 곱하면 과대평가가 됩니다.
INDV 투자 논리의 핵심은 <strong>이미 MAT를 받는 환자 안에서</strong> 매일 먹는 약 → 월 주사로 전환(침투)하는 속도입니다.
</p>

{gloss([
    ("TAM (Total Addressable Market)", "회사가 이론상 노릴 수 있는 전체 시장 크기."),
    ("SAM (Serviceable Available Market)", "현재 제품·규격·지역으로 실제로 팔 수 있는 부분 시장."),
    ("SOM (Serviceable Obtainable Market)", "경쟁·유통·브랜드를 감안해 단기적으로 가져갈 수 있는(또는 이미 가져간) 매출 규모."),
    ("OUD (Opioid Use Disorder)", "오피오이드(마약성 진통제·헤로인 등)에 대한 사용 장애. 의존·갈망·일상 기능 저하가 특징."),
    ("MAT / BMAT", "Medication-Assisted Treatment / Buprenorphine MAT. 약으로 금단·갈망을 줄이며 치료하는 방식."),
    ("침투율(Penetration)", "대상 환자 중 특정 제형(여기선 장기주사)을 쓰는 비율. 올라가면 같은 환자 풀에서 매출이 커짐."),
])}
</div>

<!-- ========== BLOCK 3 ========== -->
<div class="block">
<h2>3. 민감도 사슬 — 무엇이 이익을 흔드나</h2>
<div class="plain">
  <strong>쉽게:</strong> 공장 컨베이어처럼, 앞 단계가 흔들리면 뒤 숫자도 같이 흔들립니다.
  INDV는 “새 환자 → 계속 주사 맞음 → 보험이 인정하는 가격 → 할인 후 남는 돈 → 회사 비용” 순입니다.
</div>
{c4}

<table>
  <tr><th>단계</th><th>측정 지표(예시)</th><th>좋게 나오면</th><th>나쁘게 나오면</th></tr>
  <tr><td>① 신규 환자</td><td>분기 new patient starts (~31.8k in Q1'26)</td><td>미래 투약 저수지 확대</td><td>성장 둔화 신호</td></tr>
  <tr><td>② 지속률</td><td>재투약·유지율, discontinue</td><td>매출 ‘잔존’ 강화</td><td>신규만 많고 금방 이탈</td></tr>
  <tr><td>③ 단가·믹스</td><td>net price, channel mix</td><td>볼륨 이상으로 매출↑</td><td>할인 경쟁·믹스 악화</td></tr>
  <tr><td>④ GTN 조정</td><td>rebates, chargebacks, returns</td><td>순매출 품질↑</td><td>총매출은 커도 순매출 밋밋</td></tr>
  <tr><td>⑤ 총이익</td><td>GM ~85%</td><td>스페셜티 약 특성 유지</td><td>원가·폐기·반품 충격</td></tr>
  <tr><td>⑥ 영업비용</td><td>판관비, R&amp;D, legal</td><td>레버리지로 EPS 가속</td><td>소송·판촉비 재확대</td></tr>
  <tr><td>⑦ 순이익·EPS</td><td>GAAP / Non-GAAP EPS</td><td>밸류에이션 지지</td><td>멀티플 압축</td></tr>
</table>

<p>
Q1'26에서 관찰된 패턴: <strong>투약량 +20%</strong>인데 미국 SUBLOCADE 매출 <strong>+33%</strong> →
③④(가격·믹스·GTN)가 우호적이었다는 뜻입니다.
동시에 영업이익이 매출보다 더 빨리 늘어 <strong>⑥ 비용 레버리지</strong>도 작동 중이었습니다.
반대로 깨지기 쉬운 고리는 ① 신규 시작 둔화, 소송/규제 비용 재확대, 보험 급여(커버리지) 악화입니다.
</p>

{gloss([
    ("New patient starts", "해당 분기에 처음으로 SUBLOCADE 치료를 시작한 환자 수. 성장의 ‘입구’ 지표."),
    ("지속률 / 유지율", "시작한 환자가 몇 개월 뒤에도 계속 투약하는지. 구독형 매출과 비슷한 개념."),
    ("믹스(Mix)", "고가·고마진 제품/채널 비중이 늘거나 줄어 평균 단가·마진이 바뀌는 효과."),
    ("GTN (Gross-to-Net)", "총매출에서 리베이트·할인 등을 빼 순매출로 가는 과정. 제약 회계의 핵심."),
    ("레버리지(Operating leverage)", "매출이 늘 때 고정비가 상대적으로 덜 늘어 이익이 더 빨리 증가하는 현상."),
    ("EPS", "Earnings Per Share. 순이익 ÷ 희석 주식 수. 주당 이익."),
    ("GAAP / Non-GAAP", "법정 회계 기준 수치 vs 일회성·비현금 항목을 조정한 경영진 제시 수치."),
])}
</div>

<!-- ========== BLOCK 4 ========== -->
<div class="block">
<h2>4. Bear / Base / Bull — 숫자 시나리오</h2>
<div class="plain">
  <strong>쉽게:</strong> 날씨 예보처럼 나쁜 날·보통 날·좋은 날을 미리 적어 둡니다.
  아래 숫자는 “정확한 약속”이 아니라, 가이던스·침투율·마진을 조합한 <em>작업용 시나리오</em>입니다.
</div>
{c5}

<table>
  <tr><th>시나리오</th><th>가정</th><th>매출(연)</th><th>SUBLOCADE</th><th>조정 EPS(개념)</th><th>주가 함의(개념)</th></tr>
  <tr>
    <td>Bear</td>
    <td>신규 시작 둔화, 설하정 하락 가속, 소송·비용↑, 가이던스 하단 이탈</td>
    <td>~$1.10B</td>
    <td>~$0.85B</td>
    <td>~$3.2</td>
    <td>$28–34 압박 (실적·멀티플 동시 악화)</td>
  </tr>
  <tr>
    <td>Base</td>
    <td>FY26 가이던스 중간~상단 달성, 침투 지속, 비용 규율 유지</td>
    <td>~$1.25B</td>
    <td>~$0.97B</td>
    <td>~$4.6</td>
    <td>$46–52 (PT 밴드과 정합)</td>
  </tr>
  <tr>
    <td>Bull</td>
    <td>신규·유지 동반 강세, GTN 우호, 추가 가이던스 상향, 소송 리스크 완화</td>
    <td>~$1.38B+</td>
    <td>~$1.05B+</td>
    <td>~$5.8</td>
    <td>$55–62 (PT 고점~$59 상회 시도)</td>
  </tr>
</table>

<p>
현재 가격 <strong>$40.54</strong> vs 애널리스트 PT 평균 <strong>~$50.8</strong>(저 $46 / 고 $59) →
베이스 시나리오 대비 약 <strong>+25%</strong> 여유(업사이드)가 열려 있는 구간입니다.
다만 최근 52주 고점 $42.81 근처라 “싸게 줍는” 구간은 아니고,
실적(07-30 전후) 전후로 변동성이 커질 수 있어 <strong>추가 매수보다 보유·관전</strong>이 기본 원칙입니다.
</p>

{c7}
<p>
최근 4분기 EPS는 컨센서스 대비 <strong>+22% ~ +104%</strong>로 연속 상회(Beat)했습니다.
“예상보다 잘 내는 회사”로 시장이 인식하면 실적 전 주가가 먼저 오르고,
실적 당일에는 ‘좋은 숫자인데도 차익실현’이 나오기도 합니다(좋은 실적 ≠ 무조건 주가 상승).
</p>

{gloss([
    ("Bear / Base / Bull", "비관·기본·낙관 시나리오. 투자 메모에서 리스크 범위를 잡기 위해 씀."),
    ("컨센서스(Consensus)", "여러 증권사 애널리스트 추정치의 평균(또는 중앙값)."),
    ("Beat / Miss", "실제 실적이 컨센서스보다 좋음/나쁨."),
    ("업사이드(Upside)", "현재가 대비 목표가가 얼마나 위에 있는지(상승 여력)."),
    ("차익실현", "이미 오른 주식을 팔아 이익을 확정하는 매도. 호재에도 주가가 빠질 수 있는 이유."),
])}
</div>

<!-- ========== BLOCK 5 ========== -->
<div class="block">
<h2>5. 경쟁·점유 — 파이 싸움</h2>
<div class="plain">
  <strong>쉽게:</strong> 같은 “중독 치료약” 선반에 여러 브랜드가 있습니다.
  INDV의 옛 주력 SUBOXONE Film은 제네릭(복제약)과 싸우고,
  새 주력 SUBLOCADE는 “주사로 바꾸자”는 설득 싸움입니다.
</div>

<table>
  <tr><th>전선</th><th>INDV 위치</th><th>경쟁·대체</th><th>관찰 포인트</th></tr>
  <tr>
    <td>설하 부프레노르핀</td>
    <td>SUBOXONE Film 등, BMAT 점유 ~14–15%대(보고)</td>
    <td>다수의 제네릭·다른 브랜드 필름/정</td>
    <td>가격 압력, 점유율 하락 속도</td>
  </tr>
  <tr>
    <td>장기 주사(LAI)</td>
    <td>SUBLOCADE가 회사 성장축</td>
    <td>다른 LAI·비약물 치료·메사돈 클리닉</td>
    <td>클리닉 채택, 보험 급여, 신규 시작</td>
  </tr>
  <tr>
    <td>종합 OUD 케어</td>
    <td>약 중심</td>
    <td>행동치료·디지털치료·정부 프로그램</td>
    <td>정책 예산, 처방 접근성(의사·클리닉 수)</td>
  </tr>
</table>

<p>
전략적으로는 <strong>설하정 방어(느리게 줄이기) + 주사 공격(빠르게 늘리기)</strong> 조합입니다.
설하정이 줄어드는 것 자체는 “망하는 신호”가 아니라,
회사가 의도적으로 고마진·고잔존 주사로 포트폴리오를 옮기는 과정일 수 있습니다.
다만 주사가 설하정 감소분을 <strong>충분히 덮지 못하면</strong> 전체 매출이 꺾입니다 — 그게 Bear의 핵심 경로입니다.
</p>

{gloss([
    ("제네릭(Generic)", "특허가 만료된 뒤 나오는 복제약. 보통 더 싸서 오리지널 점유를 잠식."),
    ("LAI (Long-Acting Injectable)", "효과를 길게 가져가는 주사 제형. SUBLOCADE가 여기에 속함."),
    ("점유율(Share)", "해당 카테고리 처방·매출 중 우리 제품이 차지하는 비율."),
    ("메사돈(Methadone)", "오피오이드 의존 치료에 쓰이는 다른 계열 약물. 주로 특화 클리닉에서 투여."),
])}
</div>

<!-- ========== BLOCK 6 ========== -->
<div class="block">
<h2>6. 선행 지표 — 실적 전에 볼 것</h2>
<div class="plain">
  <strong>쉽게:</strong> 시험 점수(실적)가 나오기 전에, 출석·숙제(선행 지표)를 보면 대략 짐작할 수 있습니다.
</div>
<ul>
  <li><strong>신규 환자 시작 수</strong> — 가이던스 상향의 연료. 둔화 시 즉시 경계.</li>
  <li><strong> dispenses / 볼륨 코멘트</strong> — 가격 착시 없이 “약이 실제로 더 나갔는지”.</li>
  <li><strong>GTN·믹스 코멘트</strong> — 매출이 볼륨보다 너무 빠르거나 느리면 여기 확인.</li>
  <li><strong>소송·규제 헤드라인</strong> — 비용·충당금·평판. Non-GAAP와 GAAP 괴리 확대 여부.</li>
  <li><strong>자사주 매입 속도</strong> — Q1'26에 약 400만 주 / $125M 매입. EPS에 도움, 현금·부채와 균형 확인.</li>
  <li><strong>차기 실적(시장 관전 07-30 전후)</strong> — Beat여도 가이던스 톤이 더 중요할 수 있음.</li>
</ul>
{gloss([
    ("선행 지표(Leading indicator)", "실적 숫자보다 먼저 움직이는 신호. 방향성을 미리 보여 줌."),
    ("자사주 매입(Buyback)", "회사가 자기 주식을 사들이는 것. 주식 수가 줄면 EPS가 높아질 수 있음."),
    ("충당금", "앞으로 나갈 가능성이 큰 비용(소송 합의 등)을 미리 비용으로 잡아 두는 회계."),
])}
</div>

<!-- ========== BLOCK 7 ========== -->
<div class="block">
<h2>7. 비중 상한 · Thesis Breakers</h2>
{c8}
<div class="plain">
  <strong>쉽게:</strong> 소액으로 종목을 몇 개만 들고 있다면, 한 종목에 올인하지 않는 게 생존 규칙입니다.
  INDV는 이미 보유 중이고 고점·실적 임박이라 <strong>추가 매수(애드)는 하지 않는다</strong>가 기본값입니다.
</div>

<table>
  <tr><th>항목</th><th>권고</th><th>이유</th></tr>
  <tr><td>현재 포지션</td><td>보유(Hold) 1주</td><td>Beat 머신·업사이드 존재, 이미 편입</td></tr>
  <tr><td>추가 매수</td><td><strong>금지</strong> (실적 전)</td><td>고점권 + 이벤트 리스크 + 현금은 다른 기회(버퍼)용</td></tr>
  <tr><td>비중 상한(소액 포트)</td><td>총 자산의 ~15–20% 이내</td><td>집중 포트(3–4종목)에서도 단일 리스크 제한</td></tr>
  <tr><td>재진입 후보 조건</td><td>실적 후 눌림 + 가이던스 유지</td><td>예: 의미 있는 조정 후 Base 시나리오 유지</td></tr>
</table>

<div class="warn">
  <strong>Thesis Breakers (논리가 깨지는 신호):</strong>
  <ul>
    <li>SUBLOCADE 신규 시작·볼륨이 뚜렷하게 꺾이는데 설하정 하락은 가속</li>
    <li>FY 가이던스 하향, 또는 조정 EBITDA 가이던스 후퇴</li>
    <li>대형 소송 비용·합의금으로 현금·이익이 훼손</li>
    <li>보험 급여·처방 접근성 악화가 실적 콜에서 반복 언급</li>
    <li>연속 Beat가 Miss로 전환되며 컨센서스 신뢰 붕괴</li>
  </ul>
</div>

{gloss([
    ("비중 상한", "한 종목에 넣을 수 있는 최대 비율. 감정적 추격을 막는 안전장치."),
    ("애드(Add)", "이미 가진 종목을 더 사는 것. 반대로 트림(Trim)은 일부 매도."),
    ("Thesis / Thesis Breaker", "이 주식을 보유하는 핵심 논리 / 그 논리를 무효로 만드는 사건."),
    ("버퍼(현금 버퍼)", "급락·새 기회에 쓰기 위해 일부러 남겨 둔 현금."),
])}
</div>

<!-- ========== BLOCK 8 ========== -->
<div class="block">
<h2>8. 한계 · 데이터 출처</h2>
<ul>
  <li>시가·PT·재무 일부는 Yahoo Finance 등 시장 데이터 집계에 의존하며, 지연·수정될 수 있습니다.</li>
  <li>세그먼트·가이던스·환자 수는 회사 IR / 10-Q / 보도자료(Q1'26) 기준입니다.</li>
  <li>TAM·SAM은 공개 시장 추정과 산업 구조를 바탕으로 한 <strong>근사 구간</strong>이며 확정값이 아닙니다.</li>
  <li>Bear/Base/Bull EPS·주가 함의는 교육·의사결정 보조용 시나리오이며 투자 권유가 아닙니다.</li>
  <li>환율·세금·개인 계좌 제약(소수점 매수 여부 등)은 반영하지 않았습니다.</li>
</ul>
<div class="footer-note">
  생성: 수익구조분석() · 티커 INDV · 기준 {ASOF} · WeasyPrint + NanumGothic ·
  본 PDF는 정보 제공 목적이며 매수·매도 권고가 아닙니다.
</div>
</div>

</body>
</html>
"""
    return html


def main() -> None:
    charts = {
        "mix": chart_product_mix(),
        "yoy": chart_us_sublocade_bridge(),
        "funnel": chart_tam_funnel(),
        "sens": chart_sensitivity(),
        "scen": chart_scenarios(),
        "qtr": chart_quarterly_trend(),
        "eps": chart_eps_surprise(),
        "pos": chart_position(),
    }
    html = build_html(charts)
    html, _px = build_and_insert_price("INDV", CHART_DIR, html)
    if _px.ok:
        print(f"price-charts {_px.candle_path} {_px.momentum_path}")
    else:
        print(f"price-charts SKIP {_px.error}")
    OUT_HTML.write_text(html, encoding="utf-8")
    print("HTML:", OUT_HTML, OUT_HTML.stat().st_size)
    for out in OUT_PDF:
        out.parent.mkdir(parents=True, exist_ok=True)
        HTML(string=html, base_url=str(CHART_DIR)).write_pdf(out)
        print("PDF:", out, out.stat().st_size)


if __name__ == "__main__":
    main()
