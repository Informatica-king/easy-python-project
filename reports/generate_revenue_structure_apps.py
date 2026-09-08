#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(APPS) — Digital Turbine ODS + App Growth Platform + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-09-08"
PX = 10.71
PT = 17.17
H52 = 15.34
L52 = 2.74
UPSIDE = PT / PX - 1.0
EARN = "08-04"  # Q1 FY'27 reported
OUT_PDF = [
    Path("/opt/cursor/artifacts/APPS_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/APPS_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/APPS_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/APPS_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/apps")
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
    "ods": "#0e7490",
    "agp": "#c2410c",
    "slate": "#334155",
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
        (0.1, 0.7, 1.7, 1.6, "통신사·\nOEM·기기", C["sand"]),
        (2.0, 0.7, 1.75, 1.6, "ODS\n프리로드·\n미디어", C["ods"]),
        (3.95, 0.7, 1.75, 1.6, "AGP\n브랜드·\nDT Exchange", C["agp"]),
        (5.9, 0.7, 1.7, 1.6, "광고주·\n퍼블리셔", C["navy"]),
        (7.8, 0.7, 1.9, 1.6, "매출·\nAdj.EBITDA", C["teal"]),
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
    ax.set_title("비즈니스 한눈에 — 기기 안·밖으로 앱·광고를 연결",
                 fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [66.0, 34.0]
    labels = ["On Device\nSolutions ~66%", "App Growth\nPlatform ~34%"]
    ax.pie(
        sizes, labels=labels,
        colors=[C["ods"], C["agp"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.5),
    )
    ax.set_title("세그먼트 믹스 (elim 전)", fontproperties=PROP_B, fontsize=10)

    ax = axes[1]
    # FY quarters: Q1'26=Jun'25 … Q1'27=Jun'26
    labels_q = ["Q1'26", "Q2'26", "Q3'26", "Q4'26", "Q1'27"]
    revs = [130.9, 140.4, 151.4, 142.5, 166.0]
    ax.bar(labels_q, revs, color=[C["sand"], C["sand"], C["sand"], C["navy"], C["teal"]])
    ax.set_ylabel("매출 ($M)", fontproperties=PROP)
    ax.set_title("분기 매출 ($M, FY 기준)", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(revs):
        ax.text(i, v + 3, f"{v:.0f}", ha="center", fontsize=8, fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "02_segment_mix.png")


def chart_margin_bridge() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    labels = ["매출", "직접비+", "총이익*", "영업비용", "영업이익", "이자·기타", "GAAP 순손실"]
    # Q1 FY27: Rev 166, GP~82 GAAP / Non-GAAP GP 82.0-ish; OpInc 23.1; NI -3.2 press
    vals = [166.0, -84.0, 82.0, -58.9, 23.1, -26.3, -3.2]
    colors = [C["teal"], C["red"], C["ods"], C["agp"], C["green"], C["red"], C["red"]]
    ax.bar(labels, vals, color=colors)
    ax.axhline(0, color=C["ink"], lw=0.8)
    ax.set_title("Q1 FY'27 손익 브리지 ($M) — 영업흑자·GAAP 소폭 적자",
                 fontproperties=PROP_B, fontsize=11)
    ax.set_ylabel("$M", fontproperties=PROP)
    for i, v in enumerate(vals):
        label = f"+{v:.0f}" if v >= 0 else f"-{abs(v):.0f}"
        ax.text(i, v + (4 if v >= 0 else -10), label, ha="center",
                fontsize=8, fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "03_margin_bridge.png")


def chart_guide() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    cats = ["FY27 매출\n가이던스", "FY27 Adj.\nEBITDA"]
    lo = [650, 145]
    hi = [670, 155]
    ax.barh(cats, [h - l for l, h in zip(lo, hi)], left=lo, height=0.45,
            color=[C["teal"], C["navy"]], alpha=0.9)
    for i, (l, h) in enumerate(zip(lo, hi)):
        ax.text((l + h) / 2, i, f"${l}–{h}M", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.set_title("FY27 가이던스 상향 (Q1 후 · 08-04)", fontproperties=PROP_B, fontsize=12)
    ax.set_xlabel("$M", fontproperties=PROP)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "05_guide.png")


def chart_leverage() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.bar(["순레버리지\n(~1년 전)", "순레버리지\n현재"], [5.2, 2.5],
           color=[C["red"], C["teal"]], width=0.45)
    ax.set_ylabel("x", fontproperties=PROP)
    ax.set_title("순레버리지 — >5x → ~2.5x (경영진 코멘트)", fontproperties=PROP_B, fontsize=12)
    for i, v in enumerate([5.2, 2.5]):
        ax.text(i, v + 0.15, f"{v:.1f}x", ha="center", fontproperties=PROP_B, fontsize=11)
    ax.set_ylim(0, 6.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "04_leverage.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 6, 9, C["red"]),
        ("Base", 11, 16, C["teal"]),
        ("Bull", 18, 24, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}–{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"현재 ${PX:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT평균 ${PT:.1f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 — AGP 모멘텀·가이던스 vs 부채·경쟁", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(4, 26)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, "AGP", "가속", "YoY +56%\nDTX·브랜드", C["agp"]),
        (0.28, "가이던스", "상향", "매출·EBITDA\nFY27↑", C["teal"]),
        (0.52, "레버리지", "개선", "~2.5x\nFCF +", C["navy"]),
        (0.76, "부채·경쟁", "리스크", "이자·APP/U\n점유 압박", C["red"]),
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
    ax.set_title("촉매 — AGP·가이던스 vs 대형 피어·부채", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "보유 20주\n품질C·NO_ADD", C["teal"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "16% OVER\nC≤6% 한도", C["navy"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", "stop $10\n추가·물타기 금지", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "−8%권 · stop 근접 · APP/U 스케일 격차 · 추격·물타기 금지", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "매출+27% · AGP+56% · 가이던스↑ · 레버리지↓", C["ods"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                           facecolor=c, edgecolor="white", lw=1.5)
        )
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.35, body, ha="center", va="center",
                fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title("실행 포지션 맵 (포트 9/8 · APPS 20주 NO_ADD · stop $10)", fontproperties=PROP_B, fontsize=12, pad=4)
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
<div class="easy"><b>쉽게:</b> APPS는 <b>중형 모바일 성장 플랫폼</b>이다.
APP·U 대비 스케일은 작고, 피어셋 점유는 <b>+0.8pp</b> 추정 — 성장은 보이지만 대형 대비 챌린저.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> 공시는 <b>ODS(온디바이스)</b>와 <b>AGP(앱성장·광고)</b> 두 축.
이번 분기 AGP가 +56%로 믹스를 끌어올렸다 (~34%).</div>
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
      @bottom-center {{ content:"APPS 수익구조분석 {ASOF} — " counter(page);
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
<html lang="ko"><head><meta charset="utf-8"/><title>APPS 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>APPS 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Digital Turbine · 모바일 온디바이스·앱성장 플랫폼</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q1 FY'27 실적({EARN} 발표) · 시총 ~$1.3B · ${PX:.2f}</p>
  <div style="margin-top:22px">
    <span class="tag">ODS + AGP</span>
    <span class="tag good">매출 +27% YoY</span>
    <span class="tag good">AGP +56%</span>
    <span class="tag warn">보유 20주 NO_ADD</span>
    <span class="tag bad">stop $10 근접</span>
  </div>
  <div style="margin-top:28px">
    <div class="kpi"><div class="l">Q1 매출</div><div class="v">$166M</div><div class="s">YoY +27%</div></div>
    <div class="kpi"><div class="l">Adj.EBITDA</div><div class="v">$42.5M</div><div class="s">YoY +69%</div></div>
    <div class="kpi"><div class="l">Adj. EPS</div><div class="v">$0.19</div><div class="s">vs $0.06</div></div>
    <div class="kpi"><div class="l">업사이드</div><div class="v">{UPSIDE*100:+.1f}%</div><div class="s">PT ${PT:.1f}</div></div>
  </div>
  <p class="small" style="margin-top:36px;max-width:520px;margin-left:auto;margin-right:auto">
    통신사·OEM 프리로드(ODS)와 브랜드·DT Exchange(AGP)  Dual. Q1 FY'27은 AGP 가속·가이던스 상향·레버리지 개선이 핵심.
    GAAP는 아직 소폭 적자·부채 잔존. APP/U 대비 스케일 격차는 큼.
  </p>
</section>

<h2>0. 한줄 결론</h2>
<div class="box">
<b>성장·레버리지는 개선, 포트는 보유 NO_ADD · stop 경계.</b>
매출 $166M(+27%) · AGP +56% · Adj.EBITDA $42.5M(+69%) · FY27 가이던스 상향 · 순레버리지 ~2.5x.
다만 GAAP 소폭 적자·이자·대형 피어 경쟁. 포트: <b>보유 20주 · 품질C · 16% OVER · stop $10 · NO_ADD</b> — 물타기·추격 금지.
</div>

<h2>1. 비즈니스 구조</h2>
<div class="easy"><b>쉽게:</b> 새 폰에 앱·콘텐츠를 심고(ODS), 앱·광고 네트워크로 성장시킨다(AGP).
광고주·퍼블리셔·통신사·OEM을 한 플랫폼으로 연결해 수수료·광고비를 받는다.</div>
{fig_block(charts['flow'], 'OEM·통신사 → ODS/AGP → 매출')}
{gloss([
    ("ODS", "On Device Solutions — 기기 프리로드·온디바이스 미디어"),
    ("AGP", "App Growth Platform — 브랜드·DT Exchange(SSP) 등 앱성장·광고"),
    ("DT Exchange", "Digital Turbine의 프로그래머틱/SSP 성격 공급 플랫폼"),
])}

{compete_html}

<h2>2. 매출·마진 (Q1 FY'27)</h2>
<div class="easy"><b>쉽게:</b> 매출 $166M은 작년보다 27% 늘었고, 조정 EBITDA는 69% 늘었다.
영업이익은 흑자($23M)인데 GAAP 순이익은 아직 소폭 적자(이자·비현금 등).</div>
{fig_block(charts['mix'], '세그먼트 믹스 + 분기 매출')}
{fig_block(charts['bridge'], '손익 브리지')}
<table>
  <tr><th>항목</th><th>Q1 FY'27</th><th>Q1 FY'26</th><th>메모</th></tr>
  <tr><td>매출</td><td>$166.0M</td><td>$130.9M</td><td>+27%</td></tr>
  <tr><td>ODS (elim 전)</td><td>$110.0M</td><td>$95.4M</td><td>+15%</td></tr>
  <tr><td>AGP (elim 전)</td><td>$56.6M</td><td>$36.3M</td><td>+56%</td></tr>
  <tr><td>Adj. EBITDA</td><td>$42.5M</td><td>$25.1M</td><td>+69%</td></tr>
  <tr><td>Adj. EPS</td><td>$0.19</td><td>$0.06</td><td>비트</td></tr>
  <tr><td>GAAP EPS</td><td>$(0.03)</td><td>—</td><td>순손실 $3.2M</td></tr>
  <tr><td>Non-GAAP FCF</td><td>$11.3M</td><td>$1.4M</td><td>개선</td></tr>
</table>
{gloss([
    ("Non-GAAP Adj. EPS", "SBC·무형상각·리파이낸스 관련 등 제외"),
    ("순레버리지", "순부채/Adj.EBITDA 근사. 경영진 ~2.5x 코멘트"),
])}

<h2>3. 레버리지 · 가이던스</h2>
{fig_block(charts['lev'], '순레버리지 개선')}
{fig_block(charts['guide'], 'FY27 가이던스')}
<div class="easy"><b>쉽게:</b> 회사가 FY27 매출 $650–670M · Adj.EBITDA $145–155M으로 올렸다.
레버리지가 5x대에서 ~2.5x로 내려온 것이 “성장 + 재무 안정” 스토리의 축.</div>

<h2>4. 시나리오 · 촉매</h2>
{fig_block(charts['scen'], '주가 시나리오 밴드')}
{fig_block(charts['cat'], '촉매 카드')}
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$6–9</td><td>AGP 둔화 · 기기 출하 약세 · 이자·리파이낸스 재악화</td></tr>
  <tr><td>Base</td><td>$11–16</td><td>가이던스 달성 · AGP 성장 지속 · 레버리지 추가 개선</td></tr>
  <tr><td>Bull</td><td>$18–24</td><td>AGP 가속 · GAAP 흑자 전환 · 멀티플 재평가</td></tr>
</table>

<h2>5. 포트 실행</h2>
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (9/8 스냅 · 심층 연동)</b><br/>
보유 <b>20주</b> · 평단 ~$11.54 · 마크 ~${PX:.2f} (−8%권) · 품질C · 비중 OVER · stop <b>$10</b> · <b>NO_ADD</b>.<br/>
PT 업사이드 ~{UPSIDE*100:+.0f}% · 52주 ${L52:.2f}–${H52:.2f}. 실행: <b>추가·물타기·추격 금지</b> · stop 이탈 시 축소 검토.<br/>
품질 게이트: 다음 분기도 AGP YoY 성장 · 가이던스 궤적 · 레버리지 ≤3x대 유지.
</div>

<p class="small">생성: 수익구조분석() · 티커 APPS · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart<br/>
출처: Digital Turbine Q1 FY'27 earnings (2026-08-04) · yfinance · 피어 점유/믹스는 방향 비교용 추정</p>
</body></html>
"""


def main() -> int:
    charts: dict[str, Path] = {
        "flow": chart_business_flow(),
        "mix": chart_segment_mix(),
        "bridge": chart_margin_bridge(),
        "lev": chart_leverage(),
        "guide": chart_guide(),
        "scen": chart_scenarios(),
        "cat": chart_catalysts(),
        "pos": chart_position(),
    }
    bundle, cpaths = build_compete_charts("APPS", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("APPS", CHART_DIR, html_doc)
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

        tag = "sepa-rev-apps"
        notes = (
            f"## APPS 수익구조분석 ({ASOF})\n\n"
            f"Digital Turbine · Q1 FY'27 · ODS 66% / AGP 34% · FY27 $650–670M.\n\n"
            f"- 매출 $166M(+27%) · Adj EBITDA $42.5M(+69%) · AGP +56%\n"
            f"- 포트: 보유 20주 · NO_ADD · stop $10 · 품질C OVER\n"
            f"- 업사이드 {UPSIDE*100:+.1f}% (PT ${PT:.2f} · px ${PX:.2f})\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — APPS",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
