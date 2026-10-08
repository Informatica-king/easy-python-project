#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(ENTG) — Entegris 반도체 소재·순도솔루션 + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-10-08"
PX = 164.58
PT = 175.58
H52 = 186.94
L52 = 67.97
UPSIDE = PT / PX - 1.0
EARN = "10-29"
OUT_PDF = [
    Path("/opt/cursor/artifacts/ENTG_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/ENTG_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/ENTG_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/ENTG_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/entg")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "navy": "#1e3a5f",
    "navy2": "#1d4ed8",
    "teal": "#0f766e",
    "teal2": "#14b8a6",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "ms": "#c2410c",
    "aps": "#0e7490",
    "logic": "#1d4ed8",
    "mem": "#7c3aed",
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
        (0.1, 0.7, 1.75, 1.6, "웨이퍼 스타트\n+ 팹 캡ex", C["sand"]),
        (2.0, 0.7, 1.8, 1.6, "소재·순도\n플랫폼", C["navy"]),
        (3.95, 0.7, 1.8, 1.6, "MS 42%\n증착·CMP·식각", C["ms"]),
        (5.9, 0.7, 1.8, 1.6, "APS 58%\n필터·FOUP", C["aps"]),
        (7.85, 0.7, 1.9, 1.6, "수율·순도\nAdj.EBITDA", C["teal"]),
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
                fontproperties=PROP_B, fontsize=8.2, color=tc)
    ax.set_title(
        "ENTG 가치사슬 — 첨단 노드일수록 소재·필터 콘텐츠가 늘어난다",
        fontproperties=PROP_B, fontsize=11, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [371.3, 514.6]
    labels = ["Materials\nSolutions\n$371M (42%)", "Advanced Purity\nSolutions\n$515M (58%)"]
    ax.pie(
        sizes, labels=labels, colors=[C["ms"], C["aps"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.2),
    )
    ax.set_title("보고 세그먼트 (Q2'26, 총 $883M)", fontproperties=PROP_B, fontsize=10.5)

    ax = axes[1]
    cats = ["첨단 로직", "메모리", "메인스트림\n로직"]
    vals = [40, 30, 30]
    colors = [C["logic"], C["mem"], C["muted"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.0f}%",
                ha="center", fontproperties=PROP_B, fontsize=9)
    ax.set_ylim(0, 50)
    ax.set_ylabel("% of sales", fontproperties=PROP)
    ax.set_title("엔드마켓 (콜 근사)", fontproperties=PROP_B, fontsize=10.5)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_mix.png")


def chart_growth_bridge() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    cats = ["MS", "APS", "연결"]
    yoy = [4.6, 17.0, 11.5]
    colors = [C["ms"], C["aps"], C["navy"]]
    for i, (v, c) in enumerate(zip(yoy, colors)):
        ax.bar(i, v, color=c, width=0.55)
        ax.text(i, v + 0.4, f"+{v:.1f}%", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(cats, fontproperties=PROP)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("세그먼트 성장 (Q2'26)", fontproperties=PROP_B, fontsize=10.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    labs = ["유닛\n(웨이퍼)", "캡ex\n전체", "  WFE", "  팹건설"]
    share = [75, 25, 10, 15]
    yoy2 = [10, 15, None, None]
    cols = [C["teal"], C["gold"], C["navy2"], C["muted"]]
    for i, (s, c) in enumerate(zip(share, cols)):
        ax.bar(i, s, color=c, width=0.55)
        extra = f"\n+{yoy2[i]:.0f}%" if yoy2[i] is not None else ""
        ax.text(i, s + 1.5, f"{s:.0f}%{extra}", ha="center", fontproperties=PROP, fontsize=7.5)
    ax.set_xticks(list(range(4)))
    ax.set_xticklabels(labs, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("% of sales", fontproperties=PROP)
    ax.set_title("엔진 — 유닛 75% / 캡ex 25%", fontproperties=PROP_B, fontsize=10.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "03_growth_bridge.png")


def chart_pnl() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    x = [0, 1, 2]
    gm = [44.4, 46.9, 47.6]
    ebitda = [27.3, 27.8, 28.4]
    ax.plot(x, gm, marker="o", color=C["teal"], lw=2.2, label="GP%")
    ax.plot(x, ebitda, marker="o", color=C["navy"], lw=2.2, label="Adj EBITDA%")
    ax.set_xticks(x)
    ax.set_xticklabels(["Q2'25", "Q1'26", "Q2'26"], fontproperties=PROP)
    ax.set_ylabel("% of sales", fontproperties=PROP)
    ax.set_title("마진 확장 — GP 47.6% · EBITDA 28.4%", fontproperties=PROP_B, fontsize=10)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    names = ["MS adj OM", "APS adj OM"]
    vals = [20.9, 30.3]
    bars = ax.bar(names, vals, color=[C["ms"], C["aps"]], width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.5, f"{v:.1f}%",
                ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 38)
    ax.set_title("세그먼트 조정영업이익률", fontproperties=PROP_B, fontsize=10.5)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "04_pnl.png")


def chart_leverage() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
    ax = axes[0]
    w = 0.35
    ax.bar([i - w / 2 for i in range(3)], [792, 217, 0], w, color=C["sand"], label="Q2'25")
    ax.bar([i + w / 2 for i in range(3)], [883, 251, 120], w, color=C["navy"], label="Q2'26")
    ax.text(0 + w / 2, 900, "+11%", ha="center", fontproperties=PROP, fontsize=8, color=C["teal"])
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["매출 $M", "Adj EBITDA $M", "FCF $M"], fontproperties=PROP, fontsize=8)
    ax.set_title("달러 실적 · FCF $120M (매출 14%)", fontproperties=PROP_B, fontsize=10.5)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    ax.bar(["Q2'26", "FY26 가이던스"], [3.4, 2.7], color=[C["gold"], C["teal"]], width=0.5)
    ax.text(0, 3.55, "3.4x", ha="center", fontproperties=PROP, fontsize=9)
    ax.text(1, 2.85, "high-2x", ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylabel("순레버리지 (x)", fontproperties=PROP)
    ax.set_title("부채 — Q2 $200M 상환 · 연말 <3x", fontproperties=PROP_B, fontsize=10.5)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "05_leverage.png")


def chart_guide() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.axis("off")
    items = [
        (0.04, "Q3 매출", "$905-935M\n중간 +14% YoY", C["navy"]),
        (0.28, "Q3 GP", "47.5-48.5%\n+400bp YoY", C["teal"]),
        (0.52, "Q3 Adj EPS", "$0.96-1.04\nEBITDA 28.5%", C["aps"]),
        (0.76, "Q4 방향", "Q3 중간 대비\n+4% seq", C["gold"]),
    ]
    for x, title, body, c in items:
        ax.add_patch(
            FancyBboxPatch(
                (x, 0.28), 0.2, 0.5, boxstyle="round,pad=0.02,rounding_size=0.04",
                facecolor=c, edgecolor="white", lw=1.5, transform=ax.transAxes,
            )
        )
        ax.text(x + 0.1, 0.62, title, ha="center", transform=ax.transAxes,
                fontproperties=PROP_B, fontsize=10, color="white")
        ax.text(x + 0.1, 0.42, body, ha="center", transform=ax.transAxes,
                fontproperties=PROP, fontsize=8.2, color="white")
    ax.set_title("가이던스 — Q3 가속 · 2H MS 두 자릿수 · 연말 레버리지 <3x", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "06_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 95, 125, C["red"]),
        ("Base", 145, 170, C["teal"]),
        ("Bull", 180, 215, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}-{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"현재 ${PX:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT평균 ${PT:.0f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 밴드 (예시 · 투자권유 아님)", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(80, 230)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    cards = [
        (0.2, 1.55, 3.0, 1.4, "실적 10-29", "Q3 · 가이던스\nMS 두 자릿수", C["navy"]),
        (3.5, 1.55, 3.0, 1.4, "IR Day 11-09", "AI 소재 플랫폼\n장기 프레임", C["aps"]),
        (6.8, 1.55, 3.0, 1.4, "필터·FOUP", "액상필터 4연속\n최고 · FOUP 3년+", C["teal"]),
        (0.2, 0.15, 3.0, 1.2, "레버리지", "3.4x -> <3x\nQ2 $200M 상환", C["gold"]),
        (3.5, 0.15, 3.0, 1.2, "첨단 노드", "로직 40% · HBM\nEUV 포토필터", C["ms"]),
        (6.8, 0.15, 3.0, 1.2, "리스크", "MSI/캡ex 사이클\n고객 집중", C["red"]),
    ]
    for x, y, w, h, title, body, c in cards:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + 0.12, y + h - 0.32, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.38, body, ha="center", va="center",
                fontproperties=PROP, fontsize=8, color="white")
    ax.set_title("촉매 · 게이트", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 2.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    ax.add_patch(
        FancyBboxPatch((0.3, 0.35), 9.4, 2.3, boxstyle="round,pad=0.04,rounding_size=0.12",
                       facecolor="#fff7ed", edgecolor=C["ms"], lw=2)
    )
    ax.text(
        5.0, 2.05,
        "미보유 · 10-05 Chase 중하 · 엔트리 눌림 · 고점 88%",
        ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=C["ms"],
    )
    ax.text(
        5.0, 1.1,
        f"현재 ${PX:.2f} · PT ${PT:.0f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}-${H52:.2f}\n"
        "추격보다 눌림 · 다음 실적 10-29 · Q3 가이던스/MS 성장 확인",
        ha="center", va="center", fontproperties=PROP, fontsize=8.5, color=C["ink"],
    )
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
<div class="easy"><b>쉽게:</b> ENTG는 상장 순도·소재 피어셋에서 <b>순수극 대장(~36%)</b>이다.
MKSI·UCTT·ICHR는 진공·서브시스템 성격. 점유 Δ는 <b>+1.5pp</b> 추정 — 액상필터·첨단 노드 콘텐츠.
절대 글로벌 시장점유가 아니라 피어셋 스케일 비교용.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>
{gloss([
    ("APS", "Advanced Purity Solutions — 필터·정제·오염제어·FOUP."),
    ("FOUP", "Front Opening Unified Pod — 웨이퍼 운반 용기. 캡ex에 민감."),
])}

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> ENTG는 <b>장비 0 · 소재 42% · 순도 58%</b>.
AMAT는 장비 거인, MKSI·UCTT는 진공·서브시스템. ENTG의 차별점은 ‘웨이퍼에 들어가는 소재+필터’다.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
{gloss([
    ("MS", "Materials Solutions — CVD/ALD 전구체, CMP 슬러리·패드, 임플란트 가스, 식각·세정."),
    ("MSI", "Million Square Inches — 웨이퍼 면적 출하. 유닛 수요 지표."),
])}
"""


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"ENTG 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0e7490; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0e7490; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0e7490; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ecfeff 0%,#e0f2fe 50%,#ffedd5 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#cffafe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecdd3; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#0e7490; color:#fff; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#ecfeff; border-left:4px solid #0e7490; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#0e7490; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0e7490; }}
    .box {{ background:#fffbeb; border:1px solid #d97706; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpis {{ width:92%; margin:18px auto 0; border-collapse:separate; border-spacing:8px; }}
    .kpis td {{ background:#fff; border:1px solid #cbd5e1; padding:8px 10px; width:25%;
      text-align:center; vertical-align:middle; }}
    .kpis .l {{ font-size:7.5pt; color:#64748b; }}
    .kpis .v {{ font-size:12pt; font-weight:700; color:#0e7490; }}
    .kpis .s {{ font-size:7.5pt; color:#c2410c; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>ENTG 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>ENTG 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Entegris · 반도체 첨단소재 + 순도·오염제어 (필터·FOUP)</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 10-Q · 다음 실적 {EARN} · 시총 ~$25.1B</p>
  <table class="kpis">
    <tr>
      <td><div class="l">현재가</div><div class="v">${PX:.2f}</div><div class="s">52주고 ${H52:.2f}</div></td>
      <td><div class="l">PT 평균</div><div class="v">${PT:.0f}</div><div class="s">업사이드 {UPSIDE*100:+.1f}%</div></td>
      <td><div class="l">Q2 매출</div><div class="v">$883M</div><div class="s">+11.5% YoY</div></td>
      <td><div class="l">Adj EBITDA</div><div class="v">$251M</div><div class="s">마진 28.4%</div></td>
    </tr>
  </table>
  <p style="margin-top:18px">
    <span class="tag">Chase 중하</span>
    <span class="tag warn">고점 88% · 눌림</span>
    <span class="tag">다음 실적 {EARN}</span>
    <span class="tag">미보유</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>돈은 APS(순도·필터·FOUP, 매출 58%)에서 더 빨리 늘고, MS(소재 42%)는 2H에 두 자릿수로 가속한다는 스토리다.</b>
Q2'26: 매출 $883.2M(+11.5%) · GP 47.6% · Adj EBITDA $250.7M(28.4%) · Non-GAAP EPS $0.93 (Est $0.82 Beat).
유닛 매출 +10% / 캡ex +15%. 액상필터 4분기 연속 최고, FOUP는 3년+ 최고.
순레버리지 3.4x (Q2 $200M 상환) · 연말 high-2x 목표. 주가는 고점 -12% · PT +6.7% — <b>미보유 · 눌림 관찰</b>.</p>
{fig_block(charts['flow'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 반도체를 만들 때 <b>약품·가스가 얼마나 깨끗한지</b>와 <b>어떤 소재를 쓰는지</b>가 수율을 가른다.
선폭이 5nm·2nm로 내려갈수록 필터와 소재를 더 많이 쓴다. ENTG는 그 소모품+캡ex(FOUP)를 판다.
장비 회사(AMAT)가 아니라 <b>웨이퍼마다 반복 구매</b>되는 소재·필터가 본체(약 75%)다.</div>
{gloss([
    ("MS", "Materials Solutions — 증착 전구체, CMP, 임플란트 가스, 식각·세정 케미컬."),
    ("APS", "Advanced Purity Solutions — 액상/가스 필터, 정제, FOUP 등 오염제어."),
    ("유닛 vs 캡ex", "매출의 ~75%는 웨이퍼 스타트(반복), ~25%는 팹 투자(WFE 10% + 건설 15%)."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['mix'], '세그먼트 · 엔드마켓')}
{fig_block(charts['growth'], '성장 브리지')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>YoY / 메모</th><th>의미</th></tr>
  <tr><td><b>Total sales</b></td><td>$883.2M</td><td>+11.5% vs $792.4M</td><td>가이던스 상회</td></tr>
  <tr><td>MS sales</td><td>$371.3M</td><td>+4.6% · 매출 42%</td><td>증착·CMP·선택식각</td></tr>
  <tr><td>APS sales</td><td>$514.6M</td><td>+17.0% · 매출 58%</td><td>필터+FOUP 본체</td></tr>
  <tr><td>MS adj OM</td><td>20.9%</td><td>전년 수준</td><td>원가·인력 투자 상쇄</td></tr>
  <tr><td>APS adj OM</td><td>30.3%</td><td>YoY·QoQ 확장</td><td>물량+믹스</td></tr>
  <tr><td>GAAP NI / EPS</td><td>$93.6M / $0.61</td><td>vs $52.8M / $0.35</td><td></td></tr>
  <tr><td>Non-GAAP EPS</td><td>$0.93</td><td>Est $0.82 · Beat</td><td>무형자산상각 $46M</td></tr>
  <tr><td>Adj EBITDA</td><td>$250.7M</td><td>마진 28.4%</td><td>2022 초 이후 GP 최고</td></tr>
  <tr><td>FCF</td><td>$120M</td><td>매출의 14%</td><td>OCF $156 - capex $39</td></tr>
</table>
<p class="small">세그먼트 매출은 내부거래 제거 전. 연결 $883.2M = MS $371.3 + APS $514.6 - elim $2.7. 출처: ENTG 8/4/26 earnings + 10-Q.</p>
<div class="easy"><b>쉽게:</b> 이름표는 “소재 회사”지만 Q2 성장의 주인공은 <b>APS(필터·FOUP)</b>다.
소재(MS)는 +5%로 아직 느리고, 회사는 하반기 두 자릿수를 약속했다. 엔드마켓은 첨단 로직 ~40% · 메모리 ~30% · 나머지 메인스트림.</div>
{gloss([
    ("CMP", "Chemical Mechanical Planarization — 웨이퍼를 평탄하게 가는 슬러리·패드."),
    ("선택 식각", "Selective etch — 원하는 막만 깎는 케미컬. 첨단 노드 콘텐츠."),
])}

{compete_html}

<h2>2. 마진 · 레버리지 · 현금</h2>
{fig_block(charts['pnl'], '마진')}
{fig_block(charts['leverage'], '현금·부채')}
<ul>
  <li>GP 47.6% (Q2'25 44.4%) — 가이던스 상회, 2022 초 이후 최고</li>
  <li>Adj OP 24.5% · Adj EBITDA 28.4% · GAAP OP 18.6% (무형자산상각 $46.1M)</li>
  <li>현금 $353.6M · 장기부채 $3,456M (연초 $3,698M) · 순레버리지 3.4x</li>
  <li>Q2 부채 $200M 상환 · 연말 high-2x / 3x 미만 목표</li>
  <li>1H 매출 $1,695.1M · Adj EBITDA $476.8M · FY26 capex 가이던스 $250M</li>
  <li>Life Sciences Fluid Management 미국 사업 철수 · Logan UT 공장 폐쇄 (본업 집중)</li>
</ul>

<h2>3. 전망 · 시나리오</h2>
{fig_block(charts['guide'], 'Q3 가이던스')}
{fig_block(charts['scen'], '주가 시나리오')}
<table>
  <tr><th>드라이버</th><th>내용</th></tr>
  <tr><td>Q3 매출</td><td>$905-935M (중간 약 +14% YoY) · GP 47.5-48.5% · Adj EPS $0.96-1.04</td></tr>
  <tr><td>Q4</td><td>Q3 중간 대비 약 +4% seq = 전년 대비 중십몇 %</td></tr>
  <tr><td>MS 2H</td><td>증착·CMP·식각·임플란트 수요로 두 자릿수 YoY 가이던스</td></tr>
  <tr><td>MSI</td><td>연초 중한 자릿수 → 현재 7-8% 성장 가정</td></tr>
  <tr><td>팹 사이클</td><td>선단 증설 ~20건 추적 (로직 8-10 · 메모리 7-8 · 패키징 6-8). 팹건설 본격은 2027</td></tr>
  <tr><td>밸류</td><td>${PX:.2f} · PT ${PT:.0f} (H $215 / L $120) · 52주 ${L52:.2f}-${H52:.2f} · 업사이드 {UPSIDE*100:+.1f}%</td></tr>
</table>
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$95-125</td><td>MSI/캡ex 꺾임 · 레버리지 재확대 · 고객 집중 충격</td></tr>
  <tr><td>Base</td><td>$145-170</td><td>Q3 가이던스 달성 · 마진 유지 · 현재가가 이 밴드 안</td></tr>
  <tr><td>Bull</td><td>$180-215</td><td>MS 2H 가속 · 필터 점유 · PT 고가 · IR Day 재평가</td></tr>
</table>

<h2>4. 촉매 · 포트 실행</h2>
{fig_block(charts['cat'], '촉매')}
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (10-05 포폴 · Qual)</b><br/>
<b>미보유</b> · 10-05 심층 Chase <b>중하</b> · 엔트리 <b>눌림</b>.<br/>
현재 ${PX:.2f} · 컨센서스 PT ${PT:.0f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}-${H52:.2f} (고점 -12.0%).<br/>
실행: <b>추격보다 눌림</b>. 다음 실적 <b>2026-10-29</b> (아직 EARN_D5 아님).<br/>
게이트: Q3 가이던스 · MS 두 자릿수 · APS 필터/FOUP · 레버리지 &lt;3x · 11-09 IR Day.
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>반복 유닛(필터·소재) 75% + 팹 캡ex 25%</u>.
Q2는 APS가 성장을 끌었고 마진·현금은 좋아졌다. 다만 <b>지금 자리(고점 88% · 업사이드 +7% · 중하)</b>는 추격 자리가 아니다. 관망·눌림.</div>

<h2>부록 · 출처</h2>
<p class="small">
Entegris Q2 2026 earnings release / Exhibit 99.1 / 10-Q (기간 종료 2026-06-27, 발표 2026-08-04) ·
earnings call · yfinance 가격·PT ({ASOF}). 피어 믹스·점유는 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 ENTG · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> int:
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "growth": chart_growth_bridge(),
        "pnl": chart_pnl(),
        "leverage": chart_leverage(),
        "guide": chart_guide(),
        "scen": chart_scenarios(),
        "cat": chart_catalysts(),
        "pos": chart_position(),
    }
    bundle, cpaths = build_compete_charts("ENTG", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("ENTG", CHART_DIR, html_doc)
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

        tag = "sepa-rev-entg"
        notes = (
            f"## ENTG 수익구조분석 ({ASOF})\n\n"
            f"Entegris · 반도체 소재 + 순도솔루션 · Q2'26.\n\n"
            f"- Rev $883M (+11.5%) · GP 47.6% · Adj EBITDA $251M (28.4%)\n"
            f"- APS 58% ($515M, +17%) / MS 42% ($371M, +5%)\n"
            f"- 유닛 75% / 캡ex 25% · 레버리지 3.4x · Q3 $905-935M\n"
            f"- 미보유 · Chase 중하 · 업사이드 {UPSIDE*100:+.1f}% "
            f"(PT ${PT:.0f} · px ${PX:.2f})\n"
            f"- 눌림 관찰 · 다음 실적 2026-10-29\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — ENTG",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
