#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(NWPX) — 수자원 인프라(WTS·Precast) 매출구조 + 초보용 설명 + WeasyPrint PDF."""

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
ASOF = "2026-07-25"
OUT_PDF = [
    Path("/opt/cursor/artifacts/NWPX_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/NWPX_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/NWPX_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/NWPX_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/nwpx")
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
    "water": "#0284c7",
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
        (0.1, 0.7, 1.75, 1.6, "IIJA·주정부\n수자원 CapEx", C["sand"]),
        (2.05, 0.7, 1.8, 1.6, "입찰·설계\n장주기", C["gold"]),
        (4.05, 0.7, 1.8, 1.6, "WTS\n송수 강관", C["water"]),
        (6.05, 0.7, 1.75, 1.6, "Precast\n하수도·펌프", C["teal"]),
        (8.0, 0.7, 1.75, 1.6, "백로그\n→매출", C["navy"]),
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
    ax.set_title("비즈니스 한눈에 — 물·하수도 인프라 ‘강관·프리캐스트’를 만든다", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    # FY25: WTS 350.9, Precast 175.1 = 526.0
    sizes = [350.9, 175.1]
    labels = ["WTS\n$350.9M (67%)", "Precast\n$175.1M (33%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["water"], C["teal"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("FY2025 세그먼트 매출 ($526M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["WTS", "Precast"]
    gp = [67.1, 36.5]
    bars = ax.bar(cats, gp, color=[C["water"], C["teal"]], width=0.5)
    ax.set_ylabel("총이익 (백만 USD)", fontproperties=PROP)
    ax.set_title("FY2025 세그먼트 총이익", fontproperties=PROP_B, fontsize=11)
    for b, v, s in zip(bars, gp, [350.9, 175.1]):
        m = v / s * 100
        ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v:.1f}\n({m:.1f}%)", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 85)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_backlog() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    cats = ["WTS\n백로그\nQ1'25", "WTS\n백로그\nYE'25", "WTS\n백로그\nQ1'26", "확정주문\n포함 Q1'26", "Precast\n수주잔고"]
    vals = [203, 234, 373, 430, 55]
    colors = [C["slate"], C["slate"], C["water"], C["navy"], C["teal"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("가시성 — WTS 백로그 급증 (Q1'26 기록)", fontproperties=PROP_B, fontsize=12)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 8, f"{v}", ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 500)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)
    fig.tight_layout()
    return save_fig(fig, "03_backlog.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    qs = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [116.1, 133.2, 151.1, 125.6, 138.3]
    colors = [C["slate"]] * 4 + [C["water"]]
    bars = ax.bar(qs, rev, color=colors, width=0.58)
    ax.set_ylabel("매출 (백만 USD)", fontproperties=PROP)
    ax.set_title("분기 매출 — Q1'26 $138.3M (+19% YoY)", fontproperties=PROP_B, fontsize=12)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 180)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "04_quarterly.png")


def chart_margins() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6))
    ax = axes[0]
    yrs = ["FY22", "FY23", "FY24", "FY25"]
    gm = [18.8, 17.5, 19.4, 19.7]
    bars = ax.bar(yrs, gm, color=[C["slate"], C["slate"], C["teal"], C["navy"]], width=0.5)
    ax.set_ylabel("GM %", fontproperties=PROP)
    ax.set_title("연간 매출총이익률", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, gm):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.25, f"{v}%", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(14, 24)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    cats = ["WTS\nQ1'26", "Precast\nQ1'26", "전사\nQ1'26"]
    # WTS GP 17.3/93.5=18.5%, Precast 9.3/44.8=20.8%, consol 26.7/138.3=19.3%
    vals = [18.5, 20.8, 19.3]
    bars = ax.bar(cats, vals, color=[C["water"], C["teal"], C["navy"]], width=0.5)
    ax.set_ylabel("GM %", fontproperties=PROP)
    ax.set_title("Q1'26 세그먼트 마진", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.4, f"{v}%", ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 28)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "05_margins.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    rows = [
        (0.4, 3.9, 9.2, 0.85, C["sand"], C["ink"], "미국 수자원·하수도 인프라 (IIJA SRF 등 장기 예산)"),
        (0.9, 2.85, 8.2, 0.85, C["gold"], C["ink"], "엔지니어드 송수관 · 프리캐스트 하수/우수/펌프"),
        (1.5, 1.8, 7.0, 0.85, C["water"], "white", "NWPX WTS (북미 최대급 송수 시스템) + Precast"),
        (2.2, 0.75, 5.6, 0.85, C["navy"], "white", "백로그 소진 → 분기 매출·마진"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=1.5,
            )
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("수요 깔때기 — 공공 물 인프라 → 백로그 → 인식", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "06_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    shocks = ["입찰 -20%", "입찰 -10%", "기준", "입찰 +10%", "입찰 +20%"]
    # illustrative: WTS backlog path index
    vals = [80, 90, 100, 110, 120]
    colors = [C["red"], "#ea580c", C["slate"], C["teal"], C["navy"]]
    bars = ax.bar(shocks, vals, color=colors, width=0.55)
    ax.set_ylabel("WTS 신규수주 지수 (기준=100)", fontproperties=PROP)
    ax.set_title("민감도 — 입찰/수주 강도 (선형 예시)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 140)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "07_sensitivity.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [70, 100, 125]
    highs = [95, 125, 150]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    ax.axvline(129.31, color=C["gold"], ls="--", lw=1.5)
    ax.text(131, 2.35, "현재 ~129", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.axvline(109.3, color="#2563eb", ls=":", lw=1.2)
    ax.text(95, -0.55, "PT평균 ~109", fontproperties=PROP, fontsize=7.5, color="#2563eb")
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        mid = (lo + hi) / 2
        ax.text(mid, i, f"{lo}–{hi}", ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(55, 170)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear (12M) — 현재가 > PT평균", fontproperties=PROP_B, fontsize=11)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP_B)
    fig.tight_layout()
    return save_fig(fig, "08_scenarios.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    qs = ["Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    surp = [27.0, 35.7, 46.5, 92.9]
    bars = ax.bar(qs, surp, color=C["green"], width=0.55)
    ax.set_ylabel("EPS 서프라이즈 %", fontproperties=PROP)
    ax.set_title("최근 4분기 EPS 서프라이즈 (연속 대형 Beat)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, surp):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"+{v:.0f}%", ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 110)
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
        (0.3, 2.6, 9.4, 1.0, C["navy"], "white", "포트 역할: 미보유 · Chase ‘하·과열’ — 추격 매수 비적합"),
        (0.3, 1.4, 4.5, 0.95, C["teal"], "white", "밸류\n현재 > PT평균 (~+18%)"),
        (5.0, 1.4, 4.7, 0.95, C["gold"], C["ink"], "다음 촉매\n실적 ~07-29"),
        (0.3, 0.25, 9.4, 0.95, C["sand"], C["ink"], "우선순위: NEO 07-28 → AMRX 07-30 → 현금버퍼 · NWPX는 관망"),
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
      @bottom-center {{ content:"NWPX 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0284c7; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0284c7; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#e0f2fe 0%,#e8eef5 55%,#f0fdfa 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#dbeafe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecaca; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#f0f9ff; border-left:4px solid #0284c7; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0284c7; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:110px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#0284c7; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>NWPX 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>NWPX 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">NWPX Infrastructure · 수자원 송수관(WTS) · Precast</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · FY2025 연간 + Q1 FY2026</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~$129</div><div class="s">시총 ~$1.25B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~$109</div><div class="s">프리미엄 ~+18%</div></span>
    <span class="kpi"><div class="l">FY25 매출</div><div class="v">$526M</div><div class="s">+6.8% · 기록</div></span>
    <span class="kpi"><div class="l">WTS 백로그</div><div class="v">$373M</div><div class="s">확정포함 $430M</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">EPS 4/4 Beat</span>
    <span class="tag">실적 ~07-29</span>
    <span class="tag bad">Chase 하·과열 · 추격 비적합</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>미국 물·하수도 인프라의 ‘강관+프리캐스트’ 제조사.</b>
FY25 기록 매출 <b>$526M</b>(WTS 67% / Precast 33%), Q1'26도 +19%.
백로그는 사상 최대이나, 주가(~$129)가 PT평균(~$109)을 <b>~18% 상회</b> —
심층분석 Chase도 <b>하·과열</b>. 당신 계좌에서는 <b>미보유·추격 매수 비적합</b>.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 도시가 마시는 물·하수를 나르는 큰 파이프와 콘크리트 구조물을 만듦.
정부가 수도관을 고치면 주문이 쌓이고(백로그), 공장에서 만들어 매출로 인식.</div>
{gloss([
    ("WTS", "Water Transmission Systems — 엔지니어드 송수(물 이송) 강관·이음·피팅."),
    ("Precast", "프리캐스트 콘크리트 — 하수·우수·펌프장 등 사전 제작 구조물."),
    ("백로그", "Backlog — 이미 계약된 일 중 아직 매출로 안 잡힌 잔여 의무."),
    ("IIJA", "미국 초당파 인프라법 — 식수·하수 State Revolving Fund 등 장기 예산."),
])}

<h2>1. 어디서 돈이 오나 — 두 세그먼트</h2>
{fig_block(charts['02'], 'FY25 세그먼트 믹스')}
<table>
  <tr><th>세그먼트 (FY2025)</th><th>매출</th><th>비중</th><th>총이익</th><th>GM</th><th>YoY 매출</th></tr>
  <tr><td>Water Transmission (WTS)</td><td>$350.9M</td><td>67%</td><td>$67.1M</td><td>19.1%</td><td>+3.8%</td></tr>
  <tr><td>Precast Infrastructure</td><td>$175.1M</td><td>33%</td><td>$36.5M</td><td>20.8%</td><td>+13.3%</td></tr>
  <tr><td><b>합계</b></td><td><b>$526.0M</b></td><td>100%</td><td><b>$103.6M</b></td><td><b>19.7%</b></td><td><b>+6.8%</b></td></tr>
</table>
<table>
  <tr><th>Q1 FY2026</th><th>매출</th><th>YoY</th><th>총이익</th><th>GM</th></tr>
  <tr><td>WTS</td><td>$93.5M</td><td>+19.1%</td><td>$17.3M</td><td>~18.5% (+~300bp)</td></tr>
  <tr><td>Precast</td><td>$44.8M</td><td>+18.9%</td><td>$9.3M</td><td>~20.9% (+~180bp)</td></tr>
  <tr><td><b>합계</b></td><td><b>$138.3M</b></td><td><b>+19.1%</b></td><td><b>$26.7M</b></td><td>~19.3%</td></tr>
</table>
<p class="small">FY25 NI <b>$35.4M</b> ($3.56/주) · 영업CF $67.3M · Boughton Precast(CO) 인수로 지역 확장.</p>
<div class="easy"><b>쉽게:</b> 돈의 2/3는 ‘큰 송수 파이프 프로젝트’, 1/3은 ‘하수·펌프용 콘크리트 제품’.
Precast가 더 빨리 자라고, WTS는 백로그로 앞을 보여 줌.</div>
{gloss([
    ("GM", "매출총이익률 — (매출−제조원가)/매출."),
    ("bp", "basis point — 0.01%p. 300bp = 3%p."),
    ("Permalink / ParkUSA / Geneva", "브랜드·제품 라인 (케이싱·프리캐스트 등)."),
])}

<h2>2. 성장 엔진 — 백로그 · 공공 예산</h2>
{fig_block(charts['03'], 'WTS 백로그')}
{fig_block(charts['06'], '수요 깔때기')}
<ul>
  <li>WTS 백로그 Q1'26 <b>$373M</b> (YE'25 $234M → 급증) · 확정주문 포함 <b>$430M</b></li>
  <li>잔여 의무 인식 예상: <b>2026 ~64%</b> · 2027 ~26% · 이후 잔여 (10-Q)</li>
  <li>Precast 수주잔고 ~$55M (단기성, WTS보다 회전 빠름)</li>
  <li>수요 드라이버: 노후 수도관 교체 · IIJA/SRF · 주·지방 예산 (장주기)</li>
  <li>리스크: 연방 예산/인력 차질 → <b>설계·엔지니어링 단계 지연</b>이 먼저, 이후 입찰 공백</li>
</ul>
<div class="easy"><b>쉽게:</b> 이미 따 놓은 일(백로그)이 많으면 앞으로 몇 분기 매출이 ‘어느 정도’ 보임.
다만 정부 돈이 늦어지면 새 입찰이 먼저 줄고, 백로그 소진 후에야 아픔이 옴.</div>
{gloss([
    ("확정주문 포함 백로그", "서명 계약 + 확정됐으나 아직 정식 계약 전 주문까지 합산한 가시성."),
    ("SRF", "State Revolving Fund — 주 정부가 돌리는 식수·하수 저금리 융자 풀."),
    ("장주기", "WTS 프로젝트는 계획·설계·시공까지 수년 — 단기 매크로와 어긋날 수 있음."),
])}

<h2>3. 분기 · 마진 · Beat</h2>
{fig_block(charts['04'], '분기 매출')}
{fig_block(charts['05'], '마진')}
{fig_block(charts['09'], 'EPS 서프라이즈')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>Q1'26 매출 / EPS</td><td>$138.3M / $1.08 (기록, Beat ~+93%)</td></tr>
  <tr><td>최근 4Q EPS 서프라이즈</td><td>+27% / +36% / +47% / +93%</td></tr>
  <tr><td>다음 실적 (캘린더)</td><td>~<b>2026-07-29</b> · Rev 컨센 ~$155M · EPS ~$1.31</td></tr>
  <tr><td>애널리스트</td><td>Hold 성향 · n≈3 · PT고 $130 ≈ 현재가</td></tr>
</table>
<div class="box"><b>해석:</b> Beat 머신 + 백로그 스토리는 강함.
문제는 <b>가격이 이미 PT·고점 근처</b>라 “좋은 회사 ≠ 지금 사기 좋은 가격”.
심층분석(07-25) Chase도 <b>하·과열</b>.</div>
{gloss([
    ("Beat", "컨센서스보다 좋은 실적."),
    ("Hold", "애널리스트 ‘보유’ 의견 — 신규 매수 적극 추천은 아님."),
])}

<h2>4. 민감도 · 시나리오 · 밸류</h2>
{fig_block(charts['07'], '입찰 민감도')}
{fig_block(charts['08'], '주가 시나리오')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>125–150</td><td>백로그 지속·마진 확대·IIJA 집행 순항 · PT 상향</td></tr>
  <tr><td>Base</td><td>100–125</td><td>PT(~109) 수렴 · 성장 지속하나 멀티플 축소</td></tr>
  <tr><td>Bear</td><td>70–95</td><td>입찰 공백·강재/관세 비용·공공 예산 지연</td></tr>
</table>
<table>
  <tr><th>밸류 스냅샷 ({ASOF})</th><th>수치</th></tr>
  <tr><td>현재가 / PT평균 / PT고·저</td><td>~$129 / ~$109 (−15% to PT) / $130–$90</td></tr>
  <tr><td>Trail / Fwd P/E</td><td>~30 / ~25</td></tr>
  <tr><td>52주</td><td>40 – 152</td></tr>
  <tr><td>고점 근접</td><td>~85% of 52w high</td></tr>
</table>
<p><b>Breaker:</b> WTS 입찰 급감 · 백로그 취소/재협상 · 강재·무역비용 급등 · IIJA/SRF 집행 장기 지연</p>

<h2>5. 포트폴리오 위치</h2>
{fig_block(charts['10'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>역할</td><td><b>미보유 · 관망</b> (Chase 하·과열)</td></tr>
  <tr><td>신규</td><td><b>추격 금지</b> — PT 프리미엄·실적 D-수일</td></tr>
  <tr><td>관심 조건</td><td>07-29 실적 후 · PT 재설정 · <b>$100–110</b>대 눌림 시에만 재검토</td></tr>
  <tr><td>하지 말 것</td><td>NEO/AMRX 이벤트 예산으로 NWPX 추격 · CRDO와 동시 과확장</td></tr>
</table>
<div class="easy"><b>한줄 결론:</b> 사업(물 인프라·백로그·Beat)은 탄탄.
지금 가격은 <b>이미 좋은 뉴스를 많이 반영</b>. 소액 포트에서는 패스하고, NEO 실적·현금 버퍼가 우선.</div>

<h2>부록 · 출처</h2>
<p class="small">
NWPX FY2025 earnings (2026-02-25) · Q1 FY2026 earnings (2026-04-29) · 10-Q backlog recognition ·
yfinance 가격·PT·EPS surprise ({ASOF}).
민감도 지수는 입찰 선형 예시(공식 가이던스 아님). 투자 권유 아님.
</p>
<p class="small">생성: 수익구조분석() · 티커 NWPX · 기준 {ASOF} · WeasyPrint + NanumGothic</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_backlog(),
        "04": chart_quarterly(),
        "05": chart_margins(),
        "06": chart_tam_funnel(),
        "07": chart_sensitivity(),
        "08": chart_scenarios(),
        "09": chart_eps_surprise(),
        "10": chart_position(),
    }
    html = build_html(charts)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    doc = HTML(filename=str(OUT_HTML))
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        doc.write_pdf(str(p))
        print(f"PDF {p} {p.stat().st_size}")


if __name__ == "__main__":
    main()
