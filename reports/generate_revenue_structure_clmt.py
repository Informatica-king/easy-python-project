#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(CLMT) — Calumet 특수제품·재생연료 + 경쟁점유/믹스 + WeasyPrint PDF."""

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
PX = 55.70
PT = 53.40
H52 = 59.87
L52 = 17.42
UPSIDE = PT / PX - 1.0
EARN = "11-06"
OUT_PDF = [
    Path("/opt/cursor/artifacts/CLMT_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/CLMT_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/CLMT_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/CLMT_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/clmt")
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
    "clmt": "#7c2d12",
    "sps": "#c2410c",
    "mr": "#0f766e",
    "pb": "#a16207",
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
        (0.1, 0.7, 1.7, 1.6, "원유·바이오\n피드스톡", C["sand"]),
        (1.95, 0.7, 1.75, 1.6, "정제·전환\nSPS / MR", C["clmt"]),
        (3.9, 0.7, 1.75, 1.6, "특수제품\n윤활·용제·왁스", C["sps"]),
        (5.85, 0.7, 1.75, 1.6, "재생연료\nRD·SAF", C["mr"]),
        (7.8, 0.7, 1.9, 1.6, "브랜드\nTruFuel 등", C["pb"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = "white" if c != C["sand"] else C["ink"]
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.5, color=tc)
    for x in (1.85, 3.75, 5.7, 7.65):
        ax.annotate(
            "", xy=(x + 0.08, 1.5), xytext=(x - 0.08, 1.5),
            arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6),
        )
    ax.set_title(
        "CLMT 가치사슬 — 피드스톡 → 특수제품 + 재생연료 + 브랜드",
        fontproperties=PROP_B, fontsize=11, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_revenue_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.95))
    ax = axes[0]
    labels = ["Specialty\nProducts", "Montana/\nRenewables", "Performance\nBrands"]
    vals = [70.1, 22.8, 7.1]
    colors = [C["sps"], C["mr"], C["pb"]]
    ax.pie(
        vals, labels=labels, colors=colors,
        autopct=lambda p: f"{p:.0f}%",
        textprops={"fontproperties": PROP, "fontsize": 8.5},
        startangle=90, wedgeprops=dict(width=0.45, edgecolor="white"),
    )
    ax.set_title("Q2'26 보고 세그먼트 매출", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    segs = [
        ("SPS 연료·부산물", 537.4),
        ("SPS 윤활·용제·왁스", 475.1),
        ("Montana/Renewables", 329.0),
        ("Performance Brands", 103.6),
    ]
    names = [s[0] for s in segs]
    fvals = [s[1] for s in segs]
    bar_c = [C["gold"], C["sps"], C["mr"], C["pb"]]
    bars = ax.barh(names[::-1], fvals[::-1], color=bar_c[::-1], height=0.55)
    ax.set_xlabel("$M", fontproperties=PROP)
    ax.set_title("제품 성격별 매출 ($M)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, fvals[::-1]):
        ax.text(v + 8, b.get_y() + b.get_height() / 2, f"${v:.0f}",
                va="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_mix.png")


def chart_ebitda_segments() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    names = ["SPS", "PB", "MR+Tax", "Corp"]
    vals = [161.7, 6.3, 26.6, -19.4]
    colors = [C["sps"], C["pb"], C["mr"], C["slate"]]
    bars = ax.bar(names, vals, color=colors, width=0.55)
    ax.axhline(0, color="#94a3b8", lw=0.8)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("Q2'26 Adj. EBITDA (+Tax Attr)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (4 if v >= 0 else -12),
                f"{v:.1f}", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    qs = ["Q2'25", "Q1'26", "Q2'26"]
    tot = [76.5, 50.1, 175.2]
    ax.bar(qs, tot, color=[C["sand"], C["gold"], C["clmt"]], width=0.55)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("Adj EBITDA with Tax Attributes", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(tot):
        ax.text(i, v + 4, f"{v:.1f}", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "03_ebitda.png")


def chart_production() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    cats = ["윤활유", "용제", "왁스", "연료·기타\n(SPS)", "재생연료\n(MR)", "전통연료\n(MR)", "브랜드"]
    vals = [13318, 7637, 1559, 40389, 7011, 11113, 2164]
    colors = [C["sps"], C["sps"], C["sps"], C["sps"], C["mr"], C["teal"], C["pb"]]
    bars = ax.bar(cats, vals, color=colors, width=0.65)
    ax.set_ylabel("bpd", fontproperties=PROP)
    ax.set_title("Q2'26 설비 생산량 (bpd) · 총 83.2k", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 400, f"{v:,.0f}",
                ha="center", fontproperties=PROP, fontsize=7)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)
    fig.tight_layout()
    return save_fig(fig, "04_production.png")


def chart_pnl_quality() -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(9.4, 3.5))
    ax = axes[0]
    ax.bar(["매출"], [1445.1], color=C["clmt"], width=0.45)
    ax.set_title("Q2 매출 $1.45B", fontproperties=PROP_B, fontsize=10)
    ax.text(0, 1500, "+40.8% YoY", ha="center", fontproperties=PROP, fontsize=8, color=C["green"])
    ax.set_ylim(0, 1750)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    ax.bar(["GAAP NI"], [-95.9], color=C["red"], width=0.45)
    ax.set_title("GAAP 순손실", fontproperties=PROP_B, fontsize=10)
    ax.text(0, -70, "RIN MTM\n$164M", ha="center", fontproperties=PROP, fontsize=8, color=C["red"])
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[2]
    ax.bar(["Adj EPS"], [0.68], color=C["green"], width=0.45)
    ax.set_title("Adj EPS Beat", fontproperties=PROP_B, fontsize=10)
    ax.text(0, 0.74, "vs Est $0.16", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 0.95)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.suptitle("탑라인·Adj 이익 폭증 vs GAAP는 RIN 비현금으로 적자", fontproperties=PROP_B, fontsize=11, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "05_pnl.png")


def chart_outlook() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    ax.axis("off")
    items = [
        (0.04, "SPS", "마진 16%\n크랙·특수 강세", C["sps"]),
        (0.28, "MaxSAF", "150 완료\n5월 재가동", C["mr"]),
        (0.52, "정책", "RVO 사상최고\nRIN 변동", C["gold"]),
        (0.76, "부채", "7월 $115M\n디레버", C["navy"]),
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
    ax.set_title("전망 — SPS 마진 · SAF 램프 · 정책 · 디레버", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "06_outlook.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    px = PX
    scenarios = [
        ("Bear", 28, 40, C["red"]),
        ("Base", 42, 54, C["teal"]),
        ("Bull", 58, 75, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}-{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(px, color=C["navy"], lw=1.5, ls="--")
    ax.text(px, 2.55, f"현재 ${px:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT평균 ${PT:.1f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 밴드 (예시 · 투자권유 아님) · PT 대비 프리미엄", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(22, 80)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, "11-06", "실적", "Q3 마진·SAF\n디레버 확인", C["teal"]),
        (0.28, "SAF", "성장", "MaxSAF 150\n램프·믹스", C["mr"]),
        (0.52, "RIN", "정책", "RVO 최고치\n크레딧 변동", C["gold"]),
        (0.76, "부채", "리스크", "순부채 높음\n부의 자본", C["red"]),
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
    ax.set_title("촉매 — 11-06 실적 · SAF · RIN · 부채", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "미보유 · Chase 하\n과열 · 추격 금지", C["clmt"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "코어 아님\n위성도 비우선", C["teal"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", "고점·PT프리미엄\n11-06 후 재평가", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "52주 고점권 · 레버리지·부의자본 · RIN 변동", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "SPS 마진 폭증 · MaxSAF 완료 · GAAP/Adj 괴리", C["navy"]),
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
<div class="easy"><b>쉽게:</b> CLMT는 대형 정유사보다 작고, <b>특수제품+재생연료</b> 하이브리드다.
점유율은 상장 피어셋 스케일 비교용이다. 피어셋 대비 점유는 <b>+2.0pp</b> (방향 비교, 절대 시장점유 아님).</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>
{gloss([
    ("SPS", "Specialty Products and Solutions — 윤활·용제·왁스·부산물."),
    ("SAF", "Sustainable Aviation Fuel — 항공기용 재생연료."),
])}

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> 보고 세그먼트로는 매출의 약 <b>70%가 SPS</b>다.
다만 SPS 안에서도 Q2는 <b>연료·부산물 $537M</b>이 윤활·용제·왁스 $475M보다 크다.
피어(PBF/DINO/GPRE)는 연료·바이오 비중이 더 크다.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
{gloss([
    ("RIN", "Renewable Identification Number — 재생연료 규제 크레딧. 손익 변동성 큼."),
    ("MaxSAF", "Montana Renewables SAF 증설. Q2 완료, 5월 초 재가동."),
])}
"""


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"CLMT 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#7c2d12; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #c2410c; padding-bottom:3px; color:#7c2d12; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0f766e; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ffedd5 0%,#fef3c7 55%,#ecfdf5 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#ffedd5; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.good {{ background:#bbf7d0; }}
    .tag.bad {{ background:#fecdd3; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#fff7ed; border-left:4px solid #c2410c; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#7c2d12; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#c2410c; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpis {{ width:92%; margin:18px auto 0; border-collapse:separate; border-spacing:8px; }}
    .kpis td {{ background:#fff; border:1px solid #cbd5e1; padding:8px 10px; width:25%;
      text-align:center; vertical-align:middle; }}
    .kpis .l {{ font-size:7.5pt; color:#64748b; }}
    .kpis .v {{ font-size:12pt; font-weight:700; color:#7c2d12; }}
    .kpis .s {{ font-size:7.5pt; color:#c2410c; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>CLMT 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>CLMT 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Calumet · 특수석유제품 + 재생연료(RD/SAF) · Performance Brands</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 10-Q · 다음 실적 {EARN} · 시총 ~$4.90B</p>
  <table class="kpis">
    <tr>
      <td><div class="l">현재가</div><div class="v">${PX:.2f}</div><div class="s">52주고 ${H52:.2f}</div></td>
      <td><div class="l">PT 평균</div><div class="v">${PT:.1f}</div><div class="s">업사이드 {UPSIDE*100:+.1f}%</div></td>
      <td><div class="l">Q2 매출</div><div class="v">$1.45B</div><div class="s">+40.8% YoY</div></td>
      <td><div class="l">Adj EBITDA*</div><div class="v">$175.2M</div><div class="s">*Tax Attributes</div></td>
    </tr>
  </table>
  <p style="margin-top:18px">
    <span class="tag bad">Chase 하·과열</span>
    <span class="tag warn">PT 프리미엄 · 고점권</span>
    <span class="tag">다음 실적 {EARN}</span>
    <span class="tag">미보유</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>보고 세그먼트는 SPS 70%가 본체지만, Q2 달러 매출의 약 60%는 연료·아스팔트다.</b>
Q2'26: 매출 $1,445.1M(+40.8%) · SPS Adj EBITDA $161.7M(마진 16.0%) · PB $6.3M · MR+TaxAttr $26.6M ·
합산 Adj EBITDA with Tax Attributes $175.2M (전년 $76.5M). GAAP는 RIN MTM $163.6M 등으로
<b>순손실 $95.9M (EPS -$1.09)</b>. MaxSAF 150은 Q2 완료·5월 재가동. 7월 $115M 디레버.
주가는 52주 고점권·PT 대비 프리미엄 — <b>미보유 · 추격 금지</b>.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 원유·바이오 원료를 넣어 <b>특수 석유화학 제품</b>과 <b>재생 항공유·디젤</b>을 만든다.
Q1은 공장 이슈로 이익이 나빴고, Q2는 특수제품 가격 인상과 연료 크랙이 겹쳐 Adj 이익이 크게 뛰었다.
다만 GAAP 적자와 부채·부의 자본은 그대로다.</div>
{gloss([
    ("SPS", "Specialty Products and Solutions."),
    ("MR", "Montana/Renewables — 재생연료·일부 전통연료."),
    ("RIN", "재생연료 식별번호 크레딧. 시세·정책에 손익 민감."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '매출 믹스')}
{fig_block(charts['03'], '세그먼트 EBITDA')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>YoY / 메모</th><th>의미</th></tr>
  <tr><td><b>Total sales</b></td><td>$1,445.1M</td><td>+40.8% vs $1,026.6M</td><td>가격+특수 수요</td></tr>
  <tr><td>SPS sales</td><td>$1,012.5M</td><td>매출 70.1% · +61.3%</td><td>보고 세그먼트 본체</td></tr>
  <tr><td>윤활유 (SPS)</td><td>$281.0M</td><td>+47.7%</td><td>특수 핵심</td></tr>
  <tr><td>용제 (SPS)</td><td>$153.2M</td><td>+50.9%</td><td>특수 핵심</td></tr>
  <tr><td>왁스 (SPS)</td><td>$40.9M</td><td>+1.7%</td><td>소액</td></tr>
  <tr><td>연료·아스팔트·부산물 (SPS)</td><td>$537.4M</td><td>+81.6%</td><td>SPS 달러의 53%</td></tr>
  <tr><td>MR sales</td><td>$329.0M</td><td>+3.5% · 재생 $183.2 / 전통 $145.8</td><td>턴어라운드로 물량-30%</td></tr>
  <tr><td>PB sales</td><td>$103.6M</td><td>+28.4% · TruFuel 분기 최고</td><td>물량+24%</td></tr>
  <tr><td>SPS Adj EBITDA</td><td>$161.7M</td><td>vs $66.8M · 마진 16.0%</td><td>가격 실현+가동 정상</td></tr>
  <tr><td>PB Adj EBITDA</td><td>$6.3M</td><td>vs $13.5M · LIFO $7.3M</td><td>마진 압축</td></tr>
  <tr><td>MR Adj EBITDA + Tax</td><td>$26.6M</td><td>vs $16.3M (Adj $10.7M)</td><td>물량 감소에도 마진↑</td></tr>
  <tr><td>Corp Adj EBITDA</td><td>-$19.4M</td><td>본사비용</td><td></td></tr>
  <tr><td>GAAP Net Income</td><td>-$95.9M</td><td>RIN MTM $163.6M 등</td><td>비현금 왜곡</td></tr>
  <tr><td>Adj EPS</td><td>$0.68</td><td>Est $0.16 · Beat</td><td>Adj vs GAAP 괴리</td></tr>
</table>
<p class="small">출처: Calumet 10-Q (기간 종료 2026-06-30) Note/MD&amp;A 세그먼트 매출. 생산: SPS 62.9k / MR 18.1k / PB 2.2k bpd.</p>
<div class="easy"><b>쉽게:</b> 이름표는 “특수제품 회사”지만 Q2 달러는 <b>연료 크랙</b>이 크게 섞여 있다.
특수 핵심(윤활·용제·왁스+브랜드)은 약 $579M(40%), 연료·아스팔트는 약 $866M(60%).
이익의 대부분은 SPS Adj EBITDA $162M에서 나왔다. 재생연료는 아직 이익 기여가 작지만
MaxSAF 완료 후 <b>앞으로의 스토리</b>다.</div>
{gloss([
    ("Adj EBITDA with Tax Attributes", "Adj EBITDA + 청정연료세액공제(CFPC) 노션 가치 조정."),
    ("LIFO", "후입선출 재고. PB는 원가 급등에 $7.3M 타격."),
])}

{compete_html}

<h2>2. 생산 · 손익 품질</h2>
{fig_block(charts['04'], '생산 구성')}
{fig_block(charts['05'], '탑라인 vs GAAP')}
<ul>
  <li>총 생산 83.2k bpd · 판매량 87.7k bpd (-1.2% YoY) — 달러 성장은 가격</li>
  <li>SPS 생산 +12.9% · MR 재생연료 생산 -41.8% (MaxSAF 턴어라운드, ~45만 배럴 손실)</li>
  <li>연결 매출총이익 $18.3M (1.3%) · 영업손실 $40.0M · 영업현금 +$92.3M</li>
  <li>현금 $109.8M + 제한 $40.0M · 총부채 $2,258.7M · 자본 -$1,137.1M</li>
  <li>RIN 유동의무 $480.2M · 유동성 $581.6M (ABL 여유 $431.8M)</li>
  <li>1H 매출 $2,474.9M · Adj EBITDA+Tax $225.3M</li>
</ul>

<h2>3. 전망 · 시나리오</h2>
{fig_block(charts['06'], '전망 포인트')}
{fig_block(charts['07'], '주가 시나리오')}
<table>
  <tr><th>드라이버</th><th>내용</th></tr>
  <tr><td>SPS 마진</td><td>가격 인상 전면 실현 + 중동 갈등으로 Group III 대체 수요. 지속성은 불확실</td></tr>
  <tr><td>MaxSAF 150</td><td>Q2 완료 · 5월 초 재가동 — Q3부터 SAF 믹스·마진 관찰</td></tr>
  <tr><td>RIN / RVO</td><td>2026-27 RVO 사상 최고. GAAP와 Adj 괴리의 핵심</td></tr>
  <tr><td>디레버</td><td>7월 $100M 9.75% 2028 노트 + 몬태나 터미널 $15.5M 상환</td></tr>
  <tr><td>밸류</td><td>${PX:.2f} · PT ${PT:.1f} (H $75 / L $40) · 52주 ${L52:.2f}-${H52:.2f} · 업사이드 {UPSIDE*100:+.1f}%</td></tr>
</table>
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$28-40</td><td>크랙/특수 마진 환원 · RIN 급등 · 레버리지 스트레스</td></tr>
  <tr><td>Base</td><td>$42-54</td><td>SPS 마진 정상화 · SAF 램프 · PT 평균권 — <b>현재가가 이미 상단 위</b></td></tr>
  <tr><td>Bull</td><td>$58-75</td><td>특수 공급부족 지속 · SAF 프리미엄 · PT 고가</td></tr>
</table>

<h2>4. 촉매 · 포트 실행</h2>
{fig_block(charts['08'], '촉매')}
{fig_block(charts['09'], '포지션 맵')}
<div class="box">
<b>OS 메모 (10-05 포폴 · Qual)</b><br/>
<b>미보유</b> · Chase <b>하·과열</b> · 타이밍 GO_A 이나 라벨이 과열이라 <b>본선 AND GO = 0</b>.<br/>
현재 ${PX:.2f} · 컨센서스 PT ${PT:.1f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}-${H52:.2f} (고점 -7.0%).<br/>
실행: <b>추격 금지</b> · 눌림만 관찰. 다음 실적 <b>2026-11-06</b>.<br/>
게이트: SPS 마진 지속 · MaxSAF 가동률 · RIN 의무 · 부채/부의자본.
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>특수제품 본체 + 연료 크랙 달러 + 재생연료 옵션</u>.
Q2 영업은 좋아졌지만 <b>지금 주가·레버리지·과열 라벨</b>이 맞지 않는다. 관망.</div>

<h2>부록 · 출처</h2>
<p class="small">
Calumet Q2 2026 10-Q / Exhibit 99.1 / IR (기간 종료 2026-06-30, 발표 2026-08-07) ·
yfinance 가격·PT ({ASOF}). 피어 믹스·점유는 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 CLMT · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> int:
    charts = {
        "01": chart_business_flow(),
        "02": chart_revenue_mix(),
        "03": chart_ebitda_segments(),
        "04": chart_production(),
        "05": chart_pnl_quality(),
        "06": chart_outlook(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("CLMT", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html = build_html(charts, compete_html=compete_html)
    html, _px = build_and_insert_price("CLMT", CHART_DIR, html)
    if _px.ok:
        print(f"price-charts {_px.candle_path} {_px.momentum_path}")
    else:
        print(f"price-charts SKIP {_px.error}")
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    pdf = HTML(filename=str(OUT_HTML)).write_pdf()
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf)
        print(f"PDF {p} {p.stat().st_size}")
    try:
        from sepa.artifacts import print_release_result, publish_github_release_asset

        tag = "sepa-rev-clmt"
        notes = (
            f"## CLMT 수익구조분석 ({ASOF})\n\n"
            f"Calumet · 특수석유제품 + 재생연료 · Q2'26.\n\n"
            f"- Rev $1.445B (+40.8%) · Adj EBITDA+Tax $175.2M · GAAP NI -$95.9M\n"
            f"- SPS 70.1% ($1,012.5M) / MR 22.8% ($329.0M) / PB 7.1% ($103.6M)\n"
            f"- SPS Adj EBITDA $161.7M (마진 16%) · MaxSAF 150 완료 · 7월 $115M 디레버\n"
            f"- 미보유 · Chase 하·과열 · 업사이드 {UPSIDE*100:+.1f}% "
            f"(PT ${PT:.1f} · px ${PX:.2f})\n"
            f"- 추격 금지 · 다음 실적 2026-11-06\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — CLMT",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
