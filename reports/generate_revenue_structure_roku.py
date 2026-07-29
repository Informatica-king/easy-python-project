#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(ROKU) — Advertising / Subscriptions / Devices + 초보용 설명 + WeasyPrint PDF."""

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

from sepa.rev_compete import build_compete_charts  # noqa: E402

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
ASOF = "2026-07-29"
OUT_PDF = [
    Path("/opt/cursor/artifacts/ROKU_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/ROKU_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/ROKU_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/ROKU_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/roku")
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
    "roku": "#6c2bd9",
    "ad": "#0e7490",
    "sub": "#047857",
    "dev": "#a16207",
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
        (0.1, 0.7, 1.7, 1.6, "시청자\n스트리밍\n가구", C["sand"]),
        (1.95, 0.7, 1.75, 1.6, "Roku OS\n·홈·추천", C["roku"]),
        (3.85, 0.7, 1.85, 1.6, "광고주\n+ SVOD\n파트너", C["teal"]),
        (5.85, 0.7, 1.85, 1.6, "광고·구독\n플랫폼 매출", C["ad"]),
        (7.9, 0.7, 1.85, 1.6, "기기(적자)\n→ 가구 유입", C["dev"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c in (C["sand"], C["dev"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.2, color=tc)
    ax.set_title("비즈니스 한눈에 — 기기로 모으고, 플랫폼으로 번다", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    # Q1'26 $M
    sizes = [612.7, 518.5, 117.6]
    labels = ["Advertising\n$613M (49%)", "Subscriptions\n$519M (42%)", "Devices\n$118M (9%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["ad"], C["sub"], C["dev"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("Q1'26 매출 믹스 (총 $1.25B)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    segs = ["Advertising", "Subscriptions", "Devices"]
    gm = [60.5, 41.1, -16.3]
    colors = [C["ad"], C["sub"], C["red"]]
    bars = ax.bar(segs, gm, color=colors, width=0.55)
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_ylabel("총이익률 %", fontproperties=PROP)
    ax.set_title("세그먼트 총이익률 (Q1'26)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, gm):
        ax.text(b.get_x() + b.get_width() / 2, v + (1.5 if v >= 0 else -4), f"{v:.1f}%",
                ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_platform_growth() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    q = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    adv = [482.8, 539.1, 591.2, 714.7, 612.7]
    sub = [398.0, 436.4, 473.4, 509.3, 518.5]
    x = range(len(q))
    ax.bar(x, adv, color=C["ad"], label="Advertising", width=0.55)
    ax.bar(x, sub, bottom=adv, color=C["sub"], label="Subscriptions", width=0.55)
    ax.set_xticks(list(x))
    ax.set_xticklabels(q, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("플랫폼 매출 추이 (Ad+Sub)", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8)

    ax = axes[1]
    yoy = [27, 30, 28, -16, 22]
    labs = ["Ad\nYoY", "Sub\nYoY", "Platform\nYoY", "Devices\nYoY", "Total\nYoY"]
    cols = [C["ad"], C["sub"], C["teal"], C["red"], C["navy"]]
    bars = ax.bar(labs, yoy, color=cols, width=0.55)
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("Q1'26 성장률 스냅샷", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, yoy):
        ax.text(b.get_x() + b.get_width() / 2, v + (1.2 if v >= 0 else -3), f"{v}%",
                ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)
    fig.tight_layout()
    return save_fig(fig, "03_platform_growth.png")


def chart_flywheel() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")
    layers = [
        (0.3, 3.1, 9.4, 0.85, C["navy"], "white",
         "④ FCF/주 — 북극성 · 회사 목표 $1B FCF by 2028 (또는 그 전)"),
        (0.3, 2.15, 9.4, 0.8, C["ad"], "white",
         "③ Advertising — 1P 데이터·RX·프로그램매틱 · GM ~60% · 이익 엔진"),
        (0.3, 1.2, 9.4, 0.8, C["sub"], "white",
         "② Subscriptions — 프리미엄 가입·Frndly/Howdy · GM ~41% · 다각화"),
        (0.3, 0.25, 9.4, 0.8, C["dev"], C["ink"],
         "① Devices — 플레이어·자사 TV 판매(적자) · OEM Roku TV로 가구 확보(매출 제외)"),
    ]
    for x, y, w, h, c, tc, t in layers:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.0, color=tc)
    ax.set_title("수익 스택 (아래→위 = 유입 → 고마진 플랫폼 → FCF)", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "04_flywheel.png")


def chart_gp_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.7))
    cats = ["Ad GP", "Sub GP", "Platform\nGP", "Devices\nGP", "Total GP"]
    vals = [371.0, 213.1, 584.1, -19.1, 564.9]
    colors = [C["ad"], C["sub"], C["teal"], C["red"], C["navy"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("Q1'26 총이익 구성 — 기기가 플랫폼 GP를 깎음", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (8 if v >= 0 else -18), f"{v:.0f}",
                ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "05_gp_bridge.png")


def chart_outlook() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    labs = ["Platform\nFY26E", "Devices\nFY26E", "Total\nFY26E"]
    vals = [5000, 535, 5500]
    cols = [C["teal"], C["dev"], C["navy"]]
    bars = ax.bar(labs, vals, color=cols, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("FY26 가이던스 (회사, 상향 후)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 80, f"{v:,.0f}", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)

    ax = axes[1]
    labs2 = ["Q1'26\nAdj.EBITDA", "Q2'26E\nAdj.EBITDA", "FY26E\nAdj.EBITDA", "FCF'28\n목표"]
    vals2 = [148, 170, 675, 1000]
    cols2 = [C["teal2"], C["teal"], C["navy"], C["roku"]]
    bars = ax.bar(labs2, vals2, color=cols2, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("수익성·FCF 경로", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals2):
        ax.text(b.get_x() + b.get_width() / 2, v + 20, f"{v}", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)
    fig.tight_layout()
    return save_fig(fig, "06_outlook.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [95, 130, 160]
    highs = [120, 160, 205]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    ax.axvline(142.92, color=C["gold"], ls="--", lw=1.5)
    ax.text(145, 2.35, "현재 ~143", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.axvline(158.4, color="#2563eb", ls=":", lw=1.2)
    ax.text(160, -0.55, "PT평균 ~158", fontproperties=PROP, fontsize=7.5, color="#2563eb")
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        mid = (lo + hi) / 2
        ax.text(mid, i, f"{lo}–{hi}", ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(80, 220)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear (12M · 플랫폼·광고·가이던스)", fontproperties=PROP_B, fontsize=11)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP_B)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    items = [
        (0.25, 2.5, 3.0, 1.2, C["roku"], "white", "08-06\n실적·가이던스"),
        (3.5, 2.5, 3.0, 1.2, C["ad"], "white", "광고\n필레이트·DSP"),
        (6.75, 2.5, 3.0, 1.2, C["sub"], "white", "Premium Sub\n·Howdy/Frndly"),
        (0.25, 0.4, 4.7, 1.5, C["dev"], C["ink"], "2H'26\n메모리 원가↑ → Devices GM 압박"),
        (5.2, 0.4, 4.55, 1.5, C["navy"], "white", "FCF/주 · $1B FCF by'28\n· $400M 자사주"),
    ]
    for x, y, w, h, c, tc, t in items:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9, color=tc)
    ax.set_title("촉매·리스크 캘린더", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    rows = [
        (0.3, 2.6, 9.4, 1.0, C["navy"], "white",
         "포트 역할: 미보유 · Chase 상·08-06 · TA 대기+NO_ADD (코어 아님)"),
        (0.3, 1.4, 4.5, 0.95, C["teal"], "white", "사이즈\n1주~$143 ≈ 주식~20%"),
        (5.0, 1.4, 4.7, 0.95, C["gold"], C["ink"], "현금 우선순위\n바닥·MU·LASR ≫ ROKU"),
        (0.3, 0.25, 9.4, 0.95, C["sand"], C["ink"],
         "지금: 고점근접·실적 D-9 · 소액북 코어 부적합 · 08-06 추격 금지"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9, color=tc)
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
      @bottom-center {{ content:"ROKU 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0e7490; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0e7490; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#eef6f9 0%,#e8eef5 55%,#f5f3ff 100%);
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
<html lang="ko"><head><meta charset="utf-8"/><title>ROKU 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>ROKU 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Roku, Inc. · CTV OS · Advertising + Subscriptions + Devices</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1'26 실적(4/30) · 다음 실적 ~08-06 · 플랫폼 수익화</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~$143</div><div class="s">시총 ~$21.2B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~$158</div><div class="s">업사이드 ~+11%</div></span>
    <span class="kpi"><div class="l">Q1 매출</div><div class="v">$1.25B</div><div class="s">+22% YoY</div></span>
    <span class="kpi"><div class="l">플랫폼</div><div class="v">$1.13B</div><div class="s">+28% · GM 51.6%</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">Chase 상·08-06</span>
    <span class="tag warn">TA 대기 · NO_ADD</span>
    <span class="tag bad">고점근접 · 1주=코어급</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>하드웨어로 가구를 모으고, 광고·구독 플랫폼으로 버는 CTV OS 회사.</b>
Q1'26부터 Platform을 <b>Advertising / Subscriptions</b>로 분리 공시.
매출의 <b>~91%</b>가 플랫폼이고 Devices(~9%)는 의도적 적자(유입 엔진).
스토리는 <b>이중자릿수 플랫폼 성장 + 마진 + FCF/주</b>이며, 북극성은 <b>2028년 FCF $1B</b>.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 싸게(또는 적자로) 기기·OS를 깔아 시청자를 모은 뒤,
홈스크린·추천으로 <b>광고</b>와 <b>유료구독</b>을 판다. 이익은 거의 전부 플랫폼에서 난다.</div>
{gloss([
    ("CTV / OTT", "Connected TV / Over-The-Top — 인터넷으로 TV를 보는 방식."),
    ("Streaming Household", "최근 30일 내 플랫폼에서 스트리밍한 고유 계정 수."),
    ("Roku Experience (RX)", "홈스크린·디스커버리·AI 추천 등 플랫폼 UI 경험면."),
])}

<h2>1. 어디서 돈이 오나 — 3세그먼트</h2>
{fig_block(charts['02'], '매출 믹스·총이익률')}
{fig_block(charts['04'], '수익 스택')}
<table>
  <tr><th>세그먼트</th><th>Q1'26 매출</th><th>YoY</th><th>총이익률</th><th>역할</th></tr>
  <tr><td><b>Advertising</b></td><td>$613M (49%)</td><td>+27%</td><td><b>60.5%</b></td><td>고마진 엔진 · 비디오 임프레션 +59%</td></tr>
  <tr><td><b>Subscriptions</b></td><td>$519M (42%)</td><td>+30%</td><td>41.1%</td><td>프리미엄 가입·Frndly/Howdy · (Frndly 제외 +23%)</td></tr>
  <tr><td>Devices</td><td>$118M (9%)</td><td>−16%</td><td><b>−16.3%</b></td><td>플레이어·자사 TV · OEM TV 매출은 미포함</td></tr>
  <tr><td>합계</td><td>$1.25B</td><td>+22%</td><td>GP $565M (+27%)</td><td>순이익 $86M · Adj.EBITDA $148M</td></tr>
</table>
<p class="small">2026 Q1부터 보고 세그먼트를 Advertising / Subscriptions / Devices 3개로 변경
(이전: Platform+Devices).</p>
<div class="easy"><b>쉽게:</b> 광고 1달러는 마진이 두껍고, 기기는 일부러 싸게 판다.
기기 적자는 “고객 유치 비용”에 가깝다. OEM이 만든 Roku TV는 대량인데
그 TV 판매액은 Roku 매출에 <b>안</b> 잡힌다(OS·광고·구독으로 회수).</div>
{gloss([
    ("Programmatic / DSP", "자동 입찰 광고 구매. DV360·Amazon DSP·TTD 등과 연동."),
    ("OEM 라이선스", "삼성 등이 아닌 TV 제조사가 Roku OS를 탑재해 판매. 유닛 매출≠Roku Devices."),
    ("Premium Subscriptions", "Roku Channel 안에서 파트너 SVOD를 묶어 가입·결제."),
])}

{compete_html}

<h2>2. 성장 엔진 — 광고·구독·스케일</h2>
{fig_block(charts['03'], '플랫폼 추이·성장률')}
{fig_block(charts['05'], '총이익 브리지')}
<ul>
  <li><b>광고:</b> 미국 OTT·디지털 광고 시장 대비 아웃퍼폼 주장 · 3P 프로그램매틱 지출 +40%+ ·
      Ads Manager 광고주 수 YoY 2배+ · 비 M&amp;E 브랜드가 RX 광고의 ~30%</li>
  <li><b>구독:</b> Q1 프리미엄 가입 사상 최고 · Apple TV·Peacock Premium Sub 편입 · Howdy $3/월 확장</li>
  <li><b>스케일:</b> 스트리밍 시간 38.7B시간(+8%) · Roku TV OS 탑재 가구 <b>1억+</b>(4월)</li>
  <li><b>자본:</b> Q1 자사주 $100M · Q3 이후 누적 $250M / 한도 $400M · FCF TTM 사상 최고</li>
</ul>
<div class="box"><b>FY26 가이던스(상향):</b> Platform ~$5.0B(+~21%) · Devices ~$535M · Total ~$5.5B ·
Adj.EBITDA <b>$675M</b>(마진 +~330bps YoY) · Platform GM 51–52% 상단 ·
Devices GM 하이 −20%s(2H 메모리 원가↑).</div>
{gloss([
    ("Adj. EBITDA", "순이익에서 SBC·감가·구조조정 등 조정. 영업 현금창출력 근사."),
    ("FCF", "영업CF − CapEx. 회사 북극성 지표(FCF/주)."),
    ("bps", "basis points. 100bps = 1%p."),
])}

<h2>3. 전망 · 촉매 · 비용 압력</h2>
{fig_block(charts['06'], '가이던스·FCF')}
{fig_block(charts['08'], '촉매')}
<table>
  <tr><th>항목</th><th>수치·코멘트</th></tr>
  <tr><td>Q2'26 가이드</td><td>Platform +~20% · Devices 하이싱글↓ · Total ~$1.3B(+~17%) · GP $580M · Adj.EBITDA $170M</td></tr>
  <tr><td>다음 실적</td><td>~<b>2026-08-06</b> · 가이던스·광고 시즌·마진이 핵심</td></tr>
  <tr><td>Devices 리스크</td><td>메모리(DRAM/Flash) 원가↑ → 2H GM 압박 · 단 Roku OS는 경쟁 대비 메모리 요구↓ 주장</td></tr>
  <tr><td>장기</td><td><b>$1B FCF by 2028</b>(또는 그 전) · 이중자릿수 Platform 성장 지속</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 실적 때는 “플랫폼이 얼마나 빨리 크느냐”와 “기기 적자가 얼마나 커지느냐”를 본다.
메모리 가격이 뛰면 기기 쪽 숫자가 더러워져도, 플랫폼만 견고하면 스토리는 유지된다.</div>
{gloss([
    ("Loss leader", "손실을 감수하고 팔아 본업(플랫폼) 고객을 모으는 제품."),
    ("SBC", "주식보상비용. Adj.EBITDA에서 가산/제외되는 비현금 비용."),
])}

<h2>4. 민감도 · 시나리오</h2>
{fig_block(charts['07'], '주가 시나리오')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>160–205</td><td>광고·구독 지속 아웃퍼폼 · FY 가이던스 재상향 · FCF 경로 가속 · PT 상단</td></tr>
  <tr><td>Base</td><td>130–160</td><td>Platform ~20%대 · PT(~158) 수렴 · 기기 적자 관리</td></tr>
  <tr><td>Bear</td><td>95–120</td><td>광고 둔화·필레이트 악화 · 메모리로 Devices 적자 확대 · 멀티플 압축</td></tr>
</table>
<p><b>Breaker:</b> CTV 광고 침체 · 파트너 SVOD 이탈 · OEM 점유율 하락 ·
메모리/관세 쇼크 · 경쟁 OS(Google TV 등) 가격전쟁 · 08-06 가이던스 컷</p>
{gloss([
    ("고점근접", "현재가/52주최고. ~0.96이면 업사이드보다 되돌림 리스크가 큼."),
    ("NO_ADD", "포트 정책상 추가매수 차단 태그(워치·사이즈 부적합)."),
])}

<h2>5. 포트폴리오 위치</h2>
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>역할</td><td>미보유 <b>워치</b> · Chase는 상이나 <b>코어 후보 아님</b></td></tr>
  <tr><td>사이즈</td><td>1주 ~$143 ≈ 주식평가(~$709)의 <b>~20%</b> → 소액북에 단일주로 과대</td></tr>
  <tr><td>현금</td><td>바닥 $150 · MU $70 · LASR $70 예약 후 · ROKU는 <b>후순위</b></td></tr>
  <tr><td>타이밍</td><td><b>08-06 전후 추격 금지</b> · 실적·가이던스·눌림 후 재평가</td></tr>
  <tr><td>하지 말 것</td><td>NEO 현금으로 ROKU 1주 코어화 · 고점 추격 · Devices 적자=회사 붕괴로 오해</td></tr>
</table>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>고마진 광고+구독 플랫폼</u>이 본체, 기기는 유입 비용.
비즈니스 품질은 좋지만, <b>지금 계좌에는 비싸·크고·실적 임박</b>이라 현금 대기·LASR 우선이 맞다.</div>

<h2>부록 · 출처</h2>
<p class="small">
Roku Q1 2026 Shareholder Letter (2026-04-30) · SEC Exhibit 99.1 / 10-Q segment breakout ·
Pixalate CTV Device SOV (Q1'26 vs Q1'25) · 피어 매출믹스 근사(SPOT/NFLX/FUBO) ·
yfinance TTM 매출·가격·PT ({ASOF}).
시나리오는 예시 밴드(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 ROKU · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete</p>
</body></html>
"""


def _compete_section(charts: dict[str, Path], bundle) -> str:
    if bundle is None or "share" not in charts:
        return ""
    share_rows = "".join(
        f"<tr><td>{r.name}</td><td>{r.current:.0f}%</td><td>{r.prior:.0f}%</td>"
        f"<td>{r.delta_pp:+.0f}pp</td></tr>"
        for r in bundle.share_rows
    )
    mix_head = "".join(f"<th>{b}</th>" for b in bundle.mix_buckets)
    mix_body = []
    for r in bundle.mix_rows:
        cells = "".join(f"<td>{r['mix'].get(b, 0):.1f}%</td>" for b in bundle.mix_buckets)
        tag = " <b>(대상)</b>" if r.get("subject") else ""
        mix_body.append(f"<tr><td>{r['name']}{tag}</td>{cells}<td class='small'>{r.get('note','')}</td></tr>")
    ttm_fig = fig_block(charts["ttm"], "TTM 매출 규모") if "ttm" in charts else ""
    return f"""
<h2>1-B. 심층 섹터 경쟁 점유율 · 변화</h2>
<p><b>섹터</b> {bundle.sector_ko}</p>
<div class="easy"><b>쉽게:</b> CTV에서 <b>누가 OS·디바이스 레이어를 쥐고 광고 인벤토리를 먹나</b>를 본다.
ROKU는 콘텐츠 회사가 아니라 <b>플랫폼 레이어</b>라 Fire TV·삼성·애플·LG와 점유율을 겨룬다.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년동기</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>
{gloss([
    ("SOV (Share of Voice)", "프로그램매틱 CTV 거래에서 해당 디바이스·OS가 차지하는 비중."),
    ("pp", "percentage points. 36%→38%면 +2pp (상대 % 변화와 다름)."),
])}

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> 같은 ‘스트리밍’이라도 <b>광고 vs 구독 vs 기기</b> 비중이 다르다.
ROKU는 광고+구독 투트랙, NFLX/SPOT는 구독 편중, FUBO는 구독+광고 하이브리드에 가깝다.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
{gloss([
    ("정규화 버킷", "공시 세그먼트명이 달라도 Ad/Sub/Devices·Other로 맞춰 비교."),
    ("TTM", "Trailing Twelve Months — 최근 12개월 매출. 스케일 감각용."),
])}
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_platform_growth(),
        "04": chart_flywheel(),
        "05": chart_gp_bridge(),
        "06": chart_outlook(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("ROKU", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html = build_html(charts, compete_html=compete_html)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    doc = HTML(filename=str(OUT_HTML))
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        doc.write_pdf(str(p))
        print(f"PDF {p} {p.stat().st_size}")


if __name__ == "__main__":
    main()
