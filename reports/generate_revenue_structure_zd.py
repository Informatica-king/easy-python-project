#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(ZD) — Ziff Davis · 4세그먼트 + Connectivity 매각 · WeasyPrint PDF."""

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
PX = 53.50
PT = 58.60
H52 = 58.06
L52 = 22.45
UPSIDE = PT / PX - 1.0
NEAR_HI = PX / H52
MCAP_B = 1.83
EARN = "2026-11-05"
OUT_PDF = [
    Path("/opt/cursor/artifacts/ZD_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/ZD_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/ZD_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/ZD_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/zd")
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
    "blue": "#1d4ed8",
    "rose": "#be123c",
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
        (0.1, 0.7, 1.75, 1.6, "디지털 브랜드\n콘텐츠·툴", C["sand"]),
        (2.05, 0.7, 1.85, 1.6, "광고·커머스\n라이선스", C["blue"]),
        (4.1, 0.7, 1.85, 1.6, "Cyber/Martech\nSaaS", C["teal"]),
        (6.15, 0.7, 1.7, 1.6, "FCF\n+자사주", C["gold"]),
        (8.05, 0.7, 1.7, 1.6, "현금 $1.6B\nM&A 옵션", C["navy"]),
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
    ax.set_title("가치 사슬 — 버티컬 미디어/SaaS → FCF → 자사주·소형 M&A",
                 fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [94.7, 76.7, 68.7, 46.6]
    labs = [
        "Health &\nWellness\n$94.7M",
        "Tech &\nShopping\n$76.7M",
        "Cyber &\nMartech\n$68.7M",
        "Gaming &\nEnt.\n$46.6M",
    ]
    colors = [C["rose"], C["blue"], C["teal"], C["gold"]]
    ax.pie(
        sizes, labels=labs, colors=colors, startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=7),
    )
    ax.set_title("Q2'26 계속영업 매출 $286.7M", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["Health", "Tech&\nShop", "Cyber&\nMartech", "Gaming"]
    yoy = [-4.8, -5.0, 0.5, 0.9]
    colors = [C["green"] if v >= 0 else C["red"] for v in yoy]
    bars = ax.bar(cats, yoy, color=colors, width=0.55)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("세그먼트 성장 — 광고/헬스가 약, SaaS·게임 보합+",
                 fontproperties=PROP_B, fontsize=10.5)
    for b, v in zip(bars, yoy):
        ax.text(b.get_x() + b.get_width() / 2, v + (0.35 if v >= 0 else -0.9),
                f"{v:+.1f}%", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_connectivity_pivot() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.8)
    ax.axis("off")
    items = [
        (0.25, 0.5, 4.6, 2.9, C["sand"], C["ink"],
         "Before\nConnectivity 포함\n다각화(구독·연결)\n시총에 할인 반영"),
        (5.15, 0.5, 4.6, 2.9, C["navy"], "white",
         "After (Q2'26)\nAccenture 매각\n대금 ~$1.22B\n현금 ~$1.61B · 순현금"),
    ]
    for x, y, w, h, c, tc, t in items:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                           facecolor=c, edgecolor="white", lw=2)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=9.5, color=tc)
    ax.annotate("", xy=(5.0, 1.95), xytext=(5.0, 1.95),
                arrowprops=dict(arrowstyle="->", color=C["slate"], lw=2))
    ax.set_title("피벗 — Connectivity 매각으로 ‘미디어+SaaS+현금’ 구조",
                 fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "03_connectivity_pivot.png")


def chart_profitability() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    cats = ["매출", "Adj.\nEBITDA", "Adj.\nEPS"]
    # show YoY
    vals = [-2.7, -3.7, 13.2]
    colors = [C["red"], C["red"], C["green"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("Q2 성장 — EPS는 자사주로 방어", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (0.8 if v >= 0 else -1.8),
                f"{v:+.1f}%", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    cats = ["Adj.EBITDA\nmargin", "GAAP OP\nmargin"]
    vals = [26.8, -15.6]
    colors = [C["teal"], C["red"]]
    bars = ax.bar(cats, vals, color=colors, width=0.5)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_ylabel("%", fontproperties=PROP)
    ax.set_title("마진 — Adj 견조 · GAAP은 손상차손", fontproperties=PROP_B, fontsize=11)
    ax.text(0.5, -0.28, "Health & Wellness 영업권 손상 $54.8M → GAAP 영업손실",
            transform=ax.transAxes, fontproperties=PROP, fontsize=7, color=C["muted"], ha="center")
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "04_profitability.png")


def chart_cash_capital() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    cats = ["현금", "총부채", "순현금\n(개략)"]
    vals = [1606, 868, 738]
    colors = [C["teal"], C["gold"], C["navy"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("대차 (6/30'26) — 매각 후 순현금", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 30, f"{v:.0f}",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 1900)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    cats = ["Q2 FCF", "Q2\n자사주", "Q2\n인수"]
    vals = [54.0, 121.5, 9.2]
    colors = [C["teal"], C["blue"], C["sand"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("자본배분 — FCF + 매각대금 → 자사주", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 3, f"{v:.0f}",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 145)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "05_cash_capital.png")


def chart_revenue_stack() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")
    layers = [
        (0.3, 3.15, 9.4, 0.8, C["navy"], "white",
         "④ 자본수익 — 자사주·소형 M&A($5–50M EBITDA) · 추가 매각 옵션"),
        (0.3, 2.2, 9.4, 0.8, C["teal"], "white",
         "③ Cybersecurity & Martech — 클라우드 SaaS · 소폭 성장(+0.5%)"),
        (0.3, 1.25, 9.4, 0.8, C["gold"], C["ink"],
         "② Gaming & Entertainment — IGN 등 · +0.9% · 마진은 마케팅비 압력"),
        (0.3, 0.3, 9.4, 0.8, C["blue"], "white",
         "① Health + Tech&Shopping — 매출 비중 최대 · 광고/헬스케어 YoY 역풍"),
    ]
    for x, y, w, h, c, tc, t in layers:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=7.8, color=tc)
    ax.set_title("수익 스택 — 광고/콘텐츠가 본체, SaaS가 완충, 현금이 옵션",
                 fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "06_revenue_stack.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [28, 45, 65]
    highs = [42, 65, 85]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    ax.axvline(PX, color=C["gold"], ls="--", lw=1.5)
    ax.text(PX + 1, 2.35, f"현재 ~{PX:.0f}", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.axvline(PT, color="#2563eb", ls=":", lw=1.2)
    ax.text(PT + 1, -0.55, f"PT평균 ~{PT:.0f}", fontproperties=PROP, fontsize=7.5, color="#2563eb")
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        mid = (lo + hi) / 2
        ax.text(mid, i, f"{lo}–{hi}", ha="center", va="center", color="white",
                fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(20, 95)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear (12M · 광고·헬스·자사주·M&A)", fontproperties=PROP_B, fontsize=11)
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
        (0.2, 2.45, 3.1, 1.3, C["teal"], "white", "진행중\n자사주·소형\nM&A 배분"),
        (3.45, 2.45, 3.1, 1.3, C["navy"], "white", "2026-11-05\n다음 실적\n(계속영업 윤곽)"),
        (6.7, 2.45, 3.1, 1.3, C["gold"], C["ink"], "중기\n추가 매각/\n가치실현 옵션"),
        (0.2, 0.35, 4.7, 1.7, C["blue"], "white", "관전\n헬스 손상 후\n회복·광고 반등"),
        (5.15, 0.35, 4.65, 1.7, C["sand"], C["ink"], "옵션\nAI 라이선스\n소송·협상 진전"),
    ]
    for x, y, w, h, c, tc, t in items:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.8, color=tc)
    ax.set_title("촉매 — 자본배분 · 11/5 실적 · 광고/헬스 회복",
                 fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.1)
    ax.axis("off")
    rows = [
        (0.3, 2.7, 9.4, 1.05, C["navy"], "white",
         "포트 역할: 미보유 · 심층 A′ · Chase 중하(업사이드 +9.5% · 고점 92%)"),
        (0.3, 1.45, 4.5, 1.0, C["teal"], "white", "관심 금액\nC급 1주(~$54) 감각"),
        (5.0, 1.45, 4.7, 1.0, C["gold"], C["ink"], "타이밍\n눌림·고점 이탈 후"),
        (0.3, 0.25, 9.4, 1.0, C["sand"], C["ink"],
         "지금: SYRE/DNTH보다 수익구조 명확 · 단 추격 금지 · 보유 NO_ADD 우선"),
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
      @bottom-center {{ content:"ZD 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #1d4ed8; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#1d4ed8; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#dbeafe 0%,#e8eef5 55%,#f0fdfa 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#bfdbfe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.good {{ background:#bbf7d0; }}
    .tag.bad {{ background:#fecdd3; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#dbeafe; border-left:4px solid #1d4ed8; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#1d4ed8; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:100px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#1d4ed8; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>ZD 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>ZD 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Ziff Davis · 버티컬 디지털 미디어 + Cyber/Martech</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적(계속영업) · Connectivity 매각 완료 · 다음 실적 ~{EARN}</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.0f}</div><div class="s">시총 ~${MCAP_B:.2f}B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.0f}</div><div class="s">업사이드 {UPSIDE*100:+.0f}%</div></span>
    <span class="kpi"><div class="l">Q2 매출</div><div class="v">$287M</div><div class="s">YoY −2.7%</div></span>
    <span class="kpi"><div class="l">현금</div><div class="v">$1.61B</div><div class="s">순현금 개략</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">심층 A′ · 실매출·FCF</span>
    <span class="tag warn">Chase 중하 · 고점 {NEAR_HI*100:.0f}%</span>
    <span class="tag">Connectivity 매각 ~$1.22B</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>광고·콘텐츠 미디어 + 소규모 SaaS를 FCF·자사주로 운영하는 회사. Connectivity를 팔아 현금 요새가 됐다.</b>
Q2 계속영업 매출 <b>$286.7M (−2.7%)</b> · Adj.EBITDA <b>$76.8M (마진 26.8%)</b>.
GAAP는 Health 영업권 손상 <b>$54.8M</b>으로 손실이지만,
Adj EPS는 자사주로 <b>+13%</b>. 시총 ~$1.8B 대비 현금 ~$1.6B·순현금이라
‘브랜드 포트폴리오 할인 + 현금’ 구조다. 단 근기 유기성장은 약하다.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
{fig_block(charts['03'], 'Connectivity 피벗')}
<div class="easy"><b>쉽게:</b> CNET·PCMag·IGN·Everyday Health 같은 브랜드로 광고/커머스를 벌고,
보안·마케팅 SaaS도 판다. 연결(Connectivity) 사업은 Accenture에 팔아
통장에 현금이 크게 들어왔다. 성장 스토리보다 <b>현금·자사주·싸게 사기</b>가 본체에 가깝다.</div>
{gloss([
    ("계속영업 (continuing ops)", "Connectivity 매각 후 남는 4세그먼트 실적."),
    ("Connectivity", "연결/통신형 사업부 — Accenture에 ~$1.22B에 매각(Q2'26)."),
    ("Programmatic M&A", "소형($5–50M EBITDA) 브랜드·SaaS를 꾸준히 사는 DNA."),
])}

<h2>1. 세그먼트 — 어디서 돈이 오나</h2>
{fig_block(charts['02'], '세그먼트 믹스')}
{fig_block(charts['06'], '수익 스택')}
<table>
  <tr><th>세그먼트</th><th>Q2'26 매출</th><th>YoY</th><th>성격</th></tr>
  <tr><td><b>Health &amp; Wellness</b></td><td>$94.7M (33%)</td><td>−4.8%</td><td>최대 · 영업권 손상 $54.8M</td></tr>
  <tr><td><b>Technology &amp; Shopping</b></td><td>$76.7M (27%)</td><td>−5.0%</td><td>테크 미디어·쇼핑 광고/커머스</td></tr>
  <tr><td><b>Cybersecurity &amp; Martech</b></td><td>$68.7M (24%)</td><td>+0.5%</td><td>클라우드 SaaS · 완충축</td></tr>
  <tr><td><b>Gaming &amp; Entertainment</b></td><td>$46.6M (16%)</td><td>+0.9%</td><td>게임 콘텐츠 · 마진 압력</td></tr>
  <tr><td>합계(계속)</td><td><b>$286.7M</b></td><td>−2.7%</td><td>Adj.EBITDA $76.8M · 마진 26.8%</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 돈의 절반은 <b>헬스+테크쇼핑(광고)</b>에서 나온다.
지금 그 축이 역풍. SaaS·게임이 겨우 받쳐 주는 그림이다.</div>
{gloss([
    ("Digital media ads", "콘텐츠 트래픽 기반 광고·제휴 매출. 경기·트래픽에 민감."),
    ("Martech", "마케팅 기술 SaaS — 구독형으로 광고보다 반복성 높음."),
    ("Goodwill impairment", "과거 인수가가 현재가치보다 높다 판단해 장부가를 깎음(비현금)."),
])}

<h2>2. 수익성 · 현금 · 자본배분</h2>
{fig_block(charts['04'], '수익성')}
{fig_block(charts['05'], '현금·자본')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>Q2 Adj.EBITDA / 마진</td><td>$76.8M / <b>26.8%</b> (−3.7% YoY)</td></tr>
  <tr><td>Q2 Adj diluted EPS</td><td><b>$1.03</b> (+13.2%) — 주식수 감소 효과</td></tr>
  <tr><td>Q2 FCF (계열 합산)</td><td><b>$54.0M</b> (+100% YoY)</td></tr>
  <tr><td>Connectivity 매각</td><td>대금 ~<b>$1,216M</b> (현금 수취 ~$1,179M, 에스크로 $37M)</td></tr>
  <tr><td>현금 / 총부채 (6/30)</td><td><b>$1.61B</b> / ~$0.87B → <b>순현금</b></td></tr>
  <tr><td>Q2 자사주 / 인수</td><td>$121.5M / $9.2M</td></tr>
  <tr><td>다음 실적</td><td>~<b>{EARN}</b></td></tr>
</table>
<div class="box"><b>자본 스토리:</b> CEO — “매각·자사주·강한 FCF로 재무 위치 강화. 장기 주주수익 극대화에 자본 배분.”
DNA는 소형 브랜드 M&A. AI 라이선스는 소송·협상으로 <b>서두르지 않음</b>.</div>
{gloss([
    ("Free cash flow", "영업CF − CapEx. 자사주·인수의 연료."),
    ("Net cash", "현금 &gt; 부채 — 밸류에이션에 현금 할증이 중요."),
    ("Adj EPS vs GAAP", "손상·일회성 제외. GAAP는 Health 손상으로 크게 왜곡."),
])}

<h2>3. 시나리오</h2>
{fig_block(charts['07'], '주가 시나리오')}
{fig_block(charts['08'], '촉매')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>65–85</td><td>광고/헬스 반등 · 자사주 지속 · AI 라이선스 가시화 · 멀티플 재평가</td></tr>
  <tr><td>Base</td><td>45–65</td><td>유기성장 약보합 · FCF·바이백 · PT(~59) 수렴</td></tr>
  <tr><td>Bear</td><td>28–42</td><td>광고 침체 · 헬스 추가 압력 · M&amp;A 희석 · 현금 낭비 인식</td></tr>
</table>
<p><b>Breaker:</b> 광고 경기 악화 · Health 추가 손상 · 대형 M&A 실패 ·
AI 트래픽 침식 · 자사주 중단 · 추가 매각 실망</p>
<p class="small">현재가 ${PX:.2f} · 52주 고 ${H52:.2f} (근접 {NEAR_HI*100:.0f}%) · 저 ${L52:.2f} ·
업사이드 {UPSIDE*100:+.1f}% — <b>PT 여유가 얇아 추격 매력 낮음</b>.</p>

<h2>4. 포트폴리오 위치</h2>
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>역할</td><td>미보유 · 심층 <b>A′</b> 중 <b>수익구조가 가장 읽히는 후보</b> · Chase는 <b>중하</b></td></tr>
  <tr><td>금액</td><td>관심 시 <b>C급 1주(~$54)</b> — SYRE/DNTH 1주보다 계좌 부담 작음</td></tr>
  <tr><td>타이밍</td><td><b>고점권·업사이드 +9% → 추격 금지</b> · 눌림 후 · 보유 NO_ADD·구조 수리 우선</td></tr>
  <tr><td>하지 말 것</td><td>GAAP 손실만 보고 파산 착각 · 현금=$시총 착각(영업가치 별도) · 실적전 풀베팅</td></tr>
</table>
<div class="easy"><b>한줄 결론:</b> 수익구조의 실체는 <u>광고/콘텐츠 + SaaS FCF + Connectivity 매각 현금 → 자사주/M&A</u>.
A′ 3형제 중 <b>운영·밸류 가시성은 ZD가 우위</b>이나,
지금 가격은 고점·PT 근접이라 <b>워치·눌림 대기</b>가 맞고 추격은 아니다.</div>

<h2>부록 · 출처</h2>
<p class="small">
Ziff Davis Q2 2026 earnings release · earnings call 요약 · SEC 10-Q 세그먼트 ·
yfinance 분기 손익·BS·가격·PT ({ASOF}) · 심층분석 2026-08-12 (A′ / Chase 중하).
시나리오는 예시 밴드(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 ZD · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_connectivity_pivot(),
        "04": chart_profitability(),
        "05": chart_cash_capital(),
        "06": chart_revenue_stack(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    html = build_html(charts)
    html, _px = build_and_insert_price("ZD", CHART_DIR, html)
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
        tag="sepa-rev-zd",
        title="SEPA Revenue Structure — ZD",
        notes=(
            "## 수익구조분석(ZD) · Ziff Davis\n\n"
            f"Q2 계속영업 $286.7M (−2.7%) · Adj.EBITDA $76.8M (마진 26.8%)\n"
            f"Connectivity 매각 ~$1.22B · 현금 $1.61B · Q2 자사주 $122M · FCF $54M\n"
            f"px~${PX:.0f} · PT~${PT:.0f} · 업사이드 {UPSIDE*100:+.0f}%\n\n"
            f"- 심층 A′ · Chase 중하 (고점 {NEAR_HI*100:.0f}%)\n"
            "- 포트: 미보유 워치 · 추격 금지 · 눌림 후 C급 1주 후보\n"
        ),
    )
    print_release_result(rel, label="ZD 수익구조 PDF")
    print(f"ZD rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% near_hi={NEAR_HI*100:.0f}%")


if __name__ == "__main__":
    main()
