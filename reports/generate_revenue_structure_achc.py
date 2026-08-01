#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(ACHC) — Acadia 행동건강 + 법적리스크 전용 섹션 + 경쟁점유/믹스 PDF."""

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
PX = 29.62
PT = 33.39
H52 = 35.83
UPSIDE = PT / PX - 1.0
EARN = "07-28"  # Q2 reported
OUT_PDF = [
    Path("/opt/cursor/artifacts/ACHC_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/ACHC_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/ACHC_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/ACHC_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/achc")
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
    "achc": "#0e7490",
    "acute": "#0369a1",
    "spec": "#7c3aed",
    "ctc": "#c2410c",
    "rtc": "#059669",
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
        (0.1, 0.7, 1.85, 1.6, "환자·페이여\nMedicaid 중심", C["sand"]),
        (2.15, 0.7, 1.75, 1.6, "Acute\n정신입원", C["acute"]),
        (4.1, 0.7, 1.75, 1.6, "Specialty\n중독·섭식 등", C["spec"]),
        (6.05, 0.7, 1.7, 1.6, "CTC\n아편 MAT", C["ctc"]),
        (7.95, 0.7, 1.75, 1.6, "RTC\n주거치료", C["rtc"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c == C["sand"] else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("ACHC 가치사슬 — 279시설·~12.6k병상 · 행동건강 전 스펙트럼",
                 fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_revenue_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9))
    ax = axes[0]
    labels = ["Acute\n57%", "CTC\n16%", "Specialty\n15%", "RTC\n11%"]
    vals = [57.1, 16.3, 15.4, 11.1]
    colors = [C["acute"], C["ctc"], C["spec"], C["rtc"]]
    ax.pie(
        vals, labels=labels, colors=colors,
        textprops={"fontproperties": PROP, "fontsize": 8},
        startangle=90, wedgeprops=dict(width=0.48, edgecolor="white"),
    )
    ax.set_title("Q2'26 서비스 매출 믹스", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    segs = [("Acute", 494.6), ("CTC", 141.2), ("Specialty", 133.5), ("RTC", 96.5)]
    names = [s[0] for s in segs]
    fvals = [s[1] for s in segs]
    bars = ax.barh(names[::-1], fvals[::-1],
                   color=[C["rtc"], C["spec"], C["ctc"], C["acute"]], height=0.55)
    ax.set_xlabel("$M", fontproperties=PROP)
    ax.set_title("Q2'26 라인별 매출 ($M) · 총 $865.8M", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, fvals[::-1]):
        ax.text(v + 6, b.get_y() + b.get_height() / 2, f"${v:.0f}",
                va="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_mix.png")


def chart_payor_mix() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    cats = ["Medicaid", "Commercial", "Medicare", "Self-pay", "Other"]
    vals = [61.9, 21.6, 14.0, 1.5, 1.0]
    colors = [C["acute"], C["teal"], C["navy"], C["gold"], C["slate"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("% of revenue", fontproperties=PROP)
    ax.set_title("H1'26 페이여 믹스 — 정부 프로그램 의존도 높음",
                 fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v:.1f}%",
                ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "03_payor_mix.png")


def chart_growth() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.7))
    cats = ["Acute\n(보고)", "Acute\n(정규화)", "Specialty", "CTC", "RTC", "Total\n(보고)", "Same-fac\n정규화"]
    vals = [0.0, 5.7, -8.4, 0.0, 11.6, 0.0, 3.2]
    colors = [C["green"] if v >= 0 else C["red"] for v in vals]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.axhline(0, color=C["muted"], lw=0.8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("Q2'26 성장 — Acute 정규화 +6%대 · Specialty −8% · RTC +12%",
                 fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (0.4 if v >= 0 else -1.2),
                f"{v:+.1f}%", ha="center", fontproperties=PROP, fontsize=7.5)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)
    fig.tight_layout()
    return save_fig(fig, "04_growth.png")


def chart_legal_timeline() -> Path:
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.2)
    ax.axis("off")
    items = [
        (0.2, 4.0, 4.6, 0.95, C["slate"], "white",
         "2023–24 · Desert Hills\n배심 $485M → 합의 $400M 지급(종결)"),
        (5.1, 4.0, 4.6, 0.95, C["navy"], "white",
         "2025-11 · 증권집단\n합의 $179M (보험 $31.5M) · 2026-04 승인"),
        (0.2, 2.7, 4.6, 0.95, C["red"], "white",
         "진행중 · DOJ Criminal\nAcute 입원·LOS·빌링 대배심"),
        (5.1, 2.7, 4.6, 0.95, C["red"], "white",
         "진행중 · SEC\nAcute 유사 + CTC 정보요청"),
        (0.2, 1.4, 4.6, 0.95, C["ctc"], "white",
         "2026-05 · Fashion Valley\n배심 $105M (징벌 $70M) · 항소예정"),
        (5.1, 1.4, 4.6, 0.95, C["gold"], C["ink"],
         "2026 H1 · Sandoval\n합의원칙 $15M · 보험초과 $13.8M"),
        (0.2, 0.2, 9.5, 0.95, C["sand"], C["ink"],
         "추가 오픈: 2025 증권집단(Kachrodia·기각신청 기각 2026-07) · Desert Hills 6번째 소송 · 파생소송 합의원칙"),
    ]
    for x, y, w, h, c, tc, t in items:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.4)
        )
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8, color=tc)
    ax.set_title("법적 분쟁 타임라인 — 종결 vs 진행중 (10-Q as of 2026-06-30)",
                 fontproperties=PROP_B, fontsize=11, pad=4)
    return save_fig(fig, "05_legal_timeline.png")


def chart_legal_pnl() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    cats = ["조사·소송\n비용 H1", "Sandoval\n보험초과", "PGL 준비금\n증액", "합계\n(선택항목)"]
    vals = [19.9, 13.8, 28.6, 62.3]
    bars = ax.bar(cats, vals, color=[C["red"], C["gold"], C["ctc"], C["navy"]], width=0.55)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("H1'26 법적·관련 손익 압박", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v:.0f}",
                ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)

    ax = axes[1]
    cats2 = ["Adj EBITDA\nQ2'26", "Adj EBITDA\nQ2'25", "FY26 가이드\nAdj EBITDA"]
    vals2 = [149.2, 201.8, 602.5]  # mid of 590-615
    ax.bar(cats2, vals2, color=[C["achc"], C["sand"], C["teal"]], width=0.5)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("이익 — 법적·PGL이 Adj EBITDA 압박", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(vals2):
        ax.text(i, v + 8, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7.5)
    fig.tight_layout()
    return save_fig(fig, "06_legal_pnl.png")


def chart_legal_status() -> Path:
    fig, ax = plt.subplots(figsize=(9.2, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    rows = [
        (0.25, 2.0, 3.0, 0.95, C["red"], "white", "미해결·고위험",
         "DOJ Criminal\nSEC · 신증권집단"),
        (3.5, 2.0, 3.0, 0.95, C["ctc"], "white", "판결·변동성",
         "Fashion Valley\n$105M 항소"),
        (6.75, 2.0, 3.0, 0.95, C["green"], "white", "종결·축소",
         "증권 $179M\nDesert Hills $400M"),
        (0.25, 0.35, 9.5, 1.35, C["sand"], C["ink"], "",
         "투자 관점: 탑라인(Acute·RTC)은 돌아가지만, 법적비용·PGL·징벌적 판결이 "
         "현금·마진·멀티플을 깎는 구조. 부채비율(순레버리지 ~4.1x)과 겹치면 리스크 프리미엄 유지."),
    ]
    for x, y, w, h, c, tc, title, body in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.4)
        )
        if title:
            ax.text(x + w / 2, y + h - 0.28, title, ha="center",
                    fontproperties=PROP_B, fontsize=9, color=tc)
            ax.text(x + w / 2, y + 0.32, body, ha="center",
                    fontproperties=PROP, fontsize=8, color=tc)
        else:
            ax.text(x + w / 2, y + h / 2, body, ha="center", va="center",
                    fontproperties=PROP, fontsize=8.5, color=tc)
    ax.set_title("법적 리스크 맵 — 상태별 정리", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "07_legal_status.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 14, 22, C["red"]),
        ("Base", 24, 34, C["teal"]),
        ("Bull", 36, 48, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}–{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"현재 ${PX:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT평균~${PT:.0f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 — 법적 결과·마진이 밴드폭을 좌우", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(10, 52)
    fig.tight_layout()
    return save_fig(fig, "08_scenarios.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "심층 RR 상위\n법적할인 반영", C["achc"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "코어 비추천\n위성도 소액만", C["teal"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", "DOJ/SEC 가시성\nFashion Valley 감액", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "미해결 형사·SEC · 징벌판결 · PGL·레버리지", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "Acute·RTC 수요 · Medicaid 의존 · 법적오버행", C["navy"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
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
<div class="easy"><b>쉽게:</b> ACHC는 <b>행동건강 전문</b> 상장사 중 규모가 큰 편이다.
UHS 등은 급성병원과 섞여 있어 절대 점유가 아니라 피어셋 상대 위치용이다.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> ACHC는 매출의 약 <b>57%가 Acute 정신입원</b>, CTC·Specialty·RTC가 나머지다.
피어는 급성/재활 비중이 더 크거나 혼합이다.</div>
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
      @bottom-center {{ content:"ACHC 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0e7490; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0369a1; padding-bottom:3px; color:#0e7490; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0369a1; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ecfeff 0%,#e0f2fe 55%,#fef3c7 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#cffafe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecdd3; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#ecfeff; border-left:4px solid #0e7490; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#0e7490; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0369a1; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .legal-box {{ background:#fff1f2; border:1px solid #9f1239; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#0e7490; }}
    .kpi .s {{ font-size:7.5pt; color:#0369a1; }}
    .legal-section {{ page-break-before:always; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>ACHC 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>ACHC 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Acadia Healthcare · 행동건강 시설 (Acute · Specialty · CTC · RTC)</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적({EARN} 발표) · 시총 ~$2.8B · 279시설 / ~12.6k병상</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.2f}</div><div class="s">52주고 ${H52:.2f}</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.1f}</div><div class="s">{UPSIDE*100:+.1f}%</div></span>
    <span class="kpi"><div class="l">Q2 매출</div><div class="v">$865.8M</div><div class="s">보고 YoY ~0%</div></span>
    <span class="kpi"><div class="l">Adj EBITDA</div><div class="v">$149.2M</div><div class="s">−26% YoY</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag bad">법적오버행 · DOJ/SEC 미해결</span>
    <span class="tag warn">Fashion Valley $105M</span>
    <span class="tag">Medicaid ~62%</span>
    <span class="tag warn">심층 RR 상위 · 코어 비추</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>행동건강 수요(Acute·RTC)는 돌아가지만, 법적·보험·조사 비용이 이익을 깎는 구조.</b>
Q2'26 매출 $865.8M(보고 거의 플랫 · 보충지급 정규화 시 same-facility ~+3%).
Acute 정규화 +5.7% · RTC +12% · Specialty −8% · CTC 플랫.
Adj EBITDA $149.2M(−26%) — PGL 준비금 증액·법적비용이 핵심 드래그.
주가는 PT 대비 할인({UPSIDE*100:+.0f}%)이나 <b>미해결 DOJ/SEC·징벌판결</b>이 할인 이유를 설명한다.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 정신건강·중독 치료 병원을 전국에 운영한다.
환자는 많고 Medicaid가 매출의 60%를 넘는다. 문제는 ‘환자 수’보다
<b>소송·정부조사·징벌적 판결</b>이 현금과 이익을 계속 갉아먹는 점이다.</div>
{gloss([
    ("Acute", "급성 정신건강 입원 시설 — 매출 본체(~57%)."),
    ("CTC", "Comprehensive Treatment Center — 아편 중독 MAT 외래."),
    ("RTC", "Residential Treatment Center — 주거형 치료."),
    ("PGL", "Professional & General Liability — 의료과실·일반배상 준비금."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '서비스 믹스')}
{fig_block(charts['03'], '페이여 믹스')}
<table>
  <tr><th>라인 (Q2'26)</th><th>매출</th><th>비중</th><th>YoY</th><th>메모</th></tr>
  <tr><td><b>Acute</b></td><td>$494.6M</td><td>57%</td><td>0% / <b>정규화 +5.7%</b></td><td>병상·JV 확장</td></tr>
  <tr><td>CTC</td><td>$141.2M</td><td>16%</td><td>0%</td><td>OTP·MAT · 조사 노출</td></tr>
  <tr><td>Specialty</td><td>$133.5M</td><td>15%</td><td>−8.4%</td><td>PA·폐쇄 영향</td></tr>
  <tr><td>RTC</td><td>$96.5M</td><td>11%</td><td>+11.6%</td><td>볼륨·단가</td></tr>
  <tr><td><b>합계</b></td><td><b>$865.8M</b></td><td>100%</td><td>~0% / SF정규화 ~+3%</td><td>보충지급 타이밍</td></tr>
</table>
<p class="small">페이여 H1'26: Medicaid 61.9% · Commercial 21.6% · Medicare 14.0% · Self-pay 1.5% · Other 1.0%.</p>
<div class="easy"><b>쉽게:</b> 돈의 절반 이상이 <b>급성 정신입원</b>에서 나온다.
정부가 내는 돈(Medicaid/Medicare) 비중이 높아, 정책·감사·빌링 이슈가 곧 매출 리스크다.</div>
{gloss([
    ("MAT", "Medication-Assisted Treatment — 약물보조 중독치료."),
    ("Same-facility", "기존 시설만 비교한 유기 성장."),
    ("Supplemental payment", "주 정부 보충지급 — 분기 인식 타이밍이 YoY를 왜곡."),
])}

{compete_html}

<section class="legal-section">
<h2>L. 법적 분쟁 · 진행상황 (전용 섹션)</h2>
<div class="legal-box">
<b>왜 별도 섹션인가</b><br/>
ACHC의 수익구조만 보면 Acute·RTC가 ‘괜찮아’ 보인다. 그러나 최근 수년 현금유출·마진 훼손의
상당 부분이 <b>소송·합의·정부조사·징벌배상</b>에서 나온다. 수익구조 해석과 분리해
상태(종결/진행)·규모·손익 경로를 고정한다.
</div>
{fig_block(charts['05'], '법적 타임라인')}
{fig_block(charts['07'], '상태 맵')}

<h3>L-1. 진행중 (미해결) — 최우선 모니터</h3>
<table>
  <tr><th>사건</th><th>내용</th><th>현황 (as of 2026-06-30 / 이후)</th><th>투자 함의</th></tr>
  <tr>
    <td><b>DOJ Criminal</b></td>
    <td>Acute 입원·재원일수(LOS)·빌링. W.D.Mo. 대배심 소환(2024-09, 10월 철회 후 12월 재발부). Criminal Division 주도.</td>
    <td>협력 중 · <b>잠재부채 추정 불가</b> (회사 공시)</td>
    <td>형사·과징금·CIA·프로그램 배제 꼬리위험. Acute 본체와 직결.</td>
  </tr>
  <tr>
    <td><b>SEC</b></td>
    <td>Acute 유사 정보 + <b>CTC</b> 라인 정보 요청</td>
    <td>협력 중 · 부채 추정 불가</td>
    <td>공시·지배구조·CTC 운영 리스크. DOJ와 병행.</td>
  </tr>
  <tr>
    <td><b>Fashion Valley</b></td>
    <td>CTC 자회사 고용보복 소송. 2026-05-12 배심: 보상 $35M + 징벌 $70M = <b>$105M</b></td>
    <td>회사(당사자 아님)·Fashion Valley <b>항소/사후심리 예정</b>. 감액 불확실.</td>
    <td>징벌배상·평판. CTC 운영품질 이슈 신호.</td>
  </tr>
  <tr>
    <td><b>Kachrodia 증권집단</b></td>
    <td>2020-02~2025-02 매수자 대상 Exchange Act 주장. 2025-07 소제기.</td>
    <td>기각신청 <b>2026-07-24 기각</b> → 본안 진행. 부채 추정 불가.</td>
    <td>추가 현금유출·거버넌스 오버행.</td>
  </tr>
  <tr>
    <td>Desert Hills #6</td>
    <td>기존 학대 소송 계열 6번째 (2024-01)</td>
    <td>진행 (과거 3건은 $400M 합의로 종결)</td>
    <td>잔여 민사 꼬리.</td>
  </tr>
</table>

<h3>L-2. 최근 종결·축소 (현금은 이미 나감)</h3>
<table>
  <tr><th>사건</th><th>결과</th><th>규모</th></tr>
  <tr><td>Desert Hills (Inman 등)</td><td>2023 배심 후 2024-01 합의 지급</td><td><b>$400M</b></td></tr>
  <tr><td>2019 증권집단 (St. Clair)</td><td>2025-11 합의 · 2026-04 승인</td><td><b>$179M</b> (보험회수 $31.5M)</td></tr>
  <tr><td>Sandoval (환자사망)</td><td>항소 후 2026 합의원칙</td><td>$15M (보험초과 <b>$13.8M</b> H1 비용)</td></tr>
  <tr><td>파생소송 다수</td><td>합의원칙 (법원 승인 대기)</td><td>회사: 중대손실 예상 안 함</td></tr>
</table>

<h3>L-3. 손익·현금에 찍히는 경로</h3>
{fig_block(charts['06'], '법적 관련 P&L')}
<ul>
  <li>H1'26 Transaction/legal/other <b>$44.6M</b> 중 정부조사·관련 소송 <b>$19.9M</b></li>
  <li>PGL 준비금 불리한 보험계리 조정 <b>$28.6M</b> (과거 클레임 예상 합의비 상승)</li>
  <li>Legal settlements expense <b>$13.8M</b> (Sandoval 보험초과)</li>
  <li>유효세율 상승(비공제 합의 등) → H1 NI $15.0M (전년 $38.5M)</li>
  <li>순레버리지 ~<b>4.1x</b> Adj EBITDA — 법적 현금유출과 겹치면 완충 여력 제한</li>
</ul>
<div class="easy"><b>쉽게:</b> ‘병원이 돈을 못 벌어서’가 아니라,
<b>소송·조사 변호사비 + 합의금 + 보험준비금</b>이 이익을 깎는다.
이미 끝난 사건만으로도 수백억 원~수천억 원 단위가 나갔고, DOJ/SEC는 아직 숫자조차 못 박는다.</div>
{gloss([
    ("Grand jury subpoena", "대배심 소환 — 형사 조사 단계의 증거제출 명령."),
    ("CIA", "Corporate Integrity Agreement — 정부와 맺는 준법감시 합의. 운영비용↑."),
    ("Punitive damages", "징벌적 손해배상 — 보험 미적용·감액 불확실성이 큼."),
    ("Qui tam", "내부고발자가 정부를 대신해 제기하는 False Claims Act 소송."),
])}
<p class="small">출처: ACHC Form 10-Q (quarter ended 2026-06-30) Note — Legal Proceedings · Q2'26 earnings release (2026-07-28) ·
Behavioral Health Business (Fashion Valley 2026-05-19). 투자 권유 아님 · 소송 결과는 변할 수 있음.</p>
</section>

<h2>2. 성장 · 가이던스</h2>
{fig_block(charts['04'], '성장 브리지')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>FY26 Adj EBITDA 가이드</td><td><b>$590–615M</b> (7월 업데이트 · 하단 상향)</td></tr>
  <tr><td>Q2 Adj EPS</td><td>$0.38 (전년 $0.83)</td></tr>
  <tr><td>현금 / 리볼빙 여유</td><td>$171M / ~$670M available</td></tr>
  <tr><td>용량</td><td>Q2 JV 240병상 + CTC 2개소 오픈</td></tr>
</table>
<p class="small">가이던스는 미래 인수·법적·비경상 합의 비용을 제외. 법적 이벤트가 가이던스 밖 변수.</p>

<h2>3. 시나리오 · 포트 실행</h2>
{fig_block(charts['08'], '주가 시나리오')}
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>36–48</td><td>DOJ/SEC 경미 종결 · Fashion Valley 대폭 감액 · 마진 정상화</td></tr>
  <tr><td>Base</td><td>24–34</td><td>조사 장기화·법적비용 지속 · PT대 박스</td></tr>
  <tr><td>Bear</td><td>14–22</td><td>중대 합의/CIA · 징벌 확정 · 레버리지 압박</td></tr>
</table>
<div class="box">
<b>계좌 기준 실행</b><br/>
· 심층 Chase RR은 상위이나 <b>법적 꼬리위험</b> 때문에 코어 부적합<br/>
· 위성도 DOJ/SEC 가시성 전엔 소액·관망 우위 · 추격 금지<br/>
· 모니터: DOJ/SEC 업데이트 · Fashion Valley 감액/항소 · PGL·법적비용 추이 · 순레버리지
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>Acute 본체 + RTC 성장 + Medicaid 의존</u>.
스토리의 반대편에 <b>미해결 형사·SEC·징벌판결</b>이 있다. 싸 보여도 ‘할인 이유’가 법적이다.</div>

<h2>부록 · 출처</h2>
<p class="small">
Acadia Q2 2026 earnings release / Exhibit 99 (2026-07-28) · Form 10-Q (period ended 2026-06-30) Legal Proceedings ·
yfinance 가격·PT ({ASOF}) · BHB Fashion Valley 보도. 피어 믹스·점유는 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 ACHC · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart · Legal section L</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_revenue_mix(),
        "03": chart_payor_mix(),
        "04": chart_growth(),
        "05": chart_legal_timeline(),
        "06": chart_legal_pnl(),
        "07": chart_legal_status(),
        "08": chart_scenarios(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("ACHC", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html = build_html(charts, compete_html=compete_html)
    html, _px = build_and_insert_price("ACHC", CHART_DIR, html)
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
    print(f"ACHC rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% legal=section_L compete={bundle is not None}")


if __name__ == "__main__":
    main()
