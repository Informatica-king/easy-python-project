#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(VSAT) — Viasat · Comm Services / DAT + VS-3 · WeasyPrint PDF."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sepa.artifacts import print_release_result, publish_github_release_asset  # noqa: E402
from sepa.rev_compete import (  # noqa: E402
    build_compete_charts,
    render_compete_section_html,
)
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
PX = 84.52
PT = 101.44
H52 = 93.03
L52 = 25.50
UPSIDE = PT / PX - 1.0
NEAR_HI = PX / H52
MCAP_B = 11.64
EARN = "2026-08-04"  # Q1 FY27 reported
OUT_PDF = [
    Path("/opt/cursor/artifacts/VSAT_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/VSAT_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/VSAT_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/VSAT_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/vsat")
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
    "sky": "#0369a1",
    "orange": "#c2410c",
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
        (0.1, 0.7, 1.75, 1.6, "위성·지상망\n멀티오빗", C["sand"]),
        (2.05, 0.7, 1.85, 1.6, "Comm Services\n항공·정부·해사", C["sky"]),
        (4.1, 0.7, 1.85, 1.6, "DAT\n방산·사이·전술", C["navy"]),
        (6.15, 0.7, 1.7, 1.6, "VS-3 F2/F3\n용량 확장", C["teal"]),
        (8.05, 0.7, 1.7, 1.6, "FCF·디레버\n+백로그", C["gold"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.3, color=tc)
    for x in (1.95, 4.0, 6.0, 7.9):
        ax.annotate(
            "", xy=(x + 0.08, 1.5), xytext=(x - 0.08, 1.5),
            arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6),
        )
    ax.set_title("가치 사슬 — 위성통신 서비스 + 방산기술 · 용량 투입 → 현금·디레버",
                 fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9))
    ax = axes[0]
    sizes = [825, 331]
    labs = ["Comm Services\n$825M (71%)", "DAT\n$331M (29%)"]
    ax.pie(
        sizes, labels=labs, colors=[C["sky"], C["navy"]], startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("Q1 FY27 매출 세그먼트 (~$1.16B)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["Comm\nAdj.EBITDA", "DAT\nAdj.EBITDA"]
    vals = [311, 70]
    colors = [C["teal"], C["gold"]]
    bars = ax.bar(cats, vals, color=colors, width=0.5)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("세그먼트 Adj.EBITDA (합 $381M)", fontproperties=PROP_B, fontsize=11)
    for b, v, yoy in zip(bars, vals, ["−3%", "−20%"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 8, f"{v}\n({yoy})",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 380)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_comm_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    cats = ["Aviation\nYoY", "Govt\nSATCOM", "Maritime\nYoY", "FS&O\nYoY", "Comm\nTotal"]
    vals = [11, 10, -7, -27, 0]
    colors = [C["green"] if v >= 0 else C["red"] for v in vals]
    colors[-1] = C["slate"]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("Comm Services 성장 브리지 — 항공·정부가 레거시 고정망·해사 상쇄",
                 fontproperties=PROP_B, fontsize=10.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (1.2 if v >= 0 else -3.5),
                f"{v:+.0f}%", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "03_comm_bridge.png")


def chart_kpi_units() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.8)
    ax.axis("off")
    items = [
        (0.2, 2.0, 3.1, 1.5, C["sky"], "white", "상업 항공\n~4,530대 (+10%)\nIFC 백로그 ~850"),
        (3.45, 2.0, 3.1, 1.5, C["teal"], "white", "비즈니스 항공\n~2,080대 (+1%)\nGovt SATCOM +10%"),
        (6.7, 2.0, 3.1, 1.5, C["gold"], C["ink"], "해사 선박\n~12,900 (−)\nNexusWave >1,700"),
        (0.2, 0.3, 9.6, 1.45, C["sand"], C["ink"],
         "미국 고정 브로드밴드 ~115,000 가입 · ARPU $111 · FS&O 매출 −27% (레거시 축소)"),
    ]
    for x, y, w, h, c, tc, t in items:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("운영 KPI — 모빌리티가 본체, 고정망은 의도적 축소",
                 fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "04_kpi_units.png")


def chart_dat_awards() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    cats = ["DAT\n매출", "DAT\n수주", "DAT\n백로그"]
    vals = [331, 524, 1400]
    colors = [C["slate"], C["teal"], C["navy"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("DAT — 수주·백로그가 매출을 선행", fontproperties=PROP_B, fontsize=11)
    for b, v, note in zip(bars, vals, ["−4%", "+22%", "+32%"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 40, f"{v}\n{note}",
                ha="center", fontproperties=PROP, fontsize=7.5)
    ax.set_ylim(0, 1700)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    cats2 = ["전술네트\n워킹 제품", "Space&\nMission", "InfoSec\n제품", "AT&O\n(IP등)"]
    # directional: tactical +36, space down, infosec -8, ATO -$17M
    vals2 = [36, -15, -8, -25]
    colors2 = [C["green"] if v >= 0 else C["red"] for v in vals2]
    ax.bar(cats2, vals2, color=colors2, width=0.55)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_ylabel("YoY 감각 (%)", fontproperties=PROP)
    ax.set_title("DAT 내부 — 전술↑ · IP로열티↓", fontproperties=PROP_B, fontsize=11)
    ax.text(0.02, -0.26, "Space&Mission/AT&O는 방향 감각(공급지연·IP −$19M). Book-to-bill 1.6x.",
            transform=ax.transAxes, fontproperties=PROP, fontsize=6.8, color=C["muted"])
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)
    fig.tight_layout()
    return save_fig(fig, "05_dat_awards.png")


def chart_cash_debt() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    cats = ["Q1 FCF\n(ex NR)", "LTM FCF\n(ex Ligado)", "FY27 FCF\n가이드"]
    vals = [72, 189, 180]
    bars = ax.bar(cats, vals, color=[C["teal"], C["sky"], C["navy"]], width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("자유현금흐름", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 5, f"{v}",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 230)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)

    ax = axes[1]
    cats = ["순부채", "현금", "유동성\n(현금+미인출)"]
    vals = [4800, 1740, 2900]
    colors = [C["orange"], C["teal"], C["gold"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("대차 — 레버리지 3.2x (−0.4x YoY)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 80, f"{v/1000:.1f}B",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 5800)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "06_cash_debt.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [40, 70, 105]
    highs = [65, 105, 140]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    ax.axvline(PX, color=C["gold"], ls="--", lw=1.5)
    ax.text(PX + 1.5, 2.35, f"현재 ~{PX:.0f}", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.axvline(PT, color="#2563eb", ls=":", lw=1.2)
    ax.text(PT + 1.5, -0.55, f"PT평균 ~{PT:.0f}", fontproperties=PROP, fontsize=7.5, color="#2563eb")
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        mid = (lo + hi) / 2
        ax.text(mid, i, f"{lo}–{hi}", ha="center", va="center", color="white",
                fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(25, 155)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear (12M · VS-3·DAT·디레버·경쟁)", fontproperties=PROP_B, fontsize=11)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP_B)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.0)
    ax.axis("off")
    items = [
        (0.2, 2.45, 3.1, 1.3, C["teal"], "white", "지금~\nVS-3 F2/F3\n서비스 진입"),
        (3.45, 2.45, 3.1, 1.3, C["navy"], "white", "FY27 H2\n가이드 가속\n(백로그 전환)"),
        (6.7, 2.45, 3.1, 1.3, C["sky"], "white", "DAT\nPTS-G·파이프라인\n수주→매출"),
        (0.2, 0.35, 4.7, 1.7, C["gold"], C["ink"], "중기\nD2D / Equatys\nL-band MSS 옵션"),
        (5.15, 0.35, 4.65, 1.7, C["sand"], C["ink"], "상시\n디레버 3.2x→\nFCF~$180M 가이드"),
    ]
    for x, y, w, h, c, tc, t in items:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.8, color=tc)
    ax.set_title("촉매 — VS-3 용량 · DAT 수주 전환 · 디레버",
                 fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.1)
    ax.axis("off")
    rows = [
        (0.3, 2.7, 9.4, 1.05, C["navy"], "white",
         "포트 역할: 미보유 · Chase 상 · 업사이드 +20% · 고점 91% → 추격 금지"),
        (0.3, 1.45, 4.5, 1.0, C["teal"], "white", "관심 금액\n눌림 후 C급 위성"),
        (5.0, 1.45, 4.7, 1.0, C["gold"], C["ink"], "타이밍\nVS-3 상용·레버리지 확인"),
        (0.3, 0.25, 9.4, 1.0, C["sand"], C["ink"],
         "지금: 실매출·FCF는 읽힘 · 순부채 $4.8B·고점권 · Starlink 경쟁·레거시 역풍 모니터"),
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


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"VSAT 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0369a1; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0369a1; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#e0f2fe 0%,#e8eef5 55%,#f0fdfa 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#bae6fd; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.good {{ background:#bbf7d0; }}
    .tag.bad {{ background:#fecdd3; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#e0f2fe; border-left:4px solid #0369a1; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0369a1; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:100px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#0369a1; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>VSAT 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>VSAT 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Viasat · 위성통신 서비스 + 방산/첨단기술 (DAT)</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1 FY2027 실적({EARN}) · VS-3 F2/F3 서비스 진입 직전</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.0f}</div><div class="s">시총 ~${MCAP_B:.1f}B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.0f}</div><div class="s">업사이드 {UPSIDE*100:+.0f}%</div></span>
    <span class="kpi"><div class="l">Q1 매출</div><div class="v">$1.16B</div><div class="s">YoY −1%</div></span>
    <span class="kpi"><div class="l">Adj.EBITDA</div><div class="v">$381M</div><div class="s">YoY −7%</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">Chase 상 · 실매출·FCF</span>
    <span class="tag warn">고점 {NEAR_HI*100:.0f}% · 순부채 $4.8B</span>
    <span class="tag">레버리지 3.2x (−0.4x)</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>임상 옵션이 아니라, 항공·정부 SATCOM이 끌고 고정망·해사가 깎는 ‘실매출’ 위성통신 회사.</b>
Q1 FY27 매출 <b>~$1.16B (−1%)</b> · Adj.EBITDA <b>$381M (−7%)</b> · FCF <b>$72M</b>.
성장축은 <b>항공(+11%)·정부 SATCOM(+10%)·DAT 수주(+22%)</b>이고,
역풍은 <b>FS&O(−27%)·해사(−7%)·IP 라이선스 감소</b>다.
VS-3 F2/F3 서비스 진입과 DAT 백로그 전환이 FY27 H2·중기 스토리의 핵심.
단 <b>순부채 ~$4.8B · 레버리지 3.2x</b>가 밸류에이션 상한을 만든다.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 비행기·군에 위성 인터넷/통신을 팔고, 방산 장비·암호·전술망도 판다.
집 위성인터넷(고정망)은 줄어드는 중. 새 위성(VS-3)이 뜨면 모빌리티에 용량을 더 붓겠다는 그림이다.</div>
{gloss([
    ("Comm Services", "통신서비스 — 항공 IFC, 정부 SATCOM, 해사, 고정 브로드밴드 등."),
    ("DAT", "Defense and Advanced Technologies — 방산·암호·전술네트·우주미션 시스템."),
    ("VS-3", "ViaSat-3 위성군. F2/F3가 2026 늦여름~초가을 서비스 진입 목표."),
])}

{compete_html}

<h2>1. 세그먼트 — 어디서 돈이 오나</h2>
{fig_block(charts['02'], '세그먼트 믹스')}
{fig_block(charts['03'], 'Comm 성장 브리지')}
{fig_block(charts['04'], '운영 KPI')}
<table>
  <tr><th>세그먼트</th><th>Q1 FY27</th><th>동력 / 역풍</th></tr>
  <tr><td><b>Communication Services</b></td><td>매출 <b>$825M</b> (flat) · Adj.EBITDA $311M (−3%)</td>
      <td>항공 +11% · Govt +10% / 해사 −7% · FS&O −27%</td></tr>
  <tr><td><b>DAT</b></td><td>매출 <b>$331M</b> (−4%) · Adj.EBITDA $70M (−20%)</td>
      <td>전술네트 +36% · 수주 +22% / Space&amp;Mission·IP 라이선스 감소</td></tr>
  <tr><td>전사</td><td>매출 ~$1.16B (−1%) · Adj.EBITDA $381M (−7%) · 순손실 $52M</td>
      <td>수주 $1.3B(+10%) · 백로그 $4.2B(+19%)</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 매출의 ~70%는 Comm. 그 안에서 <b>항공+정부</b>가 성장하고
<b>집 인터넷·일부 해사</b>가 깎는다. DAT는 이번 분기 매출은 약했지만 <b>수주·백로그가 강</b>하다.</div>
{gloss([
    ("ARPA", "Average Revenue Per Aircraft — 항공기당 평균 매출. Full/Fast/Free로 상승 유도."),
    ("FS&O", "Fixed Services & Other — 미국 고정 브로드밴드 등 레거시."),
    ("NexusWave", "멀티오빗 해사 연결 상품. 설치 지연이 단기 해사 역풍 요인."),
])}

<h2>2. DAT — 수주가 미래 매출</h2>
{fig_block(charts['05'], 'DAT 수주·내부')}
<ul>
  <li>DAT 수주 <b>$524M (+22%)</b> · 백로그 <b>$1.4B (+32%)</b> · Book-to-bill <b>1.6x</b></li>
  <li><b>PTS-G</b> 차기 단계 수주 — Space Force 보호전술 SATCOM · IDIQ 천장 $4B(프로그램 전체)</li>
  <li>전술네트워킹 제품 <b>+36%</b> (TrellisWare 등 국제)</li>
  <li>IP 라이선스/로열티 감소가 Adj.EBITDA에 약 <b>$19M</b> YoY 헤드윈드</li>
  <li>경영진: DAT 전략검토는 진행 중 · 조기 분리(one-way door)는 신중</li>
</ul>
<div class="box"><b>FY27 가이드:</b> 전사 매출 mid-single-digit 성장 · Adj.EBITDA flat~소폭↑(H2 강세).
Comm low-SD · <b>DAT mid-teens</b>. CapEx $0.95–1.0B · FCF ~$180M · 레버리지 소폭 하락.</div>
{gloss([
    ("Book-to-bill", "수주/매출 비율. &gt;1이면 미래 매출 파이프가 두꺼워짐."),
    ("PTS-G", "Protected Tactical SATCOM-Global — 미국 우주군 보호전술 위성 프로그램."),
    ("Dual-use", "민·군 겸용 기술/인프라. DAT↔서비스 전환 스토리의 핵심."),
])}

<h2>3. 현금 · 부채 · VS-3</h2>
{fig_block(charts['06'], 'FCF·부채')}
{fig_block(charts['08'], '촉매')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>Q1 FCF (비경상 제외)</td><td><b>$72M</b> (+19% YoY)</td></tr>
  <tr><td>LTM FCF (Ligado 제외)</td><td>$189M</td></tr>
  <tr><td>현금 / 유동성</td><td>$1.74B / <b>$2.9B</b> (미인출 RCF $1.15B 포함)</td></tr>
  <tr><td>순부채 / 레버리지</td><td><b>$4.8B</b> / <b>3.2x</b> (−0.4x YoY)</td></tr>
  <tr><td>Q1 CapEx</td><td>$219M (+11%)</td></tr>
  <tr><td>VS-3</td><td>F2 ~2026-09 서비스 · F3 APAC 늦8~초9월 목표</td></tr>
  <tr><td>중기 옵션</td><td>D2D / Equatys · L-band MSS · 멀티오빗</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 영업은 현금을 만든다. 그런데 위성·인수(Inmarsat)로 쌓인 <b>부채가 큼</b>.
‘성장이냐 디레버냐’를 동시에 해야 해서, 고점권에서는 리스크 프리미엄이 붙는다.</div>
{gloss([
    ("Net leverage", "순부채 / LTM Adj.EBITDA."),
    ("FCF", "영업CF − CapEx. 부채상환·투자 여력의 핵심."),
    ("D2D", "Direct-to-Device — 휴대폰 직결 위성. 3GPP NTN·스펙트럼 경쟁 환경."),
])}

<h2>4. 시나리오</h2>
{fig_block(charts['07'], '주가 시나리오')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>105–140</td><td>VS-3 순항 · DAT 수주→매출 · 디레버 가속 · D2D 옵션 부각</td></tr>
  <tr><td>Base</td><td>70–105</td><td>가이드 유지 · PT(~101) 수렴 · 레거시 역풍 지속</td></tr>
  <tr><td>Bear</td><td>40–65</td><td>경쟁 심화 · CapEx 초과 · 레버리지 고착 · 항공 churn</td></tr>
</table>
<p><b>Breaker:</b> VS-3 성능/지연 · Starlink 등 IFC 전환 가속 · 해사 설치 정체 ·
정부예산/계약 지연 · 이자·부채 부담 · DAT 분리 혼란</p>
<p class="small">현재가 ${PX:.2f} · 52주 고 ${H52:.2f} (근접 {NEAR_HI*100:.0f}%) · 저 ${L52:.2f} ·
업사이드 {UPSIDE*100:+.1f}% — <b>고점권 추격 논리 약함</b>.</p>

<h2>5. 포트폴리오 위치</h2>
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>역할</td><td>미보유 · Chase <b>상</b> · SYRE/DNTH와 달리 <b>실매출·FCF가 읽힘</b></td></tr>
  <tr><td>금액</td><td>관심 시 <b>C급 위성</b> (부채·경쟁 감안 · 풀베팅 금지)</td></tr>
  <tr><td>타이밍</td><td><b>고점 91% → 추격 금지</b> · VS-3 상용·레버리지/눌림 확인 후</td></tr>
  <tr><td>하지 말 것</td><td>Adj.EBITDA만 보고 저부채로 착각 · FS&O 회복을 단기 베팅</td></tr>
</table>
<div class="easy"><b>한줄 결론:</b> 수익구조의 실체는 <u>항공·정부 모빌리티 + DAT 수주 파이프 − 레거시 고정망</u>.
돈의 경로는 명확하나 <b>순부채 $4.8B·고점권</b>이라 당신 시드에는
<b>공부·워치 → 눌림 후 C급</b>이 맞고 지금 추격은 아니다.</div>

<h2>부록 · 출처</h2>
<p class="small">
Viasat Q1 FY2027 shareholder letter / earnings (2026-08-04) · earnings call 요약 ·
yfinance 분기 손익·BS·가격·PT ({ASOF}) · 심층분석 2026-08-12 (Chase 상 · 고점 91%).
시나리오는 예시 밴드(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 VSAT · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_comm_bridge(),
        "04": chart_kpi_units(),
        "05": chart_dat_awards(),
        "06": chart_cash_debt(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("VSAT", CHART_DIR)
    charts.update(cpaths)
    compete_html = render_compete_section_html(
        charts,
        bundle,
        img_b64_fn=img_b64,
        gloss_fn=gloss,
        easy_share="<div class='easy'><b>쉽게:</b> 상장 위성통신 피어셋 안에서의 상대 위치다. Starlink(비상장)는 빠져 있다.</div>",
        easy_mix="<div class='easy'><b>쉽게:</b> VSAT는 Comm(~70%)이 본체, DAT가 수주 선행. IRDM은 MSS 서비스 편중이 더 크다.</div>",
        gloss_share=[("satcom peer", "상장 위성통신사(Starlink 제외)."), ("MSS", "모바일 위성 서비스.")],
        gloss_mix=[("Comm Services", "항공·정부·해사·고정망 등."), ("DAT/Defense", "방산·암호·전술·우주미션.")],
    )
    html = build_html(charts, compete_html=compete_html)
    html, _px = build_and_insert_price("VSAT", CHART_DIR, html)
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
        tag="sepa-rev-vsat",
        title="SEPA Revenue Structure — VSAT",
        notes=(
            "## 수익구조분석(VSAT) · Viasat\n\n"
            f"Q1 FY27: 매출 ~$1.16B · Adj.EBITDA $381M · Comm $825M / DAT $331M\n"
            f"FCF $72M · 순부채 $4.8B · 레버리지 3.2x · VS-3 F2/F3 서비스 진입\n"
            f"px~${PX:.0f} · PT~${PT:.0f} · 업사이드 {UPSIDE*100:+.0f}%\n\n"
            f"- Chase 상 · 고점 {NEAR_HI*100:.0f}% → 추격 금지\n"
            "- 포트: 미보유 워치 · 눌림/VS-3·디레버 확인 후 C급 검토\n"
        ),
    )
    print_release_result(rel, label="VSAT 수익구조 PDF")
    print(f"compete={bundle.ticker if bundle else None}\nVSAT rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% near_hi={NEAR_HI*100:.0f}%")


if __name__ == "__main__":
    main()
