#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(APA) — APA Corporation 독립 E&P + 경쟁점유/믹스 + WeasyPrint PDF."""

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
from sepa.rev_price_chart import build_and_insert_price  # noqa: E402

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
ASOF = "2026-09-08"
PX = 42.77
PT = 44.46
H52 = 45.66
L52 = 21.57
UPSIDE = PT / PX - 1.0
EARN = "08-05"  # Q2'26 reported
OUT_PDF = [
    Path("/opt/cursor/artifacts/APA_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/APA_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/APA_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/APA_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/apa")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "teal": "#0f766e",
    "teal2": "#14b8a6",
    "navy": "#1e3a5f",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "gold": "#b8860b",
    "amber": "#d97706",
    "oil": "#b45309",
    "gas": "#2563eb",
    "ngl": "#ca8a04",
    "sand": "#e8dcc8",
    "egypt": "#0e7490",
    "ns": "#334155",
    "suriname": "#065f46",
}


def img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def save_fig(fig, name: str) -> Path:
    p = CHART_DIR / name
    fig.savefig(p, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def fig_block(path: Path, cap: str) -> str:
    return (
        f"<figure><img src='data:image/png;base64,{img_b64(path)}'/>"
        f"<figcaption>{cap}</figcaption></figure>"
    )


def gloss(items: list[tuple[str, str]]) -> str:
    lis = "".join(f"<li><span class='term'>{t}</span> — {d}</li>" for t, d in items)
    return f"<div class='gloss'><div class='gloss-title'>용어</div><ul>{lis}</ul></div>"


def chart_business_flow() -> Path:
    fig, ax = plt.subplots(figsize=(9.4, 3.5))
    ax.set_xlim(0, 10.2)
    ax.set_ylim(0, 3.4)
    ax.axis("off")
    boxes = [
        (0.1, 0.85, 1.55, 1.55, "에너지\n수요·유가", C["sand"]),
        (1.85, 0.85, 1.55, 1.55, "US Permian\n오일·NGL", C["oil"]),
        (3.55, 0.85, 1.45, 1.55, "Egypt\n오일·가스", C["egypt"]),
        (5.15, 0.85, 1.35, 1.55, "North Sea\n(UK)", C["ns"]),
        (6.65, 0.85, 1.55, 1.55, "생산\n410k BOE/d", C["navy"]),
        (8.35, 0.85, 1.65, 1.55, "현금·FCF\n·EBITDAX", C["teal"]),
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
            fontproperties=PROP_B, fontsize=8, color=tc,
        )
    # Suriname option strip
    ax.add_patch(
        FancyBboxPatch(
            (3.55, 0.15), 4.65, 0.55, boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=C["suriname"], edgecolor="white", lw=1.5,
        )
    )
    ax.text(
        5.875, 0.42, "Suriname GranMorgu (40% WI) · mid-2028 first oil 옵션",
        ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=8,
    )
    ax.set_title(
        "비즈니스 한눈에 — Permian / Egypt / North Sea → 생산 → 현금 (+ Suriname)",
        fontproperties=PROP_B, fontsize=11.5, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    # reported BOE mix US~64% / Egypt~30% / NS~5%
    sizes = [64.2, 30.4, 5.4]
    labels = ["US ~64%", "Egypt ~30%", "NS ~5%"]
    ax.pie(
        sizes, labels=labels,
        colors=[C["oil"], C["egypt"], C["ns"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.5),
    )
    ax.set_title("지역 BOE 믹스 (Q2'26 reported)", fontproperties=PROP_B, fontsize=10)

    ax = axes[1]
    labs = ["Oil", "NGL", "Gas"]
    vals = [1826, 170, 41]
    cols = [C["oil"], C["ngl"], C["gas"]]
    bars = ax.bar(labs, vals, color=cols, width=0.55)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("제품 매출 (Q2'26 hydrocarbon)", fontproperties=PROP_B, fontsize=10)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2, v + 25, f"{v:,.0f}",
            ha="center", fontsize=8, fontproperties=PROP,
        )
    ax.text(
        0.98, 0.02, "Oil ~90% of hydrocarbon rev",
        transform=ax.transAxes, ha="right", fontsize=7,
        color=C["muted"], fontproperties=PROP,
    )
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_growth_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    labels = [
        "Prod\n410k BOE/d",
        "Adj Prod\n347k",
        "Adj Earn\n$669M",
        "Adj EBITDAX\n$1.8B",
        "Q2 FCF\n$738M",
    ]
    # display-scale bars (relative visual weights)
    heights = [41.0, 34.7, 33.5, 45.0, 36.9]
    display = ["410k", "347k", "$669M", "$1.8B", "$738M"]
    colors = [C["navy"], C["egypt"], C["teal"], C["teal2"], C["green"]]
    bars = ax.bar(labels, heights, color=colors, width=0.55)
    ax.set_ylabel("표시용 스케일", fontproperties=PROP)
    ax.set_title(
        "성장 브리지 — 생산·조정이익·EBITDAX·FCF KPI",
        fontproperties=PROP_B, fontsize=11,
    )
    for b, d in zip(bars, display):
        ax.text(
            b.get_x() + b.get_width() / 2, b.get_height() + 0.8, d,
            ha="center", fontproperties=PROP, fontsize=8,
        )
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "03_growth_bridge.png")


def chart_pnl() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    labs = ["Oil\n$M", "Gas\n$M", "NGL\n$M", "Adj Earn\n$M", "FCF\n$M"]
    vals = [1826, 41, 170, 669, 738]
    cols = [C["oil"], C["gas"], C["ngl"], C["teal"], C["green"]]
    bars = ax.bar(labs, vals, color=cols, width=0.55)
    ax.set_title(
        "손익·현금 — Oil/Gas/NGL 매출 + Adj earnings / FCF (Q2'26)",
        fontproperties=PROP_B, fontsize=11,
    )
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2, v + 30, f"{v:,.0f}",
            ha="center", fontproperties=PROP, fontsize=8,
        )
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.text(
        0.02, 0.95, "Total rev $2,373M · NI $747M ($2.11) · Adj $1.89/sh",
        transform=ax.transAxes, va="top", fontsize=7.5,
        color=C["muted"], fontproperties=PROP,
    )
    fig.tight_layout()
    return save_fig(fig, "04_pnl.png")


def chart_backlog() -> Path:
    """Pipeline / options (E&P has no traditional backlog)."""
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    cards = [
        (0.2, 0.45, 2.25, 2.2, "Permian\n효율·US oil\n123.5 kb/d", C["oil"]),
        (2.65, 0.45, 2.25, 2.2, "Egypt 가스\n가격·Gross\n539 MMcf/d", C["egypt"]),
        (5.1, 0.45, 2.25, 2.2, "Suriname\nGranMorgu\nmid-2028", C["suriname"]),
        (7.55, 0.45, 2.2, 2.2, "Alaska /\nUruguay\n옵션성", C["navy"]),
    ]
    for x, y, w, h, t, c in cards:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        ax.text(
            x + w / 2, y + h / 2, t, ha="center", va="center",
            color="white", fontproperties=PROP_B, fontsize=9,
        )
    ax.set_title(
        "파이프라인·옵션 — Permian 효율 · Egypt 가스 · Suriname · 탐사 옵션",
        fontproperties=PROP_B, fontsize=11, pad=4,
    )
    return save_fig(fig, "05_backlog.png")


def chart_guide() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    metrics = [
        "FY26 US oil\nkb/d",
        "Upstream\ncapex $B",
        "LOE\n$B",
        "FCF outlook\n$B strip",
    ]
    vals = [123, 2.07, 1.50, 2.3]
    colors = [C["oil"], C["navy"], C["teal"], C["green"]]
    bars = ax.bar(metrics, vals, color=colors, width=0.5)
    ax.set_title(
        "가이던스 — FY26 US oil 123 · capex $2.07B · LOE $1.5B · FCF ~$2.3B",
        fontproperties=PROP_B, fontsize=10.5,
    )
    labels_txt = ["123", "2.07", "1.50", "~2.3"]
    for b, t in zip(bars, labels_txt):
        ax.text(
            b.get_x() + b.get_width() / 2, b.get_height() + 2.5, t,
            ha="center", fontproperties=PROP, fontsize=9,
        )
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.text(
        0.98, 0.02, "US oil 가이던스 상향 · LOE −$25M 하향 · Q2 capex/LOE 모두 가이던스↓",
        transform=ax.transAxes, ha="right", fontsize=7,
        color=C["muted"], fontproperties=PROP,
    )
    fig.tight_layout()
    return save_fig(fig, "06_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    bands = [("Bear", 28.0, 36.0), ("Base", 40.0, 48.0), ("Bull", 52.0, 62.0)]
    colors = [C["red"], C["amber"], C["green"]]
    for i, ((name, lo, hi), c) in enumerate(zip(bands, colors)):
        ax.barh(i, hi - lo, left=lo, height=0.45, color=c, alpha=0.85)
        ax.text(
            (lo + hi) / 2, i, f"{name} ${lo:.0f}–{hi:.0f}",
            ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=9,
        )
    ax.axvline(PX, color=C["navy"], ls="--", lw=1.4, label=f"현재 ${PX:.2f}")
    ax.axvline(PT, color=C["teal"], ls=":", lw=1.4, label=f"PT ${PT:.2f}")
    ax.set_yticks([])
    ax.set_xlabel("주가 $", fontproperties=PROP)
    ax.set_title("시나리오 밴드", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8, loc="lower right")
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.0)
    ax.axis("off")
    cards = [
        (0.2, 0.4, 2.2, 2.1, "유가·스트립\n·FCF 민감도", C["oil"]),
        (2.7, 0.4, 2.2, 2.1, "Permian\n효율·US oil\n가이던스", C["amber"]),
        (5.2, 0.4, 2.2, 2.1, "Egypt 가스\n가격·생산", C["egypt"]),
        (7.7, 0.4, 2.0, 2.1, "Suriname\n일정·FID\n진행", C["suriname"]),
    ]
    for x, y, w, h, t, c in cards:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        ax.text(
            x + w / 2, y + h / 2, t, ha="center", va="center",
            color="white", fontproperties=PROP_B, fontsize=9,
        )
    ax.set_title("촉매 카드", fontproperties=PROP_B, fontsize=11, pad=4)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.1))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.0)
    ax.axis("off")
    ax.add_patch(
        FancyBboxPatch(
            (0.25, 0.4), 9.5, 2.2, boxstyle="round,pad=0.05,rounding_size=0.12",
            facecolor="#ecfdf5", edgecolor=C["teal"], lw=2,
        )
    )
    ax.text(
        5.0, 2.05, "포폴 실행후보 (본선∩GO) · 심층 Chase 중상 · GO_A · 권고 극소/워치 · 미보유",
        ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=C["teal"],
    )
    ax.text(
        5.0, 1.15,
        f"현재 ${PX:.2f} · PT ${PT:.2f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}–${H52:.2f}\n"
        "추격 금지 · 소액·눌림만 · 유가·Permian 효율·Egypt 가스·Suriname 일정 게이트",
        ha="center", va="center", fontproperties=PROP, fontsize=8.5, color=C["ink"],
    )
    return save_fig(fig, "09_position.png")


def _compete_section(charts: dict[str, Path], bundle) -> str:
    if bundle is None:
        return ""
    share_rows = ""
    for r in bundle.share_rows:
        d = r.delta_pp
        share_rows += (
            f"<tr><td>{r.name}</td><td>{r.current:.1f}%</td>"
            f"<td>{r.prior:.1f}%</td><td>{d:+.1f}pp</td></tr>"
        )
    mix_head = "".join(f"<th>{b}</th>" for b in bundle.mix_buckets)
    mix_body = []
    for row in bundle.mix_rows:
        cells = "".join(
            f"<td>{row['mix'].get(b, 0):.0f}%</td>" for b in bundle.mix_buckets
        )
        bold = " style='font-weight:700;background:#ecfdf5'" if row.get("subject") else ""
        mix_body.append(
            f"<tr{bold}><td>{row['name']}</td>{cells}"
            f"<td class='small'>{row.get('note','')}</td></tr>"
        )
    ttm_fig = fig_block(charts["ttm"], "TTM 매출 규모") if "ttm" in charts else ""
    return f"""
<h2>1-B. 심층 섹터 경쟁 점유율 · 변화</h2>
<p><b>섹터</b> {bundle.sector_ko}</p>
<div class="easy"><b>쉽게:</b> APA는 상장 독립 E&P 피어셋에서 <b>중하위(~9.5%)</b> 스케일이다.
COP·EOG·OXY가 스케일을 주도. APA 점유 Δ는 <b>+0.5pp</b> 추정 — Egypt·Permian 기여로 상대 비중 소폭↑.
절대 시장점유가 아니라 피어 대비 상대 크기. 메이저(XOM/CVX)는 제외.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> APA는 <b>US ~64% / Egypt ~30% / North Sea ~5%</b>의 지역 분산 E&P.
피어(DVN·EOG)는 미국 셰일 집중, COP·OXY는 글로벌 분산. APA만 Egypt 비중이 독특하다.
제품으로는 Oil ~90%로 유가 민감도가 높다.</div>
{fig_block(charts['mix'], '지역 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
"""


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"APA 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0f766e; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #14b8a6; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#1e3a5f; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ecfdf5 0%,#ccfbf1 45%,#e0f2fe 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#ccfbf1; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecdd3; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#0f766e; color:#fff; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#ecfdf5; border-left:4px solid #0f766e; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#0f766e; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0f766e; }}
    .box {{ background:#fffbeb; border:1px solid #d97706; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #99f6e4; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#0f766e; }}
    .kpi .s {{ font-size:7.5pt; color:#0e7490; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>APA 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>APA 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">APA Corporation · 독립 E&P · Permian + Egypt + North Sea (+ Suriname)</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적({EARN} 발표) · ${PX:.2f}</p>
  <div style="margin-top:22px">
    <span class="tag good">Adj Earn $669M</span>
    <span class="tag good">Adj EBITDAX $1.8B</span>
    <span class="tag good">Q2 FCF $738M</span>
    <span class="tag">US oil 123 kb/d ↑</span>
    <span class="tag warn">Chase 중상 · GO_A</span>
  </div>
  <div style="margin-top:28px">
    <div class="kpi"><div class="l">Total rev</div><div class="v">$2.37B</div><div class="s">Q2'26</div></div>
    <div class="kpi"><div class="l">BOE/d</div><div class="v">410k</div><div class="s">adj 347k</div></div>
    <div class="kpi"><div class="l">Oil 비중</div><div class="v">~90%</div><div class="s">hydrocarbon</div></div>
    <div class="kpi"><div class="l">업사이드</div><div class="v">{UPSIDE*100:+.0f}%</div><div class="s">PT ${PT:.0f}</div></div>
  </div>
  <p class="small" style="margin-top:36px;max-width:560px;margin-left:auto;margin-right:auto">
    Oil-heavy 독립 E&P. US Permian이 생산·현금 본체, Egypt가 가스·국제 레그, North Sea는 소형.
    Suriname GranMorgu(40% WI)는 mid-2028 first oil 옵션.
    심층: Chase 중상 · GO_A · 포폴 실행후보(ROKU와 함께) · 권고 극소/워치 — 추격 금지 · 소액·눌림만.
  </p>
</section>

<h2>0. 한줄 결론</h2>
<div class="box">
<b>구조는 “Oil-heavy 독립 E&P: Permian 본체 + Egypt 국제 + Suriname 옵션” — 실적·현금은 강한데 업사이드는 얇고 추격 금지.</b>
Q2'26 NI $747M($2.11) · Adj $669M($1.89) · 생산 410k BOE/d(adj 347k) ·
Oil 매출 $1,826M(~90%) · Adj EBITDAX $1.8B · FCF $738M(1H $1.2B) ·
FY26 US oil 123 kb/d 상향 · capex $2.07B · LOE $1.5B · FCF outlook ~$2.3B strip.
포트: <b>미보유 · Chase 중상 · GO_A · 포폴 실행후보 · 권고 극소/워치 Σ2</b> ·
업사이드 {UPSIDE*100:+.0f}% — <b>추격 금지 · 소액·눌림만</b>.
</div>

<h2>1. 비즈니스 구조</h2>
<div class="easy"><b>쉽게:</b> APA는 원유·가스를 직접 뽑는 <b>독립 탐사·생산(E&P)</b> 회사다.
미국(Permian)에서 오일을 많이 뽑고, 이집트에서 오일·가스를, 북해(영국)에서 소량 생산한다.
수린남 GranMorgu는 아직 생산 전(2028년 중반 목표) 성장 옵션이다.</div>
{fig_block(charts['flow'], '수요 → Permian/Egypt/NS → 생산 → 현금·FCF (+ Suriname)')}
{gloss([
    ("BOE/d", "Barrels of Oil Equivalent per day — 오일·가스·NGL을 오일 환산 일산"),
    ("NCI / tax barrels", "비지배지분·세금 배럴 — 조정 생산에서 제외하는 Egypt 관련 항목"),
    ("Adj EBITDAX", "탐비·손상 등 제외 조정 EBITDA — E&P 현금창출력 지표"),
    ("GranMorgu", "수린남 해상 개발 프로젝트 · APA 40% WI · mid-2028 first oil 목표"),
    ("LOE", "Lease Operating Expense — 조업비(리프트 코스트)"),
])}

{compete_html}

<h2>2. 매출·손익 (Q2'26)</h2>
<div class="easy"><b>쉽게:</b> 돈의 거의 전부 <b>원유 매출</b>에서 나온다(오일 ~90%).
가스·NGL은 보조. 조정 이익·EBITDAX·FCF가 동시에 강하고, 설비투자·조업비는 가이던스보다 낮았다.</div>
{fig_block(charts['mix'], '지역 BOE · 제품 매출 믹스')}
{fig_block(charts['growth'], '생산·이익·FCF 브리지')}
{fig_block(charts['pnl'], '제품 매출 · Adj earnings · FCF')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>메모</th></tr>
  <tr><td>Total revenues</td><td>$2,373M</td><td>IR / SEC 99.1</td></tr>
  <tr><td>Oil production revenue</td><td>$1,826M</td><td>~90% of hydrocarbon</td></tr>
  <tr><td>Gas production revenue</td><td>$41M</td><td>~2%</td></tr>
  <tr><td>NGL production revenue</td><td>$170M</td><td>~8%</td></tr>
  <tr><td>Reported production</td><td>410k BOE/d</td><td>US~64% / Egypt~30% / NS~5%</td></tr>
  <tr><td>Adjusted production</td><td>347k BOE/d</td><td>ex Egypt NCI + tax barrels</td></tr>
  <tr><td>US oil</td><td>123.5 kb/d</td><td>+2.5k above guide</td></tr>
  <tr><td>Egypt adjusted</td><td>61k BOE/d</td><td>Gross Egypt gas 539 MMcf/d</td></tr>
  <tr><td>Net income / EPS</td><td>$747M / $2.11</td><td>reported</td></tr>
  <tr><td>Adjusted earnings / EPS</td><td>$669M / $1.89</td><td>핵심 이익</td></tr>
  <tr><td>Adj EBITDAX</td><td>$1.8B</td><td>분기 현금창출력</td></tr>
  <tr><td>Free cash flow</td><td>$738M</td><td>1H FCF $1.2B</td></tr>
  <tr><td>Upstream capex</td><td>$546M</td><td>below guide</td></tr>
  <tr><td>LOE</td><td>$353M</td><td>below guide</td></tr>
</table>
{gloss([
    ("Hydrocarbon revenue", "오일·가스·NGL 생산 매출 합 — 기타 매출 제외"),
    ("Adjusted production", "보고 생산에서 Egypt NCI·tax barrels 제외한 경제 지분 생산"),
    ("FCF", "Free Cash Flow — 영업현금 − 설비투자 등 후 잉여현금"),
])}

<h2>3. 파이프라인 · 가이던스</h2>
{fig_block(charts['backlog'], '파이프라인·옵션 카드')}
{fig_block(charts['guide'], 'FY26 가이던스')}
<div class="easy"><b>쉽게:</b> 올해 미국 오일 가이던스를 <b>123 kb/d</b>로 올렸고, 조업비 가이던스는
<b>$1.5B(−$25M)</b>로 깎았다. 설비투자 $2.07B. 스트립 기준 FCF는 약 <b>$2.3B</b> 전망.
Suriname는 2028년 중반 첫 오일 일정 유지.</div>
<table>
  <tr><th>지표</th><th>내용</th></tr>
  <tr><td>FY26 US oil guide</td><td>123 kb/d (상향)</td></tr>
  <tr><td>FY26 upstream capex</td><td>$2.07B</td></tr>
  <tr><td>FY26 LOE guide</td><td>$1.5B (−$25M vs prior)</td></tr>
  <tr><td>FY26 FCF outlook</td><td>~$2.3B (strip)</td></tr>
  <tr><td>Q2 US oil vs guide</td><td>123.5 kb/d · +2.5k above</td></tr>
  <tr><td>Q2 capex / LOE</td><td>$546M / $353M · both below guide</td></tr>
  <tr><td>Suriname GranMorgu</td><td>40% WI · mid-2028 first oil on track</td></tr>
  <tr><td>Optionality</td><td>Alaska / Uruguay exploration optionality</td></tr>
</table>

<h2>4. 시나리오 · 촉매</h2>
{fig_block(charts['scen'], '주가 시나리오 밴드')}
{fig_block(charts['cat'], '촉매 카드')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$28–36</td><td>유가 약세 · Egypt 가스가격↓ · Permian 효율 악화 · Suriname 지연</td></tr>
  <tr><td>Base</td><td>$40–48</td><td>스트립 유지 · FY26 가이던스 달성 · PT 수렴</td></tr>
  <tr><td>Bull</td><td>$52–62</td><td>유가↑ · FCF 초과 · Suriname 일정 가속 · 고점 돌파</td></tr>
</table>

<h2>5. 포트 실행</h2>
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (09-08 포폴)</b><br/>
미보유 · 심층 Chase <b>중상</b> · 타이밍 <b>GO_A</b> · 포폴 실행후보 <b>(ROKU와 함께)</b> · 권고 극소/워치 Σ2.<br/>
현재 ${PX:.2f} · PT ${PT:.2f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}–${H52:.2f}.<br/>
실행: <b>추격 금지</b> · <b>소액·눌림만</b>. 게이트: 유가 · Permian 효율 · Egypt 가스가격 · Suriname 일정.<br/>
품질 게이트: FY26 US oil 123 · capex/LOE 준수 · FCF strip ~$2.3B 경로 유지.
</div>

<p class="small">생성: 수익구조분석() · 티커 APA · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart<br/>
출처: APA IR / SEC exhibit 99.1 (2026-08-05) · yfinance · 피어 점유/믹스는 방향 비교용 추정</p>
</body></html>
"""


def main() -> int:
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "growth": chart_growth_bridge(),
        "pnl": chart_pnl(),
        "backlog": chart_backlog(),
        "guide": chart_guide(),
        "scen": chart_scenarios(),
        "cat": chart_catalysts(),
        "pos": chart_position(),
    }
    bundle, cpaths = build_compete_charts("APA", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("APA", CHART_DIR, html_doc)
    if _px.ok:
        print(f"price-charts {_px.candle_path} {_px.momentum_path}")
    else:
        print(f"price-charts SKIP {_px.error}")
    OUT_HTML.write_text(html_doc, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    pdf = HTML(filename=str(OUT_HTML)).write_pdf()
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf)
        print(f"PDF {p} {p.stat().st_size}")
    try:
        from sepa.artifacts import print_release_result, publish_github_release_asset

        tag = "sepa-rev-apa"
        notes = (
            f"## APA 수익구조분석 ({ASOF})\n\n"
            f"APA Corporation · 독립 E&P · Q2'26 · Oil-heavy Permian/Egypt/NS.\n\n"
            f"- Rev $2.37B · Adj Earn $669M · Adj EBITDAX $1.8B · FCF $738M\n"
            f"- Prod 410k BOE/d (adj 347k) · US oil 123.5 kb/d · FY26 FCF ~$2.3B strip\n"
            f"- Chase 중상 · GO_A · 포폴 실행후보 · 업사이드 {UPSIDE*100:+.1f}% "
            f"(PT ${PT:.0f} · px ${PX:.2f})\n"
            f"- 추격 금지 · 소액·눌림만 · 유가·Permian·Egypt·Suriname 게이트\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — APA",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
