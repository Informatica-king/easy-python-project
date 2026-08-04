#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(CMPR) — Cimpress 대량맞춤 인쇄 (Vista/Upload&Print/National Pen) + compete PDF."""

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
ASOF = "2026-08-04"
PX = 97.96
PT = 110.5
H52 = 106.58
UPSIDE = PT / PX - 1.0
EARN = "07-29"  # Q4 FY26 reported (FY ends Jun)
OUT_PDF = [
    Path("/opt/cursor/artifacts/CMPR_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/CMPR_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/CMPR_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/CMPR_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/cmpr")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "teal": "#0f766e",
    "teal2": "#14b8a6",
    "navy": "#1e3a5f",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "vista": "#0369a1",
    "upload": "#c2410c",
    "pen": "#7c3aed",
    "other": "#64748b",
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
        (0.1, 0.7, 1.85, 1.6, "SMB·소비자\n주문", C["sand"]),
        (2.15, 0.7, 1.75, 1.6, "디자인·\n업로드", C["vista"]),
        (4.1, 0.7, 1.75, 1.6, "대량맞춤\n생산", C["teal"]),
        (6.05, 0.7, 1.7, 1.6, "물류·\n크로스필필", C["navy"]),
        (7.95, 0.7, 1.75, 1.6, "매출·\nEBITDA", C["teal2"]),
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
    ax.set_title("비즈니스 한눈에 — 소량도 공장처럼 찍어 주는 대량맞춤 인쇄",
                 fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.1))
    ax = axes[0]
    # Q4 FY26 pre-elim
    sizes = [486.4, 215.5, 126.5, 95.7, 68.7]
    labels = [
        "Vista\n$486M",
        "PrintBrothers\n$216M",
        "Print Group\n$127M",
        "National Pen\n$96M",
        "All Other\n$69M",
    ]
    ax.pie(
        sizes, labels=labels,
        colors=[C["vista"], C["upload"], "#ea580c", C["pen"], C["other"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=7.5),
    )
    ax.set_title("Q4 FY'26 세그먼트 (elim 전)", fontproperties=PROP_B, fontsize=10)

    ax = axes[1]
    cats = ["Vista", "Upload&\nPrint", "NatPen+\nOther"]
    fy = [1934.5, 823.2 + 445.6, 446.8 + 258.1]
    ax.bar(cats, fy, color=[C["vista"], C["upload"], C["pen"]])
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("FY'26 세그먼트 매출 (elim 전)", fontproperties=PROP_B, fontsize=10)
    for i, v in enumerate(fy):
        ax.text(i, v + 40, f"{v:.0f}", ha="center", fontsize=8, fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_growth() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    labels = ["FY'23", "FY'24", "FY'25", "FY'26"]
    revs = [3079.6, 3291.9, 3403.1, 3736.6]
    ax.plot(labels, revs, marker="o", color=C["teal"], lw=2.2, markersize=8)
    ax.fill_between(range(len(revs)), revs, alpha=0.15, color=C["teal"])
    for i, v in enumerate(revs):
        ax.text(i, v + 40, f"${v/1000:.2f}B", ha="center", fontsize=8, fontproperties=PROP)
    ax.set_title("연간 매출 — FY'26 $3.74B (+10% reported / +4% organic CC)",
                 fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "03_growth.png")


def chart_profit() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
    ax = axes[0]
    ax.bar(["FY'25", "FY'26"], [433.2, 458.5], color=[C["sand"], C["teal"]], width=0.5)
    ax.set_title("Adj. EBITDA ($M)", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate([433.2, 458.5]):
        ax.text(i, v + 5, f"{v:.0f}", ha="center", fontproperties=PROP_B, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    ax.bar(["FY'25 NI", "FY'26 NI"], [12.9, 97.1], color=[C["sand"], C["navy"]], width=0.5)
    ax.set_title("Net Income ($M)", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate([12.9, 97.1]):
        ax.text(i, v + 2, f"{v:.0f}", ha="center", fontproperties=PROP_B, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "04_profit.png")


def chart_guide() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    rows = [
        ("FY'27 Rev growth", ">=7% reported\n(organic CC >=3%)", C["teal"]),
        ("FY'27 Adj. EBITDA", ">= $520M", C["navy"]),
        ("FY'27 Adj. FCF", "~ $200M", C["vista"]),
        ("FY'28 Adj. EBITDA", ">= $615M (상향)", C["green"]),
    ]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")
    for i, (title, body, c) in enumerate(rows):
        y = 3.2 - i * 0.9
        ax.add_patch(
            FancyBboxPatch((0.3, y), 9.2, 0.75, boxstyle="round,pad=0.02,rounding_size=0.08",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(0.6, y + 0.38, title, va="center", fontproperties=PROP_B, fontsize=10, color="white")
        ax.text(9.2, y + 0.38, body, va="center", ha="right", fontproperties=PROP, fontsize=9, color="white")
    ax.set_title("가이던스 — FY'27 수익·FCF, FY'28 EBITDA 타깃 상향", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "05_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 70, 88, C["red"]),
        ("Base", 90, 115, C["teal"]),
        ("Bull", 120, 145, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}-{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"now ${PX:.0f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT ${PT:.0f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("USD", fontproperties=PROP)
    ax.set_title("시나리오 — Vista 믹스·공장 투자 vs 관세·광고비", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(60, 155)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, "Vista", "본진", "VGP/고객\n$93.60", C["vista"]),
        (0.28, "U&P", "성장", "보고 +20%\nM&A+유기", C["upload"]),
        (0.52, "공장", "투자", "NA 캐파\nCOGS↓ 기대", C["navy"]),
        (0.76, "관세", "리스크", "섹션301/338\n공급망대응", C["red"]),
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
    ax.set_title("촉매 — Upload&Print·공장 효율 vs 관세·일회성 비용", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "보유 위성\n1주·NO_ADD", C["teal"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "~10.7%\n위성상단", C["navy"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", "stop $90\ntp 110/120", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "추가·물타기 금지 · 고점권 · 관세/공장 일회성", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "점유Δ+1.5pp · FY가이던스·FCF 궤적", C["vista"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.35, body, ha="center", va="center",
                fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title("실행 포지션 맵 (포트 8/4 · CMPR 1@$98.70)", fontproperties=PROP_B, fontsize=12, pad=4)
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
<div class="easy"><b>쉽게:</b> CMPR(VistaPrint 등)은 상장 특수인쇄 피어 중 <b>스케일 1위</b>이고
점유 추정 <b>+1.5pp</b> — 챌린저가 아니라 피어셋 내 대장에 가깝다. Canva 파트너십은 장기 옵션.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> CMPR은 <b>Vista(DTC) ~절반</b> + 유럽 Upload&amp;Print 성장 + National Pen/BuildASign.
피어(DLX·EBF)는 수표·상업인쇄 비중이 달라 버킷은 근사 비교용.</div>
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
      @bottom-center {{ content:"CMPR 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0369a1; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0ea5e9; padding-bottom:3px; color:#0369a1; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#1e3a5f; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#e0f2fe 0%,#f0f9ff 55%,#ecfeff 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#bae6fd; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecdd3; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#0369a1; color:#fff; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#f0f9ff; border-left:4px solid #0369a1; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#0369a1; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0284c7; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#0369a1; }}
    .kpi .s {{ font-size:7.5pt; color:#0284c7; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>CMPR 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>CMPR 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Cimpress plc · VistaPrint · Upload&amp;Print · National Pen</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q4/FY'26 실적({EARN} 발표, FY ends Jun) · 시총 ~$2.4B · ${PX:.2f}</p>
  <div style="margin-top:22px">
    <span class="tag">대량맞춤 인쇄</span>
    <span class="tag good">FY 매출 +10%</span>
    <span class="tag good">점유 Δ +1.5pp</span>
    <span class="tag warn">위성 보유·NO_ADD</span>
    <span class="tag">다음실적 ~10-28</span>
  </div>
  <div style="margin-top:28px">
    <div class="kpi"><div class="l">FY'26 매출</div><div class="v">$3.74B</div><div class="s">+10% / org+4%</div></div>
    <div class="kpi"><div class="l">Adj.EBITDA</div><div class="v">$459M</div><div class="s">+6%</div></div>
    <div class="kpi"><div class="l">Q4 매출</div><div class="v">$945M</div><div class="s">+9%</div></div>
    <div class="kpi"><div class="l">업사이드</div><div class="v">{UPSIDE*100:+.1f}%</div><div class="s">PT ${PT:.0f}</div></div>
  </div>
  <p class="small" style="margin-top:36px;max-width:540px;margin-left:auto;margin-right:auto">
    Vista가 본진, Upload&amp;Print(유럽)가 성장 엔진. FY'27은 Adj.EBITDA ≥$520M·FCF ~$200M 가이던스.
    포트는 위성 1주 보유 — 추격·추가 금지, stop $90.
  </p>
</section>

<h2>0. 한줄 결론</h2>
<div class="box">
<b>품질은 챌린저 OS에 맞지만, 지금은 ‘더 사기’보다 홀드.</b>
FY'26 매출·이익 성장 + Upload&amp;Print 강세 + FY'27/28 가이던스 상향은 플러스.
공장 스타트업·관세·일회성(캐나다 duty)이 단기 마진을 누르나, 구조는 대량맞춤 해자.
실행: <b>보유 1주 · NO_ADD · 위성상단</b> — A′ 재진입은 비중·손절 여유 있을 때만.
</div>

<h2>1. 비즈니스 구조</h2>
<div class="easy"><b>쉽게:</b> 명함·전단지·티셔츠·포장을 <b>한 장부터</b> 주문해도
공장 라인처럼 자동 생산하는 회사다. VistaPrint가 소비자·SMB 얼굴, Upload&amp;Print는 유럽 B2B 업로드 인쇄.</div>
{fig_block(charts['flow'], '주문 → 생산 → 크로스필필 → 매출')}
{gloss([
    ("Mass customization", "대량생산 효율로 맞춤 소량 주문을 처리"),
    ("Upload & Print", "PrintBrothers + The Print Group — 주로 유럽 업로드형 상업인쇄"),
    ("Cross-Cimpress fulfillment", "그룹 공장끼리 주문을 나눠 찍어 원가·캐파 공유"),
])}

{compete_html}

<h2>2. 세그먼트 · 성장</h2>
<div class="easy"><b>쉽게:</b> 매출의 약 절반이 Vista, 1/3이 Upload&amp;Print.
Upload&amp;Print는 보고성장이 빠르고(M&amp;A+통화), 유기성장도 ~6–7%대.</div>
{fig_block(charts['mix'], 'Q4·FY 세그먼트')}
{fig_block(charts['growth'], '연간 매출')}
<table>
  <tr><th>세그먼트</th><th>Q4 FY'26</th><th>YoY</th><th>FY'26</th><th>메모</th></tr>
  <tr><td>VistaPrint</td><td>$486.4M</td><td>+4% (+3% org CC)</td><td>$1.93B</td><td>본진 · VGP/고객 +9%</td></tr>
  <tr><td>PrintBrothers</td><td>$215.5M</td><td>+21% (+6% org)</td><td>$823M</td><td>Upload&amp;Print</td></tr>
  <tr><td>The Print Group</td><td>$126.5M</td><td>+19% (+5% org)</td><td>$446M</td><td>크로스필필 강세</td></tr>
  <tr><td>National Pen</td><td>$95.7M</td><td>+2%</td><td>$447M</td><td>프로모·펜</td></tr>
  <tr><td>All Other</td><td>$68.7M</td><td>+17%</td><td>$258M</td><td>BuildASign 등</td></tr>
  <tr><td><b>Total</b></td><td><b>$945.0M</b></td><td>+9% / +3% org</td><td><b>$3.74B</b></td><td>elim 후</td></tr>
</table>
{gloss([
    ("Organic CC", "인수·환율 제외 상수성장"),
    ("VGP/고객", "Vista variable gross profit per customer — 고객당 공헌이익 근사"),
])}

<h2>3. 수익성 · 가이던스</h2>
{fig_block(charts['profit'], 'EBITDA·순이익')}
{fig_block(charts['guide'], 'FY27–28 타깃')}
<table>
  <tr><th>항목</th><th>FY'26</th><th>가이던스/메모</th></tr>
  <tr><td>Adj. EBITDA</td><td>$458.5M (+6%)</td><td>FY'27 ≥$520M · FY'28 ≥$615M</td></tr>
  <tr><td>Net income</td><td>$97.1M</td><td>FY'27 ≥$125M · FY'28 ≥$192M</td></tr>
  <tr><td>Adj. FCF</td><td>$122.4M</td><td>FY'27 ~$200M</td></tr>
  <tr><td>Net leverage</td><td>2.9x</td><td>FY'27 ~2.5x → FY'28 &lt;2.0x 목표</td></tr>
  <tr><td>유동성</td><td>현금 $249M + 미인출 RCF $250M</td><td>양호</td></tr>
</table>
<div class="easy"><b>쉽게:</b> Q4는 공장 스타트업·캐나다 duty 일회성으로 Adj.EBITDA가 살짝 줄었지만,
연간·중기 가이던스는 <b>이익·현금 증가</b> 쪽이다.</div>

<h2>4. 시나리오 · 촉매</h2>
{fig_block(charts['scen'], '주가 시나리오')}
{fig_block(charts['cat'], '촉매 카드')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$70–88</td><td>관세 확전 · Vista 정체 · 공장 투자 회수 지연</td></tr>
  <tr><td>Base</td><td>$90–115</td><td>FY'27 가이던스 궤적 · U&amp;P 시너지 · stop 준수</td></tr>
  <tr><td>Bull</td><td>$120–145</td><td>유기성장 가속 · Canva 파트너 가시화 · FCF 전환↑</td></tr>
</table>

<h2>5. 포트 실행</h2>
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (8/4)</b><br/>
보유 위성 1주 · 평단 $98.70 · 위성 ~10.7% 상단 · <b>NO_ADD · 물타기 금지</b> · stop $90 · tp 110/120.<br/>
품질: 피어셋 점유 Δ+1.5pp (L2 가산 후보) · 다만 이미 보유·비중 한도.<br/>
다음: Investor Day 09-30 · 실적 ~10-28 · 가이던스/관세 업데이트 확인.
</div>

<p class="small">생성: 수익구조분석() · 티커 CMPR · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart<br/>
출처: Cimpress Q4/FY2026 earnings materials (2026-07-29) · yfinance · 피어 점유/믹스는 방향 비교용 추정</p>
</body></html>
"""


def main() -> int:
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "growth": chart_growth(),
        "profit": chart_profit(),
        "guide": chart_guide(),
        "scen": chart_scenarios(),
        "cat": chart_catalysts(),
        "pos": chart_position(),
    }
    bundle, cpaths = build_compete_charts("CMPR", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("CMPR", CHART_DIR, html_doc)
    OUT_HTML.write_text(html_doc, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    pdf = HTML(filename=str(OUT_HTML)).write_pdf()
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf)
        print(f"PDF {p} {p.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
