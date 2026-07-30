#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(RELY) — Remitly 크로스보더 송금 + 경쟁점유/믹스 + WeasyPrint PDF."""

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
    Path("/opt/cursor/artifacts/RELY_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/RELY_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/RELY_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/RELY_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/rely")
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
    "rely": "#0ea5e9",
    "us": "#1d4ed8",
    "ca": "#0f766e",
    "row": "#a16207",
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
        (0.1, 0.7, 1.7, 1.6, "송금자\n앱·웹", C["sand"]),
        (1.95, 0.7, 1.75, 1.6, "수수료\n+ FX스프레드", C["rely"]),
        (3.9, 0.7, 1.75, 1.6, "지급망\n지갑·은행·캐시", C["teal"]),
        (5.85, 0.7, 1.75, 1.6, "수취인\n175+국", C["navy"]),
        (7.8, 0.7, 1.9, 1.6, "Growth\n고액·Biz·Receiver", C["gold"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = "white" if c in (C["rely"], C["teal"], C["navy"], C["gold"]) else C["ink"]
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    for x in (1.85, 3.75, 5.7, 7.65):
        ax.annotate("", xy=(x + 0.08, 1.5), xytext=(x - 0.08, 1.5),
                    arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6))
    ax.set_title("RELY 가치사슬 — 디지털 송금 → 수수료·FX → 지급 → 인접 성장엔진", fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_geo_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9))
    # Q1'26 send-customer geography
    labels = ["미국", "캐나다", "기타"]
    vals = [297.785, 42.914, 112.103]
    colors = [C["us"], C["ca"], C["row"]]
    ax = axes[0]
    ax.pie(vals, labels=labels, colors=colors, autopct=lambda p: f"{p:.0f}%",
           textprops={"fontproperties": PROP, "fontsize": 9}, startangle=90,
           wedgeprops=dict(width=0.45, edgecolor="white"))
    ax.set_title("Q1'26 매출 지리 (송금자 소재)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    yoy = [297.785 / 237.300 - 1, 42.914 / 38.646 - 1, 112.103 / 85.678 - 1]
    bars = ax.bar(labels, [v * 100 for v in yoy], color=colors, width=0.55)
    ax.axhline(0, color="#94a3b8", lw=0.8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("지역별 매출 성장률", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, yoy):
        ax.text(b.get_x() + b.get_width() / 2, v * 100 + 1.2, f"{v*100:+.0f}%",
                ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "02_geo_mix.png")


def chart_unit_econ() -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(9.4, 3.6))
    # Volume / customers / take-rate
    ax = axes[0]
    ax.bar(["Q1'25", "Q1'26"], [16.2, 22.1], color=[C["sand"], C["rely"]], width=0.5)
    ax.set_title("Send Volume ($B)", fontproperties=PROP_B, fontsize=10)
    ax.set_ylabel("$B", fontproperties=PROP)
    for i, v in enumerate([16.2, 22.1]):
        ax.text(i, v + 0.3, f"{v:.1f}", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    ax.bar(["Q1'25", "Q1'26"], [8.0, 9.6], color=[C["sand"], C["teal"]], width=0.5)
    ax.set_title("Active Customers (M)", fontproperties=PROP_B, fontsize=10)
    for i, v in enumerate([8.0, 9.6]):
        ax.text(i, v + 0.15, f"{v:.1f}", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[2]
    # take rate = rev/volume
    tr = [361.6 / 16200 * 100, 452.8 / 22100 * 100]
    ax.bar(["Q1'25", "Q1'26"], tr, color=[C["sand"], C["gold"]], width=0.5)
    ax.set_title("Take Rate (Rev/Volume)", fontproperties=PROP_B, fontsize=10)
    ax.set_ylabel("%", fontproperties=PROP)
    for i, v in enumerate(tr):
        ax.text(i, v + 0.03, f"{v:.2f}%", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.suptitle("단위경제 — 볼륨↑ · 고객↑ · 테이크레이트 소폭↓(믹스)", fontproperties=PROP_B, fontsize=11, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "03_unit_econ.png")


def chart_growth_engines() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    # Conceptual mix FY26 guidance
    labels = ["Core\nSenders", "Growth\nAccelerators\n(고액·Biz·Receiver 등)"]
    vals = [95, 5]
    colors = [C["rely"], C["gold"]]
    left = 0
    for lab, v, c in zip(labels, vals, colors):
        ax.barh([0], [v], left=left, color=c, height=0.45, edgecolor="white")
        ax.text(left + v / 2, 0, f"{lab}\n{v}%", ha="center", va="center",
                fontproperties=PROP_B, fontsize=9, color="white" if v > 8 else C["ink"])
        left += v
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_xlabel("FY26 매출 구성 가이던스 근사", fontproperties=PROP)
    ax.set_title("성장 엔진 — Core 본체 + Accelerators(~5% → 2028 >10% 목표)", fontproperties=PROP_B, fontsize=11)
    ax.text(0.99, -0.22, "고액송금($5k+) 볼륨 +73% YoY · Biz 볼륨 QoQ +30% · Receiver 매출 YoY 2배+",
            transform=ax.transAxes, ha="right", fontproperties=PROP, fontsize=7.5, color=C["muted"])
    fig.tight_layout()
    return save_fig(fig, "04_growth_engines.png")


def chart_pnl_stack() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 4.2))
    # Q1'26 waterfall-ish stacked bars vs Q1'25
    cats = ["매출", "−거래비", "RLTE", "−마케팅", "−인건/기술", "Adj.EBITDA"]
    # Simplified illustrative levels ($M)
    q26 = [452.8, 144.9, 307.9, 86.4, None, 101.6]
    # show key bars
    names = ["Revenue", "Txn Exp", "RLTE\n(Rev-Txn)", "Marketing", "Adj.\nEBITDA"]
    vals = [452.8, 144.9, 307.9, 86.4, 101.6]
    colors = [C["rely"], C["red"], C["teal"], C["gold"], C["green"]]
    bars = ax.bar(names, vals, color=colors, width=0.55)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("Q1'26 수익 스택 (핵심 라인)", fontproperties=PROP_B, fontsize=12)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 6, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.text(0.99, -0.14, "NI $49.1M (+332%) · Adj.EBITDA 마진 ~22%",
            transform=ax.transAxes, ha="right", fontproperties=PROP, fontsize=8, color=C["muted"])
    fig.tight_layout()
    return save_fig(fig, "05_pnl_stack.png")


def chart_outlook() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    labels = ["Q1'26A", "Q2'26E", "FY26E\n(중점)"]
    # midpoint FY 1.9675
    vals = [0.453, 0.484, 1.968]
    colors = [C["rely"], C["teal"], C["navy"]]
    bars = ax.bar(labels, vals, color=colors, width=0.5)
    ax.set_ylabel("$B", fontproperties=PROP)
    ax.set_title("매출 가이던스 — Q2 $483–485M · FY26 $1.96–1.975B (+20–21%)", fontproperties=PROP_B, fontsize=11)
    for b, v, t in zip(bars, vals, ["실적", "+17–18%", "+20–21%"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.04, f"${v:.2f}B\n{t}", ha="center",
                fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    ax.set_ylim(0, 2.35)
    fig.tight_layout()
    return save_fig(fig, "06_outlook.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    # Price scenarios around PT — illustrative for portfolio
    px = 23.29
    scenarios = [
        ("Bear", 16, 19, C["red"]),
        ("Base", 24, 29, C["teal"]),
        ("Bull", 30, 36, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}–{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(px, color=C["navy"], lw=1.5, ls="--")
    ax.text(px, 2.55, f"현재 ${px:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(29.33, color=C["gold"], lw=1.2, ls=":")
    ax.text(29.33, -0.7, "PT평균~$29.3", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 밴드 (예시 · 투자권유 아님)", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(12, 40)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.axis("off")
    items = [
        (0.05, "08-05", "실적", "Q2 가이던스 소화\nEARN_D5 주의", C["red"]),
        (0.28, "2H'26", "가속", "Core+Accel\n하반기 성장 가속 가이던스", C["teal"]),
        (0.52, "Accel", "믹스", "고액·Biz·Receiver\nFY26~5% → '28>10%", C["gold"]),
        (0.76, "마진", "레버리지", "AI·스케일\nAdj.EBITDA 레버리지", C["navy"]),
    ]
    for x, tag, title, body, c in items:
        ax.add_patch(FancyBboxPatch((x, 0.25), 0.2, 0.55, boxstyle="round,pad=0.02,rounding_size=0.04",
                                    facecolor=c, edgecolor="white", lw=1.5, transform=ax.transAxes))
        ax.text(x + 0.1, 0.68, tag, ha="center", transform=ax.transAxes, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + 0.1, 0.55, title, ha="center", transform=ax.transAxes, fontproperties=PROP_B, fontsize=10, color="white")
        ax.text(x + 0.1, 0.38, body, ha="center", transform=ax.transAxes, fontproperties=PROP, fontsize=7.5, color="white")
    ax.set_title("촉매 캘린더 — 이벤트 갭베팅 금지 · 소화 후 눌림", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "위성 워치 1순위\n코어 아님", C["rely"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "≤~$70 / 동시 1종\n현금 45%+ 유지", C["teal"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", "08-05 소화 후\n$22.69–23.39 눌림", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "금지", "실적 전 추격 · 물타기 · 1주 과대비중", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "손절감각", "TA stop ~$21.41 · 무효시 즉시 정리", C["navy"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    facecolor=c, edgecolor="white", lw=1.5))
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.35, body, ha="center", va="center", fontproperties=PROP, fontsize=8.5, color="white")
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
        mix_body.append(f"<tr><td>{r['name']}{tag}</td>{cells}<td class='small'>{r.get('note','')}</td></tr>")
    ttm_fig = fig_block(charts["ttm"], "TTM 매출 규모") if "ttm" in charts else ""
    return f"""
<h2>1-B. 심층 섹터 경쟁 점유율 · 변화</h2>
<p><b>섹터</b> {bundle.sector_ko}</p>
<div class="easy"><b>쉽게:</b> 송금은 WU·MoneyGram 같은 <b>에이전트 공룡</b>과 Wise·Remitly 같은
<b>디지털 네이티브</b>가 같은 파이에서 싸운다. Remitly는 점유율 자체는 작지만
<b>성장률·디지털 지갑 지급</b>으로 점유를 늘리는 쪽이다.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>
{gloss([
    ("pp", "percentage points. 1.9%→2.3%면 +0.4pp."),
    ("디지털 네이티브", "에이전트 매장 없이 앱·웹 중심으로 송금하는 사업자."),
])}

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> Remitly는 아직 <b>개인 송금(Core)</b>이 본체(~95%).
Wise는 플랫폼·비즈니스 비중이 더 크고, WU는 컨슈머 MT + B2B 하이브리드에 가깝다.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
{gloss([
    ("Growth Accelerators", "고액송금($5k+)·비즈니스·Receiver 등 Core 인접 성장축. FY26~5% 매출 가이던스."),
    ("TTM", "Trailing Twelve Months — 규모 감각용."),
])}
"""


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"RELY 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0ea5e9; padding-bottom:3px; color:#1e3a5f; }}
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
    .easy {{ background:#ecfeff; border-left:4px solid #0ea5e9; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0ea5e9; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#0ea5e9; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>RELY 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>RELY 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Remitly Global · 크로스보더 디지털 송금 · 수수료 + FX 스프레드</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1'26 실적(5/6) · 다음 실적 ~08-05 · 위성 워치</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~$23.3</div><div class="s">시총 ~$4.9B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~$29.3</div><div class="s">업사이드 ~+26%</div></span>
    <span class="kpi"><div class="l">Q1 매출</div><div class="v">$453M</div><div class="s">+25% YoY</div></span>
    <span class="kpi"><div class="l">Send Vol</div><div class="v">$22.1B</div><div class="s">+37% · 고객 9.6M</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">Chase 상·08-05</span>
    <span class="tag good">TA 분할OK(실적후)</span>
    <span class="tag warn">위성 ≤$70 · EARN_D5</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>디지털 송금 앱으로 볼륨을 모으고, 수수료+FX 스프레드로 버는 크로스보더 핀테크.</b>
공시 세그먼트는 <b>단일</b>이지만, 실질 엔진은 <b>Core 송금자</b> + <b>Growth Accelerators</b>(고액·비즈니스·Receiver 등).
Q1'26: 매출 +25% · 볼륨 +37% · Adj.EBITDA +74%(마진~22%). FY26 매출 <b>$1.96–1.975B (+20–21%)</b>.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 이민·디아스포라 고객이 앱으로 돈을 보내면 Remitly가
<b>수수료</b>와 <b>환전 마진</b>을 받는다. 기기를 팔지 않고, 거래가 날수록 돈이 된다.</div>
{gloss([
    ("Send Volume", "고객이 보낸 원금 합계. 매출이 아님."),
    ("Take Rate", "매출 ÷ Send Volume. Q1'26 ~2.05%."),
    ("FX 스프레드", "고객에게 제시한 환율과 회사가 조달한 환율 차이."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '지리 믹스 — 송금자 소재국')}
{fig_block(charts['03'], '단위경제')}
<table>
  <tr><th>항목</th><th>Q1'26</th><th>YoY</th><th>의미</th></tr>
  <tr><td><b>Revenue</b></td><td>$452.8M</td><td>+25%</td><td>수수료+FX · 단일 세그먼트</td></tr>
  <tr><td>Send Volume</td><td>$22.1B</td><td>+37%</td><td>볼륨이 매출보다 빠름 → 테이크레이트 희석</td></tr>
  <tr><td>Active Customers</td><td>9.6M</td><td>+20%</td><td>분기 활성 송금자</td></tr>
  <tr><td>Transaction Exp.</td><td>$144.9M</td><td>+19%</td><td>지급·결제·사기·컴플라이언스</td></tr>
  <tr><td>RLTE (Rev−Txn)</td><td>~$308M</td><td>—</td><td>거래 후 남는 1차 마진 풀</td></tr>
  <tr><td>Adj.EBITDA</td><td>$101.6M</td><td>+74%</td><td>마진 ~22% · 영업 레버리지</td></tr>
  <tr><td>Net Income</td><td>$49.1M</td><td>+332%</td><td>흑자 스케일 구간</td></tr>
</table>
<p class="small">지리(송금자): 미국 $298M(66%) · 캐나다 $43M(9%) · 기타 $112M(25%).
미국이 본체이나 RoW 성장(+31%)이 더 빠름.</p>
<div class="easy"><b>쉽게:</b> “보낸 돈”($22B)의 약 <b>2%</b>가 회사 매출이 된다.
볼륨이 매출보다 빨리 늘면 고액·저수수료 믹스가 섞였다는 뜻 — 그래도 EBITDA는 더 빨리 늘었다.</div>
{gloss([
    ("RLTE", "Revenue less Transaction Expenses — 거래직접비 차감 후."),
    ("Transaction expenses", "지급 파트너·결제·차지백·사기방지·컴플라이언스 비용."),
])}

{compete_html}

<h2>2. 성장 엔진 — Core vs Accelerators</h2>
{fig_block(charts['04'], '성장 엔진 믹스')}
{fig_block(charts['05'], '수익 스택')}
<ul>
  <li><b>Core Senders:</b> 기존 개인 송금 본체. 코리도어 아웃퍼폼·활성 고객 +20%.</li>
  <li><b>High Value ($5k+):</b> 볼륨 +73% YoY · 볼륨믹스 +220bp. Growth Accelerator로 편입.</li>
  <li><b>Remitly Business:</b> 활성 비즈니스 &gt;20K · 송금볼륨 QoQ +30% · 고객당 RLTE Core의 2배+.</li>
  <li><b>Receivers / Borrow·Spend·Save:</b> Receiver 매출 YoY 2배+ · 인접 ARPU.</li>
  <li><b>가이던스:</b> Accelerators FY26 매출 ~<b>5%</b> → 2028 <b>&gt;10%</b>.</li>
</ul>
<div class="easy"><b>쉽게:</b> 지금은 “작은 금액 자주 보내기”가 본체고,
큰손·사업자·수취인 서비스가 <b>옆가지</b>로 붙는 중. 옆가지가 아직 5%라 스토리는 Core 성장이 먼저다.</div>

<h2>3. 가이던스 · 시나리오</h2>
{fig_block(charts['06'], '매출 아웃룩')}
{fig_block(charts['07'], '주가 시나리오')}
<table>
  <tr><th>구간</th><th>가이던스</th><th>메모</th></tr>
  <tr><td>Q2'26</td><td>매출 $483–485M (+17–18%)</td><td>라마단·부활절 타이밍 · 지정학 비교 역풍</td></tr>
  <tr><td>FY26</td><td>매출 $1.960–1.975B (+20–21%)</td><td>하반기 가속 가정</td></tr>
  <tr><td>FY26</td><td>Adj.EBITDA $370–385M</td><td>레버리지 지속</td></tr>
</table>

<h2>4. 촉매 · 포트 실행</h2>
{fig_block(charts['08'], '촉매')}
{fig_block(charts['09'], '포지션 맵')}
<div class="box">
<b>계좌 기준 실행</b><br/>
· 역할: <b>위성 워치 1순위</b> (코어 아님) · 사이즈 ≤~$70 · 동시 신규 1종<br/>
· 트리거: <b>08-05 실적·가이던스 소화 후</b> TA 밴드 $22.69–23.39 재진입<br/>
· 금지: 실적 전 추격 · 물타기 · ROKU식 고가 1주 코어화<br/>
· 손절 감각: TA stop ~$21.41 · 이탈 시 정리
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>디지털 송금 수수료+FX</u> 본체에 Accelerators가 붙는 형태.
품질(성장+흑자전환 레버리지)은 양호. <b>지금은 EARN_D5·관망</b>, 소화 후 눌림만 위성.</div>

<h2>부록 · 출처</h2>
<p class="small">
Remitly Q1 2026 earnings release / shareholder materials (2026-05-06) ·
Form 10-Q geography &amp; segment note · VMR digital remittance share estimates ·
yfinance TTM·가격·PT ({ASOF}). 시나리오는 예시 밴드(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 RELY · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_geo_mix(),
        "03": chart_unit_econ(),
        "04": chart_growth_engines(),
        "05": chart_pnl_stack(),
        "06": chart_outlook(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("RELY", CHART_DIR)
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
