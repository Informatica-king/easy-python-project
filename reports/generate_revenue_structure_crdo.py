#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(CRDO) — AI 연결(AEC·광학) 매출구조 + 초보용 설명 + WeasyPrint PDF."""

from __future__ import annotations

import base64
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from weasyprint import HTML

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
ASOF = "2026-07-24"
OUT_PDF = [
    Path("/opt/cursor/artifacts/CRDO_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/CRDO_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/CRDO_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/CRDO_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/crdo")
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
        (0.1, 0.7, 1.75, 1.6, "AI GPU\n클러스터", C["sand"]),
        (2.05, 0.7, 1.8, 1.6, "SerDes·DSP\n핵심 IP", C["gold"]),
        (4.05, 0.7, 1.8, 1.6, "AEC 구리\n케이블(현재)", C["teal2"]),
        (6.05, 0.7, 1.75, 1.6, "광학 DSP\n·PIC·ZF", C["teal"]),
        (8.0, 0.7, 1.75, 1.6, "하이퍼스케일\n매출", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("비즈니스 한눈에 — AI 랙 안팎의 초고속 연결을 판다", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    # FY26 growth almost entirely AEC; conceptual mix current vs FY27 guided optical
    sizes = [78, 15, 7]
    labels = ["AEC(구리)\n~지배적", "IC·DSP\n·Retimer", "IP·기타"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["navy"], C["teal"], C["gold"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("FY26 매출 드라이버 (개념)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["AEC\n구리", "광학\n합계", "DSP", "PIC", "ZF\nOptics"]
    # FY27 optical guide >600M total; each bucket >100. Copper continues.
    vals = [0, 600, 100, 100, 100]  # optical breakdown guide mins
    # Better bar: FY27 optical components
    cats = ["광학 DSP", "SiPho PIC", "ZF Optics", "합계"]
    vals = [100, 100, 100, 600]
    colors = [C["teal"], C["teal2"], C["gold"], C["navy"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD (가이던스 하한/합)", fontproperties=PROP)
    ax.set_title("FY27 광학 가이던스 (각 >100, 합 >600)", fontproperties=PROP_B, fontsize=10)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 15, f">{v}+", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 750)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("CRDO — 지금은 AEC, 다음은 광학 ramp", fontproperties=PROP_B, fontsize=13, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_growth() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    years = ["FY23", "FY24", "FY25", "FY26"]
    rev = [184, 193, 437, 1335]
    bars = ax.bar(years, rev, color=[C["sand"], C["gold"], C["teal"], C["navy"]], width=0.55)
    ax.set_title("연간 매출 (백만 USD)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 30, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 1600)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    labels = ["Q1'26", "Q2'26", "Q3'26", "Q4'26"]
    # fiscal quarters ending Jul/Oct/Jan/Apr: from data Apr26=437, Jan26=407, Oct25=268, Jul25=223
    qrev = [223, 268, 407, 437]
    oi = [61, 79, 150, 156]
    x = range(len(labels))
    ax.bar(x, qrev, color=C["teal"], alpha=0.85, label="매출", width=0.5)
    ax2 = ax.twinx()
    ax2.plot(x, oi, "o-", color=C["gold"], lw=2.2, ms=7, label="영업이익")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("매출 (백만)", fontproperties=PROP, color=C["teal"])
    ax2.set_ylabel("영업이익 (백만)", fontproperties=PROP, color=C["gold"])
    ax.set_title("FY26 분기 — 급가속", fontproperties=PROP_B, fontsize=11)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left", fontsize=8)
    ax.spines["top"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "03_growth.png")


def chart_margins() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    years = ["FY23", "FY24", "FY25", "FY26"]
    gm = [57.7, 61.9, 64.8, 68.1]  # approx from GP/Rev: 106/184, 119/193, 283/437, 908/1335
    # recalc precisely
    gm = [round(106.19 / 184.19 * 100, 1), round(119.43 / 192.97 * 100, 1), round(282.91 / 436.77 * 100, 1), round(908.35 / 1335.12 * 100, 1)]
    om = [round(-18.83 / 184.19 * 100, 1), round(-37.06 / 192.97 * 100, 1), round(37.12 / 436.77 * 100, 1), round(445.0 / 1335.12 * 100, 1)]
    ax.plot(years, gm, "o-", color=C["teal"], lw=2.2, ms=8, label="총이익률 %")
    ax.plot(years, om, "s-", color=C["navy"], lw=2.2, ms=8, label="영업이익률 %")
    ax.axhline(0, color=C["muted"], lw=0.8)
    for i, v in enumerate(gm):
        ax.text(i, v + 2, f"{v}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylabel("%", fontproperties=PROP)
    ax.set_title("마진 확장 — 스케일업 + 믹스", fontproperties=PROP_B, fontsize=12)
    ax.legend(prop=PROP, frameon=False)
    ax.set_ylim(-30, 85)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "04_margins.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    rows = [
        (0.5, 3.6, 9.0, 1.0, "TAM — AI/클라우드 데이터센터 연결 (구리+광학)", C["sand"]),
        (1.2, 2.4, 7.6, 1.0, "SAM — 랙내 AEC · 광학 DSP/모듈 · Scale-out", C["gold"]),
        (2.0, 1.2, 6.0, 1.0, "SOM — FY26 $1.3B · FY27 가이던스 +80%+", C["teal"]),
    ]
    for x, y, w, h, t, c in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9.5, color=tc)
    ax.set_title("시장 깔때기 — AI CapEx가 수요의 천장", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "05_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    boxes = [
        (0.1, 0.7, 1.45, 1.6, "① AI\nCapEx", C["sand"]),
        (1.7, 0.7, 1.45, 1.6, "② 하이퍼\n스케일 주문", C["gold"]),
        (3.3, 0.7, 1.45, 1.6, "③ AEC\n볼륨", C["teal2"]),
        (4.9, 0.7, 1.45, 1.6, "④ 광학\nramp", C["teal"]),
        (6.5, 0.7, 1.45, 1.6, "⑤ GM%\n·믹스", C["navy"]),
        (8.1, 0.7, 1.6, 1.6, "⑥ EPS·\n멀티플", C["slate"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8, color=tc)
    ax.set_title("민감도 사슬 — 고객 집중 + AI 투자 사이클", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "06_sensitivity.png")


def chart_scenarios() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    labels = ["Bear", "Base", "Bull"]
    rev = [1800, 2400, 3000]  # FY27 conceptual vs >80% on 1335 => ~2400
    colors = [C["red"], C["teal"], C["gold"]]
    ax = axes[0]
    bars = ax.bar(labels, rev, color=colors, width=0.55)
    ax.set_title("시나리오 FY27 매출 (백만 USD)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 50, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.axhline(1335, color=C["muted"], ls=":", lw=1)
    ax.text(2.05, 1380, "FY26", fontproperties=PROP, fontsize=8, color=C["muted"])
    ax.set_ylim(0, 3600)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    px = [150, 260, 350]
    bars = ax.bar(labels, px, color=colors, width=0.55)
    ax.set_title("시나리오 주가 (USD, 개념)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, px):
        ax.text(b.get_x() + b.get_width() / 2, v + 8, f"${v}", ha="center", fontproperties=PROP, fontsize=9)
    ax.axhline(236.5, color=C["muted"], ls=":", lw=1)
    ax.text(2.05, 245, "현재", fontproperties=PROP, fontsize=8, color=C["muted"])
    ax.set_ylim(0, 420)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("Bear / Base / Bull — 광학 ramp · 고객 집중", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "07_scenarios.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["~4Q전", "~3Q전", "~2Q전", "최근(Q4)"]
    actual = [0.52, 0.67, 1.07, 1.16]
    est = [0.36, 0.50, 0.94, 1.03]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], est, w, label="예상 EPS", color=C["sand"])
    ax.bar([i + w / 2 for i in x], actual, w, label="실제 EPS", color=C["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("EPS (USD)", fontproperties=PROP)
    ax.set_title("실적 서프라이즈 — 연속 Beat", fontproperties=PROP_B, fontsize=12)
    for i, (a, e) in enumerate(zip(actual, est)):
        s = int(round((a - e) / abs(e) * 100))
        ax.text(i + w / 2, a + 0.03, f"+{s}%", ha="center", fontsize=8, fontproperties=PROP, color=C["green"])
    ax.legend(prop=PROP, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "08_eps_surprise.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 2.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.3, 0.55, 2.2, 1.7, "코어\nNEO/ECPG", C["navy"]),
        (2.7, 0.55, 2.1, 1.7, "MU 좌석\n·AMRX", C["teal"]),
        (5.0, 0.55, 2.4, 1.7, "CRDO\n워치\n(ASTH교체)", C["gold"]),
        (7.6, 0.55, 2.0, 1.7, "현금\n버퍼", C["sand"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=tc)
    ax.set_title("포지션 — 07-28 이후 소량($60–80)만 · 추격 금지", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "09_position.png")


def gloss(items: list[tuple[str, str]]) -> str:
    if not items:
        return ""
    lis = "".join(f"<li><span class='term'>{t}</span> — {d}</li>" for t, d in items)
    return f"<div class='gloss'><div class='gloss-title'>이 블록 용어 주석</div><ul>{lis}</ul></div>"


def fig_block(path: Path, caption: str) -> str:
    return f"""
    <figure class="viz">
      <img src="data:image/png;base64,{img_b64(path)}" alt="{caption}"/>
      <figcaption>{caption}</figcaption>
    </figure>
    """


def build_html(charts: dict[str, Path]) -> str:
    css = f"""
    @font-face {{ font-family: 'NanumGothic'; src: url('file://{FONT_REG}'); font-weight: 400; }}
    @font-face {{ font-family: 'NanumGothic'; src: url('file://{FONT_BOLD}'); font-weight: 700; }}
    @page {{
      size: A4; margin: 16mm 14mm 18mm 14mm;
      @bottom-center {{
        content: "수익구조분석(CRDO) · {ASOF} · " counter(page) " / " counter(pages);
        font-family: NanumGothic; font-size: 8.5pt; color: #78716c;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: NanumGothic, sans-serif; color: #1c1917; font-size: 10pt; line-height: 1.55; }}
    h1 {{ font-size: 20pt; font-weight: 700; margin: 0 0 4px; color: #1e3a5f; }}
    h2 {{ font-size: 13.5pt; font-weight: 700; margin: 22px 0 8px; padding-bottom: 4px;
         border-bottom: 2px solid #1e3a5f; color: #1e3a5f; page-break-after: avoid; }}
    h3 {{ font-size: 11pt; font-weight: 700; margin: 12px 0 6px; color: #0f766e; }}
    .hero {{
      background: linear-gradient(135deg, #1e3a5f 0%, #0f766e 55%, #b8860b 125%);
      color: #fff; padding: 18px; border-radius: 6px; margin-bottom: 16px;
    }}
    .hero h1 {{ color: #fff; }}
    .hero .oneline {{ font-size: 12pt; margin-top: 8px; line-height: 1.45; }}
    .kpi {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .kpi span {{ background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 4px; font-size: 8.5pt; }}
    .block {{ page-break-inside: avoid; margin-bottom: 6px; }}
    p {{ margin: 0 0 8px; }}
    ul {{ margin: 4px 0 10px 18px; padding: 0; }}
    li {{ margin-bottom: 3px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0 12px; font-size: 9pt; }}
    th, td {{ border: 1px solid #d6d3d1; padding: 5px 7px; text-align: left; vertical-align: top; }}
    th {{ background: #1e3a5f; color: #fff; font-weight: 700; }}
    tr:nth-child(even) td {{ background: #f0fdfa; }}
    .viz {{ margin: 8px 0 12px; text-align: center; }}
    .viz img {{ max-width: 100%; height: auto; }}
    .viz figcaption {{ font-size: 8.5pt; color: #57534e; margin-top: 4px; }}
    .callout {{ background: #f7f3eb; border-left: 4px solid #b8860b; padding: 8px 12px; margin: 8px 0 12px; font-size: 9.5pt; }}
    .gloss {{ background: #fafaf9; border: 1px solid #e7e5e4; padding: 8px 12px; margin: 6px 0 14px; font-size: 8.5pt; color: #44403c; }}
    .gloss-title {{ font-weight: 700; color: #0f766e; margin-bottom: 4px; font-size: 9pt; }}
    .gloss ul {{ margin: 0 0 0 14px; }}
    .gloss .term {{ font-weight: 700; color: #1e3a5f; }}
    .plain {{ background: #eff6ff; border: 1px solid #bfdbfe; padding: 8px 12px; margin: 6px 0 10px; font-size: 9.5pt; }}
    .plain strong {{ color: #1e3a5f; }}
    .warn {{ background: #fff1f2; border-left: 4px solid #9f1239; padding: 8px 12px; margin: 8px 0; font-size: 9.5pt; }}
    .footer-note {{ font-size: 8pt; color: #78716c; margin-top: 18px; border-top: 1px solid #e7e5e4; padding-top: 8px; }}
    """

    c0 = fig_block(charts["flow"], "그림 0. 비즈니스 흐름 — SerDes → AEC/광학 → 하이퍼스케일")
    c1 = fig_block(charts["mix"], "그림 1. FY26 드라이버 vs FY27 광학 가이던스")
    c2 = fig_block(charts["growth"], "그림 2. 연간·분기 매출 가속")
    c3 = fig_block(charts["margins"], "그림 3. 총이익·영업이익률")
    c4 = fig_block(charts["funnel"], "그림 4. TAM→SAM→SOM")
    c5 = fig_block(charts["sens"], "그림 5. 민감도 사슬")
    c6 = fig_block(charts["scen"], "그림 6. Bear/Base/Bull")
    c7 = fig_block(charts["eps"], "그림 7. EPS 서프라이즈")
    c8 = fig_block(charts["pos"], "그림 8. 포트폴리오에서의 CRDO")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"/><title>수익구조분석 — CRDO (Credo)</title>
<style>{css}</style></head>
<body>

<div class="hero">
  <h1>수익구조분석 · CRDO</h1>
  <div>Credo Technology Group Holding Ltd · 나스닥 · AI 데이터센터 초고속 연결</div>
  <div class="oneline">
    <strong>한 줄 구조:</strong> FY26 매출 <em>$1.33B(+206%)</em>의 거의 전부가
    하이퍼스케일향 <strong>ZeroFlap AEC(구리 활성전기케이블)</strong> 볼륨이고,
    FY27은 광학(DSP·SiPho PIC·ZF Optics)이 <strong>$600M+</strong>로 ramp하며
    성장을 이을 계획입니다. 마진은 GM ~68%, 고객은 <strong>상위 10곳이 ~90%</strong>.
  </div>
  <div class="kpi">
    <span>종가 ~$236.5</span>
    <span>시총 ~$44B</span>
    <span>PT $184 / $279 / $350</span>
    <span>FY26 매출 $1.33B (+206%)</span>
    <span>GM 68.1% · OM ~33%</span>
    <span>Q1'27 가이던스 $465–475M</span>
    <span>실적 09-02</span>
    <span>기준일 {ASOF}</span>
  </div>
</div>

<div class="plain">
  <strong>읽는 법:</strong> “무엇을 파는지(AEC→광학) → 누구에게(하이퍼스케일) →
  마진·가이던스 → 집중 리스크 → 비중” 순입니다.
  ASTH 손절 대금의 <em>교체 후보</em>이나, <strong>07-28 NEO 전 매수 금지 · 소량만</strong>.
</div>

{c0}

<div class="block">
<h2>1. 수익 구조 — 제품·고객·마진</h2>
<div class="plain">
  <strong>쉽게:</strong> AI 서버 선반을 구리 케이블(AEC)로 튼튼히 잇는 회사입니다.
  멀리 갈 때는 광학(빛) 칩·모듈로 확장 중이고, 지금은 구리가 돈을 벌고 광학이 내년 성장 스토리입니다.
</div>
{c1}
{c2}

<h3>1-1. 제품 축</h3>
<table>
  <tr><th>축</th><th>역할</th><th>현황</th></tr>
  <tr>
    <td><strong>ZeroFlap AEC</strong></td>
    <td>랙내·수 m 구리 활성케이블 (100G–1.6T)</td>
    <td>FY26 성장의 <strong>~99%</strong>를 설명. 하이퍼스케일·NeoCloud</td>
  </tr>
  <tr>
    <td>광학 PAM4 DSP</td>
    <td>광모듈용 신호처리 (Robin 100G / Cardinal 200G)</td>
    <td>FY27 각 축 &gt;$100M 목표의 하나</td>
  </tr>
  <tr>
    <td>SiPho PIC (Dust)</td>
    <td>실리콘 포토닉스 · 레이저 수 감소</td>
    <td>Dust Photonics 인수. CPO/NPO는 FY28 초기 매출 언급</td>
  </tr>
  <tr>
    <td>ZeroFlap Optics</td>
    <td>신뢰성·텔레메트리 강조 광모듈</td>
    <td>FY27 &gt;$100M. PILOT 소프트웨어와 결합</td>
  </tr>
  <tr>
    <td>기타</td>
    <td>PCIe Retimer, SerDes Chiplet, OmniConnect, IP</td>
    <td>중장기. OmniConnect/ALC는 FY28 벡터</td>
  </tr>
</table>

{c3}

<h3>1-2. 연간 손익 (백만 USD, FY 종료 4/30)</h3>
<table>
  <tr><th>연도</th><th>매출</th><th>총이익</th><th>영업이익</th><th>순이익</th></tr>
  <tr><td>FY2023</td><td>$184</td><td>$106</td><td>−$19</td><td>−$17</td></tr>
  <tr><td>FY2024</td><td>$193</td><td>$119</td><td>−$37</td><td>−$28</td></tr>
  <tr><td>FY2025</td><td>$437</td><td>$283</td><td>$37</td><td>$52</td></tr>
  <tr><td>FY2026</td><td><strong>$1,335</strong></td><td>$908</td><td>$445</td><td>$472</td></tr>
</table>

<div class="callout">
  <strong>가이던스:</strong> Q1 FY27 매출 <strong>$465–475M</strong> · non-GAAP GM 67–69%.
  FY27 전체 매출 성장 <strong>+80%+</strong>, 광학 합계 <strong>$600M+</strong>
  (DSP·PIC·ZF Optics 각 &gt;$100M). OpEx는 매출보다 느리게(~+50%) 증가 전망.
</div>

<p>
고객: 상위 10곳 ≈ <strong>매출의 90%</strong>, Q4에 국내 대형 4곳이 각 ≥10%.
팹리스 — 웨이퍼 <strong>TSMC</strong> 의존. 현금 Q4 말 ~$1.4B(인수 전 기준 언급).
</p>

{gloss([
    ("AEC", "Active Electrical Cable. 구리 케이블에 칩을 넣어 고속·저전력·고신뢰 전송."),
    ("ZeroFlap", "링크 끊김(flap)을 줄이는 Credo 브랜드/아키텍처·텔레메트리."),
    ("SerDes / DSP", "직렬화·역직렬화 / 디지털 신호처리. 고속 연결의 핵심 IP."),
    ("SiPho PIC", "실리콘 포토닉스 광집적회로. Dust 인수로 확보."),
    ("NeoCloud", "AI 특화 클라우드/인프라 사업자."),
    ("CPO / NPO", "패키지/보드에 가까운 광학 실장. 장기 로드맵."),
])}
</div>

<div class="block">
<h2>2. 시장 깔때기</h2>
{c4}
<table>
  <tr><th>단계</th><th>내용</th><th>주의</th></tr>
  <tr><td>TAM</td><td>AI 클러스터 연결(구리+광학)</td><td>CapEx 사이클에 연동</td></tr>
  <tr><td>SAM</td><td>랙내 AEC · 광학 DSP/모듈</td><td>MRVL·동급 경쟁</td></tr>
  <tr><td>SOM</td><td>FY26 $1.3B → FY27 +80% 가정</td><td>고객 소수에 집중</td></tr>
</table>
</div>

<div class="block">
<h2>3. 민감도 사슬</h2>
{c5}
<table>
  <tr><th>단계</th><th>좋게</th><th>나쁘게</th></tr>
  <tr><td>① AI CapEx</td><td>지속 확장</td><td>예산 동결</td></tr>
  <tr><td>② 소수 고객 주문</td><td>다수 ≥10% 유지</td><td>1–2곳 발주 공백</td></tr>
  <tr><td>③ AEC</td><td>200G/lane 전환</td><td>가격·점유 압력</td></tr>
  <tr><td>④ 광학 ramp</td><td>$600M+ 달성</td><td>지연·믹스 악화</td></tr>
  <tr><td>⑤ GM</td><td>~67–69% 유지</td><td>관세·원가·믹스</td></tr>
</table>
{c7}
</div>

<div class="block">
<h2>4. Bear / Base / Bull</h2>
{c6}
<table>
  <tr><th>시나리오</th><th>가정</th><th>매출(FY27)</th><th>주가 함의</th></tr>
  <tr><td>Bear</td><td>광학 지연·고객 공백·멀티플 압축</td><td>~$1.8B</td><td>$150–190 (PT 저점)</td></tr>
  <tr><td>Base</td><td>+80% 가이던스 근처, GM 유지</td><td>~$2.4B</td><td>$240–290 (PT 평균~$279)</td></tr>
  <tr><td>Bull</td><td>광학 초과·점유 확대</td><td>~$3.0B+</td><td>$320–350+</td></tr>
</table>
<p>
현재 ~$236 vs PT 평균 ~$279(<strong>+18%</strong>). Forward PE ~26대로 “성장은 반영, 실패는 비쌈”.
시총~$44B는 소액 포트에서 <strong>추격 매수 금물</strong>.
</p>
</div>

<div class="block">
<h2>5. 경쟁·리스크</h2>
<table>
  <tr><th>전선</th><th>CRDO</th><th>압력</th></tr>
  <tr><td>AEC/연결</td><td>ZeroFlap 리더십 주장</td><td>대형 반도체·케이블 경쟁</td></tr>
  <tr><td>광학</td><td>DSP+PIC+모듈 수직화</td><td>기존 광모듈·DSP 강자</td></tr>
  <tr><td>고객</td><td>하이퍼스케일 밀착</td><td><strong>상위 10≈90%</strong></td></tr>
  <tr><td>공급</td><td>팹리스</td><td>TSMC·OSAT 집중</td></tr>
</table>
</div>

<div class="block">
<h2>6. 선행 지표</h2>
<ul>
  <li>Q1 FY27 실적 vs 가이던스 $465–475M · GM</li>
  <li>광학 매출 run-rate · Dust 통합</li>
  <li>≥10% 고객 수·NeoCloud 비중</li>
  <li>재고·공급망 · 관세 코멘트</li>
  <li><strong>09-02</strong> 실적</li>
</ul>
</div>

<div class="block">
<h2>7. 비중 · Thesis Breakers</h2>
{c8}
<div class="plain">
  <strong>포트:</strong> ASTH 매도대금 교체 후보. <strong>07-28 NEO 실적 후</strong> · 사이즈 <strong>$60–80</strong> 한도.
  AMAT와 둘 중 하나 또는 분할. SLS 바이너리와 혼동 금지.
</div>
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>지금</td><td>매수 금지 (NEO D-4 · no_add)</td></tr>
  <tr><td>진입</td><td>07-28 후 눌림·가이던스 확인 시 소량</td></tr>
  <tr><td>손절(워치)</td><td>~$190 (설정 stop)</td></tr>
  <tr><td>익절 참고</td><td>tp1~$279 / tp2~$320</td></tr>
</table>
<div class="warn">
  <strong>Thesis Breakers:</strong> 하이퍼스케일 발주 공백 · 광학 ramp 실패 · GM 급락 ·
  AI CapEx 둔화 · 경쟁 가격전쟁.
</div>
</div>

<div class="block">
<h2>8. 한계 · 출처</h2>
<ul>
  <li>재무·가격: Yahoo Finance / yfinance.</li>
  <li>제품·고객·가이던스: Credo FY26 10-K · Q4 FY26 실적콜 (2026-06-01).</li>
  <li>시나리오·믹스 %는 작업용. 투자 권고 아님.</li>
</ul>
<div class="footer-note">
  생성: 수익구조분석() · 티커 CRDO · 기준 {ASOF} · WeasyPrint + NanumGothic
</div>
</div>

</body></html>
"""
    return html


def main() -> None:
    charts = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "growth": chart_growth(),
        "margins": chart_margins(),
        "funnel": chart_tam_funnel(),
        "sens": chart_sensitivity(),
        "scen": chart_scenarios(),
        "eps": chart_eps_surprise(),
        "pos": chart_position(),
    }
    html = build_html(charts)
    OUT_HTML.write_text(html, encoding="utf-8")
    print("HTML", OUT_HTML, OUT_HTML.stat().st_size)
    for out in OUT_PDF:
        out.parent.mkdir(parents=True, exist_ok=True)
        HTML(string=html, base_url=str(CHART_DIR)).write_pdf(out)
        print("PDF", out, out.stat().st_size)


if __name__ == "__main__":
    main()
