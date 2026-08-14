#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(IART) — Integra Specialty Surgery + Tissue Reconstruction + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-08-14"
PX = 18.24
PT = 19.56
H52 = 20.49
UPSIDE = PT / PX - 1.0
EARN = "07-29"  # Q2'26 reported
OUT_PDF = [
    Path("/opt/cursor/artifacts/IART_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/IART_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/IART_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/IART_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/iart")
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
    "ss": "#0e7490",
    "tr": "#c2410c",
    "slate": "#334155",
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
        (0.1, 0.7, 1.7, 1.6, "병원·\n수술실", C["sand"]),
        (2.0, 0.7, 1.8, 1.6, "Specialty\nSurgery\n신경·기구·ENT", C["ss"]),
        (4.0, 0.7, 1.8, 1.6, "Tissue\nReconstruction\n상처·PL", C["tr"]),
        (6.0, 0.7, 1.7, 1.6, "품질·\n공급망\nBraintree", C["navy"]),
        (7.9, 0.7, 1.8, 1.6, "매출·\nAdj.EBITDA", C["teal"]),
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
                fontproperties=PROP_B, fontsize=8, color=tc)
    ax.set_title("비즈니스 한눈에 — 신경외과·조직재건 메드텍",
                 fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [73.9, 26.1]
    labels = ["Specialty\nSurgery ~74%", "Tissue\nReconstruction ~26%"]
    ax.pie(
        sizes, labels=labels,
        colors=[C["ss"], C["tr"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.5),
    )
    ax.set_title("세그먼트 믹스 (Q2'26)", fontproperties=PROP_B, fontsize=10)

    ax = axes[1]
    labels_q = ["Q3'25", "Q4'25", "Q1'26", "Q2'26"]
    revs = [402.1, 434.9, 391.9, 418.8]
    ax.bar(labels_q, revs, color=[C["sand"], C["sand"], C["navy"], C["teal"]])
    ax.set_ylabel("매출 ($M)", fontproperties=PROP)
    ax.set_title("분기 매출 ($M)", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(revs):
        ax.text(i, v + 5, f"{v:.0f}", ha="center", fontsize=8, fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_ss_detail() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    cats = ["Neurosurgery", "Instruments", "ENT", "Wound Recon", "Private Label"]
    vals = [213.3, 54.8, 41.2, 81.3, 28.2]
    colors = [C["ss"], C["ss"], C["ss"], C["tr"], C["tr"]]
    ax.barh(cats[::-1], vals[::-1], color=colors[::-1])
    ax.set_xlabel("$M", fontproperties=PROP)
    ax.set_title("Q2'26 세부 매출 ($M)", fontproperties=PROP_B, fontsize=12)
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 2, i, f"{v:.0f}", va="center", fontsize=8, fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "04_detail.png")


def chart_margin_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    labels = ["매출", "COGS", "총이익", "영업비+", "영업이익", "이자·기타", "GAAP NI"]
    # Q2: Rev 418.8, GP 219.7, OpInc 19.3, NI 4.5
    vals = [418.8, -199.1, 219.7, -200.4, 19.3, -14.8, 4.5]
    colors = [C["teal"], C["red"], C["ss"], C["tr"], C["green"], C["red"], C["green"]]
    ax.bar(labels, vals, color=colors)
    ax.axhline(0, color=C["ink"], lw=0.8)
    ax.set_title("Q2'26 손익 브리지 ($M) — GAAP 소폭 흑자", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("$M", fontproperties=PROP)
    for i, v in enumerate(vals):
        label = f"+{v:.0f}" if v >= 0 else f"-{abs(v):.0f}"
        ax.text(i, v + (8 if v >= 0 else -18), label, ha="center",
                fontsize=8, fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "03_margin_bridge.png")


def chart_guide() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.4))
    ax = axes[0]
    ax.barh(["FY26 Rev"], [1695 - 1654], left=[1654], height=0.4, color=C["teal"])
    ax.text(1674.5, 0, "$1.654–1.695B", ha="center", va="center",
            fontproperties=PROP_B, fontsize=10, color="white")
    ax.set_title("매출 가이던스 (FX로 소폭 하향)", fontproperties=PROP_B, fontsize=11)
    ax.set_xlabel("$M", fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    ax.barh(["FY26 Adj EPS"], [2.50 - 2.40], left=[2.40], height=0.4, color=C["navy"])
    ax.text(2.45, 0, "$2.40–2.50", ha="center", va="center",
            fontproperties=PROP_B, fontsize=10, color="white")
    ax.set_title("Adj. EPS (재확인)", fontproperties=PROP_B, fontsize=11)
    ax.set_xlabel("$", fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "05_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 10, 14, C["red"]),
        ("Base", 16, 21, C["teal"]),
        ("Bull", 22, 28, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}–{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"현재 ${PX:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT평균 ${PT:.1f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 — SurgiMend·공급 회복 vs 부채·성장 둔화", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(8, 30)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, "SS", "안정", "신경·기구 +\nENT 약세", C["ss"]),
        (0.28, "SurgiMend", "촉매", "Braintree 생산\nQ4 재런칭", C["teal"]),
        (0.52, "마진", "개선", "Adj.EBITDA\n18.7%", C["navy"]),
        (0.76, "부채", "리스크", "순부채 $1.6B\n레버리지 4.1x", C["red"]),
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
    ax.set_title("촉매 — 공급·SurgiMend vs 레버리지·저성장", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "워치·SOFT\n미보유", C["teal"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "위성 후보\n≤10% 소액", C["navy"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", "A′ 재스캔\nSurgiMend 확인", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "유기성장 ~0–3% · 부채 4.1x · PT 업사이드 얇음", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "Adj.EPS↑ · GM 개선 · Braintree 가동", C["ss"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.35, body, ha="center", va="center",
                fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title("실행 포지션 맵 (심층 8/14 · IART SOFT · 미보유)", fontproperties=PROP_B, fontsize=12, pad=4)
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
<div class="easy"><b>쉽게:</b> IART는 <b>중형 신경·조직재건 메드텍</b>이다.
MDT·SYK 대비 스케일은 작고, 피어셋 점유는 <b>+0.3pp</b> 추정 — 회복 스토리이지 점유 폭등 아님.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> 공시는 <b>Specialty Surgery(~74%)</b>와 <b>Tissue Reconstruction(~26%)</b>.
신경·기구는 성장, 상처재건은 아직 약세 — SurgiMend 재런칭이 Tissue 쪽 열쇠.</div>
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
      @bottom-center {{ content:"IART 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0f766e; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #14b8a6; padding-bottom:3px; color:#0f766e; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#1e3a5f; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ecfeff 0%,#f0fdfa 55%,#e0f2fe 100%);
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
    .easy {{ background:#f0fdfa; border-left:4px solid #0f766e; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#0f766e; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0e7490; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#0f766e; }}
    .kpi .s {{ font-size:7.5pt; color:#0e7490; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>IART 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>IART 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Integra LifeSciences · Specialty Surgery + Tissue Reconstruction</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적({EARN} 발표) · 시총 ~$1.4B · ${PX:.2f}</p>
  <div style="margin-top:22px">
    <span class="tag">SS ~74% / TR ~26%</span>
    <span class="tag good">Adj.EPS $0.56</span>
    <span class="tag warn">유기 +0.7%</span>
    <span class="tag bad">레버리지 4.1x</span>
    <span class="tag">SOFT 워치</span>
  </div>
  <div style="margin-top:28px">
    <div class="kpi"><div class="l">Q2 매출</div><div class="v">$419M</div><div class="s">YoY +0.8%</div></div>
    <div class="kpi"><div class="l">Adj.EBITDA</div><div class="v">$78.4M</div><div class="s">18.7%</div></div>
    <div class="kpi"><div class="l">Adj. EPS</div><div class="v">$0.56</div><div class="s">vs $0.45</div></div>
    <div class="kpi"><div class="l">업사이드</div><div class="v">{UPSIDE*100:+.1f}%</div><div class="s">PT ${PT:.1f}</div></div>
  </div>
  <p class="small" style="margin-top:36px;max-width:520px;margin-left:auto;margin-right:auto">
    신경외과·기구·ENT(Specialty)와 상처·프라이빗라벨(Tissue). 공급·품질 정상화와 Braintree·SurgiMend이 핵심 촉매.
    성장은 낮고 부채는 높다 — 마진·EPS 개선이 주가 지지축.
  </p>
</section>

<h2>0. 한줄 결론</h2>
<div class="box">
<b>저성장 회복주 — 마진·공급 스토리, 업사이드는 얇다.</b>
Q2 매출 $419M(+0.8%/유기 +0.7%) · Adj.EPS $0.56 · Adj.EBITDA 마진 18.7%.
Tissue −1.9%·레버리지 4.1x·PT 업사이드 ~{UPSIDE*100:.0f}%가 제약.
포트: <b>미보유 · SOFT 워치</b> — SurgiMend Q4 가시화·레버리지 개선 전 추격 비추.
</div>

<h2>1. 비즈니스 구조</h2>
<div class="easy"><b>쉽게:</b> 뇌·신경·ENT 수술 도구·이식재(Specialty)와 상처·조직재건(Tissue)을 병원에 판다.
2026초 세그먼트명만 바뀌었고(구 Codman CSS / Tissue Technologies), 제품 브랜드는 동일.</div>
{fig_block(charts['flow'], '병원 → SS/TR → 공급망 → 매출')}
{gloss([
    ("Specialty Surgery", "신경외과·Instruments·ENT — Q2 ~$309M"),
    ("Tissue Reconstruction", "상처재건·Private Label — Q2 ~$110M"),
    ("SurgiMend", "조직재건 제품. Braintree 생산 후 Q4'26 재런칭 계획"),
])}

{compete_html}

<h2>2. 매출·마진 (Q2'26)</h2>
<div class="easy"><b>쉽게:</b> 전체는 거의 flat(+0.8%). Specialty는 소폭 성장, Tissue는 감소.
조정 이익은 늘었고 GAAP도 소폭 흑자 전환(전년 대형 손상 대비).</div>
{fig_block(charts['mix'], '세그먼트 믹스 + 분기 매출')}
{fig_block(charts['detail'], '세부 매출')}
{fig_block(charts['bridge'], '손익 브리지')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>Q2'25</th><th>메모</th></tr>
  <tr><td>매출</td><td>$418.8M</td><td>$415.6M</td><td>+0.8% · 유기 +0.7%</td></tr>
  <tr><td>Specialty Surgery</td><td>$309.3M</td><td>$304.0M</td><td>+1.7%</td></tr>
  <tr><td>Tissue Reconstruction</td><td>$109.5M</td><td>$111.6M</td><td>−1.9%</td></tr>
  <tr><td>Adj. EBITDA</td><td>$78.4M</td><td>$71.2M</td><td>마진 18.7%</td></tr>
  <tr><td>Adj. EPS</td><td>$0.56</td><td>$0.45</td><td>개선</td></tr>
  <tr><td>GAAP EPS</td><td>$0.06</td><td>$(6.31)*</td><td>*전기 대형 손상</td></tr>
  <tr><td>영업CF</td><td>$22.8M</td><td>—</td><td>순부채 $1.6B · 4.1x</td></tr>
</table>
{gloss([
    ("유기성장", "환율·인수·매각 제외 성장"),
    ("Braintree", "제조시설. 가동 시작 → SurgiMend 재공급 경로"),
])}

<h2>3. 가이던스 · 촉매</h2>
{fig_block(charts['guide'], 'FY26 가이던스')}
<div class="easy"><b>쉽게:</b> 보고 매출 가이던스는 달러 강세로 $1.654–1.695B로 살짝 낮췄고,
유기성장 0.8–3.3%·Adj.EPS $2.40–2.50은 유지. Q4 SurgiMend이 Tissue 반등 열쇠.</div>
{fig_block(charts['cat'], '촉매 카드')}

<h2>4. 시나리오</h2>
{fig_block(charts['scen'], '주가 시나리오 밴드')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$10–14</td><td>SurgiMend 지연 · Tissue 추가 약세 · 레버리지·리파이낸스 압박</td></tr>
  <tr><td>Base</td><td>$16–21</td><td>가이던스 달성 · Q4 재런칭 · 레버리지 완만 하락</td></tr>
  <tr><td>Bull</td><td>$22–28</td><td>Tissue 반등 · 유기 성장 상단 · 멀티플 회복</td></tr>
</table>

<h2>5. 포트 실행</h2>
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (8/14)</b><br/>
미보유 · 심층 SOFT. PT 업사이드 ~{UPSIDE*100:+.0f}%로 얇음 · 52주 고점 ${H52:.2f} 근접권.<br/>
실행: <b>추격 금지</b> · A′/포폴 3레이어 + Surg·현금여유 확인 후에만 극소.<br/>
품질 게이트: Surg ≤4x 궤적 · Tissue YoY 개선 · SurgiMend 일정 유지.
</div>

<p class="small">생성: 수익구조분석() · 티커 IART · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart<br/>
출처: Integra Q2'26 earnings (2026-07-29) · yfinance · 피어 점유/믹스는 방향 비교용 추정</p>
</body></html>
"""


def main() -> int:
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "bridge": chart_margin_bridge(),
        "detail": chart_ss_detail(),
        "guide": chart_guide(),
        "scen": chart_scenarios(),
        "cat": chart_catalysts(),
        "pos": chart_position(),
    }
    bundle, cpaths = build_compete_charts("IART", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("IART", CHART_DIR, html_doc)
    OUT_HTML.write_text(html_doc, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    pdf = HTML(filename=str(OUT_HTML)).write_pdf()
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf)
        print(f"PDF {p} {p.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
