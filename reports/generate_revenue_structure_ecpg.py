#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(ECPG) — 시각자료 + 초보용 설명 + 전문용어 주석 + WeasyPrint PDF."""

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
ASOF = "2026-07-20"
OUT_PDF = [
    Path("/opt/cursor/artifacts/ECPG_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/ECPG_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/ECPG_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/ecpg")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "navy": "#1e3a5f",
    "navy2": "#2c5282",
    "teal": "#0d5c4d",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "light": "#f7f3eb",
}


def img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def save_fig(fig, name: str) -> Path:
    p = CHART_DIR / name
    fig.savefig(p, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def chart_rev_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    # Q1'26 revenue mix from press release
    sizes = [390, 63, 21, 2]  # portfolio / changes in recoveries / servicing / other ≈ 475
    labels = ["포트폴리오\n수익\n390M", "회수 추정\n변동\n63M", "서비싱\n21M", "기타\n2M"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["navy"], C["teal"], C["gold"], C["sand"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("매출 구성 (Q1'26, 총 475M USD)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    # Collections geo approx: US 556 / Europe(Cabot) 161 of 718
    sizes = [556, 162]
    labels = ["미국 회수\n556M (77%)", "유럽(Cabot)\n~162M (23%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["navy2"], C["teal"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("회수(Collections) 지역 (Q1'26, 718M)", fontproperties=PROP_B, fontsize=11)
    fig.suptitle("ECPG 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    return save_fig(fig, "01_rev_geo_mix.png")


def chart_collections_purchases() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    cats = ["포트폴리오\n매입", "회수\n(Collections)", "매출\n(Revenue)", "EPS"]
    # normalize for dual visual - use two groups
    # Better: bar chart for key ops metrics
    fig.clf()
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))

    ax = axes[0]
    labels = ["Q1'25", "Q1'26"]
    coll = [605, 718]
    purch = [368, 363]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], purch, w, label="매입", color=C["sand"])
    ax.bar([i + w / 2 for i in x], coll, w, label="회수", color=C["navy"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("매입 vs 회수 (분기)", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for i, (a, b) in enumerate(zip([368, 363], [605, 718])):
        if i == 1:
            ax.text(i + w / 2, b + 12, "+19%", ha="center", fontproperties=PROP, fontsize=8, color=C["teal"])

    ax = axes[1]
    years = ["FY22", "FY23", "FY24", "FY25"]
    rev = [1398, 1223, 1316, 1769]
    ax.bar(years, rev, color=C["navy"], width=0.55)
    ax.set_title("연간 매출 추이", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for i, v in enumerate(rev):
        ax.text(i, v + 30, str(v), ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 2100)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.suptitle("운영 엔진 — 싸게 사서, 오래 회수한다", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "02_collections_purchases.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    layers = [
        (9.2, 8.3, "TAM ≈ 50B+ USD/년", "미국 등 소비자 신용 · 연체·상각(NPL) 발생 규모(대략)", C["sand"]),
        (7.6, 6.2, "SAM ≈ 수~십수 B USD", "은행·카드사가 매각하는 부실채권(NPL) 매각 시장", C["gold"]),
        (5.8, 4.1, "SOM 매입 ≈ 1.4–1.5B", "ECPG FY26 글로벌 포트폴리오 매입 가이던스", C["navy2"]),
        (4.2, 2.0, "회수·수익 엔진", "ERC ~9.8B 저수지 · FY26 회수 가이던스 ~2.8B · EPS ~13", C["navy"]),
    ]
    for w, y, title, sub, c in layers:
        x0 = (10 - w) / 2
        ax.add_patch(
            FancyBboxPatch(
                (x0, y - 0.85),
                w,
                1.55,
                boxstyle="round,pad=0.02,rounding_size=0.15",
                facecolor=c,
                edgecolor="white",
                linewidth=2,
                alpha=0.92,
            )
        )
        tc = "white" if c in (C["navy"], C["navy2"], C["teal"]) else C["ink"]
        ax.text(5, y + 0.25, title, ha="center", va="center", fontproperties=PROP_B, fontsize=11, color=tc)
        ax.text(5, y - 0.35, sub, ha="center", va="center", fontproperties=PROP, fontsize=8.2, color=tc)
    ax.set_title("시장 깔때기 — 연체 빚이 생겨서 ECPG 매출이 되기까지", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "03_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    steps = [
        "연체·상각\n공급",
        "매입가\n(IRP)",
        "회수율\n·속도",
        "ERC\n재추정",
        "매출\n인식",
        "회수비용\n·이자",
        "순이익\n·EPS",
    ]
    xs = list(range(len(steps)))
    ys = [1.0, 0.93, 0.88, 0.84, 0.80, 0.72, 0.66]
    ax.plot(xs, ys, "o-", color=C["navy"], lw=2.5, ms=9)
    for i, (s, y) in enumerate(zip(steps, ys)):
        ax.annotate(s, (i, y), textcoords="offset points", xytext=(0, 14), ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0.55, 1.15)
    ax.set_xticks([])
    ax.set_ylabel("상대 기여(개념)", fontproperties=PROP)
    ax.set_title("민감도 사슬 — 무엇이 이익을 흔드나", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "04_sensitivity.png")


def chart_scenarios() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    labels = ["Bear", "Base", "Bull"]
    coll = [2400, 2800, 3100]  # FY collections guide
    eps = [9.5, 13.0, 15.5]
    colors = [C["red"], C["gold"], C["teal"]]
    ax = axes[0]
    bars = ax.bar(labels, coll, color=colors, edgecolor="white", width=0.55)
    ax.set_title("시나리오별 연간 회수 (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, coll):
        ax.text(b.get_x() + b.get_width() / 2, v + 40, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 3600)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    bars = ax.bar(labels, eps, color=colors, edgecolor="white", width=0.55)
    ax.set_title("시나리오별 EPS (USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("USD / 주", fontproperties=PROP)
    for b, v in zip(bars, eps):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.25, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 18)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("Bear / Base / Bull — 회수와 EPS로 본 세 갈래", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "05_scenarios.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [393, 442, 460, 474, 475]
    oi = [129, 151, 173, 173, 184]
    x = range(len(labels))
    ax.bar(x, rev, color=C["navy"], alpha=0.85, label="매출 (백만 USD)", width=0.55)
    ax2 = ax.twinx()
    ax2.plot(x, oi, "o-", color=C["gold"], lw=2.2, ms=8, label="영업이익 (백만 USD)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("매출 (백만 USD)", fontproperties=PROP, color=C["navy"])
    ax2.set_ylabel("영업이익 (백만 USD)", fontproperties=PROP, color=C["gold"])
    ax.set_title("분기 추이 — 매출과 영업이익", fontproperties=PROP_B, fontsize=12)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    return save_fig(fig, "06_quarterly.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["~4Q전", "~3Q전", "~2Q전", "최근(Q1'26)"]
    actual = [2.52, 3.18, 3.48, 3.91]
    est = [1.21, 1.59, 1.75, 2.78]
    surprise = [109, 101, 99, 41]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], est, w, label="예상 EPS", color=C["sand"])
    ax.bar([i + w / 2 for i in x], actual, w, label="실제 EPS", color=C["navy"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("EPS (USD)", fontproperties=PROP)
    ax.set_title("실적 서프라이즈 — 연속 대형 Beat", fontproperties=PROP_B, fontsize=12)
    for i, s in enumerate(surprise):
        ax.text(i + w / 2, actual[i] + 0.12, f"+{s}%", ha="center", fontsize=8, fontproperties=PROP, color=C["green"])
    ax.legend(prop=PROP, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "07_eps_surprise.png")


def chart_business_flow() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.2, 0.7, 1.8, 1.5, "소비자\n연체·상각", C["sand"]),
        (2.2, 0.7, 1.8, 1.5, "은행이\nNPL 매각", C["gold"]),
        (4.2, 0.7, 1.9, 1.5, "ECPG\n싸게 매입", C["navy2"]),
        (6.3, 0.7, 1.8, 1.5, "수년 걸쳐\n회수", C["teal"]),
        (8.3, 0.7, 1.5, 1.5, "매출\n·이익", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9, color=tc)
        if x < 8:
            ax.annotate("", xy=(x + w + 0.12, y + h / 2), xytext=(x + w + 0.02, y + h / 2),
                        arrowprops=dict(arrowstyle="->", color=C["muted"]))
    ax.set_title("비즈니스 한눈에 — 연체 빚을 사서 회수하는 회사", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "08_business_flow.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 2.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.4, 0.55, 2.4, 1.7, "코어 1순위\nECPG\n보유·유지", C["navy"]),
        (3.1, 0.55, 2.2, 1.7, "코어\nASTH", C["teal"]),
        (5.6, 0.55, 2.0, 1.7, "INDV/BTSG\n추가금지", C["gold"]),
        (7.9, 0.55, 1.8, 1.7, "현금\n버퍼", C["sand"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=tc)
    ax.set_title("포지션 맥락 — Chase RR 최상 · 코어 홀드", fontproperties=PROP_B, fontsize=12, pad=6)
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
        content: "수익구조분석(ECPG) · {ASOF} · " counter(page) " / " counter(pages);
        font-family: NanumGothic; font-size: 8.5pt; color: #78716c;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: NanumGothic, sans-serif; color: #1c1917; font-size: 10pt; line-height: 1.55; }}
    h1 {{ font-size: 20pt; font-weight: 700; margin: 0 0 4px; color: #1e3a5f; }}
    h2 {{ font-size: 13.5pt; font-weight: 700; margin: 22px 0 8px; padding-bottom: 4px;
         border-bottom: 2px solid #1e3a5f; color: #1e3a5f; page-break-after: avoid; }}
    h3 {{ font-size: 11pt; font-weight: 700; margin: 12px 0 6px; color: #0d5c4d; }}
    .hero {{
      background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 55%, #b8860b 130%);
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
    tr:nth-child(even) td {{ background: #f7f3eb; }}
    .viz {{ margin: 8px 0 12px; text-align: center; }}
    .viz img {{ max-width: 100%; height: auto; }}
    .viz figcaption {{ font-size: 8.5pt; color: #57534e; margin-top: 4px; }}
    .callout {{ background: #f7f3eb; border-left: 4px solid #b8860b; padding: 8px 12px; margin: 8px 0 12px; font-size: 9.5pt; }}
    .gloss {{ background: #fafaf9; border: 1px solid #e7e5e4; padding: 8px 12px; margin: 6px 0 14px; font-size: 8.5pt; color: #44403c; }}
    .gloss-title {{ font-weight: 700; color: #1e3a5f; margin-bottom: 4px; font-size: 9pt; }}
    .gloss ul {{ margin: 0 0 0 14px; }}
    .gloss .term {{ font-weight: 700; color: #0d5c4d; }}
    .plain {{ background: #eff6ff; border: 1px solid #bfdbfe; padding: 8px 12px; margin: 6px 0 10px; font-size: 9.5pt; }}
    .plain strong {{ color: #1e3a5f; }}
    .warn {{ background: #fff1f2; border-left: 4px solid #9f1239; padding: 8px 12px; margin: 8px 0; font-size: 9.5pt; }}
    .footer-note {{ font-size: 8pt; color: #78716c; margin-top: 18px; border-top: 1px solid #e7e5e4; padding-top: 8px; }}
    """

    c_flow = fig_block(charts["flow"], "그림 0. 비즈니스 흐름 — 연체 빚 → 매입 → 회수 → 이익")
    c1 = fig_block(charts["mix"], "그림 1. 매출·회수 구성 — 한눈에 보는 돈의 출처")
    c2 = fig_block(charts["ops"], "그림 2. 매입·회수·연간 매출")
    c3 = fig_block(charts["funnel"], "그림 3. TAM→SAM→SOM 깔때기")
    c4 = fig_block(charts["sens"], "그림 4. 민감도 사슬")
    c5 = fig_block(charts["scen"], "그림 5. Bear/Base/Bull")
    c6 = fig_block(charts["qtr"], "그림 6. 최근 5분기 매출·영업이익")
    c7 = fig_block(charts["eps"], "그림 7. EPS 서프라이즈 (4분기)")
    c8 = fig_block(charts["pos"], "그림 8. 포트폴리오에서의 ECPG")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"/><title>수익구조분석 — ECPG (Encore Capital)</title>
<style>{css}</style></head>
<body>

<div class="hero">
  <h1>수익구조분석 · ECPG</h1>
  <div>Encore Capital Group, Inc. · 나스닥 · 부실채권(NPL) 매입·회수 전문 금융</div>
  <div class="oneline">
    <strong>한 줄 구조:</strong> 은행·카드사가 포기한 연체 빚을 <em>싸게 사서</em>,
    수년에 걸쳐 소비자에게 회수합니다. 매출의 대부분은 “포트폴리오 수익”(매입한 채권에서 나오는 회계상 수익)이고,
    실제 현금은 <em>회수(Collections)</em>로 들어옵니다. 미국(MCM)이 엔진, 유럽(Cabot)이 보조입니다.
  </div>
  <div class="kpi">
    <span>종가 $91.33</span>
    <span>시총 ~$2.0B</span>
    <span>PT $105 / $113 / $120</span>
    <span>Q1'26 매출 $475M (+21%)</span>
    <span>회수 $718M (+19%)</span>
    <span>ERC $9.83B</span>
    <span>FY26 가이던스 회수~$2.8B · EPS~$13</span>
    <span>실적 ~08-05</span>
    <span>기준일 {ASOF}</span>
  </div>
</div>

<div class="plain">
  <strong>이 보고서를 읽는 법 (비전공자용):</strong>
  아래는 “이 회사가 무엇을 파는지 → 시장 크기 → 무엇이 흔들리는지 → 좋은/나쁜 숫자 →
  경쟁 → 미리 볼 신호 → 얼마나 들고 있을지” 순서입니다.
  각 블록 끝에 <em>용어 주석</em>이 있고, 이미 설명한 말은 다시 쓰지 않습니다.
</div>

{c_flow}

<div class="block">
<h2>1. 수익 구조 — 매출·회수·지역</h2>
<div class="plain">
  <strong>쉽게:</strong> 중고차를 “헐값에 사서 고쳐 팔아 돈 버는” 가게와 비슷합니다.
  다만 파는 물건이 차가 아니라 <em>남의 연체 빚</em>이고, 고치는 대신 <em>전화·우편·디지털·법적 절차로 돈을 받아내는</em> 일입니다.
  장부상의 “매출”과 통장에 들어오는 “회수 현금”이 같은 숫자가 아니라는 점이 초보자가 가장 헷갈리는 부분입니다.
</div>
{c1}
{c2}

<h3>1-1. Q1'26 매출 분해 (회사 공시)</h3>
<table>
  <tr><th>항목</th><th>금액</th><th>설명(쉬운 말)</th></tr>
  <tr><td>포트폴리오 수익</td><td>$390M</td><td>매입 채권에서 나오는 기본 회계 수익 (전체의 ~82%)</td></tr>
  <tr><td>회수 추정 변동 (Changes in recoveries)</td><td>$63M</td><td>“앞으로 이만큼 더/덜 받을 것 같다” 추정을 바꾼 효과</td></tr>
  <tr><td>부채 매입 관련 매출 합</td><td>$453M</td><td>위 둘을 합친 핵심 사업 (~95%)</td></tr>
  <tr><td>서비싱 수익</td><td>$21M</td><td>남의 채권을 대신 받아주는 수수료성 수입</td></tr>
  <tr><td>기타</td><td>$2M</td><td>소량</td></tr>
  <tr><td><strong>총 매출</strong></td><td><strong>$475M</strong></td><td>전년 $393M 대비 +21%</td></tr>
</table>

<h3>1-2. 같은 분기, “현금 회수”와 “매입” 숫자</h3>
<table>
  <tr><th>지표</th><th>Q1'26</th><th>Q1'25</th><th>변화</th><th>의미</th></tr>
  <tr><td>글로벌 회수 (Collections)</td><td>$718M</td><td>$605M</td><td>+19%</td><td>실제로 거둬들인 현금(대략)</td></tr>
  <tr><td> ㄴ 미국 회수</td><td>$556M</td><td>—</td><td>—</td><td>회수의 ~77%, 성장 엔진</td></tr>
  <tr><td> ㄴ 유럽(Cabot) 회수</td><td>~$161M</td><td>—</td><td>—</td><td>보조 축</td></tr>
  <tr><td>글로벌 포트폴리오 매입</td><td>$363M</td><td>$368M</td><td>−1%</td><td>이번 분기 새로 산 빚 규모</td></tr>
  <tr><td> ㄴ 미국 매입</td><td>$316M</td><td>—</td><td>—</td><td>매입의 대부분</td></tr>
  <tr><td>ERC (잔여 회수 추정)</td><td>$9.83B</td><td>$8.86B</td><td>+11%</td><td>앞으로 받을 수 있다고 보는 “저수지”</td></tr>
  <tr><td>EPS</td><td>$3.86</td><td>$1.93</td><td>+100%</td><td>주당 이익 급증</td></tr>
</table>

<p>
핵심 공식(개념): <strong>좋은 매입가 × 충분한 회수율 × 큰 ERC</strong> → 매출·이익.
Q1에 매입은 거의 비슷했는데 회수·매출·EPS가 크게 오른 것은,
이미 사 둔 포트폴리오에서 회수가 잘 나오고(운영 효율), 회수 전망(ERC)도 상향된 영향이 큽니다.
</p>

{c6}

<h3>1-3. 연간 재무 (보고)</h3>
<table>
  <tr><th>연도</th><th>매출</th><th>영업이익</th><th>순이익</th><th>이자비용</th></tr>
  <tr><td>FY2022</td><td>$1,398M</td><td>$466M</td><td>$195M</td><td>$153M</td></tr>
  <tr><td>FY2023</td><td>$1,223M</td><td>$273M</td><td>−$206M</td><td>$202M</td></tr>
  <tr><td>FY2024</td><td>$1,316M</td><td>$276M</td><td>−$139M</td><td>$238M</td></tr>
  <tr><td>FY2025</td><td>$1,769M</td><td>$627M</td><td>$257M</td><td>$280M</td></tr>
</table>

<div class="callout">
  <strong>FY26 가이던스(Q1 후 상향):</strong> 글로벌 회수 약 <strong>$2.8B</strong>(+8% YoY) ·
  EPS 약 <strong>$13.00</strong>(+19%) · 포트폴리오 매입 <strong>$1.4–1.5B</strong>.
  FY25 실제: 회수 $2.59B, 매입 $1.41B(미국 $1.17B).
</div>

<p>
부채가 큰 업종입니다(총부채 ~$4.0B, 시총 ~$2.0B). “남의 돈을 빌려 채권을 사고, 회수로 갚으며 스프레드를 남기는”
구조라 <strong>이자비용·조달금리</strong>가 마진을 깎습니다. FY23–24 순손실 구간은 회계·포트폴리오 평가·비용 요인이 겹친 시기로,
FY25부터 이익이 뚜렷히 회복된 상태입니다.
</p>

{gloss([
    ("NPL (Non-Performing Loan)", "이자를 제때 못 갚아 ‘부실’로 분류된 대출·카드채권. 은행이 장부에서 정리하려고 싸게 팔기도 함."),
    ("포트폴리오 매입", "수천~수만 건의 연체 계정을 묶음(포트폴리오)으로 할인 매수하는 것."),
    ("Collections (회수)", "매입한 계정에서 실제로 받아낸 금액. 투자자가 현금 창출력로 가장 먼저 보는 숫자."),
    ("ERC (Estimated Remaining Collections)", "이미 산 포트폴리오에서 앞으로 회수될 것으로 추정하는 총액. ‘남은 저수지’."),
    ("포트폴리오 수익", "매입 원가와 예상 회수를 바탕으로 회계 기준에 따라 인식하는 수익. 당기 회수 현금과 1:1이 아님."),
    ("Changes in recoveries", "앞으로의 회수 전망을 올려/내려 잡을 때 당기 손익에 반영되는 조정."),
    ("서비싱(Servicing)", "남의 채권을 대신 관리·회수하고 수수료를 받는 사업."),
    ("MCM / Cabot", "Encore의 미국 브랜드(Midland Credit Management) / 유럽 사업 축."),
])}
</div>

<div class="block">
<h2>2. 시장 깔때기 — TAM → SAM → SOM</h2>
<div class="plain">
  <strong>쉽게:</strong> 피자 비유 — <em>TAM</em>은 “연체가 생기는 전체 신용 시장”,
  <em>SAM</em>은 “은행이 실제로 내다 파는 부실채권”,
  <em>SOM</em>은 “ECPG가 올해 사들이는 양 + 이미 산 것에서 거둬들이는 회수”입니다.
</div>
{c3}

<table>
  <tr><th>단계</th><th>대략 규모</th><th>정의</th><th>헷갈리기 쉬운 점</th></tr>
  <tr>
    <td>TAM</td>
    <td>연 ~$50B+ (대략)</td>
    <td>소비자 신용 잔액 × 상각·연체에서 나오는 부실 흐름</td>
    <td>TAM ≠ ECPG 매출. 대부분이 은행 내부에 남거나 다른 경로로 처리됨</td>
  </tr>
  <tr>
    <td>SAM</td>
    <td>수~십수 B USD</td>
    <td>제3자(ECPG 같은 회사)에게 매각되는 NPL 시장</td>
    <td>금리·규제·은행 자본 상황에 따라 매각 물량이 출렁임</td>
  </tr>
  <tr>
    <td>SOM — 매입</td>
    <td>$1.4–1.5B (FY26 가이던스)</td>
    <td>ECPG가 올해 살 포트폴리오 예산</td>
    <td>매입액은 ‘투자’, 매출은 ‘그 투자에서 나오는 수익’</td>
  </tr>
  <tr>
    <td>SOM — 회수 엔진</td>
    <td>ERC ~$9.8B · FY26 회수 ~$2.8B</td>
    <td>이미 보유한 저수지에서 매년 빼 가는 현금</td>
    <td>시총($2B)과 ERC($9.8B)를 직접 비교하면 안 됨(할인·비용·시간 미반영)</td>
  </tr>
</table>

<p>
미국은 최근 카드·리볼빙 잔액이 높은 구간에서 상각률도 함께 오르면 <strong>매각 물량(공급)</strong>이 늘고,
매입 경쟁이 과하지 않으면 <strong>매입 수익률(IRP)</strong>이 좋아집니다.
Q1 경영진 코멘트도 “미국 매입 환경이 유리하다”는 톤이었습니다.
유럽(Cabot)은 경쟁이 더 치열해 매입 규모가 상대적으로 작습니다.
</p>

{gloss([
    ("TAM / SAM / SOM", "전체 시장 / 우리가 팔 수 있는 시장 / 실제로 가져가는(가져갈) 규모."),
    ("상각(Charge-off)", "은행이 ‘받기 어렵다’고 보고 대출을 손실 처리하는 것. NPL 매각의 재료가 됨."),
    ("리볼빙(Revolving credit)", "신용카드처럼 한도 안에서 쓰고 갚기를 반복하는 신용."),
    ("IRP (Internal Rate of Return on Purchases 등)", "매입 건의 기대 수익률. 싸게 살수록(같은 회수 가정) IRP↑."),
])}
</div>

<div class="block">
<h2>3. 민감도 사슬 — 무엇이 이익을 흔드나</h2>
<div class="plain">
  <strong>쉽게:</strong> 컨베이어 벨트입니다. 앞 단계(연체 공급·매입가)가 나빠지면
  뒤의 ERC·매출·EPS까지 천천히, 하지만 크게 흔들릴 수 있습니다.
</div>
{c4}

<table>
  <tr><th>단계</th><th>좋게 나오면</th><th>나쁘게 나오면</th></tr>
  <tr><td>① 연체·상각 공급</td><td>살 물건(포트폴리오)이 충분</td><td>매각 물량 가뭄 → 성장 정체</td></tr>
  <tr><td>② 매입가·IRP</td><td>같은 회수에 원가↓ → 마진↑</td><td>경쟁 입찰로 비싸게 삼 → 장기 수익↓</td></tr>
  <tr><td>③ 회수율·속도</td><td>Collections·효율↑</td><td>실업·규제·소비자 상환 능력↓</td></tr>
  <tr><td>④ ERC 재추정</td><td>Changes in recoveries 플러스</td><td>저수지 하향 = 당기 손익 충격</td></tr>
  <tr><td>⑤ 매출 인식</td><td>포트폴리오 수익 안정</td><td>회계 변동성 확대</td></tr>
  <tr><td>⑥ 회수비용·이자</td><td>단위당 비용↓, 금리 안정</td><td>소송비·인건비·조달금리↑</td></tr>
  <tr><td>⑦ 순이익·EPS</td><td>가이던스 상향 여지</td><td>멀티플·신용 스프레드 악화</td></tr>
</table>

<p>
ECPG는 <strong>⑥ 이자</strong> 비중이 커서(FY25 이자 ~$280M), 금리 환경이 조달 비용에 직접 영향을 줍니다.
또한 규제가 회수 채널(전화·소송)을 조이면 ③⑥이 동시에 나빠질 수 있습니다.
</p>

{gloss([
    ("회수율(Liquidation rate)", "매입 원가 대비 실제로 얼마나 거둬들이는지. 높을수록 좋음."),
    ("조달금리", "채권 매입 자금을 빌릴 때 내는 이자율."),
    ("멀티플", "주가 ÷ 이익(또는 장부가치 등). 시장이 회사에 매기는 ‘배수’."),
])}
</div>

<div class="block">
<h2>4. Bear / Base / Bull — 숫자 시나리오</h2>
<div class="plain">
  <strong>쉽게:</strong> 가이던스를 중심으로 나쁜 날·평범한 날·좋은 날을 적어 둔 작업용 표입니다. 약속이 아닙니다.
</div>
{c5}

<table>
  <tr><th>시나리오</th><th>가정</th><th>연간 회수</th><th>EPS(개념)</th><th>주가 함의(개념)</th></tr>
  <tr>
    <td>Bear</td>
    <td>회수 둔화, ERC 하향, 매입 경쟁 심화, 금리·규제 비용↑</td>
    <td>~$2.4B</td>
    <td>~$9.5</td>
    <td>$70–82 (가이던스 이탈 충격)</td>
  </tr>
  <tr>
    <td>Base</td>
    <td>FY26 가이던스 달성(회수~$2.8B, EPS~$13), 미국 매입 환경 유지</td>
    <td>~$2.8B</td>
    <td>~$13.0</td>
    <td>$105–115 (PT 밴드과 정합)</td>
  </tr>
  <tr>
    <td>Bull</td>
    <td>회수·ERC 추가 상향, 매입 IRP 유지, 자사주·레버리지 개선</td>
    <td>~$3.1B+</td>
    <td>~$15.5</td>
    <td>$118–130 (PT 고점 상회 시도)</td>
  </tr>
</table>

<p>
현재가 <strong>$91.33</strong> vs PT 평균 <strong>~$113</strong> → 약 <strong>+24%</strong> 업사이드.
52주 고점 $94.60 근처지만, 절대 밸류(시총~$2B) 대비 ERC·이익 회복 스토리가 남아
Chase RR에서 <strong>최상위·코어</strong>로 분류된 종목입니다.
</p>

{c7}
<p>
최근 4분기 EPS 서프라이즈가 <strong>+41% ~ +109%</strong>로 매우 큽니다.
컨센서스가 보수적이거나, 회수·회계 모멘텀이 애널리스트 모델보다 빠른 상태로 해석할 수 있습니다.
실적일(~08-05)에는 Beat 여부보다 <strong>회수·매입·ERC·FY 가이던스 톤</strong>이 더 중요합니다.
</p>

{gloss([
    ("Bear / Base / Bull", "비관·기본·낙관 시나리오."),
    ("컨센서스", "애널리스트 추정치 평균."),
    ("Beat", "실제 실적 &gt; 컨센서스."),
    ("업사이드", "현재가 대비 목표가 상승 여력."),
    ("자사주 매입", "Q1에 $20M 규모 매입 공시. 주식 수 감소 → EPS에 도움 가능."),
])}
</div>

<div class="block">
<h2>5. 경쟁·점유</h2>
<div class="plain">
  <strong>쉽게:</strong> 같은 “연체 빚 경매장”에 여러 회사가 입찰합니다.
  너무 비싸게 사면 나중에 회수를 잘해도 남는 게 없습니다.
</div>
<table>
  <tr><th>전선</th><th>ECPG</th><th>경쟁·압력</th><th>관찰</th></tr>
  <tr>
    <td>미국 NPL 매입</td>
    <td>MCM, 규모·데이터·컴플라이언스 강점</td>
    <td>다른 채무매입사, 사모 자금</td>
    <td>매입 단가·IRP, 분기 매입액</td>
  </tr>
  <tr>
    <td>유럽</td>
    <td>Cabot</td>
    <td>현지 플레이어, 경쟁 입찰</td>
    <td>매입 규모가 미국보다 작음</td>
  </tr>
  <tr>
    <td>회수 채널</td>
    <td>콜센터·디지털·법적 회수</td>
    <td>규제(연락 제한 등), 소비자 보호</td>
    <td>단위당 회수비용, 소송비</td>
  </tr>
</table>
<p>
규모의 경제(데이터·컴플라이언스·자금)가 진입장벽입니다.
규제 강화는 작은 업체에 더 불리할 수 있어, 오히려 대형에 유리한 면도 있습니다(양날의 검).
</p>
{gloss([
    ("컴플라이언스", "법·규제·내부 절차를 지키는 체계. 회수 업종에서는 생존 조건에 가깝다."),
    ("진입장벽", "새 경쟁자가 들어오기 어렵게 만드는 조건(자본·인허가·데이터 등)."),
])}
</div>

<div class="block">
<h2>6. 선행 지표</h2>
<ul>
  <li><strong>분기 Collections</strong> — 가이던스($2.8B) 페이스와의 거리</li>
  <li><strong>포트폴리오 매입액·지역 믹스</strong> — 미국 비중, 단가 코멘트</li>
  <li><strong>ERC 증감</strong> — 저수지가 커지는지(매입+재추정−회수)</li>
  <li><strong>Changes in recoveries</strong> — 일회성 플러스가 과도하면 지속성 점검</li>
  <li><strong>이자비용·순부채</strong> — 조달 스트레스</li>
  <li><strong>규제·소송 헤드라인</strong></li>
  <li><strong>차기 실적 ~08-05</strong> — 가이던스 유지/상향 여부</li>
</ul>
{gloss([
    ("선행 지표", "실적 발표 전에 방향성을 가늠하는 신호."),
    ("순부채", "총부채 − 현금. 레버리지 부담의 간단한 척도."),
])}
</div>

<div class="block">
<h2>7. 비중 상한 · Thesis Breakers</h2>
{c8}
<div class="plain">
  <strong>쉽게:</strong> 소액 집중 포트(3–4종목)에서 ECPG는 <strong>코어 1순위</strong>로 이미 편입되어 있습니다.
  추격 매수보다는 홀드, 큰 조정 시에만 비중을 점검하는 편이 맞습니다.
</div>
<table>
  <tr><th>항목</th><th>권고</th><th>이유</th></tr>
  <tr><td>현재</td><td>코어 Hold (예: 2주)</td><td>서프라이즈·PT 정합·수익구조 가시성</td></tr>
  <tr><td>고점 추격 애드</td><td>신중 / 소량만</td><td>$91–95 구간은 이미 반영된 측면, 08-05 이벤트</td></tr>
  <tr><td>비중 상한</td><td>총자산 ~25–35% (코어 한도 내)</td><td>최선호라도 단일 종목 올인 금지</td></tr>
  <tr><td>손절·논리 폐기</td><td>아래 Breaker 발생 시</td><td>감정이 아니라 규칙으로</td></tr>
</table>

<div class="warn">
  <strong>Thesis Breakers:</strong>
  <ul>
    <li>분기 회수가 가이던스 페이스를 크게 하회하고 ERC가 연속 하향</li>
    <li>미국 매입 IRP가 구조적으로 악화(비싸게 사기 고착)</li>
    <li>대형 규제 제재·소송으로 회수 채널·비용 구조 훼손</li>
    <li>조달금리·신용 스프레드 급등으로 이자부담이 이익을 잠식</li>
    <li>연속 Beat가 끊기고 FY EPS 가이던스 하향</li>
  </ul>
</div>

{gloss([
    ("코어", "포트폴리오에서 가장 오래·가장 크게 가져가는 중심 보유 종목."),
    ("애드", "기존 보유를 더 사는 것."),
    ("Thesis Breaker", "이 주식을 들고 있는 핵심 논리를 무효로 만드는 사건."),
])}
</div>

<div class="block">
<h2>8. 한계 · 출처</h2>
<ul>
  <li>시가·PT·일부 재무는 Yahoo Finance 집계(지연·수정 가능).</li>
  <li>회수·매입·ERC·매출 분해·가이던스는 Encore IR / 실적 자료(Q1'26, FY25) 기준.</li>
  <li>TAM은 산업 구조 기반 <strong>근사</strong>이며 확정 통계가 아님.</li>
  <li>시나리오 EPS·주가 함의는 교육·의사결정 보조용.</li>
  <li>본 PDF는 정보 제공 목적이며 매수·매도 권고가 아닙니다.</li>
</ul>
<div class="footer-note">
  생성: 수익구조분석() · 티커 ECPG · 기준 {ASOF} · WeasyPrint + NanumGothic
</div>
</div>

</body></html>
"""
    return html


def main() -> None:
    charts = {
        "flow": chart_business_flow(),
        "mix": chart_rev_mix(),
        "ops": chart_collections_purchases(),
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
