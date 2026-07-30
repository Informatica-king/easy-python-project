#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(MU) — 시각자료 + 초보용 설명 + 전문용어 주석 + WeasyPrint PDF."""

from __future__ import annotations

import base64
from pathlib import Path
import sys

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sepa.rev_price_chart import build_and_insert_price  # noqa: E402


import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from weasyprint import HTML

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
ASOF = "2026-07-22"
OUT_PDF = [
    Path("/opt/cursor/artifacts/MU_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/MU_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/MU_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/mu")
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
        (0.1, 0.7, 1.7, 1.6, "AI/클라우드\nCapEx 수요", C["sand"]),
        (2.0, 0.7, 1.85, 1.6, "DRAM\n(+HBM)", C["gold"]),
        (4.05, 0.7, 1.75, 1.6, "NAND\nSSD·스토리지", C["teal2"]),
        (6.0, 0.7, 1.8, 1.6, "데이터센터\n·모바일·PC", C["teal"]),
        (8.0, 0.7, 1.75, 1.6, "ASP·비트\n매출", C["navy"]),
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
    ax.set_title("비즈니스 한눈에 — AI 시대 메모리(DRAM·NAND)를 판다", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    # FQ3-26: DRAM 31328, NAND 9943, Other 185 → total 41456
    sizes = [31328, 9943, 185]
    labels = ["DRAM\n31.3B (76%)", "NAND\n9.9B (24%)", "Other/NOR\n0.2B"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["navy"], C["teal"], C["gold"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("기술별 매출 (FQ3-26, 총 41.5B)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["DRAM", "NAND"]
    yoy = [343, 361]
    bars = ax.bar(cats, yoy, color=[C["navy"], C["teal"]], width=0.5)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("기술별 YoY 성장 (FQ3-26)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, yoy):
        ax.text(b.get_x() + b.get_width() / 2, v + 8, f"+{v}%", ha="center", fontproperties=PROP_B, fontsize=10)
    ax.set_ylim(0, 420)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_dc_hbm() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    cats = ["전체 매출\n41.5B", "데이터센터\n>25B", "DC SSD\n>5B", "HBM4\n>1B"]
    vals = [41.5, 25.0, 5.0, 1.0]
    colors = [C["slate"], C["navy"], C["teal"], C["gold"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("십억 USD (분기)", fontproperties=PROP)
    ax.set_title("FQ3-26 성장 엔진 — 데이터센터·HBM", fontproperties=PROP_B, fontsize=12)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f">{v:.1f}B+", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "03_dc_hbm.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    qs = ["FQ3-25\n25-05", "FQ4-25\n25-08", "FQ1-26\n25-11", "FQ2-26\n26-02", "FQ3-26\n26-05"]
    rev = [9.30, 11.32, 13.64, 23.86, 41.46]
    colors = [C["slate"]] * 4 + [C["navy"]]
    bars = ax.bar(qs, rev, color=colors, width=0.58)
    ax.set_ylabel("매출 (십억 USD)", fontproperties=PROP)
    ax.set_title("분기 매출 추이 — AI 메모리 슈퍼사이클", fontproperties=PROP_B, fontsize=12)
    for b, v in zip(bars, rev):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.7, f"{v:.1f}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 50)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "04_quarterly.png")


def chart_price_mix() -> Path:
    """ASP vs bits narrative — qualitative bars from earnings commentary."""
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6))
    ax = axes[0]
    ax.bar(["비트 출하", "ASP"], [3, 62], color=[C["teal2"], C["navy"]], width=0.5)
    ax.set_title("DRAM QoQ 기여 (대략)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("QoQ %대", fontproperties=PROP)
    ax.text(0, 5, "한자릿수+", ha="center", fontproperties=PROP, fontsize=8)
    ax.text(1, 65, "60%대", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    ax.bar(["비트 출하", "ASP"], [5, 85], color=[C["teal2"], C["teal"]], width=0.5)
    ax.set_title("NAND QoQ 기여 (대략)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("QoQ %대", fontproperties=PROP)
    ax.text(0, 8, "중한자릿수", ha="center", fontproperties=PROP, fontsize=8)
    ax.text(1, 88, "80%대", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.suptitle("이번 분기는 '물량'보다 '가격(ASP)'이 매출을 밀었다", fontproperties=PROP_B, fontsize=12, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "05_price_mix.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    qs = ["FQ4-25", "FQ1-26", "FQ2-26", "FQ3-26"]
    surp = [5.9, 20.6, 33.2, 21.3]
    bars = ax.bar(qs, surp, color=C["green"], width=0.55)
    ax.set_ylabel("EPS 서프라이즈 %", fontproperties=PROP)
    ax.set_title("최근 4분기 Non-GAAP EPS 서프라이즈 (대형 Beat)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, surp):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"+{v:.0f}%", ha="center", fontproperties=PROP, fontsize=9)
    ax.set_ylim(0, 42)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "06_eps_surprise.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [650, 1100, 1500]
    highs = [900, 1500, 2000]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    ax.axvline(970.8, color=C["gold"], ls="--", lw=1.5)
    ax.text(980, 2.35, "현재 ~971", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.axvline(1492, color="#2563eb", ls=":", lw=1.2)
    ax.text(1500, -0.55, "PT평균 ~1492", fontproperties=PROP, fontsize=7.5, color="#2563eb")
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        mid = (lo + hi) / 2
        ax.text(mid, i, f"{lo}–{hi}", ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(400, 2300)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear (12M 관점)", fontproperties=PROP_B, fontsize=11)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP_B)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_sensitivity() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    # illustrative: ASP shock impact on quarterly DRAM revenue direction
    shocks = ["ASP -20%", "ASP -10%", "기준", "ASP +10%", "ASP +20%"]
    # DRAM ~31.3B; rough linear ASP sensitivity (bits fixed)
    base = 31.3
    vals = [base * x for x in (0.8, 0.9, 1.0, 1.1, 1.2)]
    colors = [C["red"], "#ea580c", C["slate"], C["teal"], C["navy"]]
    bars = ax.bar(shocks, vals, color=colors, width=0.55)
    ax.set_ylabel("DRAM 분기 매출 근사 (B)", fontproperties=PROP)
    ax.set_title("민감도 — DRAM ASP 변동 시 (비트 고정 가정)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.5, f"{v:.1f}", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "08_sensitivity.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    rows = [
        (0.3, 2.6, 9.4, 1.0, C["navy"], "white", "포트 역할: 반도체 1자리 · 소수점 위성 (테마=AI 메모리)"),
        (0.3, 1.4, 4.5, 0.95, C["teal"], "white", "권장 금액\n120–150 USD"),
        (5.0, 1.4, 4.7, 0.95, C["gold"], C["ink"], "진입 밴드\n920–980 (추격 자제)"),
        (0.3, 0.25, 9.4, 0.95, C["sand"], C["ink"], "우선순위: 버퍼 300 → NEO → AMRX → MU → NESR(25–27만)"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=1.5,
            )
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9, color=tc)
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


def build_html(charts: dict[str, Path]) -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"MU 수익구조분석 {ASOF} — " counter(page);
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
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>MU 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>MU 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Micron Technology · DRAM / NAND / HBM · AI 메모리</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · FQ3-26(종료 2026-05-28) 실적 중심</p>
  <p style="margin-top:22px">
    <span class="tag">현재 ~970.8 USD</span>
    <span class="tag good">PT평균 ~1,492 (+54%)</span>
    <span class="tag">FQ3 매출 41.5B</span>
    <span class="tag warn">포트: 반도체 위성 120–150 USD</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>AI 데이터센터 메모리 슈퍼사이클의 본류.</b> FQ3-26 매출 41.5B(+346% YoY), DRAM 76% / NAND 24%.
데이터센터 &gt;25B, HBM4 &gt;1B. 매출 증가는 비트보다 <b>ASP(가격)</b>가 주도.
당신 계좌에서는 <b>소수점 120–150 USD 위성</b>으로 ‘반도체 1자리’ 역할.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> AI 서버가 폭발하면 GPU만 필요한 게 아니라, GPU 옆의 ‘기억장치 칩’(메모리)도 같이 부족해짐. 마이크론이 그 메모리를 만듦.</div>
{gloss([
    ("DRAM", "컴퓨터·서버가 당장 쓰는 주 메모리. AI 서버 수요의 핵심."),
    ("HBM", "High Bandwidth Memory — GPU에 붙는 초고속 적층 DRAM. AI 학습·추론용."),
    ("NAND", "SSD·저장장치용 플래시 메모리. 데이터센터 스토리지 수요."),
    ("ASP", "Average Selling Price — 비트당·제품당 평균 판매 가격."),
])}

<h2>1. 어디서 돈이 오나 — 기술 믹스</h2>
{fig_block(charts['02'], 'DRAM vs NAND')}
<table>
  <tr><th>기술 (FQ3-26)</th><th>매출</th><th>비중</th><th>QoQ</th><th>YoY</th></tr>
  <tr><td>DRAM</td><td>31.33B</td><td>76%</td><td>+67%</td><td>+343%</td></tr>
  <tr><td>NAND</td><td>9.94B</td><td>24%</td><td>+99%</td><td>+361%</td></tr>
  <tr><td>Other (주로 NOR)</td><td>0.19B</td><td>&lt;1%</td><td>+95%</td><td>+147%</td></tr>
  <tr><td><b>합계</b></td><td><b>41.46B</b></td><td>100%</td><td><b>+74%</b></td><td><b>+346%</b></td></tr>
</table>
<div class="easy"><b>쉽게:</b> 매출 4분의 3이 DRAM. NAND도 같이 폭등했지만, ‘회사의 뼈대’는 DRAM(특히 데이터센터·HBM)이다.</div>
{gloss([
    ("QoQ", "직전 분기 대비 성장."),
    ("YoY", "작년 같은 분기 대비 성장."),
    ("NOR", "코드 저장용 메모리. 비중은 작음."),
])}

<h2>2. 성장 엔진 — 데이터센터 · HBM</h2>
{fig_block(charts['03'], 'DC / SSD / HBM 규모')}
<ul>
  <li><b>데이터센터 매출</b> &gt;25B (연환산 &gt;100B 런레이트 언급)</li>
  <li><b>데이터센터 SSD</b> &gt;5B (QoQ 2배+)</li>
  <li><b>HBM4</b> 이미 &gt;1B 출하 · 램프 속도 HBM3E 대비 약 2배</li>
  <li>HBM4E는 캘린더 2027 양산 목표 (로드맵)</li>
</ul>
<div class="easy"><b>쉽게:</b> 예전엔 PC·폰 메모리가 메인. 지금은 ‘클라우드 AI 공장’이 마이크론 매출의 엔진이다.</div>
{gloss([
    ("Data center", "클라우드·AI 학습용 대형 서버 단지."),
    ("SSD", "NAND 기반 저장장치. 서버용 고용량 SSD 수요 급증."),
    ("HBM4 / HBM4E", "차세대·그 다음 세대 HBM 제품."),
    ("런레이트", "현재 분기 매출을 연간으로 환산한 속도."),
])}

<h2>3. 분기 궤적 · 가격 vs 물량</h2>
{fig_block(charts['04'], '분기 매출')}
{fig_block(charts['05'], 'ASP vs 비트')}
<p>FQ3 DRAM: 비트 출하 소폭↑, <b>ASP 60%대↑</b>. NAND: 비트 중한자릿수↑, <b>ASP 80%대↑</b>.
즉 호황의 상당 부분은 <b>공급 타이트 → 가격</b>이다. 사이클이 꺾이면 ASP가 먼저 내려갈 수 있음.</p>
{gloss([
    ("비트 출하", "실제로 출하한 메모리 용량(비트) 증가율."),
    ("공급 타이트", "수요 &gt; 공급으로 가격이 오르는 상태."),
    ("메모리 사이클", "호황↔불황이 반복되는 반도체 메모리 업황."),
])}

<h2>4. 실적 품질 · 밸류</h2>
{fig_block(charts['06'], 'EPS 서프라이즈')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>FQ3 매출 / YoY</td><td>41.46B / +346%</td></tr>
  <tr><td>Non-GAAP EPS</td><td>25.11 (컨센 대비 대형 Beat, ~+21%)</td></tr>
  <tr><td>최근 4Q EPS 서프라이즈</td><td>+6% / +21% / +33% / +21%</td></tr>
  <tr><td>매출총이익률(참고)</td><td>~73%대 (라이브 집계) — 사이클 피크 구간</td></tr>
  <tr><td>현재가 / PT평균</td><td>~970.8 / ~1,492 (+54%)</td></tr>
  <tr><td>52주</td><td>103.4 – 1,255</td></tr>
  <tr><td>Fwd P/E (참고)</td><td>~6.3 — 이익 폭증 반영</td></tr>
</table>
<div class="box"><b>해석:</b> Beat 머신이지만, 이미 ‘기록적 이익’이 가격에 상당 부분 반영됨.
업사이드는 PT 기준 남아 있으나, <b>사이클 민감</b>이라 비중은 위성(소액)이 맞음.</div>
{gloss([
    ("Non-GAAP EPS", "일회성·주식보상 등 조정 후 주당순이익. 시장이 주로 보는 숫자."),
    ("Beat", "컨센서스(예상치)보다 좋은 실적."),
    ("Fwd P/E", "앞으로 예상 이익 대비 주가. 이익이 급증하면 낮아 보임."),
])}

<h2>5. 민감도 · 시나리오</h2>
{fig_block(charts['08'], 'ASP 민감도')}
{fig_block(charts['07'], '주가 시나리오')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>1,500–2,000</td><td>타이트 지속·HBM 점유 확대·가이던스 재상향</td></tr>
  <tr><td>Base</td><td>1,100–1,500</td><td>PT 수렴 · 고수익 유지하나 증가율 둔화</td></tr>
  <tr><td>Bear</td><td>650–900</td><td>ASP 급락 · CapEx 둔화 · 재고 조정</td></tr>
</table>
<p><b>Breaker:</b> 데이터센터/HBM 수요 가이던스 하향 · ASP 급락 · 대형 고객 재고조정</p>
{gloss([
    ("CapEx", "설비투자 — 클라우드 기업의 서버·칩 투자."),
    ("재고 조정", "고객이 쌓아둔 재고를 소진하며 신규 주문을 줄이는 국면."),
])}

<h2>6. 포트폴리오 위치</h2>
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>역할</td><td>반도체 테마 <b>1자리 · 소수점 위성</b></td></tr>
  <tr><td>금액</td><td><b>120–150 USD</b> (현금 ~781 기준, 버퍼 300 후)</td></tr>
  <tr><td>진입</td><td><b>920–980</b> (과도한 장중 급등 추격 자제)</td></tr>
  <tr><td>우선순위</td><td>버퍼 → NEO → AMRX → <b>MU</b> → NESR(25–27)</td></tr>
  <tr><td>하지 말 것</td><td>MU로 NEO 이벤트 예산 잠식 · 300+ USD 과비중</td></tr>
</table>
<div class="easy"><b>한줄 결론:</b> 사업은 AI 메모리 본류로 강함. 계좌에는 <u>소수점 소액</u>으로 ‘자리’만 준다. 수익구조상 리스크는 수요가 아니라 <b>ASP 사이클</b>이다.</div>

<h2>부록 · 출처</h2>
<p class="small">
Micron FQ3-26 earnings release (2026-06-24, SEC Exhibit 99.1) · earnings call/슬라이드 요약
(DRAM/NAND/DC/HBM) · Yahoo/yfinance 가격·PT·분기 매출 ({ASOF}).
민감도 막대는 ASP 선형 가정 예시(공식 가이던스 아님). 투자 권유 아님.
</p>
<p class="small">생성: 수익구조분석() · 티커 MU · 기준 {ASOF} · WeasyPrint + NanumGothic</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_dc_hbm(),
        "04": chart_quarterly(),
        "05": chart_price_mix(),
        "06": chart_eps_surprise(),
        "07": chart_scenarios(),
        "08": chart_sensitivity(),
        "09": chart_position(),
    }
    html = build_html(charts)
    html, _px = build_and_insert_price("MU", CHART_DIR, html)
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


if __name__ == "__main__":
    main()
