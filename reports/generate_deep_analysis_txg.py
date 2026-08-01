#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""심층분석(TXG) — 10x Genomics 단일종목 심층 + Chase/A′ + 1년 주가 · WeasyPrint PDF."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from weasyprint import HTML

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sepa.rev_price_chart import build_and_insert_price  # noqa: E402

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
ASOF = "2026-08-01"
OUT_PDF = [
    Path("/opt/cursor/artifacts/TXG_Deep_Analysis.pdf"),
    Path("/workspace/reports/TXG_Deep_Analysis.pdf"),
    Path("/workspace/assets/TXG_Deep_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/TXG_Deep_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/txg")
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
    "txg": "#4c1d95",
    "chrom": "#7c3aed",
    "vis": "#0ea5e9",
    "xen": "#a16207",
}

# Live snapshot 2026-08-01
PX = 47.27
PT = 41.54
H52 = 50.34
L52 = 11.16
UPSIDE = PT / PX - 1.0  # negative
NEAR_H = PX / H52
MCAP = 6.0  # $B approx
EARN = "2026-08-06"
CHASE = "하·과열"
CHASE_DETAIL = (
    "하·과열 — EPS 4/4 Beat는 강하나 현재가가 PT 평균·52주 고점권. "
    "업사이드 음수·EARN_D5(08-06). 추격·신규 분할 비추."
)


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
        (0.1, 0.7, 1.7, 1.6, "연구실·바이오\n파마 R&D", C["sand"]),
        (1.95, 0.7, 1.75, 1.6, "Chromium\n단일세포", C["chrom"]),
        (3.9, 0.7, 1.75, 1.6, "Visium\n공간전사", C["vis"]),
        (5.85, 0.7, 1.75, 1.6, "Xenium\nIn situ", C["xen"]),
        (7.8, 0.7, 1.9, 1.6, "장비+소모품\n매출", C["txg"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c == C["sand"] else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.5, color=tc)
    for x in (1.85, 3.75, 5.7, 7.65):
        ax.annotate(
            "", xy=(x + 0.08, 1.5), xytext=(x - 0.08, 1.5),
            arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6),
        )
    ax.set_title(
        "비즈니스 한눈에 — 단일세포·공간 생물학 도구를 판다",
        fontproperties=PROP_B, fontsize=12, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_revenue_trend() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    qs = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [154.9, 172.9, 149.0, 166.0, 150.8]
    ax.plot(qs, rev, marker="o", color=C["txg"], lw=2)
    ax.fill_between(range(5), rev, alpha=0.12, color=C["chrom"])
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("분기 매출 ($M)", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(rev):
        ax.text(i, v + 2.5, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)

    ax = axes[1]
    oi = [-48.5, -10.6, -32.2, -19.5, -17.0]
    colors = [C["red"] if v < 0 else C["green"] for v in oi]
    ax.bar(qs, oi, color=colors, width=0.55)
    ax.axhline(0, color="#94a3b8", lw=0.8)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("영업이익 ($M) · 손실 축소 추세", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(oi):
        ax.text(i, v - 3.5 if v < 0 else v + 1.5, f"{v:.0f}", ha="center",
                fontproperties=PROP, fontsize=7.5)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_opinc.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    qs = ["Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    actual = [0.48, -0.02, 0.07, 0.07]
    est = [-0.08, -0.07, -0.04, -0.06]
    x = range(len(qs))
    ax.bar([i - 0.18 for i in x], est, width=0.35, color=C["sand"], label="Estimate")
    ax.bar([i + 0.18 for i in x], actual, width=0.35, color=C["txg"], label="Actual")
    ax.axhline(0, color="#94a3b8", lw=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(qs, fontproperties=PROP)
    ax.set_ylabel("EPS ($)", fontproperties=PROP)
    ax.set_title("EPS 서프라이즈 — 4/4 Beat (평균 서프 강)", fontproperties=PROP_B, fontsize=12)
    ax.legend(prop=PROP, fontsize=8)
    fig.tight_layout()
    return save_fig(fig, "03_eps_surprise.png")


def chart_valuation() -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(9.4, 3.5))
    ax = axes[0]
    ax.bar(["현재", "PT평균", "52주고"], [PX, PT, H52], color=[C["txg"], C["gold"], C["red"]], width=0.55)
    ax.set_title("가격 vs PT vs 고점", fontproperties=PROP_B, fontsize=10)
    for i, v in enumerate([PX, PT, H52]):
        ax.text(i, v + 0.8, f"${v:.1f}", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    ax.bar(["업사이드"], [UPSIDE * 100], color=C["red"], width=0.45)
    ax.axhline(0, color="#94a3b8", lw=0.8)
    ax.set_title(f"PT 업사이드 {UPSIDE*100:.1f}%", fontproperties=PROP_B, fontsize=10)
    ax.text(0, UPSIDE * 100 - 1.5, "프리미엄", ha="center", fontproperties=PROP_B, fontsize=9, color="white")
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[2]
    ax.bar(["고점근접"], [NEAR_H * 100], color=C["gold"], width=0.45)
    ax.set_ylim(0, 105)
    ax.set_title(f"52주 고점 대비 {NEAR_H*100:.0f}%", fontproperties=PROP_B, fontsize=10)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.suptitle("밸류 — Beat와 별개로 가격이 이미 비쌈", fontproperties=PROP_B, fontsize=11, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "04_valuation.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 22, 30, C["red"]),
        ("Base", 32, 40, C["teal"]),
        ("Bull", 42, 50, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}–{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"현재 ${PX:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, "PT~$42", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 밴드 (예시 · 투자권유 아님)", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(18, 55)
    fig.tight_layout()
    return save_fig(fig, "05_scenarios.png")


def chart_buy_gate() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.04, "A′", "미충족", "MA20 이격\n+ EARN_D5", C["red"]),
        (0.28, "B", "미충족", "돌파·거래량\n조건 없음", C["slate"]),
        (0.52, "Chase", "하·과열", "PT 프리미엄\n고점권", C["txg"]),
        (0.76, "실적", "08-06", "D-5 창\n추가·추격 X", C["gold"]),
    ]
    for x, tag, title, body, c in items:
        ax.add_patch(
            FancyBboxPatch(
                (x, 0.25), 0.2, 0.55, boxstyle="round,pad=0.02,rounding_size=0.04",
                facecolor=c, edgecolor="white", lw=1.5, transform=ax.transAxes,
            )
        )
        ax.text(x + 0.1, 0.68, tag, ha="center", transform=ax.transAxes,
                fontproperties=PROP_B, fontsize=11, color="white")
        ax.text(x + 0.1, 0.55, title, ha="center", transform=ax.transAxes,
                fontproperties=PROP_B, fontsize=10, color="white")
        ax.text(x + 0.1, 0.38, body, ha="center", transform=ax.transAxes,
                fontproperties=PROP, fontsize=7.5, color="white")
    ax.set_title("매수 시나리오 게이트 (RS≥70용 A′) — A/B 0건 · 적극 고지", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "06_buy_gate.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "미보유 워치\n우선순위 낮음", C["txg"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "신규 비추\n위성도 후순위", C["teal"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", "08-06 소화\n깊은 눌림만", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "PT 대비 프리미엄 · 고점권 · EARN_D5 · 연구비 사이클", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "GM~70% · EPS 4/4 Beat · 영업손실 축소 중", C["navy"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=1.5,
            )
        )
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.35, body, ha="center", va="center",
                fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title("실행 포지션 맵 (사용자 계좌 기준)", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "07_position.png")


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
      @bottom-center {{ content:"TXG 심층분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#4c1d95; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #7c3aed; padding-bottom:3px; color:#4c1d95; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ede9fe 0%,#e0e7ff 55%,#f0fdf4 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#ede9fe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecdd3; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#f5f3ff; border-left:4px solid #7c3aed; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#4c1d95; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#7c3aed; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#4c1d95; }}
    .kpi .s {{ font-size:7.5pt; color:#7c3aed; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>TXG 심층분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>TXG 심층분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">10x Genomics · 단일세포·공간 생물학 툴 · Chromium / Visium / Xenium</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · 다음 실적 {EARN} · 시총 ~${MCAP:.1f}B</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">${PX:.2f}</div><div class="s">고점 {NEAR_H*100:.0f}%</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">${PT:.1f}</div><div class="s">{UPSIDE*100:+.1f}%</div></span>
    <span class="kpi"><div class="l">EPS Beat</div><div class="v">4/4</div><div class="s">서프 강</div></span>
    <span class="kpi"><div class="l">Q1 매출</div><div class="v">$151M</div><div class="s">GM ~70%</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag bad">Chase {CHASE}</span>
    <span class="tag warn">A′/B 0건</span>
    <span class="tag warn">EARN_D5 · 08-06</span>
  </p>
</section>

<h2>0. 한줄 Thesis · Chase</h2>
<p><b>연구실에 단일세포·공간 분석 장비와 소모품을 파는 라이프사이언스 툴 회사.</b>
펀더멘털(EPS 4/4 Beat, 매출총이익 ~70%, 영업손실 축소)은 개선 중이나,
가격이 PT·고점권에 이미 반영되어 <b>Chase {CHASE}</b>. 08-06 실적 전 추격 금지.</p>
<div class="box"><b>Chase</b><br/>{CHASE}<br/><span class="small">{CHASE_DETAIL}</span></div>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 바이오·제약 연구실이 세포를 하나씩, 조직 위치별로 볼 때 쓰는
기계와 시약을 판다. 제품 퀄리티는 좋은데, <b>주가가 너무 앞서가 있다</b>.</div>
{gloss([
    ("Chromium", "단일세포 분석 플랫폼 (주력 설치기반)."),
    ("Visium / Xenium", "공간 전사체·In situ 분석. 성장 스토리."),
    ("EARN_D5", "실적일 전후 5일 창 — 신규 분할 차단."),
])}

<h2>1. 매출·손익 추이</h2>
{fig_block(charts['02'], '분기 매출 · 영업이익')}
<table>
  <tr><th>항목</th><th>Q1'26</th><th>메모</th></tr>
  <tr><td>매출</td><td>$150.8M</td><td>전년 $154.9M · 소폭 YoY↓ / 시즌·수요 혼조</td></tr>
  <tr><td>매출총이익</td><td>$106.2M</td><td>GM ~70% — 툴 비즈니스 품질</td></tr>
  <tr><td>영업이익</td><td>−$17.0M</td><td>전년 −$48.5M 대비 손실 대폭 축소</td></tr>
  <tr><td>순이익</td><td>−$13.5M</td><td>여전히 적자이나 개선</td></tr>
  <tr><td>TTM 매출</td><td>~$0.64B</td><td>성장률 소폭 음수</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 팔아서 남기는 마진(총이익)은 높다. 아직 전체로는 적자지만,
적자 폭이 줄어드는 중이라 “망가지는 회사” 그림은 아니다. 문제는 <b>가격</b>이다.</div>

<h2>2. 서프라이즈 · 밸류</h2>
{fig_block(charts['03'], 'EPS Beat')}
{fig_block(charts['04'], '밸류에이션')}
<ul>
  <li>EPS 4분기 연속 Beat · 컨센서스 대비 서프라이즈 강함</li>
  <li>현재 ${PX:.2f} vs PT ${PT:.1f} → <b>업사이드 {UPSIDE*100:.1f}%</b> (비쌈)</li>
  <li>52주 고점 ${H52:.2f}의 {NEAR_H*100:.0f}% — 고점권</li>
  <li>Forward P/E 매우 높음(적자→흑자 전환 기대가 가격에 선반영)</li>
</ul>

<h2>3. 매수 시나리오 게이트 (A′)</h2>
{fig_block(charts['06'], 'A′/B 게이트')}
<div class="box" style="border-color:#9f1239;background:#fff1f2">
<b>적극 고지: 매수 시나리오 A′/B = 0건</b><br/>
· A′(RS≥70 얕은 눌림): MA20 이격(+6%대) · RSI 경계 · <b>EARN_D5 차단</b><br/>
· B(돌파): 해당 없음<br/>
· → 오늘은 “사야 한다”가 아니라 <b>관망</b>
</div>
{gloss([
    ("A′", "MA200위+정배열+(MA20|스윙L)+RSI42–62+고점−1%~−8%+거래량+실적창밖."),
    ("B", "돌파+거래량 급증+RSI&lt;70+실적창밖."),
])}

<h2>4. 시나리오 · 촉매</h2>
{fig_block(charts['05'], '주가 시나리오')}
<table>
  <tr><th>촉매</th><th>내용</th></tr>
  <tr><td>08-06 실적</td><td>가이드·소모품 성장·마진. 이벤트 갭 베팅 비추</td></tr>
  <tr><td>연구비 사이클</td><td>NIH/바이오 예산·고객 CapEx 둔화 리스크</td></tr>
  <tr><td>제품 믹스</td><td>Xenium/Visium 채택 vs Chromium 성숙</td></tr>
  <tr><td>밸류 정상화</td><td>PT~$42 아래로의 되돌림이 “기회” 조건</td></tr>
</table>

<h2>5. 포트 실행</h2>
{fig_block(charts['07'], '포지션 맵')}
<div class="box">
<b>계좌 기준 (08-01)</b><br/>
· 보유 여부: <b>미보유</b> · 코어(ECPG/AMRX)·위성 우선순위와 무관하게 <b>신규 비추</b><br/>
· 현금 여유 있어도 SCHD/실적창(RELY·ECPG 08-05) 관리가 먼저<br/>
· 재평가: 08-06 소화 후 · PT 대비 할인·MA20 근처 A′ 재스캔
</div>
<div class="easy"><b>한줄 결론:</b> 비즈니스 품질(마진·Beat)은 괜찮지만
<u>가격·실적창·Chase 하</u>가 막는다. <b>추격하지 말 것.</b></div>

<h2>부록 · 출처</h2>
<p class="small">
yfinance 가격·PT·실적 히스토리 · 분기 income statement ({ASOF}).
시나리오·게이트는 작업용(투자 권유 아님). Chase 라벨은 심층 RR 관례 + 포트 맥락.
</p>
<p class="small">생성: 심층분석(TXG) · {ASOF} · WeasyPrint + NanumGothic · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_revenue_trend(),
        "03": chart_eps_surprise(),
        "04": chart_valuation(),
        "05": chart_scenarios(),
        "06": chart_buy_gate(),
        "07": chart_position(),
    }
    html = build_html(charts)
    html, _px = build_and_insert_price("TXG", CHART_DIR, html)
    if _px.ok:
        print(f"price-charts {_px.candle_path} {_px.momentum_path}")
    else:
        print(f"price-charts SKIP {_px.error}")
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    doc = HTML(filename=str(OUT_HTML))
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        doc.write_pdf(str(p))
        print(f"PDF {p} {p.stat().st_size}")
    print(f"Chase={CHASE} A'/B=0 earn={EARN} px={PX} pt={PT} upside={UPSIDE*100:.1f}%")


if __name__ == "__main__":
    main()
