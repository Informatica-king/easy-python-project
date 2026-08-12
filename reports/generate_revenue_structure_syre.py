#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(SYRE) — Spyre Therapeutics · IBD/류마티스 장기항체 · WeasyPrint PDF."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sepa.artifacts import print_release_result, publish_github_release_asset  # noqa: E402
from sepa.rev_price_chart import build_and_insert_price  # noqa: E402

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from weasyprint import HTML

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
ASOF = "2026-08-12"
PX = 102.74
PT = 122.14
H52 = 108.14
L52 = 14.51
UPSIDE = PT / PX - 1.0
NEAR_HI = PX / H52
MCAP_B = 9.06
EARN = "2026-11-03"
OUT_PDF = [
    Path("/opt/cursor/artifacts/SYRE_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/SYRE_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/SYRE_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/SYRE_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/syre")
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
    "bio": "#7c3aed",
    "pink": "#be185d",
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
        (0.1, 0.7, 1.75, 1.6, "장기 반감기\n항체 플랫폼", C["sand"]),
        (2.05, 0.7, 1.8, 1.6, "α4β7·TL1A\n·IL-23", C["bio"]),
        (4.05, 0.7, 1.85, 1.6, "SKYLINE UC\n+ SKYWAY RD", C["teal"]),
        (6.1, 0.7, 1.75, 1.6, "콤보\n(Part B)", C["gold"]),
        (8.05, 0.7, 1.7, 1.6, "승인 후\n제품매출", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = "white" if c in (C["bio"], C["teal"], C["navy"], C["gold"]) else C["ink"]
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.5, color=tc)
    for x in (1.95, 3.95, 5.95, 7.9):
        ax.annotate(
            "", xy=(x + 0.08, 1.5), xytext=(x - 0.08, 1.5),
            arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6),
        )
    ax.set_title("가치 사슬 — 타깃 항체 → Ph2 플랫폼 → 콤보 → (미실현) 상업화",
                 fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_revenue_today() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9))
    ax = axes[0]
    labels = ["제품·협업\n영업매출", "레거시\n마일스톤 이익", "이자수익\n(Q2'26)"]
    vals = [0.15, 40.0, 10.1]  # visual floor for zero product
    colors = [C["sand"], C["gold"], C["teal"]]
    bars = ax.bar(labels, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("현재 ‘돈’의 성격 (Q2'26)", fontproperties=PROP_B, fontsize=11)
    ax.text(0, 1.5, "실질 $0", ha="center", fontproperties=PROP, fontsize=8, color=C["muted"])
    ax.text(1, 42.5, "$40M\n(pegzilarginase)", ha="center", fontproperties=PROP, fontsize=7.5)
    ax.text(2, 11.5, "$10.1M", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 52)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)

    ax = axes[1]
    # H1'26 sources of non-product cash-like P&L
    sizes = [70, 17.0]
    labs = ["레거시 마일스톤\n이익 H1 $70M", "이자수익\nH1 ~$17M"]
    ax.pie(
        sizes, labels=labs, colors=[C["gold"], C["teal"]], startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("H1'26 — 영업매출 아닌 손익 항목", fontproperties=PROP_B, fontsize=11)
    fig.suptitle("수익구조의 실체: 제품 $0 · 일회성 레거시 + 현금이자",
                 fontproperties=PROP_B, fontsize=12, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_today.png")


def chart_future_stack() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.3)
    ax.axis("off")
    layers = [
        (0.3, 3.2, 9.4, 0.85, C["navy"], "white",
         "④ 제품 매출 (미승인) — IBD·류마티스 상업화 · 콤보 프리미엄 가정"),
        (0.3, 2.25, 9.4, 0.8, C["teal"], "white",
         "③ 파트너 딜 (잠재) — 지역 라이선스 upfront·마일스톤·로열티 (아직 핵심 딜 없음)"),
        (0.3, 1.3, 9.4, 0.8, C["gold"], C["ink"],
         "② 레거시 마일스톤 — pegzilarginase/PRV 관련 일회성 (Q1–Q2'26 합 $70M)"),
        (0.3, 0.35, 9.4, 0.8, C["bio"], "white",
         "① 이자수익 — 현금~$1.15B 운용 · Q2'26 $10.1M (본업 아님)"),
    ]
    for x, y, w, h, c, tc, t in layers:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.0, color=tc)
    ax.set_title("미래 수익 스택 (아래→위 = 현재→장기)", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "03_future_stack.png")


def chart_pipeline() -> Path:
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.4)
    ax.axis("off")
    stages = ["Discovery", "IND", "Ph1", "Ph2", "Ph3", "Market"]
    for i, s in enumerate(stages):
        ax.text(0.8 + i * 1.5, 5.05, s, ha="center", fontproperties=PROP_B, fontsize=8, color=C["muted"])
        ax.plot([0.8 + i * 1.5, 0.8 + i * 1.5], [0.25, 4.8], color="#e7e5e4", lw=0.8)

    programs = [
        (3.9, "SPY001 α4β7 (UC)", "SKYLINE Part A 양성 · Part B 진행", C["bio"], 4),
        (3.9, "SPY002 TL1A (UC)", "SKYLINE Part A 양성 · Part B 진행", C["teal"], 3),
        (3.5, "SPY003 IL-23 (UC)", "Part A 유도 데이터 목표 3Q'26", C["teal2"], 2),
        (3.5, "콤보 SPY120/130/230", "Part B · 유도 데이터 2027", C["gold"], 1),
        (3.5, "SPY072 TL1A (RD)", "SKYWAY 등록完 · RA~9월 · PsA/axSpA 4Q", C["pink"], 0),
    ]
    for x_end, name, note, color, row in programs:
        y = 0.4 + row * 0.85
        ax.add_patch(
            FancyBboxPatch(
                (0.35, y), x_end + 0.9, 0.7,
                boxstyle="round,pad=0.02,rounding_size=0.08",
                facecolor=color, edgecolor="white", lw=1.2, alpha=0.92,
            )
        )
        tc = C["ink"] if color in (C["gold"], C["teal2"]) else "white"
        ax.text(0.55, y + 0.42, name, ha="left", va="center", fontproperties=PROP_B, fontsize=8.2, color=tc)
        ax.text(0.55, y + 0.14, note, ha="left", va="center", fontproperties=PROP, fontsize=6.8, color=tc)
    ax.set_title("파이프라인 — IBD 플랫폼(SKYLINE) + 류마티스 바스켓(SKYWAY)",
                 fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "04_pipeline.png")


def chart_opex_cash() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    qtrs = ["Q2'25", "Q3'25", "Q4'25", "Q1'26", "Q2'26"]
    rd = [40.1, 45.2, 44.6, 60.4, 65.5]
    ga = [11.8, 11.6, 12.5, 15.2, 16.1]
    x = range(len(qtrs))
    ax.bar(x, rd, color=C["bio"], label="R&D", width=0.55)
    ax.bar(x, ga, bottom=rd, color=C["slate"], label="G&A", width=0.55)
    ax.set_xticks(list(x))
    ax.set_xticklabels(qtrs, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("분기 OpEx — Ph2 가속 = 소진 가속", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8)

    ax = axes[1]
    labels = ["3/31'26\npro forma*", "6/30'26\n실측"]
    cash = [1200, 1145]
    bars = ax.bar(labels, cash, color=[C["teal"], C["navy"]], width=0.5)
    ax.set_ylabel("현금+유가증권 (M)", fontproperties=PROP)
    ax.set_title("현금 · 런웨이 목표 2H'29", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, cash):
        ax.text(b.get_x() + b.get_width() / 2, v + 25, f"{v:.0f}",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.text(0.02, -0.28, "*회사 발표: 3/31 pro forma ~$1.2B (4월 증자 $435M net 반영)",
            transform=ax.transAxes, fontproperties=PROP, fontsize=7, color=C["muted"])
    ax.set_ylim(0, 1450)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "05_opex_cash.png")


def chart_burn_vs_gain() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    cats = ["Q2 OpEx\n(R&D+G&A)", "Q2 영업\n현금유출", "Q2 레거시\n이익", "Q2 이자", "시총\n(~$9.1B)"]
    vals = [81.6, 69.9, 40.0, 10.1, 150]  # mcap visual compress
    colors = [C["red"], C["pink"], C["gold"], C["teal"], C["navy"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD (시총은 축 압축)", fontproperties=PROP)
    ax.set_title("소진 vs 일회성 이익 vs 시총 감각", fontproperties=PROP_B, fontsize=11)
    labels_v = ["81.6", "69.9", "40", "10.1", "~9,060"]
    for b, lab in zip(bars, labels_v):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 4, lab,
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 180)
    ax.text(0.02, -0.22, "시총 막대는 스케일 비교용(실제 ~$9.1B). 제품매출 $0 상태에서 밸류가 이미 큼.",
            transform=ax.transAxes, fontproperties=PROP, fontsize=7, color=C["muted"])
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "06_burn_vs_gain.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [35, 85, 130]
    highs = [65, 125, 170]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    ax.axvline(PX, color=C["gold"], ls="--", lw=1.5)
    ax.text(PX + 2, 2.35, f"현재 ~{PX:.0f}", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.axvline(PT, color="#2563eb", ls=":", lw=1.2)
    ax.text(PT + 2, -0.55, f"PT평균 ~{PT:.0f}", fontproperties=PROP, fontsize=7.5, color="#2563eb")
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        mid = (lo + hi) / 2
        ax.text(mid, i, f"{lo}–{hi}", ha="center", va="center", color="white",
                fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(20, 185)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear (12M · 임상·자금 중심)", fontproperties=PROP_B, fontsize=11)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP_B)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.1)
    ax.axis("off")
    items = [
        (0.2, 2.55, 3.1, 1.25, C["pink"], "white", "2026-09\nSPY072 RA PoC"),
        (3.45, 2.55, 3.1, 1.25, C["bio"], "white", "3Q'26\nSPY003 UC 유도"),
        (6.7, 2.55, 3.1, 1.25, C["teal"], "white", "4Q'26\nPsA·axSpA PoC"),
        (0.2, 0.35, 4.7, 1.7, C["gold"], C["ink"], "2027\nSKYLINE Part B\n콤보·용량 데이터"),
        (5.15, 0.35, 4.65, 1.7, C["sand"], C["ink"], "다음 실적\n~2026-11-03\n(Rev 컨센 $0)"),
    ]
    for x, y, w, h, c, tc, t in items:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=9, color=tc)
    ax.set_title("촉매 캘린더 — 주가·가치는 Ph2 이벤트가 지배", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.1)
    ax.axis("off")
    rows = [
        (0.3, 2.7, 9.4, 1.05, C["navy"], "white",
         "포트 역할: 미보유 · 심층 A′ 후보 · Chase 중하(고점 95%) · 추격 금지"),
        (0.3, 1.45, 4.5, 1.0, C["teal"], "white", "관심 금액\n최대 C급 극소(≤1주 감각)"),
        (5.0, 1.45, 4.7, 1.0, C["gold"], C["ink"], "타이밍\nRA PoC·눌림 후 재평가"),
        (0.3, 0.25, 9.4, 1.0, C["sand"], C["ink"],
         "지금: 제품매출 $0 · 시총~$9B · 임상 바이너리 · 계좌 현금·보유주 우선"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.8, color=tc)
    ax.set_title("실행 포지션 맵 (사용자 계좌 기준)", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "09_position.png")


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
      @bottom-center {{ content:"SYRE 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #7c3aed; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#7c3aed; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#f5f3ff 0%,#e8eef5 55%,#fdf2f8 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#ddd6fe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.good {{ background:#bbf7d0; }}
    .tag.bad {{ background:#fecdd3; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#f5f3ff; border-left:4px solid #7c3aed; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#7c3aed; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#7c3aed; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>SYRE 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>SYRE 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Spyre Therapeutics · 장기 반감기 항체 · IBD &amp; 류마티스</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적(8/5) · 다음 실적 ~{EARN} · 임상단계</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.0f}</div><div class="s">시총 ~${MCAP_B:.1f}B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.0f}</div><div class="s">업사이드 {UPSIDE*100:+.0f}%</div></span>
    <span class="kpi"><div class="l">영업매출</div><div class="v">$0</div><div class="s">제품·협업 없음</div></span>
    <span class="kpi"><div class="l">현금</div><div class="v">$1.15B</div><div class="s">런웨이 2H'29</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">심층 A′ · 기술적 후보</span>
    <span class="tag warn">Chase 중하 · 고점 {NEAR_HI*100:.0f}%</span>
    <span class="tag bad">제품매출 없음 · 임상 바이너리</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>약 팔아서 버는 회사가 아니라, IBD·류마티스 Ph2 성공 옵션에 ~$9B 시총을 붙인 회사.</b>
최근 5분기 <b>Total Revenue $0</b>. 손익을 완화한 것은
레거시(pegzilarginase) 마일스톤 이익(H1'26 <b>$70M</b>)과 이자(~$17M)다.
본업 현금은 <b>R&amp;D 소진</b>이고, 기업가치는
<b>SPY001/002 양성 후속 · SPY003 · SPY072 RA/PsA</b> 데이터에 연동한다.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 재무제표에 ‘매출’이 거의 없다.
보이는 큰 숫자는 <b>옛날 자산 잔여 마일스톤</b>이거나 <b>예금 이자</b>다.
진짜 수익구조는 <u>약이 승인·판매된 뒤</u>에야 생긴다.</div>
{gloss([
    ("임상단계 (clinical-stage)", "승인·상업화 전 — 제품매출 없이 개발비로 적자."),
    ("IBD", "염증성 장질환(궤양성 대장염·크론). Spyre의 핵심 적응증."),
    ("장기 반감기 항체", "투여 간격을 늘리도록 개량한 항체 — 편의·지속 효능 스토리."),
])}

<h2>1. 어디서 돈이 오나 — 지금 vs 나중</h2>
{fig_block(charts['02'], '현재 현금성 손익')}
{fig_block(charts['03'], '미래 수익 스택')}
<table>
  <tr><th>수익원</th><th>상태</th><th>규모·조건</th></tr>
  <tr><td>제품(처방약) 매출</td><td>없음</td><td>승인 전 · 분기 Total/Operating Revenue <b>$0</b></td></tr>
  <tr><td>협업·라이선스 매출</td><td>핵심 없음</td><td>주요 지역 딜 upfront 인식 사례 없음 (RAPP형 딜과 구분)</td></tr>
  <tr><td>레거시 마일스톤 이익</td><td>일회성</td><td>Q1'26 $30M + Q2'26 $40M = H1 <b>$70M</b> (pegzilarginase/PRV)</td></tr>
  <tr><td>이자수익</td><td>있음</td><td>Q2'26 <b>$10.1M</b> · H1 ~$17M · 현금·유가증권 운용</td></tr>
  <tr><td>미래 제품·딜</td><td>미실현</td><td>Ph2→pivotal→승인 후 · 콤보 차별화 가정</td></tr>
</table>
<p class="small">레거시 이익은 구 Aeglea/pegzilarginase 권리 매각(2023, Immedica) 잔여 마일스톤.
<b>본업 파이프라인 매출이 아니다.</b></p>
<div class="easy"><b>쉽게:</b> 지금은 <b>예금 이자 + 옛 딜 잔금</b>.
앞으로 돈이 되려면 ①Ph2/확증 성공 → ②FDA 등 승인 → ③약 판매(또는 빅파마 딜) 순서다.</div>
{gloss([
    ("Milestone gain", "과거 매각 계약 조건 달성 시 인식하는 일회성 이익. 반복 매출 아님."),
    ("PRV", "Priority Review Voucher — 우선심사권. 매각·이전으로 현금화 가능."),
    ("Royalty/Upfront", "파트너 딜이 생기면 그때부터 협업매출·로열티 스택이 열림."),
])}

<h2>2. 성장 엔진 — 파이프라인</h2>
{fig_block(charts['04'], '파이프라인')}
{fig_block(charts['08'], '촉매')}
<ul>
  <li><b>SPY001 (α4β7)</b> — SKYLINE Part A 유도 양성 · RHI −9.2 · 임상관해 40% · 내시경 개선 51% (회사)</li>
  <li><b>SPY002 (TL1A)</b> — Part A 양성 · RHI −10.7 · 관해 33% · 내시경 42%</li>
  <li><b>SPY003 (IL-23)</b> — Part A 유도 데이터 목표 <b>3Q'26</b></li>
  <li><b>콤보 (SPY120/130/230)</b> — Part B 용량·기여도 · 유도 데이터 <b>2027</b></li>
  <li><b>SPY072 (TL1A, 류마티스)</b> — SKYWAY 등록 완료 · <b>RA ~2026-09</b> · PsA/axSpA <b>4Q'26</b></li>
</ul>
<div class="box"><b>상업 내러티브:</b> 장기 피하투여 + 모노·콤보로 ‘더 완전한 질환 조절’을 주장.
이는 TAM/피크세일즈 가정치이며, <u>현재 손익계산서에 들어오는 숫자가 아님</u>.
시총 ~$9B는 이미 상당 부분의 성공을 선반영한 수준으로 읽힌다.</div>
{gloss([
    ("α4β7", "장 조직 귀소 관련 인테그린. 엔티비오(베돌리주맙)와 같은 계열 타깃."),
    ("TL1A", "염증 사이토카인 경로. IBD·류마티스에서 유망 타깃으로 부상."),
    ("PoC", "Proof-of-Concept — 개념증명. Ph2에서 ‘약효가 있다’는 첫 임상 증거."),
])}

<h2>3. 비용 · 현금 · 희석</h2>
{fig_block(charts['05'], 'OpEx·현금')}
{fig_block(charts['06'], '소진 vs 일회성')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>Q2'26 R&amp;D / G&amp;A</td><td><b>$65.5M</b> / $16.1M (전년 $40.1 / $11.8)</td></tr>
  <tr><td>Q2'26 영업현금유출</td><td><b>$69.9M</b></td></tr>
  <tr><td>Q2'26 순손실</td><td>$36.2M (레거시 이익 $40M으로 축소 · 정규화 손실은 더 큼)</td></tr>
  <tr><td>H1'26 순손실</td><td>$105.2M (전년 H1 $81.5M)</td></tr>
  <tr><td>현금+유가증권 (6/30/26)</td><td><b>$1,145.3M</b></td></tr>
  <tr><td>4월 증자</td><td>순수취 <b>$435.2M</b> · 보통주 78.2M→88.1M (희석)</td></tr>
  <tr><td>런웨이(회사)</td><td><b>2029년 하반기</b>까지 OpEx 충당 예상</td></tr>
  <tr><td>다음 실적</td><td>~<b>{EARN}</b> · Rev 컨센 $0 · 임상 업데이트가 핵심</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 분기 소진(~$70M)은 이자·일회성 이익보다 크다.
진짜 방패는 <b>현금 $1.15B</b>다. 대신 4월 증자로 <b>주식 수가 늘었고</b>,
pivotal로 가면 소진이 더 커질 수 있다.</div>
{gloss([
    ("Runway", "현재 현금으로 적자를 버티는 예상 기간."),
    ("희석", "추가 자금조달로 주식 수가 늘어 기존 지분 가치가 줄어듦."),
    ("정규화 손실", "일회성 이익을 빼면 보이는 ‘본업 적자’ 규모."),
])}

<h2>4. 민감도 · 시나리오</h2>
{fig_block(charts['07'], '주가 시나리오')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>130–170</td><td>SPY072 RA 성공 · SPY003/콤보 스토리 강화 · PT 상향</td></tr>
  <tr><td>Base</td><td>85–125</td><td>혼재 데이터 · PT(~122) 수렴 · 런웨이 유지</td></tr>
  <tr><td>Bear</td><td>35–65</td><td>Ph2 실패·안전성 · TL1A 경쟁 열세 · 대규모 추가 희석</td></tr>
</table>
<p><b>Breaker:</b> SKYWAY RA 실패 · SPY003 미스 · 콤보 기여도 불명 · 안전성 ·
경쟁 TL1A/IBD 자산 우위 · 현금 소진 가속·희석 · 규제 해석 이견</p>
<p class="small">현재가 ${PX:.2f} · 52주 고 ${H52:.2f} (근접 {NEAR_HI*100:.0f}%) · 저 ${L52:.2f} ·
업사이드 {UPSIDE*100:+.1f}% — <b>고점권에서 ‘싸게 산다’ 논리는 약함</b>.</p>
{gloss([
    ("바이너리", "임상 성공/실패가 시총을 크게 흔드는 구조."),
    ("PT 업사이드", "목표가 할인은 분석가 가정의 합 — Ph2 리스크를 과소평가할 수 있음."),
])}

<h2>5. 포트폴리오 위치</h2>
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>역할</td><td>미보유 <b>워치</b> · 심층 A′는 기술적 후보일 뿐 · Chase <b>중하</b></td></tr>
  <tr><td>금액</td><td>관심 시에도 <b>C급 극소(≤1주 감각)</b> · 시총·바이너리 대비 계좌 과대노출 금지</td></tr>
  <tr><td>타이밍</td><td><b>RA PoC(~9월)</b> 또는 고점권 이탈·눌림 확인 후 · 추격 금지</td></tr>
  <tr><td>하지 말 것</td><td>레거시 이익을 본업 매출로 착각 · Ph2 전 풀베팅 · 현금층·보유주 예산 잠식</td></tr>
</table>
<div class="easy"><b>한줄 결론:</b> 수익구조의 실체는 <u>이자 + 레거시 일회성 + 미래 승인 옵션</u>.
Ph2 데이터 스토리는 강하지만, <b>~$9B 시총·고점 95%·제품매출 $0</b>이라
당신 시드에는 <b>공부·워치</b>가 맞고 추격 매수는 아니다.</div>

<h2>부록 · 출처</h2>
<p class="small">
Spyre Q2 2026 earnings release (2026-08-05) · Q1 2026 update (2026-05-05) ·
yfinance 분기 손익·가격·PT ({ASOF}) · 심층분석 2026-08-12 (A′ / Chase 중하).
시나리오는 예시 밴드(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 SYRE · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_revenue_today(),
        "03": chart_future_stack(),
        "04": chart_pipeline(),
        "05": chart_opex_cash(),
        "06": chart_burn_vs_gain(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    html = build_html(charts)
    html, _px = build_and_insert_price("SYRE", CHART_DIR, html)
    if _px.ok:
        print(f"price-charts {_px.candle_path} {_px.momentum_path}")
    else:
        print(f"price-charts SKIP {_px.error}")
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    doc = HTML(filename=str(OUT_HTML))
    pdf_main = None
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        doc.write_pdf(str(p))
        print(f"PDF {p} {p.stat().st_size}")
        if "reports" in str(p):
            pdf_main = p
    if pdf_main is None:
        pdf_main = OUT_PDF[0]

    rel = publish_github_release_asset(
        pdf_main,
        tag="sepa-rev-syre",
        title="SEPA Revenue Structure — SYRE",
        notes=(
            "## 수익구조분석(SYRE) · Spyre Therapeutics\n\n"
            f"임상단계 · 제품매출 $0 · 현금 $1.15B (런웨이 2H'29)\n"
            f"Q2'26 R&D $65.5M · 레거시 마일스톤 이익 $40M · px~${PX:.0f} · PT~${PT:.0f}\n\n"
            f"- 심층 A′ · Chase 중하(고점 {NEAR_HI*100:.0f}%)\n"
            "- 포트: 미보유 워치 · 추격 금지 · RA PoC/눌림 후 재평가\n"
        ),
    )
    print_release_result(rel, label="SYRE 수익구조 PDF")
    print(f"SYRE rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% near_hi={NEAR_HI*100:.0f}%")


if __name__ == "__main__":
    main()
