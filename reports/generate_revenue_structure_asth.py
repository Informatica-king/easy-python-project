#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(ASTH) — 시각자료 + 초보용 설명 + 전문용어 주석 + WeasyPrint PDF."""

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
    Path("/opt/cursor/artifacts/ASTH_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/ASTH_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/ASTH_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/asth")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "teal": "#0f766e",
    "teal2": "#14b8a6",
    "slate": "#334155",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "blue": "#1e3a5f",
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
        (0.15, 0.65, 1.7, 1.55, "보험사\n(MA·Medicaid\n등)", C["sand"]),
        (2.05, 0.65, 1.85, 1.55, "인두제\n(PMPM)\n지급", C["gold"]),
        (4.1, 0.65, 1.9, 1.55, "ASTH\nCare Partners\n리스크 관리", C["teal"]),
        (6.2, 0.65, 1.75, 1.55, "의료비\n통제·케어", C["teal2"]),
        (8.15, 0.65, 1.65, 1.55, "절감분\n=이익", C["slate"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("비즈니스 한눈에 — 환자 케어를 맡아 의료비를 아끼면 이익", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    # Gross segment before elim: CP 910, CD 85, CE 88 — show share of gross then note elim
    ax = axes[0]
    sizes = [910, 85, 88]
    labels = ["Care Partners\n910M", "Care Delivery\n85M", "Care Enablement\n88M"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["teal"], C["gold"], C["sand"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("세그먼트 매출 (Q1'26, 제거 전)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    # Full-risk vs other of Care Partners ~80% full risk
    sizes = [80, 20]
    labels = ["풀리스크\n(~80% of CP)", "그 외\n위험공유 등"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["slate"], C["teal2"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("Care Partners 계약 형태 (Q1'26)", fontproperties=PROP_B, fontsize=11)
    fig.suptitle("ASTH 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    return save_fig(fig, "02_segment_mix.png")


def chart_segment_bars() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    cats = ["Care\nPartners", "Care\nDelivery", "Care\nEnablement", "제거\n(내부거래)", "연결\n합계"]
    # Q1'26
    vals = [910, 85, 88, -117, 965]
    colors = [C["teal"], C["gold"], C["sand"], C["red"], C["slate"]]
    bars = ax.bar(cats, [abs(v) if v < 0 else v for v in vals], color=colors, width=0.55)
    # show negative elim differently - use signed
    ax.clear()
    x = range(len(cats))
    for i, (v, c) in enumerate(zip(vals, colors)):
        ax.bar(i, v, color=c, width=0.55)
        ax.text(i, v + (25 if v >= 0 else -45), f"{v}", ha="center", fontproperties=PROP, fontsize=8)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(cats, fontproperties=PROP, fontsize=9)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("Q1'26 세그먼트 → 연결 매출 브리지", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "03_segment_bridge.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    layers = [
        (9.2, 8.3, "TAM — 미국 VBC·MA 시장", "메디케어 어드밴티지·가치기반 케어 전체 (수백 B USD급)", C["sand"]),
        (7.6, 6.2, "SAM — 리스크 이전 가능 인구", "인두제·공유저축 계약으로 이전되는 멤버십 풀", C["gold"]),
        (5.8, 4.1, "SOM — ASTH 멤버 ~1.55M", "가치기반 케어 배열 환자 · FY26 매출 가이던스 3.8–4.1B", C["teal2"]),
        (4.2, 2.0, "핵심 엔진 Care Partners", "Q1 CP 910M · 풀리스크 ~80% of CP 매출", C["teal"]),
    ]
    for w, y, title, sub, c in layers:
        x0 = (10 - w) / 2
        ax.add_patch(
            FancyBboxPatch(
                (x0, y - 0.85), w, 1.55, boxstyle="round,pad=0.02,rounding_size=0.15",
                facecolor=c, edgecolor="white", linewidth=2, alpha=0.92,
            )
        )
        tc = "white" if c in (C["teal"], C["slate"], C["blue"]) else C["ink"]
        ax.text(5, y + 0.25, title, ha="center", va="center", fontproperties=PROP_B, fontsize=11, color=tc)
        ax.text(5, y - 0.35, sub, ha="center", va="center", fontproperties=PROP, fontsize=8.2, color=tc)
    ax.set_title("시장 깔때기 — 가치기반 케어에서 ASTH의 자리", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "04_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    steps = [
        "멤버십\n·믹스",
        "PMPM\n단가",
        "의료비\n(MCR)",
        "리스크\n이전 비중",
        "Adj.\nEBITDA",
        "이자·세금",
        "EPS",
    ]
    xs = list(range(len(steps)))
    ys = [1.0, 0.94, 0.82, 0.88, 0.75, 0.70, 0.65]
    ax.plot(xs, ys, "o-", color=C["teal"], lw=2.5, ms=9)
    for i, (s, y) in enumerate(zip(steps, ys)):
        ax.annotate(s, (i, y), textcoords="offset points", xytext=(0, 14), ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0.55, 1.15)
    ax.set_xticks([])
    ax.set_ylabel("상대 기여(개념)", fontproperties=PROP)
    ax.set_title("민감도 사슬 — 멤버·의료비가 이익을 흔든다", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    # highlight MCR as key
    ax.annotate("핵심 리스크", xy=(2, 0.82), xytext=(2.6, 0.58),
                fontproperties=PROP, fontsize=8, color=C["red"],
                arrowprops=dict(arrowstyle="->", color=C["red"]))
    return save_fig(fig, "05_sensitivity.png")


def chart_scenarios() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    labels = ["Bear", "Base", "Bull"]
    rev = [3500, 3950, 4300]
    ebitda = [200, 265, 320]
    colors = [C["red"], C["gold"], C["teal"]]
    ax = axes[0]
    bars = ax.bar(labels, rev, color=colors, width=0.55)
    ax.set_title("시나리오별 연간 매출 (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 50, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 5000)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    bars = ax.bar(labels, ebitda, color=colors, width=0.55)
    ax.set_title("시나리오별 Adj. EBITDA (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, ebitda):
        ax.text(b.get_x() + b.get_width() / 2, v + 8, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 380)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("Bear / Base / Bull — 가이던스 중심 시나리오", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "06_scenarios.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [620, 655, 956, 951, 965]
    oi = [21, 20, 19, 18, 29]
    x = range(len(labels))
    ax.bar(x, rev, color=C["teal"], alpha=0.85, label="매출 (백만 USD)", width=0.55)
    ax2 = ax.twinx()
    ax2.plot(x, oi, "o-", color=C["gold"], lw=2.2, ms=8, label="영업이익 (백만 USD)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("매출 (백만 USD)", fontproperties=PROP, color=C["teal"])
    ax2.set_ylabel("영업이익 (백만 USD)", fontproperties=PROP, color=C["gold"])
    ax.set_title("분기 추이 — 매출 점프와 영업이익", fontproperties=PROP_B, fontsize=12)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    return save_fig(fig, "07_quarterly.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["~4Q전", "~3Q전", "~2Q전", "최근(Q1'26)"]
    # using adjusted-ish from earn hist - actuals were 0.58, 0.67, 0.42, 0.74
    actual = [0.58, 0.67, 0.42, 0.74]
    est = [0.48, 0.61, 0.33, 0.65]
    surprise = [21, 11, 29, 14]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], est, w, label="예상 EPS", color=C["sand"])
    ax.bar([i + w / 2 for i in x], actual, w, label="실제 EPS", color=C["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("EPS (USD)", fontproperties=PROP)
    ax.set_title("실적 서프라이즈 — 연속 Beat", fontproperties=PROP_B, fontsize=12)
    for i, s in enumerate(surprise):
        ax.text(i + w / 2, actual[i] + 0.03, f"+{s}%", ha="center", fontsize=8, fontproperties=PROP, color=C["green"])
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
        (0.4, 0.55, 2.3, 1.7, "코어\nECPG", C["blue"]),
        (2.95, 0.55, 2.4, 1.7, "코어\nASTH\n보유·유지", C["teal"]),
        (5.6, 0.55, 2.0, 1.7, "INDV/BTSG\n추가금지", C["gold"]),
        (7.9, 0.55, 1.8, 1.7, "현금\n버퍼", C["sand"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=tc)
    ax.set_title("포지션 맥락 — 가치기반 케어 코어 홀드", fontproperties=PROP_B, fontsize=12, pad=6)
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
        content: "수익구조분석(ASTH) · {ASOF} · " counter(page) " / " counter(pages);
        font-family: NanumGothic; font-size: 8.5pt; color: #78716c;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: NanumGothic, sans-serif; color: #1c1917; font-size: 10pt; line-height: 1.55; }}
    h1 {{ font-size: 20pt; font-weight: 700; margin: 0 0 4px; color: #0f766e; }}
    h2 {{ font-size: 13.5pt; font-weight: 700; margin: 22px 0 8px; padding-bottom: 4px;
         border-bottom: 2px solid #0f766e; color: #0f766e; page-break-after: avoid; }}
    h3 {{ font-size: 11pt; font-weight: 700; margin: 12px 0 6px; color: #334155; }}
    .hero {{
      background: linear-gradient(135deg, #0f766e 0%, #14b8a6 50%, #b8860b 125%);
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
    .gloss-title {{ font-weight: 700; color: #334155; margin-bottom: 4px; font-size: 9pt; }}
    .gloss ul {{ margin: 0 0 0 14px; }}
    .gloss .term {{ font-weight: 700; color: #0f766e; }}
    .plain {{ background: #f0fdfa; border: 1px solid #99f6e4; padding: 8px 12px; margin: 6px 0 10px; font-size: 9.5pt; }}
    .plain strong {{ color: #0f766e; }}
    .warn {{ background: #fff1f2; border-left: 4px solid #9f1239; padding: 8px 12px; margin: 8px 0; font-size: 9.5pt; }}
    .footer-note {{ font-size: 8pt; color: #78716c; margin-top: 18px; border-top: 1px solid #e7e5e4; padding-top: 8px; }}
    """

    c0 = fig_block(charts["flow"], "그림 0. 비즈니스 흐름 — 보험료(인두제) → 케어 → 절감 = 이익")
    c1 = fig_block(charts["mix"], "그림 1. 세그먼트·계약 형태 파이")
    c2 = fig_block(charts["bridge"], "그림 2. 세그먼트 → 연결 매출 브리지 (Q1'26)")
    c3 = fig_block(charts["funnel"], "그림 3. TAM→SAM→SOM 깔때기")
    c4 = fig_block(charts["sens"], "그림 4. 민감도 사슬 — MCR이 핵심")
    c5 = fig_block(charts["scen"], "그림 5. Bear/Base/Bull")
    c6 = fig_block(charts["qtr"], "그림 6. 최근 5분기 매출·영업이익")
    c7 = fig_block(charts["eps"], "그림 7. EPS 서프라이즈")
    c8 = fig_block(charts["pos"], "그림 8. 포트폴리오에서의 ASTH")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"/><title>수익구조분석 — ASTH (Astrana Health)</title>
<style>{css}</style></head>
<body>

<div class="hero">
  <h1>수익구조분석 · ASTH</h1>
  <div>Astrana Health, Inc. · 나스닥 · 가치기반 케어(VBC) · 의료 네트워크/MSO</div>
  <div class="oneline">
    <strong>한 줄 구조:</strong> 보험사로부터 환자 1명당 정해진 돈(인두제)을 받고,
    그 안에서 진료비를 관리합니다. 의료비를 잘 통제하면 남는 돈이 이익이 되고,
    환자가 예상보다 아프면 손해가 납니다. 매출의 압도적 비중은 <em>Care Partners</em>이며,
    그중 약 80%가 <em>풀리스크(전액 위험 부담)</em> 계약입니다.
  </div>
  <div class="kpi">
    <span>종가 $44.94</span>
    <span>시총 ~$2.2B</span>
    <span>PT $41 / $49.3 / $65</span>
    <span>Q1'26 매출 $965M (+56%)</span>
    <span>Care Partners $910M</span>
    <span>멤버 ~1.55M</span>
    <span>FY26 매출 $3.8–4.1B · Adj.EBITDA $250–280M</span>
    <span>실적 ~08-06</span>
    <span>기준일 {ASOF}</span>
  </div>
</div>

<div class="plain">
  <strong>이 보고서를 읽는 법 (비전공자용):</strong>
  “어디서 돈을 받는지 → 시장 크기 → 무엇이 흔들리는지 → 좋은/나쁜 숫자 →
  경쟁 → 미리 볼 신호 → 얼마나 들고 있을지” 순서입니다.
  각 블록 끝에 용어 주석이 있고, 이미 설명한 말은 다시 쓰지 않습니다.
</div>

{c0}

<div class="block">
<h2>1. 수익 구조 — 세그먼트·계약·마진</h2>
<div class="plain">
  <strong>쉽게:</strong> 일반 병원은 “진료할 때마다 돈”(행위별 수가)을 받습니다.
  ASTH의 핵심은 반대에 가깝습니다. “이 환자들 건강을 우리가 책임질 테니, 한 달에 얼마씩 주세요.”
  그다음 병원·의사·약값을 아껴서, 받은 돈보다 적게 쓰면 이익입니다.
  그래서 <em>환자 수 × 인당 단가</em>가 매출이고, <em>실제 의료비</em>가 원가에 가깝습니다.
</div>
{c1}
{c2}

<h3>1-1. Q1'26 세그먼트 (회사 공시, 천 단위 반올림)</h3>
<table>
  <tr><th>세그먼트</th><th>매출</th><th>역할(쉬운 말)</th></tr>
  <tr><td>Care Partners</td><td>$909.7M (+51% YoY)</td><td>보험과 계약해 환자 집단을 지고 케어 네트워크를 운영. <strong>사실상 회사 전부</strong></td></tr>
  <tr><td>Care Delivery</td><td>$85.1M</td><td>직접 운영하는 클리닉·진료 전달</td></tr>
  <tr><td>Care Enablement</td><td>$87.7M</td><td>MSO·플랫폼·운영 지원(다른 세그먼트에도 서비스)</td></tr>
  <tr><td>세그먼트 간 제거</td><td>−$117.4M</td><td>내부 거래를 빼서 중복 계산 방지</td></tr>
  <tr><td><strong>연결 매출</strong></td><td><strong>$965.1M (+56%)</strong></td><td>외부 고객 기준 최종 매출</td></tr>
</table>

<p>
Care Partners 안에서는 분기 말 기준 <strong>약 80%의 인두제(캡itation) 매출</strong>이 풀리스크 계약이고,
보유 멤버십의 약 <strong>40%</strong>가 풀리스크입니다.
“매출 비중 80% vs 멤버 비중 40%”가 다른 이유: 풀리스크 계약 쪽 인당 매출(또는 계약 규모)이 더 크기 때문입니다.
새 계약도 인수 기준에 맞게 돌아가고 있다고 경영진이 코멘트했습니다.
</p>

<table>
  <tr><th>Q1'26 손익 하이라이트</th><th>금액</th><th>YoY</th></tr>
  <tr><td>순이익 (Astrana 귀속)</td><td>$14.4M</td><td>+116%</td></tr>
  <tr><td>희석 EPS (GAAP)</td><td>$0.29</td><td>+107%</td></tr>
  <tr><td>Adjusted EBITDA</td><td>$66.3M</td><td>+82%</td></tr>
  <tr><td>Adjusted EPS (희석)</td><td>$0.74</td><td>+76%</td></tr>
  <tr><td>영업현금흐름</td><td>$68M대</td><td>+309%대</td></tr>
  <tr><td>Free Cash Flow</td><td>~$64M</td><td>+372%대</td></tr>
</table>

{c6}

<h3>1-2. 연간 추이</h3>
<table>
  <tr><th>연도</th><th>매출</th><th>매출총이익</th><th>영업이익</th><th>순이익</th><th>이자비용</th></tr>
  <tr><td>FY2022</td><td>$1,144M</td><td>$199M</td><td>$104M</td><td>$45M</td><td>$8M</td></tr>
  <tr><td>FY2023</td><td>$1,387M</td><td>$215M</td><td>$85M</td><td>$61M</td><td>$16M</td></tr>
  <tr><td>FY2024</td><td>$2,035M</td><td>$271M</td><td>$89M</td><td>$43M</td><td>$33M</td></tr>
  <tr><td>FY2025</td><td>$3,182M</td><td>$342M</td><td>$79M</td><td>$22M</td><td>$50M</td></tr>
</table>

<p>
매출은 급증(FY25 Care Partners만 $3.02B)했지만, GAAP 영업이익·순이익은 늘지 않거나 줄었습니다 —
<strong>성장 투자, 인수, 이자(부채 ~$1.07B), 풀리스크 전환 비용</strong>이 겹친 전형적인 VBC 스케일업 패턴입니다.
그래서 시장은 GAAP보다 <strong>Adjusted EBITDA / Adjusted EPS</strong>와 멤버십·의료비 트렌드를 더 봅니다.
보고 GM ~10.7%, OM ~3.0%, PM ~0.9%로, “초고마진 제약”이 아니라 “얇은 마진의 대규모 케어 플랫폼”입니다.
</p>

<div class="callout">
  <strong>FY26 가이던스(재확인):</strong> 매출 <strong>$3.8–4.1B</strong> · Adjusted EBITDA <strong>$250–280M</strong>.
  Q2'26 가이던스 매출 ~$969M–$1.00B, Adj.EBITDA ~$60–70M.
  보수적 멤버십 가정, HQAF 기여 0 가정 등 경영진이 “보수적으로 잡는다”고 반복.
</div>

{gloss([
    ("가치기반 케어 (VBC)", "진료 횟수보다 ‘환자 건강 결과·비용 효율’에 맞춰 돈을 주는 방식. ASTH 비즈니스의 뼈대."),
    ("인두제 / Capitation / PMPM", "환자 1명당 한 달(또는 해)에 정해진 금액. Per Member Per Month."),
    ("풀리스크 (Full risk)", "의료비 전액(또는 거의 전부)을 회사가 책임. 잘하면 이익, 못하면 손실이 커짐."),
    ("Care Partners", "보험사와 리스크 계약을 맺고 제휴 의사·네트워크로 케어하는 ASTH 핵심 세그먼트."),
    ("Care Delivery", "회사가 직접 돌리는 클리닉·진료."),
    ("Care Enablement / MSO", "관리서비스조직. 청구·운영·데이터 등으로 케어를 ‘가능하게’ 하는 팔."),
    ("세그먼트 간 제거", "회사 안끼리 사고판 금액을 연결 재무에서 빼는 회계 조정."),
    ("Adjusted EBITDA", "일회성·비현금 등을 조정한 영업 현금창출력 지표. VBC 기업 비교에 자주 씀."),
    ("GAAP", "법정 회계 기준. 조정 지표와 숫자가 다를 수 있음."),
])}
</div>

<div class="block">
<h2>2. 시장 깔때기 — TAM → SAM → SOM</h2>
<div class="plain">
  <strong>쉽게:</strong> 미국 건강보험 시장은 거대합니다. 그중 ASTH가 먹는 조각은
  “보험사가 리스크를 의사 네트워크에 넘기는 계약”에 들어간 환자들입니다.
</div>
{c3}

<table>
  <tr><th>단계</th><th>대략</th><th>정의</th><th>헷갈리기 쉬운 점</th></tr>
  <tr>
    <td>TAM</td>
    <td>수백 B USD급</td>
    <td>미국 MA·Medicaid·교환 등 VBC로 전환 가능한 의료비 풀</td>
    <td>TAM이 커도 ASTH 매출이 바로 그 크기는 아님</td>
  </tr>
  <tr>
    <td>SAM</td>
    <td>리스크 이전 계약 시장</td>
    <td>인두제·공유저축으로 실제 이전되는 인구</td>
    <td>주·보험사·규제에 따라 속도가 다름</td>
  </tr>
  <tr>
    <td>SOM</td>
    <td>멤버 ~1.55M · 매출 가이던스 $3.8–4.1B</td>
    <td>ASTH가 이미 서비스하는 VBC 배열</td>
    <td>멤버 수 ↑가 곧바로 이익 ↑는 아님 (의료비·믹스 중요)</td>
  </tr>
  <tr>
    <td>핵심</td>
    <td>Care Partners + 풀리스크 전환</td>
    <td>같은 멤버라도 풀리스크 비중이 올라가면 매출·변동성 동시 ↑</td>
    <td>성장과 리스크는 한 몸</td>
  </tr>
</table>

<p>
페이여 구성은 Medicare Advantage, Medicaid, Exchange(ACA) 등이 섞여 있습니다.
콜에서 Medicaid·Exchange 이탈(attrition)·중증도(acuity)를 “대체로 가이던스 안”으로 관리한다고 했습니다.
<strong>HQAF(병원 수수료 관련 프로그램) 기여는 FY26 가이던스에 0</strong>으로 넣어 보수성을 강조했습니다.
</p>

{gloss([
    ("TAM / SAM / SOM", "전체 시장 / 우리가 팔 수 있는 시장 / 실제로 가져가는 규모."),
    ("Medicare Advantage (MA)", "민간 보험사가 운영하는 메디케어 대안 플랜. VBC·인두제와 자주 결합."),
    ("Medicaid", "저소득층 공적 의료보장. 주마다 규칙이 다름."),
    ("Exchange / ACA", "오바마케어 건강보험 거래소 가입자."),
    ("Attrition (이탈)", "멤버가 플랜·네트워크를 떠나는 비율."),
    ("Acuity (중증도)", "환자 집단이 얼마나 아픈지. 높으면 의료비 ↑."),
    ("HQAF", "가이던스에서 제외한 병원 관련 수수료/프로그램 항목(경영진 보수 가정의 일부)."),
])}
</div>

<div class="block">
<h2>3. 민감도 사슬 — 무엇이 이익을 흔드나</h2>
<div class="plain">
  <strong>쉽게:</strong> 용돈(인두제)은 고정에 가깝고, 병원비 청구서가 커지면 용돈이 모자라 적자입니다.
  그래서 <em>의료비 비율</em>이 이 회사의 온도계입니다.
</div>
{c4}

<table>
  <tr><th>단계</th><th>좋게 나오면</th><th>나쁘게 나오면</th></tr>
  <tr><td>① 멤버십·페이여 믹스</td><td>안정적 가입, 유리한 구성</td><td>이탈↑, 고비용 환자 편중</td></tr>
  <tr><td>② PMPM 단가</td><td>계약 갱신·리스크 조정 유리</td><td>단가 압박, 불리한 리스크 점수</td></tr>
  <tr><td>③ 의료비 (MCR)</td><td>예방·케어관리로 비용 통제</td><td>입원·고가약·이용량 급증 → 마진 붕괴</td></tr>
  <tr><td>④ 풀리스크 비중</td><td>실적 레버리지↑ (잘할 때)</td><td>손실 레버리지↑ (못할 때)</td></tr>
  <tr><td>⑤ Adj. EBITDA</td><td>가이던스 달성·상향</td><td>마진 압축</td></tr>
  <tr><td>⑥ 이자·세금</td><td>현금창출력으로 부채 관리</td><td>이자 $50M(FY25) 부담 가중</td></tr>
  <tr><td>⑦ EPS</td><td>조정 EPS Beat 지속</td><td>GAAP·조정 괴리 확대, 신뢰↓</td></tr>
</table>

<p>
Q1'26은 매출 +56%, Adj.EBITDA +82%로 <strong>이익 레버리지가 매출보다 큼</strong> —
플랫폼 효율·풀리스크 전환이 우호적으로 작동한 분기입니다.
반대로 독감 시즌·코로나 재확산·약가 충격처럼 의료비가 한꺼번에 튀면 ③이 바로 실습니다.
</p>

{gloss([
    ("MCR (Medical Cost Ratio) / Medical Loss Ratio 유사 개념", "받은 인두제 대비 실제 의료비 비율. 낮을수록(비용 통제) 이익에 유리."),
    ("리스크 조정", "환자 중증도에 따라 보험이 주는 금액을 보정하는 장치. 점수·문서화가 중요."),
    ("레버리지", "잘될 때 이익이 더 빨리 늘, 안 될 때 손실도 더 큼."),
])}
</div>

<div class="block">
<h2>4. Bear / Base / Bull — 숫자 시나리오</h2>
<div class="plain">
  <strong>쉽게:</strong> FY26 가이던스($3.8–4.1B 매출, $250–280M Adj.EBITDA)를 가운데 두고
  아래위 시나리오를 작업용으로 잡았습니다.
</div>
{c5}

<table>
  <tr><th>시나리오</th><th>가정</th><th>매출</th><th>Adj.EBITDA</th><th>주가 함의(개념)</th></tr>
  <tr>
    <td>Bear</td>
    <td>의료비 스파이크, 이탈↑, 풀리스크 손실, 가이던스 하단 이탈</td>
    <td>~$3.5B</td>
    <td>~$200M</td>
    <td>$28–36</td>
  </tr>
  <tr>
    <td>Base</td>
    <td>가이던스 중간~상단, 풀리스크 안정, 멤버십 보수 가정 유지</td>
    <td>~$3.95B</td>
    <td>~$265M</td>
    <td>$46–55 (PT 평균~$49 정합)</td>
  </tr>
  <tr>
    <td>Bull</td>
    <td>의료비 우호, 추가 계약, EBITDA 상향, 현금흐름 가속</td>
    <td>~$4.3B+</td>
    <td>~$320M</td>
    <td>$58–68 (PT 고점 $65 근처)</td>
  </tr>
</table>

<p>
현재가 <strong>$44.94</strong> vs PT 평균 <strong>~$49.3</strong>(저 $41 / 고 $65).
저점 PT($41)가 현재가 아래라 “애널리스트도 하방 시나리오를 열어 둔” 상태이고,
업사이드는 고점 기준 여유가 있습니다. 52주 고점 $51.60 대비는 소폭 아래.
</p>

{c7}
<p>
최근 분기 EPS는 컨센서스 대비 대략 <strong>+11%~+29%</strong> Beat.
ECPG·INDV만큼 “초대형 서프라이즈”는 아니지만, 연속 Beat 패턴은 유지입니다.
차기 실적(~08-06)에서는 매출 Beat보다 <strong>Adj.EBITDA·의료비 톤·멤버십 코멘트</strong>가 주가에 더 중요할 수 있습니다.
</p>

{gloss([
    ("Bear / Base / Bull", "비관·기본·낙관 시나리오."),
    ("컨센서스", "애널리스트 추정 평균."),
    ("Beat", "실제 &gt; 예상."),
])}
</div>

<div class="block">
<h2>5. 경쟁·포지션</h2>
<div class="plain">
  <strong>쉽게:</strong> “환자 리스크를 떠안는 네트워크” 시장에는 보험사 직영, 대형 의사그룹, 다른 VBC 상장사들이 있습니다.
  ASTH는 캘리포니아 등에서 쌓은 네트워크·MSO·풀리스크 전환 실행력이 무기입니다.
</div>
<table>
  <tr><th>전선</th><th>ASTH</th><th>압력</th><th>관찰</th></tr>
  <tr>
    <td>MA·Medicaid VBC</td>
    <td>Care Partners 규모 확대</td>
    <td>보험사 계약 조건, 경쟁 네트워크</td>
    <td>신규 계약, 풀리스크 %</td>
  </tr>
  <tr>
    <td>케어 전달</td>
    <td>자체 클리닉 + 제휴</td>
    <td>인력·임대·진료 용량</td>
    <td>Care Delivery 마진</td>
  </tr>
  <tr>
    <td>플랫폼/MSO</td>
    <td>Enablement</td>
    <td>IT·인건비</td>
    <td>내부 제거 후 기여</td>
  </tr>
</table>
{gloss([
    ("의사 네트워크", "계약된 개원·그룹 의사 집단. 환자가 여기서 진료받음."),
    ("상장 VBC 피어", "유사 사업을 하는 다른 공개회사들. 멀티플 비교에 사용."),
])}
</div>

<div class="block">
<h2>6. 선행 지표</h2>
<ul>
  <li><strong>멤버십 수·페이여 믹스</strong> — 1.55M 추이, MA/Medicaid/Exchange</li>
  <li><strong>풀리스크 매출·멤버 비중</strong> — 80% / 40%에서 어떻게 변하는지</li>
  <li><strong>의료비·이용량 코멘트</strong> — 입원, 약국, 시즌성</li>
  <li><strong>Adj. EBITDA 마진</strong> — 매출 성장 대비 이익 레버리지</li>
  <li><strong>FCF·순부채</strong> — 이자 부담과 성장 투자 균형</li>
  <li><strong>차기 실적 ~08-06</strong> — Q2 가이던스 대비 실제, FY 톤</li>
</ul>
{gloss([
    ("선행 지표", "실적 전에 방향성을 가늠하는 신호."),
    ("FCF (Free Cash Flow)", "영업현금에서 설비투자 등을 뺀 여유 현금."),
])}
</div>

<div class="block">
<h2>7. 비중 상한 · Thesis Breakers</h2>
{c8}
<div class="plain">
  <strong>쉽게:</strong> 소액 포트에서 ASTH는 <strong>코어 보유</strong>입니다.
  실적(~08-06) 앞에서는 무리한 추격보다 홀드가 기본입니다.
</div>
<table>
  <tr><th>항목</th><th>권고</th><th>이유</th></tr>
  <tr><td>현재</td><td>코어 Hold (예: 3주)</td><td>VBC 스케일 + Adj 지표 개선 + PT 여유</td></tr>
  <tr><td>추가 매수</td><td>실적 전 신중</td><td>이벤트 리스크, 의료비 서프라이즈 가능</td></tr>
  <tr><td>비중 상한</td><td>총자산 ~20–30%</td><td>코어지만 ECPG와 분산</td></tr>
  <tr><td>논리 폐기</td><td>아래 Breaker</td><td>규칙으로 대응</td></tr>
</table>

<div class="warn">
  <strong>Thesis Breakers:</strong>
  <ul>
    <li>의료비 급등으로 Adj.EBITDA 가이던스 하향</li>
    <li>풀리스크 계약에서 구조적 손실 (인수 실패)</li>
    <li>멤버십 이탈이 가이던스를 깨는 수준으로 악화</li>
    <li>대형 규제·환수·감사 이슈</li>
    <li>부채·이자 부담이 현금흐름을 잠식</li>
  </ul>
</div>

{gloss([
    ("코어", "포트의 중심 보유 종목."),
    ("Thesis Breaker", "보유 논리를 무효로 만드는 사건."),
])}
</div>

<div class="block">
<h2>8. 한계 · 출처</h2>
<ul>
  <li>시가·PT·일부 재무: Yahoo Finance 집계(지연·수정 가능).</li>
  <li>세그먼트·멤버십·가이던스·조정 지표: Astrana IR / 실적자료(Q1'26, FY25).</li>
  <li>TAM은 산업 구조 기반 근사.</li>
  <li>시나리오는 교육·의사결정 보조용. 투자 권고 아님.</li>
</ul>
<div class="footer-note">
  생성: 수익구조분석() · 티커 ASTH · 기준 {ASOF} · WeasyPrint + NanumGothic
</div>
</div>

</body></html>
"""
    return html


def main() -> None:
    charts = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "bridge": chart_segment_bars(),
        "funnel": chart_tam_funnel(),
        "sens": chart_sensitivity(),
        "scen": chart_scenarios(),
        "qtr": chart_quarterly(),
        "eps": chart_eps_surprise(),
        "pos": chart_position(),
    }
    html = build_html(charts)
    html, _px = build_and_insert_price("ASTH", CHART_DIR, html)
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
