#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""심층분석(MRVL) — 7섹션 + 차트 + Chase RR 맥락 · WeasyPrint PDF."""

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
ASOF = "2026-07-21"
OUT_PDF = [
    Path("/opt/cursor/artifacts/MRVL_Deep_Analysis.pdf"),
    Path("/workspace/reports/MRVL_Deep_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/MRVL_Deep_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/mrvl")
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
    "blue": "#2563eb",
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
        (0.1, 0.7, 1.75, 1.6, "하이퍼스케일러\nAI CapEx", C["sand"]),
        (2.0, 0.7, 1.85, 1.6, "커스텀 XPU\n·XPU-attach", C["gold"]),
        (4.0, 0.7, 1.85, 1.6, "광학·스위치\n800G/1.6T", C["teal2"]),
        (6.05, 0.7, 1.8, 1.6, "데이터센터\n인프라 SoC", C["teal"]),
        (8.05, 0.7, 1.75, 1.6, "칩·모듈\n매출", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c,
                edgecolor="white",
                lw=2,
            )
        )
        tc = C["ink"] if c in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(
            x + w / 2,
            y + h / 2,
            t,
            ha="center",
            va="center",
            fontproperties=PROP_B,
            fontsize=8.5,
            color=tc,
        )
    ax.set_title(
        "비즈니스 한눈에 — AI 데이터센터 연결·커스텀 실리콘을 판다",
        fontproperties=PROP_B,
        fontsize=12,
        pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [1832.7, 585.1]
    labels = ["Data Center\n1,833M (76%)", "Comm & Other\n585M (24%)"]
    ax.pie(
        sizes,
        labels=labels,
        colors=[C["teal"], C["gold"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("엔드마켓 매출 (Q1 FY27, 총 2,418M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["광학·\n인터커넥트", "커스텀\n실리콘", "이더넷\n스위치", "스토리지\n·기타 DC"]
    # qualitative share of DC growth drivers — illustrative ranking not exact disclosure
    vals = [38, 28, 18, 16]
    bars = ax.bar(cats, vals, color=[C["navy"], C["teal"], C["teal2"], C["gold"]])
    ax.set_ylabel("성장 기여 가중(상대, %)", fontproperties=PROP, fontsize=9)
    ax.set_title("DC 성장 드라이버(상대 가중)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylim(0, 50)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 1,
            f"{v}",
            ha="center",
            fontproperties=PROP,
            fontsize=8,
        )
    ax.tick_params(axis="x", labelsize=8)
    for label in ax.get_xticklabels():
        label.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_revenue_trend() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    qs = ["Q1'26\nFY26", "Q2'26", "Q3'26", "Q4'26", "Q1'27", "Q2'27\n가이드"]
    # FY26 quarters approximate from filings / yfinance; Q1 FY27 actual; Q2 guide mid
    rev = [1.895, 2.006, 2.075, 2.219, 2.418, 2.700]
    colors = [C["slate"]] * 4 + [C["teal"], C["gold"]]
    bars = ax.bar(qs, rev, color=colors, width=0.62)
    ax.set_ylabel("매출 (십억 USD)", fontproperties=PROP, fontsize=9)
    ax.set_title("분기 매출 추이 + Q2 FY27 가이드 중점", fontproperties=PROP_B, fontsize=12)
    ax.set_ylim(0, 3.2)
    for b, v in zip(bars, rev):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 0.06,
            f"{v:.2f}",
            ha="center",
            fontproperties=PROP,
            fontsize=8,
        )
    ax.axhline(2.7, color=C["gold"], ls="--", lw=1, alpha=0.7)
    ax.text(5.35, 2.78, "가이드 2.70 +/-5%", fontproperties=PROP, fontsize=7.5, color=C["gold"])
    for label in ax.get_xticklabels():
        label.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "03_revenue_trend.png")


def chart_outlook() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    years = ["FY26\n(실적근사)", "FY27\n가이던스", "FY28\n가이던스"]
    vals = [8.2, 11.5, 16.5]  # FY26 ~8.2B from sum of quarters ~8.19; company raised FY27/28
    bars = ax.bar(years, vals, color=[C["slate"], C["teal"], C["navy"]], width=0.55)
    ax.set_ylabel("매출 (십억 USD)", fontproperties=PROP, fontsize=9)
    ax.set_title("경영진 매출 아웃룩 (FY27 ~11.5B, FY28 ~16.5B)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylim(0, 20)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 0.35,
            f"~{v:.1f}B",
            ha="center",
            fontproperties=PROP_B,
            fontsize=10,
        )
    ax.annotate(
        "+40% YoY",
        xy=(1, 11.5),
        xytext=(0.55, 14.2),
        arrowprops=dict(arrowstyle="->", color=C["green"]),
        fontproperties=PROP,
        fontsize=8,
        color=C["green"],
    )
    ax.annotate(
        "+~45% YoY",
        xy=(2, 16.5),
        xytext=(1.55, 18.5),
        arrowprops=dict(arrowstyle="->", color=C["green"]),
        fontproperties=PROP,
        fontsize=8,
        color=C["green"],
    )
    for label in ax.get_xticklabels():
        label.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "04_outlook.png")


def chart_eps_surprise() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    qs = ["Q2 FY26\n25-08", "Q3 FY26\n25-12", "Q4 FY26\n26-03", "Q1 FY27\n26-05"]
    # yfinance non-GAAP surprise %; Q1 public sources also cite beat vs older est
    surp = [-0.5, 3.0, 1.1, 0.6]
    colors = [C["red"] if v < 0 else C["green"] for v in surp]
    bars = ax.bar(qs, surp, color=colors, width=0.55)
    ax.axhline(0, color=C["ink"], lw=0.8)
    ax.set_ylabel("EPS 서프라이즈 (%)", fontproperties=PROP, fontsize=9)
    ax.set_title("최근 4분기 Non-GAAP EPS 서프라이즈 (소폭·안정)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, surp):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + (0.25 if v >= 0 else -0.45),
            f"{v:+.1f}%",
            ha="center",
            fontproperties=PROP,
            fontsize=8,
        )
    for label in ax.get_xticklabels():
        label.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "05_eps_surprise.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [140, 220, 290]
    highs = [175, 260, 360]
    mids = [(a + b) / 2 for a, b in zip(lows, highs)]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    ax.axvline(194.94, color=C["gold"], ls="--", lw=1.5)
    ax.text(196, 2.35, "현재 ~195", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.axvline(253.7, color=C["blue"], ls=":", lw=1.2)
    ax.text(255, -0.55, "PT평균 ~254", fontproperties=PROP, fontsize=7.5, color=C["blue"])
    for i, (lo, hi, mid) in enumerate(zip(lows, highs, mids)):
        ax.text(mid, i, f"{lo}–{hi}", ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(100, 400)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP, fontsize=9)
    ax.set_title("Bull / Base / Bear 밴드 (12M 관점)", fontproperties=PROP_B, fontsize=11)
    for label in ax.get_yticklabels():
        label.set_fontproperties(PROP_B)
    fig.tight_layout()
    return save_fig(fig, "06_scenarios.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    rows = [
        (0.3, 2.6, 9.4, 1.0, C["navy"], "white", "포트폴리오 적합도: 낮음 — 시총 ~175B 대형주, 1주~195달러"),
        (0.3, 1.4, 4.5, 0.95, C["teal"], "white", "이벤트: 08-27 실적\n(D-37, 대기 가능)"),
        (5.0, 1.4, 4.7, 0.95, C["gold"], C["ink"], "현금~$945 기준\n최대 ~4–5주 (집중위반)"),
        (0.3, 0.25, 9.4, 0.95, C["sand"], C["ink"], "Chase 판정: 관망·비적합 — 소형/중형 모멘텀 추격 전략과 불일치"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor=c,
                edgecolor="white",
                lw=1.5,
            )
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9, color=tc)
    ax.set_title("실행 포지션 맵 (사용자 전략 기준)", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "07_position.png")


def build_html(charts: dict[str, Path]) -> str:
    def im(key: str) -> str:
        return f'<img src="data:image/png;base64,{img_b64(charts[key])}" />'

    css = f"""
    @font-face {{
      font-family: 'NanumGothic';
      src: url('file://{FONT_REG}');
      font-weight: normal;
    }}
    @font-face {{
      font-family: 'NanumGothic';
      src: url('file://{FONT_BOLD}');
      font-weight: bold;
    }}
    @page {{
      size: A4;
      margin: 14mm 12mm 16mm 12mm;
      @bottom-center {{
        content: "MRVL 심층분석 {ASOF} — " counter(page);
        font-size: 8pt;
        color: #666;
        font-family: 'NanumGothic', sans-serif;
      }}
    }}
    body {{
      font-family: 'NanumGothic', sans-serif;
      font-size: 9.5pt;
      line-height: 1.45;
      color: #1a1a1a;
    }}
    h1 {{ font-size: 22pt; margin: 0 0 6px; color: #1e3a5f; }}
    h2 {{
      font-size: 13pt; margin: 16px 0 6px;
      border-bottom: 2px solid #0f766e; padding-bottom: 3px; color: #1e3a5f;
      page-break-after: avoid;
    }}
    h3 {{ font-size: 10.5pt; margin: 10px 0 4px; color: #0f766e; }}
    .cover {{
      page-break-after: always;
      min-height: 240mm;
      display: flex;
      flex-direction: column;
      justify-content: center;
      text-align: center;
      background: linear-gradient(165deg, #f0f7f6 0%, #e8eef5 55%, #f7f3e8 100%);
      padding: 24px;
      border-radius: 8px;
    }}
    .cover .sub {{ font-size: 12pt; color: #444; margin-top: 10px; }}
    .meta {{ font-size: 10pt; color: #555; margin-top: 20px; }}
    .tag {{
      display: inline-block; background: #dbeafe; padding: 2px 7px;
      border-radius: 3px; font-size: 8pt; margin: 2px 2px;
    }}
    .tag.warn {{ background: #fde68a; }}
    .tag.bad {{ background: #fecaca; }}
    .tag.good {{ background: #bbf7d0; }}
    table {{
      width: 100%; border-collapse: collapse; font-size: 8.5pt; margin: 8px 0;
    }}
    th, td {{ border: 1px solid #ccc; padding: 4px 6px; vertical-align: top; }}
    th {{ background: #edf2f7; font-weight: bold; }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    .conclusion td:first-child {{ font-weight: bold; width: 24%; background: #f0fdfa; }}
    img {{ max-width: 100%; height: auto; margin: 6px 0 10px; }}
    .easy {{
      background: #f0fdfa; border-left: 4px solid #0f766e;
      padding: 8px 10px; margin: 8px 0; font-size: 8.5pt;
    }}
    .gloss {{
      background: #fafaf9; border: 1px solid #e7e5e4;
      padding: 8px 10px; margin: 8px 0; font-size: 8pt; color: #444;
    }}
    .box {{
      background: #fffbeb; border: 1px solid #d69e2e;
      padding: 10px; margin: 10px 0;
    }}
    .small {{ font-size: 8pt; color: #555; }}
    .section {{ page-break-inside: avoid; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"/><title>MRVL 심층분석</title><style>{css}</style></head>
<body>
  <section class="cover">
    <h1>MRVL 심층분석</h1>
    <p class="sub">Marvell Technology · AI 데이터센터 인프라 반도체</p>
    <p class="meta">기준일 {ASOF} (미국 장중/최근가) · 7섹션 + Chase RR 포트폴리오 맥락</p>
    <p style="margin-top:28px">
      <span class="tag">현재 $194.94</span>
      <span class="tag good">PT평균 $253.7 (+30%)</span>
      <span class="tag">시총 ~$175B</span>
      <span class="tag warn">실적 08-27</span>
      <span class="tag bad">Chase: 관망·비적합</span>
    </p>
  </section>

  <h2>스냅샷</h2>
  <table>
    <tr><th>항목</th><th>값</th><th>해석</th></tr>
    <tr><td>가격 / 전일</td><td>$194.94 / $188.68</td><td>단기 반등, 52주 고점($329.9) 대비 −41%</td></tr>
    <tr><td>52주 고저</td><td>$61.44 – $329.88</td><td>고점 대비 크게 조정된 상태</td></tr>
    <tr><td>애널리스트 PT</td><td>$110 / $253.7 / $400 (n=40)</td><td>Strong Buy · 업사이드 +30%</td></tr>
    <tr><td>밸류</td><td>Fwd P/E ~31 · Trailing ~65 · PEG ~1.07</td><td>성장 반영 프리미엄</td></tr>
    <tr><td>유동성</td><td>ADV ~4,300만주</td><td>초대형 — 체결 리스크 없음</td></tr>
    <tr><td>베타</td><td>~2.20</td><td>시장 대비 고변동</td></tr>
    <tr><td>다음 실적</td><td>2026-08-27</td><td>Q2 FY27 · EPS컨센서스 ~$0.93</td></tr>
  </table>

  <div class="section">
  <h2>1. 한줄 Thesis</h2>
  <p><b>AI 데이터센터의 ‘연결층+커스텀 실리콘’ 수혜주.</b> Q1 FY27 매출 $2.42B(+28% YoY), FY27~$11.5B / FY28~$16.5B로 아웃룩 상향.
  다만 시총 ~$175B·주가 ~$195로 <b>소형/중형 모멘텀 집중 포트(현금~$945)에는 구조적으로 맞지 않음</b>. 추격보다 관망.</p>
  {im("01")}
  <div class="easy"><b>쉽게:</b> 엔비디아 GPU만 사는 게 아니라, GPU끼리 연결하는 광케이블 칩·스위치·고객 맞춤 AI칩도 폭발적으로 필요해짐. 마벨이 그 쪽을 팜.</div>
  </div>

  <div class="section">
  <h2>2. 섹터 · 특성 · 시총</h2>
  <p><b>섹터</b> Technology · Semiconductors &nbsp;|&nbsp; <b>특성</b> 데이터센터 네트워킹·광학·커스텀 ASIC &nbsp;|&nbsp; <b>시총</b> ~$175B (메가캡)</p>
  <table>
    <tr><th>축</th><th>내용</th></tr>
    <tr><td>포지션</td><td>하이퍼스케일러 AI CapEx 사이클의 interconnect / custom XPU 공급자</td></tr>
    <tr><td>경쟁</td><td>Broadcom(스위치·커스텀), NVIDIA(네트워킹), Alchip 등 ASIC 파운드리 파트너</td></tr>
    <tr><td>고객 집중</td><td>소수 초대형 클라우드에 매출 편중 — 디자인윈·점유율 변동이 주가 진폭 키움</td></tr>
    <tr><td>재무 체력</td><td>현금~$3.8B · 총부채~$5.3B · 자기자본~$18.2B · FCF 분기 $0.3–0.5B급</td></tr>
  </table>
  <div class="gloss">
    <b>용어</b> · <b>XPU</b>: 하이퍼스케일러가 자체 설계하는 AI/가속 칩 총칭.
    · <b>XPU-attach</b>: XPU에 붙는 NIC·CXL 메모리 등 주변 실리콘.
    · <b>Interconnect</b>: 칩·랙·데이터센터 간 고속 연결(광학 DSP, 트랜시버 등).
    · <b>CPO/NPO</b>: 패키지/보드에 광을 더 가깝게 붙이는 차세대 광학 형태.
  </div>
  </div>

  <div class="section">
  <h2>3. 핵심 제품 · 수익 구조</h2>
  <p>한줄: <b>클라우드·온프레미스 AI 인프라용 SoC·광학·스위치·커스텀 ASIC</b>을 설계·판매.</p>
  {im("02")}
  <table>
    <tr><th>엔드마켓 (Q1 FY27)</th><th>매출</th><th>비중</th><th>YoY</th></tr>
    <tr><td>Data Center</td><td>$1,833M</td><td>76%</td><td>+27%</td></tr>
    <tr><td>Communications &amp; Other</td><td>$585M</td><td>24%</td><td>+29%</td></tr>
    <tr><td><b>합계</b></td><td><b>$2,418M</b></td><td>100%</td><td><b>+28%</b></td></tr>
  </table>
  <h3>성장 엔진 (경영진 메시지)</h3>
  <ul>
    <li><b>광학·인터커넥트</b>: 800G / 1.6T scale-out, NPO·CPO scale-up, DCI — FY27 interconnect +70%대 가이던스 언급</li>
    <li><b>커스텀 실리콘</b>: FY27 +20%+ → FY28 <b>2배 이상</b> 성장 전망 · 장기 FY29 custom &gt;$10B 목표 논의</li>
    <li><b>이더넷 스위치</b>: 51.2T scale-out · FY27 스위치 &gt;$600M, FY28 연환산 &gt;$1B 런레이트 언급</li>
  </ul>
  <div class="easy"><b>쉽게:</b> 매출 4분의 3이 데이터센터. AI 붐이 커질수록 ‘칩끼리 연결하는 부품’과 ‘클라우드가 직접 만드는 AI칩’ 둘 다 마벨 매출로 들어옴.</div>
  </div>

  <div class="section">
  <h2>4. 재무 · 컨센서스 · 서프라이즈 · 전략</h2>
  {im("03")}
  {im("04")}
  <table>
    <tr><th>지표</th><th>수치</th></tr>
    <tr><td>Q1 FY27 매출</td><td>$2,418M (+28% YoY, +9% QoQ)</td></tr>
    <tr><td>GAAP / Non-GAAP GM</td><td>52.1% / 58.9%</td></tr>
    <tr><td>Non-GAAP EPS (최근)</td><td>~$0.80 (컨센서스 대비 소폭~인라인; 일부 집계 +6% Beat)</td></tr>
    <tr><td>Q2 FY27 매출 가이드</td><td>$2,700M +/-5% (~+35% YoY)</td></tr>
    <tr><td>FY27 / FY28 매출 아웃룩</td><td>~$11.5B (~+40%) / ~$16.5B (~+45%)</td></tr>
    <tr><td>DC FY27 / FY28</td><td>~+50% / ~+55% YoY (가이던스)</td></tr>
    <tr><td>컨센서스</td><td>Strong Buy · PT평균 $253.7 (+30% 업사이드)</td></tr>
  </table>
  {im("05")}
  <p><b>서프라이즈:</b> 최근 4분기 Non-GAAP EPS는 <b>대체로 소폭 Beat(3/4)</b>, 한 분기는 −0.5% 미세 Miss.
  ‘서프라이즈 머신’ 타입(INDV/ECPG류)은 아님 — <b>가이던스 상향·성장 가속</b>이 주 촉매.</p>
  <p><b>전략 비교 (사용자 모델):</b></p>
  <ul>
    <li>펀더멘털·성장 스토리: <b>강</b> (AI infra multi-year)</li>
    <li>실적 서프라이즈 알파: <b>중하</b> (이미 기대치 높음)</li>
    <li>PT 대비 여유: <b>중상</b> (+30%, 고점 대비는 −41% 조정)</li>
    <li>포지션 사이징: <b>부적합</b> — 메가캡 1주~$195, 집중 3–4종목 소형 전략과 충돌</li>
  </ul>
  <div class="box">
    <b>실행 전략:</b> 신규 진입·이벤트 리저브 배정 <u>비추천</u>.
    NEO ≫ AMRX &gt; ALKS 우선순위 유지. MRVL은 관심 리스트(워치)만.
    만약 예외적으로 산다면 비중 상한 1주(또는 포트의 5% 미만) + 08-27 실적 후 확인.
  </div>
  </div>

  <div class="section">
  <h2>5. 섹터 뉴스 · 촉매 · 리스크</h2>
  <table>
    <tr><th>구분</th><th>내용</th><th>출처/시점</th></tr>
    <tr><td>실적</td><td>Q1 FY27 발표, FY27/28 매출 아웃룩 대폭 상향</td><td>2026-05-27 IR / 8-K</td></tr>
    <tr><td>다음 콜</td><td>Q2 FY27 실적 ~2026-08-27</td><td>Yahoo Calendar</td></tr>
    <tr><td>배당</td><td>Ex 2026-07-10 · 지급 07-30 · 수익률 ~0.13%</td><td>yfinance</td></tr>
    <tr><td>테마</td><td>1.6T 광학 램프, 커스텀 XPU 파이프라인, 스위치 $1B 런레이트</td><td>Earnings call</td></tr>
    <tr><td>경쟁 이슈</td><td>일부 하이퍼스케일러 ASIC 점유(예: Trainium 세대) 변동 보도 — 커스텀 성장률이 CapEx보다 낮을 수 있음</td><td>시장 체크/리서치</td></tr>
  </table>
  <p class="small">출처: Marvell Q1 FY27 8-K/Exhibit 99.1, earnings call 요약, Yahoo Finance, 애널리스트 컨센서스(yfinance).</p>
  <div class="gloss">
    <b>추가 용어</b> · <b>Design win</b>: 고객 제품에 채택 확정(매출은 양산 후).
    · <b>Bookings</b>: 수주 — 매출보다 선행.
    · <b>Gross margin</b>: 매출총이익률 — Non-GAAP는 SBC·무형자산상각 등 조정.
    · <b>Hyperscaler CapEx</b>: 초대형 클라우드의 설비투자(서버·네트워크·칩).
  </div>
  </div>

  <div class="section">
  <h2>6. Bull / Base / Bear · Breakers</h2>
  {im("06")}
  <table>
    <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
    <tr><td>Bull</td><td>$290–360</td><td>FY28 가이던스 재상향, custom 배증 가시화, 멀티플 재확장</td></tr>
    <tr><td>Base</td><td>$220–260</td><td>FY27~$11.5B 경로 유지, PT평균($254) 수렴</td></tr>
    <tr><td>Bear</td><td>$140–175</td><td>클라우드 CapEx 둔화, 디자인윈 지연/점유 상실, GM 압박</td></tr>
  </table>
  <p><b>ABC 목표가:</b> $220 / $254 / $320 &nbsp;|&nbsp; <b>Breaker(탈락):</b> FY27 DC 성장 가이던스 하향 · Q2 매출 가이드 미스 · 주요 커스텀 프로그램 취소/이관</p>
  <p><b>무효화 가격 힌트:</b> 추세 추격 관점이라면 최근 스윙 저점·$170대 이탈 시 스토리 재검토 (베타 2.2 — 와이드스탑 필요).</p>
  </div>

  <div class="section">
  <h2>7. 결론 표 · Chase RR</h2>
  {im("07")}
  <table class="conclusion">
    <tr><td>섹터</td><td>Technology · Semiconductors (AI 데이터센터 인프라)</td></tr>
    <tr><td>핵심</td><td>광학·인터커넥트 + 커스텀 XPU/XPU-attach + 이더넷 스위치</td></tr>
    <tr><td>EPS</td><td>최근 4Q 소폭 Beat 위주 (3/4) — 서프라이즈보다 가이던스 상향형</td></tr>
    <tr><td>신규진입</td><td><b>비추천</b> (관망). 예외 시 08-27 실적 후 + 비중 최소화</td></tr>
    <tr><td>탈락</td><td>DC/커스텀 가이던스 컷, 주요 고객 ASIC 이탈</td></tr>
    <tr><td>Chase</td><td><b>관망·비적합</b> — 메가캡·고단가, 소형 모멘텀 집중전략과 불일치</td></tr>
    <tr><td>비중 상한</td><td>워치리스트 전용 / 예외 시 ≤1주 또는 &lt;5%</td></tr>
    <tr><td>이벤트 리저브</td><td>배정 없음 (NEO ≫ AMRX &gt; ALKS 유지)</td></tr>
  </table>
  <div class="easy">
    <b>한줄 결론:</b> 사업은 좋지만 <u>당신 봇/포트 규칙에는 안 맞음</u>.
    심층분석 점수는 ‘관심’이지 ‘매수’가 아님. 수요일 입금($811)은 NESR 분할·NEO/AMRX 이벤트에 남겨둘 것.
  </div>
  </div>

  <h2>부록 · 데이터 메모</h2>
  <p class="small">
    가격·시총·PT·베타·실적일: Yahoo Finance / yfinance ({ASOF}).
    세그먼트·가이던스: Marvell Q1 FY27 earnings release (Exhibit 99.1, SEC).
    EPS surprise: yfinance earnings_history (Non-GAAP).
    FY26 연간 ~$8.2B는 분기 합산 근사. DC 성장 드라이버 막대는 경영진 코멘트의 상대 가중 시각화(공식 매출 배분 공시 아님).
    본 자료는 투자 권유가 아니며, 실행은 사용자 리스크 한도 내에서.
  </p>
</body>
</html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_revenue_trend(),
        "04": chart_outlook(),
        "05": chart_eps_surprise(),
        "06": chart_scenarios(),
        "07": chart_position(),
    }
    html = build_html(charts)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    doc = HTML(filename=str(OUT_HTML))
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        doc.write_pdf(str(p))
        print(f"PDF {p} {p.stat().st_size}")


if __name__ == "__main__":
    main()
