#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(FTRE) — Fortrea CRO Clinical Services + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-08-04"
PX = 18.94
PT = 20.55
H52 = 21.39
UPSIDE = PT / PX - 1.0
EARN = "07-29"  # Q2'26 reported
OUT_PDF = [
    Path("/opt/cursor/artifacts/FTRE_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/FTRE_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/FTRE_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/FTRE_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/ftre")
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
    "slate": "#334155",
    "clin": "#0e7490",
    "fsp": "#c2410c",
    "pharm": "#7c3aed",
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
        (0.1, 0.7, 1.85, 1.6, "바이오·제약\n고객 의뢰", C["sand"]),
        (2.15, 0.7, 1.75, 1.6, "Phase I–IV\n임상설계", C["clin"]),
        (4.1, 0.7, 1.75, 1.6, "사이트·\n환자모집", C["teal"]),
        (6.05, 0.7, 1.7, 1.6, "데이터·\n모니터링", C["navy"]),
        (7.95, 0.7, 1.75, 1.6, "매출·\n백로그", C["teal2"]),
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
    ax.set_title("비즈니스 한눈에 — 임상시험을 대신 돌려 주는 CRO",
                 fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [72, 18, 10]
    labels = [
        "Full-service/\nHybrid ~72%",
        "FSP ~18%",
        "ClinPharm/\nOther ~10%",
    ]
    ax.pie(
        sizes, labels=labels,
        colors=[C["clin"], C["fsp"], C["pharm"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.5),
    )
    ax.set_title("전달모델 근사 (단일 Clinical Services)", fontproperties=PROP_B, fontsize=10)

    ax = axes[1]
    labels_q = ["Q2'25", "Q3'25", "Q4'25", "Q1'26", "Q2'26"]
    revs = [710.3, 701.3, 660.5, 636.5, 678.2]
    ax.bar(labels_q, revs, color=[C["sand"], C["sand"], C["sand"], C["navy"], C["teal"]])
    ax.set_ylabel("매출 ($M)", fontproperties=PROP)
    ax.set_title("분기 매출 ($M)", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(revs):
        ax.text(i, v + 8, f"{v:.0f}", ha="center", fontsize=8, fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_margin_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    labels = ["매출", "직접비", "총이익", "SG&A+", "영업이익", "이자 등", "순손실"]
    # Q2'26: Rev 678.2, COGS 539, GP 139.2, OpInc 14.8, NI -13.2
    vals = [678.2, -539.0, 139.2, -124.4, 14.8, -28.0, -13.2]
    colors = [C["teal"], C["red"], C["clin"], C["fsp"], C["green"], C["red"], C["red"]]
    ax.bar(labels, vals, color=colors)
    ax.axhline(0, color=C["ink"], lw=0.8)
    ax.set_title("Q2'26 손익 브리지 ($M) — 영업흑자·이자로 순손실", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("$M", fontproperties=PROP)
    for i, v in enumerate(vals):
        label = f"+{v:.0f}" if v >= 0 else f"-{abs(v):.0f}"
        ax.text(i, v + (6 if v >= 0 else -14), label, ha="center",
                fontsize=8, fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "03_margin_bridge.png")


def chart_backlog_btb() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
    ax = axes[0]
    ax.bar(["Backlog\n6/30/26"], [7.8], color=C["teal"], width=0.45)
    ax.set_ylabel("$B", fontproperties=PROP)
    ax.set_title("백로그 $7.8B", fontproperties=PROP_B, fontsize=11)
    ax.text(0, 7.95, "$7.8B", ha="center", fontproperties=PROP_B, fontsize=11, color=C["teal"])
    ax.set_ylim(0, 9.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    ax.bar(["Q2 B2B", "TTM B2B"], [1.06, 1.12], color=[C["clin"], C["navy"]], width=0.5)
    ax.axhline(1.0, color=C["gold"], ls="--", lw=1.2)
    ax.text(1.35, 1.02, "1.0x", fontsize=8, color=C["gold"], fontproperties=PROP)
    ax.set_ylim(0.8, 1.25)
    ax.set_title("Book-to-Bill (4분기 연속 >1.0x)", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate([1.06, 1.12]):
        ax.text(i, v + 0.015, f"{v:.2f}x", ha="center", fontproperties=PROP_B, fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "04_backlog_btb.png")


def chart_guide() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    cats = ["FY26 매출\n가이던스", "FY26 Adj.\nEBITDA"]
    lo = [2620, 205]
    hi = [2690, 220]
    ax.barh(cats, [h - l for l, h in zip(lo, hi)], left=lo, height=0.45,
            color=[C["teal"], C["navy"]], alpha=0.9)
    for i, (l, h) in enumerate(zip(lo, hi)):
        ax.text((l + h) / 2, i, f"${l}–{h}M", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.set_title("FY26 가이던스 상향 (Q2 후)", fontproperties=PROP_B, fontsize=12)
    ax.set_xlabel("$M", fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "05_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 10, 14, C["red"]),
        ("Base", 16, 22, C["teal"]),
        ("Bull", 24, 30, C["green"]),
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
    ax.set_title("시나리오 — B2B·마진 회복 vs 바이오캡ex·부채", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(8, 32)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, "B2B", "수주", "TTM 1.12x\n4분기>1.0", C["teal"]),
        (0.28, "가이던스", "상향", "매출·EBITDA\nFY26↑", C["navy"]),
        (0.52, "FSP", "약점", "FSP 수요↓\n유기 −4.9%", C["fsp"]),
        (0.76, "부채", "리스크", "이자~$19M/Q\n순손실", C["red"]),
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
    ax.set_title("촉매 — 수주 회복 vs FSP·이자 부담", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "워치·SOFT\n미보유", C["teal"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "위성 후보\n≤10% 소액", C["navy"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", "A′ 재스캔\n마진·B2B 확인", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "매출 YoY↓ · 이자·순손실 · 고점권·과열주의", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "B2B>1 · 가이던스↑ · Adj.EBITDA 개선", C["clin"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.35, body, ha="center", va="center",
                fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title("실행 포지션 맵 (심층 8/4 · FTRE SOFT · 미보유)", fontproperties=PROP_B, fontsize=12, pad=4)
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
<div class="easy"><b>쉽게:</b> FTRE는 Labcorp에서 분리된 <b>중형 CRO</b>다.
IQV·ICLR 대비 스케일은 작고, 점유 Δ는 <b>소폭 하락(−0.2pp)</b> 추정 — 수주(B2B) 회복과 별개로 피어 대비 점유는 아직 챌린저.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> 공시 세그먼트는 <b>Clinical Services 하나</b>다.
비교를 위해 Full-service / FSP / ClinPharm으로 나눴다. FSP 약세·ClinPharm 상쇄가 Q2 스토리.</div>
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
      @bottom-center {{ content:"FTRE 수익구조분석 {ASOF} — " counter(page);
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
<html lang="ko"><head><meta charset="utf-8"/><title>FTRE 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>FTRE 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Fortrea Holdings · 글로벌 CRO (Clinical Services)</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적({EARN} 발표) · 시총 ~$1.8B · ${PX:.2f}</p>
  <div style="margin-top:22px">
    <span class="tag">단일 세그먼트</span>
    <span class="tag good">B2B 1.06x / TTM 1.12x</span>
    <span class="tag warn">매출 YoY −4.5%</span>
    <span class="tag bad">GAAP 순손실</span>
    <span class="tag">SOFT 워치</span>
  </div>
  <div style="margin-top:28px">
    <div class="kpi"><div class="l">Q2 매출</div><div class="v">$678M</div><div class="s">YoY −4.5%</div></div>
    <div class="kpi"><div class="l">Adj.EBITDA</div><div class="v">$58.7M</div><div class="s">YoY ↑</div></div>
    <div class="kpi"><div class="l">Backlog</div><div class="v">$7.8B</div><div class="s">6/30</div></div>
    <div class="kpi"><div class="l">업사이드</div><div class="v">{UPSIDE*100:+.1f}%</div><div class="s">PT ${PT:.1f}</div></div>
  </div>
  <p class="small" style="margin-top:36px;max-width:520px;margin-left:auto;margin-right:auto">
    Labcorp 임상사업 스핀(2023) 이후 중형 CRO. 수주(B2B)는 4분기 연속 1.0x 상회·가이던스 상향이나,
    매출은 FSP·패스스루 약세로 아직 YoY 감소. 이자 부담으로 GAAP는 적자.
  </p>
</section>

<h2>0. 한줄 결론</h2>
<div class="box">
<b>수주는 회복, 매출·GAAP는 아직 회복 중.</b>
Q2'26 B2B 1.06x·TTM 1.12x·FY26 가이던스 상향은 플러스.
다만 매출 −4.5%(유기 −4.9%, FSP↓) · 순손실 · 부채·이자가 발목을 잡는다.
포트: <b>미보유 · SOFT 워치</b> — A′ 재통과·마진 가시화 전 추격 비추.
</div>

<h2>1. 비즈니스 구조</h2>
<div class="easy"><b>쉽게:</b> 약이 나오려면 사람 대상 임상시험이 필요하다.
Fortrea는 그 시험의 <b>설계·사이트·데이터</b>를 제약·바이오 대신 수행하고 수수료를 받는다 (CRO).</div>
{fig_block(charts['flow'], '고객 → 임상 → 백로그 → 매출')}
{gloss([
    ("CRO", "Contract Research Organization — 임상·개발 아웃소싱 기업"),
    ("Phase I–IV", "임상 단계. I=안전, II–III=유효성, IV=시판 후"),
    ("백로그", "수주잔고. 미래 매출 후보이나 취소·지연 가능"),
])}

{compete_html}

<h2>2. 매출·마진 (Q2'26)</h2>
<div class="easy"><b>쉽게:</b> 매출 $678M은 작년 동기보다 줄었지만,
조정 EBITDA는 늘었다. 영업은 흑자($14.8M)인데 <b>이자(~$19M)</b> 때문에 순손실.</div>
{fig_block(charts['mix'], '전달모델 근사 + 분기 매출')}
{fig_block(charts['bridge'], '손익 브리지')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>Q2'25</th><th>메모</th></tr>
  <tr><td>매출</td><td>$678.2M</td><td>$710.3M</td><td>−4.5% · 유기 −4.9%</td></tr>
  <tr><td>Adj. EBITDA</td><td>$58.7M</td><td>$54.9M</td><td>개선</td></tr>
  <tr><td>Adj. EPS</td><td>$0.23</td><td>$0.19</td><td>개선</td></tr>
  <tr><td>GAAP EPS</td><td>$(0.14)</td><td>$(4.14)*</td><td>*전기 영업권손상 포함</td></tr>
  <tr><td>영업CF</td><td>$28.9M</td><td>—</td><td>FCF $19.9M</td></tr>
</table>
{gloss([
    ("FSP", "Functional Service Provider — 인력·기능 단위 아웃소싱. Q2 수요 약세"),
    ("Pass-through", "고객 대신 지출 후 전가. 줄면 매출도 줄지만 마진 영향은 제한적"),
    ("Adj. EBITDA", "일회성·비현금 제외 영업현금창출력 근사"),
])}

<h2>3. 수주 · 가이던스</h2>
{fig_block(charts['btb'], '백로그·Book-to-Bill')}
{fig_block(charts['guide'], 'FY26 가이던스')}
<div class="easy"><b>쉽게:</b> Book-to-Bill &gt;1이면 새로 따는 일(수주)이 이번 분기 매출보다 많다.
4분기 연속 &gt;1.0x + 가이던스 상향은 “일은 들어오고 있다”는 신호.</div>
{gloss([
    ("Book-to-Bill", "순수주 / 매출. 1.0 초과면 백로그 증가 방향"),
    ("Net new business", "Q2 ~$720M — 취소 반영 후 순수주"),
])}

<h2>4. 시나리오 · 촉매</h2>
{fig_block(charts['scen'], '주가 시나리오 밴드')}
{fig_block(charts['cat'], '촉매 카드')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$10–14</td><td>바이오캡ex 재둔화 · B2B&lt;1 · 이자·리파이낸스 압박</td></tr>
  <tr><td>Base</td><td>$16–22</td><td>가이던스 달성 · B2B≥1 · 마진 완만 회복</td></tr>
  <tr><td>Bull</td><td>$24–30</td><td>매출 턴어라운드 · FSP 안정 · 순이익 흑자 전환</td></tr>
</table>

<h2>5. 포트 실행</h2>
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (8/4)</b><br/>
미보유 · 심층 SOFT. 업사이드 ~+8% · 고점 −11%대 · Chase 중·과열주의.<br/>
실행: <b>추격 금지</b> · A′/포폴 3레이어 통과 + 위성한도·현금여유 확인 후에만 극소.<br/>
품질 게이트: 다음 분기에도 B2B&gt;1 · 매출 YoY 개선 · Adj.EBITDA 가이던스 궤적.
</div>

<p class="small">생성: 수익구조분석() · 티커 FTRE · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart<br/>
출처: Fortrea Q2'26 earnings release (2026-07-29) · yfinance · 피어 점유/믹스는 방향 비교용 추정</p>
</body></html>
"""


def main() -> int:
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "bridge": chart_margin_bridge(),
        "btb": chart_backlog_btb(),
        "guide": chart_guide(),
        "scen": chart_scenarios(),
        "cat": chart_catalysts(),
        "pos": chart_position(),
    }
    bundle, cpaths = build_compete_charts("FTRE", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("FTRE", CHART_DIR, html_doc)
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
