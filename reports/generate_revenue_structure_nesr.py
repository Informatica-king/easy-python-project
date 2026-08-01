#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(NESR) — MENA OFS Production/D&E + 경쟁점유/믹스 + WeasyPrint PDF."""

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
PX = 26.96
PT = 33.0
H52 = 30.31
UPSIDE = PT / PX - 1.0
EARN = "08-18"
OUT_PDF = [
    Path("/opt/cursor/artifacts/NESR_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/NESR_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/NESR_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/NESR_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/nesr")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "sandstone": "#c4a35a",
    "desert": "#e8dcc8",
    "oil": "#1a3a2a",
    "teal": "#0d5c4d",
    "teal2": "#1a7a66",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "navy": "#1e3a5f",
    "gold": "#b8860b",
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
        (0.15, 0.65, 1.7, 1.55, "NOC/IOC\n중동 유전\nCAPEX", C["desert"]),
        (2.05, 0.65, 1.8, 1.55, "시추·평가\n(D&E)", C["sandstone"]),
        (4.05, 0.65, 1.85, 1.55, "생산서비스\n(프랙·시멘트)", C["teal2"]),
        (6.1, 0.65, 1.75, 1.55, "가동률\n·계약", C["teal"]),
        (8.1, 0.65, 1.65, 1.55, "매출\n·마진", C["oil"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                           facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["desert"], C["sandstone"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("비즈니스 한눈에 — MENA 유전에서 장비·인력 서비스를 판다",
                 fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [241.0, 163.5]
    labels = ["Production\n241M (60%)", "Drilling &\nEvaluation\n164M (40%)"]
    ax.pie(
        sizes, labels=labels, colors=[C["teal"], C["sandstone"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("세그먼트 매출 (Q1'26, 총 $404.6M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    sizes = [99.56, 0.44]
    labels = ["MENA\n~99.6%", "RoW\n~0.4%"]
    ax.pie(
        sizes, labels=labels, colors=[C["oil"], C["desert"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("지역 매출 (Q1'26)", fontproperties=PROP_B, fontsize=11)
    fig.suptitle("NESR 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "02_segment_geo.png")


def chart_segment_oi() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    cats = ["Production\n매출", "D&E\n매출", "Production\n영업이익", "D&E\n영업이익", "미배분\n비용", "연결\n영업이익"]
    vals = [241, 164, 32.7, 18.2, -14.9, 36.0]
    colors = [C["teal"], C["sandstone"], C["teal2"], C["gold"], C["red"], C["oil"]]
    for i, (v, c) in enumerate(zip(vals, colors)):
        ax.bar(i, v, color=c, width=0.55)
        ax.text(i, v + (8 if v >= 0 else -18), f"{v}", ha="center", fontproperties=PROP, fontsize=8)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_xticks(list(range(len(cats))))
    ax.set_xticklabels(cats, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("Q1'26 세그먼트 매출·영업이익 브리지", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "03_segment_bridge.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    layers = [
        (9.2, 8.3, "TAM — 글로벌 OFS", "전 세계 오일필드 서비스", C["desert"]),
        (7.6, 6.2, "SAM — MENA OFS ≈ 30–40B", "중동·북아프리카 유전 서비스 (근사)", C["sandstone"]),
        (5.8, 4.1, "SOM — NESR ~$1.3B+", "FY25 ~$1.32B · Q1'26 런레이트 상승", C["teal2"]),
        (4.2, 2.0, "성장 스토리", "Jafurah 프랙 · 장기 비전 경로", C["teal"]),
    ]
    for w, y, title, sub, c in layers:
        x0 = (10 - w) / 2
        ax.add_patch(
            FancyBboxPatch(
                (x0, y - 0.85), w, 1.55, boxstyle="round,pad=0.02,rounding_size=0.15",
                facecolor=c, edgecolor="white", linewidth=2, alpha=0.92,
            )
        )
        tc = "white" if c in (C["teal"], C["teal2"], C["oil"]) else C["ink"]
        ax.text(5, y + 0.25, title, ha="center", va="center", fontproperties=PROP_B, fontsize=11, color=tc)
        ax.text(5, y - 0.35, sub, ha="center", va="center", fontproperties=PROP, fontsize=8.2, color=tc)
    ax.set_title("시장 깔때기 — MENA OFS에서 NESR의 자리", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "04_tam_funnel.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [303, 327, 295, 398, 405]
    oi = [21, 27, 20, 31, 36]
    x = range(len(labels))
    ax.bar(x, rev, color=C["teal"], alpha=0.85, label="매출 ($M)", width=0.55)
    ax2 = ax.twinx()
    ax2.plot(x, oi, "o-", color=C["gold"], lw=2.2, ms=8, label="영업이익 ($M)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("매출 ($M)", fontproperties=PROP, color=C["teal"])
    ax2.set_ylabel("영업이익 ($M)", fontproperties=PROP, color=C["gold"])
    ax.set_title("분기 추이 — Q4'25~Q1'26 매출 점프 (+33% YoY)", fontproperties=PROP_B, fontsize=12)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    return save_fig(fig, "05_quarterly.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["Q3'25", "Q4'25", "Q1'26"]
    actual = [0.16, 0.32, 0.26]
    est = [0.15, 0.25, 0.21]
    surprise = [7, 26, 25]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], est, w, label="예상 EPS", color=C["desert"])
    ax.bar([i + w / 2 for i in x], actual, w, label="실제 EPS", color=C["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("EPS (USD)", fontproperties=PROP)
    ax.set_title("실적 서프라이즈 — 연속 Beat", fontproperties=PROP_B, fontsize=12)
    for i, s in enumerate(surprise):
        ax.text(i + w / 2, actual[i] + 0.01, f"+{s}%", ha="center", fontsize=8,
                fontproperties=PROP, color=C["green"])
    ax.legend(prop=PROP, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "06_eps_surprise.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 16, 22, C["red"]),
        ("Base", 24, 34, C["teal"]),
        ("Bull", 36, 44, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}–{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"현재 ${PX:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT평균 ${PT:.0f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 — MENA CAPEX·Jafurah 실행이 밴드폭", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(12, 48)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, EARN, "실적", "Q2 가동·마진\nJafurah", C["teal"]),
        (0.28, "배당", "환원", "Q4'26부터\n$0.10/분기", C["navy"]),
        (0.52, "바이백", "유동성", "최대 $50M\n승인", C["gold"]),
        (0.76, "지정학", "리스크", "MENA 집중\n~100%", C["red"]),
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
    ax.set_title(f"촉매 — {EARN} 실적 · 배당·바이백 · MENA 리스크",
                 fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "보유 위성\nSOFT·홀드관찰", C["teal"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "≤10%±2%\n추가보다 홀드", C["navy"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", f"{EARN} 소화 후\nA′/B 재스캔", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "MENA 집중·지정학 · 에너지 베타 · 실적창 주의", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "Production 60% · Beat 연속 · PT 업사이드", C["oil"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.35, body, ha="center", va="center",
                fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title("실행 포지션 맵 (사용자 계좌 · NESR×3 보유위성)", fontproperties=PROP_B, fontsize=12, pad=4)
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
<div class="easy"><b>쉽게:</b> NESR은 <b>MENA 현지 OFS</b>로 SLB/HAL/BKR 글로벌 대비 스케일은 작지만,
중동 현장 밀착·NOC 관계가 경쟁축이다. 절대 글로벌 점유가 아님.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> NESR은 매출의 약 <b>60%가 Production(프랙·시멘트 등)</b>, 40%가 시추·평가다.
글로벌 메이저는 장비·디지털·국제 믹스가 더 넓다.</div>
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
      @bottom-center {{ content:"NESR 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0d5c4d; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #1a7a66; padding-bottom:3px; color:#0d5c4d; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#1a3a2a; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ecfdf5 0%,#f7f3eb 55%,#e8dcc8 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#d1fae5; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecdd3; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#0d5c4d; color:#fff; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#ecfdf5; border-left:4px solid #0d5c4d; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#0d5c4d; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#1a7a66; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#0d5c4d; }}
    .kpi .s {{ font-size:7.5pt; color:#1a7a66; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>NESR 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>NESR 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">National Energy Services Reunited · MENA 오일필드 서비스</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1'26 실적 · 다음 실적 {EARN} · 시총 ~$2.7B</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.2f}</div><div class="s">52주고 ${H52:.2f}</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.0f}</div><div class="s">{UPSIDE*100:+.1f}%</div></span>
    <span class="kpi"><div class="l">Q1 매출</div><div class="v">$404.6M</div><div class="s">+33.5% YoY</div></span>
    <span class="kpi"><div class="l">Adj EBITDA</div><div class="v">$76.7M</div><div class="s">+22.7% YoY</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">보유위성 · Chase 중상·SOFT</span>
    <span class="tag">Production ~60%</span>
    <span class="tag warn">실적 {EARN}</span>
    <span class="tag warn">MENA ~100%</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>MENA 현지 OFS — Production(프랙·시멘트) 60% + D&E 40%.</b>
Q1'26 매출 <b>$404.6M</b>(+33.5% YoY, 사상 최고) · Adj EBITDA $76.7M(+22.7%) · NI $23.8M.
사우디 <b>Jafurah</b> 비전통 프랙이 성장 축. MENA 매출 ~99.6%로 지정학·NOC CAPEX 의존이 높다.
주가 ~${PX:.1f} vs PT ${PT:.0f}({UPSIDE*100:+.0f}%) — 당신 계좌는 <b>위성×3 보유</b>, 추가는 홀드/축소 관찰이 우선.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 중동 국영·국제 석유회사가 유전을 돌릴 때 필요한
시추·프랙·시멘트·코일튜빙 같은 <b>현장 서비스</b>를 판다. 장비+인력이 상품이다.</div>
{gloss([
    ("OFS", "Oilfield Services — 유전 서비스."),
    ("NOC/IOC", "국영/국제 석유회사 — NESR의 주요 고객."),
    ("Jafurah", "사우디 대형 비전통(가스/콘덴세이트) 개발 — 프랙 수요."),
    ("MENA", "Middle East & North Africa."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '세그먼트·지역 믹스')}
{fig_block(charts['03'], '세그먼트 손익')}
<table>
  <tr><th>세그먼트 (Q1'26)</th><th>매출</th><th>비중</th><th>영업이익</th><th>내용</th></tr>
  <tr><td><b>Production Services</b></td><td>~$241M</td><td>~60%</td><td>~$32.7M</td><td>프랙·시멘트·코일튜빙·자극 등</td></tr>
  <tr><td>Drilling &amp; Evaluation</td><td>~$164M</td><td>~40%</td><td>~$18.2M</td><td>시추공구·방향시추·와이어라인·이수 등</td></tr>
  <tr><td>미배분 / 연결</td><td>$404.6M</td><td>100%</td><td>~$36.0M</td><td>본사비용 차감 후</td></tr>
</table>
<p class="small">지역: MENA ~99.6% · Rest of World 미미. FY25 매출 ~$1.32B.</p>
<div class="easy"><b>쉽게:</b> 돈의 대부분은 <b>생산 단계 서비스(프랙 등)</b>에서 나온다.
시추·평가도 상당하지만, 최근 점프의 중심은 사우디 프랙 가동이다.</div>
{gloss([
    ("Hydraulic fracturing", "수압파쇄 — 저류층 생산성 높이는 핵심 생산서비스."),
    ("Coiled tubing", "코일 튜빙 — 유정 작업·세척·리프트 등."),
    ("Wireline / Slickline", "유정 로깅·공구 강하용 케이블 서비스."),
])}

{compete_html}

<h2>2. 성장 · 분기 궤적</h2>
{fig_block(charts['04'], '시장 깔때기')}
{fig_block(charts['05'], '분기 매출·영업이익')}
{fig_block(charts['06'], 'EPS Beat')}
<ul>
  <li>Q1'26 매출 +33.5% YoY / +1.6% QoQ — 기록 경신</li>
  <li>Adj EBITDA $76.7M(+22.7%) · 영업CF $30.7M · FCF는 캡ex로 −$5.3M</li>
  <li>순부채 ~$194M (현금 $93M / 총부채 $287M)</li>
  <li>자본환원: Q4'26부터 분기배당 예상 <b>$0.10</b> · 자사주 최대 <b>$50M</b></li>
</ul>

<h2>3. 시나리오 · 촉매 · 포트</h2>
{fig_block(charts['07'], '주가 시나리오')}
{fig_block(charts['08'], '촉매')}
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>36–44</td><td>Jafurah·MENA CAPEX 가속 · 마진 확장 · PT 상향</td></tr>
  <tr><td>Base</td><td>24–34</td><td>가동 유지 · PT 평균대 · 배당 개시</td></tr>
  <tr><td>Bear</td><td>16–22</td><td>지정학·CAPEX 둔화 · 가동률 하락 · 가이드 미스</td></tr>
</table>
<div class="box">
<b>계좌 기준 실행</b><br/>
· 역할: <b>보유 위성</b>(×3) · Chase 중상·SOFT — 추가매수보다 홀드/축소 관찰<br/>
· 코어는 ECPG/AMRX · NESR은 위성 한도(10%±2%) 안에서만<br/>
· 트리거: <b>{EARN}</b> Q2에서 프랙 가동·마진·가이던스 확인 후 A′/B 재스캔<br/>
· Breaker: MENA 지정학 악화 · NOC CAPEX 컷 · 연속 Beat 종료
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>MENA Production 중심 OFS</u>로 건강하고 성장 중이다.
다만 <b>지역 집중·에너지 베타</b>가 크므로 위성 유지·실적 소화가 맞고, 지금 추격 추가는 비추.</div>

<h2>부록 · 출처</h2>
<p class="small">
NESR Q1 2026 earnings release (2026-05-11) · yfinance 가격·PT·실적일 ({ASOF}).
피어 믹스·점유는 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 NESR · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_segment_oi(),
        "04": chart_tam_funnel(),
        "05": chart_quarterly(),
        "06": chart_eps_surprise(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("NESR", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html = build_html(charts, compete_html=compete_html)
    html, _px = build_and_insert_price("NESR", CHART_DIR, html)
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
    print(f"NESR rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% earn={EARN} compete={bundle is not None}")


if __name__ == "__main__":
    main()
