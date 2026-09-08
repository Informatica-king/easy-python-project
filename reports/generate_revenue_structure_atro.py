#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(ATRO) — Astronics 항공전자·테스트 + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-08-28"
PX = 77.56
PT = 89.55
H52 = 94.46
L52 = 28.40
UPSIDE = PT / PX - 1.0
EARN = "08-18"  # Q2'26 reported (ended 7/4/26)
OUT_PDF = [
    Path("/opt/cursor/artifacts/ATRO_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/ATRO_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/ATRO_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/ATRO_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/atro")
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
    "sand": "#e8dcc8",
    "aero": "#1d4ed8",
    "test": "#c2410c",
    "ct": "#0369a1",
    "mil": "#7c3aed",
    "ga": "#0f766e",
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
    fig, ax = plt.subplots(figsize=(9.2, 3.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    boxes = [
        (0.1, 0.7, 1.85, 1.6, "항공·방산\n수요", C["sand"]),
        (2.15, 0.7, 1.75, 1.6, "Cabin power\n·IFEC·Seat", C["aero"]),
        (4.1, 0.7, 1.75, 1.6, "Test Systems\n·Radio Test", C["test"]),
        (6.05, 0.7, 1.7, 1.6, "수주·백로그\n·생산", C["navy"]),
        (7.95, 0.7, 1.75, 1.6, "매출·\nAdj EBITDA", C["teal"]),
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
            fontproperties=PROP_B, fontsize=8.5, color=tc,
        )
    ax.set_title(
        "비즈니스 한눈에 — 항공기 객실·전력·연결 + 군용 테스트",
        fontproperties=PROP_B, fontsize=12, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [91.3, 8.7]
    labels = ["Aerospace 91.3%", "Test 8.7%"]
    ax.pie(
        sizes, labels=labels,
        colors=[C["aero"], C["test"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.5),
    )
    ax.set_title("세그먼트 매출 (Q2'26)", fontproperties=PROP_B, fontsize=10)

    ax = axes[1]
    labs = ["CT", "Military", "GA", "Other"]
    vals = [177.0, 30.6, 27.6, 2.1]
    cols = [C["ct"], C["mil"], C["ga"], C["muted"]]
    bars = ax.bar(labs, vals, color=cols, width=0.6)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("Aerospace 시장별 (Q2'26)", fontproperties=PROP_B, fontsize=10)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2, v + 3, f"{v:.0f}",
            ha="center", fontsize=8, fontproperties=PROP,
        )
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_growth_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    labels = [
        "Total\n+27.0%",
        "Aerospace\n+22.6%",
        "Test\n+105%",
        "Adj EBITDA\n$51.5M",
        "Op Margin\n15.6%",
    ]
    vals = [27.0, 22.6, 105.0, 103.0, 15.6]  # EBITDA ~2x YoY narrative
    # Use display values carefully - for EBITDA show YoY approx doubling
    display = ["+27%", "+23%", "+105%", "19.8% mg", "15.6%"]
    colors = [C["green"], C["aero"], C["test"], C["teal"], C["navy"]]
    bars = ax.bar(labels, [27, 22.6, 40, 35, 15.6], color=colors, width=0.55)
    ax.set_ylabel("표시용 스케일", fontproperties=PROP)
    ax.set_title(
        "성장 브리지 — 항공 본체 + 테스트 반등 → 마진 레버리지",
        fontproperties=PROP_B, fontsize=11,
    )
    for b, d in zip(bars, display):
        ax.text(
            b.get_x() + b.get_width() / 2, b.get_height() + 1.2, d,
            ha="center", fontproperties=PROP, fontsize=8,
        )
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "03_growth_bridge.png")


def chart_pnl() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    labs = ["Sales\n$M", "Gross\n$M", "Op Inc\n$M", "Adj EBITDA\n$M", "NI\n$M"]
    q225 = [204.7, 52.8, 4.8, 25.4, 1.3]  # prior Q2 approx from narrative / yahoo Q2'25
    # Prior year Q2 sales from +27% → 260/1.27 ≈ 204.7 — matches yahoo 2025-06-30
    # Adj EBITDA prior $25.4M from transcript
    q226 = [260.0, 86.9, 40.5, 51.5, 35.1]
    x = range(len(labs))
    ax.bar([i - 0.18 for i in x], q225, width=0.35, color="#94a3b8", label="Q2'25")
    ax.bar([i + 0.18 for i in x], q226, width=0.35, color=C["aero"], label="Q2'26")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labs, fontproperties=PROP)
    ax.set_title("손익 확대 — 매출·마진·Adj EBITDA 동반 개선", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8)
    fig.tight_layout()
    return save_fig(fig, "04_pnl.png")


def chart_backlog() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    # Use known Q2 backlog + bookings
    cats = ["Bookings\n$M", "B2B", "Backlog\n$M", "Aero BL\n$M", "Test BL\n$M"]
    vals = [306.2, 1.18, 780.6, 657.2, 123.3]
    # normalize for bar display - separate scales is hard; use two axes conceptually via labels
    display_vals = [306.2, 118, 780.6, 657.2, 123.3]  # B2B *100
    colors = [C["gold"], C["teal"], C["navy"], C["aero"], C["test"]]
    bars = ax.bar(cats, display_vals, color=colors, width=0.55)
    labels_txt = ["306", "1.18x", "781", "657", "123"]
    ax.set_title("수주·백로그 — 3분기 연속 기록 백로그", fontproperties=PROP_B, fontsize=11)
    for b, t in zip(bars, labels_txt):
        ax.text(
            b.get_x() + b.get_width() / 2, b.get_height() + 8, t,
            ha="center", fontproperties=PROP, fontsize=8,
        )
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.text(
        0.98, 0.02, "B2B는 1.18×를 118로 표시(스케일)",
        transform=ax.transAxes, ha="right", fontsize=7,
        color=C["muted"], fontproperties=PROP,
    )
    fig.tight_layout()
    return save_fig(fig, "05_backlog.png")


def chart_guide() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    metrics = ["FY26 매출\n$B 중점", "Q3 매출\n$M 중점"]
    # prior guide not fully known - company raised to 1.02-1.04; use mid
    vals = [1.03, 270]
    ax.bar(metrics, vals, color=[C["aero"], C["teal"]], width=0.45)
    ax.set_title("가이던스 — FY26 매출 $1.02–1.04B · Q3 $265–275M", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.02, f"{v:g}", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "06_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    bands = [("Bear", 45.0, 60.0), ("Base", 70.0, 90.0), ("Bull", 95.0, 120.0)]
    colors = [C["red"], C["gold"], C["green"]]
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
        (0.2, 0.4, 2.2, 2.1, "백로그\n전환", C["navy"]),
        (2.7, 0.4, 2.2, 2.1, "FLRAA\n·Radio Test", C["mil"]),
        (5.2, 0.4, 2.2, 2.1, "FY26 가이던스\n$1.02–1.04B", C["aero"]),
        (7.7, 0.4, 2.0, 2.1, "다음 실적\n(~11-05)", C["gold"]),
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
    fig, ax = plt.subplots(figsize=(8.6, 3.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.0)
    ax.axis("off")
    ax.add_patch(
        FancyBboxPatch(
            (0.3, 0.5), 9.2, 2.0, boxstyle="round,pad=0.05,rounding_size=0.12",
            facecolor="#eff6ff", edgecolor=C["aero"], lw=2,
        )
    )
    ax.text(
        5.0, 1.9, "미보유 · Chase 중 · SOFT WAIT · 눌림 대기",
        ha="center", va="center", fontproperties=PROP_B, fontsize=12, color=C["aero"],
    )
    ax.text(
        5.0, 1.15,
        f"현재 ${PX:.2f} · PT ${PT:.2f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 고점 ${H52:.2f} (−18%)\n"
        "본선∩GO 없음 · 추격 금지 · 백로그·마진 확인 후 위성만",
        ha="center", va="center", fontproperties=PROP, fontsize=9, color=C["ink"],
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
        bold = " style='font-weight:700;background:#eff6ff'" if row.get("subject") else ""
        mix_body.append(
            f"<tr{bold}><td>{row['name']}</td>{cells}"
            f"<td class='small'>{row.get('note','')}</td></tr>"
        )
    ttm_fig = fig_block(charts["ttm"], "TTM 매출 규모") if "ttm" in charts else ""
    return f"""
<h2>1-B. 심층 섹터 경쟁 점유율 · 변화</h2>
<p><b>섹터</b> {bundle.sector_ko}</p>
<div class="easy"><b>쉽게:</b> ATRO는 상장 항공부품·전자 피어셋에서 <b>소형(~3%)</b>이다.
TDG·HWM이 스케일을 지배. ATRO 점유 Δ는 <b>+0.3pp</b> 추정 — 기록 매출로 상대 비중 소폭↑.
절대 시장점유가 아니라 피어 대비 상대 크기.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> ATRO는 <b>Aerospace ~91%</b>가 본체이고 Test ~9%가 옵션·회복 스토리.
피어(HEI·TDG·HWM)도 항공 비중이 높다. ATRO만 군용 Radio Test 백로그가 눈에 띈다.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
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
      @bottom-center {{ content:"ATRO 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1d4ed8; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #3b82f6; padding-bottom:3px; color:#1e3a8a; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#1e3a5f; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#eff6ff 0%,#dbeafe 55%,#e0f2fe 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#dbeafe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecdd3; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#1d4ed8; color:#fff; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#eff6ff; border-left:4px solid #1d4ed8; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1d4ed8; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#1d4ed8; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1d4ed8; }}
    .kpi .s {{ font-size:7.5pt; color:#2563eb; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>ATRO 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>ATRO 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Astronics · 항공 객실전력·IFEC·Seat Motion + Test Systems</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적({EARN} 발표) · 시총 ~$3.3B · ${PX:.2f}</p>
  <div style="margin-top:22px">
    <span class="tag good">매출 +27% 기록</span>
    <span class="tag good">Adj EBITDA 19.8%</span>
    <span class="tag good">백로그 $781M</span>
    <span class="tag">FY26 $1.02–1.04B</span>
    <span class="tag warn">Chase 중 · SOFT</span>
  </div>
  <div style="margin-top:28px">
    <div class="kpi"><div class="l">Q2 매출</div><div class="v">$260M</div><div class="s">YoY +27%</div></div>
    <div class="kpi"><div class="l">Aero / Test</div><div class="v">91/9</div><div class="s">$237M / $23M</div></div>
    <div class="kpi"><div class="l">Adj EBITDA</div><div class="v">$51.5M</div><div class="s">마진 19.8%</div></div>
    <div class="kpi"><div class="l">업사이드</div><div class="v">{UPSIDE*100:+.0f}%</div><div class="s">PT ${PT:.0f}</div></div>
  </div>
  <p class="small" style="margin-top:36px;max-width:540px;margin-left:auto;margin-right:auto">
    Aerospace가 매출·이익 본체(Commercial Transport seat motion·IFEC). Test는 소형이지만
    Radio Test 양산 수주로 백로그 급증. FY26 가이던스 상향·기록 백로그가 스토리.
    심층: Chase 중 · SOFT WAIT · 본선∩GO 없음 → 추격보다 눌림.
  </p>
</section>

<h2>0. 한줄 결론</h2>
<div class="box">
<b>구조는 “항공 객실·전력 본체 + 테스트 회복” — 실적은 강한데 타이밍은 WAIT.</b>
Q2'26 매출 $260M(+27%) · Aerospace $237M(마진 20.3%) · Test $23M ·
Adj EBITDA $51.5M(19.8%) · 백로그 $781M(B2B 1.18) · FY26 $1.02–1.04B 상향.
포트: <b>미보유 · Chase 중 · SOFT</b> · 업사이드 {UPSIDE*100:+.0f}% · 고점 −18% —
본선∩GO 없음 · <b>추격 금지 · 눌림·위성만</b>.
</div>

<h2>1. 비즈니스 구조</h2>
<div class="easy"><b>쉽게:</b> Astronics는 비행기 좌석·전원·기내 엔터/연결(IFEC) 장비를 만들고,
별도로 군·통신용 <b>테스트 장비</b>도 판다. 돈의 대부분 항공(Aerospace)에서 나온다.</div>
{fig_block(charts['flow'], '수요 → Aero/Test → 백로그 → Adj EBITDA')}
{gloss([
    ("IFEC", "Inflight Entertainment & Connectivity — 기내 엔터·와이파이·연결"),
    ("Seat Motion", "항공기 좌석 구동·모션 시스템 (BMA 인수 기여)"),
    ("Book-to-Bill", "수주/매출 비율. 1 초과면 백로그 축적"),
    ("FLRAA / MV-75", "미 육군 차세대 장거리 돌격기 프로그램 — 엔지니어링 계약 확정"),
])}

{compete_html}

<h2>2. 매출·손익 (Q2'26)</h2>
<div class="easy"><b>쉽게:</b> 항공이 23% 늘고 테스트가 두 배 가까이 뛰면서
전체 매출 +27%, 영업이익·Adj EBITDA가 크게 늘었다. “물량↑ → 고정비 흡수 → 마진↑”.</div>
{fig_block(charts['mix'], '세그먼트·시장 믹스')}
{fig_block(charts['growth'], '성장 브리지')}
{fig_block(charts['pnl'], '손익 비교')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>Q2'25</th><th>메모</th></tr>
  <tr><td>Total sales</td><td>$260.0M</td><td>~$204.7M</td><td>+27.0% 기록</td></tr>
  <tr><td>Aerospace</td><td>$237.3M (91.3%)</td><td>$193.6M</td><td>+22.6% · OP 20.3%</td></tr>
  <tr><td> Commercial Transport</td><td>$177.0M</td><td>$145.6M</td><td>+21.6% · Seat/IFEC</td></tr>
  <tr><td> Military Aircraft</td><td>$30.6M</td><td>$27.4M</td><td>+11.7% · 비행전력</td></tr>
  <tr><td> General Aviation</td><td>$27.6M</td><td>$18.4M</td><td>+50.3% · VVIP IFEC</td></tr>
  <tr><td>Test Systems</td><td>$22.7M (8.7%)</td><td>$11.1M</td><td>+105% · OP $0.6M</td></tr>
  <tr><td>Gross profit</td><td>$86.9M (33.4%)</td><td>—</td><td>+760bps</td></tr>
  <tr><td>Operating income</td><td>$40.5M (15.6%)</td><td>—</td><td>기록</td></tr>
  <tr><td>Adj EBITDA</td><td>$51.5M (19.8%)</td><td>$25.4M</td><td>다년간 고점 마진</td></tr>
  <tr><td>Net income / EPS</td><td>$35.1M / $0.75</td><td>—</td><td>희석 EPS</td></tr>
</table>
{gloss([
    ("BMA", "Bühler Motor Aviation — 2025-10 인수. Q2 Seat Motion에 +$5.9M"),
    ("IEEPA tariff refund", "Q2 총이익에 +$2.0M 일회성 환급"),
    ("Radio Test Sets", "TS-4549/T — 미 육군 양산 수주 $44.7M (Test 백로그)"),
])}

<h2>3. 수주 · 가이던스</h2>
{fig_block(charts['backlog'], '수주·백로그')}
{fig_block(charts['guide'], 'FY26·Q3 가이던스')}
<div class="easy"><b>쉽게:</b> 회사가 “올해 매출을 더 높게 본다”고 올렸다($1.02–1.04B).
백로그 $781M 중 ~82%가 향후 12개월 매출로 전환될 전망.</div>
<table>
  <tr><th>지표</th><th>내용</th></tr>
  <tr><td>FY26 revenue guide</td><td>$1.02–1.04B (상향)</td></tr>
  <tr><td>Q3'26 sales guide</td><td>$265–275M (또 분기 기록 예상)</td></tr>
  <tr><td>Q2 bookings / B2B</td><td>$306.2M / 1.18×</td></tr>
  <tr><td>Total backlog</td><td>$780.6M (3분기 연속 기록)</td></tr>
  <tr><td>Aerospace backlog</td><td>$657.2M · FLRAA 엔지니어링 $27.4M 부킹</td></tr>
  <tr><td>Test backlog</td><td>$123.3M · Army Radio Test 양산 개시</td></tr>
  <tr><td>TTM book-to-bill</td><td>1.13× · TTM bookings $1.06B</td></tr>
</table>

<h2>4. 시나리오 · 촉매</h2>
{fig_block(charts['scen'], '주가 시나리오 밴드')}
{fig_block(charts['cat'], '촉매 카드')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$45–60</td><td>항공기 인도 둔화 · IFEC 수요↓ · Test 마진 재악화</td></tr>
  <tr><td>Base</td><td>$70–90</td><td>가이던스 달성 · 백로그 전환 · PT 수렴</td></tr>
  <tr><td>Bull</td><td>$95–120</td><td>마진 지속 · FLRAA/Radio Test 가속 · 고점 돌파</td></tr>
</table>

<h2>5. 포트 실행</h2>
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (8/28 심층)</b><br/>
미보유 · Chase <b>중</b> · 타이밍 <b>SOFT WAIT</b> · 본선∩GO <b>없음</b>.<br/>
현재 ${PX:.2f} · PT ${PT:.2f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}–${H52:.2f} · 고점 −18%.<br/>
실행: <b>추격 금지</b> · 관망. 재검토는 MA20 눌림 + SOFT→GO 전환 + 현금여유 시 위성 소액.<br/>
품질 게이트: Q3 가이던스($265–275M) 달성 · Aero 마진 유지 · Test 흡수율 개선.
</div>

<p class="small">생성: 수익구조분석() · 티커 ATRO · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart<br/>
출처: Astronics Q2 2026 earnings release (2026-08-18, Business Wire / IR) · yfinance · 피어 점유/믹스는 방향 비교용 추정</p>
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
    bundle, cpaths = build_compete_charts("ATRO", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("ATRO", CHART_DIR, html_doc)
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

        tag = "sepa-rev-atro"
        notes = (
            f"## ATRO 수익구조분석 ({ASOF})\n\n"
            f"Astronics · Q2'26 · Aerospace 91% / Test 9% · FY26 $1.02–1.04B.\n\n"
            f"- 매출 $260M(+27%) · Adj EBITDA $51.5M(19.8%) · 백로그 $781M\n"
            f"- Chase 중 · SOFT WAIT · 업사이드 {UPSIDE*100:+.1f}% (PT ${PT:.0f} · px ${PX:.2f})\n"
            f"- 본선∩GO 없음 · 추격 금지 · 눌림·위성만\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — ATRO",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
