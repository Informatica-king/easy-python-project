#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(OMER) — Omeros · YARTEMLEA 런칭 + Novo/OMIDRIA 가치층 + WeasyPrint PDF."""

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
ASOF = "2026-09-16"
PX = 17.17
PT = 33.0
H52 = 19.65
L52 = 3.94
UPSIDE = PT / PX - 1.0
EARN = "11-12"  # next
OUT_PDF = [
    Path("/opt/cursor/artifacts/OMER_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/OMER_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/OMER_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/OMER_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/omer")
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
    "bio": "#6d28d9",
    "pink": "#be185d",
    "amber": "#d97706",
    "sky": "#0369a1",
}


def img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def save_fig(fig, name: str) -> Path:
    p = CHART_DIR / name
    fig.savefig(p, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def fig_block(path: Path, cap: str) -> str:
    return (
        f"<figure><img src='data:image/png;base64,{img_b64(path)}'/>"
        f"<figcaption>{cap}</figcaption></figure>"
    )


def gloss(items: list[tuple[str, str]]) -> str:
    lis = "".join(f"<li><span class='term'>{t}</span> — {d}</li>" for t, d in items)
    return f"<div class='gloss'><div class='gloss-title'>용어</div><ul>{lis}</ul></div>"


def chart_business_flow() -> Path:
    fig, ax = plt.subplots(figsize=(9.4, 3.6))
    ax.set_xlim(0, 10.2)
    ax.set_ylim(0, 3.5)
    ax.axis("off")
    boxes = [
        (0.1, 0.95, 1.7, 1.55, "MASP-2\n플랫폼", C["sand"]),
        (2.0, 0.95, 1.85, 1.55, "YARTEMLEA\nTA-TMA 승인", C["bio"]),
        (4.05, 0.95, 1.7, 1.55, "US 상업\n런칭'26", C["teal"]),
        (5.95, 0.95, 1.7, 1.55, "제품매출\n순$28.5M Q2", C["navy"]),
        (7.85, 0.95, 2.1, 1.55, "현금·부채\n재편", C["gold"]),
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
    for x in (1.85, 3.9, 5.8, 7.7):
        ax.annotate(
            "", xy=(x + 0.12, 1.7), xytext=(x - 0.05, 1.7),
            arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.5),
        )
    ax.add_patch(
        FancyBboxPatch(
            (0.1, 0.12), 4.7, 0.65, boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=C["sky"], edgecolor="white", lw=1.4,
        )
    )
    ax.text(
        2.45, 0.44, "Novo · zaltenibart $240M upfront + ≤$1.8B MS + royalty",
        ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=7.8,
    )
    ax.add_patch(
        FancyBboxPatch(
            (5.0, 0.12), 4.95, 0.65, boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=C["slate"], edgecolor="white", lw=1.4,
        )
    )
    ax.text(
        7.47, 0.44, "OMIDRIA 로열티 → DRI(~'31 US) · 중단영업",
        ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=7.8,
    )
    ax.set_title(
        "비즈니스 한눈에 — MASP-2 제품 + Novo 옵션 + OMIDRIA 잔여",
        fontproperties=PROP_B, fontsize=11.5, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_revenue_bridge() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.3, 3.9))
    ax = axes[0]
    labels = ["Q1'26\nGross", "Q1'26\nNet", "Q2'26\nGross", "Q2'26\nNet"]
    vals = [11.1, 9.9, 32.2, 28.5]
    colors = [C["sand"], C["teal2"], C["sand"], C["teal"]]
    ax.bar(labels, vals, color=colors, width=0.62)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("YARTEMLEA 분기 매출", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.8, f"${v}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 38)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)

    ax = axes[1]
    # H1 product vs illustrative other layers (not P&L mix)
    sizes = [38.4, 240.0, 9.2]
    labs = [
        "H1'26\n제품순\n$38.4M",
        "Novo\nupfront\n$240M\n('25)",
        "OMIDRIA\n로열티예\nQ4'25 $9.2M\n(→DRI)",
    ]
    ax.pie(
        sizes, labels=labs,
        colors=[C["teal"], C["sky"], C["slate"]],
        startangle=90,
        wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=7.2),
    )
    ax.set_title("가치층 스케일 비교 (상이 시점)", fontproperties=PROP_B, fontsize=10)
    return save_fig(fig, "02_revenue_bridge.png")


def chart_pnl_cash() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.3, 3.8))
    ax = axes[0]
    cats = ["제품순매출", "COGS", "R&D+SG&A", "영업이익"]
    q2 = [28.5, -0.8, -27.7, 0.1]
    colors = [C["teal"], C["red"], C["amber"], C["green"]]
    ax.barh(cats[::-1], q2[::-1], color=colors[::-1], height=0.55)
    ax.axvline(0, color=C["muted"], lw=0.8)
    ax.set_xlabel("백만 USD · Q2'26", fontproperties=PROP)
    ax.set_title("Q2'26 손익 스케치", fontproperties=PROP_B, fontsize=11)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)

    ax = axes[1]
    periods = ["YE'25", "Q1'26", "Q2'26"]
    cash = [171.8, 135.3, 132.0]
    ax.plot(periods, cash, marker="o", color=C["navy"], lw=2.2, markersize=8)
    ax.fill_between(range(3), cash, alpha=0.12, color=C["navy"])
    ax.set_ylabel("현금+단기투자 $M", fontproperties=PROP)
    ax.set_title("현금 추이", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(cash):
        ax.text(i, v + 4, f"${v:.0f}M", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylim(100, 200)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    return save_fig(fig, "03_pnl_cash.png")


def chart_value_stack() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")
    layers = [
        (0.3, 2.7, 9.4, 1.1, "① 제품 — YARTEMLEA US (H1'26 net $38.4M · QoQ +190% gross)", C["teal"]),
        (0.3, 1.5, 9.4, 1.0, "② 파트너 — Novo zaltenibart ($240M + ≤$1.8B MS + HSD~HT royalty)", C["sky"]),
        (0.3, 0.3, 9.4, 1.0, "③ 잔여 — OMIDRIA US 로열티는 DRI 통과(~'31) · EU 등 잔여 가능", C["slate"]),
    ]
    for x, y, w, h, t, c in layers:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        ax.text(
            x + 0.25, y + h / 2, t, ha="left", va="center",
            color="white", fontproperties=PROP_B, fontsize=9,
        )
    ax.set_title("수익·가치 3층 — 제품 / 파트너 / 잔여 로열티", fontproperties=PROP_B, fontsize=11)
    return save_fig(fig, "04_value_stack.png")


def chart_pipeline() -> Path:
    fig, ax = plt.subplots(figsize=(9.2, 3.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    rows = [
        (4.2, "YARTEMLEA", "승인·판매 (US) · EMA 재심사 · 적응증 확장 탐색", C["teal"]),
        (3.2, "OMS1029", "장기형 MASP-2 · Ph1 완료", C["bio"]),
        (2.2, "zaltenibart", "Novo · MASP-3 · Ph3 개시 궤도 (PNH 등)", C["sky"]),
        (1.2, "OMS527", "PDE7 · 코카인 사용장애 · NIDA 전액 지원", C["gold"]),
        (0.2, "OncotoX / T-CAT", "AML·내성균 등 초기 플랫폼", C["slate"]),
    ]
    for y, name, desc, c in rows:
        ax.add_patch(
            FancyBboxPatch(
                (0.2, y), 2.4, 0.75, boxstyle="round,pad=0.02,rounding_size=0.08",
                facecolor=c, edgecolor="white", lw=1.5,
            )
        )
        ax.text(
            1.4, y + 0.37, name, ha="center", va="center",
            color="white", fontproperties=PROP_B, fontsize=8.5,
        )
        ax.text(2.85, y + 0.37, desc, ha="left", va="center", fontproperties=PROP, fontsize=8.5, color=C["ink"])
    ax.set_title("파이프라인 맵", fontproperties=PROP_B, fontsize=11)
    return save_fig(fig, "05_pipeline.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.4)
    ax.axis("off")
    cards = [
        (0.2, 1.6, 3.0, 1.5, "접근·상환", "J-code(7/1)\nNTAP(10/1'26)\n센터 침투", C["teal"]),
        (3.5, 1.6, 3.0, 1.5, "유럽", "CHMP 부정의견\n→ 재심사·AHEG\n바이너리 리스크", C["red"]),
        (6.8, 1.6, 3.0, 1.5, "파트너", "Novo Ph3 개시\n근기 MS ≤$100M\n총 ≤$1.8B", C["sky"]),
        (0.2, 0.15, 3.0, 1.2, "적응증", "ARDS·소아예방\n연구자 주도 YE'26", C["bio"]),
        (3.5, 0.15, 3.0, 1.2, "재무", "현금 $132M\n노트 축소·자사주", C["gold"]),
        (6.8, 0.15, 3.0, 1.2, "실적", f"다음 ~{EARN}\n런칭 지속성 확인", C["navy"]),
    ]
    for x, y, w, h, title, body, c in cards:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=1.6,
            )
        )
        ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="top", color="white", fontproperties=PROP_B, fontsize=9)
        ax.text(x + w / 2, y + h / 2 - 0.15, body, ha="center", va="center", color="white", fontproperties=PROP, fontsize=7.5)
    ax.set_title("촉매 카드", fontproperties=PROP_B, fontsize=11)
    return save_fig(fig, "06_catalysts.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    bands = [
        ("Bear", 6, 11, C["red"]),
        ("Base", 14, 22, C["teal"]),
        ("Bull", 28, 40, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(bands):
        ax.barh(i, hi - lo, left=lo, color=c, height=0.55, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}–{hi}", ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=9)
    ax.axvline(PX, color=C["navy"], ls="--", lw=1.4)
    ax.text(PX + 0.3, 2.55, f"px ${PX:.2f}", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], ls=":", lw=1.4)
    ax.text(PT - 4.5, 2.55, f"PT ${PT:.0f}", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 밴드 (예시 · 권유 아님)", fontproperties=PROP)
    ax.set_xlim(0, 45)
    ax.set_title("시나리오 밴드", fontproperties=PROP_B, fontsize=11)
    return save_fig(fig, "07_scenarios.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(8.4, 3.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    ax.add_patch(
        FancyBboxPatch(
            (0.3, 0.4), 9.4, 2.4, boxstyle="round,pad=0.04,rounding_size=0.12",
            facecolor=C["sand"], edgecolor=C["navy"], lw=2,
        )
    )
    ax.text(5.0, 2.35, "포트 위치 — 미보유 · 워치", ha="center", fontproperties=PROP_B, fontsize=12, color=C["navy"])
    ax.text(
        5.0, 1.55,
        f"심층 Chase #1 · 라벨 중하·임상변동 · TA 미선정\n"
        f"px ${PX:.2f} · PT ${PT:.0f} ({UPSIDE*100:+.0f}%) · 고점근접 {PX/H52:.0%}\n"
        f"추격 금지 · 임상·EU·희석 확인 전 극소 위성만",
        ha="center", va="center", fontproperties=PROP, fontsize=9, color=C["ink"],
    )
    return save_fig(fig, "08_position.png")


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
<div class="easy"><b>쉽게:</b> TA-TMA는 <b>첫 승인 치료제</b> 국면이다.
YARTEMLEA가 오프라벨 C5·지지요법 자리를 잠식하는지가 점유 스토리의 전부다.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> 지금 P&amp;L의 continuing ops는 <b>제품 100%</b>.
진짜 옵션성은 Novo 마일스톤·로열티에 있고, OMIDRIA 현금은 DRI로 빠진다.</div>
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
      @bottom-center {{ content:"OMER 수익구조 · {ASOF}"; font-size:8pt; color:#78716c; }} }}
    body {{ font-family:'NanumGothic',sans-serif; color:#1c1917; font-size:10pt; line-height:1.45; }}
    h1 {{ font-size:20pt; color:#1e3a5f; margin:0 0 4px; }}
    h2 {{ font-size:13pt; color:#0f766e; border-bottom:2px solid #99f6e4; padding-bottom:3px; margin-top:16px; }}
    .sub {{ color:#57534e; font-size:9.5pt; margin:0 0 10px; }}
    .box {{ background:#f5f5f4; border-left:4px solid #0f766e; padding:8px 10px; margin:8px 0; }}
    .easy {{ background:#ecfdf5; border-left:4px solid #059669; padding:8px 10px; margin:8px 0; }}
    .warn {{ background:#fff1f2; border-left:4px solid #9f1239; padding:8px 10px; margin:8px 0; }}
    table {{ width:100%; border-collapse:collapse; margin:8px 0 12px; font-size:9pt; }}
    th {{ background:#1e3a5f; color:white; padding:5px 6px; text-align:left; }}
    td {{ border-bottom:1px solid #e7e5e4; padding:5px 6px; vertical-align:top; }}
    figure {{ margin:10px 0; text-align:center; }}
    img {{ max-width:100%; height:auto; }}
    figcaption {{ font-size:8pt; color:#78716c; margin-top:3px; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss-title {{ font-weight:bold; color:#0f766e; margin-bottom:4px; }}
    .term {{ font-weight:bold; color:#1e3a5f; }}
    .small {{ font-size:8pt; color:#78716c; }}
    ul {{ margin:6px 0 8px 18px; }}
    li {{ margin:2px 0; }}
    """
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"/>
<title>OMER 수익구조분석 {ASOF}</title><style>{css}</style></head><body>
<h1>수익구조분석 — OMER (Omeros)</h1>
<p class="sub">보체 MASP-2 · YARTEMLEA 상업 런칭 · Novo zaltenibart 옵션 · 기준 {ASOF} ·
px ${PX:.2f} · PT ${PT:.0f} ({UPSIDE*100:+.0f}%) · 52주 ${L52:.2f}–${H52:.2f} · 실적 ~{EARN}</p>

<div class="box">
<b>한줄:</b> continuing ops 수익의 실체는 <b>YARTEMLEA 제품매출</b>(Q2 net $28.5M).
밸류에이션의 두 번째 층은 <b>Novo 딜</b>, OMIDRIA는 <b>DRI로 흐르는 잔여</b>다.
</div>

<!--PRICE_CHARTS-->

<h2>1. 비즈니스 · 현재 매출</h2>
{fig_block(charts['flow'], '비즈니스 플로우')}
{fig_block(charts['rev'], 'YARTEMLEA 분기 매출 · 가치층 스케일')}
{fig_block(charts['stack'], '수익·가치 3층')}
<ul>
  <li><b>YARTEMLEA (narsoplimab)</b> — FDA 승인(2025-12) · US 런칭 2026-01 · TA-TMA 성인·소아(≥2세) 유일 승인</li>
  <li>Q1'26: gross $11.1M / net <b>$9.9M</b> · Q2'26: gross $32.2M / net <b>$28.5M</b> (gross QoQ +190%)</li>
  <li>H1'26 제품순매출 합 <b>$38.4M</b> · Q2 COGS $0.8M · R&amp;D+SG&amp;A ~$27.7M · 영업이익 ~$0.1M</li>
  <li>J-code 2026-07-01 발효 · NTAP 2026-10-01 — 병원 접근·상환 개선 기대</li>
</ul>
{gloss([
    ("TA-TMA", "조혈모세포이식 관련 혈전미세혈관병증. 치명률 높은 희귀 합병증."),
    ("MASP-2", "렉틴 경로 효과효소. YARTEMLEA가 선택 억제 — 고전/대체 경로 보존 주장."),
    ("Gross-to-net", "총매출→순매출 차감(유통·차지백 등). Q2 ~11.5%."),
])}
{compete_html}

<h2>2. 파트너 · 잔여 자산</h2>
{fig_block(charts['pipe'], '파이프라인')}
<ul>
  <li><b>Novo Nordisk (2025-11)</b> — zaltenibart(구 OMS906, MASP-3) 글로벌 권리.
    upfront <b>$240M</b> · 개발·승인 MS 최대 ~$510M(근기 ≤$100M 포함) · 매출 MS ≤$1.3B · 합 ≤$1.8B + HSD~HT royalty</li>
  <li><b>OMIDRIA</b> — Rayner 매각 후 로열티. US 로열티 ~2031까지 <b>DRI에 전액 이관</b>(현금은 회사에 안 들어옴).
    Q4'25 earned royalty $9.2M on Rayner US $30.7M — 참고용</li>
  <li><b>OMS1029</b> 장기형 MASP-2 Ph1 완료 · <b>OMS527</b> NIDA 전액 지원 · OncotoX/T-CAT 초기</li>
</ul>
<div class="easy"><b>쉽게:</b> Novo $240M은 이미 장부에 찍힌 현금 사건이다.
앞으로의 “추가 매출”은 마일스톤·로열티 확률 게임이고, OMIDRIA US 현금은 DRI 몫이다.</div>

<h2>3. 비용 · 현금 · 자본구조</h2>
{fig_block(charts['pnl'], '손익·현금')}
<table>
  <tr><th>항목</th><th>수치</th></tr>
  <tr><td>현금+단기투자 (6/30/26)</td><td><b>$132.0M</b> (Q1 $135.3M · YE'25 $171.8M)</td></tr>
  <tr><td>Q2'26 영업현금</td><td>+$4.1M (company-wide)</td></tr>
  <tr><td>2029 Notes</td><td>원금 ~$40.3M 잔여 (7월 리퍼체이스 후 · 희석 잠재주식 ↓)</td></tr>
  <tr><td>자사주</td><td>H1 ~0.8M주 · 평균 ~$11.70 · 합 ~$9.9M</td></tr>
  <tr><td>Q2 GAAP 순이익</td><td>$13.2M ($0.18) — 내재파생 비현금 +$11.5M 포함</td></tr>
  <tr><td>Q2 non-GAAP adj.</td><td>+$1.8M ($0.02) · Q1 adj. −$17.1M</td></tr>
</table>
<div class="warn"><b>리스크:</b> 2026-06 CHMP <b>부정의견</b> → EMA 재심사.
유럽 승인 지연·실패는 매출 옵션을 깎고, 미국 런칭 스토리만으로 시총을 지탱해야 한다.</div>

<h2>4. 촉매 · 시나리오</h2>
{fig_block(charts['cat'], '촉매')}
{fig_block(charts['scen'], '시나리오 밴드')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$6–11</td><td>US 침투 정체 · EMA 최종 실패 · 희석·유동성 압박</td></tr>
  <tr><td>Base</td><td>$14–22</td><td>US 순매출 QoQ 성장 지속 · NTAP 효과 · Novo Ph3 순항 · PT 할인 유지</td></tr>
  <tr><td>Bull</td><td>$28–40</td><td>US 런레이트 가속 · EMA 반전 · Novo 근기 MS · PT($33) 상회</td></tr>
</table>
<p><b>Breaker:</b> 런칭 둔화 · 상환/접근 이슈 · EMA 최종 거절 · Novo 일정 지연 · 전환사채·희석 재확대</p>

<h2>5. 포트 실행</h2>
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (09-16 심층 · 포폴)</b><br/>
미보유 · Chase RR <b>#1</b> · 라벨 <b>중하·임상변동</b> · 본선∩GO 아님 · TA 자동선정 제외.<br/>
업사이드 {UPSIDE*100:+.0f}%는 PT($33) 할인 — <b>임상·EU·런칭 지속성</b>이 먼저다.<br/>
실행: <b>추격 금지</b> · 관심 시 <b>극소 위성</b>만 · 게이트: Q3 순매출 · NTAP 후 접근 · EMA 재심사 · 현금/노트.
</div>

<p class="small">생성: 수익구조분석() · 티커 OMER · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart<br/>
출처: Omeros Q1/Q2'26 earnings releases · FY25 YE results · SEC exhibits · yfinance · 점유/믹스 피어는 방향 비교용 추정</p>
</body></html>
"""


def main() -> int:
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "rev": chart_revenue_bridge(),
        "stack": chart_value_stack(),
        "pnl": chart_pnl_cash(),
        "pipe": chart_pipeline(),
        "cat": chart_catalysts(),
        "scen": chart_scenarios(),
        "pos": chart_position(),
    }
    bundle, cpaths = build_compete_charts("OMER", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("OMER", CHART_DIR, html_doc)
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

        tag = "sepa-rev-omer"
        notes = (
            f"## OMER 수익구조분석 ({ASOF})\n\n"
            f"Omeros · YARTEMLEA 상업 런칭 · Novo zaltenibart · OMIDRIA→DRI.\n\n"
            f"- Q2'26 net product **$28.5M** (gross $32.2M · QoQ +190%) · H1 net $38.4M\n"
            f"- 현금 $132M · 2029 Notes ~$40.3M · Q2 adj. NI $1.8M\n"
            f"- Novo: $240M upfront + ≤$1.8B milestones + royalties\n"
            f"- Chase #1 · 중하·임상변동 · 미보유 · 추격 금지\n"
            f"- 업사이드 {UPSIDE*100:+.0f}% (PT ${PT:.0f} · px ${PX:.2f})\n"
            f"- 리스크: EMA CHMP 부정의견·재심사 · 런칭 지속성\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — OMER",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
