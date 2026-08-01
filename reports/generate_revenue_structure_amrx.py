#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(AMRX) — 제네릭·Specialty·AvKARE + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-08-01"
PX = 18.32
PT = 20.25
H52 = 19.26
UPSIDE = PT / PX - 1.0
EARN = "10-29"  # next; Q2 reported 07-30
OUT_PDF = [
    Path("/opt/cursor/artifacts/AMRX_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/AMRX_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/AMRX_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/AMRX_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/amrx")
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
    "cyan": "#0e7490",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
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
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.1, 0.65, 1.85, 1.55, "복제약\nAffordable\n대량·복잡제형", C["sand"]),
        (2.15, 0.65, 1.85, 1.55, "브랜드\nSpecialty\n신경·내분비", C["gold"]),
        (4.2, 0.65, 1.8, 1.55, "유통\nAvKARE\n정부·기관", C["teal2"]),
        (6.2, 0.65, 1.7, 1.55, "약국·병원\n·VA/DoD", C["teal"]),
        (8.1, 0.65, 1.65, 1.55, "매출\n·마진", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8, color=tc)
    ax.set_title("비즈니스 한눈에 — 싼 복제약 + 브랜드약 + 정부 유통",
                 fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [490.0, 149.3, 157.0]
    labels = ["Affordable\n490M (61.5%)", "Specialty\n149M (18.8%)", "AvKARE\n157M (19.7%)"]
    ax.pie(
        sizes, labels=labels, colors=[C["teal"], C["gold"], C["navy"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.5),
    )
    ax.set_title("세그먼트 매출 (Q2'26, 총 $796M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    # Q1 vs Q2 absolute
    cats = ["Affordable", "Specialty", "AvKARE"]
    q1 = [423.2, 133.3, 166.0]
    q2 = [490.0, 149.3, 157.0]
    x = range(len(cats))
    w = 0.35
    ax.bar([i - w / 2 for i in x], q1, w, label="Q1'26", color=C["sand"])
    ax.bar([i + w / 2 for i in x], q2, w, label="Q2'26", color=C["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(cats, fontproperties=PROP, fontsize=9)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("Q1→Q2 세그먼트 ($M)", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("AMRX 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_growth_yoy() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    cats = ["Affordable\nMedicines", "Specialty", "AvKARE", "연결\n순매출"]
    yoy = [13, 17, -4, 10]
    colors = [C["teal"] if v >= 0 else C["red"] for v in yoy]
    ax.bar(cats, yoy, color=colors, width=0.55)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("Q2'26 세그먼트·연결 성장률 (YoY)", fontproperties=PROP_B, fontsize=12)
    for i, v in enumerate(yoy):
        ax.text(i, v + (1.2 if v >= 0 else -2.8), f"{v:+d}%", ha="center",
                fontproperties=PROP_B, fontsize=10)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "03_growth_yoy.png")


def chart_specialty_drivers() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.3, 0.55, 2.9, 1.9, "CREXONT", "파킨슨\nSpecialty 핵심", C["navy"]),
        (3.5, 0.55, 2.9, 1.9, "BREKIYA", "군발두통\n오토인젝터", C["teal"]),
        (6.7, 0.55, 2.9, 1.9, "UNITHROID", "갑상선\n내분비", C["gold"]),
    ]
    for x, y, w, h, title, body, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c == C["gold"] else "white"
        ax.text(x + w / 2, y + h - 0.45, title, ha="center",
                fontproperties=PROP_B, fontsize=11, color=tc)
        ax.text(x + w / 2, y + 0.55, body, ha="center",
                fontproperties=PROP, fontsize=9, color=tc)
    ax.set_title("Specialty 성장 드라이버 — CREXONT · BREKIYA · UNITHROID",
                 fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "04_specialty_drivers.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26", "Q2'26"]
    rev = [695, 725, 785, 814, 722.5, 796]
    x = range(len(labels))
    colors = [C["teal2"] if i < 4 else (C["sand"] if i == 4 else C["teal"]) for i in x]
    ax.bar(x, rev, color=colors, alpha=0.9, width=0.55)
    for i, v in enumerate(rev):
        ax.text(i, v + 12, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("순매출 ($M)", fontproperties=PROP)
    ax.set_title("분기 추이 — Q2'26 $796M (+10% YoY, +10% QoQ)", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "05_quarterly.png")


def chart_margin_guide() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6))
    ax = axes[0]
    cats = ["Adj GM\nQ2'25", "Adj GM\nQ2'26"]
    vals = [45.6, 46.2]  # +60bps
    ax.bar(cats, vals, color=[C["sand"], C["teal"]], width=0.5)
    ax.set_ylim(40, 50)
    ax.set_ylabel("%", fontproperties=PROP)
    ax.set_title("조정 총이익률 (+60bps YoY)", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.25, f"{v:.1f}%", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    cats2 = ["FY25\n실적", "FY26\n가이던스\n(상향)"]
    vals2 = [3.02, 3.15]  # mid ~3.10–3.20
    ax.bar(cats2, vals2, color=[C["navy"], C["gold"]], width=0.5)
    ax.set_ylim(2.5, 3.5)
    ax.set_ylabel("매출 ($B)", fontproperties=PROP)
    ax.set_title("매출 가이던스 — ~$3.10–3.20B 대", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(vals2):
        ax.text(i, v + 0.04, f"${v:.2f}B", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "06_margin_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 12, 16, C["red"]),
        ("Base", 17, 22, C["teal"]),
        ("Bull", 23, 28, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}–{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"현재 ${PX:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT평균 ${PT:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 — Specialty 가속·믹스가 밴드폭", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(10, 30)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, EARN, "실적", "Q3 Specialty\n·가이던스", C["teal"]),
        (0.28, "Specialty", "성장", "CREXONT\nBREKIYA", C["navy"]),
        (0.52, "마진", "믹스", "Adj GM\n지속 확대", C["gold"]),
        (0.76, "가격", "리스크", "제네릭\n가격전쟁", C["red"]),
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
    ax.set_title(f"촉매 — 다음 실적 {EARN} · Specialty · 마진 · 제네릭 가격",
                 fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "코어 보유\n헬스케어 축", C["teal"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "추가금지\n홀드 관찰", C["navy"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", f"{EARN} 소화 후\n재평가만", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "52주고 근접 · 추격·추가매수 금지 · Chase 중", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "AM+Spec 성장 · Adj GM↑ · 가이던스 상향", C["cyan"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.35, body, ha="center", va="center",
                fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title("실행 포지션 맵 (사용자 계좌 · AMRX 코어 · 추가금지)",
                 fontproperties=PROP_B, fontsize=12, pad=4)
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
<div class="easy"><b>쉽게:</b> AMRX는 <b>복잡 제네릭 + Specialty 브랜드</b>로 Teva/Viatris 대비 스케일은 작지만,
미국 복잡제형·신경/내분비 브랜드에서 점유를 키우는 쪽이다. 절대 글로벌 제네릭 점유가 아님.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> AMRX는 매출의 약 <b>62%가 Affordable(복제약)</b>, Specialty ~19%, AvKARE 유통 ~20%다.
대형 피어는 Specialty 비중이나 OTC/유통 믹스가 다르다.</div>
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
      @bottom-center {{ content:"AMRX 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0f766e; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0e7490; padding-bottom:3px; color:#0f766e; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#1e3a5f; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#f0fdfa 0%,#e0f2fe 55%,#e8dcc8 100%);
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
<html lang="ko"><head><meta charset="utf-8"/><title>AMRX 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>AMRX 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Amneal Pharmaceuticals · 복제약(제네릭) + Specialty 브랜드 + 정부 유통</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적(07-30 발표) · 다음 실적 {EARN} · 시총 ~$5.8B</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.2f}</div><div class="s">52주고 ${H52:.2f}</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.2f}</div><div class="s">{UPSIDE*100:+.1f}%</div></span>
    <span class="kpi"><div class="l">Q2 매출</div><div class="v">$796M</div><div class="s">+10% YoY</div></span>
    <span class="kpi"><div class="l">Adj GM</div><div class="v">~46.2%</div><div class="s">+60bps</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">코어 보유 · Chase 중·추가금지</span>
    <span class="tag">AM ~61.5%</span>
    <span class="tag">Specialty +17%</span>
    <span class="tag warn">다음 실적 {EARN}</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>Affordable(복잡 제네릭) 본체 + Specialty(CREXONT·BREKIYA·UNITHROID) 가속 + AvKARE 저마진 정리.</b>
Q2'26 순매출 <b>$796M</b>(+10% YoY) · AM $490M(+13%) · Spec $149.3M(+17%) · AvKARE $157M(−4%).
Adj 총이익률 ~<b>46.2%</b>(+60bps). FY26 가이던스 상향·Specialty/AM 성장(콜에서 매출 전망 +~$50M 언급 · ~$3.10–3.20B 대).
주가 ~${PX:.2f} vs PT ${PT:.2f}({UPSIDE*100:+.0f}%) · 52주고 ${H52:.2f} 근접 —
당신 계좌는 <b>코어 보유·추가금지</b>(Chase 중·보유·추가금지).</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 약국에 값싼 복제약을 많이 팔고(Affordable),
파킨슨·두통·갑상선 같은 <b>브랜드약</b>으로 마진을 올리고,
정부·기관 유통(AvKARE)은 저마진 부분을 줄이는 회사다.</div>
{gloss([
    ("Affordable Medicines", "리테일·주사·바이오시밀러 등 복제약 세그먼트 — 매출 본체(~62%)."),
    ("Specialty", "브랜드 처방약 — CREXONT·BREKIYA·UNITHROID 등."),
    ("AvKARE", "연방·보훈·기관·소매 유통 세그먼트."),
    ("Adj GM", "조정 총이익률 — 일회성·비현금 항목 조정 후."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '세그먼트 믹스')}
{fig_block(charts['03'], 'YoY 성장')}
{fig_block(charts['04'], 'Specialty 드라이버')}
<table>
  <tr><th>세그먼트 (Q2'26)</th><th>매출</th><th>비중</th><th>YoY</th><th>내용</th></tr>
  <tr><td><b>Affordable Medicines</b></td><td>$490M</td><td>~61.5%</td><td>+13%</td><td>복잡 제네릭·주사·바이오시밀러</td></tr>
  <tr><td>Specialty</td><td>$149.3M</td><td>~18.8%</td><td>+17%</td><td>CREXONT·BREKIYA·UNITHROID</td></tr>
  <tr><td>AvKARE</td><td>$157M</td><td>~19.7%</td><td>−4%</td><td>정부·기관 유통 · 저마진↓</td></tr>
  <tr><td><b>합계</b></td><td><b>$796M</b></td><td>100%</td><td><b>+10%</b></td><td>Adj GM ~46.2% (+60bps)</td></tr>
</table>
<p class="small">Q1'26 참고: 총 $722.5M · AM $423.2 / Spec $133.3 / AvKARE $166.0. FY25 매출 ~$3.02B.</p>
<div class="easy"><b>쉽게:</b> 돈의 대부분은 여전히 <b>복제약</b>이지만, 성장·마진의 스토리는 Specialty다.
AvKARE가 빠져도(−4%) 전체는 +10% — 믹스 시프트가 작동 중이다.</div>
{gloss([
    ("CREXONT", "파킨슨병 치료 브랜드 — Specialty 성장 핵심."),
    ("BREKIYA", "군발두통용 오토인젝터(자동주사)."),
    ("UNITHROID", "갑상선호르몬 제제 — 내분비 Specialty."),
    ("bp", "basis point = 0.01%p. 60bps = 0.6%p."),
])}

{compete_html}

<h2>2. 성장 · 분기 · 가이던스</h2>
{fig_block(charts['05'], '분기 매출')}
{fig_block(charts['06'], '마진·가이던스')}
<ul>
  <li>Q2'26 순매출 $796M(+10% YoY / ~+10% QoQ vs Q1 $722.5M)</li>
  <li>AM +13% · Specialty +17% · AvKARE −4% — 고마진 비중↑</li>
  <li>Adj 총이익률 ~46.2%(+60bps YoY)</li>
  <li>FY26: <b>가이던스 상향·Specialty/AM 성장</b> (콜 매출전망 +~$50M · ~$3.10–3.20B 대)</li>
  <li>다음 실적창: <b>{EARN}</b> (Q3) — Specialty 런레이트·가이던스 톤 확인</li>
</ul>

<h2>3. 시나리오 · 촉매 · 포트</h2>
{fig_block(charts['07'], '주가 시나리오')}
{fig_block(charts['08'], '촉매')}
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>23–28</td><td>Specialty 초과 · GM 추가 확대 · PT 상향</td></tr>
  <tr><td>Base</td><td>17–22</td><td>AM/Spec 가이던스 유지 · PT 평균대</td></tr>
  <tr><td>Bear</td><td>12–16</td><td>제네릭 가격전쟁 · Specialty 둔화 · 가이던스 하향</td></tr>
</table>
<div class="box">
<b>계좌 기준 실행</b><br/>
· 역할: <b>코어 보유</b>(헬스케어 축 · ECPG와 쌍) · Chase <b>중·보유·추가금지</b><br/>
· 추가매수·추격 금지 — 52주고(${H52:.2f}) 근접 · PT 업사이드 ~{UPSIDE*100:.0f}%로 얇음<br/>
· 트리거: <b>{EARN}</b> Q3에서 Specialty·Adj GM·가이던스 확인 후 재평가만<br/>
· Breaker: Specialty 성장 급락 · GM 재악화 · 가이던스 하향 · 레버리지 재상승
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>AM 본체 + Specialty 가속 + AvKARE 정리</u>로 건강하다.
이미 코어로 들고 있으니 <b>홀드·추가금지</b>가 맞고, 지금 추격 추가는 비추.</div>

<h2>부록 · 출처</h2>
<p class="small">
Amneal Q2 2026 earnings (2026-07-30) · Q1'26 세그먼트 참고 · yfinance 가격·PT·실적일 ({ASOF}).
피어 믹스·점유는 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 AMRX · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_growth_yoy(),
        "04": chart_specialty_drivers(),
        "05": chart_quarterly(),
        "06": chart_margin_guide(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("AMRX", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html = build_html(charts, compete_html=compete_html)
    html, _px = build_and_insert_price("AMRX", CHART_DIR, html)
    if _px.ok:
        print(f"price-charts {_px.candle_path} {_px.momentum_path}")
    else:
        print(f"price-charts SKIP {_px.error}")
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    doc = HTML(filename=str(OUT_HTML))
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        doc.write_pdf(str(p))
        print(f"PDF {p} {p.stat().st_size}")
    print(f"AMRX rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% earn={EARN} compete={bundle is not None}")


if __name__ == "__main__":
    main()
