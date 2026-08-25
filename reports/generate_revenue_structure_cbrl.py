#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(CBRL) — Cracker Barrel 레스토랑+리테일 + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-08-25"
PX = 58.02
PT = 45.00
H52 = 63.15
L52 = 24.85
UPSIDE = PT / PX - 1.0
EARN = "06-09"  # Q3 FY'26 reported (ended 5/1/26)
OUT_PDF = [
    Path("/opt/cursor/artifacts/CBRL_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/CBRL_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/CBRL_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/CBRL_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/cbrl")
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
    "rest": "#b45309",
    "retail": "#0369a1",
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
    lis = "".join(f"<li><span class='term'>{t}</span> — {d}</li>" for t, d in items)
    return f"<div class='gloss'><div class='gloss-title'>용어</div><ul>{lis}</ul></div>"


def chart_business_flow() -> Path:
    fig, ax = plt.subplots(figsize=(9.2, 3.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    boxes = [
        (0.1, 0.7, 1.85, 1.6, "고속도로·\n가족 수요", C["sand"]),
        (2.15, 0.7, 1.75, 1.6, "~660 매장\n(+Maple St)", C["rest"]),
        (4.1, 0.7, 1.75, 1.6, "홈스타일\n식사", C["teal"]),
        (6.05, 0.7, 1.7, 1.6, "Old Country\nStore 리테일", C["retail"]),
        (7.95, 0.7, 1.75, 1.6, "매출·\nAdj EBITDA", C["navy"]),
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
        "비즈니스 한눈에 — 식당 + 선물가게가 한 지붕",
        fontproperties=PROP_B, fontsize=12, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [82.6, 17.4]
    labels = ["Restaurant 82.6%", "Retail 17.4%"]
    ax.pie(
        sizes, labels=labels,
        colors=[C["rest"], C["retail"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.5),
    )
    ax.set_title("매출 믹스 (Q3 FY'26)", fontproperties=PROP_B, fontsize=10)

    ax = axes[1]
    labs = ["Q3'25", "Q3'26"]
    rest = [679.0, 658.4]  # approx prior from mix; PR: rest $658.4 / retail $139
    retail = [142.1, 139.0]
    x = range(len(labs))
    ax.bar([i - 0.18 for i in x], rest, width=0.35, color=C["rest"], label="Restaurant")
    ax.bar([i + 0.18 for i in x], retail, width=0.35, color=C["retail"], label="Retail")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labs, fontproperties=PROP)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("세그먼트 매출", fontproperties=PROP_B, fontsize=10)
    ax.legend(prop=PROP, fontsize=8)
    for i, (r, t) in enumerate(zip(rest, retail)):
        ax.text(i - 0.18, r + 8, f"{r:.0f}", ha="center", fontsize=7.5, fontproperties=PROP)
        ax.text(i + 0.18, t + 8, f"{t:.0f}", ha="center", fontsize=7.5, fontproperties=PROP)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_traffic_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    labels = [
        "Rest Comp\n−2.6%",
        "Traffic\n−6.7%",
        "Check\n+4.3%",
        "Retail Comp\n−1.8%",
        "Adj EBITDA\n$40.3M",
    ]
    vals = [-2.6, -6.7, 4.3, -1.8, -16.2]  # EBITDA YoY ~−16%
    colors = [C["gold"], C["red"], C["green"], C["gold"], C["navy"]]
    bars = ax.bar(labels, vals, color=colors, width=0.55)
    ax.axhline(0, color="#ccc", lw=0.8)
    ax.set_ylabel("% (또는 YoY)", fontproperties=PROP)
    ax.set_title(
        "트래픽↓ · 체크↑ — 가격으로 버티지만 방문은 아직 약함",
        fontproperties=PROP_B, fontsize=11,
    )
    for b, v in zip(bars, vals):
        label = f"{v:+.1f}%".replace("\u2212", "-")
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + (0.5 if v >= 0 else -1.2),
            label,
            ha="center", fontproperties=PROP, fontsize=8,
        )
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "03_traffic_bridge.png")


def chart_pnl_quality() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    labs = ["Revenue\n$M", "Adj EBITDA\n$M", "GAAP NI\n$M", "Adj NI\n$M"]
    q325 = [821.1, 48.1, 12.6, 13.1]
    q326 = [797.4, 40.3, 42.8, 6.5]
    x = range(len(labs))
    ax.bar([i - 0.18 for i in x], q325, width=0.35, color="#94a3b8", label="Q3'25")
    ax.bar([i + 0.18 for i in x], q326, width=0.35, color=C["teal"], label="Q3'26")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labs, fontproperties=PROP)
    ax.set_title("손익 품질 — GAAP는 소송합의 $47M 포함", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8)
    fig.tight_layout()
    return save_fig(fig, "04_pnl_quality.png")


def chart_guide() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    metrics = ["매출\n$B 중점", "Adj EBITDA\n$M 중점"]
    prior = [3.255, 92.5]
    new = [3.285, 122.5]
    x = range(len(metrics))
    ax.bar([i - 0.18 for i in x], prior, width=0.35, color="#94a3b8", label="이전 가이던스 중점")
    ax.bar([i + 0.18 for i in x], new, width=0.35, color=C["teal"], label="상향 후 중점")
    ax.set_xticks(list(x))
    ax.set_xticklabels(metrics, fontproperties=PROP)
    ax.set_title("FY'26 가이던스 상향 (중점)", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8)
    for i, (a, b) in enumerate(zip(prior, new)):
        ax.text(i - 0.18, a + max(new) * 0.02, f"{a:g}", ha="center", fontsize=7.5, fontproperties=PROP)
        ax.text(i + 0.18, b + max(new) * 0.02, f"{b:g}", ha="center", fontsize=7.5, fontproperties=PROP)
    fig.tight_layout()
    return save_fig(fig, "05_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    bands = [("Bear", 28.0, 40.0), ("Base", 42.0, 52.0), ("Bull", 55.0, 68.0)]
    colors = [C["red"], C["gold"], C["green"]]
    for i, ((name, lo, hi), c) in enumerate(zip(bands, colors)):
        ax.barh(i, hi - lo, left=lo, height=0.45, color=c, alpha=0.85)
        ax.text(
            (lo + hi) / 2, i, f"{name} ${lo:.0f}–{hi:.0f}",
            ha="center", va="center", color="white", fontproperties=PROP_B, fontsize=9,
        )
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
        (0.2, 0.4, 2.2, 2.1, "트래픽\n개선 지속?", C["gold"]),
        (2.7, 0.4, 2.2, 2.1, "메뉴·게스트\n메트릭", C["rest"]),
        (5.2, 0.4, 2.2, 2.1, "FY26 EBITDA\n가이던스", C["teal"]),
        (7.7, 0.4, 2.0, 2.1, "다음 실적\n(~09-16)", C["navy"]),
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
            facecolor="#fff1f2", edgecolor=C["red"], lw=2,
        )
    )
    ax.text(
        5.0, 1.9, "미보유 · Chase 하·과열 · PT 프리미엄 · 추격 금지",
        ha="center", va="center", fontproperties=PROP_B, fontsize=12, color=C["red"],
    )
    ax.text(
        5.0, 1.15,
        f"현재 ${PX:.2f} · PT ${PT:.2f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 고점 ${H52:.2f}\n"
        "GO_A 타이밍만으로는 본선 제외 · 눌림·트래픽 확인 전 신규 비추",
        ha="center", va="center", fontproperties=PROP, fontsize=9, color=C["ink"],
    )
    return save_fig(fig, "08_position.png")


def chart_cogs() -> Path:
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    cats = ["Rest COGS\n% of Rest", "Retail COGS\n% of Retail", "Total COGS\n% of Rev"]
    prior = [26.2, 48.9, 30.1]
    curr = [26.1, 49.8, 30.2]
    x = range(len(cats))
    ax.bar([i - 0.18 for i in x], prior, width=0.35, color="#94a3b8", label="Q3'25")
    ax.bar([i + 0.18 for i in x], curr, width=0.35, color=C["rest"], label="Q3'26")
    ax.set_xticks(list(x))
    ax.set_xticklabels(cats, fontproperties=PROP)
    ax.set_ylabel("%", fontproperties=PROP)
    ax.set_title("원가율 — 레스토랑 안정 · 리테일 관세↑", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, fontsize=8)
    fig.tight_layout()
    return save_fig(fig, "09_cogs.png")


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
        bold = " style='font-weight:700;background:#fff7ed'" if row.get("subject") else ""
        mix_body.append(
            f"<tr{bold}><td>{row['name']}</td>{cells}"
            f"<td class='small'>{row.get('note','')}</td></tr>"
        )
    ttm_fig = fig_block(charts["ttm"], "TTM 매출 규모") if "ttm" in charts else ""
    return f"""
<h2>1-B. 심층 섹터 경쟁 점유율 · 변화</h2>
<p><b>섹터</b> {bundle.sector_ko}</p>
<div class="easy"><b>쉽게:</b> CBRL는 상장 캐주얼 다이닝 피어셋에서 <b>하위권(~9%)</b>이다.
Darden이 ~36%로 압도. CBRL 점유 Δ는 <b>하락(−1.2pp)</b> 추정 — 매출이 줄어든 구간.
절대 시장점유가 아니라 피어 대비 상대 크기.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> 대부분의 캐주얼 체인은 <b>거의 100% 식사</b>다.
CBRL만 <b>리테일 ~17%</b>이 붙어 있다 — 차별점이자 관세·재고 리스크 원천.</div>
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
      @bottom-center {{ content:"CBRL 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#b45309; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #d97706; padding-bottom:3px; color:#92400e; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#1e3a5f; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#fff7ed 0%,#fef3c7 55%,#ffedd5 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#ffedd5; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecdd3; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#b45309; color:#fff; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#fff7ed; border-left:4px solid #b45309; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#b45309; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#c2410c; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#b45309; }}
    .kpi .s {{ font-size:7.5pt; color:#c2410c; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>CBRL 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>CBRL 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Cracker Barrel · 홈스타일 레스토랑 + Old Country Store 리테일</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q3 FY'26 실적({EARN} 발표) · 시총 ~$1.3B · ${PX:.2f}</p>
  <div style="margin-top:22px">
    <span class="tag bad">Chase 하·과열</span>
    <span class="tag bad">PT 프리미엄 {UPSIDE*100:+.0f}%</span>
    <span class="tag warn">Traffic −6.7%</span>
    <span class="tag good">FY26 가이던스 상향</span>
    <span class="tag">GO_A · 본선 제외</span>
  </div>
  <div style="margin-top:28px">
    <div class="kpi"><div class="l">Q3 매출</div><div class="v">$797M</div><div class="s">YoY −2.9%</div></div>
    <div class="kpi"><div class="l">Rest / Retail</div><div class="v">83/17</div><div class="s">$658M / $139M</div></div>
    <div class="kpi"><div class="l">Adj EBITDA</div><div class="v">$40.3M</div><div class="s">YoY −16%</div></div>
    <div class="kpi"><div class="l">업사이드</div><div class="v">{UPSIDE*100:+.0f}%</div><div class="s">PT ${PT:.0f}</div></div>
  </div>
  <p class="small" style="margin-top:36px;max-width:540px;margin-left:auto;margin-right:auto">
    ~660개 회사 직영 매장(43개 주) + Maple Street Biscuit. 식사 ~83% · 선물리테일 ~17%.
    Q3는 트래픽 약세·가격으로 방어, Adj 이익은 줄었으나 FY26 가이던스 상향.
    GAAP 순이익은 카드수수료 소송합의 $47.4M이 부풀림 — Adj가 실체.
  </p>
</section>

<h2>0. 한줄 결론</h2>
<div class="box">
<b>구조는 “식당이 본체, 리테일이 차별” — 지금 주가는 PT·고점 대비 비싸다.</b>
Q3 FY'26 매출 $797M(−2.9%) · Rest Comp −2.6%(트래픽 −6.7% · 체크 +4.3%) ·
Retail Comp −1.8%(4년+ 만에 Rest보다 나음) · Adj EBITDA $40.3M(−16%) ·
Adj EPS $0.29 vs GAAP $1.90(소송합의). FY26 매출·EBITDA 가이던스 상향은 플러스.
포트: <b>미보유 · Chase 하·과열 · PT 업사이드 {UPSIDE*100:+.0f}%</b> —
심층 GO_A여도 본선(과열) 제외 · <b>추격·신규 비추</b>.
</div>

<h2>1. 비즈니스 구조</h2>
<div class="easy"><b>쉽게:</b> 크래커배럴은 고속도로 옆 <b>남부 홈스타일 식당</b>과
같은 건물 안 <b>선물·잡화 가게</b>를 함께 운영한다. 돈의 대부분 식사에서 나온다.</div>
{fig_block(charts['flow'], '수요 → 매장 → 식사/리테일 → Adj EBITDA')}
{gloss([
    ("Comparable store sales", "동일 매장 매출 증감. 신규점·폐쇄 효과 제외"),
    ("Traffic / Check", "방문객 수 vs 객단가. 가격↑로 체크는 오르고 방문은 줄 수 있음"),
    ("Off-premise", "포장·배달·케이터링. Q3 레스토랑 매출의 19.6%"),
    ("Maple Street Biscuit", "패스트캐주얼 비스킷 브랜드. CBRL 자회사"),
])}

{compete_html}

<h2>2. 매출·원가 (Q3 FY'26)</h2>
<div class="easy"><b>쉽게:</b> 손님이 줄었지만(트래픽 −6.7%) 메뉴 가격(+4.4%)으로
객단가를 올려 레스토랑 Comp −2.6%로 방어했다. 이익(Adj EBITDA)은 그래도 줄었다.</div>
{fig_block(charts['mix'], '레스토랑/리테일 믹스')}
{fig_block(charts['traffic'], '트래픽·체크 브리지')}
{fig_block(charts['cogs'], '원가율')}
<table>
  <tr><th>항목</th><th>Q3'26</th><th>Q3'25</th><th>메모</th></tr>
  <tr><td>Total revenue</td><td>$797.4M</td><td>$821.1M</td><td>−2.9%</td></tr>
  <tr><td>Restaurant</td><td>$658.4M (82.6%)</td><td>~82.7%</td><td>Comp −2.6%</td></tr>
  <tr><td>Retail</td><td>$139.0M (17.4%)</td><td>~17.3%</td><td>Comp −1.8%</td></tr>
  <tr><td>Rest COGS / Rest sales</td><td>26.1%</td><td>26.2%</td><td>가격 &gt; 원자재(+2.5%)</td></tr>
  <tr><td>Retail COGS / Retail</td><td>49.8%</td><td>48.9%</td><td>관세↑</td></tr>
  <tr><td>Operating income</td><td>$6.7M</td><td>$14.9M</td><td>−55%</td></tr>
  <tr><td>Litigation settlement</td><td>$47.4M</td><td>—</td><td>GAAP만 부풀림</td></tr>
  <tr><td>GAAP NI / EPS</td><td>$42.8M / $1.90</td><td>$12.6M / $0.56</td><td>일회성 포함</td></tr>
  <tr><td>Adj NI / EPS</td><td>$6.5M / $0.29</td><td>$13.1M / $0.58</td><td>실체</td></tr>
  <tr><td>Adj EBITDA</td><td>$40.3M (5.1%)</td><td>$48.1M</td><td>−16%</td></tr>
</table>
{gloss([
    ("Adj EBITDA", "감가·일회성 제외 영업현금 근사. FY26 가이던스 핵심 KPI"),
    ("Interchange settlement", "카드수수료 소송 합의. Q3 GAAP에 +$47.4M(수수료 차감 후)"),
])}

<h2>3. 가이던스 · 재무</h2>
{fig_block(charts['pnl'], '탑라인 vs GAAP/Adj')}
{fig_block(charts['guide'], 'FY26 가이던스 상향')}
<div class="easy"><b>쉽게:</b> 회사는 “올해 매출·Adj EBITDA를 더 높게 본다”고 올렸다.
운영·비용 절감이 먹히고 있다는 신호. 다만 <b>주가는 이미 PT($45) 위</b>다.</div>
<table>
  <tr><th>지표</th><th>이전</th><th>상향 후</th></tr>
  <tr><td>FY26 Total revenue</td><td>$3.24–3.27B</td><td>$3.27–3.30B</td></tr>
  <tr><td>FY26 Adj EBITDA</td><td>$85–100M</td><td>$120–125M</td></tr>
  <tr><td>Commodity inflation</td><td>2.0–2.5%</td><td>low 2%</td></tr>
  <tr><td>Hourly wage inflation</td><td>2.5–3.0%</td><td>low 2%</td></tr>
  <tr><td>Capex</td><td>$105–115M</td><td>동일</td></tr>
  <tr><td>신규점</td><td>2개</td><td>둘 다 오픈 완료</td></tr>
</table>
<table>
  <tr><th>자본·BS (Q3말)</th><th>내용</th></tr>
  <tr><td>총부채</td><td>$486.6M (0.625% CN $149.9M 단기 + 1.75% CN $336.8M)</td></tr>
  <tr><td>RCF</td><td>인출 0 · 가용 ~$541M · 단기 CN은 RCF로 상환 예정(06/26)</td></tr>
  <tr><td>배당</td><td>$0.25/주 · 지급 08-12 · 기준 07-17</td></tr>
</table>

<h2>4. 시나리오 · 촉매</h2>
{fig_block(charts['scen'], '주가 시나리오 밴드')}
{fig_block(charts['cat'], '촉매 카드')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$28–40</td><td>트래픽 재악화 · 가이던스 컷 · 리테일 관세·재고</td></tr>
  <tr><td>Base</td><td>$42–52</td><td>가이던스 달성 · 트래픽 점진 개선 · PT 수렴</td></tr>
  <tr><td>Bull</td><td>$55–68</td><td>트래픽 턴 · 마진 가속 · 52주 고점 돌파 유지</td></tr>
</table>

<h2>5. 포트 실행</h2>
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (8/25 심층)</b><br/>
미보유 · Chase <b>하·과열</b> · 타이밍 GO_A였으나 <b>본선 제외</b> → 저녁창 실행 없음.<br/>
현재 ${PX:.2f} · PT ${PT:.2f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}–${H52:.2f} · 고점 −8.1%.<br/>
실행: <b>추격·신규 금지</b> · 관망. 재검토는 트래픽 개선 + PT 수렴(또는 뚜렷한 눌림) 후.<br/>
현금바닥 $150 · 보유 7종 NO_ADD 유지 · CBRL은 워치만.
</div>

<p class="small">생성: 수익구조분석() · 티커 CBRL · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart<br/>
출처: Cracker Barrel Q3 FY2026 earnings release (2026-06-09, PR Newswire) · yfinance · 피어 점유/믹스는 방향 비교용 추정</p>
</body></html>
"""


def main() -> int:
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "traffic": chart_traffic_bridge(),
        "pnl": chart_pnl_quality(),
        "guide": chart_guide(),
        "scen": chart_scenarios(),
        "cat": chart_catalysts(),
        "pos": chart_position(),
        "cogs": chart_cogs(),
    }
    bundle, cpaths = build_compete_charts("CBRL", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("CBRL", CHART_DIR, html_doc)
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

        tag = "sepa-rev-cbrl"
        notes = (
            f"## CBRL 수익구조분석 ({ASOF})\n\n"
            f"Cracker Barrel · Q3 FY'26 · Rest 83% / Retail 17% · FY26 가이던스 상향.\n\n"
            f"- Chase 하·과열 · PT 업사이드 {UPSIDE*100:+.1f}% (PT ${PT:.0f} · px ${PX:.2f})\n"
            f"- GO_A였으나 본선 제외 · 추격·신규 금지 · 관망\n"
            f"- Adj EBITDA $40.3M · GAAP는 소송합의 $47.4M 포함\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — CBRL",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
