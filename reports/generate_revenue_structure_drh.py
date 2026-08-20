#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(DRH) — DiamondRock 호텔 REIT + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-08-20"
PX = 12.72
PT = 13.33
H52 = 13.79
UPSIDE = PT / PX - 1.0
EARN = "07-30"  # Q2'26 reported
OUT_PDF = [
    Path("/opt/cursor/artifacts/DRH_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/DRH_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/DRH_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/DRH_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/drh")
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
    "slate": "#334155",
    "room": "#0e7490",
    "fb": "#c2410c",
    "oth": "#7c3aed",
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
    lis = "".join(
        f"<li><span class='term'>{t}</span> — {d}</li>" for t, d in items
    )
    return f"<div class='gloss'><div class='gloss-title'>용어</div><ul>{lis}</ul></div>"


def chart_business_flow() -> Path:
    fig, ax = plt.subplots(figsize=(9.2, 3.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    boxes = [
        (0.1, 0.7, 1.85, 1.6, "여행·그룹\n수요", C["sand"]),
        (2.15, 0.7, 1.75, 1.6, "34개 프리미엄\n호텔 소유", C["room"]),
        (4.1, 0.7, 1.75, 1.6, "브랜드·독립\n매니저 운영", C["teal"]),
        (6.05, 0.7, 1.7, 1.6, "RevPAR·\n호텔 EBITDA", C["navy"]),
        (7.95, 0.7, 1.75, 1.6, "배당·FFO\n·리파이낸스", C["teal2"]),
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
            fontproperties=PROP_B, fontsize=8.5, color=tc,
        )
    ax.set_title(
        "비즈니스 한눈에 — 호텔을 소유하고 현금흐름(FFO)을 돌린다",
        fontproperties=PROP_B, fontsize=12, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [65, 25, 10]
    labels = ["Rooms ~65%", "F&B ~25%", "Other ~10%"]
    ax.pie(
        sizes, labels=labels,
        colors=[C["room"], C["fb"], C["oth"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.5),
    )
    ax.set_title("매출 믹스 (Q2'26 근사)", fontproperties=PROP_B, fontsize=10)

    ax = axes[1]
    labs = ["Q2'25", "Q2'26"]
    room = [192.6, 206.0]
    tot = [300.0, 316.6]
    x = range(len(labs))
    ax.bar([i - 0.18 for i in x], room, width=0.35, color=C["room"], label="Comp Rooms")
    ax.bar([i + 0.18 for i in x], tot, width=0.35, color=C["teal"], label="Comp Total")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labs, fontproperties=PROP)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("Comparable 매출", fontproperties=PROP_B, fontsize=10)
    ax.legend(prop=PROP, fontsize=8)
    for i, (r, t) in enumerate(zip(room, tot)):
        ax.text(i - 0.18, r + 4, f"{r:.0f}", ha="center", fontsize=7.5, fontproperties=PROP)
        ax.text(i + 0.18, t + 4, f"{t:.0f}", ha="center", fontsize=7.5, fontproperties=PROP)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_ops_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    labels = [
        "Comp\nRevPAR\n+7.0%",
        "호텔비용\n+1.8%*",
        "Hotel Adj.\nEBITDA\n$113M",
        "Adj.\nEBITDA\n$108M",
        "Adj. FFO\n$0.44",
    ]
    vals = [7.0, 1.8, 20.9, 19.2, 25.7]
    colors = [C["green"], C["gold"], C["teal"], C["teal2"], C["navy"]]
    bars = ax.bar(labels, vals, color=colors, width=0.55)
    ax.axhline(0, color="#ccc", lw=0.8)
    ax.set_ylabel("YoY % (RevPAR·비용·이익)", fontproperties=PROP)
    ax.set_title(
        "운영 레버리지 — RevPAR↑ · 비용억제 → 마진·FFO 확대",
        fontproperties=PROP_B, fontsize=11,
    )
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2, v + 0.6, f"+{v:.1f}%",
            ha="center", fontproperties=PROP, fontsize=8,
        )
    ax.text(
        0.98, 0.02, "*시카고 재산세 일회성 제외 시 비용 +1.8%",
        transform=ax.transAxes, ha="right", fontsize=7.5,
        color=C["muted"], fontproperties=PROP,
    )
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "03_ops_bridge.png")


def chart_revpar() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    q = ["Q1'26", "Q2'26"]
    revpar = [189.54, 240.79]
    trevpar = [300.46, 370.06]
    x = range(len(q))
    ax.plot(list(x), revpar, "o-", color=C["room"], lw=2.2, label="Comp RevPAR $")
    ax.plot(list(x), trevpar, "s-", color=C["fb"], lw=2.2, label="Comp Total RevPAR $")
    ax.set_xticks(list(x))
    ax.set_xticklabels(q, fontproperties=PROP)
    ax.set_ylabel("$", fontproperties=PROP)
    ax.set_title("분기 RevPAR · Total RevPAR", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8)
    for i, (r, t) in enumerate(zip(revpar, trevpar)):
        ax.text(i, r + 6, f"{r:.0f}", ha="center", fontsize=8, fontproperties=PROP, color=C["room"])
        ax.text(i, t + 6, f"{t:.0f}", ha="center", fontsize=8, fontproperties=PROP, color=C["fb"])
    fig.tight_layout()
    return save_fig(fig, "04_revpar.png")


def chart_guide() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    metrics = ["RevPAR\n성장%", "Adj.EBITDA\n$M", "Adj.FFO/sh\n$"]
    prior_mid = [2.5, 296.2, 1.13]
    new_mid = [3.25, 315.0, 1.205]
    x = range(len(metrics))
    ax.bar([i - 0.18 for i in x], prior_mid, width=0.35, color="#94a3b8", label="이전 가이던스 중점")
    ax.bar([i + 0.18 for i in x], new_mid, width=0.35, color=C["teal"], label="상향 후 중점")
    ax.set_xticks(list(x))
    ax.set_xticklabels(metrics, fontproperties=PROP)
    ax.set_title("FY'26 가이던스 상향 (중점 비교)", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8)
    for i, (a, b) in enumerate(zip(prior_mid, new_mid)):
        ax.text(i - 0.18, a + max(new_mid) * 0.02, f"{a:g}", ha="center", fontsize=7.5, fontproperties=PROP)
        ax.text(i + 0.18, b + max(new_mid) * 0.02, f"{b:g}", ha="center", fontsize=7.5, fontproperties=PROP)
    fig.tight_layout()
    return save_fig(fig, "05_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    bands = [("Bear", 9.5, 11.0), ("Base", 11.5, 13.5), ("Bull", 14.0, 16.0)]
    colors = [C["red"], C["gold"], C["green"]]
    for i, ((name, lo, hi), c) in enumerate(zip(bands, colors)):
        ax.barh(i, hi - lo, left=lo, height=0.45, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo:.1f}–{hi:.1f}", ha="center", va="center",
                color="white", fontproperties=PROP_B, fontsize=9)
    ax.axvline(PX, color=C["navy"], ls="--", lw=1.4, label=f"현재 ${PX:.2f}")
    ax.axvline(PT, color=C["teal"], ls=":", lw=1.4, label=f"PT ${PT:.2f}")
    ax.set_yticks([])
    ax.set_xlabel("주가 $", fontproperties=PROP)
    ax.set_title("시나리오 밴드", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8, loc="lower right")
    fig.tight_layout()
    return save_fig(fig, "06_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.0)
    ax.axis("off")
    cards = [
        (0.2, 0.4, 2.2, 2.1, "가이던스\n상향 유지", C["teal"]),
        (2.7, 0.4, 2.2, 2.1, "그룹 예약\n페이스", C["room"]),
        (5.2, 0.4, 2.2, 2.1, "배당 $0.11\n+자사주", C["navy"]),
        (7.7, 0.4, 2.0, 2.1, "리노·매각\n캐펙스", C["gold"]),
    ]
    for x, y, w, h, t, c in cards:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        ax.text(
            x + w / 2, y + h / 2, t, ha="center", va="center",
            color="white", fontproperties=PROP_B, fontsize=9,
        )
    ax.set_title("촉매 카드", fontproperties=PROP_B, fontsize=11, pad=4)
    return save_fig(fig, "07_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.0)
    ax.axis("off")
    ax.add_patch(
        FancyBboxPatch(
            (0.3, 0.5), 9.2, 2.0, boxstyle="round,pad=0.05,rounding_size=0.12",
            facecolor="#ecfdf5", edgecolor=C["teal"], lw=2,
        )
    )
    ax.text(
        5.0, 1.9, "미보유 · 본선∩GO_A · TA 분할OK",
        ha="center", va="center", fontproperties=PROP_B, fontsize=12, color=C["teal"],
    )
    ax.text(
        5.0, 1.15,
        f"진입 ${12.37:.2f}–${12.63:.2f} · stop ${11.94:.2f} · PT ${PT:.2f} (업사이드 {UPSIDE*100:+.1f}%)\n"
        "업사이드 얇음 · 고점 −7.8% · 위성 소액만 · 추격 금지",
        ha="center", va="center", fontproperties=PROP, fontsize=9, color=C["ink"],
    )
    return save_fig(fig, "08_position.png")


def chart_portfolio_map() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    boxes = [
        (0.3, 0.5, 2.8, 2.2, "34 hotels\n9,400 rooms", C["room"], "포트폴리오"),
        (3.5, 0.5, 2.8, 2.2, "~40% Independent\nLifestyle", C["fb"], "운영 형태"),
        (6.7, 0.5, 2.8, 2.2, "Urban gateway\n+ Leisure resort", C["navy"], "입지 믹스"),
    ]
    for x, y, w, h, t, c, title in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        ax.text(x + w / 2, y + h * 0.72, title, ha="center", color="#ccfbf1",
                fontproperties=PROP, fontsize=8)
        ax.text(x + w / 2, y + h * 0.38, t, ha="center", color="white",
                fontproperties=PROP_B, fontsize=10)
    ax.set_title("자산 지도 — 소유 REIT (운영은 매니저)", fontproperties=PROP_B, fontsize=11)
    return save_fig(fig, "09_portfolio_map.png")


def _compete_section(charts: dict[str, Path], bundle) -> str:
    if bundle is None:
        return ""
    share_rows = ""
    for r in bundle.share_rows:
        d = r.delta_pp
        share_rows += (
            f"<tr><td>{r.name}</td><td>{r.current:.1f}%</td>"
            f"<td>{r.prior:.1f}%</td><td>{d:+.1f}pp</td></tr>"
        )
    mix_head = "".join(f"<th>{b}</th>" for b in bundle.mix_buckets)
    mix_body = []
    for row in bundle.mix_rows:
        cells = "".join(
            f"<td>{row['mix'].get(b, 0):.0f}%</td>" for b in bundle.mix_buckets
        )
        bold = " style='font-weight:700;background:#ecfdf5'" if row.get("subject") else ""
        mix_body.append(
            f"<tr{bold}><td>{row['name']}</td>{cells}"
            f"<td class='small'>{row.get('note','')}</td></tr>"
        )
    ttm_fig = fig_block(charts["ttm"], "TTM 매출 규모") if "ttm" in charts else ""
    return f"""
<h2>1-B. 심층 섹터 경쟁 점유율 · 변화</h2>
<p><b>섹터</b> {bundle.sector_ko}</p>
<div class="easy"><b>쉽게:</b> DRH는 상장 호텔 REIT 피어셋에서 <b>중하위 스케일(~7%)</b>다.
HST가 ~39%로 압도적. DRH 점유 Δ는 <b>소폭 하락(−0.3pp)</b> 추정 — 절대 시장점유가 아니라
피어 대비 상대 크기 비교.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> 호텔 매출은 대부분 <b>객실(Rooms)</b>, 그다음 식음(F&amp;B), 기타(주차·스파 등).
DRH는 룸 ~65% · F&amp;B ~25%로 풀서비스·라이프스타일 쪽에 가깝다.
셀렉트서비스(APLE)는 룸 비중이 훨씬 높다.</div>
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
      @bottom-center {{ content:"DRH 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0f766e; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #14b8a6; padding-bottom:3px; color:#0f766e; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#1e3a5f; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ecfeff 0%,#f0fdfa 55%,#e0f2fe 100%);
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
    .easy {{ background:#f0fdfa; border-left:4px solid #0f766e; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#0f766e; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0e7490; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#0f766e; }}
    .kpi .s {{ font-size:7.5pt; color:#0e7490; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>DRH 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>DRH 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">DiamondRock Hospitality · 미국 프리미엄 호텔 REIT</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적({EARN} 발표) · 시총 ~$2.6B · ${PX:.2f}</p>
  <div style="margin-top:22px">
    <span class="tag good">Comp RevPAR +7.0%</span>
    <span class="tag good">Adj.EBITDA +19%</span>
    <span class="tag good">FY26 가이던스 상향</span>
    <span class="tag">배당 $0.11 (+22%)</span>
    <span class="tag warn">업사이드 얇음</span>
    <span class="tag good">본선∩GO_A</span>
  </div>
  <div style="margin-top:28px">
    <div class="kpi"><div class="l">Q2 매출</div><div class="v">$318M</div><div class="s">YoY +4.1%</div></div>
    <div class="kpi"><div class="l">Adj.EBITDA</div><div class="v">$108M</div><div class="s">YoY +19%</div></div>
    <div class="kpi"><div class="l">Adj.FFO/sh</div><div class="v">$0.44</div><div class="s">YoY +26%</div></div>
    <div class="kpi"><div class="l">업사이드</div><div class="v">{UPSIDE*100:+.1f}%</div><div class="s">PT ${PT:.2f}</div></div>
  </div>
  <p class="small" style="margin-top:36px;max-width:520px;margin-left:auto;margin-right:auto">
    34개 프리미엄 호텔(~9,400실) 소유 REIT. ~40% 독립 라이프스타일, 나머지 글로벌 브랜드.
    Q2는 RevPAR·마진 레버리지로 FFO 확대·가이던스·배당 상향. 다만 PT 업사이드는 얇고 고점 근접.
  </p>
</section>

<h2>0. 한줄 결론</h2>
<div class="box">
<b>운영은 강한데, 밸류에이션 여유는 얇다.</b>
Q2'26 Comp RevPAR +7% · 호텔비용 +1.8%(일회성 제외) · Hotel Adj.EBITDA 마진 +239~457bps ·
Adj.FFO/sh $0.44(+26%) · FY26 가이던스·분기배당 상향은 명확한 플러스.
시카고 재산세 $6.9M 일회성·월드컵 테일윈드·PT 업사이드 ~+4.8%는 할인 요인.
포트: <b>미보유 · 본선∩GO_A · TA 분할OK</b> — 위성 소액·지정가·추격 금지.
</div>

<h2>1. 비즈니스 구조</h2>
<div class="easy"><b>쉽게:</b> DiamondRock은 호텔을 <b>직접 운영하지 않고 소유</b>한다.
매니저·브랜드에 수수료를 주고, 남는 호텔 영업이익을 REIT 현금흐름(FFO)·배당으로 돌린다.</div>
{fig_block(charts['flow'], '수요 → 소유 호텔 → RevPAR → FFO/배당')}
{fig_block(charts['pmap'], '포트폴리오 구성')}
{gloss([
    ("REIT", "부동산투자신탁. 과세소득 대부분을 배당으로 보내 법인세를 줄이는 구조"),
    ("RevPAR", "Revenue Per Available Room = ADR × Occupancy. 호텔 핵심 KPI"),
    ("Hotel Adj. EBITDA", "개별 호텔 영업현금창출력(본사비·이자·감가 제외)"),
    ("FFO / Adj. FFO", "REIT 현금이익 근사. 감가상각 가산 등 조정"),
])}

{compete_html}

<h2>2. 매출·운영 (Q2'26)</h2>
<div class="easy"><b>쉽게:</b> 방 값(RevPAR)이 7% 올랐는데 비용은 ~2%만 올라
호텔 이익이 21% 늘었다. “가격·점유↑ + 비용억제 = 레버리지”.</div>
{fig_block(charts['mix'], '룸/식음 믹스 + Comparable 매출')}
{fig_block(charts['revpar'], 'RevPAR 추이')}
{fig_block(charts['bridge'], '운영 레버리지 브리지')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>Q2'25</th><th>메모</th></tr>
  <tr><td>Total Revenues (Actual)</td><td>$318.3M</td><td>$305.7M</td><td>+4.1%</td></tr>
  <tr><td>Comp Room Revenues</td><td>$206.0M</td><td>$192.6M</td><td>+7.0%</td></tr>
  <tr><td>Comp RevPAR</td><td>$240.79</td><td>$225.03</td><td>+7.0% · ADR+Occ</td></tr>
  <tr><td>Comp Total RevPAR</td><td>$370.06</td><td>$350.49</td><td>+5.6%</td></tr>
  <tr><td>Hotel Adj. EBITDA</td><td>$113.2M</td><td>$93.6M</td><td>+20.9% · 마진 35.8%</td></tr>
  <tr><td>Adj. EBITDA</td><td>$107.9M</td><td>$90.5M</td><td>+19.2%</td></tr>
  <tr><td>Adj. FFO / dil. sh</td><td>$0.44</td><td>$0.35</td><td>+25.7% · ex-tax $0.41</td></tr>
  <tr><td>GAAP NI (common)</td><td>$90.5M</td><td>—</td><td>$0.44 / dil. sh</td></tr>
</table>
{gloss([
    ("ADR", "Average Daily Rate — 평균 객실단가. Q2 $308.50 (+4.6%)"),
    ("Occupancy", "점유율. Q2 78.1% (+1.8pp)"),
    ("시카고 재산세", "Q2 일회성 +$6.9M. 제외 시 FFO/sh $0.41 · 마진 +239bps"),
])}

<h2>3. 가이던스 · 자본배분</h2>
{fig_block(charts['guide'], 'FY26 가이던스 상향')}
<div class="easy"><b>쉽게:</b> 회사가 “올해 더 잘할 것 같다”고 숫자를 올렸다.
RevPAR 성장·EBITDA·FFO/주 모두 중점이 상향. 배당도 $0.09→$0.11(+22%).</div>
<table>
  <tr><th>지표</th><th>이전</th><th>상향 후</th><th>중점 Δ</th></tr>
  <tr><td>Comp RevPAR Growth</td><td>1.5–3.5%</td><td>2.5–4.0%</td><td>+75bps</td></tr>
  <tr><td>Comp Total RevPAR Growth</td><td>1.75–3.75%</td><td>2.75–4.25%</td><td>+75bps</td></tr>
  <tr><td>Adj. EBITDA</td><td>$290–302M</td><td>$310–320M</td><td>+$19M</td></tr>
  <tr><td>Adj. FFO</td><td>$228–240M</td><td>$246–256M</td><td>+$16M</td></tr>
  <tr><td>Adj. FFO / sh</td><td>$1.10–1.16</td><td>$1.18–1.23</td><td>+$0.075</td></tr>
</table>
<table>
  <tr><th>자본·BS (6/30)</th><th>내용</th></tr>
  <tr><td>부채</td><td>$1.1B 텀론 · 가중금리 ~4.9% · RCF $400M 미인출</td></tr>
  <tr><td>현금</td><td>비제한 ~$106M</td></tr>
  <tr><td>자사주</td><td>$300M 한도 · Q2 $1.9M 매입 · 잔여 $299M</td></tr>
  <tr><td>배당</td><td>Q3 $0.11/주 (+22%) · 연환산 ~$0.44 + stub 가능</td></tr>
  <tr><td>자산매각</td><td>Courtyard NYC Fifth Ave 리스홀드 $33M (5/1)</td></tr>
</table>

<h2>4. 시나리오 · 촉매</h2>
{fig_block(charts['scen'], '주가 시나리오 밴드')}
{fig_block(charts['cat'], '촉매 카드')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$9.5–11</td><td>여행수요 둔화 · RevPAR 가이던스 미달 · 금리·비용 재상승</td></tr>
  <tr><td>Base</td><td>$11.5–13.5</td><td>가이던스 달성 · 배당 유지 · 그룹 페이스 안정</td></tr>
  <tr><td>Bull</td><td>$14–16</td><td>RevPAR 상단 · 마진 지속 · 자사주·배당 가속</td></tr>
</table>

<h2>5. 포트 실행</h2>
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (8/20 심층)</b><br/>
미보유 · Chase 중·실적직후·고점 · <b>본선∩GO_A</b> · TA <b>분할OK</b>.<br/>
진입 ${12.37:.2f}–${12.63:.2f} · stop ${11.94:.2f} · PT ${PT:.2f} (업사이드 {UPSIDE*100:+.1f}%) · 고점대비 −7.8%.<br/>
실행: 저녁창 KR 17:30~20:55 <b>지정가</b> · 상한=종가+1.5% · 갭+2% VOID · 시장가·돌파추격 금지.<br/>
사이징: 업사이드 얇아 <b>위성 소액</b> · 현금바닥 $150 유지 · 물타기 금지.<br/>
품질 게이트: 다음 분기에도 Comp RevPAR≥가이던스 · Hotel 마진 유지 · 일회성 제외 FFO 궤적.
</div>

<p class="small">생성: 수익구조분석() · 티커 DRH · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart<br/>
출처: DiamondRock Q2'26 earnings release (2026-07-30) · yfinance · 피어 점유/믹스는 방향 비교용 추정</p>
</body></html>
"""


def main() -> int:
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "bridge": chart_ops_bridge(),
        "revpar": chart_revpar(),
        "guide": chart_guide(),
        "scen": chart_scenarios(),
        "cat": chart_catalysts(),
        "pos": chart_position(),
        "pmap": chart_portfolio_map(),
    }
    bundle, cpaths = build_compete_charts("DRH", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("DRH", CHART_DIR, html_doc)
    OUT_HTML.write_text(html_doc, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    pdf = HTML(filename=str(OUT_HTML)).write_pdf()
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf)
        print(f"PDF {p} {p.stat().st_size}")
    # Mobile download
    try:
        from sepa.artifacts import print_release_result, publish_github_release_asset

        tag = "sepa-rev-drh"
        notes = (
            f"## DRH 수익구조분석 ({ASOF})\n\n"
            f"DiamondRock Hospitality · Q2'26 · Comp RevPAR +7% · FY26 가이던스 상향.\n\n"
            f"- 본선∩GO_A · TA 분할OK · 업사이드 {UPSIDE*100:+.1f}% (PT ${PT:.2f})\n"
            f"- 진입 $12.37–$12.63 · stop $11.94 · 위성 소액·추격 금지\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — DRH",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
