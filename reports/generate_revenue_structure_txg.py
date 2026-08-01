#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(TXG) — 10x Genomics 소모품·장비 + 경쟁점유/믹스 + WeasyPrint PDF."""

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
PX = 47.27
PT = 41.54
H52 = 50.34
UPSIDE = PT / PX - 1.0
EARN = "08-06"
OUT_PDF = [
    Path("/opt/cursor/artifacts/TXG_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/TXG_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/TXG_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/TXG_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/txg")
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
    "txg": "#0f766e",
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
        (0.1, 0.7, 1.75, 1.6, "연구소·바이오\n파마 고객", C["sand"]),
        (2.05, 0.7, 1.8, 1.6, "장비 설치\n(Instruments)", C["gold"]),
        (4.05, 0.7, 1.85, 1.6, "시약·칩\nConsumables", C["teal2"]),
        (6.1, 0.7, 1.75, 1.6, "단일세포\n·공간전사체", C["teal"]),
        (8.05, 0.7, 1.7, 1.6, "반복 매출\n+서비스", C["navy"]),
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
                fontproperties=PROP_B, fontsize=8.5, color=tc)
    for x in (1.95, 3.95, 5.95, 7.9):
        ax.annotate(
            "", xy=(x + 0.08, 1.5), xytext=(x - 0.08, 1.5),
            arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6),
        )
    ax.set_title("비즈니스 한눈에 — 장비 깔고, 시약·칩을 반복 판매",
                 fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [129.8, 11.3, 8.8, 0.9]
    labels = ["Consumables\n129.8M (86%)", "Instruments\n11.3M (7%)",
              "Services\n8.8M (6%)", "License\n0.9M"]
    ax.pie(
        sizes, labels=labels,
        colors=[C["teal"], C["gold"], C["navy"], C["sand"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=7.5),
    )
    ax.set_title("매출 유형 (Q1'26, 총 150.8M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["SC\nConsum.", "Spatial\nConsum.", "SC\nInstr.", "Spatial\nInstr."]
    vals = [88.9, 40.9, 5.2, 6.0]
    colors = [C["navy"], C["teal"], C["gold"], C["sand"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("제품 라인 상세 (Q1'26)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}",
                ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_growth_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    cats = ["Consum.\nYoY", "SC Cons.\nYoY", "Spatial\nCons. YoY",
            "Instruments\nYoY", "Reported\nTotal YoY", "Ex-license\nYoY"]
    vals = [13, 6, 31, -24, -3, 9]
    colors = [C["green"] if v >= 0 else C["red"] for v in vals]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("성장 브리지 — 소모품 강·장비 약·라이선스 기저효과",
                 fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (1.5 if v >= 0 else -3.5),
                f"{v:+d}%", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)
    fig.tight_layout()
    return save_fig(fig, "03_growth_bridge.png")


def chart_razor_blade() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.3, 0.6, 2.8, 1.8, "1. 장비 판매\n(낮은/마이너스 성장)", C["gold"]),
        (3.6, 0.6, 2.8, 1.8, "2. 설치 기반(IB)\n연구소에 기기 확보", C["teal2"]),
        (6.9, 0.6, 2.8, 1.8, "3. 소모품 반복\n=매출·마진 핵심", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                           facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["gold"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=9, color=tc)
    ax.set_title("레이저-블레이드 모델 — 장비는 문, 소모품이 본업",
                 fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "04_razor_blade.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    qs = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [154.9, 172.9, 149.0, 166.0, 150.8]
    colors = [C["slate"]] * 4 + [C["teal"]]
    bars = ax.bar(qs, rev, color=colors, width=0.55)
    ax.set_ylabel("매출 (백만 USD)", fontproperties=PROP)
    ax.set_title("분기 매출 — 라이선스 기저 제거 후 핵심은 완만 성장",
                 fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.axhline(150, color=C["gold"], ls="--", lw=1, alpha=0.7)
    ax.set_ylim(0, 200)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "05_quarterly.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    qs = ["Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    actual = [0.48, -0.02, 0.07, 0.07]
    colors = [C["green"] if a >= 0 else C["teal"] for a in actual]
    bars = ax.bar(qs, actual, color=colors, width=0.55)
    ax.axhline(0, color=C["ink"], lw=0.8)
    ax.set_ylabel("Non-GAAP EPS (근사)", fontproperties=PROP)
    ax.set_title("최근 4분기 EPS — 컨센서스 대비 연속 Beat",
                 fontproperties=PROP_B, fontsize=11)
    notes = ["+대형Beat", "Beat(소폭)", "Beat", "Beat"]
    for b, a, n in zip(bars, actual, notes):
        ax.text(b.get_x() + b.get_width() / 2, a + (0.04 if a >= 0 else -0.06),
                f"{a:.2f}\n{n}", ha="center", fontproperties=PROP, fontsize=7.5)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "06_eps_surprise.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [22, 32, 42]
    highs = [32, 42, 55]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    ax.axvline(PX, color=C["gold"], ls="--", lw=1.5)
    ax.text(PX + 0.3, 2.35, f"현재 ~{PX:.1f}", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.axvline(PT, color="#2563eb", ls=":", lw=1.2)
    ax.text(PT + 0.3, -0.55, f"PT평균 ~{PT:.1f}", fontproperties=PROP, fontsize=7.5, color="#2563eb")
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        mid = (lo + hi) / 2
        ax.text(mid, i, f"{lo}–{hi}", ha="center", va="center",
                color="white", fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(15, 60)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear — 현재는 PT 대비 프리미엄",
                 fontproperties=PROP_B, fontsize=11)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP_B)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    cats = ["가이드\n하단 600", "가이드\n중단 612", "가이드\n상단 625", "Q1런레이트\n~603"]
    vals = [600, 612, 625, 603]
    bars = ax.bar(cats, vals, color=[C["slate"], C["teal"], C["navy"], C["gold"]], width=0.55)
    ax.set_ylabel("연간 매출 (백만 USD)", fontproperties=PROP)
    ax.set_title("FY26 가이던스 600–625M vs Q1 런레이트",
                 fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 3, f"{v}",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(560, 650)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "08_sensitivity.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, EARN, "실적", "Q2 소모품\n장비·가이드", C["teal"]),
        (0.28, "Atera", "촉매", "공간 전장\nH2 출하", C["navy"]),
        (0.52, "Spatial", "성장", "소모품 +31%\n모멘텀 유지?", C["gold"]),
        (0.76, "밸류", "리스크", f"PT {UPSIDE*100:+.0f}%\n고점권", C["red"]),
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
    ax.set_title(f"촉매 — {EARN} 실적 · Atera · Spatial · 밸류",
                 fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "09_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    rows = [
        (0.3, 2.6, 9.4, 1.0, C["red"], "white",
         f"포트 적합도: 낮음 — PT 프리미엄({UPSIDE*100:+.0f}%) · 52주고점권 · Chase 하·과열"),
        (0.3, 1.4, 4.5, 0.95, C["gold"], C["ink"], f"실적 {EARN}\nEARN_D5 관전"),
        (5.0, 1.4, 4.7, 0.95, C["slate"], "white", "오늘 배분\n편입 없음"),
        (0.3, 0.25, 9.4, 0.95, C["sand"], C["ink"],
         "관심만: Atera·소모품 확인 후 · 코어(ECPG/AMRX)·SCHD와 예산 경쟁 금지"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=1.5,
            )
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=9, color=tc)
    ax.set_title("실행 포지션 맵 (사용자 계좌 기준)", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "10_position.png")


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
<div class="easy"><b>쉽게:</b> TXG는 <b>단일세포·공간전사체</b> 툴 피어셋에서 선두 성격이다.
Illumina는 NGS 전체 스케일이 커서 SC 전용 점유와 다르다 — 순위·Δpp 감각용.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>
{gloss([
    ("Single Cell", "세포 단위 유전자 발현 분석 — Chromium 계열."),
    ("Spatial", "조직 내 위치까지 보는 전사체 — Xenium·Atera."),
])}

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> TXG 매출의 약 <b>86%가 소모품</b>이다. 장비는 ‘문’, 시약·칩이 본업.
피어(ILMN/TECH/TWST)도 소모품 편중이 크고, PACB만 장비 비중이 상대적으로 높다.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
{gloss([
    ("Consumables", "칩·시약·키트 — 고마진·반복 매출."),
    ("Instruments", "분석 장비 — 신규 설치·교체."),
    ("Installed base", "설치 대수. 소모품 수요의 기반."),
])}
"""


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"TXG 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0f766e; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0f766e; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#f0f7f6 0%,#e8eef5 55%,#f7f3e8 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#dbeafe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecaca; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#f0fdfa; border-left:4px solid #0f766e; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0f766e; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#0f766e; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>TXG 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>TXG 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">10x Genomics · 단일세포 · 공간전사체 (Spatial)</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1'26(종료 2026-03-31) · 다음 실적 {EARN} · 시총 ~$6.0B</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.2f}</div><div class="s">52주고 ${H52:.2f}</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.1f}</div><div class="s">{UPSIDE*100:+.1f}%</div></span>
    <span class="kpi"><div class="l">Q1 매출</div><div class="v">$150.8M</div><div class="s">ex-lic +9% YoY</div></span>
    <span class="kpi"><div class="l">소모품 비중</div><div class="v">86%</div><div class="s">Spatial +31%</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag bad">Chase 하·과열</span>
    <span class="tag warn">PT 프리미엄 · 고점권</span>
    <span class="tag warn">실적 {EARN} · EARN_D5</span>
    <span class="tag bad">오늘 포트 편입 비추천</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>장비(문) + 소모품(본업) 레이저-블레이드.</b> Q1 매출 150.8M — 보고 YoY −3%이나,
작년 일회성 라이선스(~16.8M) 제외 시 <b>핵심 +9%</b>. 소모품 +13%(Spatial +31%), 장비 −24%.
FY26 가이드 600–625M. <b>Atera</b> 신제품이 중기 촉매.
다만 주가는 52주 고점·PT 대비 프리미엄({UPSIDE*100:+.0f}%) → <b>Chase 하·과열 · 오늘 배분 없음</b>.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 연구소에 ‘분석 기계’를 팔고, 그 기계에 넣는 ‘시약·칩’을 계속 팔아 돈을 번다. 면도기와 면도날 모델.</div>
{gloss([
    ("Single Cell (단일세포)", "세포 하나하나를 따로 읽어 유전자 발현을 보는 분석."),
    ("Spatial (공간전사체)", "조직에서 ‘어디서’ 어떤 유전자가 켜졌는지 위치까지 보는 기술."),
    ("Chromium / Xenium", "10x의 대표 단일세포·공간 플랫폼 브랜드."),
    ("Atera", "2026 출시 공간 전장전사체 신플랫폼 — 경영진이 ‘역사상 최대 제품’으로 언급."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '유형·제품 믹스')}
<table>
  <tr><th>구분 (Q1'26)</th><th>매출</th><th>비중</th><th>YoY</th></tr>
  <tr><td>Consumables — Single Cell</td><td>88.9M</td><td>59%</td><td>+6%</td></tr>
  <tr><td>Consumables — Spatial</td><td>40.9M</td><td>27%</td><td>+31%</td></tr>
  <tr><td><b>Consumables 합계</b></td><td><b>129.8M</b></td><td><b>86%</b></td><td><b>+13%</b></td></tr>
  <tr><td>Instruments — Single Cell</td><td>5.2M</td><td>3%</td><td>−12%</td></tr>
  <tr><td>Instruments — Spatial</td><td>6.0M</td><td>4%</td><td>−32%</td></tr>
  <tr><td>Instruments 합계</td><td>11.3M</td><td>7%</td><td>−24%</td></tr>
  <tr><td>Services</td><td>8.8M</td><td>6%</td><td>+15%</td></tr>
  <tr><td>License &amp; royalty</td><td>0.9M</td><td>&lt;1%</td><td>급감(기저)</td></tr>
  <tr><td><b>총매출</b></td><td><b>150.8M</b></td><td>100%</td><td>−3% / <b>ex-lic +9%</b></td></tr>
</table>
{fig_block(charts['04'], '레이저-블레이드')}
<div class="easy"><b>쉽게:</b> 지금 돈의 86%는 소모품. 장비 매출이 줄어도, 이미 깔린 기계가 시약을 계속 사게 만드는 구조가 핵심이다.</div>
{gloss([
    ("Consumables", "칩·시약·키트 등 실험마다 쓰는 소모품 — 고마진·반복 매출."),
    ("Instruments", "Chromium·Xenium 등 분석 장비 — 신규 설치·교체 수요."),
    ("Installed base (IB)", "고객 현장에 설치된 장비 대수. 소모품 수요의 기반."),
    ("License & royalty", "특허 소송 합의 등 라이선스 수입 — 2025에 일회성 크게 잡힘."),
])}

{compete_html}

<h2>2. 성장·둔화의 구조</h2>
{fig_block(charts['03'], '성장 브리지')}
<ul>
  <li><b>Spatial 소모품 +31%</b> — Xenium 모멘텀이 성장 엔진</li>
  <li>Single Cell 소모품 +6% · 반응(reaction) 볼륨은 두 자릿수↑ (ASP/믹스 영향)</li>
  <li>장비 −24% — 신규 캐펙스/구매 사이클 약함 → 단기 톱라인 부담</li>
  <li>보고 −3%는 <b>작년 라이선스 16.8M 기저</b> 효과가 큼</li>
</ul>
{gloss([
    ("Reaction volume", "소모품으로 돌린 실험 반응 수 — 사용량 지표."),
    ("ASP/믹스", "제품 구성·할인에 따른 평균판매가 변화."),
    ("기저효과", "작년 일회성 매출이 커서 올해 성장률이 낮아 보이는 현상."),
])}

<h2>3. 분기 궤적 · FY 가이드</h2>
{fig_block(charts['05'], '분기 매출')}
{fig_block(charts['08'], 'FY26 가이드')}
<p>FY26 매출 가이던스 <b>600–625M</b> (2025 일회성 라이선스 제외 시 약 0–4% 성장).
Q1 런레이트(~603M)는 가이드 하단 근처 — <b>상단 달성엔 하반기(Atera 등) 필요</b>.</p>
<div class="box"><b>촉매:</b> Atera(공간 전장전사체) 출시·H2 초기 출하. 중기적으로 Spatial IB·소모품 확장 스토리.</div>
{gloss([
    ("가이던스", "회사가 제시하는 연간 매출 전망 구간."),
    ("런레이트", "현재 분기 매출×4로 연환산한 속도."),
])}

<h2>4. 수익성 · 서프라이즈</h2>
{fig_block(charts['06'], 'EPS')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>Q1 매출총이익률</td><td>~70% (전년 ~68%)</td></tr>
  <tr><td>영업이익</td><td>여전히 적자 구간 (개선 중)</td></tr>
  <tr><td>EPS</td><td>최근 4Q 컨센서스 대비 Beat 기조</td></tr>
  <tr><td>다음 실적</td><td><b>2026-{EARN}</b></td></tr>
  <tr><td>현재가 / PT</td><td>~{PX:.1f} / 평균 ~{PT:.1f} · 고 ~{H52:.1f}</td></tr>
  <tr><td>시총</td><td>~6.0B</td></tr>
</table>
{gloss([
    ("Gross margin", "매출총이익률 — 소모품 비중이 높을수록 유리한 편."),
    ("Beat", "컨센서스보다 좋은 EPS/매출."),
])}

<h2>5. 시나리오 · Breaker · 촉매</h2>
{fig_block(charts['07'], '주가 시나리오')}
{fig_block(charts['09'], '촉매')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>42–55</td><td>Atera 조기 기여 · 가이드 상향 · PT 재상향</td></tr>
  <tr><td>Base</td><td>32–42</td><td>가이드 유지 · PT 평균대 회귀</td></tr>
  <tr><td>Bear</td><td>22–32</td><td>학술/바이오 예산 둔화 · 장비 부진 지속 · 가이드 컷</td></tr>
</table>
<p><b>Breaker:</b> FY 가이드 하향 · Spatial 성장 둔화 · Atera 출하/수요 미스 · 경쟁(공간·단일세포) 심화</p>

<h2>6. 포트폴리오 위치</h2>
{fig_block(charts['10'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>오늘 최종 배분</td><td><b>편입 없음</b> (코어 ECPG/AMRX · SCHD 우선)</td></tr>
  <tr><td>이유</td><td>52주 고점 근접 · PT 프리미엄({UPSIDE*100:+.0f}%) · Chase 하·과열 · EARN_D5</td></tr>
  <tr><td>관전 포인트</td><td>{EARN} 실적 · Atera 초기 반응 · 소모품 YoY 유지 여부</td></tr>
  <tr><td>관심 재진입 힌트</td><td>PT 평균(~{PT:.0f}) 하회 또는 실적 후 A′/B 셋업 + 가이드 상향</td></tr>
</table>
<div class="box">
<b>계좌 기준 실행</b><br/>
· 역할: 심층 <b>Chase 하·과열</b> · 코어/위성 우선순위 낮음<br/>
· 가격: ~${PX:.2f} · PT~${PT:.1f} · <b>업사이드 {UPSIDE*100:+.1f}% · 고점권</b> → 추격 금지<br/>
· 트리거: <b>{EARN}</b> Q2에서 소모품·장비·가이드·Atera 확인 후 재평가<br/>
· A′/B: 실적창이라 신규 게이트 모두 0 — 소화 후 재스캔
</div>
<div class="easy"><b>한줄 결론:</b> 사업은 ‘소모품 반복’이 건강하고 Spatial이 성장축이다.
다만 <u>가격이 이미 앞서가</u> 당신 시드(코어·SCHD·실적창)와는 지금 충돌한다. 수익구조 공부는 OK, 매수는 대기.</div>

<h2>부록 · 출처</h2>
<p class="small">
10x Genomics Q1 2026 earnings release (2026-05-07, SEC Exhibit 99.1) · earnings call 요약 ·
Yahoo/yfinance 가격·PT·분기 매출 ({ASOF}). 피어 믹스·점유는 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 TXG · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_growth_bridge(),
        "04": chart_razor_blade(),
        "05": chart_quarterly(),
        "06": chart_eps_surprise(),
        "07": chart_scenarios(),
        "08": chart_sensitivity(),
        "09": chart_catalysts(),
        "10": chart_position(),
    }
    bundle, cpaths = build_compete_charts("TXG", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html = build_html(charts, compete_html=compete_html)
    html, _px = build_and_insert_price("TXG", CHART_DIR, html)
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
    print(f"TXG rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% earn={EARN} compete={bundle is not None}")


if __name__ == "__main__":
    main()
