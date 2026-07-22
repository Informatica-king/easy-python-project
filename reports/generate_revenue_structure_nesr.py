#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(NESR) — 시각자료 + 초보용 설명 + 전문용어 주석 + WeasyPrint PDF."""

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
ASOF = "2026-07-20"
OUT_PDF = [
    Path("/opt/cursor/artifacts/NESR_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/NESR_Revenue_Structure_Analysis.pdf"),
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
        (2.05, 0.65, 1.8, 1.55, "시추·평가\n서비스", C["sandstone"]),
        (4.05, 0.65, 1.85, 1.55, "생산\n(프랙·시멘트\n등)", C["teal2"]),
        (6.1, 0.65, 1.75, 1.55, "가동률\n·계약", C["teal"]),
        (8.1, 0.65, 1.65, 1.55, "매출\n·마진", C["oil"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["desert"], C["sandstone"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("비즈니스 한눈에 — 중동 유전에서 장비·인력 서비스를 판다", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [241, 164]
    labels = ["Production\n241M (60%)", "Drilling &\nEvaluation\n164M (40%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["teal"], C["sandstone"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("세그먼트 매출 (Q1'26, 총 405M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    sizes = [99.75, 0.25]
    labels = ["MENA\n99.75%", "Rest of\nWorld 0.25%"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["oil"], C["desert"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("지역 매출 (Q1'26)", fontproperties=PROP_B, fontsize=11)
    fig.suptitle("NESR 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    return save_fig(fig, "02_segment_geo.png")


def chart_segment_oi() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    cats = ["Production\n매출", "D&E\n매출", "Production\n영업이익", "D&E\n영업이익", "미배분\n비용", "연결\n영업이익"]
    # Q1'26: rev 241/164, OI 32.7/18.2, unalloc -14.9, total OI 36.0
    vals = [241, 164, 32.7, 18.2, -14.9, 36.0]
    colors = [C["teal"], C["sandstone"], C["teal2"], C["gold"], C["red"], C["oil"]]
    x = range(len(cats))
    for i, (v, c) in enumerate(zip(vals, colors)):
        ax.bar(i, v, color=c, width=0.55)
        ax.text(i, v + (8 if v >= 0 else -18), f"{v}", ha="center", fontproperties=PROP, fontsize=8)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(cats, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("Q1'26 세그먼트 매출·영업이익 브리지", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "03_segment_bridge.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    layers = [
        (9.2, 8.3, "TAM — 글로벌 OFS", "전 세계 오일필드 서비스 (장비·인력·시추지원)", C["desert"]),
        (7.6, 6.2, "SAM — MENA OFS ≈ 30–40B", "중동·북아프리카 유전 서비스 시장 (근사)", C["sandstone"]),
        (5.8, 4.1, "SOM — NESR 매출 ~1.3B+", "FY25 ~1.32B · Q1'26 연환산 런레이트 상승 중", C["teal2"]),
        (4.2, 2.0, "성장 스토리", "Jafurah 등 대형 계약 · 장기 목표 경로 ~3B (경영 비전)", C["teal"]),
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
    ax.set_title("시장 깔때기 — MENA 오일필드 서비스에서 NESR의 자리", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "04_tam_funnel.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    steps = [
        "NOC\nCAPEX",
        "수주·\n백로그",
        "가동률\n·가동일",
        "가격\n·믹스",
        "원가\n(인건·장비)",
        "마진",
        "EPS",
    ]
    xs = list(range(len(steps)))
    ys = [1.0, 0.94, 0.88, 0.86, 0.78, 0.72, 0.66]
    ax.plot(xs, ys, "o-", color=C["teal"], lw=2.5, ms=9)
    for i, (s, y) in enumerate(zip(steps, ys)):
        ax.annotate(s, (i, y), textcoords="offset points", xytext=(0, 14), ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0.55, 1.15)
    ax.set_xticks([])
    ax.set_ylabel("상대 기여(개념)", fontproperties=PROP)
    ax.set_title("민감도 사슬 — 중동 CAPEX와 가동률이 핵심", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "05_sensitivity.png")


def chart_scenarios() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    labels = ["Bear", "Base", "Bull"]
    rev = [1400, 1700, 2000]  # FY-ish trajectory scenarios $M
    px = [22, 33, 36]
    colors = [C["red"], C["gold"], C["teal"]]
    ax = axes[0]
    bars = ax.bar(labels, rev, color=colors, width=0.55)
    ax.set_title("시나리오별 연간 매출 (백만 USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 40, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 2400)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    bars = ax.bar(labels, px, color=colors, width=0.55)
    ax.set_title("시나리오별 주가 함의 (USD)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("USD / 주", fontproperties=PROP)
    for b, v in zip(bars, px):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.8, str(v), ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("Bear / Base / Bull — 가동·계약 시나리오", fontproperties=PROP_B, fontsize=12, y=1.02)
    return save_fig(fig, "06_scenarios.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [303, 327, 295, 398, 405]
    oi = [21, 27, 20, 31, 36]
    x = range(len(labels))
    ax.bar(x, rev, color=C["teal"], alpha=0.85, label="매출 (백만 USD)", width=0.55)
    ax2 = ax.twinx()
    ax2.plot(x, oi, "o-", color=C["gold"], lw=2.2, ms=8, label="영업이익 (백만 USD)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("매출 (백만 USD)", fontproperties=PROP, color=C["teal"])
    ax2.set_ylabel("영업이익 (백만 USD)", fontproperties=PROP, color=C["gold"])
    ax.set_title("분기 추이 — Q4'25~Q1'26 매출 점프", fontproperties=PROP_B, fontsize=12)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    return save_fig(fig, "07_quarterly.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["~4Q전", "~3Q전", "~2Q전", "최근(Q1'26)"]
    actual = [0.21, 0.16, 0.32, 0.26]
    est = [0.18, 0.15, 0.25, 0.21]
    surprise = [16, 7, 26, 25]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], est, w, label="예상 EPS", color=C["desert"])
    ax.bar([i + w / 2 for i in x], actual, w, label="실제 EPS", color=C["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("EPS (USD)", fontproperties=PROP)
    ax.set_title("실적 서프라이즈 — 연속 Beat", fontproperties=PROP_B, fontsize=12)
    for i, s in enumerate(surprise):
        ax.text(i + w / 2, actual[i] + 0.01, f"+{s}%", ha="center", fontsize=8, fontproperties=PROP, color=C["green"])
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
        (0.35, 0.55, 2.2, 1.7, "코어\nECPG/ASTH", C["navy"]),
        (2.8, 0.55, 2.6, 1.7, "NESR\n분할매수\n후보 1순위", C["teal"]),
        (5.65, 0.55, 2.0, 1.7, "진입\n25–28", C["gold"]),
        (7.9, 0.55, 1.8, 1.7, "현금\n버퍼", C["desert"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12", facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["desert"], C["gold"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=tc)
    ax.set_title("포지션 맥락 — Chase 상위 · 분할 진입 후보", fontproperties=PROP_B, fontsize=12, pad=6)
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
        content: "수익구조분석(NESR) · {ASOF} · " counter(page) " / " counter(pages);
        font-family: NanumGothic; font-size: 8.5pt; color: #78716c;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: NanumGothic, sans-serif; color: #1c1917; font-size: 10pt; line-height: 1.55; }}
    h1 {{ font-size: 20pt; font-weight: 700; margin: 0 0 4px; color: #0d5c4d; }}
    h2 {{ font-size: 13.5pt; font-weight: 700; margin: 22px 0 8px; padding-bottom: 4px;
         border-bottom: 2px solid #0d5c4d; color: #0d5c4d; page-break-after: avoid; }}
    h3 {{ font-size: 11pt; font-weight: 700; margin: 12px 0 6px; color: #1a3a2a; }}
    .hero {{
      background: linear-gradient(135deg, #1a3a2a 0%, #0d5c4d 45%, #c4a35a 120%);
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
    th {{ background: #0d5c4d; color: #fff; font-weight: 700; }}
    tr:nth-child(even) td {{ background: #f7f3eb; }}
    .viz {{ margin: 8px 0 12px; text-align: center; }}
    .viz img {{ max-width: 100%; height: auto; }}
    .viz figcaption {{ font-size: 8.5pt; color: #57534e; margin-top: 4px; }}
    .callout {{ background: #f7f3eb; border-left: 4px solid #c4a35a; padding: 8px 12px; margin: 8px 0 12px; font-size: 9.5pt; }}
    .gloss {{ background: #fafaf9; border: 1px solid #e7e5e4; padding: 8px 12px; margin: 6px 0 14px; font-size: 8.5pt; color: #44403c; }}
    .gloss-title {{ font-weight: 700; color: #1a3a2a; margin-bottom: 4px; font-size: 9pt; }}
    .gloss ul {{ margin: 0 0 0 14px; }}
    .gloss .term {{ font-weight: 700; color: #0d5c4d; }}
    .plain {{ background: #ecfdf5; border: 1px solid #a7f3d0; padding: 8px 12px; margin: 6px 0 10px; font-size: 9.5pt; }}
    .plain strong {{ color: #065f46; }}
    .warn {{ background: #fff1f2; border-left: 4px solid #9f1239; padding: 8px 12px; margin: 8px 0; font-size: 9.5pt; }}
    .footer-note {{ font-size: 8pt; color: #78716c; margin-top: 18px; border-top: 1px solid #e7e5e4; padding-top: 8px; }}
    """

    c0 = fig_block(charts["flow"], "그림 0. 비즈니스 흐름 — 유전 CAPEX → 시추/생산 서비스 → 매출")
    c1 = fig_block(charts["mix"], "그림 1. 세그먼트·지역 파이")
    c2 = fig_block(charts["bridge"], "그림 2. Q1'26 세그먼트 매출·이익 브리지")
    c3 = fig_block(charts["funnel"], "그림 3. TAM→SAM→SOM 깔때기")
    c4 = fig_block(charts["sens"], "그림 4. 민감도 사슬")
    c5 = fig_block(charts["scen"], "그림 5. Bear/Base/Bull")
    c6 = fig_block(charts["qtr"], "그림 6. 최근 5분기 매출·영업이익")
    c7 = fig_block(charts["eps"], "그림 7. EPS 서프라이즈")
    c8 = fig_block(charts["pos"], "그림 8. 포트폴리오에서의 NESR")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"/><title>수익구조분석 — NESR (National Energy Services)</title>
<style>{css}</style></head>
<body>

<div class="hero">
  <h1>수익구조분석 · NESR</h1>
  <div>National Energy Services Reunited Corp. · 나스닥 · 중동·북아프리카(MENA) 오일필드 서비스(OFS)</div>
  <div class="oneline">
    <strong>한 줄 구조:</strong> 중동 국영·국제 석유회사가 유전을 팔 때 필요한
    <em>장비·인력·기술 서비스</em>를 팝니다. 매출의 약 60%는 생산 단계 서비스(수압파쇄·시멘트 등),
    약 40%는 시추·평가 서비스이며, <em>매출의 99% 이상이 MENA</em>에서 나옵니다.
  </div>
  <div class="kpi">
    <span>종가 $27.99</span>
    <span>시총 ~$2.8B</span>
    <span>PT $30 / $33 / $36</span>
    <span>Q1'26 매출 $405M (+33.5%)</span>
    <span>Production 241M · D&amp;E 164M</span>
    <span>MENA ~99.8%</span>
    <span>진입 아이디어 $25–28 분할</span>
    <span>기준일 {ASOF}</span>
  </div>
</div>

<div class="plain">
  <strong>이 보고서를 읽는 법 (비전공자용):</strong>
  “어디서 돈을 받는지 → 시장 크기 → 무엇이 흔들리는지 → 좋은/나쁜 숫자 →
  경쟁 → 미리 볼 신호 → 얼마나 살지” 순서입니다.
  각 블록 끝 용어 주석은 중복 없이, 처음 나온 말만 설명합니다.
</div>

{c0}

<div class="block">
<h2>1. 수익 구조 — 세그먼트·지역·마진</h2>
<div class="plain">
  <strong>쉽게:</strong> 자동차로 치면 NESR은 차를 만드는 회사가 아니라,
  <em>정비소·견인·부품 장착 팀</em>에 가깝습니다. 석유회사가 “우물을 뚫고 기름을 뽑을 때”
  필요한 특수 장비와 숙련 인력을 빌려 쓰는 구조입니다. 손님이 거의 전부 <strong>중동</strong>입니다.
</div>
{c1}
{c2}

<h3>1-1. Q1'26 세그먼트 (10-Q)</h3>
<table>
  <tr><th>세그먼트</th><th>매출</th><th>전년</th><th>세그먼트 영업이익</th><th>하는 일(쉬운 말)</th></tr>
  <tr>
    <td>Production Services</td>
    <td>$241.0M</td>
    <td>$188.1M</td>
    <td>$32.7M</td>
    <td>수압파쇄(프랙), 시멘트, 코일드 튜빙, 자극, 완결 등 — <strong>이미 뚫린 우물에서 생산을 돕는 일</strong></td>
  </tr>
  <tr>
    <td>Drilling &amp; Evaluation</td>
    <td>$163.5M</td>
    <td>$115.0M</td>
    <td>$18.2M</td>
    <td>시추 공구, 방향성 시추, 와이어라인, 이수, 리그 관련 — <strong>우물을 찾고 뚫는 일</strong></td>
  </tr>
  <tr>
    <td>미배분 비용</td>
    <td>—</td>
    <td>—</td>
    <td>−$14.9M</td>
    <td>본사·주식보상 등 공통비</td>
  </tr>
  <tr>
    <td><strong>합계</strong></td>
    <td><strong>$404.6M (+33.5%)</strong></td>
    <td>$303.1M</td>
    <td><strong>OI $36.0M</strong></td>
    <td>연결 영업이익</td>
  </tr>
</table>

<p>
지역: MENA <strong>$402.8M (99.75%)</strong>, Rest of World $1.8M.
사실상 <strong>중동·북아프리카 원 베팅</strong>입니다. 장점(집중 성장)과 단점(지정학·단일 시장)이 동시에 있습니다.
</p>

{c6}

<h3>1-2. 연간 추이</h3>
<table>
  <tr><th>연도</th><th>매출</th><th>매출총이익</th><th>영업이익</th><th>순이익</th><th>이자</th></tr>
  <tr><td>FY2022</td><td>$910M</td><td>$65M</td><td>−$1M</td><td>−$36M</td><td>$34M</td></tr>
  <tr><td>FY2023</td><td>$1,146M</td><td>$149M</td><td>$81M</td><td>$13M</td><td>$46M</td></tr>
  <tr><td>FY2024</td><td>$1,302M</td><td>$209M</td><td>$138M</td><td>$76M</td><td>$40M</td></tr>
  <tr><td>FY2025</td><td>$1,324M</td><td>$165M</td><td>$98M</td><td>$51M</td><td>$33M</td></tr>
</table>

<p>
FY25 연간 매출은 $1.32B로 전년 대비 소폭 증가에 그쳤지만,
<strong>Q4'25 $398M → Q1'26 $405M</strong>으로 분기 런레이트가 한 단계 올라왔습니다(+33% YoY).
FY25 Production $816M / D&amp;E $508M.
보고 GM ~12.5%, OM ~8.9%, PM ~4.5%. 부채 ~$0.32B, 현금 ~$0.09B로 레버리지는 상대적으로 관리 구간.
순부채는 FY25 말 기준 약 $185M 수준으로 전년 대비 크게 줄였다고 경영진이 강조했습니다.
</p>

<div class="callout">
  <strong>계약·모멘텀:</strong> 사우디 Jafurah 비전통(언컨벤셔널) 개발 관련 프랙 등 대형 수주가
  성장 스토리의 상징입니다. “백로그를 효율적으로 실행하고 마진·운전자본을 개선한다”가 2026 경영 초점.
</div>

{gloss([
    ("OFS (Oilfield Services)", "유전에서 시추·완결·생산을 돕는 장비·인력·기술 서비스 산업."),
    ("MENA", "Middle East & North Africa. 중동·북아프리카."),
    ("Production Services", "생산 단계 서비스. 프랙·시멘트·코일드 튜빙 등."),
    ("Drilling & Evaluation (D&E)", "시추·평가 서비스. 구멍을 뚫고 지층을 평가하는 쪽."),
    ("수압파쇄 / Frac (Hydraulic Fracturing)", "암석에 고압 유체를 넣어 균열을 만들어 오일·가스가 잘 나오게 하는 시술."),
    ("시멘트 (Cementing)", "케이싱(강관)과 지층 사이를 시멘트로 막아 우물을 안정시키는 작업."),
    ("코일드 튜빙 (Coiled Tubing)", "릴에 감긴 연속 배관으로 우물 안에서 작업하는 기술."),
    ("NOC / IOC", "국영석유회사 / 국제석유회사. NESR의 주요 고객군."),
    ("CAPEX", "설비투자. 유전 개발 예산이 늘면 OFS 수요↑."),
    ("백로그 (Backlog)", "아직 매출로 인식되지 않았지만 수주해 둔 일감."),
    ("Jafurah", "사우디의 대형 비전통(셰일성) 가스 개발 프로젝트. NESR 수주 모멘텀의 핵심 키워드."),
])}
</div>

<div class="block">
<h2>2. 시장 깔때기 — TAM → SAM → SOM</h2>
<div class="plain">
  <strong>쉽게:</strong> 전 세계 유전 서비스 시장은 거대하지만, NESR이 실제로 싸우는 링은
  <em>중동·북아프리카</em>입니다. 여기서 국영 석유회사 예산이 곧 주문량입니다.
</div>
{c3}

<table>
  <tr><th>단계</th><th>대략</th><th>정의</th><th>헷갈리기 쉬운 점</th></tr>
  <tr>
    <td>TAM</td>
    <td>글로벌 OFS</td>
    <td>전 세계 시추·완결·생산 서비스</td>
    <td>NESR은 미주·북해 비중이 거의 없음</td>
  </tr>
  <tr>
    <td>SAM</td>
    <td>MENA OFS ~$30–40B (근사)</td>
    <td>중동·북아프리카에서 발주되는 서비스</td>
    <td>유가·국가 예산·지정학에 따라 출렁</td>
  </tr>
  <tr>
    <td>SOM</td>
    <td>~$1.3B+ (현재) → 성장 중</td>
    <td>NESR 매출. Q1 런레이트는 더 높은 궤적</td>
    <td>장기 ~$3B 비전은 가이던스가 아니라 지향점</td>
  </tr>
  <tr>
    <td>점유 논리</td>
    <td>로컬·통합 서비스</td>
    <td>MENA 현지 밀착 + 생산·시추 포트폴리오</td>
    <td>SLB·HAL 등 메이저와 부분 경쟁·공존</td>
  </tr>
</table>

{gloss([
    ("TAM / SAM / SOM", "전체 시장 / 우리가 팔 수 있는 시장 / 실제로 가져가는 규모."),
    ("언컨벤셔널 (Unconventional)", "전통 유정과 달리 셰일 등 특수 지층. 프랙 수요가 큼."),
    ("런레이트 (Run-rate)", "최근 분기 실적을 1년으로 환산한 대략 속도. 정확한 연간 가이던스는 아님."),
])}
</div>

<div class="block">
<h2>3. 민감도 사슬 — 무엇이 이익을 흔드나</h2>
<div class="plain">
  <strong>쉽게:</strong> 건설 하도급과 비슷합니다. 발주(CAPEX)가 끊기면 장비가 놀고,
  인건비·감가는 나가서 마진이 깎입니다. 반대로 장비가 풀가동이면 이익이 빨리 늘어납니다.
</div>
{c4}

<table>
  <tr><th>단계</th><th>좋게 나오면</th><th>나쁘게 나오면</th></tr>
  <tr><td>① NOC CAPEX</td><td>사우디 등 개발 예산 유지·확대</td><td>유가 급락·재정 긴축 → 발주 축소</td></tr>
  <tr><td>② 수주·백로그</td><td>Jafurah류 대형 일감</td><td>수주 공백</td></tr>
  <tr><td>③ 가동률</td><td>장비·인력 풀가동</td><td>유휴 → 고정비 압박</td></tr>
  <tr><td>④ 가격·믹스</td><td>고마진 작업 비중↑</td><td>가격 경쟁·믹스 악화</td></tr>
  <tr><td>⑤ 원가</td><td>조달·효율 개선</td><td>인건·부품·물류비↑</td></tr>
  <tr><td>⑥ 마진</td><td>OI·EBITDA 레버리지</td><td>마진 압축 (FY25 GP 하락 경험)</td></tr>
  <tr><td>⑦ EPS</td><td>연속 Beat 유지</td><td>Miss + 멀티플 축소</td></tr>
</table>

<p>
참고: FY25 매출총이익은 FY24보다 줄었습니다($209M→$165M). “매출은 있는데 마진이 흔들릴 수 있다”는
경계 신호입니다. Q1'26은 매출·OI가 동반 회복 중인지 계속 확인해야 합니다.
</p>

{gloss([
    ("가동률 (Utilization)", "보유 장비·인력이 실제로 일에 투입되는 비율."),
    ("유휴", "일이 없어 장비가 멈춰 있는 상태. 비용은 나가는데 매출이 없음."),
    ("지정학 리스크", "전쟁·제재·정세 불안이 발주·물류·인력에 주는 충격. MENA 집중의 그림자."),
])}
</div>

<div class="block">
<h2>4. Bear / Base / Bull — 숫자 시나리오</h2>
<div class="plain">
  <strong>쉽게:</strong> PT 밴드($30/$33/$36)와 분기 모멘텀을 기준으로 작업용 시나리오를 잡았습니다.
</div>
{c5}

<table>
  <tr><th>시나리오</th><th>가정</th><th>매출(개념)</th><th>주가 함의</th></tr>
  <tr>
    <td>Bear</td>
    <td>CAPEX 둔화, 가동률↓, 마진 재압축, 지정학 충격</td>
    <td>~$1.4B</td>
    <td>$22–25</td>
  </tr>
  <tr>
    <td>Base</td>
    <td>MENA 발주 유지, Q1 런레이트 지속, 마진 안정, PT 평균</td>
    <td>~$1.7B</td>
    <td>$30–34</td>
  </tr>
  <tr>
    <td>Bull</td>
    <td>Jafurah 등 실행 가속, 가동·가격 동반, PT 고점</td>
    <td>~$2.0B+</td>
    <td>$35–38</td>
  </tr>
</table>

<p>
현재가 <strong>$27.99</strong> vs PT 평균 <strong>$33</strong>(+18%) · 고점 PT $36.
52주 고점 $30.31 아래, 저점 $6 대비는 이미 크게 회복한 상태.
전략상 <strong>$25–28 분할 매수</strong>가 진입 아이디어로, 지금 가격은 그 밴드 상단 근처입니다.
</p>

{c7}
<p>
최근 4분기 EPS 전부 Beat(+7%~+26%). Rev도 연속 Beat 패턴.
“서프라이즈 + PT 여유” 조합으로 Chase RR에서 상위로 분류된 근거입니다.
</p>

{gloss([
    ("Bear / Base / Bull", "비관·기본·낙관."),
    ("Beat", "실제 실적 &gt; 컨센서스."),
    ("분할 매수", "한 번에 몰빵하지 않고 가격·시점을 나눠 사는 것."),
])}
</div>

<div class="block">
<h2>5. 경쟁·포지션</h2>
<div class="plain">
  <strong>쉽게:</strong> 중동 유전에는 글로벌 메이저(슐럼버거·할리버튼 등)와
  현지·지역 특화 업체가 같이 있습니다. NESR은 “MENA에 깊게 뿌리내린 통합 OFS” 포지션입니다.
</div>
<table>
  <tr><th>전선</th><th>NESR</th><th>압력</th><th>관찰</th></tr>
  <tr>
    <td>Production (프랙 등)</td>
    <td>Q1 매출·OI 동반</td>
    <td>가격·가동 경쟁</td>
    <td>프랙 가동, Jafurah 실행</td>
  </tr>
  <tr>
    <td>D&amp;E</td>
    <td>YoY 고성장 (+42%)</td>
    <td>시추 리그 사이클</td>
    <td>시추 활동 지표</td>
  </tr>
  <tr>
    <td>지역</td>
    <td>MENA 99%+</td>
    <td>단일 지역 리스크</td>
    <td>국가별 예산·정세</td>
  </tr>
</table>
{gloss([
    ("메이저 OFS", "Schlumberger(SLB), Halliburton(HAL), Baker Hughes 등 대형 글로벌 업체."),
    ("리그 (Rig)", "시추기. 가동 리그 수가 시추 활동의 바로미터."),
])}
</div>

<div class="block">
<h2>6. 선행 지표</h2>
<ul>
  <li><strong>분기 매출·세그먼트 믹스</strong> (Production vs D&amp;E)</li>
  <li><strong>세그먼트 영업이익률</strong> — FY25 GP 둔화 재발 여부</li>
  <li><strong>수주·Jafurah 등 계약 뉴스</strong></li>
  <li><strong>순부채·FCF·운전자본</strong></li>
  <li><strong>사우디·MENA CAPEX / 유가 환경</strong></li>
  <li><strong>차기 실적</strong> — 시장 관전 창(대략 8월대, 확정일은 IR 확인)</li>
</ul>
{gloss([
    ("선행 지표", "실적 전 방향성을 가늠하는 신호."),
    ("운전자본", "매출채권·재고 등. 성장기에 현금이 여기 묶일 수 있음."),
    ("FCF", "여유 현금흐름."),
])}
</div>

<div class="block">
<h2>7. 비중 상한 · Thesis Breakers</h2>
{c8}
<div class="plain">
  <strong>쉽게:</strong> 소액 포트에서 NESR은 <strong>아직 코어가 아니라 ‘분할로 넣을 후보’</strong>입니다.
  수요일 입금 후 버퍼를 남기고, $25–28에서 나눠 사는 그림이 기본입니다.
</div>
<table>
  <tr><th>항목</th><th>권고</th><th>이유</th></tr>
  <tr><td>현재</td><td>미보유 또는 관망 → 분할 진입 후보</td><td>Chase 상위, PT 여유, MENA 모멘텀</td></tr>
  <tr><td>진입</td><td>$25–28 분할 (1차 소량)</td><td>고점($30) 추격 대신 밴드 매수</td></tr>
  <tr><td>1차 규모(소액)</td><td>~$220–260 (수요일 이후 여유 기준)</td><td>버퍼 $280–320 유지 전제</td></tr>
  <tr><td>비중 상한</td><td>총자산 ~15–20%</td><td>지정학 단일 리스크 한도</td></tr>
</table>

<div class="warn">
  <strong>Thesis Breakers:</strong>
  <ul>
    <li>MENA CAPEX·가동률이 뚜렷히 꺾임</li>
    <li>마진 재압축이 분기 연속으로 악화</li>
    <li>대형 계약 지연·취소, 백로그 소진 공백</li>
    <li>지정학 사건으로 조업·물류 차질</li>
    <li>연속 Beat가 Miss로 전환되며 PT 하향</li>
  </ul>
</div>

{gloss([
    ("버퍼", "급락·다른 기회를 위해 남겨 둔 현금."),
    ("Thesis Breaker", "매수·보유 논리를 깨는 사건."),
])}
</div>

<div class="block">
<h2>8. 한계 · 출처</h2>
<ul>
  <li>시가·PT·일부 재무: Yahoo Finance 집계.</li>
  <li>세그먼트·지역: NESR 10-Q / IR (Q1'26, FY25).</li>
  <li>MENA TAM·$3B 비전은 근사·지향점. 확정 가이던스 아님.</li>
  <li>시나리오는 교육·의사결정 보조용. 투자 권고 아님.</li>
</ul>
<div class="footer-note">
  생성: 수익구조분석() · 티커 NESR · 기준 {ASOF} · WeasyPrint + NanumGothic
</div>
</div>

</body></html>
"""
    return html


def main() -> None:
    charts = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "bridge": chart_segment_oi(),
        "funnel": chart_tam_funnel(),
        "sens": chart_sensitivity(),
        "scen": chart_scenarios(),
        "qtr": chart_quarterly(),
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
