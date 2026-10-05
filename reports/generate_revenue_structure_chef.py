#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(CHEF) — The Chefs' Warehouse 특화 유통 + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-10-05"
PX = 117.82
PT = 122.00
H52 = 118.51
L52 = 53.24
UPSIDE = PT / PX - 1.0
EARN = "10-28"
OUT_PDF = [
    Path("/opt/cursor/artifacts/CHEF_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/CHEF_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/CHEF_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/CHEF_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/chef")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "navy": "#1e3a5f",
    "navy2": "#2c5282",
    "teal": "#0f766e",
    "teal2": "#14b8a6",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "spec": "#0e7490",
    "cop": "#c2410c",
    "olive": "#3f6212",
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
        (0.12, 0.7, 1.75, 1.6, "독립 셰프\n레스토랑·호텔\n55k+ 로케이션", C["sand"]),
        (2.05, 0.7, 1.8, 1.6, "23개 시장\nUS·중동·캐나다\n9만+ SKU", C["navy2"]),
        (4.05, 0.7, 1.75, 1.6, "Specialty\n식자재 61%", C["spec"]),
        (5.95, 0.7, 1.75, 1.6, "Center-of-\nPlate 단백질 39%", C["cop"]),
        (7.9, 0.7, 1.85, 1.6, "매출·GP\nAdj.EBITDA", C["teal"]),
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
            fontproperties=PROP_B, fontsize=8.2, color=tc,
        )
    ax.set_title(
        "비즈니스 한눈에 — 독립 셰프에게 특화 식자재·단백질을 배달",
        fontproperties=PROP_B, fontsize=12, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.15))
    ax = axes[0]
    sizes = [711.0, 457.6]
    labels = ["Specialty\n$711M (60.8%)", "Center-of-Plate\n$458M (39.2%)"]
    ax.pie(
        sizes, labels=labels, colors=[C["spec"], C["cop"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.5),
    )
    ax.set_title("매출 믹스 (Q2'26, 총 $1.17B)", fontproperties=PROP_B, fontsize=10.5)

    ax = axes[1]
    cats = ["건식", "농산", "페이스트리", "치즈\n샤퀴테리", "유제품\n계란", "오일\n식초", "주방용품"]
    vals = [185.8, 166.2, 149.4, 79.4, 68.6, 36.8, 24.9]
    colors = [C["spec"], C["olive"], C["teal2"], C["gold"], C["navy2"], C["navy"], C["muted"]]
    for i, (v, c) in enumerate(zip(vals, colors)):
        ax.bar(i, v, color=c, width=0.62)
        ax.text(i, v + 3.5, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=7.5)
    ax.set_xticks(list(range(len(cats))))
    ax.set_xticklabels(cats, fontproperties=PROP, fontsize=7.2)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("Specialty 세부 (Q2'26)", fontproperties=PROP_B, fontsize=10.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("CHEF 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_mix.png")


def chart_growth_bridge() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.85))

    ax = axes[0]
    labels = ["Q2'25", "유기\n성장", "Italco\nM&A", "Q2'26"]
    vals = [1034.9, 126.1, 7.6, 1168.6]
    colors = [C["muted"], C["teal"], C["gold"], C["navy"]]
    for i, (v, c) in enumerate(zip(vals, colors)):
        ax.bar(i, v, color=c, width=0.55)
        ax.text(i, v + 18, f"{v:.0f}" if i != 2 else "+8", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_xticks(list(range(4)))
    ax.set_xticklabels(labels, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("매출 브리지 — 유기 +12.2% · M&A +0.7%", fontproperties=PROP_B, fontsize=10.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    cats = ["Specialty\n케이스", "Specialty\n고객", "Specialty\n플레이스먼트", "CoP\npounds"]
    yoy = [6.0, 3.6, 7.2, 8.8]
    for i, v in enumerate(yoy):
        ax.bar(i, v, color=C["teal"] if v >= 5 else C["gold"], width=0.55)
        ax.text(i, v + 0.15, f"+{v:.1f}%", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_xticks(list(range(len(cats))))
    ax.set_xticklabels(cats, fontproperties=PROP, fontsize=7.5)
    ax.set_ylabel("유기 YoY %", fontproperties=PROP)
    ax.set_title("물량 엔진 (유기, Q2'26)", fontproperties=PROP_B, fontsize=10.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("성장은 인수보다 기존 점포·고객 침투", fontproperties=PROP_B, fontsize=12, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "03_growth_bridge.png")


def chart_pnl() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    x = [0, 1]
    gp = [24.6, 25.1]
    sga = [20.7, 20.0]
    op = [3.9, 5.1]
    ax.plot(x, gp, marker="o", color=C["teal"], lw=2.2, label="GP%")
    ax.plot(x, sga, marker="o", color=C["gold"], lw=2.2, label="SG&A%")
    ax.plot(x, op, marker="o", color=C["navy"], lw=2.2, label="영업이익%")
    ax.set_xticks(x)
    ax.set_xticklabels(["Q2'25", "Q2'26"], fontproperties=PROP)
    ax.set_ylabel("% of sales", fontproperties=PROP)
    ax.set_title("마진 확장 — GP +49bp · SG&A −70bp", fontproperties=PROP_B, fontsize=10.5)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    labs = ["매출\n$B", "GP\n$M", "Adj EBITDA\n$M", "순이익\n$M"]
    a = [1.03, 254, 65.4, 21.2]
    b = [1.17, 293, 88.1, 33.8]
    w = 0.35
    ax.bar([i - w / 2 for i in range(4)], a, w, label="Q2'25", color=C["sand"])
    ax.bar([i + w / 2 for i in range(4)], b, w, label="Q2'26", color=C["navy"])
    ax.set_xticks(list(range(4)))
    ax.set_xticklabels(labs, fontproperties=PROP, fontsize=8)
    ax.set_title("달러 실적 YoY", fontproperties=PROP_B, fontsize=10.5)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "04_pnl.png")


def chart_geo() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.5))
    labs = ["미국", "국제\n(중동+캐나다)"]
    y26 = [1083.8, 84.8]
    y25 = [941.5, 93.4]
    w = 0.35
    ax.bar([0 - w / 2, 1 - w / 2], y25, w, label="Q2'25", color=C["sand"])
    ax.bar([0 + w / 2, 1 + w / 2], y26, w, label="Q2'26", color=C["navy"])
    ax.text(0 + w / 2, 1083.8 + 18, "+15.1%", ha="center", fontproperties=PROP, fontsize=8, color=C["teal"])
    ax.text(1 + w / 2, 84.8 + 18, "−9.2%", ha="center", fontproperties=PROP, fontsize=8, color=C["red"])
    ax.set_xticks([0, 1])
    ax.set_xticklabels(labs, fontproperties=PROP, fontsize=9)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("지역 — 미국 92.7% 본체 · 국제는 중동 계절 약세", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(
        0.99, 0.04,
        "중동 5–6월 전년의 ~94% · 국가별 10% 넘는 해외국 없음",
        transform=ax.transAxes, ha="right", fontproperties=PROP, fontsize=7.5, color=C["muted"],
    )
    fig.tight_layout()
    return save_fig(fig, "05_geo.png")


def chart_guide() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.55))
    metrics = ["매출\n$B", "매출총이익\n$B", "Adj EBITDA\n$M"]
    lo = [4.50, 1.102, 305]
    hi = [4.60, 1.125, 315]
    x = list(range(3))
    ax.bar(x, hi, color=C["teal2"], width=0.45, label="상단")
    ax.bar(x, lo, color=C["navy"], width=0.45, label="하단")
    labels = ["4.50–4.60", "1.10–1.13", "305–315"]
    for i, t in enumerate(labels):
        ax.text(i, hi[i] * 1.03 if i < 2 else hi[i] + 8, t, ha="center", fontproperties=PROP, fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontproperties=PROP, fontsize=9)
    ax.set_title("FY26 가이던스 (Q2 후 재확인)", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "06_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.4))
    ax.set_xlim(50, 140)
    ax.set_ylim(0, 4)
    ax.axis("off")
    bands = [
        (66, 80, 3.05, C["red"], "Bear $66–80"),
        (89, 102, 2.05, C["gold"], "Base $89–102"),
        (113, 128, 1.05, C["teal"], "Bull $113–128"),
    ]
    for lo, hi, y, c, lab in bands:
        ax.barh(y, hi - lo, left=lo, height=0.7, color=c, alpha=0.75)
        ax.text((lo + hi) / 2, y, lab, ha="center", va="center", fontproperties=PROP_B, fontsize=9, color="white")
    ax.axvline(PX, color=C["ink"], lw=1.4, ls="--")
    ax.text(PX + 1.2, 3.7, f"현재 ${PX:.2f}", fontproperties=PROP, fontsize=8)
    ax.set_title("시나리오 밴드 vs 현재가 (Qual 10-05)", fontproperties=PROP_B, fontsize=11)
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    cards = [
        (0.2, 1.55, 3.0, 1.4, "실적 10-28", "Q3 · EARN 창\n가이던스 유지 여부", C["navy"]),
        (3.5, 1.55, 3.0, 1.4, "농산·침투", "Produce +34%\n플레이스먼트 +7%", C["teal"]),
        (6.8, 1.55, 3.0, 1.4, "중동·Italco", "ME 회복 · Denver\n특화 통합", C["gold"]),
        (0.2, 0.15, 3.0, 1.2, "마진", "GP 25.1% · 레버리지\n~2x 이하", C["olive"]),
        (3.5, 0.15, 3.0, 1.2, "리스크", "외식 소비 · 인플레\n고점 추격", C["cop"]),
        (6.8, 0.15, 3.0, 1.2, "전환사채", "2028 · 희석 이미\n희석EPS에 반영", C["navy2"]),
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
                       facecolor="#fff7ed", edgecolor=C["cop"], lw=2)
    )
    ax.text(
        5.0, 2.05,
        "미보유 · 10-05 심층 유니버스 제외 · Qual Chase 중 · 고점주의",
        ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=C["cop"],
    )
    ax.text(
        5.0, 1.1,
        f"현재 ${PX:.2f} · PT ${PT:.0f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}–${H52:.2f}\n"
        "추격 금지 · 눌림만 · 다음 실적 10-28 · 외식·중동·가이던스 게이트",
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
<div class="easy"><b>쉽게:</b> CHEF는 상장 푸드서비스 유통 피어셋에서 <b>스케일 미니(~2.5%)</b>다.
Sysco·PFGC·US Foods가 브로드라인 거인. CHEF 점유 Δ는 <b>+0.3pp</b> 추정 — 성장률이 빨라 상대 비중만 소폭↑.
절대 시장점유가 아니라 피어 대비 상대 크기. 특화 독립 레스토랑 틈새가 본체.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> CHEF는 <b>Specialty ~61% / 단백질(CoP) ~39% / 브로드라인 0</b>.
피어는 브로드라인(대량 식자재)이 본체라 마진·고객이 다르다. CHEF의 차별점은 ‘셰프가 메뉴에 넣는 특화 SKU’다.</div>
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
      @bottom-center {{ content:"CHEF 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0f766e; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #14b8a6; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#1e3a5f; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ecfdf5 0%,#ccfbf1 45%,#ffedd5 100%);
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
<html lang="ko"><head><meta charset="utf-8"/><title>CHEF 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>CHEF 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">The Chefs' Warehouse · 특화 푸드서비스 유통 · 독립 셰프·파인다이닝</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적(07-29 발표) · ${PX:.2f}</p>
  <div style="margin-top:22px">
    <span class="tag good">매출 $1.17B +12.9%</span>
    <span class="tag good">유기 +12.2%</span>
    <span class="tag good">Adj EBITDA $88M</span>
    <span class="tag">GP 25.1% +49bp</span>
    <span class="tag warn">52주 고점 직전</span>
  </div>
  <div style="margin-top:28px">
    <div class="kpi"><div class="l">Q2 매출</div><div class="v">$1.17B</div><div class="s">+12.9% YoY</div></div>
    <div class="kpi"><div class="l">Specialty</div><div class="v">60.8%</div><div class="s">$711M</div></div>
    <div class="kpi"><div class="l">Center-of-Plate</div><div class="v">39.2%</div><div class="s">$458M</div></div>
    <div class="kpi"><div class="l">업사이드</div><div class="v">{UPSIDE*100:+.0f}%</div><div class="s">PT ${PT:.0f}</div></div>
  </div>
  <p class="small" style="margin-top:36px;max-width:560px;margin-left:auto;margin-right:auto">
    독립 레스토랑 셰프에게 특화 식자재와 단백질을 배달하는 유통사.
    미국 23개 요리 시장이 본체(매출 93%), 중동·캐나다는 소형.
    실적·마진은 강한 성장. 주가는 52주 고점 직전이라 수익구조 공부와 매수는 분리.
  </p>
</section>

<h2>0. 한줄 결론</h2>
<div class="box">
<b>구조는 “독립 셰프향 특화 유통: Specialty 본체(~61%) + Center-of-Plate 단백질(~39%)” — 실적·마진은 좋은데 업사이드는 얇고 추격 금지.</b>
Q2'26 매출 $1.169B(+12.9%, 유기 +12.2%) · GP $293M(25.1%, +49bp) · Adj EBITDA $88.1M(+35%) ·
희석 EPS $0.76 / Adj $0.78 · FY26 가이던스 매출 $4.50–4.60B · GP $1.10–1.13B · Adj EBITDA $305–315M.
포트: <b>미보유 · 10-05 심층 유니버스 제외 · Qual Chase 중 · 고점주의</b> ·
업사이드 {UPSIDE*100:+.1f}% — <b>추격 금지 · 눌림만</b>. 다음 실적 {EARN}.
</div>

<h2>1. 비즈니스 구조</h2>
<div class="easy"><b>쉽게:</b> CHEF는 마트형 대량 유통(Sysco 같은 브로드라인)이 아니다.
<b>요리사가 메뉴에 넣는 특화 식자재</b>(오일, 치즈, 페이스트리, 농산 등)와
스테이크·해산물 같은 <b>접시 한가운데 단백질(Center-of-Plate)</b>을 독립 레스토랑·호텔에 배달한다.
보고 세그먼트는 하나(foodservice distribution)지만, 운영은 East / Midwest / West 세 권역이다.</div>
{fig_block(charts['flow'], '셰프 수요 → 23개 시장 특화 유통 → Specialty / CoP → 매출·이익')}
{gloss([
    ("Specialty", "특화 식자재 — 건식·농산·페이스트리·치즈·유제품·오일·주방용품. 케이스(상자) 수로 물량 측정"),
    ("Center-of-Plate (CoP)", "접시 한가운데 단백질 — 소고기·해산물·가금. 파운드(무게)로 물량 측정"),
    ("Broadline", "Sysco류 대량 범용 식자재 유통. CHEF는 이 축이 거의 없음"),
    ("Placements", "고객 한 명에게 몇 가지 SKU를 팔았는지 — 침투(크로스셀) 지표"),
    ("Italco", "2025-10-01 인수한 덴버 특화 유통사. Q2 매출 기여 +0.7%"),
])}

{compete_html}

<h2>2. 매출·손익 (Q2'26)</h2>
<div class="easy"><b>쉽게:</b> 돈의 약 61%는 특화 식자재, 39%는 단백질.
성장의 대부분은 <b>기존 고객이 더 사고(유기 +12.2%)</b> 인수는 소수(+0.7%).
마진도 같이 올라 GP 25.1%, 영업이익률 5.1%. 다만 중동은 여름 비수기로 전년보다 약하다.</div>
{fig_block(charts['mix'], 'Specialty vs CoP · Specialty 세부 카테고리')}
{fig_block(charts['growth'], '유기 성장 브리지 · 물량')}
{fig_block(charts['pnl'], '마진 · 달러 실적')}
{fig_block(charts['geo'], '미국 vs 국제')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>Q2'25</th><th>메모</th></tr>
  <tr><td>Net sales</td><td>$1,168.6M</td><td>$1,034.9M</td><td>+12.9% · 유기 +12.2% · Italco +0.7%</td></tr>
  <tr><td>Specialty</td><td>$711.0M (60.8%)</td><td>$640.6M (61.9%)</td><td>케이스 +6.0% · 고객 +3.6% · 플레이스먼트 +7.2%</td></tr>
  <tr><td>Center-of-Plate</td><td>$457.6M (39.2%)</td><td>$394.3M (38.1%)</td><td>파운드 +8.8% · 인플레 +6.4%</td></tr>
  <tr><td> Dry Goods</td><td>$185.8M (15.9%)</td><td>$167.7M</td><td>+10.8%</td></tr>
  <tr><td> Produce</td><td>$166.2M (14.2%)</td><td>$124.0M</td><td>+34.0% — 카테고리 중 가장 빠름</td></tr>
  <tr><td> Pastry</td><td>$149.4M (12.8%)</td><td>$139.3M</td><td>+7.3%</td></tr>
  <tr><td> Cheese &amp; Charcuterie</td><td>$79.4M (6.8%)</td><td>$76.0M</td><td>+4.5%</td></tr>
  <tr><td> Dairy &amp; Eggs</td><td>$68.6M (5.9%)</td><td>$78.0M</td><td>−12.0% — 가격/믹스 역풍</td></tr>
  <tr><td>United States</td><td>$1,083.8M (92.7%)</td><td>$941.5M</td><td>+15.1%</td></tr>
  <tr><td>International</td><td>$84.8M (7.3%)</td><td>$93.4M</td><td>−9.2% · 중동 5–6월 ~94% of PY</td></tr>
  <tr><td>Gross profit / margin</td><td>$292.9M / 25.1%</td><td>$254.3M / 24.6%</td><td>+49bp · Specialty +47bp · CoP +75bp</td></tr>
  <tr><td>SG&amp;A / % sales</td><td>$234.2M / 20.0%</td><td>$213.8M / 20.7%</td><td>고정비 레버리지 −70bp</td></tr>
  <tr><td>Operating income</td><td>$58.6M (5.1%)</td><td>$40.2M (3.9%)</td><td>+45.8%</td></tr>
  <tr><td>Net income / dil. EPS</td><td>$33.8M / $0.76</td><td>$21.2M / $0.49</td><td>+59%</td></tr>
  <tr><td>Adj. EPS / Adj. EBITDA</td><td>$0.78 / $88.1M</td><td>$0.52 / $65.4M</td><td>EBITDA +35%</td></tr>
  <tr><td>1H OCF / capex</td><td>$96.7M / $16.9M</td><td>$64.1M / $22.3M</td><td>현금창출력 개선</td></tr>
</table>
{gloss([
    ("유기 성장", "인수 후 12개월이 지난 기존 사업만의 성장. Q2는 +$126M"),
    ("인플레 기여", "같은 물량이라도 식자재 가격이 올라 매출 달러가 커지는 부분. Specialty +4.0% · CoP +6.4%"),
    ("Adj. EBITDA", "주식보상·중복임차 등 조정 후 영업 현금창출력"),
    ("희석 EPS", "2028 전환사채 649만주 효과가 분모에 들어감. 전환 전에도 희석 기준으로 발표"),
])}

<h2>3. 파이프라인 · 가이던스</h2>
{fig_block(charts['guide'], 'FY26 가이던스')}
<div class="easy"><b>쉽게:</b> 회사는 Q2 이후에도 연간 가이던스를 <b>유지</b>했다.
올해 매출 $4.50–4.60B, 매출총이익 $1.10–1.13B, Adj EBITDA $305–315M.
설비투자는 $45–55M. 자사주 $100M 한도 중 잔여 $57.6M (1H에 15.7만주, 평균 $63.75 — 현재가보다 훨씬 낮게 매입).</div>
<table>
  <tr><th>지표</th><th>내용</th></tr>
  <tr><td>FY26 매출</td><td>$4.50–4.60B (재확인)</td></tr>
  <tr><td>FY26 Gross profit</td><td>$1.102–1.125B</td></tr>
  <tr><td>FY26 Adj. EBITDA</td><td>$305–315M</td></tr>
  <tr><td>FY26 순이익 가이던스 브리지</td><td>$104–108M (EBITDA 가이던스 표)</td></tr>
  <tr><td>FY26 capex</td><td>$45–55M</td></tr>
  <tr><td>순부채 감각</td><td>총부채 ~$725M − 현금 $135M ≈ $590M · EBITDA 런레이트 대비 ~2x 전후</td></tr>
  <tr><td>ABL 여유</td><td>$186M available</td></tr>
  <tr><td>Italco</td><td>2025-10-01 Denver 특화 · Q2 +$7.6M</td></tr>
  <tr><td>중동</td><td>성수기 지나 5–6월 전년의 ~94% · 점진 개선 코멘트</td></tr>
</table>

<h2>4. 시나리오 · 촉매</h2>
{fig_block(charts['scen'], '주가 시나리오 밴드')}
{fig_block(charts['cat'], '촉매 카드')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$66–80</td><td>외식 소비 꺾임 · 가이던스 컷 · 중동 추가 악화 · 마진 환원</td></tr>
  <tr><td>Base</td><td>$89–102</td><td>FY26 가이던스 달성 · 유기 고한자릿수 유지 · 멀티플 정상화</td></tr>
  <tr><td>Bull</td><td>$113–128</td><td>침투·농산 지속 · 중동 회복 · 가이던스 상향 — <b>현재가가 이미 이 밴드</b></td></tr>
</table>

<h2>5. 포트 실행</h2>
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (10-05 포폴 · Qual)</b><br/>
<b>미보유</b> · 10-05 심층 46종 유니버스에 없음 · Qual Chase <b>중</b> · 엔트리 <b>눌림</b>.<br/>
현재 ${PX:.2f} · 컨센서스 PT ${PT:.0f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}–${H52:.2f} (고점 −0.6%).<br/>
실행: <b>추격 금지</b> · <b>눌림만</b>. 다음 실적 <b>2026-10-28</b> (아직 EARN_D5 아님).<br/>
게이트: FY26 가이던스 유지 · Specialty 케이스/플레이스먼트 · CoP 파운드 · 중동 회복 · 외식 소비.
</div>

<p class="small">생성: 수익구조분석() · 티커 CHEF · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart<br/>
출처: CHEF 10-Q / exhibit 99.1 (분기 종료 2026-06-26, 발표 2026-07-29) · yfinance · 피어 점유/믹스는 방향 비교용 추정</p>
</body></html>
"""


def main() -> int:
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "growth": chart_growth_bridge(),
        "pnl": chart_pnl(),
        "geo": chart_geo(),
        "guide": chart_guide(),
        "scen": chart_scenarios(),
        "cat": chart_catalysts(),
        "pos": chart_position(),
    }
    bundle, cpaths = build_compete_charts("CHEF", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("CHEF", CHART_DIR, html_doc)
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

        tag = "sepa-rev-chef"
        notes = (
            f"## CHEF 수익구조분석 ({ASOF})\n\n"
            f"The Chefs' Warehouse · 특화 푸드서비스 유통 · Q2'26.\n\n"
            f"- Rev $1.17B (+12.9%, organic +12.2%) · GP 25.1% · Adj EBITDA $88.1M\n"
            f"- Specialty 60.8% / Center-of-Plate 39.2% · US 92.7%\n"
            f"- FY26 guide $4.50–4.60B · Adj EBITDA $305–315M\n"
            f"- 미보유 · 고점주의 · 업사이드 {UPSIDE*100:+.1f}% "
            f"(PT ${PT:.0f} · px ${PX:.2f})\n"
            f"- 추격 금지 · 눌림만 · 다음 실적 2026-10-28\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — CHEF",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
