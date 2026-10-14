#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(VRNS) — Varonis 데이터보안 플랫폼(DSPM) + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-10-14"
PX = 48.72
PT = 51.45
H52 = 63.80
L52 = 19.70
UPSIDE = PT / PX - 1.0
NEAR = PX / H52
EARN = "10-27"
OUT_PDF = [
    Path("/opt/cursor/artifacts/VRNS_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/VRNS_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/VRNS_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/VRNS_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/vrns")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "navy": "#1e3a5f",
    "navy2": "#1d4ed8",
    "teal": "#0f766e",
    "teal2": "#14b8a6",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "saas": "#0e7490",
    "svc": "#a16207",
    "rd": "#7c3aed",
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
        (0.1, 0.7, 1.8, 1.6, "데이터 발견\n분류 · 민감도", C["sand"]),
        (2.05, 0.7, 1.8, 1.6, "권한·노출\nDSPM", C["navy"]),
        (4.0, 0.7, 1.8, 1.6, "탐지·대응\nDDR / UEBA", C["saas"]),
        (5.95, 0.7, 1.8, 1.6, "M365·클라우드\n패키지 구독", C["teal"]),
        (7.9, 0.7, 1.85, 1.6, "SaaS ARR\n반복매출", C["gold"]),
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
                fontproperties=PROP_B, fontsize=8.2, color=tc)
    ax.set_title(
        "VRNS 가치사슬 — 데이터를 찾아 잠그고, 이상행위를 잡아 SaaS 구독으로 판다",
        fontproperties=PROP_B, fontsize=11, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [94, 4, 2]
    labels = ["SaaS 구독\n94%", "서비스\n4%", "유지·Term\n2%"]
    ax.pie(
        sizes, labels=labels, colors=[C["saas"], C["svc"], C["muted"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.2),
    )
    ax.set_title("수익 인식 (Q2'26 근사)", fontproperties=PROP_B, fontsize=10.5)

    ax = axes[1]
    q = ["Q2'25", "Q3'25", "Q4'25", "Q1'26", "Q2'26"]
    rev = [152.2, 161.6, 173.4, 173.1, 180.0]
    ax.bar(q, rev, color=C["saas"], width=0.55)
    for i, v in enumerate(rev):
        ax.text(i, v + 2.2, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylabel("USD M", fontproperties=PROP)
    ax.set_title("분기 매출 — Q2 180M (+18% YoY)", fontproperties=PROP_B, fontsize=10)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_mix.png")


def chart_growth_bridge() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    cats = ["Q2 매출", "FY'25", "TTM", "Q3 컨센"]
    yoy = [18.3, 13.2, 18.3, 15.7]
    colors = [C["navy"], C["saas"], C["teal"], C["gold"]]
    for i, (v, c) in enumerate(zip(yoy, colors)):
        ax.bar(i, v, color=c, width=0.55)
        ax.text(i, v + 0.4, f"+{v:.1f}%", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_xticks(range(4))
    ax.set_xticklabels(cats, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("성장 — 분기 +18% · TTM 688M", fontproperties=PROP_B, fontsize=10.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    labs = ["SaaS\n비중", "GP%\nQ2", "SBC/\n매출", "FCF\n마진"]
    vals = [94.0, 75.3, 19.2, 11.1]
    cols = [C["saas"], C["teal"], C["rd"], C["gold"]]
    for i, (s, c) in enumerate(zip(vals, cols)):
        ax.bar(i, s, color=c, width=0.55)
        ax.text(i, s + 1.6, f"{s:.0f}%", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_xticks(list(range(4)))
    ax.set_xticklabels(labs, fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 115)
    ax.set_title("엔진 — 구독 94% · GP 75% · SBC 19%", fontproperties=PROP_B, fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "03_growth_bridge.png")


def chart_pnl() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    x = [0, 1]
    gm = [79.5, 75.3]
    rd = [37.0, 40.7]
    sm = [40.0, 43.9]
    ax.plot(x, gm, marker="o", color=C["teal"], lw=2.2, label="GP%")
    ax.plot(x, rd, marker="o", color=C["rd"], lw=2.2, label="R&D%")
    ax.plot(x, sm, marker="s", color=C["gold"], lw=2.2, label="S&M%")
    ax.set_xticks(x)
    ax.set_xticklabels(["Q2'25", "Q2'26"], fontproperties=PROP)
    ax.set_ylabel("% of sales", fontproperties=PROP)
    ax.set_ylim(30, 90)
    ax.set_title("마진 — GP 75% (YoY -4pp) · R&D 41%", fontproperties=PROP_B, fontsize=10)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    names = ["매출\nUSD M", "OCF\nUSD M", "FCF\nUSD M"]
    q25 = [152.2, 21.3, 17.3]
    q26 = [180.0, 25.1, 20.0]
    w = 0.35
    ax.bar([i - w / 2 for i in range(3)], q25, w, color=C["sand"], label="Q2'25")
    ax.bar([i + w / 2 for i in range(3)], q26, w, color=C["saas"], label="Q2'26")
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(names, fontproperties=PROP, fontsize=8)
    ax.set_title("달러 실적 · FCF 20M (매출 11%)", fontproperties=PROP_B, fontsize=10.5)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "04_pnl.png")


def chart_leverage() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
    ax = axes[0]
    labs = ["현금+ST", "장기부채", "리스", "순현금"]
    vals = [698, 453, 63, 182]
    cols = [C["teal"], C["red"], C["muted"], C["navy"]]
    bars = ax.bar(labs, vals, color=cols, width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 12, f"{v:.0f}M",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylabel("USD M", fontproperties=PROP)
    ax.set_title("BS — 현금 698M · 전환사채 453M", fontproperties=PROP_B, fontsize=10.5)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    names = ["이연매출", "FCF TTM", "Q1 자사주"]
    v2 = [435, 118, 135]
    cols2 = [C["saas"], C["teal"], C["gold"]]
    bars = ax.bar(names, v2, color=cols2, width=0.5)
    for b, v in zip(bars, v2):
        ax.text(b.get_x() + b.get_width() / 2, v + 8, f"{v:.0f}M",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_title("선수금 435M · TTM FCF 118M", fontproperties=PROP_B, fontsize=10.5)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "05_leverage.png")


def chart_guide() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.axis("off")
    items = [
        (0.04, "Q3 컨센 매출", "185.8-189.2M\n평균 186.9M", C["navy"]),
        (0.28, "Q3 EPS", "논GAAP ~0.03\n(4연속 Beat)", C["teal"]),
        (0.52, "실적일", "2026-10-27\nD-13 · D-5=10-22", C["gold"]),
        (0.76, "런레이트", "Q2x4 ~ 720M\nTTM 688M", C["saas"]),
    ]
    for x, title, body, c in items:
        ax.add_patch(
            FancyBboxPatch(
                (x, 0.28), 0.2, 0.5, boxstyle="round,pad=0.02,rounding_size=0.04",
                facecolor=c, edgecolor="white", lw=1.5, transform=ax.transAxes,
            )
        )
        ax.text(x + 0.1, 0.62, title, ha="center", transform=ax.transAxes,
                fontproperties=PROP_B, fontsize=10, color="white")
        ax.text(x + 0.1, 0.42, body, ha="center", transform=ax.transAxes,
                fontproperties=PROP, fontsize=8.2, color="white")
    ax.set_title("가이던스 — 컨센서스 (공식 숫자는 10-27 콜)", fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "06_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 28, 38, C["red"]),
        ("Base", 44, 56, C["teal"]),
        ("Bull", 58, 70, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} {lo}-{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"현재 {PX:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT평균 {PT:.0f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("시나리오 밴드 (예시 · 투자권유 아님)", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(20, 78)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    cards = [
        (0.2, 1.55, 3.0, 1.4, "실적 10-27", "Q3 컨센 187M\n논GAAP EPS 0.03", C["navy"]),
        (3.5, 1.55, 3.0, 1.4, "SaaS 레버리지", "GP 75% 방어\nSBC 소화", C["teal"]),
        (6.8, 1.55, 3.0, 1.4, "DSPM 점유", "피어셋 +1.5pp\nMSFT와 공존", C["saas"]),
        (0.2, 0.15, 3.0, 1.2, "현금환원", "Q1 자사주 135M\n순현금 182M", C["gold"]),
        (3.5, 0.15, 3.0, 1.2, "M&A 소화", "Q3'25 +105M\nQ1'26 +114M", C["rd"]),
        (6.8, 0.15, 3.0, 1.2, "리스크", "GP 압축 · 실적창\n업사이드 +5.6%", C["red"]),
    ]
    for x, y, w, h, title, body, c in cards:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + 0.12, y + h - 0.32, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.38, body, ha="center", va="center",
                fontproperties=PROP, fontsize=8, color="white")
    ax.set_title("촉매 · 게이트", fontproperties=PROP_B, fontsize=12, pad=4)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 2.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    ax.add_patch(
        FancyBboxPatch((0.3, 0.35), 9.4, 2.3, boxstyle="round,pad=0.04,rounding_size=0.12",
                       facecolor="#ecfeff", edgecolor=C["teal"], lw=2)
    )
    ax.text(
        5.0, 2.05,
        f"미보유 · 10-14 심층 본선∩GO_A · Chase 상(#2) · 고점 {NEAR*100:.0f}%",
        ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=C["teal"],
    )
    ax.text(
        5.0, 1.1,
        f"현재 {PX:.2f} · PT {PT:.0f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 {L52:.2f}-{H52:.2f}\n"
        "저녁창 지정가 후보 · 상한=종가+1.5% · 갭+2% VOID · 실적 10-27 (D-5는 10-22)",
        ha="center", va="center", fontproperties=PROP, fontsize=8.5, color=C["ink"],
    )
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
<div class="easy"><b>쉽게:</b> VRNS는 엔드포인트(크라우드스트라이크)가 아니라
<b>파일·클라우드에 쌓인 데이터 자체를 지키는</b> 회사다.
DSPM 오버레이 피어셋에서 스케일 점유 <b>~18% · Δ+1.5pp</b> 추정.
마이크로소프트 Purview가 365 번들로 커지고, Cyera·BigID는 비상장 도전자.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>
{gloss([
    ("DSPM", "Data Security Posture Management — 어디에 민감데이터가 있고 누가 지나치게 열려 있는지 지도."),
    ("Purview", "MSFT 365에 묶인 데이터거버넌스. 가격 경쟁·번들 압박의 본체."),
])}

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> VRNS 매출의 <b>~94%는 SaaS 구독</b>, 서비스는 랜딩·정착 보조.
옥타는 아이덴티티 구독, 크라우드스트라이크는 구독 비중이 비슷하지만
엔드포인트 거인이라 규모가 한 자릿수 다르다.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
{gloss([
    ("SaaS/Subscription", "연간(또는 다년) 클라우드 구독. 이연수익으로 인식 후 기간 안분."),
    ("이연매출", "이미 받은 구독대금 중 아직 수익으로 안 푼 선수금. Q2 $435M."),
])}
"""


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"VRNS 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0f766e; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0f766e; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0f766e; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ecfeff 0%,#e0f2fe 50%,#ccfbf1 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#ccfbf1; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecdd3; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#0f766e; color:#fff; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#ecfeff; border-left:4px solid #0f766e; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#0f766e; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0f766e; }}
    .box {{ background:#fffbeb; border:1px solid #d97706; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpis {{ width:92%; margin:18px auto 0; border-collapse:separate; border-spacing:8px; }}
    .kpis td {{ background:#fff; border:1px solid #cbd5e1; padding:8px 10px; width:25%;
      text-align:center; vertical-align:middle; }}
    .kpis .l {{ font-size:7.5pt; color:#64748b; }}
    .kpis .v {{ font-size:12pt; font-weight:700; color:#0f766e; }}
    .kpis .s {{ font-size:7.5pt; color:#0e7490; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>VRNS 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>VRNS 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Varonis Systems · 데이터보안 플랫폼 (DSPM · 접근거버넌스 · DDR)</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 (6/30) · 다음 실적 {EARN} · 시총 ~$5.60B · EV/S 7.9x</p>
  <table class="kpis">
    <tr>
      <td><div class="l">현재가</div><div class="v">${PX:.2f}</div><div class="s">52주고 ${H52:.2f}</div></td>
      <td><div class="l">PT 평균</div><div class="v">${PT:.0f}</div><div class="s">업사이드 {UPSIDE*100:+.1f}%</div></td>
      <td><div class="l">Q2 매출</div><div class="v">$180M</div><div class="s">+18% YoY</div></td>
      <td><div class="l">FCF Q2</div><div class="v">$20M</div><div class="s">TTM ~$118M</div></td>
    </tr>
  </table>
  <p style="margin-top:18px">
    <span class="tag good">본선∩GO_A</span>
    <span class="tag">Chase 상 #2</span>
    <span class="tag warn">업사이드 +5.6%</span>
    <span class="tag">다음 실적 {EARN}</span>
    <span class="tag">미보유</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>돈은 민감데이터를 찾아 잠그고 이상접근을 탐지하는 SaaS 플랫폼을 구독료로 판다.</b>
Q2'26: 매출 $180.0M(+18%) · GP 75.3%(YoY −4.2pp) · 영업손실 $40.6M · GAAP NI −$46.8M (EPS −$0.41) ·
논GAAP EPS $0.04 (Est $0.007 Beat). SBC $34.6M이 GAAP 적자의 본체.
OCF $25.1M · FCF $20.0M · 현금+단기 $698M · 장기부채 $453M · 순현금 ~$182M.
이연매출 $435M · Q1 자사주 $135M. 주가는 52주 고점 −24% · PT +5.6% —
<b>미보유 · 10-14 심층 본선∩GO_A · 저녁창 지정가 후보. 업사이드는 얇다.</b></p>
{fig_block(charts['flow'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 회사 파일서버·SharePoint·Salesforce·Snowflake에 “누가 손님 명단을 열어봤나”를
지도로 그려 주고, 너무 많이 열린 권한을 접고, 이상한 다운로드를 알린다.
크라우드스트라이크가 <u>노트북</u>을 지키면 Varonis는 <u>데이터 그 자체</u>를 지킨다.
구독이 본체라 현금은 흑자인데, 주식보상(SBC)이 커서 회계상 적자다.</div>
{gloss([
    ("DSPM", "민감데이터가 어디에 있고 노출이 어디인지 자세 관리."),
    ("DDR", "Data Detection &amp; Response — 데이터 활동 이상 탐지·대응."),
    ("SBC", "주식기준보상. Q2 $34.6M · 매출의 19%. GAAP 적자의 대부분."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['segmix'], '구독 믹스 · 분기 매출')}
{fig_block(charts['growth'], '성장 브리지')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>YoY / 메모</th><th>의미</th></tr>
  <tr><td><b>Total revenue</b></td><td>$180.0M</td><td>+18.3% vs $152.2M</td><td>TTM $688M</td></tr>
  <tr><td>SaaS 구독 (근사)</td><td>~94%</td><td>전환 완료권</td><td>반복매출 본체</td></tr>
  <tr><td>서비스 / Term</td><td>~4% / 2%</td><td>랜딩·정착</td><td>구독 전환 보조</td></tr>
  <tr><td>GAAP GP / 마진</td><td>$135.5M / 75.3%</td><td>전년 79.5%</td><td>호스팅 COGS로 −4.2pp</td></tr>
  <tr><td>R&amp;D / S&amp;M / G&amp;A</td><td>$73.3 / $79.0 / $23.8M</td><td>매출대비 41/44/13%</td><td>제품회사 코스트</td></tr>
  <tr><td>영업이익</td><td>−$40.6M</td><td>전년 −$36.6M</td><td>SBC+R&amp;D 부담</td></tr>
  <tr><td>GAAP NI / EPS</td><td>−$46.8M / −$0.41</td><td>적자 지속</td><td>희석 1.15억주</td></tr>
  <tr><td>논GAAP EPS</td><td>$0.04</td><td>Est $0.007 · Beat</td><td>4연속 Beat</td></tr>
  <tr><td>SBC</td><td>$34.6M</td><td>매출 19.2%</td><td>논GAAP 가산 본체</td></tr>
  <tr><td>OCF / FCF</td><td>$25.1M / $20.0M</td><td>FCF +16% YoY</td><td>현금은 흑자</td></tr>
</table>
<p class="small">GAAP 세그먼트는 단일(데이터보안 소프트웨어). 구독 스플릿은 SaaS 전환 이후 전형 근사.
출처: yfinance Q2'26 손익·현금흐름 (기간종료 2026-06-30) · 심층 rank_20261014.</p>
<div class="easy"><b>쉽게:</b> 성장은 살아 있다(+18%). 그런데 클라우드로 옮기며
서버비(COGS)가 늘어서 <b>매출총이익률이 79%→75%로 빠졌다</b>.
영업은 적자지만 고객이 선납하는 구독(이연매출 $435M) 덕분에
<b>통장(FCF)은 분기 $20M씩 들어온다</b>. 회계와 현금을 따로 봐야 한다.</div>
{gloss([
    ("이연매출", "받아 둔 구독료 중 아직 매출로 안 푼 선수금. 단기 $420M + 장기 $15M."),
    ("논GAAP EPS", "SBC·인수 상각 등을 더한 월가 컨센 기준. Q2 $0.04."),
])}

{compete_html}

<h2>2. 마진 · 레버리지 · 현금</h2>
{fig_block(charts['pnl'], '마진')}
{fig_block(charts['leverage'], '현금·부채')}
<ul>
  <li>매출 $180.0M · COGS $44.5M · 영업비용 $176.1M (R&amp;D $73.3 · S&amp;M $79.0 · G&amp;A $23.8)</li>
  <li>GP 75.3% (Q2'25 79.5%) — SaaS 호스팅·인수분 원가. TTM GP는 77.1%</li>
  <li>SBC $34.6M · D&amp;A $7.2M · 영업손실 $40.6M · 세전 −$41.4M</li>
  <li>현금+단기투자 $698M · 장기부채 $453M (전환사채 성격) · 리스 $63M · <b>순현금 ~$182M</b></li>
  <li>이연매출 $435M · 매출채권 $151M · 영업권 $215M (Q3'25 M&amp;A ~$105M + Q1'26 ~$114M)</li>
  <li>Q1'26 자사주 $135M · 발행주식 1.149억 (연말 1.175억에서 감소)</li>
  <li>TTM FCF ~$118M · EV $5.43B · EV/S 7.9x · 시총 $5.60B</li>
</ul>

<h2>3. 전망 · 시나리오</h2>
{fig_block(charts['guide'], 'Q3 컨센서스')}
{fig_block(charts['scen'], '주가 시나리오')}
<table>
  <tr><th>드라이버</th><th>내용</th></tr>
  <tr><td>Q3 컨센</td><td>매출 $185.8–189.2M (평균 $186.9M) · EPS ~$0.03 · 실적일 2026-10-27</td></tr>
  <tr><td>SaaS</td><td>구독 정착 + 클라우드 패키지(M365·하이브리드) · GP 75% 방어가 게이트</td></tr>
  <tr><td>경쟁</td><td>MSFT Purview 번들 · Cyera/BigID 비상장 · OKTA·SAIL은 아이덴티티 인접</td></tr>
  <tr><td>자본</td><td>순현금 + 자사주 여력 · 전환사채 희석 모니터링</td></tr>
  <tr><td>밸류</td><td>${PX:.2f} · PT ${PT:.0f} (H $60 / L $28) · 52주 ${L52:.2f}–${H52:.2f} · 업사이드 {UPSIDE*100:+.1f}% · EV/S 7.9x</td></tr>
</table>
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$28–38</td><td>GP 추가 압축 · 성장 &lt;10% · Purview 점유 잠식 · PT 하단</td></tr>
  <tr><td>Base</td><td>$44–56</td><td>Q3 컨센 근접 · FCF 유지 · 현재가가 이 밴드 안</td></tr>
  <tr><td>Bull</td><td>$58–70</td><td>GP 반등 + 성장 재가속 · PT 상단·52주 고점 재도전</td></tr>
</table>

<h2>4. 촉매 · 포트 실행</h2>
{fig_block(charts['cat'], '촉매')}
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (10-14 포폴 · 10-14 심층)</b><br/>
<b>미보유</b> · 10-14 심층 Chase <b>상 #2</b> · 본선∩GO_A · 엔트리 <b>저녁창 지정가</b>.<br/>
현재 ${PX:.2f} · 컨센서스 PT ${PT:.0f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}–${H52:.2f}
(고점 −{(1-PX/H52)*100:.1f}%).<br/>
실행: 상한=종가+1.5% · 갭+2% VOID · 시장가·돌파추격 금지 · KR 17:30~20:55.<br/>
실적 <b>2026-10-27</b> · EARN_D5 시작은 <b>10-22</b> (오늘은 D-13, 창 아직 열림).<br/>
게이트: Q3 매출/GP · 논GAAP EPS · FCF · ARR/이연매출 · Purview 코멘트 · SBC.
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>SaaS 구독 94% + 현금흑자(FCF $20M) + 순현금</u>.
회계 적자는 SBC 착시가 크다. 다만 <b>GP가 빠져 있고 PT 업사이드 +5.6%로 얇다</b>.
심층은 타이밍 GO라 지정가 후보는 맞지만, 사이즈는 작게 · 실적창(10-22~) 전에 갭 리스크를 열어 둘 것.</div>

<h2>부록 · 출처</h2>
<p class="small">
Varonis Q2 2026 분기 실적(기간 종료 2026-06-30, yfinance 손익·CF·BS) ·
Q3 컨센(매출 $186.9M / EPS $0.03) · 심층 rank_20261014 (px/PT/52주).
피어 믹스·점유는 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 VRNS · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> int:
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "segmix": chart_segment_mix(),
        "growth": chart_growth_bridge(),
        "pnl": chart_pnl(),
        "leverage": chart_leverage(),
        "guide": chart_guide(),
        "scen": chart_scenarios(),
        "cat": chart_catalysts(),
        "pos": chart_position(),
    }
    bundle, cpaths = build_compete_charts("VRNS", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("VRNS", CHART_DIR, html_doc)
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

        tag = "sepa-rev-vrns"
        notes = (
            f"## VRNS 수익구조분석 ({ASOF})\n\n"
            f"Varonis · 데이터보안 플랫폼 (DSPM) · Q2'26.\n\n"
            f"- Rev $180.0M (+18%) · GP 75.3% (YoY −4.2pp) · FCF $20.0M\n"
            f"- SaaS ~94% · SBC $34.6M · 순현금 ~$182M · 이연매출 $435M\n"
            f"- 미보유 · 10-14 심층 본선∩GO_A · Chase 상 #2\n"
            f"- 업사이드 {UPSIDE*100:+.1f}% (PT ${PT:.0f} · px ${PX:.2f})\n"
            f"- 저녁창 지정가 · 다음 실적 2026-10-27 · D-5=10-22\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — VRNS",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
