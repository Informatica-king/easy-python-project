#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(DNTH) — Dianthus Therapeutics · claseprubart / DNTH212 · WeasyPrint PDF."""

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
PX = 108.49
PT = 137.62
H52 = 114.55
L52 = 19.75
UPSIDE = PT / PX - 1.0
NEAR_HI = PX / H52
MCAP_B = 6.07
EARN = "2026-08-04"  # just reported; next TBD
OUT_PDF = [
    Path("/opt/cursor/artifacts/DNTH_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/DNTH_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/DNTH_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/DNTH_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/dnth")
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
        (0.1, 0.7, 1.75, 1.6, "aC1s 선택\n억제 플랫폼", C["sand"]),
        (2.05, 0.7, 1.85, 1.6, "claseprubart\n(DNTH103)", C["bio"]),
        (4.1, 0.7, 1.85, 1.6, "gMG·CIDP\n·MMN Ph2/3", C["teal"]),
        (6.15, 0.7, 1.7, 1.6, "DNTH212\n·DNTH312", C["gold"]),
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
    for x in (1.95, 4.0, 6.0, 7.9):
        ax.annotate(
            "", xy=(x + 0.08, 1.5), xytext=(x - 0.08, 1.5),
            arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6),
        )
    ax.set_title("가치 사슬 — aC1s 파이프라인-인-어-프로덕트 → 류마 확장 → (미실현) 상업화",
                 fontproperties=PROP_B, fontsize=10.5, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_revenue_today() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9))
    ax = axes[0]
    labels = ["라이선스\n매출 Q2", "이자수익\nQ2", "제품매출"]
    vals = [0.76, 11.54, 0.12]  # floor for zero product
    colors = [C["gold"], C["teal"], C["sand"]]
    ax.bar(labels, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("현재 ‘돈’의 성격 (Q2'26)", fontproperties=PROP_B, fontsize=11)
    ax.text(0, 1.3, "$0.76M", ha="center", fontproperties=PROP, fontsize=8)
    ax.text(1, 12.2, "$11.5M", ha="center", fontproperties=PROP, fontsize=8)
    ax.text(2, 0.9, "실질 $0", ha="center", fontproperties=PROP, fontsize=8, color=C["muted"])
    ax.set_ylim(0, 15)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)

    ax = axes[1]
    sizes = [0.76, 11.54]
    labs = ["License\n$0.76M", "Interest\n$11.5M"]
    ax.pie(
        sizes, labels=labs, colors=[C["gold"], C["teal"]], startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("Q2 인식액 — 이자가 라이선스를 압도", fontproperties=PROP_B, fontsize=11)
    fig.suptitle("수익구조: 미미한 라이선스 + 현금이자 · 제품매출 없음",
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
         "④ 제품 매출 (미승인) — gMG·CIDP·MMN 상업화 · 류마(DNTH212) 확장"),
        (0.3, 2.25, 9.4, 0.8, C["teal"], "white",
         "③ 파트너 딜 (잠재) — 지역/적응증 라이선스 · 아직 핵심 빅딜 없음"),
        (0.3, 1.3, 9.4, 0.8, C["gold"], C["ink"],
         "② 라이선스 매출 — Q2'26 $0.76M (소규모 · 본업 스케일 아님)"),
        (0.3, 0.35, 9.4, 0.8, C["bio"], "white",
         "① 이자수익 — 현금·투자 ~$1.2B · Q2'26 $11.5M (현재 주 현금유입)"),
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
    fig, ax = plt.subplots(figsize=(9.2, 4.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.5)
    ax.axis("off")
    stages = ["Discovery", "IND", "Ph1", "Ph2", "Ph3", "Market"]
    for i, s in enumerate(stages):
        ax.text(0.8 + i * 1.5, 5.15, s, ha="center", fontproperties=PROP_B, fontsize=8, color=C["muted"])
        ax.plot([0.8 + i * 1.5, 0.8 + i * 1.5], [0.2, 4.9], color="#e7e5e4", lw=0.8)

    programs = [
        (5.2, "claseprubart · gMG", "Ph3 EMERGE 개시 · TL 2H'28", C["bio"], 4),
        (5.2, "claseprubart · CIDP", "Ph3 CAPTIVATE · PartA 75% · PartB YE'26", C["teal"], 3),
        (3.9, "claseprubart · MMN", "Ph2 MoMeNtum 46명 · TL Dec'26", C["teal2"], 2),
        (2.4, "DNTH212 (BDCA2+BAFF/APRIL)", "Ph1 HV 데이터 YE'26 · SjD/SLE/DM", C["gold"], 1),
        (1.5, "DNTH312 (aC1s+TACI)", "내부개발 · Ph1 ready 목표 YE'27", C["pink"], 0),
    ]
    for x_end, name, note, color, row in programs:
        y = 0.35 + row * 0.88
        ax.add_patch(
            FancyBboxPatch(
                (0.3, y), x_end + 1.0, 0.72,
                boxstyle="round,pad=0.02,rounding_size=0.08",
                facecolor=color, edgecolor="white", lw=1.2, alpha=0.92,
            )
        )
        tc = C["ink"] if color in (C["gold"], C["teal2"]) else "white"
        ax.text(0.5, y + 0.44, name, ha="left", va="center", fontproperties=PROP_B, fontsize=8.0, color=tc)
        ax.text(0.5, y + 0.16, note, ha="left", va="center", fontproperties=PROP, fontsize=6.6, color=tc)
    ax.set_title("파이프라인 — 신경근육(claseprubart) + 류마(DNTH212/312)",
                 fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "04_pipeline.png")


def chart_opex_cash() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    qtrs = ["Q2'25", "Q3'25", "Q4'25", "Q1'26", "Q2'26"]
    rd = [26.25, 32.49, 59.9, 34.53, 48.69]
    ga = [8.87, 8.2, 9.93, 12.47, 13.56]
    x = range(len(qtrs))
    ax.bar(x, rd, color=C["bio"], label="R&D", width=0.55)
    ax.bar(x, ga, bottom=rd, color=C["slate"], label="G&A", width=0.55)
    ax.set_xticks(list(x))
    ax.set_xticklabels(qtrs, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("분기 OpEx — Ph2/3 가속 = 소진 가속", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8)

    ax = axes[1]
    labels = ["3/31'26", "6/30'26"]
    # Cash+STI + LT investments ≈ company ~$1.2B
    cash = [1225, 1190]
    bars = ax.bar(labels, cash, color=[C["teal"], C["navy"]], width=0.5)
    ax.set_ylabel("현금+투자 (M)", fontproperties=PROP)
    ax.set_title("현금 · 런웨이 목표 2030", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, cash):
        ax.text(b.get_x() + b.get_width() / 2, v + 25, f"~{v:.0f}",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.text(0.02, -0.26, "6/30: Cash+STI $887M + 투자 $304M ≈ 회사 발표 ~$1.2B",
            transform=ax.transAxes, fontproperties=PROP, fontsize=7, color=C["muted"])
    ax.set_ylim(0, 1500)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "05_opex_cash.png")


def chart_burn_vs_income() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    cats = ["Q2 OpEx", "Q2 순손실", "Q2 이자", "Q2 License", "시총\n(~$6.1B)"]
    vals = [62.2, 50.2, 11.5, 0.76, 120]
    colors = [C["red"], C["pink"], C["teal"], C["gold"], C["navy"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD (시총은 축 압축)", fontproperties=PROP)
    ax.set_title("소진 vs 이자·라이선스 vs 시총 감각", fontproperties=PROP_B, fontsize=11)
    labels_v = ["62", "50", "11.5", "0.8", "~6,070"]
    for b, lab in zip(bars, labels_v):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 3, lab,
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 145)
    ax.text(0.02, -0.22, "시총 막대는 스케일 비교용. 제품매출 없이 ~$6B 밸류 = 임상 성공 선반영.",
            transform=ax.transAxes, fontproperties=PROP, fontsize=7, color=C["muted"])
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "06_burn_vs_income.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [40, 95, 145]
    highs = [75, 140, 200]
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
    ax.set_xlim(25, 215)
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
        (0.2, 2.55, 3.1, 1.25, C["teal"], "white", "2026-12\nMMN Ph2 TL"),
        (3.45, 2.55, 3.1, 1.25, C["bio"], "white", "YE'26\nCIDP PartB 가이던스"),
        (6.7, 2.55, 3.1, 1.25, C["gold"], C["ink"], "YE'26\nDNTH212 Ph1 HV"),
        (0.2, 0.35, 4.7, 1.7, C["navy"], "white", "2H'28\ngMG Ph3 EMERGE\n탑라인"),
        (5.15, 0.35, 4.65, 1.7, C["sand"], C["ink"], "실적 08-04 소화\n다음: 임상 이벤트\n중심 (Rev~$0)"),
    ]
    for x, y, w, h, c, tc, t in items:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=9, color=tc)
    ax.set_title("촉매 캘린더 — 주가·가치는 Ph2/3 이벤트가 지배", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.1)
    ax.axis("off")
    rows = [
        (0.3, 2.7, 9.4, 1.05, C["navy"], "white",
         "포트 역할: 미보유 · 심층 A′ 후보 · Chase 중·임상변동 · 추격 금지"),
        (0.3, 1.45, 4.5, 1.0, C["teal"], "white", "관심 금액\n최대 C급 극소(≤1주 감각)"),
        (5.0, 1.45, 4.7, 1.0, C["gold"], C["ink"], "타이밍\nMMN TL·눌림 후 재평가"),
        (0.3, 0.25, 9.4, 1.0, C["sand"], C["ink"],
         "지금: 제품매출≈$0 · 시총~$6B · Ph3 개시 직후 고점권 · 현금·보유주 우선"),
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
      @bottom-center {{ content:"DNTH 수익구조분석 {ASOF} — " counter(page);
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
<html lang="ko"><head><meta charset="utf-8"/><title>DNTH 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>DNTH 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Dianthus Therapeutics · claseprubart (aC1s) · 중증 자가면역</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적({EARN}) · 임상단계 · 파이프라인-인-어-프로덕트</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.0f}</div><div class="s">시총 ~${MCAP_B:.1f}B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.0f}</div><div class="s">업사이드 {UPSIDE*100:+.0f}%</div></span>
    <span class="kpi"><div class="l">제품매출</div><div class="v">$0</div><div class="s">License Q2 $0.8M</div></span>
    <span class="kpi"><div class="l">현금·투자</div><div class="v">~$1.2B</div><div class="s">런웨이 ~2030</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">심층 A′ · 기술적 후보</span>
    <span class="tag warn">Chase 중·임상변동 · 고점 {NEAR_HI*100:.0f}%</span>
    <span class="tag bad">제품매출 없음 · Ph2/3 바이너리</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>약 팔아서 버는 회사가 아니라, claseprubart(aC1s) Ph2/3 성공 옵션에 ~$6B 시총을 붙인 회사.</b>
Q2'26 <b>License $0.76M</b> · 제품매출 없음. 이자수익($11.5M)이 라이선스를 압도한다.
본업 현금은 <b>R&amp;D 소진</b>이고, 가치는
<b>MMN Ph2(12월) · CIDP Part B · gMG Ph3(2H'28)</b> + DNTH212/312 확장에 연동한다.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 재무제표 ‘매출’은 거의 없다.
지금 보이는 큰 숫자는 <b>예금 이자</b>와 <b>임상 비용</b>이다.
진짜 수익구조는 <u>약이 승인·판매된 뒤</u>에야 생긴다.</div>
{gloss([
    ("임상단계", "승인·상업화 전 — 제품매출 없이 개발비로 적자."),
    ("aC1s", "활성형 C1s만 억제하는 고전 보체 경로 타깃. 감염 위험 낮추려는 선택성 스토리."),
    ("파이프라인-인-어-프로덕트", "한 분자로 여러 적응증(gMG·CIDP·MMN)을 노리는 구조."),
])}

{compete_html}

<h2>1. 어디서 돈이 오나 — 지금 vs 나중</h2>
{fig_block(charts['02'], '현재 현금성 손익')}
{fig_block(charts['03'], '미래 수익 스택')}
<table>
  <tr><th>수익원</th><th>상태</th><th>규모·조건</th></tr>
  <tr><td>제품(처방약) 매출</td><td>없음</td><td>승인 전 · 제품매출 <b>$0</b></td></tr>
  <tr><td>라이선스 매출</td><td>미미</td><td>Q2'26 <b>$0.76M</b> (전년 $0.19M) — 스케일 없음</td></tr>
  <tr><td>이자수익</td><td>주력(현재)</td><td>Q2'26 <b>$11.5M</b> · 현금·투자 ~$1.2B 운용</td></tr>
  <tr><td>파트너 빅딜</td><td>잠재</td><td>아직 핵심 지역 딜 upfront 없음</td></tr>
  <tr><td>미래 제품</td><td>미실현</td><td>Ph3 성공→승인→신경근육 프랜차이즈 + 류마 확장</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 지금은 <b>이자 &gt;&gt; 라이선스</b>.
앞으로 돈이 되려면 ①Ph2/3 성공 → ②FDA 승인 → ③약 판매(또는 빅파마 딜) 순서다.</div>
{gloss([
    ("License revenue", "연구·라이선스 계약으로 인식하는 소액 매출. 제품 판매와 다름."),
    ("Interest income", "현금·단기투자 이자 — 본업 수익성 지표가 아님."),
    ("Royalty/Upfront", "빅딜이 생기면 그때부터 협업매출 스택이 커짐."),
])}

<h2>2. 성장 엔진 — 파이프라인</h2>
{fig_block(charts['04'], '파이프라인')}
{fig_block(charts['08'], '촉매')}
<ul>
  <li><b>claseprubart · gMG</b> — Ph3 EMERGE(300mg Q2W/Q4W SC) 2026-06 개시 · 탑라인 <b>2H'28</b> · FDA Orphan(MG)</li>
  <li><b>claseprubart · CIDP</b> — Ph3 CAPTIVATE Part A 중간 <b>반응률 75%</b>(목표 ≥50%) · Part B 가이던스 <b>YE'26</b></li>
  <li><b>claseprubart · MMN</b> — Ph2 MoMeNtum 46명 등록完 · 탑라인 <b>2026-12</b></li>
  <li><b>DNTH212</b> — BDCA2 + BAFF/APRIL 이기능 · SjD/SLE/DM · Ph1 HV <b>YE'26</b></li>
  <li><b>DNTH312</b> — claseprubart + TACI · Ph1 ready 목표 <b>YE'27</b></li>
</ul>
<div class="box"><b>상업 내러티브:</b> 피하·드문 투여 + 선택적 aC1s로 ‘베스트인디지즈’ 주장.
시총 ~$6B는 Ph3 개시·CIDP 중간결과 이후 <u>성공을 상당 부분 선반영</u>한 수준으로 읽힌다.
손익계산서에 들어오는 제품 숫자는 아직 없다.</div>
{gloss([
    ("gMG / CIDP / MMN", "전신성 중증근무력증 / 만성염증탈수초다발신경병 / 다초점운동신경병."),
    ("YTE", "반감기 연장 기술 — 투여 간격(Q2W/Q4W) 스토리의 기반."),
    ("TACI / BAFF·APRIL", "B세포 생존·분화 경로. DNTH212/312의 류마·자가면역 확장 축."),
])}

<h2>3. 비용 · 현금</h2>
{fig_block(charts['05'], 'OpEx·현금')}
{fig_block(charts['06'], '소진 vs 수입')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>Q2'26 R&amp;D / G&amp;A</td><td><b>$48.7M</b> / $13.6M (전년 $26.3 / $8.9)</td></tr>
  <tr><td>Q2'26 순손실</td><td><b>$50.2M</b> ($0.90/주) vs 전년 $31.6M</td></tr>
  <tr><td>Q2'26 License / 이자</td><td>$0.76M / <b>$11.5M</b></td></tr>
  <tr><td>현금·투자 (6/30/26)</td><td><b>~$1.2B</b> (Cash+STI $887M + 투자 $304M)</td></tr>
  <tr><td>런웨이(회사)</td><td><b>2030년</b>까지 OpEx 충당 예상</td></tr>
  <tr><td>직전 실적</td><td><b>{EARN}</b> 발표 · 다음은 임상 이벤트가 핵심</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 분기 OpEx(~$62M)는 이자·라이선스보다 훨씬 크다.
진짜 방패는 <b>현금 ~$1.2B · 런웨이 2030</b>이다. Ph3가 늘면 소진도 커진다.</div>
{gloss([
    ("Runway", "현재 현금으로 적자를 버티는 예상 기간."),
    ("SBC", "주식보상비용 — R&D $5.6M 포함(현금 유출과 구분)."),
    ("희석", "추가 자금조달 시 주식 수 증가 위험(지금은 런웨이 여유)."),
])}

<h2>4. 민감도 · 시나리오</h2>
{fig_block(charts['07'], '주가 시나리오')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>145–200</td><td>MMN 성공 · CIDP Part B 순항 · PT 상향 · 212 데이터 양호</td></tr>
  <tr><td>Base</td><td>95–140</td><td>혼재 데이터 · PT(~138) 수렴 · 런웨이 유지</td></tr>
  <tr><td>Bear</td><td>40–75</td><td>MMN/CIDP 실패·안전성 · 경쟁 보체제제 우위 · 희석</td></tr>
</table>
<p><b>Breaker:</b> MoMeNtum 실패 · CAPTIVATE Part B 지연/미스 · 감염·DIL/SLE 이슈 ·
경쟁 aC1s/보체 자산 · Ph3 비용 급증·희석</p>
<p class="small">현재가 ${PX:.2f} · 52주 고 ${H52:.2f} (근접 {NEAR_HI*100:.0f}%) · 저 ${L52:.2f} ·
업사이드 {UPSIDE*100:+.1f}% — <b>고점권 추격 논리는 약함</b>.</p>
{gloss([
    ("바이너리", "임상 성공/실패가 시총을 크게 흔드는 구조."),
    ("PT 업사이드", "분석가 가정 합 — Ph2/3 리스크를 과소평가할 수 있음."),
])}

<h2>5. 포트폴리오 위치</h2>
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>역할</td><td>미보유 <b>워치</b> · 심층 A′는 기술 후보 · Chase <b>중·임상변동</b></td></tr>
  <tr><td>금액</td><td>관심 시에도 <b>C급 극소(≤1주 감각)</b> · 시총·바이너리 대비 과대노출 금지</td></tr>
  <tr><td>타이밍</td><td><b>MMN TL(12월)</b> 또는 고점권 이탈·눌림 후 · 추격 금지</td></tr>
  <tr><td>하지 말 것</td><td>이자·라이선스를 제품 성장으로 착각 · Ph3 전 풀베팅 · 현금층 잠식</td></tr>
</table>
<div class="easy"><b>한줄 결론:</b> 수익구조의 실체는 <u>이자 + 미미한 라이선스 + 미래 승인 옵션</u>.
claseprubart 스토리(CIDP 75%·Ph3 개시)는 강하지만,
<b>~$6B 시총·고점권·제품매출≈$0</b>이라 당신 시드에는 <b>공부·워치</b>가 맞고 추격 매수는 아니다.</div>

<h2>부록 · 출처</h2>
<p class="small">
Dianthus Q2 2026 earnings release (2026-08-04) · SEC 8-K 요약 ·
yfinance 분기 손익·BS·가격·PT ({ASOF}) · 심층분석 2026-08-12 (A′ / Chase 중·임상변동).
시나리오는 예시 밴드(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 DNTH · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_revenue_today(),
        "03": chart_future_stack(),
        "04": chart_pipeline(),
        "05": chart_opex_cash(),
        "06": chart_burn_vs_income(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("DNTH", CHART_DIR)
    charts.update(cpaths)
    compete_html = render_compete_section_html(
        charts,
        bundle,
        img_b64_fn=img_b64,
        gloss_fn=gloss,
        easy_share="<div class='easy'><b>쉽게:</b> gMG/CIDP·보체 피어셋에서 DNTH 스케일이 커졌지만, ARGX는 이미 약을 판다. 같은 ‘점유’가 아니다.</div>",
        easy_mix="<div class='easy'><b>쉽게:</b> DNTH는 아직 이자≫라이선스. ARGX 믹스(제품 중심)와 나란히 두면 ‘상업화 전’이 한눈에 보인다.</div>",
        gloss_share=[("complement", "보체 경로 억제 — aC1s 등."), ("gMG/CIDP", "중증근무력·만성탈수초신경병.")],
        gloss_mix=[("License/Collab", "소액 라이선스 매출."), ("Interest", "현금·투자 이자 — 현재 주 유입.")],
    )
    html = build_html(charts, compete_html=compete_html)
    html, _px = build_and_insert_price("DNTH", CHART_DIR, html)
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
        tag="sepa-rev-dnth",
        title="SEPA Revenue Structure — DNTH",
        notes=(
            "## 수익구조분석(DNTH) · Dianthus Therapeutics\n\n"
            f"임상단계 · 제품매출 $0 · License Q2 $0.76M · 현금·투자 ~$1.2B (런웨이 ~2030)\n"
            f"claseprubart Ph3 gMG/CIDP + Ph2 MMN · px~${PX:.0f} · PT~${PT:.0f}\n\n"
            f"- 심층 A′ · Chase 중·임상변동 (고점 {NEAR_HI*100:.0f}%)\n"
            "- 포트: 미보유 워치 · 추격 금지 · MMN TL/눌림 후 재평가\n"
        ),
    )
    print_release_result(rel, label="DNTH 수익구조 PDF")
    print(f"compete={bundle.ticker if bundle else None}\nDNTH rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% near_hi={NEAR_HI*100:.0f}%")


if __name__ == "__main__":
    main()
