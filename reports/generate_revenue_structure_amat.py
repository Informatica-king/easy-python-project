#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(AMAT) — 웨이퍼팹 장비·서비스 매출구조 + 초보용 설명 + WeasyPrint PDF."""

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
ASOF = "2026-07-24"
OUT_PDF = [
    Path("/opt/cursor/artifacts/AMAT_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/AMAT_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/AMAT_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/AMAT_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/amat")
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
        (0.1, 0.7, 1.75, 1.6, "AI CapEx\n·WFE 수요", C["sand"]),
        (2.05, 0.7, 1.8, 1.6, "재료공학\n장비 R&D", C["gold"]),
        (4.05, 0.7, 1.8, 1.6, "Semiconductor\nSystems", C["teal2"]),
        (6.05, 0.7, 1.75, 1.6, "AGS 서비스\n·스페어", C["teal"]),
        (8.0, 0.7, 1.75, 1.6, "팹·고객\n매출", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c,
                edgecolor="white",
                lw=2,
            )
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(
            x + w / 2,
            y + h / 2,
            t,
            ha="center",
            va="center",
            fontproperties=PROP_B,
            fontsize=8.5,
            color=tc,
        )
    ax.set_title(
        "비즈니스 한눈에 — AI 칩을 만드는 ‘공장 장비·서비스’를 판다",
        fontproperties=PROP_B,
        fontsize=12,
        pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    # Q2 FY26: SS 5965, AGS 1665, Other 280 = 7910
    sizes = [5965, 1665, 280]
    labels = ["Semi Systems\n5.97B (75%)", "AGS\n1.67B (21%)", "Other/Display\n0.28B (4%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["navy"], C["teal"], C["gold"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("보고 세그먼트 (Q2 FY26, 총 7.91B)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["Foundry/\nLogic", "DRAM", "Flash"]
    vals = [67, 29, 4]
    colors = [C["navy"], C["teal"], C["gold"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("% of Semiconductor Systems", fontproperties=PROP)
    ax.set_title("SS 최종시장 믹스 (Q2 FY26)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 1.5,
            f"{v}%",
            ha="center",
            fontproperties=PROP_B,
            fontsize=10,
        )
    ax.set_ylim(0, 85)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_growth_engines() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    cats = [
        "CY26 Semi\n장비 YoY",
        "Adv.\nPackaging",
        "SS 성장의\n핵심 3축*",
        "AGS\n장기",
    ]
    vals = [30, 50, 80, 15]
    colors = [C["navy"], C["teal"], C["gold"], C["slate"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("% (가이드/코멘트)", fontproperties=PROP)
    ax.set_title("성장 엔진 — 경영진 코멘트 요약 (캘린더 2026)", fontproperties=PROP_B, fontsize=12)
    labels = [">30%", ">50%", ">80%*", "중십대%"]
    for b, lab in zip(bars, labels):
        ax.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 2,
            lab,
            ha="center",
            fontproperties=PROP,
            fontsize=9,
        )
    ax.set_ylim(0, 100)
    ax.text(
        0.02,
        -0.18,
        "* Leading-edge foundry/logic + DRAM + advanced packaging = WFE YoY 성장의 >80%",
        transform=ax.transAxes,
        fontproperties=PROP,
        fontsize=7.5,
        color=C["muted"],
    )
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "03_growth.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    qs = ["Q2-25", "Q3-25", "Q4-25", "Q1-26", "Q2-26", "Q3-26g"]
    rev = [7.10, 7.30, 6.80, 7.01, 7.91, 8.95]
    colors = [C["slate"]] * 4 + [C["navy"], C["teal2"]]
    bars = ax.bar(qs, rev, color=colors, width=0.58)
    ax.set_ylabel("매출 (십억 USD)", fontproperties=PROP)
    ax.set_title("분기 매출 — Q2 기록 7.91B · Q3 가이던스 8.95B±0.5", fontproperties=PROP_B, fontsize=12)
    for b, v in zip(bars, rev):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 0.15,
            f"{v:.2f}",
            ha="center",
            fontproperties=PROP,
            fontsize=8,
        )
    ax.errorbar(5, 8.95, yerr=0.5, fmt="none", ecolor=C["teal"], capsize=4, lw=1.2)
    ax.set_ylim(0, 10.5)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "04_quarterly.png")


def chart_margins() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6))
    ax = axes[0]
    cats = ["FY24", "FY25", "Q2-26"]
    gm = [47.5, 48.7, 49.9]
    bars = ax.bar(cats, gm, color=[C["slate"], C["teal"], C["navy"]], width=0.5)
    ax.set_ylabel("GAAP GM %", fontproperties=PROP)
    ax.set_title("매출총이익률", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, gm):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 0.3,
            f"{v}%",
            ha="center",
            fontproperties=PROP,
            fontsize=9,
        )
    ax.set_ylim(40, 55)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    cats = ["SS GM\nQ2-26", "AGS GM\nQ2-26", "nGAAP EPS\nQ2 / Q3g"]
    # SS GM 54.7%, AGS 34.7%; show as bars for margins; EPS separate scale — use twin conceptually via labels
    vals = [54.7, 34.7, 50.0]  # last is company nGAAP GM for visual anchor
    colors = [C["navy"], C["teal"], C["gold"]]
    bars = ax.bar(["SS GM", "AGS GM", "전사 nGAAP\nGM"], [54.7, 34.7, 50.0], color=colors, width=0.5)
    ax.set_ylabel("%", fontproperties=PROP)
    ax.set_title("세그먼트 마진 (Q2 FY26)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, [54.7, 34.7, 50.0]):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 1,
            f"{v}%",
            ha="center",
            fontproperties=PROP,
            fontsize=9,
        )
    ax.set_ylim(0, 70)
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
        (0.4, 3.9, 9.2, 0.85, C["sand"], C["ink"], "글로벌 WFE / AI 인프라 CapEx (산업 수요)"),
        (0.9, 2.85, 8.2, 0.85, C["gold"], C["ink"], "Leading-edge Logic · DRAM · Adv. Packaging (>80% of YoY)"),
        (1.5, 1.8, 7.0, 0.85, C["teal2"], C["ink"], "AMAT Semiconductor Systems (재료공학 장비)"),
        (2.2, 0.75, 5.6, 0.85, C["navy"], "white", "설치 기반 → AGS 서비스·스페어 (반복 매출)"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor=c,
                edgecolor="white",
                lw=1.5,
            )
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("수요 깔때기 — WFE → 선단 장비 → 설치 후 서비스", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "06_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    # Illustrative: SS annualized from Q2 run-rate ~23.9B; shock vs CY26 +30% guide narrative
    shocks = ["WFE -15%", "WFE -5%", "기준(+30%)", "WFE +5%", "WFE +15%"]
    base = 23.9 * 1.30  # rough CY26 SS-like if +30% on ~Q2 run-rate annualized — illustrative
    # Better: use conceptual index 100 = guide path
    vals = [100 * x for x in (0.85, 0.95, 1.0, 1.05, 1.15)]
    colors = [C["red"], "#ea580c", C["slate"], C["teal"], C["navy"]]
    bars = ax.bar(shocks, vals, color=colors, width=0.55)
    ax.set_ylabel("Semi 장비 매출 지수 (기준=100)", fontproperties=PROP)
    ax.set_title("민감도 — CY26 Semi 장비 경로 vs WFE 충격 (예시)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 1.5,
            f"{v:.0f}",
            ha="center",
            fontproperties=PROP,
            fontsize=8,
        )
    ax.set_ylim(0, 130)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "07_sensitivity.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [400, 560, 700]
    highs = [480, 680, 900]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    ax.axvline(562.8, color=C["gold"], ls="--", lw=1.5)
    ax.text(568, 2.35, "현재 ~563", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.axvline(623, color="#2563eb", ls=":", lw=1.2)
    ax.text(628, -0.55, "PT평균 ~623", fontproperties=PROP, fontsize=7.5, color="#2563eb")
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        mid = (lo + hi) / 2
        ax.text(mid, i, f"{lo}–{hi}", ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(320, 980)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear (12M 관점)", fontproperties=PROP_B, fontsize=11)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP_B)
    fig.tight_layout()
    return save_fig(fig, "08_scenarios.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    qs = ["Q3-25", "Q4-25", "Q1-26", "Q2-26"]
    surp = [5.1, 3.7, 7.9, 6.5]
    bars = ax.bar(qs, surp, color=C["green"], width=0.55)
    ax.set_ylabel("EPS 서프라이즈 %", fontproperties=PROP)
    ax.set_title("최근 4분기 Non-GAAP EPS 서프라이즈", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, surp):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 0.25,
            f"+{v:.1f}%",
            ha="center",
            fontproperties=PROP,
            fontsize=9,
        )
    ax.set_ylim(0, 12)
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
        (0.3, 2.6, 9.4, 1.0, C["navy"], "white", "포트 역할: ASTH 대체 워치 · AI 장비 테마 소액 (CRDO와 택1/병행)"),
        (0.3, 1.4, 4.5, 0.95, C["teal"], "white", "권장 금액\n60–80 USD"),
        (5.0, 1.4, 4.7, 0.95, C["gold"], C["ink"], "타이밍\nNEO(07-28) 이후"),
        (0.3, 0.25, 9.4, 0.95, C["sand"], C["ink"], "훅: NO_ADD until NEO · TA 분할OK · 추격 자제 (PT 프리미엄 ~11%)"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor=c,
                edgecolor="white",
                lw=1.5,
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
      @bottom-center {{ content:"AMAT 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0f766e; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0f766e; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#f0f7f6 0%,#e8eef5 55%,#f7f3e8 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#dbeafe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#f0fdfa; border-left:4px solid #0f766e; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0f766e; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:110px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#0f766e; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>AMAT 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>AMAT 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Applied Materials · 반도체 웨이퍼팹 장비 · AGS 서비스</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2 FY26(종료 2026-04-26) + Q3 가이던스</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~$563</div><div class="s">시총 ~$447B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~$623</div><div class="s">+~11%</div></span>
    <span class="kpi"><div class="l">Q2 매출</div><div class="v">$7.91B</div><div class="s">기록 · +11% YoY</div></span>
    <span class="kpi"><div class="l">Q3 가이던스</div><div class="v">$8.95B</div><div class="s">±$0.5B</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">CY26 Semi 장비 &gt;+30%</span>
    <span class="tag">Packaging &gt;+50%</span>
    <span class="tag warn">포트: NEO 이후 60–80 USD · NO_ADD</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>AI 인프라 → 선단 로직·DRAM·첨단패키징 장비</b>의 본류. Q2 FY26 기록 매출 $7.91B,
Semiconductor Systems 75%(Foundry/Logic 67% · DRAM 29%). 경영진은 <b>캘린더 2026 Semi 장비 &gt;+30%</b>,
패키징 &gt;+50%를 제시. 당신 계좌에서는 ASTH 대체 <b>워치 · NEO(07-28) 이후 소액 60–80</b>
(CRDO와 택1/소액 병행), 지금은 <b>NO_ADD</b>.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> NVIDIA·TSMC가 AI 칩을 ‘만들려면’ 공장에 장비가 필요함.
AMAT는 그 공장에 들어가는 <b>재료공학 장비</b>와, 설치 후 <b>유지·스페어 서비스</b>를 판다.</div>
{gloss([
    ("WFE", "Wafer Fab Equipment — 웨이퍼 공장(팹)에 들어가는 반도체 제조 장비 시장."),
    ("Semiconductor Systems", "AMAT의 장비 판매 세그먼트(매출의 대부분)."),
    ("AGS", "Applied Global Services — 설치 기반에 대한 서비스·스페어·소프트웨어."),
    ("재료공학", "증착·식각·CMP 등으로 칩 구조·박막을 만드는 공정 기술."),
])}

<h2>1. 어디서 돈이 오나 — 세그먼트 · 최종시장</h2>
{fig_block(charts['02'], '세그먼트 + SS 최종시장 믹스')}
<table>
  <tr><th>세그먼트 (Q2 FY26)</th><th>매출</th><th>비중</th><th>GM / OM</th><th>YoY</th></tr>
  <tr><td>Semiconductor Systems</td><td>$5.97B</td><td>75%</td><td>GM 54.7% / OM 35.1%</td><td>+10%</td></tr>
  <tr><td>Applied Global Services</td><td>$1.67B</td><td>21%</td><td>GM 34.7% / OM 29.2%</td><td>+17%</td></tr>
  <tr><td>Other (Display 등)</td><td>$0.28B</td><td>4%</td><td>OI −$56M</td><td>~flat</td></tr>
  <tr><td><b>합계</b></td><td><b>$7.91B</b></td><td>100%</td><td>전사 GM 49.9%</td><td><b>+11%</b></td></tr>
</table>
<table>
  <tr><th>SS 최종시장</th><th>Q2 FY26</th><th>Q2 FY25</th><th>FY25 (연간)</th></tr>
  <tr><td>Foundry / Logic / Other</td><td>67%</td><td>66%</td><td>67%</td></tr>
  <tr><td>DRAM</td><td>29%</td><td>27%</td><td>26%</td></tr>
  <tr><td>Flash (NAND)</td><td>4%</td><td>7%</td><td>7%</td></tr>
</table>
<p class="small">FY25 연간: 총매출 <b>$28.37B (+4%)</b> · SS $20.80B · AGS $6.39B · Corp/Other $1.19B.
FY25 고객 집중: 상위 2고객이 각각 ~19% · ~15% of net revenue.</p>
<div class="easy"><b>쉽게:</b> 돈의 75%는 ‘새 장비 판매’, 21%는 ‘이미 깔린 장비의 유지보수’.
장비 쪽은 <b>선단 로직 + DRAM</b>이 거의 전부, NAND(플래시) 비중은 작다.</div>
{gloss([
    ("Foundry", "TSMC 같은 위탁생산 팹. AI/로직 칩 생산의 핵심."),
    ("Logic", "연산용 반도체(CPU·GPU·SoC 등). Gate-All-Around(GAA) 전환이 장비 수요."),
    ("DRAM / HBM", "메모리. AI 서버용 HBM·고대역 메모리 증설이 DRAM 장비 수요."),
    ("Flash", "NAND 플래시. 현재 AMAT SS 믹스에서는 비중이 낮음."),
    ("GM / OM", "매출총이익률 / 영업이익률."),
])}

<h2>2. 성장 엔진 — AI · 패키징 · 서비스</h2>
{fig_block(charts['03'], 'CY26 성장 코멘트')}
{fig_block(charts['06'], '수요 깔때기')}
<ul>
  <li><b>캘린더 2026 Semi 장비 사업 &gt;30%</b> (경영진, Q2 실적)</li>
  <li><b>Advanced packaging</b> 매출 &gt;+50% (CY26) — panel-level·3D 적층, NEXX(ASMPT) 인수 추진</li>
  <li>Leading-edge foundry/logic + DRAM + packaging = <b>WFE YoY 성장의 &gt;80%</b></li>
  <li><b>AGS</b> 장기 성장 mid-teens 상향, 이용률·신규 팹 램프 시 더 높을 수 있음</li>
  <li>EPIC Center: TSMC·SK hynix·Micron·Samsung 등과 공동 R&amp;D (차세대 재료·공정)</li>
</ul>
<div class="easy"><b>쉽게:</b> AI가 ‘칩’만 키우는 게 아니라, 칩을 더 쌓고(패키징)·더 미세하게(GAA) 만들게 함.
AMAT는 그 두 전환의 장비 쪽 수혜 + 설치 후 서비스 반복매출.</div>
{gloss([
    ("Advanced packaging", "칩을 2.5D/3D로 쌓거나 큰 패널에 올려 AI 가속기 성능을 올리는 후공정."),
    ("GAA", "Gate-All-Around — 차세대 트랜지스터 구조. 원자층 증착(ALD) 등 장비 수요."),
    ("ICAPS", "IoT/통신/자동차/전력/센서 등 비선단·레거시 장비 수요 묶음."),
    ("EPIC Center", "AMAT의 공동 혁신 허브(실리콘밸리). 고객·파트너와 공정 상용화 가속."),
])}

<h2>3. 분기 궤적 · 마진 · 가이던스</h2>
{fig_block(charts['04'], '분기 매출')}
{fig_block(charts['05'], '마진')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>Q2 FY26 매출 / YoY</td><td>$7.91B / +11% (기록)</td></tr>
  <tr><td>GAAP / Non-GAAP EPS</td><td>$3.51 / $2.86 (+33% / +20% YoY)</td></tr>
  <tr><td>Non-GAAP GM / OM</td><td>50.0% / 32.1%</td></tr>
  <tr><td>Q3 FY26 가이던스</td><td>매출 <b>$8.95B ± $0.5B</b> · nGAAP EPS <b>$3.36 ± $0.20</b></td></tr>
  <tr><td>Q3 세그먼트 가이드(코멘트)</td><td>SS ~$6.9B · AGS ~$1.75B · Other ~$0.3B</td></tr>
  <tr><td>H1 FY26 매출</td><td>$14.92B (Q1 $7.01B + Q2 $7.91B)</td></tr>
  <tr><td>주주환원 (Q2)</td><td>자사주 $400M + 배당 $365M · 분기배당 $0.46→$0.53 (+15%)</td></tr>
</table>
{fig_block(charts['09'], 'EPS 서프라이즈')}
<div class="box"><b>해석:</b> Beat는 꾸준하지만 MU급 ‘폭증’은 아님(+4~8%대).
업사이드는 <b>CY26 장비 +30% 경로 실현</b>과 패키징 점유.
리스크는 중국/수출규제·관세·고객 CapEx 지연·상위고객 집중.</div>
{gloss([
    ("Non-GAAP EPS", "인수·세금·일회성 등 조정 후 주당순이익. 시장이 주로 보는 숫자."),
    ("가이던스", "회사가 다음 분기에 제시하는 매출·EPS 예상 범위."),
    ("Beat", "컨센서스보다 좋은 실적."),
])}

<h2>4. 민감도 · 시나리오 · 밸류</h2>
{fig_block(charts['07'], 'WFE 민감도')}
{fig_block(charts['08'], '주가 시나리오')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>700–900</td><td>CY26 +30%+ 실현 · 패키징/GAA 점유 확대 · 가이던스 재상향</td></tr>
  <tr><td>Base</td><td>560–680</td><td>PT(~623) 수렴 · 성장 지속하나 멀티플 확대 제한</td></tr>
  <tr><td>Bear</td><td>400–480</td><td>WFE 둔화 · 수출규제/관세 · 대형 고객 CapEx 이연</td></tr>
</table>
<table>
  <tr><th>밸류 스냅샷 ({ASOF})</th><th>수치</th></tr>
  <tr><td>현재가 / PT평균 / PT고</td><td>~$563 / ~$623 (+11%) / ~$900</td></tr>
  <tr><td>Trailing / Forward P/E</td><td>~52 / ~33</td></tr>
  <tr><td>52주</td><td>154 – 740</td></tr>
  <tr><td>애널리스트</td><td>Strong Buy 성향 · ~35명</td></tr>
</table>
<p><b>Breaker:</b> Semi 장비 가이던스 하향 · 중국 매출 급감 · TSMC/메모리 고객 CapEx 동결 · 대형 M&amp;A 차질</p>
{gloss([
    ("CapEx", "팹·장비 설비투자. 고객(파운드리·메모리)의 CapEx가 AMAT 주문의 원천."),
    ("멀티플", "이익·매출 대비 주가 배수(P/E 등)."),
    ("수출규제", "첨단 장비의 특정 지역 판매 제한 — 매출·가이던스 리스크."),
])}

<h2>5. 포트폴리오 위치</h2>
{fig_block(charts['10'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>역할</td><td>ASTH 대체 <b>워치</b> · AI 웨이퍼팹 장비 테마 (CRDO와 택1/소액 병행)</td></tr>
  <tr><td>금액</td><td><b>60–80 USD</b> (현금 버퍼 유지 후)</td></tr>
  <tr><td>타이밍</td><td><b>NEO 07-28 이후</b> · 그 전 NO_ADD</td></tr>
  <tr><td>TA</td><td>심층분석 Chase 후 자동 TA <b>분할OK</b> (CRDO·SLS와 함께)</td></tr>
  <tr><td>하지 말 것</td><td>PT 프리미엄만 보고 추격 · NEO 이벤트 예산 잠식 · SLS 바이너리와 동시 과집중</td></tr>
</table>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>선단 로직·DRAM 장비 + AGS 반복매출</u>로 AI CapEx에 정면 노출.
계좌에는 <b>NEO 이후 소액</b>으로만. 밸류는 PT +11%로 ‘싸다’기보다 <b>성장 지속 여부</b>가 핵심.</div>

<h2>부록 · 출처</h2>
<p class="small">
Applied Materials Q2 FY2026 earnings release (2026-05-14, Exhibit 99.1) ·
FY2025 year-end release (2025-11-13) · IR 코멘트(CY26 semi equipment &gt;30%, packaging &gt;50%) ·
yfinance 가격·PT·EPS surprise ({ASOF}).
민감도 지수는 WFE 충격 선형 예시(공식 가이던스 아님). 투자 권유 아님.
</p>
<p class="small">생성: 수익구조분석() · 티커 AMAT · 기준 {ASOF} · WeasyPrint + NanumGothic</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_growth_engines(),
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
