#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(ECPG) — NPL 채무매입·회수 + 경쟁점유/믹스 + WeasyPrint PDF."""

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
PX = 94.08
PT = 113.33
H52 = 98.02
UPSIDE = PT / PX - 1.0
EARN = "08-05"
OUT_PDF = [
    Path("/opt/cursor/artifacts/ECPG_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/ECPG_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/ECPG_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/ECPG_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/ecpg")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "navy": "#1e3a5f",
    "navy2": "#2c5282",
    "teal": "#0d5c4d",
    "teal2": "#1a7a66",
    "gold": "#b8860b",
    "sand": "#e8dcc8",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "slate": "#334155",
    "light": "#eef2f7",
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
        (0.15, 0.65, 1.7, 1.55, "은행·카드\n연체·상각\n(NPL)", C["sand"]),
        (2.05, 0.65, 1.8, 1.55, "포트폴리오\n매입\n$363M", C["navy2"]),
        (4.05, 0.65, 1.85, 1.55, "회수\nCollections\n$718M", C["teal2"]),
        (6.1, 0.65, 1.75, 1.55, "ERC\n저수지\n$9.83B", C["teal"]),
        (8.1, 0.65, 1.65, 1.55, "매출·EPS\n$475M\n$3.86", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                facecolor=c, edgecolor="white", lw=2,
            )
        )
        tc = C["ink"] if c in (C["sand"],) else "white"
        ax.text(
            x + w / 2, y + h / 2, t, ha="center", va="center",
            fontproperties=PROP_B, fontsize=8.5, color=tc,
        )
    ax.set_title(
        "비즈니스 한눈에 — NPL 매입 → 회수 → ERC → 매출·이익",
        fontproperties=PROP_B, fontsize=12, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_revenue_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    # Debt purchasing = Portfolio $390 + Changes $62.7 = $452.8 (~95%)
    sizes = [452.8, 20.6, 2.0]
    labels = [
        "채무매입\n452.8M (95%)",
        "서비싱\n20.6M (4%)",
        "기타\n2.0M (1%)",
    ]
    ax.pie(
        sizes, labels=labels, colors=[C["navy"], C["teal"], C["gold"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("매출 믹스 (Q1'26, 총 $475.4M)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    cats = ["포트폴리오\n수익", "회수추정\n변동", "서비싱", "기타"]
    vals = [390.0, 62.7, 20.6, 2.0]
    colors = [C["navy"], C["navy2"], C["teal"], C["gold"]]
    for i, (v, c) in enumerate(zip(vals, colors)):
        ax.bar(i, v, color=c, width=0.55)
        ax.text(i, v + 8, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_xticks(list(range(len(cats))))
    ax.set_xticklabels(cats, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("매출 세부 바 (Q1'26)", fontproperties=PROP_B, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("ECPG 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_mix.png")


def chart_collections_bridge() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))

    ax = axes[0]
    labels = ["Q1'25", "Q1'26"]
    coll = [605, 718.4]
    purch = [368, 363]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], purch, w, label="매입", color=C["sand"])
    ax.bar([i + w / 2 for i in x], coll, w, label="회수", color=C["navy"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("매입 vs 회수 (기록 회수)", fontproperties=PROP_B, fontsize=11)
    ax.legend(prop=PROP, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(1 + w / 2, 718.4 + 18, "+19%", ha="center", fontproperties=PROP, fontsize=8, color=C["teal"])

    ax = axes[1]
    geo_labels = ["MCM(US)\n회수", "유럽\n(Cabot)", "글로벌\n합계"]
    geo_vals = [556, 162.4, 718.4]
    geo_colors = [C["navy"], C["teal2"], C["teal"]]
    for i, (v, c) in enumerate(zip(geo_vals, geo_colors)):
        ax.bar(i, v, color=c, width=0.55)
        ax.text(i, v + 12, f"{v:.0f}", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_xticks(list(range(len(geo_labels))))
    ax.set_xticklabels(geo_labels, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("회수 브리지 — US ~$556M (+23%)", fontproperties=PROP_B, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("운영 엔진 — 싸게 사서, 오래 회수한다", fontproperties=PROP_B, fontsize=12, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "03_collections_bridge.png")


def chart_growth_guide() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.7))

    ax = axes[0]
    metrics = ["ERC\n($B)", "평균\n포트($B)", "매입\nQ1($M)"]
    vals = [9.83, 4.40, 0.363]
    # normalize display: ERC/avg as billions, purchases as B
    display = [9.83, 4.40, 0.36]
    colors = [C["navy"], C["teal"], C["gold"]]
    for i, (v, c) in enumerate(zip(display, colors)):
        ax.bar(i, v, color=c, width=0.55)
        labels_v = ["$9.83B", "$4.40B", "$363M"]
        ax.text(i, v + 0.15, labels_v[i], ha="center", fontproperties=PROP, fontsize=8)
    ax.set_xticks(list(range(len(metrics))))
    ax.set_xticklabels(metrics, fontproperties=PROP, fontsize=8)
    ax.set_title("저수지 · 포트 · 매입 (Q1'26)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylim(0, 12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    guide_labels = ["회수\nFY26", "EPS\nFY26", "매입\nFY26"]
    # collections 2.8B, EPS 13, purchases ~1.45B midpoint
    g_vals = [2.8, 1.3, 1.45]  # EPS scaled /10 for visual
    g_colors = [C["navy"], C["teal"], C["gold"]]
    for i, (v, c) in enumerate(zip(g_vals, g_colors)):
        ax.bar(i, v, color=c, width=0.55)
    ax.text(0, 2.8 + 0.08, "~$2.8B\n(+8%)", ha="center", fontproperties=PROP, fontsize=8)
    ax.text(1, 1.3 + 0.08, "$13.00\n(+19%)", ha="center", fontproperties=PROP, fontsize=8)
    ax.text(2, 1.45 + 0.08, "$1.4–1.5B", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_xticks(list(range(len(guide_labels))))
    ax.set_xticklabels(guide_labels, fontproperties=PROP, fontsize=8)
    ax.set_title("FY26 가이던스 (상향 후)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylim(0, 3.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.suptitle("성장 · 가이던스 — ERC +11% · EPS 가이던스 $13", fontproperties=PROP_B, fontsize=12, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "04_growth_guide.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26"]
    rev = [393, 442, 460, 474, 475.4]
    oi = [129, 151, 173, 173, 184]
    x = range(len(labels))
    ax.bar(x, rev, color=C["navy"], alpha=0.85, label="매출 ($M)", width=0.55)
    ax2 = ax.twinx()
    ax2.plot(x, oi, "o-", color=C["gold"], lw=2.2, ms=8, label="영업이익 ($M)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("매출 ($M)", fontproperties=PROP, color=C["navy"])
    ax2.set_ylabel("영업이익 ($M)", fontproperties=PROP, color=C["gold"])
    ax.set_title("분기 추이 — Q1'26 매출 $475M (+21% YoY)", fontproperties=PROP_B, fontsize=12)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    return save_fig(fig, "05_quarterly.png")


def chart_eps_ni() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["Q1'25", "Q1'26"]
    eps = [1.93, 3.86]
    ni = [43, 86.2]
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], eps, w, label="EPS ($)", color=C["navy"])
    ax2 = ax.twinx()
    ax2.bar([i + w / 2 for i in x], ni, w, label="NI ($M)", color=C["teal"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("EPS (USD)", fontproperties=PROP, color=C["navy"])
    ax2.set_ylabel("순이익 ($M)", fontproperties=PROP, color=C["teal"])
    ax.set_title("순이익·EPS — Q1'26 EPS $3.86 (+100%)", fontproperties=PROP_B, fontsize=12)
    ax.text(1 - w / 2, 3.86 + 0.08, "+100%", ha="center", fontproperties=PROP, fontsize=8, color=C["green"])
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    return save_fig(fig, "06_eps_ni.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 70, 85, C["red"]),
        ("Base", 100, 118, C["teal"]),
        ("Bull", 120, 140, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text(
            (lo + hi) / 2, i, f"{name} ${lo}–{hi}", ha="center", va="center",
            fontproperties=PROP_B, fontsize=10, color="white",
        )
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"현재 ${PX:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT평균 ${PT:.0f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 — 회수·ERC·매입 IRP가 밴드폭", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(60, 150)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, EARN, "실적", "회수·ERC\n가이던스", C["navy"]),
        (0.28, "FY26", "가이드", "회수~$2.8B\nEPS $13", C["teal"]),
        (0.52, "매입", "공급", "US IRP\n$1.4–1.5B", C["gold"]),
        (0.76, "규제", "리스크", "회수채널\n조달금리", C["red"]),
    ]
    for x, tag, title, body, c in items:
        ax.add_patch(
            FancyBboxPatch(
                (x, 0.25), 0.2, 0.55, boxstyle="round,pad=0.02,rounding_size=0.04",
                facecolor=c, edgecolor="white", lw=1.5, transform=ax.transAxes,
            )
        )
        ax.text(
            x + 0.1, 0.68, tag, ha="center", transform=ax.transAxes,
            fontproperties=PROP_B, fontsize=9, color="white",
        )
        ax.text(
            x + 0.1, 0.55, title, ha="center", transform=ax.transAxes,
            fontproperties=PROP_B, fontsize=10, color="white",
        )
        ax.text(
            x + 0.1, 0.38, body, ha="center", transform=ax.transAxes,
            fontproperties=PROP, fontsize=7.5, color="white",
        )
    ax.set_title(
        f"촉매 — {EARN} 실적(EARN_D5) · FY26 가이던스 · 매입·규제",
        fontproperties=PROP_B, fontsize=12, pad=8,
    )
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "CORE 홀드\nChase 최상", C["navy"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "추가금지\n(no_add)", C["teal"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", f"EARN_D5 {EARN}\n소화 후 재평가", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "고점권·실적창 · 조달금리 · 규제·회수비용", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "회수기록 · ERC↑ · EPS+100% · PT업사이드", C["navy2"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor=c, edgecolor="white", lw=1.5,
            )
        )
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(
            x + w / 2, y + 0.35, body, ha="center", va="center",
            fontproperties=PROP, fontsize=8.5, color="white",
        )
    ax.set_title(
        "실행 포지션 맵 — CORE · 보유 · 추가금지 (Chase 최상)",
        fontproperties=PROP_B, fontsize=12, pad=4,
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
<div class="easy"><b>쉽게:</b> ECPG는 <b>미국 NPL 매입·회수</b>의 상장 대표주(MCM)다.
PRAA와 같은 공개 피어, 사모·지역 매입사와 경매에서 싸운다. 절대 전체 신용시장 점유가 아님.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> ECPG 매출의 약 <b>95%가 채무매입(포트폴리오+회수추정변동)</b>이고
서비싱은 ~4%에 불과하다. PRAA도 채무매입 중심 — 차별점은 미국 스케일·회수 효율·ERC다.</div>
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
      @bottom-center {{ content:"ECPG 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #2c5282; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0d5c4d; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#eef2f7 0%,#e6f2ef 55%,#d4e4f0 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#dbeafe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecdd3; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#1e3a5f; color:#fff; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#eef6f3; border-left:4px solid #0d5c4d; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0d5c4d; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#0d5c4d; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>ECPG 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>ECPG 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Encore Capital Group · 부실채권(NPL) 매입·회수 전문 금융</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1'26 실적 · 다음 실적 {EARN} · 시총 ~$2.1B</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.2f}</div><div class="s">52주고 ${H52:.2f}</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.0f}</div><div class="s">{UPSIDE*100:+.1f}%</div></span>
    <span class="kpi"><div class="l">Q1 매출</div><div class="v">$475.4M</div><div class="s">+21% YoY</div></span>
    <span class="kpi"><div class="l">회수</div><div class="v">$718.4M</div><div class="s">+19% · 기록</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">CORE · Chase 최상 · 보유</span>
    <span class="tag warn">추가금지 (no_add)</span>
    <span class="tag warn">실적 EARN_D5 {EARN}</span>
    <span class="tag">채무매입 ~95%</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>미국 NPL 채무매입·회수 — 포트폴리오 수익이 매출의 ~95%.</b>
Q1'26 매출 <b>$475.4M</b>(+21% YoY) · 회수 <b>$718.4M</b>(+19%, 기록) · MCM(US) ~$556M(+23%).
ERC <b>$9.83B</b>(+11%) · NI $86.2M · EPS <b>$3.86</b>(+100%).
FY26 가이드: 회수 ~$2.8B(+8%) · EPS $13.00(+19%) · 매입 $1.4–1.5B.
주가 ~${PX:.1f} vs PT ${PT:.0f}({UPSIDE*100:+.0f}%) — 계좌는 <b>CORE 홀드 · 추가금지</b>, {EARN} 실적 소화가 우선.</p>
{fig_block(charts['01'], '비즈니스 플로우 — NPL 매입 → 회수 → ERC')}
<div class="easy"><b>쉽게:</b> 은행·카드사가 포기한 연체 빚을 <b>싸게 사서</b>,
수년에 걸쳐 소비자에게 회수한다. 장부 “매출”과 통장 “회수 현금”은 같은 숫자가 아니다.
이미 산 포트폴리오(ERC 저수지)에서 매년 물을 빼는 구조다.</div>
{gloss([
    ("NPL", "Non-Performing Loan — 부실·연체 채권. 은행이 할인 매각하기도 함."),
    ("Collections", "실제로 거둬들인 현금 회수. 투자자가 가장 먼저 보는 운영 숫자."),
    ("ERC", "Estimated Remaining Collections — 앞으로 받을 것으로 보는 ‘남은 저수지’."),
    ("MCM", "Midland Credit Management — Encore의 미국 회수 브랜드."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '매출 믹스 파이 + 바')}
{fig_block(charts['03'], '회수 브리지')}
<table>
  <tr><th>항목 (Q1'26)</th><th>금액</th><th>비중</th><th>내용</th></tr>
  <tr><td>포트폴리오 수익</td><td>$390.0M</td><td>~82%</td><td>매입 채권 기본 회계 수익</td></tr>
  <tr><td>Changes in recoveries</td><td>$62.7M</td><td>~13%</td><td>회수 전망 재추정</td></tr>
  <tr><td><b>채무매입 합</b></td><td><b>$452.8M</b></td><td><b>~95%</b></td><td>핵심 엔진</td></tr>
  <tr><td>서비싱</td><td>$20.6M</td><td>~4%</td><td>타인 채권 대행 수수료</td></tr>
  <tr><td>기타</td><td>$2.0M</td><td>~1%</td><td>소량</td></tr>
  <tr><td><b>총 매출</b></td><td><b>$475.4M</b></td><td>100%</td><td>+21% YoY</td></tr>
</table>
<table>
  <tr><th>운영 지표</th><th>Q1'26</th><th>변화</th><th>의미</th></tr>
  <tr><td>글로벌 회수</td><td>$718.4M</td><td>+19%</td><td>기록 분기</td></tr>
  <tr><td>MCM(US) 회수</td><td>~$556M</td><td>+23%</td><td>회수의 ~77%</td></tr>
  <tr><td>포트폴리오 매입</td><td>$363M</td><td>~flat</td><td>매입 유지·회수 가속</td></tr>
  <tr><td>ERC</td><td>$9.83B</td><td>+11%</td><td>저수지 확대</td></tr>
  <tr><td>평균 수취채권 포트</td><td>$4.40B</td><td>—</td><td>운용 규모</td></tr>
  <tr><td>NI / EPS</td><td>$86.2M / $3.86</td><td>EPS +100%</td><td>이익 급증</td></tr>
</table>
<div class="easy"><b>쉽게:</b> 돈의 <b>거의 전부 ‘산 빚에서 나오는 수익’</b>이다.
서비싱은 부업 수준. Q1은 매입이 비슷한데 회수·EPS가 뛴 분기 — 이미 보유한 포트에서 효율이 나온 것.</div>
{gloss([
    ("포트폴리오 수익", "매입 원가·예상 회수를 바탕으로 인식하는 회계 수익. 당기 회수와 1:1 아님."),
    ("Changes in recoveries", "앞으로의 회수 전망을 올려/내려 잡을 때 당기 손익에 반영."),
    ("서비싱", "남의 채권을 대신 관리·회수하고 수수료를 받는 사업."),
    ("Cabot", "Encore의 유럽 사업 축."),
])}

{compete_html}

<h2>2. 성장 · 가이던스</h2>
{fig_block(charts['04'], 'ERC·포트·FY26 가이드')}
{fig_block(charts['05'], '분기 매출·영업이익')}
{fig_block(charts['06'], '순이익·EPS')}
<ul>
  <li>FY26 가이드: 회수 <b>~$2.8B</b>(+8%) · EPS <b>$13.00</b>(+19%) · 매입 <b>$1.4–1.5B</b></li>
  <li>Q1'26: 회수 기록 · ERC +11% · 미국 매입 환경 유리(경영진 톤)</li>
  <li>레버리지 업종 — 이자·조달금리가 마진을 깎음. FY25부터 이익 회복 뚜렷</li>
  <li>차기 실적 <b>{EARN}</b> — Beat보다 회수 페이스·ERC·가이던스 톤이 핵심</li>
</ul>
<div class="easy"><b>쉽게:</b> 성장은 “올해 얼마나 싸게 더 사느냐”와
“이미 산 저수지에서 얼마나 잘 빼느냐” 두 축이다. 가이던스 $13 EPS는 후자(운영)가 받쳐 주는 그림.</div>
{gloss([
    ("IRP", "매입 건 기대 수익률. 싸게 살수록(같은 회수 가정) ↑."),
    ("가이던스", "회사가 제시하는 연간 목표 범위."),
    ("조달금리", "채권 매입 자금을 빌릴 때 이자율."),
])}

<h2>3. 시나리오 · 포트</h2>
{fig_block(charts['07'], '주가 시나리오')}
{fig_block(charts['08'], '촉매')}
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>120–140</td><td>회수·ERC 추가 상향 · IRP 유지 · 레버리지 개선</td></tr>
  <tr><td>Base</td><td>100–118</td><td>FY26 가이드 달성(회수~$2.8B, EPS~$13) · PT 밴드</td></tr>
  <tr><td>Bear</td><td>70–85</td><td>회수 둔화 · ERC 하향 · 매입 경쟁·규제·금리 악화</td></tr>
</table>
<div class="box">
<b>계좌 기준 실행</b><br/>
· 역할: <b>CORE 홀드</b> · Chase <b>최상</b> · <b>보유 · 추가금지(no_add)</b><br/>
· 가격: ~${PX:.1f} · PT ~${PT:.0f}({UPSIDE*100:+.0f}%) · 52주고 ${H52:.1f} 근접 — 추격 애드 비추<br/>
· 트리거: <b>EARN_D5 {EARN}</b>에서 회수·ERC·FY 가이드 확인 후 재평가<br/>
· Breaker: 회수 페이스 붕괴 · ERC 연속 하향 · IRP 구조 악화 · 대형 규제·조달 충격
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>미국 NPL 매입·회수 엔진</u>으로 건강하고 가시성이 높다.
다만 <b>고점권·실적창</b>이므로 코어 유지·추가금지·{EARN} 소화가 맞고, 지금 추격은 비추.</div>

<h2>부록 · 출처</h2>
<p class="small">
Encore Capital Q1 2026 earnings / IR · yfinance 가격·PT·실적일 ({ASOF}).
피어 믹스·점유는 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 ECPG · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_revenue_mix(),
        "03": chart_collections_bridge(),
        "04": chart_growth_guide(),
        "05": chart_quarterly(),
        "06": chart_eps_ni(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("ECPG", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html = build_html(charts, compete_html=compete_html)
    html, _px = build_and_insert_price("ECPG", CHART_DIR, html)
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
    print(f"ECPG rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% earn={EARN} compete={bundle is not None}")


if __name__ == "__main__":
    main()
