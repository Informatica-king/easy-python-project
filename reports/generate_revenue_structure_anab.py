#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(ANAB) — AnaptysBio · Jemperli/imsidolimab 로열티 피벗 · WeasyPrint PDF."""

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
PX = 57.87
PT = 87.09
H52 = 72.36
L52 = 11.40
UPSIDE = PT / PX - 1.0
NEAR_HI = PX / H52
MCAP_B = 1.71
EARN = "2026-08-12"  # Q2 print day
OUT_PDF = [
    Path("/opt/cursor/artifacts/ANAB_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/ANAB_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/ANAB_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/ANAB_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/anab")
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
    "bio": "#0e7490",
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
        (0.1, 0.7, 1.7, 1.6, "GSK\nJemperli 판매", C["sand"]),
        (2.0, 0.7, 1.75, 1.6, "ANAB\n로열티 청구", C["teal"]),
        (3.95, 0.7, 1.75, 1.6, "Sagard\n선취 상환중", C["gold"]),
        (5.9, 0.7, 1.75, 1.6, "순 로열티\n현금 (상환후)", C["bio"]),
        (7.85, 0.7, 1.9, 1.6, "EBIT>95%\n+자사주/환원", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = "white" if c in (C["teal"], C["bio"], C["navy"], C["gold"]) else C["ink"]
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.3, color=tc)
    for x in (1.85, 3.8, 5.75, 7.7):
        ax.annotate(
            "", xy=(x + 0.1, 1.5), xytext=(x - 0.05, 1.5),
            arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6),
        )
    ax.set_title("가치 사슬 — 로열티 피벗 (First Tracks 스핀오프 후)",
                 fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_revenue_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9))
    ax = axes[0]
    # Q1'26: Jemperli 24.7 of 25.6 collab; residual ~0.9 other
    sizes = [24.7, 0.9]
    labs = ["Jemperli\n로열티\n$24.7M", "기타 협업\n~$0.9M"]
    ax.pie(
        sizes, labels=labs, colors=[C["teal"], C["sand"]], startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("Q1'26 협업매출 $25.6M 구성", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    qtrs = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    # chronological for bar
    rev = [27.77, 22.26, 76.32, 108.25, 25.56]
    colors = [C["slate"], C["slate"], C["gold"], C["gold"], C["teal"]]
    bars = ax.bar(qtrs, rev, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("분기 협업매출 (금=마일스톤 구간)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}",
                ha="center", fontproperties=PROP, fontsize=7.5)
    ax.text(0.02, -0.24, "Q3–Q4'25 스파이크는 일회성 인식 비중↑ · Q1'26은 로열티 런레이트에 가깝다",
            transform=ax.transAxes, fontproperties=PROP, fontsize=7, color=C["muted"])
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.suptitle("지금 매출의 실체 = GSK Jemperli 로열티 (+ 간헐 마일스톤)",
                 fontproperties=PROP_B, fontsize=12, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_mix.png")


def chart_jemperli_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.7))
    cats = ["GSK\nJemperli\nQ1 판매", "ANAB\n로열티\nQ1", "연환산\n로열티\n(×4 참고)", "피크 가정\n연 로열티\n(2029E)"]
    vals = [313, 24.7, 98.8, 390]
    colors = [C["sand"], C["teal"], C["bio"], C["navy"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("Jemperli — 판매 → ANAB 로열티 → 피크 내러티브",
                 fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 8, f"{v:.0f}",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 460)
    ax.text(0.02, -0.22,
            "피크 >$390M/년은 GSK 피크세일즈 >$2.7B 가정 기반(회사). 연환산×4는 단순 참고.",
            transform=ax.transAxes, fontproperties=PROP, fontsize=7, color=C["muted"])
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "03_jemperli_bridge.png")


def chart_sagard_stack() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")
    layers = [
        (0.3, 3.15, 9.4, 0.8, C["navy"], "white",
         "④ 자사주·주주환원 — $100M 바이백 한도(~2026-12-31) · 로열티 현금화 후"),
        (0.3, 2.2, 9.4, 0.8, C["teal"], "white",
         "③ 순 로열티 현금 — Sagard 상환 완료 후(~E Q2'27 목표) 본격 유입"),
        (0.3, 1.25, 9.4, 0.8, C["gold"], C["ink"],
         "② Sagard 선취 — 누적 ~$275M 지급 · 잔여 ~$325M · BS 부채 $264M · 비현금이자"),
        (0.3, 0.3, 9.4, 0.8, C["bio"], "white",
         "① 회계상 협업매출 — Jemperli 로열티 인식 (현금은 당분간 Sagard 우선)"),
    ]
    for x, y, w, h, c, tc, t in layers:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=7.8, color=tc)
    ax.set_title("현금 스택 — ‘매출’과 ‘주머니에 남는 돈’을 구분",
                 fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "04_sagard_stack.png")


def chart_opex_transition() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    qtrs = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rd = [41.18, 37.82, 31.41, 25.56, 33.99]
    ga = [14.13, 10.61, 10.21, 15.79, 26.2]
    x = range(len(qtrs))
    ax.bar(x, rd, color=C["slate"], label="R&D", width=0.55)
    ax.bar(x, ga, bottom=rd, color=C["gold"], label="G&A", width=0.55)
    ax.set_xticks(list(x))
    ax.set_xticklabels(qtrs, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("분기 OpEx (Q1은 스핀오프 전 혼재)", fontproperties=PROP_B, fontsize=10.5)
    ax.legend(prop=PROP, fontsize=8)
    ax.text(0.02, -0.26, "Q2'26부터 First Tracks 비용을 중단영업으로 재분류 예정 → OpEx 급감·EBIT>95% 목표",
            transform=ax.transAxes, fontproperties=PROP, fontsize=6.8, color=C["muted"])

    ax = axes[1]
    labels = ["YE'25", "3/31'26"]
    cash = [311.6, 286.5]
    debt = [276.5, 263.7]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], cash, width=w, color=C["teal"], label="현금·투자")
    ax.bar([i + w / 2 for i in x], debt, width=w, color=C["gold"], label="미래로열티 매각부채")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("현금 vs Sagard 관련 부채", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=7.5)
    fig.tight_layout()
    return save_fig(fig, "05_opex_cash.png")


def chart_two_streams() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.8)
    ax.axis("off")
    items = [
        (0.25, 0.5, 4.6, 2.9, C["teal"], "white",
         "Jemperli (GSK)\n본체 로열티\nQ1 판매 $313M (+40%+)\nANAB 로열티 $24.7M\n피크 가정 >$390M/년(’29E)"),
        (5.15, 0.5, 4.6, 2.9, C["navy"], "white",
         "imsidolimab (Vanda)\nGPP · PDUFA 2026-12-12\n승인 시 추가 로열티·마일스톤\n(규모는 Jemperli 대비 보조)"),
    ]
    for x, y, w, h, c, tc, t in items:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                           facecolor=c, edgecolor="white", lw=2)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=9, color=tc)
    ax.set_title("두 개의 금융 협업 — 본체(Jemperli) + 옵션(imsidolimab)",
                 fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "06_two_streams.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [25, 55, 95]
    highs = [45, 90, 140]
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
    ax.set_xlim(15, 155)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear (12M · 로열티·Sagard·PDUFA)", fontproperties=PROP_B, fontsize=11)
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
        (0.2, 2.45, 3.1, 1.3, C["gold"], C["ink"], f"오늘\nQ2 실적\n{EARN}"),
        (3.45, 2.45, 3.1, 1.3, C["teal"], "white", "Q2부터\n중단영업 재분류\n(클린 로열티 P&L)"),
        (6.7, 2.45, 3.1, 1.3, C["navy"], "white", "2026-12-12\nimsidolimab\nPDUFA"),
        (0.2, 0.35, 4.7, 1.7, C["bio"], "white", "~E Q2'27\nSagard 잔여\n~$325M 상환 목표"),
        (5.15, 0.35, 4.65, 1.7, C["sand"], C["ink"], "2029E\n연 로열티 >$390M\n(GSK 피크 가정)"),
    ]
    for x, y, w, h, c, tc, t in items:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.8, color=tc)
    ax.set_title("촉매 캘린더 — 실적창·PDUFA·Sagard 상환이 키",
                 fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.1)
    ax.axis("off")
    rows = [
        (0.3, 2.7, 9.4, 1.05, C["navy"], "white",
         "포트 역할: 미보유 · Chase 상 · 업사이드 +50% · 오늘은 EARN_D5(실적일)"),
        (0.3, 1.45, 4.5, 1.0, C["teal"], "white", "관심 금액\n실적 후 C급 위성 검토"),
        (5.0, 1.45, 4.7, 1.0, C["gold"], C["ink"], "타이밍\nQ2 클린 P&L·로열티 확인"),
        (0.3, 0.25, 9.4, 1.0, C["sand"], C["ink"],
         "지금: 로열티 피벗은 매력 · 단 Sagard·이자·실적창 → 추격·실적전 신규 금지"),
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
      @bottom-center {{ content:"ANAB 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0e7490; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0e7490; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ecfeff 0%,#e8eef5 55%,#f0fdfa 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#cffafe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.good {{ background:#bbf7d0; }}
    .tag.bad {{ background:#fecdd3; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#ecfeff; border-left:4px solid #0e7490; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0e7490; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#0e7490; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>ANAB 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>ANAB 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">AnaptysBio · 로열티 피벗 · Jemperli (GSK) + imsidolimab (Vanda)</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1'26 기준(스핀오프 4/20) · <b>오늘 Q2 실적일</b></p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.0f}</div><div class="s">시총 ~${MCAP_B:.2f}B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.0f}</div><div class="s">업사이드 {UPSIDE*100:+.0f}%</div></span>
    <span class="kpi"><div class="l">Q1 협업매출</div><div class="v">$25.6M</div><div class="s">Jemperli $24.7M</div></span>
    <span class="kpi"><div class="l">현금·투자</div><div class="v">$287M</div><div class="s">3/31/26</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">Chase 상 · RR 상위</span>
    <span class="tag warn">EARN_D5 · 오늘 실적</span>
    <span class="tag">로열티 회사 (임상 R&amp;D 스핀오프)</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>임상 개발사가 아니라, Jemperli·imsidolimab 로열티를 관리·환원하는 금융형 바이오.</b>
2026-04-20 First Tracks Bio 스핀오프로 R&amp;D 파이프라인(rosnilimab 등)을 분리했다.
남는 본체는 <b>GSK Jemperli 로열티</b>(Q1 $24.7M, +44% YoY)와
<b>Vanda imsidolimab</b>(GPP PDUFA 12/12)다.
목표 내러티브는 <b>EBIT 마진 &gt;95%</b> · 피크 시 연 로열티 <b>&gt;$390M(’29E)</b>.
다만 당분간 현금은 <b>Sagard 선취 상환</b>에 묶여 있다.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> SYRE/DNTH처럼 ‘약 만들어서 적자’가 아니다.
GSK가 약을 팔면 ANAB가 <b>로열티</b>를 받는 구조다.
다만 그 로열티 일부를 과거에 돈 받고 미리 팔아둔 상태(Sagard)라,
<u>회계 매출 ≠ 당장 주머니</u>를 구분해야 한다.</div>
{gloss([
    ("로열티 피벗", "신약 R&D 대신 기존 협업 로열티·자본환원에 집중하는 사업 전환."),
    ("스핀오프", "First Tracks Bio로 임상 파이프라인을 분리(2026-04-20)."),
    ("EBIT margin >95%", "회사 주장 — 인원·OpEx를 최소화한 로열티 홀딩 모델(비GAAP)."),
])}

{compete_html}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '매출 믹스')}
{fig_block(charts['03'], 'Jemperli 브리지')}
{fig_block(charts['06'], '두 스트림')}
<table>
  <tr><th>수익원</th><th>상태</th><th>규모·조건</th></tr>
  <tr><td>Jemperli 로열티 (GSK)</td><td><b>본체</b></td><td>Q1'26 <b>$24.7M</b> (+44%) · GSK 판매 $313M · 피크 가정 연 &gt;$390M(’29E)</td></tr>
  <tr><td>imsidolimab (Vanda)</td><td>옵션</td><td>GPP <b>PDUFA 2026-12-12</b> · 승인 시 로열티·마일스톤</td></tr>
  <tr><td>일회성 라이선스/마일스톤</td><td>간헐</td><td>Q3–Q4'25 매출 스파이크 요인 · Q1'25 Vanda $9.7M 기저</td></tr>
  <tr><td>자체 제품매출</td><td>없음</td><td>상업화 주체는 GSK/Vanda</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 지금 분기 ‘정상 런레이트’에 가까운 건 <b>Jemperli 로열티 ~$25M/분기</b> 감각이다.
Q3/Q4처럼 큰 숫자는 마일스톤이 섞인 구간일 수 있다.</div>
{gloss([
    ("Collaboration revenue", "파트너 판매에 따른 로열티·라이선스 인식 매출."),
    ("Peak sales guidance", "GSK가 제시한 Jemperli 피크 판매 가정(>$2.7B) — ANAB 로열티 환산의 입력."),
    ("PDUFA", "FDA 심사 목표일 — imsidolimab GPP 승인/거절 이벤트."),
])}

<h2>2. Sagard — 매출과 현금의 간극</h2>
{fig_block(charts['04'], 'Sagard 스택')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>Sagard 누적 수취(회사 추정)</td><td>~$275M (로열티+세일즈 마일스톤, ~Q1'26)</td></tr>
  <tr><td>잔여 상환 목표</td><td>~$325M · <b>~2027 Q2 말</b> 완료 예상</td></tr>
  <tr><td>BS ‘미래 로열티 매각’ 부채</td><td><b>$263.7M</b> (3/31/26) vs YE'25 $276.5M</td></tr>
  <tr><td>관련 비현금 이자</td><td>Q1'26 <b>$20.9M</b> — 순이익을 깎음</td></tr>
</table>
<div class="box"><b>핵심:</b> 회계상 로열티는 잡혀도, Sagard 상환이 끝나기 전(~E Q2'27)에는
‘고마진 로열티 현금이 온전히 ANAB 주머니로’ 오기 어렵다.
피벗 thesis의 본격 현금화는 <u>상환 완료 이후</u>다.</div>
{gloss([
    ("Sale of future royalties", "미래 로열티를 담보로 선자금을 받은 구조(비소구)."),
    ("Non-cash interest", "부채 유효이자 — 현금 이자와 다를 수 있으나 손익을 압박."),
    ("Non-recourse", "담보 범위 밖 회사 자산으로 상환 청구가 제한되는 형태."),
])}

<h2>3. 비용 · 현금 · 자본환원</h2>
{fig_block(charts['05'], 'OpEx·현금')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>Q1'26 협업매출 / 순손실</td><td>$25.6M / <b>$52.9M</b> ($1.84/주)</td></tr>
  <tr><td>Q1'26 R&amp;D / G&amp;A</td><td>$34.0M / $26.2M — <b>스핀오프 전 혼재</b></td></tr>
  <tr><td>현금·투자 (3/31/26)</td><td><b>$286.5M</b> (YE'25 $311.6M)</td></tr>
  <tr><td>스핀오프</td><td>2026-04-20 완료 · Q2부터 First Tracks를 중단영업 재분류 예정</td></tr>
  <tr><td>자사주 매입</td><td>한도 <b>$100M</b> · ~2026-12-31 (의무 아님)</td></tr>
  <tr><td>오늘 실적</td><td><b>{EARN}</b> — 첫 ‘로열티 홀딩’에 가까운 Q2 윤곽 확인</td></tr>
</table>
<div class="easy"><b>쉽게:</b> Q1 숫자는 아직 R&amp;D 회사처럼 보인다(스핀오프 전).
오늘 Q2에서 <b>비용이 확 줄었는지·로열티가 유지되는지</b>가 피벗 검증의 첫 관문이다.</div>
{gloss([
    ("Discontinued operations", "스핀오프 부문을 손익에서 분리 표시."),
    ("Buyback", "자사주 매입 — 로열티 현금·잉여자본 환원의 한 형태."),
    ("FTE 최소화", "인원을 줄여 고정비를 낮추는 로열티 홀딩 운영."),
])}

<h2>4. 시나리오</h2>
{fig_block(charts['07'], '주가 시나리오')}
{fig_block(charts['08'], '촉매')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>95–140</td><td>Jemperli 고성장 · Sagard 순항 · PDUFA 승인 · 바이백 실행 · PT 상회</td></tr>
  <tr><td>Base</td><td>55–90</td><td>로열티 안정 · Q2 클린 P&amp;L · PT(~87) 수렴</td></tr>
  <tr><td>Bear</td><td>25–45</td><td>Jemperli 둔화 · Sagard 지연 · PDUFA 실패 · 환원 실망</td></tr>
</table>
<p><b>Breaker:</b> GSK 판매 가이던스 하향 · 적응증 실패 · Sagard 상환 지연 ·
imsidolimab CRL · 자본환원 철회 · 회계/부채 재평가</p>
<p class="small">현재가 ${PX:.2f} · 52주 고 ${H52:.2f} (근접 {NEAR_HI*100:.0f}%) · 저 ${L52:.2f} ·
업사이드 {UPSIDE*100:+.1f}%.</p>

<h2>5. 포트폴리오 위치</h2>
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>역할</td><td>미보유 · Chase <b>상</b> · SYRE/DNTH형 임상바이너리보다 <b>수익구조가 읽힘</b></td></tr>
  <tr><td>금액</td><td>실적·Sagard 확인 후 <b>C급 위성</b> 후보 (풀베팅 금지)</td></tr>
  <tr><td>타이밍</td><td><b>오늘 EARN_D5 → 신규 금지</b> · Q2 로열티·OpEx·중단영업 확인 후</td></tr>
  <tr><td>하지 말 것</td><td>피크 $390M을 현재 실적으로 착각 · Sagard 무시 · 실적 전 추격</td></tr>
</table>
<div class="easy"><b>한줄 결론:</b> 수익구조의 실체는 <u>Jemperli 로열티 성장 + Sagard 상환 후 고마진 현금 + imsidolimab 옵션</u>.
스토리는 SYRE/DNTH보다 ‘돈의 경로’가 명확하다.
다만 <b>오늘 실적창</b>과 <b>Sagard 간극</b> 때문에 지금은 워치·소화, 추격 매수는 아니다.</div>

<h2>부록 · 출처</h2>
<p class="small">
Anaptys Q1 2026 earnings release (2026-05-12) · GSK Jemperli Q1 판매 코멘트 ·
yfinance 분기 손익·BS·가격·PT ({ASOF}) · 심층분석 2026-08-12 (Chase 상 · earn {EARN}).
시나리오는 예시 밴드(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 ANAB · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_revenue_mix(),
        "03": chart_jemperli_bridge(),
        "04": chart_sagard_stack(),
        "05": chart_opex_transition(),
        "06": chart_two_streams(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("ANAB", CHART_DIR)
    charts.update(cpaths)
    compete_html = render_compete_section_html(
        charts,
        bundle,
        img_b64_fn=img_b64,
        gloss_fn=gloss,
        easy_share="<div class='easy'><b>쉽게:</b> ANAB는 로열티 피어셋에서 존재감이 커진 축. RPRX는 거대 집합체라 스케일만 비교한다.</div>",
        easy_mix="<div class='easy'><b>쉽게:</b> ANAB 인식 매출은 거의 Jemperli 로열티. Sagard 때문에 현금은 당분간 선취 상환으로 간다.</div>",
        gloss_share=[("royalty peer", "로열티·바이오파이낸스 상장사."), ("RPRX", "다각화 로열티 집합 — ANAB와 비즈니스 스케일 다름.")],
        gloss_mix=[("Product Royalties", "판매 연동 로열티."), ("Other Collab", "일회성·기타 협업.")],
    )
    html = build_html(charts, compete_html=compete_html)
    html, _px = build_and_insert_price("ANAB", CHART_DIR, html)
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
        tag="sepa-rev-anab",
        title="SEPA Revenue Structure — ANAB",
        notes=(
            "## 수익구조분석(ANAB) · AnaptysBio\n\n"
            f"로열티 피벗(First Tracks 스핀오프) · Q1 Jemperli 로열티 $24.7M · 현금 $287M\n"
            f"Sagard 잔여 ~$325M(~E Q2'27) · imsidolimab PDUFA 12/12 · px~${PX:.0f} · PT~${PT:.0f}\n\n"
            f"- Chase 상 · 업사이드 {UPSIDE*100:+.0f}% · **오늘 EARN_D5**\n"
            "- 포트: 미보유 워치 · 실적 전 신규 금지 · Q2 클린 P&L 확인 후 C급 검토\n"
        ),
    )
    print_release_result(rel, label="ANAB 수익구조 PDF")
    print(f"compete={bundle.ticker if bundle else None}\nANAB rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% near_hi={NEAR_HI*100:.0f}%")


if __name__ == "__main__":
    main()
