#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(NSIT) — Insight Enterprises Hardware/Software/Services + 경쟁점유/믹스 + WeasyPrint PDF.

공식 SSOT: data/rev_filings/NSIT/NSIT_10Q_2026-06-30.pdf (Form 10-Q, period ended Jun 30, 2026)
"""

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
ASOF = "2026-09-22"
PX = 154.42
PT = 163.75
H52 = 168.50
L52 = 63.62
UPSIDE = PT / PX - 1.0
EARN = "Q2'26 (10-Q 2026-06-30)"
FILING = "data/rev_filings/NSIT/NSIT_10Q_2026-06-30.pdf"

# Q2'26 ($ millions) from 10-Q note / statements
HW_Q2, SW_Q2, SVC_Q2, TOT_Q2 = 1438.285, 447.324, 513.888, 2399.497
HW_Y25, SW_Y25, SVC_Y25, TOT_Y25 = 1191.031, 474.259, 426.192, 2091.482
HW_GP, SW_GP, SVC_GP, TOT_GP = 169.382, 23.987, 328.233, 521.602
EFO_Q2, EFO_Y25 = 130.967, 86.532
NI_Q2, EPS_Q2, EPS_Y25 = 77.569, 2.57, 1.46
NA_Q2, EMEA_Q2, APAC_Q2 = 1938.663, 375.194, 85.640
ENT_Q2, COMM_Q2, PUB_Q2 = 1648.761, 453.501, 297.235

OUT_PDF = [
    Path("/opt/cursor/artifacts/NSIT_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/NSIT_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/NSIT_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/NSIT_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/nsit")
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
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "slate": "#334155",
    "hw": "#0369a1",
    "sw": "#7c3aed",
    "svc": "#0f766e",
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
        (0.1, 0.7, 1.7, 1.6, "기업·공공\n클라이언트", C["sand"]),
        (2.0, 0.7, 1.75, 1.6, "Hardware\n리셀", C["hw"]),
        (3.95, 0.7, 1.75, 1.6, "Software\n라이선스", C["sw"]),
        (5.9, 0.7, 1.8, 1.6, "Services\n·Cloud", C["svc"]),
        (7.9, 0.7, 1.85, 1.6, "솔루션\n통합 마진", C["navy"]),
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
    for x in (1.9, 3.85, 5.8, 7.8):
        ax.annotate(
            "", xy=(x + 0.08, 1.5), xytext=(x - 0.08, 1.5),
            arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6),
        )
    ax.set_title("비즈니스 한눈에 — 하드웨어·소프트웨어 유통 + 서비스/클라우드 마진",
                 fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [HW_Q2, SW_Q2, SVC_Q2]
    labels = [
        f"Hardware\n${HW_Q2:.0f}M ({HW_Q2/TOT_Q2*100:.0f}%)",
        f"Software\n${SW_Q2:.0f}M ({SW_Q2/TOT_Q2*100:.0f}%)",
        f"Services\n${SVC_Q2:.0f}M ({SVC_Q2/TOT_Q2*100:.0f}%)",
    ]
    ax.pie(
        sizes, labels=labels,
        colors=[C["hw"], C["sw"], C["svc"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=7.5),
    )
    ax.set_title(f"매출 유형 (Q2'26, 총 ${TOT_Q2/1000:.2f}B)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["Hardware", "Software", "Services"]
    vals = [HW_Q2, SW_Q2, SVC_Q2]
    prior = [HW_Y25, SW_Y25, SVC_Y25]
    x = range(len(cats))
    w = 0.36
    ax.bar([i - w / 2 for i in x], prior, width=w, color="#94a3b8", label="Q2'25")
    ax.bar([i + w / 2 for i in x], vals, width=w,
           color=[C["hw"], C["sw"], C["svc"]], label="Q2'26")
    ax.set_xticks(list(x))
    ax.set_xticklabels(cats, fontproperties=PROP)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("오퍼링 YoY", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8)
    for i, (a, b) in enumerate(zip(prior, vals)):
        yoy = (b / a - 1) * 100
        ax.text(i + w / 2, b + 40, f"{yoy:+.0f}%", ha="center", fontproperties=PROP, fontsize=8)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_geo_client() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    geo = [("NA", NA_Q2), ("EMEA", EMEA_Q2), ("APAC", APAC_Q2)]
    ax.bar([g[0] for g in geo], [g[1] for g in geo],
           color=[C["navy"], C["teal"], C["gold"]], width=0.55)
    ax.set_title("지역 매출 (Q2'26)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for i, (_n, v) in enumerate(geo):
        ax.text(i, v + 30, f"{v/TOT_Q2*100:.0f}%", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    cli = [("Large Ent", ENT_Q2), ("Commercial", COMM_Q2), ("Public", PUB_Q2)]
    ax.bar([c[0] for c in cli], [c[1] for c in cli],
           color=[C["teal"], C["hw"], C["sand"]], width=0.55)
    ax.set_title("고객군 매출 (Q2'26)", fontproperties=PROP_B, fontsize=11)
    for i, (_n, v) in enumerate(cli):
        ax.text(i, v + 30, f"{v/TOT_Q2*100:.0f}%", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "03_geo_client.png")


def chart_margin() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    cats = ["Hardware", "Software", "Services", "Total"]
    gms = [
        HW_GP / HW_Q2 * 100,
        SW_GP / SW_Q2 * 100,
        SVC_GP / SVC_Q2 * 100,
        TOT_GP / TOT_Q2 * 100,
    ]
    colors = [C["hw"], C["sw"], C["svc"], C["navy"]]
    bars = ax.bar(cats, gms, color=colors, width=0.55)
    ax.set_ylabel("Gross Margin %", fontproperties=PROP)
    ax.set_title("총이익률 by 오퍼링 (Q2'26)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, gms):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v:.1f}%",
                ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)

    ax = axes[1]
    cats2 = ["Sales\nYoY", "GP\nYoY", "EFO\nYoY", "EPS\nYoY"]
    gp_y25 = 442.327
    vals = [
        (TOT_Q2 / TOT_Y25 - 1) * 100,
        (TOT_GP / gp_y25 - 1) * 100,
        (EFO_Q2 / EFO_Y25 - 1) * 100,
        (EPS_Q2 / EPS_Y25 - 1) * 100,
    ]
    colors2 = [C["green"] if v >= 0 else C["red"] for v in vals]
    bars = ax.bar(cats2, vals, color=colors2, width=0.55)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_title("성장·수익성 브리지 (Q2'26 YoY)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("%", fontproperties=PROP)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (2 if v >= 0 else -4),
                f"{v:+.0f}%", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "04_margin.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    rows = [
        (0.3, 2.6, "Bear", "$110–130", "HW 둔화 · SW 에이전트 매출 추가 약화 · 마진 수축", C["red"]),
        (0.3, 1.45, "Base", "$145–170", "HW/Svc 중기 성장 · GM~22% · 가이던스 궤적", C["teal"]),
        (0.3, 0.3, "Bull", "$180–210", "서비스·클라우드 가속 · 마진 +100bps · 멀티플 재평가", C["green"]),
    ]
    for x, y, name, band, note, col in rows:
        ax.add_patch(FancyBboxPatch(
            (x, y), 9.4, 1.0, boxstyle="round,pad=0.02,rounding_size=0.1",
            facecolor=col, alpha=0.12, edgecolor=col, lw=1.5,
        ))
        ax.text(x + 0.25, y + 0.55, name, fontproperties=PROP_B, fontsize=11, color=col, va="center")
        ax.text(x + 1.6, y + 0.55, band, fontproperties=PROP_B, fontsize=11, color=C["ink"], va="center")
        ax.text(x + 4.0, y + 0.55, note, fontproperties=PROP, fontsize=8.5, color=C["muted"], va="center")
    ax.set_title(f"시나리오 밴드 (현재 ~${PX:.0f} · PT ${PT:.0f})",
                 fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "05_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    cards = [
        (0.2, 0.4, 3.0, 2.4, "서비스·클라우드", "GP의 ~63%\n서비스 마진\n지속 확대가 핵심"),
        (3.5, 0.4, 3.0, 2.4, "하드웨어 사이클", "서버·스토리지\n수요 +21% YoY\n지속 여부"),
        (6.8, 0.4, 3.0, 2.4, "소프트웨어 믹스", "에이전트 매출\nSW −6% YoY\n순매출 압력"),
    ]
    cols = [C["svc"], C["hw"], C["sw"]]
    for (x, y, w, h, title, body), col in zip(cards, cols):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
            facecolor="white", edgecolor=col, lw=2,
        ))
        ax.text(x + w / 2, y + h - 0.45, title, ha="center",
                fontproperties=PROP_B, fontsize=10, color=col)
        ax.text(x + w / 2, y + 0.85, body, ha="center", va="center",
                fontproperties=PROP, fontsize=8, color=C["ink"])
    ax.set_title("촉매 · 모니터", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "06_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 2.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch(
        (0.3, 0.4), 9.4, 2.2, boxstyle="round,pad=0.04,rounding_size=0.12",
        facecolor=C["sand"], edgecolor=C["navy"], lw=1.5,
    ))
    ax.text(5, 2.1, "포트 포지션 — 미보유 (워치)",
            ha="center", fontproperties=PROP_B, fontsize=12, color=C["navy"])
    ax.text(
        5, 1.2,
        f"마크 ~${PX:.2f} · PT ${PT:.2f} ({UPSIDE*100:+.0f}%) · 52주 ${L52:.0f}–${H52:.0f}\n"
        "종목천장 20% 정책 · 신규는 본선∩GO·현금여유·Top3 여유 시에만",
        ha="center", va="center", fontproperties=PROP, fontsize=9, color=C["ink"],
    )
    return save_fig(fig, "07_position.png")


def fig_block(path: Path, caption: str) -> str:
    return (
        f'<div class="fig"><img src="data:image/png;base64,{img_b64(path)}"/>'
        f'<div class="cap">{caption}</div></div>'
    )


def gloss(rows: list[tuple[str, str]]) -> str:
    lis = "".join(f"<li><b>{k}</b> — {v}</li>" for k, v in rows)
    return f'<div class="gloss"><b>용어</b><ul>{lis}</ul></div>'


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
<div class="easy"><b>쉽게:</b> Insight는 CDW·Synnex 대비 <b>중형 IT 솔루션 통합사</b>다.
피어셋 스케일 점유 ~14%(+0.5pp) 추정 — 하드웨어 볼륨 + 서비스 마진이 축.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> NSIT Q2'26 믹스는 <b>HW ~60% / SW ~19% / Svc ~21%</b>.
서비스 GP가 총이익의 ~63% — CDW·ePlus 대비 HW 비중은 높고, Synnex·CNXN보다는 서비스가 두껍다.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
"""


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    hw_yoy = (HW_Q2 / HW_Y25 - 1) * 100
    sw_yoy = (SW_Q2 / SW_Y25 - 1) * 100
    svc_yoy = (SVC_Q2 / SVC_Y25 - 1) * 100
    tot_yoy = (TOT_Q2 / TOT_Y25 - 1) * 100
    efo_yoy = (EFO_Q2 / EFO_Y25 - 1) * 100
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/>
<title>수익구조분석 — NSIT (Insight Enterprises)</title>
<style>
@page {{ size: A4; margin: 14mm 12mm; }}
body {{ font-family: 'NanumGothic', sans-serif; color: #1c1917; font-size: 9.5pt; line-height: 1.45; }}
h1 {{ font-size: 18pt; color: #1e3a5f; margin: 0 0 4px; }}
h2 {{ font-size: 12.5pt; color: #0f766e; border-bottom: 2px solid #e8dcc8; padding-bottom: 3px; margin: 16px 0 8px; }}
.sub {{ color: #57534e; font-size: 9pt; margin-bottom: 10px; }}
.hero {{ background: linear-gradient(135deg,#1e3a5f 0%,#0f766e 100%); color: white; padding: 14px 16px; border-radius: 8px; margin-bottom: 12px; }}
.hero b {{ font-size: 13pt; }}
.kpis {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 12px; }}
.kpi {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 10px; min-width: 110px; }}
.kpi .l {{ font-size: 7.5pt; color: #64748b; }}
.kpi .v {{ font-size: 12pt; font-weight: bold; color: #1e3a5f; }}
.fig {{ margin: 8px 0 12px; text-align: center; }}
.fig img {{ max-width: 100%; height: auto; }}
.cap {{ font-size: 8pt; color: #64748b; margin-top: 3px; }}
.easy {{ background: #f0fdfa; border-left: 4px solid #0f766e; padding: 8px 10px; margin: 8px 0; font-size: 9pt; }}
.box {{ background: #fffbeb; border: 1px solid #f59e0b; border-radius: 6px; padding: 10px; margin: 8px 0; }}
table {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; margin: 6px 0 12px; }}
th, td {{ border: 1px solid #e2e8f0; padding: 4px 6px; text-align: left; }}
th {{ background: #1e3a5f; color: white; }}
.gloss {{ font-size: 8pt; color: #57534e; }}
.gloss ul {{ margin: 4px 0; padding-left: 16px; }}
.small {{ font-size: 7.5pt; color: #64748b; }}
.pill {{ display: inline-block; background: #ccfbf1; color: #0f766e; padding: 2px 8px; border-radius: 999px; font-size: 8pt; margin-right: 4px; }}
</style></head><body>

<div class="hero">
  <b>수익구조분석 · NSIT (Insight Enterprises)</b><br/>
  <span style="font-size:9pt">IT 솔루션 통합 · Hardware / Software / Services · 공식 10-Q Q2'26</span>
</div>
<p class="sub">
  <span class="pill">공식공시</span>
  <span class="pill">종목천장 20%</span>
  기준일 {ASOF} · 실적 {EARN} · 마크 ${PX:.2f} · PT ${PT:.2f} ({UPSIDE*100:+.0f}%) · 52주 ${L52:.0f}–${H52:.0f}<br/>
  SSOT: <code>{FILING}</code>
</p>

<div class="kpis">
  <div class="kpi"><div class="l">Q2'26 매출</div><div class="v">${TOT_Q2/1000:.2f}B</div></div>
  <div class="kpi"><div class="l">YoY</div><div class="v">{tot_yoy:+.0f}%</div></div>
  <div class="kpi"><div class="l">총이익률</div><div class="v">{TOT_GP/TOT_Q2*100:.1f}%</div></div>
  <div class="kpi"><div class="l">영업이익</div><div class="v">${EFO_Q2:.0f}M</div></div>
  <div class="kpi"><div class="l">희석 EPS</div><div class="v">${EPS_Q2:.2f}</div></div>
  <div class="kpi"><div class="l">NA 비중</div><div class="v">{NA_Q2/TOT_Q2*100:.0f}%</div></div>
</div>

<h2>1. 비즈니스 구조</h2>
{fig_block(charts['flow'], '가치사슬')}
<div class="easy"><b>쉽게:</b> Insight는 기업·공공에 IT 하드웨어·소프트웨어를 공급하고,
클라우드·매니지드 서비스로 마진을 붙이는 <b>솔루션 통합사</b>다.
매출의 ~60%는 하드웨어(저마진), ~21%는 서비스(고마진) — 성장·마진의 축은 서비스·클라우드.</div>

{compete_html}

<h2>2. 매출 믹스 · YoY</h2>
{fig_block(charts['seg'], '오퍼링 믹스 + YoY')}
{fig_block(charts['geo'], '지역 · 고객군')}
<table>
  <tr><th>오퍼링</th><th>Q2'26</th><th>Q2'25</th><th>YoY</th><th>비중</th><th>GM</th></tr>
  <tr><td>Hardware</td><td>${HW_Q2:,.0f}M</td><td>${HW_Y25:,.0f}M</td><td>{hw_yoy:+.0f}%</td>
      <td>{HW_Q2/TOT_Q2*100:.0f}%</td><td>{HW_GP/HW_Q2*100:.1f}%</td></tr>
  <tr><td>Software</td><td>${SW_Q2:,.0f}M</td><td>${SW_Y25:,.0f}M</td><td>{sw_yoy:+.0f}%</td>
      <td>{SW_Q2/TOT_Q2*100:.0f}%</td><td>{SW_GP/SW_Q2*100:.1f}%</td></tr>
  <tr><td>Services</td><td>${SVC_Q2:,.0f}M</td><td>${SVC_Y25:,.0f}M</td><td>{svc_yoy:+.0f}%</td>
      <td>{SVC_Q2/TOT_Q2*100:.0f}%</td><td>{SVC_GP/SVC_Q2*100:.1f}%</td></tr>
  <tr><td><b>Total</b></td><td><b>${TOT_Q2:,.0f}M</b></td><td>${TOT_Y25:,.0f}M</td>
      <td><b>{tot_yoy:+.0f}%</b></td><td>100%</td><td><b>{TOT_GP/TOT_Q2*100:.1f}%</b></td></tr>
</table>
{gloss([
    ("Hardware", "서버·스토리지·클라이언트·네트워킹 등 제품 리셀 (저마진·볼륨)"),
    ("Software", "라이선스·구독 — 상당 부분은 에이전트 매출(순액)로 인식되어 탑라인 변동"),
    ("Services", "Insight Delivered · 클라우드·컨설팅·매니지드 — 고마진 축"),
])}

<h2>3. 마진 · 손익</h2>
{fig_block(charts['margin'], '총이익률 · 성장 브리지')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>Q2'25</th><th>YoY</th></tr>
  <tr><td>총이익</td><td>${TOT_GP:.0f}M</td><td>$442M</td><td>+{(TOT_GP/442.327-1)*100:.0f}%</td></tr>
  <tr><td>총이익률</td><td>{TOT_GP/TOT_Q2*100:.1f}%</td><td>{442.327/2091.482*100:.1f}%</td><td>+{(TOT_GP/TOT_Q2-442.327/2091.482)*10000:.0f}bps</td></tr>
  <tr><td>영업이익 (EFO)</td><td>${EFO_Q2:.0f}M</td><td>${EFO_Y25:.0f}M</td><td>{efo_yoy:+.0f}%</td></tr>
  <tr><td>순이익</td><td>${NI_Q2:.0f}M</td><td>$46.9M</td><td>+{(NI_Q2/46.932-1)*100:.0f}%</td></tr>
  <tr><td>희석 EPS</td><td>${EPS_Q2:.2f}</td><td>${EPS_Y25:.2f}</td><td>+{((EPS_Q2/EPS_Y25)-1)*100:.0f}%</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 매출 +15%인데 영업이익 +51% — <b>서비스·클라우드 믹스</b>가 마진을 끌어올린 분기.
SW 순매출은 −6%(에이전트 인식)로 줄었으나 GP 스토리는 서비스가 지탱.</div>

<h2>4. 시나리오 · 촉매</h2>
{fig_block(charts['scen'], '주가 시나리오')}
{fig_block(charts['cat'], '촉매 카드')}

<h2>5. 포트 실행</h2>
{fig_block(charts['pos'], '포지션')}
<div class="box">
<b>OS 메모 ({ASOF} · 종목천장 20% 정책)</b><br/>
현재 <b>미보유</b> · 워치. 마크 ~${PX:.2f} · 컨센 PT ${PT:.2f} ({UPSIDE*100:+.0f}%).<br/>
신규 진입 조건: 본선(Chase)∩타이밍 GO · 종목≤20% · Top3≤50% · 현금바닥 $150 여유 · 추격·물타기 금지.<br/>
모니터: 서비스 GP 비중 · HW 사이클 · SW 에이전트 매출 추이 · 다음 실적.
</div>

<h2>0. 한줄 결론</h2>
<div class="box">
<b>매출 +15% · 영업이익 +51% — 서비스·클라우드 믹스가 마진을 끌어올린 분기.</b>
HW +21% / Svc +21% · SW −6%(에이전트 순액). GM 21.7% · EFO $131M · EPS $2.57.
포트: <b>미보유(워치)</b> · 종목천장 20% · 본선∩GO·현금여유 시에만 신규.
</div>

<p class="small">생성: 수익구조분석() · 티커 NSIT · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart<br/>
출처: Insight Enterprises Form 10-Q (period ended Jun 30, 2026) · yfinance · 피어 점유/믹스는 방향 비교용 추정<br/>
투자 권유 아님.</p>
</body></html>
"""


def main() -> int:
    tot_yoy = (TOT_Q2 / TOT_Y25 - 1) * 100
    efo_yoy = (EFO_Q2 / EFO_Y25 - 1) * 100
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "geo": chart_geo_client(),
        "margin": chart_margin(),
        "scen": chart_scenarios(),
        "cat": chart_catalysts(),
        "pos": chart_position(),
    }
    bundle, cpaths = build_compete_charts("NSIT", CHART_DIR)
    # compete mix key collides with segment 'mix' — keep segment under 'seg'
    charts["seg"] = charts["mix"]
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("NSIT", CHART_DIR, html_doc)
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

        tag = "sepa-rev-nsit"
        notes = (
            f"## NSIT 수익구조분석 ({ASOF})\n\n"
            f"Insight Enterprises · Q2'26 10-Q · HW/SW/Services.\n\n"
            f"- 매출 ${TOT_Q2/1000:.2f}B ({tot_yoy:+.0f}% YoY) · GM {TOT_GP/TOT_Q2*100:.1f}% · EFO ${EFO_Q2:.0f}M ({efo_yoy:+.0f}%)\n"
            f"- 믹스: HW {HW_Q2/TOT_Q2*100:.0f}% · SW {SW_Q2/TOT_Q2*100:.0f}% · Svc {SVC_Q2/TOT_Q2*100:.0f}%\n"
            f"- 포트: 미보유(워치) · 종목천장 20% 정책\n"
            f"- 업사이드 {UPSIDE*100:+.1f}% (PT ${PT:.2f} · px ${PX:.2f})\n"
            f"- SSOT: `{FILING}`\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — NSIT",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
