#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(LASR) — nLIGHT 고출력 레이저 A&D/Industrial/Micro + 경쟁점유/믹스 + WeasyPrint PDF."""

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
PX = 68.8
PT = 90.71
H52 = 86.95
UPSIDE = PT / PX - 1.0
EARN = "08-06"
OUT_PDF = [
    Path("/opt/cursor/artifacts/LASR_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/LASR_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/LASR_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/LASR_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/lasr")
CHART_DIR.mkdir(parents=True, exist_ok=True)

fm.fontManager.addfont(FONT_REG)
fm.fontManager.addfont(FONT_BOLD)
PROP = fm.FontProperties(fname=FONT_REG)
PROP_B = fm.FontProperties(fname=FONT_BOLD)
plt.rcParams["font.family"] = PROP.get_name()
plt.rcParams["axes.unicode_minus"] = False

C = {
    "slate": "#334155",
    "slate2": "#475569",
    "teal": "#0f766e",
    "teal2": "#14b8a6",
    "navy": "#1e3a5f",
    "sand": "#e2e8f0",
    "ink": "#1c1917",
    "muted": "#57534e",
    "red": "#9f1239",
    "green": "#166534",
    "gold": "#b8860b",
    "def_": "#0e7490",
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
        (0.15, 0.65, 1.7, 1.55, "반도체·광섬유\n레이저 IP", C["sand"]),
        (2.05, 0.65, 1.8, 1.55, "Products\n양산 레이저", C["teal2"]),
        (4.05, 0.65, 1.85, 1.55, "Advanced\nDevelopment", C["def_"]),
        (6.1, 0.65, 1.75, 1.55, "A&D · Industrial\n· Microfab", C["teal"]),
        (8.1, 0.65, 1.65, 1.55, "매출\n·마진", C["slate"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                           facecolor=c, edgecolor="white", lw=2)
        )
        tc = C["ink"] if c in (C["sand"], C["teal2"]) else "white"
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontproperties=PROP_B, fontsize=8.5, color=tc)
    ax.set_title("비즈니스 한눈에 — 고출력 레이저를 국방·제조·정밀가공에 판다",
                 fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [55.1, 12.0, 13.0]
    labels = ["A&D\n55.1M (69%)", "Industrial\n12.0M (15%)", "Microfab\n13.0M (16%)"]
    ax.pie(
        sizes, labels=labels, colors=[C["def_"], C["teal"], C["slate2"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.5),
    )
    ax.set_title("최종시장 매출 (Q1'26, 총 80.2M USD)", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    sizes = [58.2, 22.0]
    labels = ["Products\n58.2M (73%)", "Adv. Dev\n~22M (27%)"]
    ax.pie(
        sizes, labels=labels, colors=[C["teal"], C["navy"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=9),
    )
    ax.set_title("보고 세그먼트 (Q1'26)", fontproperties=PROP_B, fontsize=11)
    fig.suptitle("LASR 수익 구조 — 어디서 돈이 오나", fontproperties=PROP_B, fontsize=13, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_ad_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    cats = ["전사\n매출", "A&D\n합계", "A&D\nProducts", "Development", "Industrial", "Microfab"]
    vals = [80.2, 55.1, 33.1, 22.0, 12.0, 13.0]
    colors = [C["slate"], C["def_"], C["teal"], C["navy"], C["teal2"], C["slate2"]]
    for i, (v, c) in enumerate(zip(vals, colors)):
        ax.bar(i, v, color=c, width=0.55)
        ax.text(i, v + 1.5, f"{v}", ha="center", fontproperties=PROP, fontsize=8)
    notes = ["+55%", "+69%", "+98%", "+38%", "+36%", "+29%"]
    for i, n in enumerate(notes):
        ax.text(i, -6, n, ha="center", fontproperties=PROP, fontsize=7.5, color=C["muted"])
    ax.set_xticks(list(range(len(cats))))
    ax.set_xticklabels(cats, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("백만 USD", fontproperties=PROP)
    ax.set_title("Q1'26 최종시장·A&D 제품 브리지", fontproperties=PROP_B, fontsize=12)
    ax.set_ylim(-10, 95)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return save_fig(fig, "03_ad_bridge.png")


def chart_tam_funnel() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    layers = [
        (9.2, 8.3, "TAM — 고출력 레이저", "Directed Energy · Sensing · 제조·정밀가공", C["sand"]),
        (7.6, 6.2, "SAM — 미 국방·프라임 + 상용", "DE 프로그램 · 산업/마이크로팹", C["slate2"]),
        (5.8, 4.1, "SOM — nLIGHT ~0.3B+", "FY25 ~261M · Q1'26 런레이트 상승", C["teal2"]),
        (4.2, 2.0, "성장 스토리", "A&D Products 양산 · DE follow-on", C["teal"]),
    ]
    for w, y, title, sub, c in layers:
        x0 = (10 - w) / 2
        ax.add_patch(
            FancyBboxPatch(
                (x0, y - 0.85), w, 1.55, boxstyle="round,pad=0.02,rounding_size=0.15",
                facecolor=c, edgecolor="white", linewidth=2, alpha=0.92,
            )
        )
        tc = "white" if c in (C["teal"], C["teal2"], C["slate"], C["slate2"], C["navy"], C["def_"]) else C["ink"]
        ax.text(5, y + 0.25, title, ha="center", va="center", fontproperties=PROP_B, fontsize=11, color=tc)
        ax.text(5, y - 0.35, sub, ha="center", va="center", fontproperties=PROP, fontsize=8.2, color=tc)
    ax.set_title("시장 깔때기 — 국방 DE/센싱이 nLIGHT의 자리", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "04_tam_funnel.png")


def chart_quarterly() -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    labels = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26", "Q2'26g"]
    rev = [51.7, 61.7, 66.7, 81.2, 80.2, 78.0]
    gm = [26.7, 28.0, 30.0, 32.0, 33.1, 31.0]
    x = range(len(labels))
    colors = [C["slate"]] * 4 + [C["teal"], C["teal2"]]
    ax.bar(x, rev, color=colors, alpha=0.9, label="매출 (M USD)", width=0.55)
    ax2 = ax.twinx()
    ax2.plot(x[:5], gm[:5], "o-", color=C["gold"], lw=2.2, ms=8, label="GM (%)")
    ax2.plot([5], [gm[5]], "s", color=C["gold"], ms=8, alpha=0.7)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontproperties=PROP)
    ax.set_ylabel("매출 (M USD)", fontproperties=PROP, color=C["teal"])
    ax2.set_ylabel("Gross Margin (%)", fontproperties=PROP, color=C["gold"])
    ax.set_title("분기 추이 — Q1'26 80.2M(+55%) · Q2 가이드 mid 78", fontproperties=PROP_B, fontsize=12)
    ax.errorbar(5, 78, yerr=3, fmt="none", ecolor=C["def_"], capsize=4, lw=1.2)
    lines, labs = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labs + labs2, prop=PROP, frameon=False, loc="upper left")
    ax.spines["top"].set_visible(False)
    ax.set_ylim(0, 100)
    ax2.set_ylim(20, 40)
    return save_fig(fig, "05_quarterly.png")


def chart_margin_guide() -> Path:
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    labels = ["Q1'25\nGM", "Q1'26\nGM", "Q2'26g\nGM mid", "Q2'26g\nAdj EBITDA"]
    vals = [26.7, 33.1, 31.0, 10.0]
    colors = [C["slate2"], C["teal"], C["teal2"], C["def_"]]
    for i, (v, c) in enumerate(zip(vals, colors)):
        ax.bar(i, v, color=c, width=0.5)
        unit = "%" if i < 3 else "M"
        ax.text(i, v + 0.8, f"{v}{unit}" if i < 3 else f"{v:.0f}M mid",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.axhspan(29, 33, xmin=0.55, xmax=0.78, alpha=0.15, color=C["teal"])
    ax.set_xticks(list(range(len(labels))))
    ax.set_xticklabels(labels, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("GM % / EBITDA M USD", fontproperties=PROP)
    ax.set_title("마진 궤적 — GM 33.1%(vs 26.7%) · Q2 GM 29–33%", fontproperties=PROP_B, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylim(0, 42)
    return save_fig(fig, "06_margin_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 40, 55, C["red"]),
        ("Base", 65, 95, C["teal"]),
        ("Bull", 95, 125, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} {lo}–{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"현재 {PX:.1f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(H52, color=C["slate2"], lw=1.0, ls="-.")
    ax.text(H52, 2.15, f"52주고 {H52:.1f}", ha="center", fontproperties=PROP, fontsize=7.5, color=C["slate2"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT평균 {PT:.1f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 (USD)", fontproperties=PROP)
    ax.set_title("시나리오 — A&D 양산·DE 실행이 밴드폭", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(30, 135)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, EARN, "실적", "Q2 매출·GM\nProducts 믹스", C["teal"]),
        (0.28, "A&D", "성장", "Products +98%\nDE follow-on", C["def_"]),
        (0.52, "가이드", "가시성", "Q2 75–81M\nEBITDA 8–12M", C["navy"]),
        (0.76, "고점", "리스크", f"52주고 {H52:.0f}\n추격 금지", C["red"]),
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
    ax.set_title(f"촉매 — {EARN} 실적창 · A&D 양산 · 고점 추격 금지",
                 fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "보유·추격금지\n실적창", C["teal"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "LASR ×2주\nmigration core\nphase1", C["navy"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", f"EARN_D5 {EARN}\n소화 후 재평가", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "고점 부근 추격 금지 · invalidation 관찰 · 고객집중", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "A&D 69% · GM↑ · PT 업사이드", C["slate"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.35, body, ha="center", va="center",
                fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title("실행 포지션 맵 (사용자 계좌 · LASR×2 보유 · 추격금지)", fontproperties=PROP_B, fontsize=12, pad=4)
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
<div class="easy"><b>쉽게:</b> LASR(nLIGHT)은 <b>고출력 레이저</b>에서 COHR/IPGP 대비 스케일은 작지만,
<b>Aerospace &amp; Defense 편중(69%)</b>이 차별축이다. 절대 글로벌 점유가 아님.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> LASR은 매출의 약 <b>69%가 A&amp;D</b>, Industrial·Micro는 각각 ~15–16%.
IPGP는 산업 편중, COHR은 혼합, LITE는 통신·옵토 성격이 강하다.</div>
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
      @bottom-center {{ content:"LASR 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0f766e; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #14b8a6; padding-bottom:3px; color:#0f766e; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#334155; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#f0fdfa 0%,#e2e8f0 55%,#ccfbf1 100%);
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
    .kpi .s {{ font-size:7.5pt; color:#334155; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>LASR 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>LASR 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">nLIGHT · 고출력 반도체·광섬유 레이저 · Aerospace &amp; Defense</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1'26 실적 · 다음 실적 {EARN} · 시총 ~$3.5B+</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~${PX:.1f}</div><div class="s">52주고 ${H52:.2f}</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~${PT:.1f}</div><div class="s">{UPSIDE*100:+.1f}%</div></span>
    <span class="kpi"><div class="l">Q1 매출</div><div class="v">$80.2M</div><div class="s">+55% YoY</div></span>
    <span class="kpi"><div class="l">Gross Margin</div><div class="v">33.1%</div><div class="s">vs 26.7%</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag good">보유 · 추격금지 · 실적창</span>
    <span class="tag">A&amp;D ~69%</span>
    <span class="tag warn">EARN_D5 {EARN}</span>
    <span class="tag warn">고점 부근</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>방산 Directed Energy·레이저 센싱으로 다시 그린 고출력 레이저 회사.</b>
Q1'26 매출 <b>$80.2M</b>(+55% YoY) · A&amp;D <b>$55.1M (69%, +69%)</b> · A&amp;D Products 기록 <b>$33.1M (+98%)</b>.
GM <b>33.1%</b>(vs 26.7%). Q2 가이드 매출 $75–81M(mid $78: Products ~$58 / Adv Dev ~$20), GM 29–33%, Adj EBITDA $8–12M.
주가 ~${PX:.1f} vs PT ${PT:.1f}({UPSIDE*100:+.0f}%) · 52주고 ${H52:.1f} — 당신 계좌는 <b>LASR×2 보유</b>(migration core phase1),
<b>추격 추가 금지</b>, invalidation 관찰 · <b>{EARN}</b> 실적창.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 반도체·광섬유로 ‘강한 레이저’를 만들어
국방(A&amp;D)·공장(Industrial)·정밀가공(Micro)에 판다. 지금은 <b>국방이 엔진</b>.</div>
{gloss([
    ("Directed Energy (DE)", "고에너지 레이저로 위협을 요격·무력화하는 국방 응용."),
    ("Fiber / Semiconductor laser", "광섬유·반도체 기반 고출력 레이저 광원."),
    ("Products vs Development", "양산 제품 매출 vs 국방 R&D·프로토타입 계약 매출."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '최종시장·세그먼트 믹스')}
{fig_block(charts['03'], 'A&D·최종시장 브리지')}
<table>
  <tr><th>최종시장 (Q1'26)</th><th>매출</th><th>비중</th><th>YoY</th></tr>
  <tr><td><b>Aerospace &amp; Defense</b></td><td>$55.1M</td><td>69%</td><td>+69%</td></tr>
  <tr><td>Industrial</td><td>$12.0M</td><td>15%</td><td>+36%</td></tr>
  <tr><td>Microfabrication</td><td>$13.0M</td><td>16%</td><td>+29%</td></tr>
  <tr><td><b>합계</b></td><td><b>$80.2M</b></td><td>100%</td><td><b>+55%</b></td></tr>
</table>
<table>
  <tr><th>보고 세그먼트 / A&amp;D 분해</th><th>매출</th><th>YoY</th><th>내용</th></tr>
  <tr><td>Laser Products (전사)</td><td>~$58.2M</td><td>—</td><td>양산 레이저 · 마진 엔진</td></tr>
  <tr><td>&nbsp;&nbsp;└ A&amp;D Products</td><td><b>$33.1M</b></td><td><b>+98%</b></td><td>기록 · 성장 핵심</td></tr>
  <tr><td>Advanced Development</td><td>~$22M</td><td>+38%</td><td>DE·센싱 R&amp;D 계약 · 낮은 마진</td></tr>
</table>
<p class="small">전사 GM 33.1%(vs 26.7%). Top10 고객 집중·국방 프라임 의존 리스크 존재.</p>
<div class="easy"><b>쉽게:</b> 돈의 대부분은 <b>국방</b>에서 나오고, 그중에서도
<b>양산 제품(A&amp;D Products)</b>이 마진·성장의 질을 가른다. 개발 계약만 늘면 마진이 얇아진다.</div>
{gloss([
    ("Microfabrication", "전자·의료·정밀 가공용 미세 레이저."),
    ("Industrial", "절삭·용접·적층제조(additive) 등 상용 제조."),
    ("고객 집중", "국방 프라임·정부 편중 — Top 고객 발주 공백 리스크."),
])}

{compete_html}

<h2>2. 성장 · 분기 궤적</h2>
{fig_block(charts['04'], '시장 깔때기')}
{fig_block(charts['05'], '분기 매출·GM')}
{fig_block(charts['06'], '마진·가이드')}
<ul>
  <li>Q1'26 매출 +55% YoY — A&amp;D Products +98%가 핵심</li>
  <li>GM 33.1% (전년 26.7%) — 믹스·규모 개선</li>
  <li>Q2 가이드: 매출 <b>$75–81M</b> (mid $78 = Products ~$58 / Adv Dev ~$20)</li>
  <li>Q2 GM <b>29–33%</b> · Adj EBITDA <b>$8–12M</b></li>
</ul>

<h2>3. 시나리오 · 촉매 · 포트</h2>
{fig_block(charts['07'], '주가 시나리오')}
{fig_block(charts['08'], '촉매')}
{fig_block(charts['09'], '포지션 맵')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bull</td><td>95–125</td><td>DE 양산 확대 · 가이던스 상향 · PT 상회</td></tr>
  <tr><td>Base</td><td>65–95</td><td>A&amp;D 성장 유지 · PT(~91) 수렴 · 실적 소화</td></tr>
  <tr><td>Bear</td><td>40–55</td><td>국방 예산/프로그램 지연 · Products 믹스 악화 · 희석</td></tr>
</table>
<div class="box">
<b>계좌 기준 실행</b><br/>
· 역할: <b>보유·추격금지 / 실적창</b> — LASR ×2주 (migration core phase1)<br/>
· 고점 부근(~52주고 ${H52:.1f}, 현재 ~${PX:.1f}) <b>추격 추가 매수 금지</b><br/>
· 트리거: <b>EARN_D5 {EARN}</b> Q2에서 Products 믹스·GM·가이던스 확인 후 재평가<br/>
· Watch: invalidation — A&amp;D 둔화 · Products 마진 급락 · Top 고객 발주 공백 · 대규모 희석
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>A&amp;D Products 양산</u>이 성장·마진의 열쇠.
스토리는 강하지만 계좌에는 <b>보유 유지·추격 금지</b>가 맞고, {EARN} 실적 소화가 우선.</div>

<h2>부록 · 출처</h2>
<p class="small">
nLIGHT Q1 FY2026 earnings release · yfinance 가격·PT·실적일 ({ASOF}).
피어 믹스·점유는 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 LASR · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_segment_mix(),
        "03": chart_ad_bridge(),
        "04": chart_tam_funnel(),
        "05": chart_quarterly(),
        "06": chart_margin_guide(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("LASR", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html = build_html(charts, compete_html=compete_html)
    html, _px = build_and_insert_price("LASR", CHART_DIR, html)
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
    print(f"LASR rev px={PX} pt={PT} upside={UPSIDE*100:.1f}% earn={EARN} compete={bundle is not None}")


if __name__ == "__main__":
    main()
