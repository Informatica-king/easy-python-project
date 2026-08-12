#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(SCSC) — ScanSource Specialty Tech + Intelisys · WeasyPrint PDF."""

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
PX = 51.85
PT = 54.67
H52 = 59.60
L52 = 33.76
UPSIDE = PT / PX - 1.0
NEAR_HI = PX / H52
MCAP_B = 1.05
EARN = "2026-08-20"
STOP = 51.0
COST = 57.05
SHARES = 3
OUT_PDF = [
    Path("/opt/cursor/artifacts/SCSC_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/SCSC_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/SCSC_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/SCSC_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/scsc")
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
    "teal": "#0f766e",
    "teal2": "#14b8a6",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "slate": "#334155",
    "scsc": "#0e7490",
}


def img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def save_fig(fig, name: str) -> Path:
    p = CHART_DIR / name
    fig.savefig(p, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def gloss(items: list[tuple[str, str]]) -> str:
    lis = "".join(f"<li><span class='term'>{a}</span> — {b}</li>" for a, b in items)
    return f"<div class='gloss'><div class='gloss-title'>이 블록 용어 주석</div><ul>{lis}</ul></div>"


def fig_block(path: Path, caption: str) -> str:
    return (
        f"<figure><img src='data:image/png;base64,{img_b64(path)}'/>"
        f"<figcaption>{caption}</figcaption></figure>"
    )


def chart_business_flow() -> Path:
    fig, ax = plt.subplots(figsize=(9.2, 3.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    boxes = [
        (0.1, 0.7, 1.7, 1.6, "벤더\n스페셜티\n하드웨어·SaaS", C["sand"]),
        (1.95, 0.7, 1.8, 1.6, "Specialty\nTech Dist\n$741M", C["scsc"]),
        (3.95, 0.7, 1.8, 1.6, "채널 파트너\n리셀러·MSP", C["teal"]),
        (5.95, 0.7, 1.75, 1.6, "Intelisys\nAgency\n$26M", C["gold"]),
        (7.9, 0.7, 1.85, 1.6, "순매출\n$767M\nGM~14%", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c == C["sand"] else "white"
        ax.text(
            x + w / 2, y + h / 2, t, ha="center", va="center",
            fontproperties=PROP_B, fontsize=8.2, color=tc,
        )
    ax.set_title(
        "비즈니스 플로우 — Q3 FY26 (ended Mar 31) · Specialty + Intelisys",
        fontproperties=PROP_B, fontsize=11, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    labels = ["Specialty\nTech Solutions", "Intelisys\n& Advisory"]
    sales = [740.8, 26.0]
    colors = [C["scsc"], C["gold"]]
    bars = ax.bar(labels, sales, color=colors, width=0.55)
    for b, v, pct in zip(bars, sales, [96.6, 3.4]):
        ax.text(
            b.get_x() + b.get_width() / 2, v + 12, f"${v:.0f}M\n({pct:.1f}%)",
            ha="center", fontproperties=PROP_B, fontsize=9, color=C["ink"],
        )
    ax.set_ylabel("순매출 ($M)", fontproperties=PROP)
    ax.set_ylim(0, 860)
    ax.set_title("세그먼트 순매출 — Specialty가 매출의 ~97%", fontproperties=PROP_B, fontsize=11)
    for lab in ax.get_xticklabels():
        lab.set_fontproperties(PROP)
    return save_fig(fig, "02_segment_mix.png")


def chart_gp_bridge() -> Path:
    """매출 vs 총이익 기여 — Intelisys/Recurring 마진 프리미엄."""
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.5))
    # left: GP by segment
    ax = axes[0]
    labs = ["Specialty GP", "Intelisys GP"]
    vals = [81.4, 25.7]
    cols = [C["scsc"], C["gold"]]
    bars = ax.bar(labs, vals, color=cols, width=0.55)
    for b, v, pct in zip(bars, vals, [76.0, 24.0]):
        ax.text(
            b.get_x() + b.get_width() / 2, v + 1.5, f"${v:.1f}M\n({pct:.0f}%)",
            ha="center", fontproperties=PROP_B, fontsize=8.5,
        )
    ax.set_ylim(0, 100)
    ax.set_title("총이익 기여 (Q3)", fontproperties=PROP_B, fontsize=10)
    ax.set_ylabel("$M", fontproperties=PROP)
    for lab in ax.get_xticklabels():
        lab.set_fontproperties(PROP)

    ax2 = axes[1]
    cats = ["Products\n& Services", "Recurring"]
    rev = [725.7, 41.1]
    bars2 = ax2.bar(cats, rev, color=[C["navy2"], C["teal2"]], width=0.55)
    for b, v, pct in zip(bars2, rev, [94.6, 5.4]):
        ax2.text(
            b.get_x() + b.get_width() / 2, v + 15, f"${v:.0f}M\n({pct:.1f}%)",
            ha="center", fontproperties=PROP_B, fontsize=8.5,
        )
    ax2.set_ylim(0, 860)
    ax2.set_title("매출 타입 (Q3)", fontproperties=PROP_B, fontsize=10)
    for lab in ax2.get_xticklabels():
        lab.set_fontproperties(PROP)
    fig.suptitle(
        "매출은 하드웨어 · 총이익은 Recurring/Agency가 레버",
        fontproperties=PROP_B, fontsize=11, y=1.02,
    )
    fig.tight_layout()
    return save_fig(fig, "03_gp_bridge.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    qs = ["Q3'25", "Q4'25", "Q1'26", "Q2'26", "Q3'26"]
    rev = [704.8, 812.9, 739.7, 766.5, 766.8]
    opi = [23.2, 26.6, 26.2, 19.1, 23.6]
    x = range(len(qs))
    ax.bar(x, rev, color=C["sand"], width=0.55, label="순매출")
    ax2 = ax.twinx()
    ax2.plot(list(x), opi, color=C["scsc"], marker="o", lw=2.2, label="영업이익")
    ax.set_xticks(list(x))
    ax.set_xticklabels(qs, fontproperties=PROP)
    ax.set_ylabel("순매출 ($M)", fontproperties=PROP)
    ax2.set_ylabel("영업이익 ($M)", fontproperties=PROP, color=C["scsc"])
    ax.set_title("분기 매출·영업이익 추이", fontproperties=PROP_B, fontsize=11)
    ax.legend(loc="upper left", prop=PROP, fontsize=8)
    ax2.legend(loc="upper right", prop=PROP, fontsize=8)
    return save_fig(fig, "04_quarterly.png")


def chart_cash_fcf() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.5))
    labels = ["현금\n(3/31)", "총부채\n(근사)", "Q3 FCF", "YTD FCF", "자사주\n(Q3)"]
    vals = [120, 102, 69, 119, 33]
    colors = [C["teal"], C["slate"], C["green"], C["navy"], C["gold"]]
    bars = ax.bar(labels, vals, color=colors, width=0.58)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2, v + 3, f"${v}",
            ha="center", fontproperties=PROP_B, fontsize=9,
        )
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_ylim(0, 145)
    ax.set_title(
        "현금·부채·FCF · 순부채 레버리지 ≈0 · FY26 FCF 가이던스 ≥$90M",
        fontproperties=PROP_B, fontsize=10,
    )
    for lab in ax.get_xticklabels():
        lab.set_fontproperties(PROP)
    return save_fig(fig, "05_cash_fcf.png")


def chart_margin_stack() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    labels = ["매출총이익률", "영업이익률", "순이익률"]
    vals = [14.0, 3.1, 2.2]  # Q3 approx GP 107/767, OI 23.6/767, NI 16.9/767
    bars = ax.barh(labels, vals, color=[C["teal"], C["scsc"], C["navy"]], height=0.55)
    for b, v in zip(bars, vals):
        ax.text(v + 0.3, b.get_y() + b.get_height() / 2, f"{v:.1f}%",
                va="center", fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(0, 20)
    ax.set_xlabel("% of sales (Q3 FY26)", fontproperties=PROP)
    ax.set_title("마진 스택 — 유통 업종 전형 (얇은 Op/Net)", fontproperties=PROP_B, fontsize=11)
    for lab in ax.get_yticklabels():
        lab.set_fontproperties(PROP)
    return save_fig(fig, "06_margin_stack.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    items = [
        (0.3, 0.5, 2.9, 2.2, C["red"], "Bear\n$39–47", "채널 둔화\n재고·운전자본\n마진 압박"),
        (3.55, 0.5, 2.9, 2.2, C["navy"], "Base\n$50–58", "Specialty +중한\nFCF≥90\nPT 수렴"),
        (6.8, 0.5, 2.9, 2.2, C["green"], "Bull\n$60–71", "Recurring↑\nConverged Comm\n멀티플 재평가"),
    ]
    for x, y, w, h, c, title, body in items:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        ax.text(x + w / 2, y + h - 0.55, title, ha="center",
                fontproperties=PROP_B, fontsize=11, color="white")
        ax.text(x + w / 2, y + 0.55, body, ha="center",
                fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title(f"시나리오 · px~${PX:.0f} · PT~${PT:.0f} ({UPSIDE*100:+.0f}%)",
                 fontproperties=PROP_B, fontsize=11)
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    items = [
        (0.2, 0.4, 3.0, 2.1, C["red"], "08-20\nEARN_D5", "Q4/FY26\n가이던스·FCF"),
        (3.5, 0.4, 3.0, 2.1, C["scsc"], "Converged\nCommunications", "Specialty+Intelisys\n통합 유닛"),
        (6.8, 0.4, 3.0, 2.1, C["gold"], "자사주·운전자본", "잔여 $146M\n재고·AR 사이클"),
    ]
    for x, y, w, h, c, title, body in items:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=1.5,
            )
        )
        ax.text(x + w / 2, y + h - 0.55, title, ha="center",
                fontproperties=PROP_B, fontsize=10, color="white")
        ax.text(x + w / 2, y + 0.55, body, ha="center",
                fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title("촉매 — 실적창 · 조직 · 자본환원", fontproperties=PROP_B, fontsize=11)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", f"홀드 {SHARES}주\ngrade B · no_add", C["navy"]),
        (3.4, 1.6, 2.8, 1.0, "손익", f"평단 ${COST:.0f}\n마크 ${PX:.0f} (−9%)", C["teal"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", f"stop ${STOP:.0f}\nEARN {EARN[5:]}", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "stop 경계 · 실적창 · 유통 마진·재고", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "Specialty 성장 · FCF·순부채≈0", C["navy2"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=1.5,
            )
        )
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(
            x + w / 2, y + 0.35, body, ha="center", va="center",
            fontproperties=PROP, fontsize=8.5, color="white",
        )
    ax.set_title(
        "실행 포지션 — 보유·추가금지 · stop $51 경계 · EARN_D5",
        fontproperties=PROP_B, fontsize=11, pad=4,
    )
    return save_fig(fig, "09_position.png")


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    css = """
    @page { size: A4; margin: 14mm 12mm; }
    body { font-family: NanumGothic, sans-serif; color: #1c1917; font-size: 9.5pt; line-height: 1.45; }
    h1 { font-size: 20pt; color: #1e3a5f; margin: 0 0 6px; }
    h2 { font-size: 13pt; color: #0f766e; border-bottom: 2px solid #0f766e; padding-bottom: 3px; margin-top: 16px; }
    table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 8.5pt; }
    th, td { border: 1px solid #cbd5e1; padding: 4px 6px; text-align: left; }
    th { background: #e0f2fe; color: #0c4a6e; }
    figure { margin: 8px 0; text-align: center; }
    figure img { max-width: 100%; }
    figcaption { font-size: 7.5pt; color: #64748b; margin-top: 2px; }
    .easy { background: #f0fdfa; border-left: 4px solid #0f766e; padding: 8px 10px; margin: 8px 0; }
    .box { background: #f8fafc; border: 1px solid #cbd5e1; padding: 10px; margin: 10px 0; border-radius: 4px; }
    .gloss { background: #fffbeb; border: 1px solid #fcd34d; padding: 6px 10px; margin: 6px 0; font-size: 8pt; }
    .gloss-title { font-weight: 700; color: #92400e; margin-bottom: 2px; }
    .term { font-weight: 700; color: #1e3a5f; }
    .small { font-size: 7.5pt; color: #64748b; }
    .tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 8pt; font-weight: 700; margin-right: 4px; }
    .tag.good { background: #dcfce7; color: #166534; }
    .tag.warn { background: #fef3c7; color: #92400e; }
    .tag.bad { background: #fee2e2; color: #9f1239; }
    .kpi { display: inline-block; background: #f1f5f9; border-radius: 6px;
      padding: 8px 12px; margin: 6px; min-width: 100px; text-align: center; }
    .kpi .l { font-size: 7.5pt; color: #64748b; }
    .kpi .v { font-size: 12pt; font-weight: 700; color: #1e3a5f; }
    .kpi .s { font-size: 7.5pt; color: #0e7490; }
    section.cover { margin-bottom: 8px; }
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>SCSC 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>SCSC 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">ScanSource · Specialty Technology Solutions + Intelisys &amp; Advisory</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q3 FY26 (ended Mar 31) · 다음 실적 <b>{EARN}</b> (EARN_D5)</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.2f}</div><div class="s">시총 ~${MCAP_B:.2f}B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.0f}</div><div class="s">업사이드 {UPSIDE*100:+.0f}%</div></span>
    <span class="kpi"><div class="l">Q3 매출</div><div class="v">$767M</div><div class="s">YoY +8.8%</div></span>
    <span class="kpi"><div class="l">현금·FCF</div><div class="v">$120M</div><div class="s">Q3 FCF $69M</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">보유 {SHARES}주 · grade B</span>
    <span class="tag warn">no_add · stop ${STOP:.0f} 경계</span>
    <span class="tag bad">EARN_D5 {EARN[5:]} · 평단 ${COST:.0f} (−9%)</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>스페셜티 IT 유통(하드웨어·SaaS) + 고마진 Intelisys 에이전시</b>로,
매출의 ~97%는 Specialty지만 <b>총이익의 ~24%·Recurring GP(~35% of GP)</b>가 마진 레버다.
Q3 FY26 순매출 <b>$766.8M(+8.8%)</b> · Specialty <b>$740.8M(+9.2%)</b> ·
순부채 레버리지 ≈0 · FY26 FCF 가이던스 <b>≥$90M</b>(상향).
당신 계좌는 <b>3주 홀드·추가금지·stop $51</b>이며, <b>{EARN}</b> 실적창이 즉시 리스크다.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 큰 돈은 <b>하드웨어를 채널에 넘기며</b> 벌고,
진짜 마진은 <b>연결·클라우드 수수료(Intelisys)·구독</b>에서 붙는다.
유통이라 매출총이익률(~14%)·영업이익률(~3%)은 얇다 — <u>규모·운전자본·FCF</u>가 핵심이다.</div>
{gloss([
    ("Specialty Technology Solutions", "도매/리세일 모델의 스페셜티 하드웨어·SaaS·구독. NA+브라질."),
    ("Intelisys & Advisory", "채널·엔드유저 대상 커넥티비티·UCaaS·보안·클라우드 에이전시/자문."),
    ("Recurring revenue", "에이전시 수수료·managed connectivity·SaaS·구독·임대 등 반복 매출."),
])}

{compete_html}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '세그먼트 매출')}
{fig_block(charts['03'], '총이익 vs 매출 타입')}
<table>
  <tr><th>항목</th><th>Q3 FY26</th><th>YoY</th><th>메모</th></tr>
  <tr><td>연결 순매출</td><td><b>$766.8M</b></td><td>+8.8%</td><td>non-GAAP +7.6%</td></tr>
  <tr><td>Specialty Tech</td><td><b>$740.8M</b></td><td>+9.2%</td><td>NA 대부분 기술 성장</td></tr>
  <tr><td>Intelisys &amp; Advisory</td><td>$26.0M</td><td>−1.5%</td><td>Resourcive 약세 · QoQ +4%</td></tr>
  <tr><td>Products &amp; services</td><td>$725.7M</td><td>+9.1%</td><td>매출의 ~95%</td></tr>
  <tr><td>Recurring</td><td>$41.1M</td><td>+3.6%</td><td>매출 ~5% · <b>GP의 ~35%</b></td></tr>
  <tr><td>총이익 / GM</td><td>$107.1M / ~14.0%</td><td>+6.9%</td><td>Specialty GP $81.4M · Intelisys $25.7M</td></tr>
  <tr><td>영업이익 / NI / EPS</td><td>$23.6M / $16.9M / $0.78</td><td>—</td><td>얇은 마진 · 자사주 희석 축소</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 손익계산서 ‘큰 숫자’는 Specialty 유통.
다만 Intelisys는 매출은 작아도 <b>Adj.EBITDA 마진 ~42%</b>급 — 회사는 Converged Communications로
Specialty 통신 + Intelisys CX를 묶어 파트너 경험을 합치려 한다.</div>
{gloss([
    ("Intelisys annualized net billings", "에이전시가 중개하는 연환산 빌링(~$2.88B). 회사 인식 매출과 다름."),
    ("Gross profit mix", "매출 비중 ≠ 이익 비중. Recurring/Agency가 GP를 끌어올림."),
    ("Converged Communications", "Specialty Communications + Intelisys CX 통합 사업유닛."),
])}

<h2>2. 현금 · 운전자본 · 환원</h2>
{fig_block(charts['04'], '분기 추이')}
{fig_block(charts['05'], '현금·FCF')}
{fig_block(charts['06'], '마진 스택')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>현금 (3/31/26)</td><td><b>$120.3M</b></td></tr>
  <tr><td>총부채 / 순부채 레버리지</td><td>~$102M / <b>≈0x</b> (TTM Adj.EBITDA)</td></tr>
  <tr><td>재고 / 매출채권</td><td>$487M / $628M — 운전자본이 시즌·수요에 민감</td></tr>
  <tr><td>Q3 / YTD FCF</td><td><b>$69M</b> / $119M</td></tr>
  <tr><td>FY26 FCF 가이던스</td><td><b>≥$90M</b> (상향) · 매출·Adj.EBITDA 가이던스 유지</td></tr>
  <tr><td>자사주 (Q3)</td><td>$33M · 잔여 승인 <b>$146M</b></td></tr>
</table>
<div class="easy"><b>쉽게:</b> 유통사는 이익보다 <b>재고·채권을 잘 돌리고 FCF를 뽑는 능력</b>이 성적표다.
레버리지≈0 + FCF 상향은 방어적. 대신 수요 둔화 시 재고가 먼저 독이 된다.</div>

<h2>3. 시나리오 · 촉매 · 포트</h2>
{fig_block(charts['07'], '시나리오')}
{fig_block(charts['08'], '촉매')}
{fig_block(charts['09'], '포지션')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>60–71</td><td>Specialty 지속 · Recurring GP↑ · Converged 가시화 · PT 상단</td></tr>
  <tr><td>Base</td><td>50–58</td><td>FY26 가이던스 달성 · FCF≥90 · PT(~55) 수렴</td></tr>
  <tr><td>Bear</td><td>39–47</td><td>채널 둔화 · 재고/마진 압박 · 실적 미스 · stop 이탈</td></tr>
</table>
<div class="box">
<b>계좌 기준 실행</b><br/>
· 역할: <b>홀드 {SHARES}주</b> · grade <b>B</b> · <b>추가금지(no_add)</b> · 물타기 금지<br/>
· 가격: 마크 ~${PX:.2f} · 평단 ${COST:.2f} (−9.1%) · PT ~${PT:.0f}({UPSIDE*100:+.0f}%) · 52주고 ${H52:.1f} (근접 {NEAR_HI*100:.0f}%)<br/>
· <b>stop ${STOP:.0f}</b> — 현재가가 경계. 종가 이탈 시 기계적 청산 검토<br/>
· 트리거: <b>EARN_D5 {EARN}</b> — Specialty 성장·GM·FCF·FY 가이던스 톤 확인<br/>
· Breaker: 가이던스 컷 · 재고 급증·마진 붕괴 · Intelisys 빌링 역성장 고착
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>스페셜티 유통 규모 + Recurring/Agency 마진</u>으로 건강하고 FCF·레버리지도 양호.
다만 당신 포지션은 <b>손절 경계·실적창·이미 −9%</b>라서 추격·추가는 금지, <b>{EARN} 소화 또는 stop 준수</b>가 우선이다.</div>

<h2>부록 · 출처</h2>
<p class="small">
ScanSource Q3 FY2026 earnings release / BusinessWire (2026-05-07) · earnings infographic ·
콜 요약(Converged Communications, FCF≥$90M) · yfinance 가격·PT·BS ({ASOF}) ·
portfolio_watch SSOT (SCSC 3주 · stop $51 · EARN ~08-20).
피어 점유/믹스는 방향 비교용 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 SCSC · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_gp_bridge(),
        "04": chart_quarterly(),
        "05": chart_cash_fcf(),
        "06": chart_margin_stack(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("SCSC", CHART_DIR)
    charts.update(cpaths)
    compete_html = render_compete_section_html(
        charts,
        bundle,
        img_b64_fn=img_b64,
        gloss_fn=gloss,
        easy_share=(
            "<div class='easy'><b>쉽게:</b> SNX/ARW/AVT 초대형 브로드라인 대비 "
            "SCSC는 스페셜티·소형. 점유 ‘상승’은 피어셋 내 상대 스케일 감각이지 "
            "글로벌 IT유통 점유가 아니다.</div>"
        ),
        easy_mix=(
            "<div class='easy'><b>쉽게:</b> SCSC 매출은 Hardware Dist가 ~90%. "
            "NSIT/PLUS는 Solutions 비중이 더 높다. "
            "SCSC의 진짜 차별은 매출이 아니라 <b>Recurring/Agency 총이익</b> 쪽이다.</div>"
        ),
        gloss_share=[
            ("specialty vs broadline", "스페셜티(바코드·POS·통신 등) vs 범용 부품·IT 유통."),
            ("피어셋 점유", "선택 상장사 매출 스케일 정규화 — 절대 시장점유 ≠."),
        ],
        gloss_mix=[
            ("Hardware Dist", "도매 하드웨어·제품 매출."),
            ("Recurring/Agency", "수수료·구독·managed connectivity 등 반복성."),
        ],
    )
    html = build_html(charts, compete_html=compete_html)
    html, _px = build_and_insert_price("SCSC", CHART_DIR, html)
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
        tag="sepa-rev-scsc",
        title="SEPA Revenue Structure — SCSC",
        notes=(
            "## 수익구조분석(SCSC) · ScanSource\n\n"
            f"Q3 FY26 매출 $766.8M(+8.8%) · Specialty $740.8M(+9.2%) · Intelisys $26M\n"
            f"Recurring $41M · GP~$107M · 현금 $120M · 순부채≈0 · FCF 가이던스 ≥$90M\n"
            f"px~${PX:.2f} · PT~${PT:.0f} · 업사이드 {UPSIDE*100:+.0f}% · stop ${STOP:.0f}\n\n"
            f"- 포트: 홀드 {SHARES}주 · grade B · no_add · EARN_D5 {EARN}\n"
            "- 경쟁 챕터(sepa.rev_compete) 포함 · 추격·추가 금지\n"
        ),
    )
    print_release_result(rel, label="SCSC 수익구조 PDF")
    print(
        f"compete={bundle.ticker if bundle else None}\n"
        f"SCSC rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% "
        f"near_hi={NEAR_HI*100:.0f}% earn={EARN} stop={STOP}"
    )


if __name__ == "__main__":
    main()
