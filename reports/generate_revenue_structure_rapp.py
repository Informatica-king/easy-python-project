#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(RAPP) — Rapport Therapeutics · RAP-219 / 협업매출 + 초보용 설명 + WeasyPrint PDF."""

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
ASOF = "2026-07-26"
OUT_PDF = [
    Path("/opt/cursor/artifacts/RAPP_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/RAPP_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/RAPP_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/RAPP_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/rapp")
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
    "bio": "#7c3aed",
    "pink": "#be185d",
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
        (0.1, 0.7, 1.75, 1.6, "RAP\n플랫폼", C["sand"]),
        (2.05, 0.7, 1.8, 1.6, "RAP-219\nTARPγ8 NAM", C["bio"]),
        (4.05, 0.7, 1.8, 1.6, "FOS Ph3\n+ 적응증 확장", C["teal"]),
        (6.05, 0.7, 1.75, 1.6, "Tenacia\nGreater China", C["gold"]),
        (8.0, 0.7, 1.75, 1.6, "협업·로열티\n→ 제품매출", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = "white" if c in (C["bio"], C["teal"], C["navy"], C["gold"]) else C["ink"]
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    for x in (1.9, 3.9, 5.9, 7.85):
        ax.annotate("", xy=(x + 0.12, 1.5), xytext=(x - 0.05, 1.5),
                    arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6))
    ax.set_title("RAPP 가치 사슬 — 플랫폼 → 임상자산 → 지역 라이선스 → 미래 제품", fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_revenue_today() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    # FY2023-25 product rev = 0; Q1'26 collab 20
    labels = ["제품매출\n(FY23–25)", "Q1'26\n협업매출"]
    vals = [0.1, 20]  # visual floor for zero
    colors = [C["sand"], C["gold"]]
    bars = ax.bar(labels, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("현재 매출 구조", fontproperties=PROP_B, fontsize=11)
    ax.text(0, 1.2, "실질 $0", ha="center", fontproperties=PROP, fontsize=8, color=C["muted"])
    ax.text(1, 21.2, "$20M\n(Tenacia upfront)", ha="center", fontproperties=PROP, fontsize=8, color=C["ink"])
    ax.set_ylim(0, 28)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)

    ax = axes[1]
    sizes = [20, 308]
    labs = ["Upfront\n$20M\n(수취)", "마일스톤\n최대 ~$308M\n(잠재)"]
    ax.pie(
        sizes, labels=labs, colors=[C["gold"], C["teal"]], startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8),
    )
    ax.set_title("Tenacia Greater China 딜 규모", fontproperties=PROP_B, fontsize=11)
    fig.suptitle("수익은 ‘제품’이 아니라 ‘라이선스 현금’부터", fontproperties=PROP_B, fontsize=12, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_today.png")


def chart_future_stack() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")
    layers = [
        (0.3, 3.1, 9.4, 0.85, C["navy"], "white", "④ 제품 매출 (미승인) — US/RoW 상업화 · LAI 연장 · 회사 주장 US FOS >$2B 기회"),
        (0.3, 2.15, 9.4, 0.8, C["teal"], "white", "③ 로열티 — Greater China 순매출 mid-single ~ mid-teens (승인·판매 후)"),
        (0.3, 1.2, 9.4, 0.8, C["gold"], C["ink"], "② 마일스톤 — 개발·상업 합산 최대 ~$308M (확률·시점에 의존)"),
        (0.3, 0.25, 9.4, 0.8, C["bio"], "white", "① 협업 upfront — Q1'26 $20M 인식 (현재 유일 영업매출)"),
    ]
    for x, y, w, h, c, tc, t in layers:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.2, color=tc)
    ax.set_title("미래 수익 스택 (아래→위 = 현재→장기)", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "03_future_stack.png")


def chart_pipeline() -> Path:
    fig, ax = plt.subplots(figsize=(9.2, 4.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.2)
    ax.axis("off")
    # columns: Discovery / IND / Ph1 / Ph2 / Ph3 / Market
    stages = ["Discovery", "IND", "Ph1", "Ph2", "Ph3", "Market"]
    for i, s in enumerate(stages):
        ax.text(0.8 + i * 1.5, 4.85, s, ha="center", fontproperties=PROP_B, fontsize=8, color=C["muted"])
        ax.plot([0.8 + i * 1.5, 0.8 + i * 1.5], [0.3, 4.6], color="#e7e5e4", lw=0.8)

    programs = [
        (3.8, "RAP-219 FOS", "Ph3 개시 목표 2Q'26", C["bio"], 4),
        (2.9, "RAP-219 Bipolar", "Ph2 탑라인 목표 4Q'26", C["teal"], 3),
        (1.5, "RAP-219 PGTCS", "Ph3 목표 1H'27", C["teal2"], 2),
        (1.2, "RAP-219 LAI", "IND-enabling · Ph1 PK '27", C["gold"], 1),
        (0.6, "α6β4 nAChR", "만성통·편두통 · IND-enabling", C["sand"], 0),
    ]
    for x_end, name, note, color, row in programs:
        y = 0.55 + row * 0.85
        ax.add_patch(
            FancyBboxPatch((0.35, y), x_end + 0.9, 0.65,
                           boxstyle="round,pad=0.02,rounding_size=0.08",
                           facecolor=color, edgecolor="white", lw=1.2, alpha=0.92)
        )
        tc = C["ink"] if color in (C["sand"], C["gold"], C["teal2"]) else "white"
        ax.text(0.55, y + 0.38, name, ha="left", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
        ax.text(0.55, y + 0.12, note, ha="left", va="center", fontproperties=PROP, fontsize=7, color=tc)
    ax.set_title("파이프라인 맵 — RAP-219 ‘파이프라인-인-어-프로덕트’", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "04_pipeline.png")


def chart_opex_cash() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    years = ["FY23", "FY24", "FY25", "Q1'26\n(연환산×4)"]
    rd = [28.0, 60.9, 94.8, 32.7 * 4]
    ga = [8.2, 22.1, 30.3, 11.5 * 4]
    x = range(len(years))
    ax.bar(x, rd, color=C["bio"], label="R&D", width=0.55)
    ax.bar(x, ga, bottom=rd, color=C["slate"], label="G&A", width=0.55)
    ax.set_xticks(list(x))
    ax.set_xticklabels(years, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("영업비용 추이 (적자 엔진)", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8)
    ax.text(0.02, -0.22, "Q1 연환산은 Ph3 가속 시 과소/과대 가능 — 참고용", transform=ax.transAxes,
            fontproperties=PROP, fontsize=7, color=C["muted"])

    ax = axes[1]
    labels = ["YE'24", "YE'25", "3/31'26"]
    cash = [305.3, 490.5, 476.8]
    bars = ax.bar(labels, cash, color=[C["sand"], C["teal"], C["navy"]], width=0.55)
    ax.set_ylabel("현금+단기투자 (M)", fontproperties=PROP)
    ax.set_title("현금 포지션 · 런웨이 2H'29", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, cash):
        ax.text(b.get_x() + b.get_width() / 2, v + 8, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 580)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "05_opex_cash.png")


def chart_deal_vs_burn() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    cats = ["Tenacia\nupfront", "Q1'26\nOpEx", "FY25\nR&D", "마일스톤\n최대(이론)"]
    vals = [20, 44.2, 94.8, 308]
    colors = [C["gold"], C["red"], C["bio"], C["teal"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("딜 현금 vs 소진 규모 (스케일 감각)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 6, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 360)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    fig.tight_layout()
    return save_fig(fig, "06_deal_vs_burn.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    names = ["Bear", "Base", "Bull"]
    lows = [18, 36, 55]
    highs = [28, 55, 85]
    colors = [C["red"], C["teal"], C["navy"]]
    ax.barh(names, [h - l for l, h in zip(lows, highs)], left=lows, color=colors, height=0.55)
    ax.axvline(40.68, color=C["gold"], ls="--", lw=1.5)
    ax.text(42, 2.35, "현재 ~41", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.axvline(56.7, color="#2563eb", ls=":", lw=1.2)
    ax.text(58, -0.55, "PT평균 ~57", fontproperties=PROP, fontsize=7.5, color="#2563eb")
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        mid = (lo + hi) / 2
        ax.text(mid, i, f"{lo}–{hi}", ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=9)
    ax.set_xlim(10, 95)
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("Bull / Base / Bear (12M · 임상·자금 중심)", fontproperties=PROP_B, fontsize=11)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP_B)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    items = [
        (0.25, 2.5, 3.0, 1.2, C["bio"], "white", "2Q'26\nFOS Ph3 개시"),
        (3.5, 2.5, 3.0, 1.2, C["teal"], "white", "4Q'26\nBipolar Ph2 탑라인"),
        (6.75, 2.5, 3.0, 1.2, C["navy"], "white", "1H'27\nPGTCS Ph3 계획"),
        (0.25, 0.4, 4.7, 1.5, C["gold"], C["ink"], "2027~\nLAI Ph1 PK · α6 임상진입"),
        (5.2, 0.4, 4.55, 1.5, C["sand"], C["ink"], "상업화는 승인 후\n(미국·RoW 제품 + China 로열티)"),
    ]
    for x, y, w, h, c, tc, t in items:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=9, color=tc)
    ax.set_title("촉매 캘린더 — 주가·가치는 임상 이벤트가 지배", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    rows = [
        (0.3, 2.6, 9.4, 1.0, C["navy"], "white", "포트 역할: 미보유 · Chase 상·08-06 · TA 분할OK는 ‘후보’일 뿐"),
        (0.3, 1.4, 4.5, 0.95, C["teal"], "white", "관심 금액\n$40–60 극소 위성"),
        (5.0, 1.4, 4.7, 0.95, C["gold"], C["ink"], "타이밍\nNEO 이후 · 08-06 전후"),
        (0.3, 0.25, 9.4, 0.95, C["sand"], C["ink"], "지금: 제품매출 $0 · 임상 바이너리 · NEO/현금 우선 · 과열 추격 금지"),
    ]
    for x, y, w, h, c, tc, t in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
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
      @bottom-center {{ content:"RAPP 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #7c3aed; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#7c3aed; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#f5f3ff 0%,#e8eef5 55%,#fdf2f8 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#ddd6fe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.good {{ background:#bbf7d0; }}
    .tag.bad {{ background:#fecdd3; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#f5f3ff; border-left:4px solid #7c3aed; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#7c3aed; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#7c3aed; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>RAPP 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>RAPP 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Rapport Therapeutics · CNS 정밀 소분자 · RAP-219</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1'26 실적(5/7) · 다음 실적 ~08-06 · 임상단계</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~$41</div><div class="s">시총 ~$1.95B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~$57</div><div class="s">업사이드 ~+39%</div></span>
    <span class="kpi"><div class="l">Q1 협업매출</div><div class="v">$20M</div><div class="s">제품매출 $0</div></span>
    <span class="kpi"><div class="l">현금</div><div class="v">$477M</div><div class="s">런웨이 2H'29</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">Chase 상·08-06 · TA 분할OK</span>
    <span class="tag warn">임상 바이너리</span>
    <span class="tag bad">제품매출 없음</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>제품으로 버는 회사가 아니라, RAP-219 임상·승인 옵션에 시총을 붙인 회사.</b>
FY23–25 제품매출 <b>$0</b>. Q1'26에 Tenacia Greater China 라이선스로
협업매출 <b>$20M</b>이 처음 인식됨. 본업 현금은 <b>R&amp;D 소진</b>이고,
기업가치는 <b>FOS Ph3·조증 Ph2·LAI</b> 성공 확률에 연동.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 지금 ‘매출’이라고 보이는 돈은 <b>중국 판권 선금</b>에 가깝다.
약 팔아서 번 돈이 아니다. 진짜 수익구조는 <u>나중에 약이 팔리면</u> 생긴다.</div>
{gloss([
    ("임상단계 (clinical-stage)", "승인·상업화 전 — 제품매출 없이 개발비로 적자."),
    ("협업매출 (collaboration revenue)", "라이선스 upfront·연구비 등 파트너 계약으로 인식하는 매출."),
    ("RAP / TARPγ8", "수용체 결합 단백질. RAP-219는 뇌 특정 부위의 AMPA 수용체만 조절."),
])}

<h2>1. 어디서 돈이 오나 — 지금 vs 나중</h2>
{fig_block(charts['02'], '현재 매출')}
{fig_block(charts['03'], '미래 수익 스택')}
<table>
  <tr><th>수익원</th><th>상태</th><th>규모·조건</th></tr>
  <tr><td>제품(처방약) 매출</td><td>없음</td><td>승인 전 · FY23–25 Operating Revenue $0</td></tr>
  <tr><td>Tenacia upfront</td><td><b>인식됨</b></td><td>Q1'26 협업매출 <b>$20M</b> (Greater China RAP-219)</td></tr>
  <tr><td>개발·상업 마일스톤</td><td>잠재</td><td>합산 최대 약 <b>$308M</b> + 기타 지급</td></tr>
  <tr><td>China 로열티</td><td>잠재</td><td>순매출 <b>mid-single ~ mid-teens</b> (승인·판매 후)</td></tr>
  <tr><td>이자수익</td><td>있음</td><td>Q1'26 ~$4.4M · 현금·단기투자 운용</td></tr>
  <tr><td>미국·RoW 제품</td><td>미실현</td><td>Rapport 보유 · FOS 등 승인 시 본업</td></tr>
</table>
<p class="small">Tenacia는 Greater China(중국·홍콩·마카오·대만) 개발·상업화 담당.
Rapport는 그 외 전 세계 권리 유지.</p>
<div class="easy"><b>쉽게:</b> 지금은 <b>선금 한 방</b> + <b>예금 이자</b>.
앞으로 돈이 되려면 ①임상 성공 → ②FDA 등 승인 → ③약 판매(또는 추가 지역 딜) 순서다.</div>
{gloss([
    ("Upfront", "계약 체결 시 받는 선지급금. 일회성에 가깝다."),
    ("Milestone", "임상·허가·매출 목표 달성 시 추가 지급. 확률·시점이 불확실."),
    ("Royalty", "판매액의 일정 %. 지속 매출에 가깝지만 승인 후에야 의미 있음."),
])}

<h2>2. 성장 엔진 — RAP-219 파이프라인</h2>
{fig_block(charts['04'], '파이프라인')}
{fig_block(charts['08'], '촉매')}
<ul>
  <li><b>FOS (국소발작)</b> — Ph2a에서 임상발작 중앙값 큰 폭 감소 보고 · <b>Ph3 2Q'26 개시</b> 목표</li>
  <li>Ph2a 추적: weeks 9–12 임상발작 중앙값 <b>−90%</b> (베이스라인 대비, 회사 발표)</li>
  <li><b>Bipolar mania</b> — Ph2 탑라인 <b>4Q'26</b>로 앞당김 · 확증 근거로 쓰일 수 있게 SAP·등록 확대</li>
  <li><b>PGTCS</b> — Ph3 목표 <b>1H'27</b> · 뇌전증 프랜차이즈 확장</li>
  <li><b>LAI (장기 주사)</b> — IND-enabling · Ph1 PK <b>2027</b> · 독점·복약 편의 스토리</li>
  <li><b>α6β4</b> — 만성통·편두통 비마약성 후보 · IND-enabling</li>
</ul>
<div class="box"><b>상업 내러티브(회사):</b> 승인 시 US FOS 기회 <b>&gt;$2B</b> 언급.
이는 TAM/피크세일즈 가정치이며, 현재 손익계산서에 들어오는 숫자가 아님.</div>
{gloss([
    ("FOS", "Focal Onset Seizures — 국소 시작 발작. RAP-219 리드 적응증."),
    ("NAM", "Negative Allosteric Modulator — 수용체 활성을 간접적으로 억제."),
    ("LAI", "Long-Acting Injectable — 장기 지속형 주사 제형."),
])}

<h2>3. 비용 · 현금 · 손익</h2>
{fig_block(charts['05'], 'OpEx·현금')}
{fig_block(charts['06'], '딜 vs 소진')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>Q1'26 협업매출</td><td>$20.0M (YoY $0 → 첫 인식)</td></tr>
  <tr><td>Q1'26 R&amp;D / G&amp;A</td><td>$32.7M / $11.5M (합 $44.2M)</td></tr>
  <tr><td>Q1'26 순손실</td><td>$19.9M (전년 $24.1M → 협업매출로 축소)</td></tr>
  <tr><td>FY25 R&amp;D / 총비용</td><td>~$94.8M / ~$125M · 순손실 ~$111M</td></tr>
  <tr><td>현금+단기투자 (3/31/26)</td><td><b>$476.8M</b> (YE'25 $490.5M)</td></tr>
  <tr><td>런웨이(회사)</td><td><b>2029년 하반기</b>까지 OpEx·CapEx 충당 예상</td></tr>
  <tr><td>다음 실적</td><td>~<b>2026-08-06</b> · Rev 컨센 $0 · EPS 컨센 약 −$0.99</td></tr>
</table>
<div class="easy"><b>쉽게:</b> $20M 선금은 분기 비용(~$44M)보다 작다.
진짜 방패는 <b>현금 $477M</b>이다. Ph3가 비싸지면 런웨이가 줄고, 실패하면 희석 위험이 커진다.</div>
{gloss([
    ("Runway", "현재 현금으로 적자를 버티는 예상 기간."),
    ("희석", "추가 자금조달로 주식 수가 늘어 기존 지분 가치가 줄어듦."),
    ("EPS 컨센 −$1", "적자 기업 — 서프라이즈보다 현금·임상 업데이트가 중요."),
])}

<h2>4. 민감도 · 시나리오</h2>
{fig_block(charts['07'], '주가 시나리오')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>55–85</td><td>Ph3 순항·조증 데이터 양호·PT(~57) 상회·추가 지역딜</td></tr>
  <tr><td>Base</td><td>36–55</td><td>PT 수렴 · 임상 진행 · 런웨이 유지</td></tr>
  <tr><td>Bear</td><td>18–28</td><td>효능/안전 이슈 · Ph3 지연 · 대규모 희석</td></tr>
</table>
<p><b>Breaker:</b> FOS Ph3 실패·안전성 · 조증 탑라인 실망 · 현금 소진 가속·희석 ·
경쟁 CNS 자산 출현 · Tenacia/파트너 실행 리스크</p>
{gloss([
    ("바이너리", "임상 성공/실패가 시총을 크게 흔드는 구조."),
    ("PT 업사이드", "목표가 할인은 분석가 가정의 합 — 임상 리스크를 충분히 반영하지 않을 수 있음."),
])}

<h2>5. 포트폴리오 위치</h2>
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>항목</th><th>권고</th></tr>
  <tr><td>역할</td><td>미보유 <b>워치</b> · Chase 상·08-06 · TA 분할OK = 기술적 후보</td></tr>
  <tr><td>금액</td><td>관심 시 <b>$40–60 극소</b> (임상 위성 · SLS급 바이너리와 同類 취급)</td></tr>
  <tr><td>타이밍</td><td><b>NEO 07-28 이후</b> · 이상적으로 <b>08-06</b> 현금/업데이트 확인</td></tr>
  <tr><td>하지 말 것</td><td>제품매출 착각 · Ph3 전 풀베팅 · NEO 이벤트 예산 잠식</td></tr>
</table>
<div class="easy"><b>한줄 결론:</b> 수익구조의 실체는 <u>협업 선금 + 미래 승인 옵션</u>.
스토리(Ph2a·중국딜·런웨이)는 강하지만, 계좌에는 <b>NEO·현금 다음의 극소 위성</b>만 맞다.</div>

<h2>부록 · 출처</h2>
<p class="small">
Rapport Q1 2026 earnings release (2026-05-07) · Tenacia collaboration PR ·
Corporate presentation (cash runway, catalysts, US FOS opportunity) ·
yfinance 가격·PT ({ASOF}).
시나리오는 예시 밴드(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 RAPP · 기준 {ASOF} · WeasyPrint + NanumGothic</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_revenue_today(),
        "03": chart_future_stack(),
        "04": chart_pipeline(),
        "05": chart_opex_cash(),
        "06": chart_deal_vs_burn(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    html = build_html(charts)
    html, _px = build_and_insert_price("RAPP", CHART_DIR, html)
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
