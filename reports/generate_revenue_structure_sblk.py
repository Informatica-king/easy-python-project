#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(SBLK) — Star Bulk 건화물 TCE + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-07-30"
OUT_PDF = [
    Path("/opt/cursor/artifacts/SBLK_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/SBLK_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/SBLK_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/SBLK_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/sblk")
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
    "sblk": "#0c4a6e",
    "cape": "#0369a1",
    "pana": "#0f766e",
    "ultra": "#a16207",
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
        (0.1, 0.7, 1.7, 1.6, "화주·용선주\n철광·석탄·곡물", C["sand"]),
        (1.95, 0.7, 1.75, 1.6, "항차·기간용선\nVoyage / T/C", C["sblk"]),
        (3.9, 0.7, 1.75, 1.6, "TCE\n일일 순운임", C["teal"]),
        (5.85, 0.7, 1.75, 1.6, "OPEX+G&A\n~$6.4k/d", C["gold"]),
        (7.8, 0.7, 1.9, 1.6, "배당·부채\n축소", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = "white" if c in (C["sblk"], C["teal"], C["navy"], C["gold"]) else C["ink"]
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.5, color=tc)
    for x in (1.85, 3.75, 5.7, 7.65):
        ax.annotate(
            "", xy=(x + 0.08, 1.5), xytext=(x - 0.08, 1.5),
            arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6),
        )
    ax.set_title(
        "SBLK 가치사슬 — 화물 수요 → 항차/용선 → TCE → 현금·배당",
        fontproperties=PROP_B, fontsize=11, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_revenue_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9))
    ax = axes[0]
    labels = ["Cape/\nNewcastlemax", "Panamax/\nKamsarmax", "Ultramax/\nSupramax"]
    vals = [33.0, 29.0, 38.0]
    colors = [C["cape"], C["pana"], C["ultra"]]
    ax.pie(
        vals, labels=labels, colors=colors,
        autopct=lambda p: f"{p:.0f}%",
        textprops={"fontproperties": PROP, "fontsize": 8.5},
        startangle=90, wedgeprops=dict(width=0.45, edgecolor="white"),
    )
    ax.set_title("Q1'26 선급별 매출 기여", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    segs = [
        ("Cape/Newc TCE", 26627),
        ("Panamax/Kam TCE", 15849),
        ("Ultra/Supra TCE", 16050),
        ("Fleet TCE", 18493),
    ]
    names = [s[0] for s in segs]
    fvals = [s[1] for s in segs]
    colors_b = [C["cape"], C["pana"], C["ultra"], C["sblk"]]
    bars = ax.barh(names[::-1], fvals[::-1], color=colors_b[::-1], height=0.55)
    ax.set_xlabel("$/day", fontproperties=PROP)
    ax.set_title("Q1'26 선급별 TCE ($/일)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, fvals[::-1]):
        ax.text(v + 200, b.get_y() + b.get_height() / 2, f"${v:,.0f}",
                va="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_mix.png")


def chart_tce_trend() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    qs = ["Q1'25", "Q1'26"]
    tce = [12439, 18493]
    ax.bar(qs, tce, color=[C["sand"], C["sblk"]], width=0.5)
    ax.set_ylabel("$/day", fontproperties=PROP)
    ax.set_title("Fleet TCE YoY", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(tce):
        ax.text(i, v + 350, f"${v:,.0f}", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    metrics = ["Voyage Rev", "TCE Rev", "Adj EBITDA", "Net Income"]
    vals = [281.2, 214.1, 114.3, 58.5]
    colors = [C["cape"], C["sblk"], C["teal"], C["green"]]
    bars = ax.bar(metrics, vals, color=colors, width=0.55)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("Q1'26 손익 요약 ($M)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 3, f"{v:.1f}",
                ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "03_tce_pnl.png")


def chart_fleet() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    cats = ["척수", "DWT(M)"]
    vals_n = [141, 14.0]
    # dual-ish display via twin values as labeled bars
    ax.bar(["Fully-delivered\n척수"], [141], color=C["sblk"], width=0.45)
    ax.set_ylabel("척", fontproperties=PROP)
    ax.set_title("선대 규모", fontproperties=PROP_B, fontsize=11)
    ax.text(0, 145, "141척", ha="center", fontproperties=PROP_B, fontsize=11, color=C["sblk"])
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    ax.bar(["DWT"], [14.0], color=C["teal"], width=0.45)
    ax.set_ylabel("백만 dwt", fontproperties=PROP)
    ax.set_title("적재중량 ~14.0M dwt", fontproperties=PROP_B, fontsize=11)
    ax.text(0, 14.3, "14.0M dwt", ha="center", fontproperties=PROP_B, fontsize=11, color=C["teal"])
    ax.set_ylim(0, 18)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.suptitle("상장 건화물 피어셋 내 최대급 스케일", fontproperties=PROP_B, fontsize=11, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "04_fleet.png")


def chart_coverage_cost() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    ax.bar(["Q2'26 커버"], [82], color=C["sblk"], width=0.45)
    ax.set_ylim(0, 100)
    ax.set_ylabel("%", fontproperties=PROP)
    ax.set_title("Q2 운임 커버리지 82%", fontproperties=PROP_B, fontsize=11)
    ax.text(0, 86, "82% @ $22,166/d", ha="center", fontproperties=PROP_B, fontsize=10, color=C["sblk"])
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    items = ["OPEX/d", "G&A/d", "합계~"]
    vals = [5.0, 1.4, 6.4]
    colors = [C["gold"], C["sand"], C["navy"]]
    bars = ax.bar(items, vals, color=colors, width=0.5)
    ax.set_ylabel("$k / day", fontproperties=PROP)
    ax.set_title("일일 현금비용 (근사)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15, f"${v:.1f}k",
                ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "05_coverage_cost.png")


def chart_outlook() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    ax.axis("off")
    items = [
        (0.04, "운임", "BDI·케이프\n사이클 민감", C["cape"]),
        (0.28, "커버", "Q2 82%\n@$22.2k/d", C["sblk"]),
        (0.52, "배당", "Q1 $0.50\n연환산 ~3.8%", C["gold"]),
        (0.76, "실적", "08-05\nQ2 어닝", C["teal"]),
    ]
    for x, title, body, c in items:
        ax.add_patch(
            FancyBboxPatch(
                (x, 0.28), 0.2, 0.5, boxstyle="round,pad=0.02,rounding_size=0.04",
                facecolor=c, edgecolor="white", lw=1.5, transform=ax.transAxes,
            )
        )
        ax.text(x + 0.1, 0.62, title, ha="center", transform=ax.transAxes,
                fontproperties=PROP_B, fontsize=11, color="white")
        ax.text(x + 0.1, 0.42, body, ha="center", transform=ax.transAxes,
                fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title("전망 포인트 — 운임 레버리지 · 커버 · 배당 · 어닝", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "06_outlook.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    px = 27.92
    scenarios = [
        ("Bear", 18, 23, C["red"]),
        ("Base", 26, 32, C["teal"]),
        ("Bull", 33, 38, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}–{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(px, color=C["navy"], lw=1.5, ls="--")
    ax.text(px, 2.55, f"현재 ${px:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(31.98, color=C["gold"], lw=1.2, ls=":")
    ax.text(31.98, -0.7, "PT평균~$32", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 밴드 (예시 · 투자권유 아님) · 배당~3.8%", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(15, 42)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, "08-05", "실적", "Q2 TCE·커버\n배당 가이던스", C["teal"]),
        (0.28, "BDI", "운임", "케이프 강세\n→ TCE 레버리지", C["cape"]),
        (0.52, "배당", "현금", "변동배당\n운임 연동", C["gold"]),
        (0.76, "공급", "선대", "신조 공급\n중장기 리스크", C["navy"]),
    ]
    for x, tag, title, body, c in items:
        ax.add_patch(
            FancyBboxPatch(
                (x, 0.25), 0.2, 0.55, boxstyle="round,pad=0.02,rounding_size=0.04",
                facecolor=c, edgecolor="white", lw=1.5, transform=ax.transAxes,
            )
        )
        ax.text(x + 0.1, 0.68, tag, ha="center", transform=ax.transAxes,
                fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + 0.1, 0.55, title, ha="center", transform=ax.transAxes,
                fontproperties=PROP_B, fontsize=10, color="white")
        ax.text(x + 0.1, 0.38, body, ha="center", transform=ax.transAxes,
                fontproperties=PROP, fontsize=7.5, color="white")
    ax.set_title("촉매 — 08-05 실적 · 운임 · 배당 · 공급", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "매수워치 Tier2\n위성 후보", C["sblk"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "≤~$65\n코어 아님", C["teal"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", "고점 근접\n눌림·실적 후", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "52주 고점권 · 운임 사이클 · 이벤트 추격 비추", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "스케일·TCE 개선 · Q2 커버 82% · 배당~3.8%", C["navy"]),
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
    return save_fig(fig, "09_position.png")


def gloss(items: list[tuple[str, str]]) -> str:
    lis = "".join(f"<li><span class='term'>{a}</span> — {b}</li>" for a, b in items)
    return f"<div class='gloss'><div class='gloss-title'>이 블록 용어 주석</div><ul>{lis}</ul></div>"


def fig_block(path: Path, caption: str) -> str:
    return (
        f"<figure><img src='data:image/png;base64,{img_b64(path)}'/>"
        f"<figcaption>{caption}</figcaption></figure>"
    )


def _compete_section(charts: dict[str, Path], bundle) -> str:
    if bundle is None or "share" not in charts:
        return ""
    share_rows = "".join(
        f"<tr><td>{r.name}</td><td>{r.current:.1f}%</td><td>{r.prior:.1f}%</td>"
        f"<td>{r.delta_pp:+.1f}pp</td></tr>"
        for r in bundle.share_rows
    )
    mix_head = "".join(f"<th>{b}</th>" for b in bundle.mix_buckets)
    mix_body = []
    for r in bundle.mix_rows:
        cells = "".join(f"<td>{r['mix'].get(b, 0):.1f}%</td>" for b in bundle.mix_buckets)
        tag = " <b>(대상)</b>" if r.get("subject") else ""
        mix_body.append(
            f"<tr><td>{r['name']}{tag}</td>{cells}<td class='small'>{r.get('note', '')}</td></tr>"
        )
    ttm_fig = fig_block(charts["ttm"], "TTM 매출 규모") if "ttm" in charts else ""
    return f"""
<h2>1-B. 심층 섹터 경쟁 점유율 · 변화</h2>
<p><b>섹터</b> {bundle.sector_ko}</p>
<div class="easy"><b>쉽게:</b> SBLK는 상장 건화물 피어 중 <b>선대·DWT 최대급</b>.
글로벌 해운 점유가 아니라, GNK·SB·DSX 같은 <b>상장 피어셋 스케일</b> 비교다.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>
{gloss([
    ("DWT", "Deadweight tonnage — 선박이 실을 수 있는 화물·연료 등 총중량."),
    ("pp", "percentage points."),
])}

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> 건화물은 <b>어느 선급으로 버느냐</b>가 핵심.
SBLK는 Cape(~33%) + Ultra(~38%)로 대형·중형 균형. 피어는 Panamax 편중이 더 많은 편.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
{gloss([
    ("Cape/Newcastlemax", "대형 건화물선 — 철광·석탄 장거리. TCE 변동폭 큼."),
    ("Panamax/Kamsarmax", "파나마 운하급 — 곡물·석탄 등 중형."),
    ("Ultramax/Supramax", "Handy 상위 — 다목적·짧은 항차."),
])}
"""


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"SBLK 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0c4a6e; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0369a1; padding-bottom:3px; color:#0c4a6e; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0f766e; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#e0f2fe 0%,#e8eef5 55%,#ecfdf5 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#e0f2fe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.good {{ background:#bbf7d0; }}
    .tag.bad {{ background:#fecdd3; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#eff6ff; border-left:4px solid #0369a1; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#0c4a6e; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0369a1; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#0c4a6e; }}
    .kpi .s {{ font-size:7.5pt; color:#0369a1; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>SBLK 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>SBLK 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Star Bulk Carriers · 건화물(Dry Bulk) · Voyage/TCE · 배당~3.8%</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1'26 실적 · 다음 실적 08-05 · 선대 ~141척 / 14.0M dwt</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~$27.92</div><div class="s">시총 ~$3.1B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~$31.98</div><div class="s">업사이드 ~+15%</div></span>
    <span class="kpi"><div class="l">Q1 Fleet TCE</div><div class="v">$18,493</div><div class="s">YoY +49%</div></span>
    <span class="kpi"><div class="l">Q1 NI</div><div class="v">$58.5M</div><div class="s">Adj EBITDA $114M</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag">Chase 중상</span>
    <span class="tag warn">52주 고점권</span>
    <span class="tag good">스케일·커버·배당</span>
    <span class="tag">위성 워치 Tier2</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>철광·석탄·곡물을 실어 나르는 대형 건화물 선사. 돈은 항차·용선 운임(TCE)에서 나온다.</b>
Q1'26: Voyage $281M · TCE 매출 $214M · Fleet TCE $18,493/d(전년 $12,439) · NI $58.5M · 배당 $0.50.
Fully delivered ~141척·14.0M dwt로 상장 피어 대비 스케일 우위. Q2 커버리지 82% @ $22,166/d.
수익은 <b>운임 사이클 레버리지</b> — 좋으면 배당·현금이 커지고, 식으면 빠르게 꺾인다.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 배를 많이 가진 해운사다. 화주에게 배를 빌려주거나 항차로 화물을 나르고,
일당(TCE)을 받는다. 운임이 오르면 이익이 급증하고, 내리면 그만큼 줄어든다.
지금은 운임이 작년보다 훨씬 좋아서 실적·배당이 살아난 구간.</div>
{gloss([
    ("TCE", "Time Charter Equivalent — 항차비용 차감 후 일일 순운임."),
    ("Voyage revenue", "항차 운임 총액(연료·항비 등 포함 전)."),
    ("Dry bulk", "컨테이너가 아닌 벌크 화물(철광·석탄·곡물 등)."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '선급별 매출 기여 · TCE')}
{fig_block(charts['03'], 'TCE YoY · Q1 손익')}
<table>
  <tr><th>항목</th><th>Q1'26</th><th>YoY / 메모</th><th>의미</th></tr>
  <tr><td><b>Voyage revenue</b></td><td>$281.2M</td><td>운임↑</td><td>총 항차 매출</td></tr>
  <tr><td>TCE revenue</td><td>$214.1M</td><td>순운임 본체</td><td>비용 차감 후</td></tr>
  <tr><td>Fleet TCE</td><td>$18,493/d</td><td>vs $12,439 (+49%)</td><td>전 선대 일당</td></tr>
  <tr><td>Cape/Newc TCE</td><td>$26,627/d</td><td>대형선 강세</td><td>매출 기여 ~33%</td></tr>
  <tr><td>Panamax/Kam TCE</td><td>$15,849/d</td><td>중형</td><td>~29%</td></tr>
  <tr><td>Ultra/Supra TCE</td><td>$16,050/d</td><td>Handy 상위</td><td>~38%</td></tr>
  <tr><td>Adj. EBITDA</td><td>$114.3M</td><td>마진 확대</td><td>현금창출력</td></tr>
  <tr><td>Net Income</td><td>$58.5M</td><td>배당 $0.50</td><td>변동배당 여력</td></tr>
</table>
<p class="small">매출 믹스 33/29/38(Cape/Panamax/Ultra)은 Q1'26 공시 기반 근사. OPEX ~$5k/d + G&amp;A ~$1.4k/d ≈ 현금비용 ~$6.4k/d.</p>
<div class="easy"><b>쉽게:</b> 돈의 거의 전부 <b>운임(TCE)</b>다.
큰 배(Cape)가 일당이 제일 높고, 중·소형도 작년보다 많이 올랐다.
비용은 하루에 약 $6천 수준이라, TCE가 $18k면 여유(스프레드)가 큰 편이다.</div>
{gloss([
    ("OPEX", "선박 운항비(선원·정비·보험 등) — 연료는 항차 구조에 따라 별도."),
    ("G&A", "본사 관리비의 일환산."),
    ("Adj. EBITDA", "일회성 조정 후 영업현금 대용 지표."),
])}

{compete_html}

<h2>2. 선대 · 커버 · 비용</h2>
{fig_block(charts['04'], '선대 스케일')}
{fig_block(charts['05'], 'Q2 커버 · 일일 비용')}
<ul>
  <li>Fully delivered <b>~141척 · 14.0M dwt</b> — 상장 건화물 피어셋 내 최대급</li>
  <li>Q2'26 커버리지 <b>82% @ $22,166/d</b> — 단기 실적 가시성 확보</li>
  <li>현금비용 근사: OPEX ~$5.0k/d + G&amp;A ~$1.4k/d</li>
  <li>TTM 매출 ~$1.09B · 시총 ~$3.1B · EV/Sales ~3.4x (운임 민감)</li>
</ul>
<div class="easy"><b>쉽게:</b> 배가 많고, 다음 분기 운임의 상당 부분을 이미 고정해 두었다.
그래서 Q2는 “완전 깜깜이”가 아니다. 다만 고정 안 된 나머지·다음 분기는 여전히 시황에 흔들린다.</div>

<h2>3. 전망 · 시나리오</h2>
{fig_block(charts['06'], '전망 포인트')}
{fig_block(charts['07'], '주가 시나리오')}
<table>
  <tr><th>드라이버</th><th>내용</th></tr>
  <tr><td>운임(BDI·케이프)</td><td>실적·배당의 1차 변수. 사이클 업사이드/다운사이드 큼</td></tr>
  <tr><td>Q2 커버</td><td>82% @$22.2k → 단기 바닥 가시성</td></tr>
  <tr><td>배당</td><td>변동배당 · Q1 $0.50 · 연환산 수익률 ~3.8%</td></tr>
  <tr><td>공급</td><td>신조 인도·해체 속도가 중장기 운임 상한</td></tr>
  <tr><td>밸류</td><td>~$27.9 · PT~$32(~+15%) · 52주 고점 $28.5 근접</td></tr>
</table>

<h2>4. 촉매 · 포트 실행</h2>
{fig_block(charts['08'], '촉매')}
{fig_block(charts['09'], '포지션 맵')}
<div class="box">
<b>계좌 기준 실행</b><br/>
· 역할: 매수워치 <b>Tier2</b> · 위성 후보 (코어 아님)<br/>
· 가격: ~$27.9 · PT~$32 · <b>52주 고점권</b> → 추격 비추<br/>
· 트리거: <b>08-05</b> Q2 실적·배당 확인 후 눌림 · 사이즈 ≤~$65<br/>
· 우선순위: 현금 높은 국면에서 RELY/APA 아래 · 기존 보유 정리(LASR 등) 우선
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>운임(TCE) 레버리지 + 스케일</u>.
품질(커버·배당)은 괜찮으나 <b>지금 가격은 이미 운임 개선을 상당 부분 반영</b>.
매수보다 08-05 소화·눌림 대기.</div>

<h2>부록 · 출처</h2>
<p class="small">
Star Bulk Q1 2026 earnings release / fleet · fleet &amp; coverage disclosures ·
yfinance 가격·PT·캘린더 ({ASOF}). 점유율·피어 믹스는 상장 피어셋 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 SBLK · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_revenue_mix(),
        "03": chart_tce_trend(),
        "04": chart_fleet(),
        "05": chart_coverage_cost(),
        "06": chart_outlook(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("SBLK", CHART_DIR)
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
