#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(SLS) — 임상단계·파이프라인 가치 + 초보용 설명 + WeasyPrint PDF."""

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
ASOF = "2026-07-23"
OUT_PDF = [
    Path("/opt/cursor/artifacts/SLS_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/SLS_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/SLS_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/SLS_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/sls")
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
        (0.1, 0.7, 1.8, 1.6, "WT1 항원\n암세포", C["sand"]),
        (2.1, 0.7, 1.85, 1.6, "GPS\n펩타이드\n면역치료", C["gold"]),
        (4.15, 0.7, 1.75, 1.6, "REGAL\nPh3 AML\n바이너리", C["teal2"]),
        (6.1, 0.7, 1.75, 1.6, "승인·출시\n또는 실패", C["teal"]),
        (8.05, 0.7, 1.7, 1.6, "미래 매출\n(현재 $0)", C["navy"]),
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
    ax.set_title("비즈니스 한눈에 — 지금 파는 제품 없음, Ph3 결과에 회사 가치가 달림", fontproperties=PROP_B, fontsize=11.5, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_pipeline_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    # Conceptual value weight of pipeline (not revenue)
    sizes = [70, 25, 5]
    labels = ["GPS\n(Ph3 REGAL)\n~70%", "SLS009\n(CDK9 Ph2)\n~25%", "파트너십\n·기타 ~5%"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["navy"], C["teal"], C["gold"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("파이프라인 가치 비중 (개념)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["GPS\nREGAL", "SLS009\n1L AML", "Merck\n콤보"]
    stage = [95, 55, 35]  # catalyst nearness score
    bars = ax.bar(cats, stage, color=[C["navy"], C["teal"], C["gold"]], width=0.55)
    ax.set_ylabel("촉매 임박도 (개념 0-100)", fontproperties=PROP)
    ax.set_title("촉매 임박도", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, stage):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, str(v), ha="center", fontproperties=PROP_B, fontsize=9)
    ax.set_ylim(0, 110)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("SLS — 매출 $0, 가치는 임상 자산에서", fontproperties=PROP_B, fontsize=13, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "02_pipeline_mix.png")


def chart_burn() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    years = ["FY22", "FY23", "FY24", "FY25"]
    rnd = [20.3, 24.0, 19.1, 16.0]
    sga = [12.6, 13.9, 12.4, 12.3]
    ni = [-41.3, -37.3, -30.9, -26.9]
    x = range(len(years))
    ax.bar([i - 0.2 for i in x], rnd, 0.35, label="R&D", color=C["navy"])
    ax.bar([i + 0.2 for i in x], sga, 0.35, label="SG&A", color=C["teal2"])
    ax.plot(list(x), [-v for v in ni], "o--", color=C["red"], label="순손실(절댓값)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(years, fontproperties=PROP)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("연간 비용·손실", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rnd_q = [3.2, 3.9, 4.2, 4.7, 5.1]
    ni_q = [5.8, 6.6, 6.8, 7.7, 8.4]
    x = range(len(labels))
    ax.bar(x, rnd_q, color=C["navy"], alpha=0.85, label="R&D", width=0.45)
    ax.plot(x, ni_q, "o-", color=C["gold"], lw=2, ms=7, label="순손실")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("분기 소진 (매출 $0)", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "03_burn.png")


def chart_cash_runway() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    cash = [25.3, None, 44.3, 71.8, 107.1]  # sparse from quarterly; fill known
    # Use known: Q1'25~25.3 from earlier cols order was reverse - quarterly cols: 2026-03, 2025-12, 2025-09, 2025-06, 2025-03
    # Cash: 107.1, 71.8, 44.3, 25.3 (and one mid) — map:
    cash = [25.3, 25.3, 44.3, 71.8, 107.1]  # Q2 approx hold for chart simplicity - actually Q2 2025 was in data as 25.3 at index3 for Mar25... 
    # From quarterly: Mar26=107.1, Dec25=71.8, Sep25=44.3, Jun25=25.3, Mar25=? wait columns were 5:
    # [107.1, 71.8, 44.3, 25.3] only 4 shown for cash in Q - there were 4 values in one print... 
    # Actually: Cash [107.1, 71.8, 44.3, 25.3] for Mar26, Dec25, Sep25, Jun25 - missing Mar25
    cash = [22.0, 25.3, 44.3, 71.8, 107.1]  # Mar25 estimate placeholder - better use only known 4 + note
    cash = [25.3, 44.3, 71.8, 107.1]
    labels = ["Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    ax.plot(labels, cash, "o-", color=C["teal"], lw=2.4, ms=9)
    ax.fill_between(range(len(labels)), cash, alpha=0.15, color=C["teal"])
    ax.axhline(107.1 + 7.5, color=C["gold"], ls="--", lw=1.2, label="Q1 + 워런트 $7.5M (~$114.6M)")
    for i, v in enumerate(cash):
        ax.text(i, v + 4, f"{v:.0f}", ha="center", fontproperties=PROP_B, fontsize=9)
    ax.set_ylabel("현금 (백만 USD)", fontproperties=PROP)
    ax.set_title("현금 잔고 — 증자로 런웨이 연장 (희석 대가)", fontproperties=PROP_B, fontsize=12)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.set_ylim(0, 140)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "04_cash.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    rows = [
        (0.5, 3.6, 9.0, 1.0, "TAM — AML·WT1+ 혈액암·고형암 (넓음)", C["sand"]),
        (1.2, 2.4, 7.6, 1.0, "SAM — 2차 관해 AML 유지요법 (REGAL 적응증)", C["gold"]),
        (2.0, 1.2, 6.0, 1.0, "SOM — 승인 시에만 발생 (현재 매출 $0)", C["teal"]),
    ]
    for x, y, w, h, t, c in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9.5, color=tc)
    ax.set_title("시장 깔때기 — 승인 전엔 SOM=0", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "05_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    boxes = [
        (0.15, 0.7, 1.5, 1.6, "① REGAL\n80th event", C["sand"]),
        (1.85, 0.7, 1.5, 1.6, "② OS\n통계 유의", C["gold"]),
        (3.55, 0.7, 1.5, 1.6, "③ BLA/\n승인", C["teal2"]),
        (5.25, 0.7, 1.5, 1.6, "④ 가격·\n보험급여", C["teal"]),
        (6.95, 0.7, 1.4, 1.6, "⑤ 매출\n런레이트", C["navy"]),
        (8.5, 0.7, 1.3, 1.6, "⑥ 희석·\n런웨이", C["slate"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8, color=tc)
    ax.set_title("민감도 사슬 — 매출보다 바이너리 임상·자금이 주가를 흔듦", fontproperties=PROP_B, fontsize=11.5, pad=6)
    return save_fig(fig, "06_sensitivity.png")


def chart_scenarios() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    labels = ["Bear\n실패", "Base\n혼조", "Bull\n성공"]
    # Implied equity value scenarios (USD bn) - conceptual
    mcap = [0.4, 2.4, 5.5]
    px = [2, 12, 28]
    colors = [C["red"], C["teal"], C["gold"]]

    ax = axes[0]
    bars = ax.bar(labels, mcap, color=colors, width=0.55)
    ax.set_title("시나리오 시총 (십억 USD, 개념)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, mcap):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    bars = ax.bar(labels, px, color=colors, width=0.55)
    ax.set_title("시나리오 주가 (USD, 개념)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, px):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"${v}", ha="center", fontproperties=PROP, fontsize=9)
    ax.axhline(12.08, color=C["muted"], ls=":", lw=1.2)
    ax.text(2.2, 12.8, "현재~$12", fontproperties=PROP, fontsize=8, color=C["muted"])
    ax.set_ylim(0, 35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.suptitle("Bear / Base / Bull — REGAL 결과에 극단적으로 의존", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "07_scenarios.png")


def chart_eps_beat() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["~4Q전", "~3Q전", "~2Q전", "최근"]
    # losses smaller than expected = "beat"
    actual = [-0.07, -0.07, -0.06, -0.05]
    est = [-0.11, -0.08, -0.08, -0.06]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], [abs(v) for v in est], w, label="예상 |EPS|", color=C["sand"])
    ax.bar([i + w / 2 for i in x], [abs(v) for v in actual], w, label="실제 |EPS|", color=C["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("|EPS| (손실 크기)", fontproperties=PROP)
    ax.set_title("손실 축소 Beat — 실적은 연속 Beat이나 본질은 임상", fontproperties=PROP_B, fontsize=12)
    ax.legend(prop=PROP, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "08_eps_beat.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 2.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.3, 0.55, 2.2, 1.7, "코어\nNEO/ECPG", C["navy"]),
        (2.7, 0.55, 2.2, 1.7, "AMRX·MU\n이벤트/좌석", C["teal"]),
        (5.1, 0.55, 2.3, 1.7, "SLS\n워치·위성\n바이너리", C["gold"]),
        (7.6, 0.55, 2.0, 1.7, "현금\n버퍼", C["sand"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=tc)
    ax.set_title("포지션 맥락 — Chase 1위라도 코어 금지 · 위성만", fontproperties=PROP_B, fontsize=12, pad=6)
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
        content: "수익구조분석(SLS) · {ASOF} · " counter(page) " / " counter(pages);
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

    c0 = fig_block(charts["flow"], "그림 0. 비즈니스 흐름 — 임상 → 바이너리 → (가능하면) 매출")
    c1 = fig_block(charts["mix"], "그림 1. 파이프라인 가치 비중·촉매")
    c2 = fig_block(charts["burn"], "그림 2. 연간·분기 비용 소진")
    c3 = fig_block(charts["cash"], "그림 3. 현금 잔고")
    c4 = fig_block(charts["funnel"], "그림 4. TAM→SAM→SOM")
    c5 = fig_block(charts["sens"], "그림 5. 민감도 사슬")
    c6 = fig_block(charts["scen"], "그림 6. Bear/Base/Bull")
    c7 = fig_block(charts["eps"], "그림 7. 손실 Beat")
    c8 = fig_block(charts["pos"], "그림 8. 포트폴리오에서의 SLS")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"/><title>수익구조분석 — SLS (SELLAS)</title>
<style>{css}</style></head>
<body>

<div class="hero">
  <h1>수익구조분석 · SLS</h1>
  <div>SELLAS Life Sciences Group, Inc. · 나스닥 · 후기 임상 항암 바이오</div>
  <div class="oneline">
    <strong>한 줄 구조:</strong> <em>상업 매출은 $0</em>입니다.
    회사 가치의 대부분(~70%)은 AML Ph3 <strong>GPS (REGAL)</strong> 바이너리에 달려 있고,
    보조축은 CDK9 억제제 <strong>SLS009</strong>, 나머지는 Merck 콤보·라이선스 옵션입니다.
    “수익 구조” = <strong>파이프라인 옵션 가치 + 현금 소진 구조</strong>로 읽어야 합니다.
  </div>
  <div class="kpi">
    <span>종가 ~$12.08</span>
    <span>시총 ~$2.4B</span>
    <span>PT $25 / $27.5 / $30</span>
    <span>상업매출 $0</span>
    <span>현금 Q1'26 $107M (+워런트 $7.5M)</span>
    <span>REGAL 78/80 events</span>
    <span>실적 08-11</span>
    <span>기준일 {ASOF}</span>
  </div>
</div>

<div class="plain">
  <strong>이 보고서를 읽는 법:</strong>
  일반 기업처럼 “제품 믹스 %”가 없습니다.
  <em>무엇을 개발 중인지 → 언제 판가름 나는지 → 돈이 얼마나 타는지 → 성공/실패 시나리오 → 비중</em>
  순서로 읽습니다. Chase 1위라도 <strong>바이너리 위성</strong>입니다.
</div>

{c0}

<div class="block">
<h2>1. “수익” 구조 — 파이프라인 · 비용 · 현금</h2>
<div class="plain">
  <strong>쉽게:</strong> 편의점에 물건이 없는 회사입니다.
  대신 “임상시험 티켓” 두 장이 전 재산이고, 매월 연구비·인건비를 태웁니다.
</div>
{c1}

<h3>1-1. 파이프라인 맵</h3>
<table>
  <tr><th>자산</th><th>단계</th><th>적응증</th><th>의미</th></tr>
  <tr>
    <td><strong>GPS (galinpepimut-S)</strong></td>
    <td>Ph3 REGAL</td>
    <td>AML 2차 관해 유지</td>
    <td>WT1 펩타이드 면역치료. <strong>80번째 사망 이벤트</strong>에서 최종 분석·공개. 5/11 기준 78/80</td>
  </tr>
  <tr>
    <td><strong>SLS009 (tambiciclib)</strong></td>
    <td>Ph2</td>
    <td>신규진단 1L AML (80명)</td>
    <td>CDK9 억제제. MCL-1↓·고위험 돌연변이. 탑라인 <strong>2026 Q4</strong> 목표</td>
  </tr>
  <tr>
    <td>파트너십</td>
    <td>연구/라이선스</td>
    <td>Merck(키트루다 콤보), GenFleet, MSK</td>
    <td>당장 큰 마일스톤 매출보다 개발 옵션·신뢰 신호</td>
  </tr>
  <tr>
    <td><strong>상업 제품</strong></td>
    <td>—</td>
    <td>—</td>
    <td><strong>순매출 $0</strong> (FY22–25, Q1'26 동일)</td>
  </tr>
</table>

{c2}
{c3}

<h3>1-2. 비용·손실 (백만 USD)</h3>
<table>
  <tr><th>연도</th><th>매출</th><th>R&D</th><th>SG&A</th><th>영업이익</th><th>순이익</th></tr>
  <tr><td>FY2022</td><td>~$1</td><td>$20</td><td>$13</td><td>−$32</td><td>−$41</td></tr>
  <tr><td>FY2023</td><td>$0</td><td>$24</td><td>$14</td><td>−$38</td><td>−$37</td></tr>
  <tr><td>FY2024</td><td>$0</td><td>$19</td><td>$12</td><td>−$32</td><td>−$31</td></tr>
  <tr><td>FY2025</td><td>$0</td><td>$16</td><td>$12</td><td>−$28</td><td>−$27</td></tr>
  <tr><td>Q1'26</td><td>$0</td><td>$5.1</td><td>~$4.1</td><td>−$9.3</td><td>−$8.4</td></tr>
</table>

<p>
Q1'26 R&D↑는 REGAL 최종분석·잠재 BLA 준비(제조·임상·규제) 비용.
현금 Q1 말 <strong>$107.1M</strong> + Q2 워런트 행사 <strong>$7.5M</strong>.
ATM(최대 $150M) 설정했으나 <strong>아직 미사용</strong> — 희석 옵션이 열려 있음.
주식 수: FY말 ~1.53억 → Q1'26 ~1.81억 (지속 희석).
</p>

<div class="callout">
  <strong>핵심:</strong> P/S·매출 성장률로 이 회사를 재면 안 됩니다.
  시총~$2.4B는 “REGAL 성공 확률 × 출시 가치 + SLS009 옵션 − 희석”의 시장 합의에 가깝습니다.
</div>

{gloss([
    ("GPS / WT1", "Wilms tumor 1 항원을 겨냥한 펩타이드 암 백신(면역치료)."),
    ("REGAL", "AML Ph3. 이벤트(사망) 80회 도달 시 최종 생존(OS) 분석."),
    ("SLS009 / CDK9", "세포주기·생존 단백질(MCL-1 등)을 억제하는 저분자."),
    ("BLA", "바이오의약품 허가신청서. 성공 데이터 후 FDA에 제출."),
    ("ATM", "시장가 주식 매도 프로그램. 필요할 때 증자·희석 가능."),
    ("희석", "신주 발행으로 기존 주주 지분율↓."),
])}
</div>

<div class="block">
<h2>2. 시장 깔때기 — TAM → SAM → SOM</h2>
{c4}
<table>
  <tr><th>단계</th><th>내용</th><th>주의</th></tr>
  <tr><td>TAM</td><td>WT1+ 암 전반</td><td>TAM ≠ 당장 매출</td></tr>
  <tr><td>SAM</td><td>REGAL AML 유지요법 환자군</td><td>적응증이 좁을 수 있음</td></tr>
  <tr><td>SOM</td><td>승인·급여 후에만</td><td><strong>지금 SOM=$0</strong></td></tr>
</table>
{gloss([("OS", "Overall Survival. 전체생존기간 — REGAL의 핵심 평가변수.")])}
</div>

<div class="block">
<h2>3. 민감도 사슬</h2>
{c5}
<table>
  <tr><th>단계</th><th>좋게</th><th>나쁘게</th></tr>
  <tr><td>① 80th event</td><td>일정 가시화</td><td>지연·불확실</td></tr>
  <tr><td>② OS 결과</td><td>통계적 유의·임상적 의미</td><td>실패·경계선</td></tr>
  <tr><td>③ 규제</td><td>BLA·승인 경로</td><td>추가시험 요구</td></tr>
  <tr><td>④ 상업화</td><td>가격·침투</td><td>경쟁·급여 난항</td></tr>
  <tr><td>⑤ 자금</td><td>파트너·비희석 자금</td><td>ATM 대량 매도</td></tr>
</table>
<p>EPS “Beat”는 손실이 예상보다 작다는 뜻일 뿐, <strong>매출 서프라이즈가 아닙니다.</strong></p>
{c7}
</div>

<div class="block">
<h2>4. Bear / Base / Bull</h2>
{c6}
<table>
  <tr><th>시나리오</th><th>가정</th><th>주가 함의</th></tr>
  <tr>
    <td>Bear</td>
    <td>REGAL 실패·경계선, 현금 소진·대량 희석</td>
    <td>~$2–5 (시총 급감)</td>
  </tr>
  <tr>
    <td>Base</td>
    <td>혼조/지연, SLS009만 옵션 유지, 현재 확률 반영</td>
    <td>~$8–15 (현주가대)</td>
  </tr>
  <tr>
    <td>Bull</td>
    <td>REGAL 명확 성공 → BLA·파트너 관심</td>
    <td>~$25–30+ (PT대)</td>
  </tr>
</table>
<p>
현재가 <strong>~$12</strong> vs PT 평균 <strong>$27.5</strong>(+128%).
업사이드가 커 보이는 이유는 <strong>바이너리 성공을 PT가 가정</strong>하기 때문.
실패 시 다운사이드는 PT 여유와 비대칭적으로 큼.
</p>
{gloss([("바이너리", "성공/실패로 가치가 갈리는 사건. 중간이 얇음.")])}
</div>

<div class="block">
<h2>5. 경쟁·포지션</h2>
<table>
  <tr><th>전선</th><th>SLS</th><th>압력</th></tr>
  <tr><td>AML 유지</td><td>GPS 면역</td><td>기존 표준치료·다른 면역/세포치료</td></tr>
  <tr><td>1L 고위험 AML</td><td>SLS009 ± AZA/VEN</td><td>Venetoclax 기반 표준, 다른 CDK·MCL-1 접근</td></tr>
  <tr><td>자금</td><td>현금~$114M급</td><td>ATM $150M · 워런트·희석 이력</td></tr>
</table>
</div>

<div class="block">
<h2>6. 선행 지표</h2>
<ul>
  <li><strong>REGAL 80th event 도달 공지</strong> → DB lock → 탑라인</li>
  <li>탑라인 OS HR·p값·안전성 · BLA 톤</li>
  <li>SLS009 Ph2 등록·중간/탑라인 (Q4'26)</li>
  <li>현금·ATM 사용 여부·주식 수</li>
  <li>08-11 실적 — 임상 업데이트 &gt; EPS</li>
</ul>
</div>

<div class="block">
<h2>7. 비중 상한 · Thesis Breakers</h2>
{c8}
<div class="plain">
  <strong>쉽게:</strong> Chase RR 1위여도 <strong>미보유·위성만</strong>.
  군인 루틴·소액 포트에 Ph3 바이너리 풀베팅은 부적합.
</div>
<table>
  <tr><th>항목</th><th>권고</th><th>이유</th></tr>
  <tr><td>신규</td><td>관심만 / 있다면 <strong>≤3–5%</strong></td><td>바이너리·희석</td></tr>
  <tr><td>REGAL 전</td><td>추격 매수 금지</td><td>이미 모멘텀 선반영</td></tr>
  <tr><td>성공 후</td><td>재평가 후 소량</td><td>승인·상업화는 별 레이스</td></tr>
  <tr><td>실패 시</td><td>즉시 청산</td><td>Thesis 붕괴</td></tr>
</table>

<div class="warn">
  <strong>Thesis Breakers:</strong>
  <ul>
    <li>REGAL OS 실패·임상적 무의미</li>
    <li>안전성 이슈·개발 중단</li>
    <li>ATM/대규모 희석으로 런웨이만 연장·스토리 공허</li>
    <li>파트너십 파기·자금 고갈</li>
  </ul>
</div>
</div>

<div class="block">
<h2>8. 한계 · 출처</h2>
<ul>
  <li>가격·재무: Yahoo Finance / yfinance.</li>
  <li>임상·현금·ATM: SELLAS Q1'26 IR / 8-K (2026-05).</li>
  <li>시나리오·파이프라인 비중은 작업용 개념. 투자 권고 아님.</li>
</ul>
<div class="footer-note">
  생성: 수익구조분석() · 티커 SLS · 기준 {ASOF} · WeasyPrint + NanumGothic
</div>
</div>

</body></html>
"""
    return html


def main() -> None:
    charts = {
        "flow": chart_business_flow(),
        "mix": chart_pipeline_mix(),
        "burn": chart_burn(),
        "cash": chart_cash_runway(),
        "funnel": chart_tam_funnel(),
        "sens": chart_sensitivity(),
        "scen": chart_scenarios(),
        "eps": chart_eps_beat(),
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
