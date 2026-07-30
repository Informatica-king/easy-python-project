#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(PEBO) — Peoples Bancorp 지역은행 NII+수수료 + 경쟁점유/믹스 + WeasyPrint PDF."""

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

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
ASOF = "2026-07-30"
OUT_PDF = [
    Path("/opt/cursor/artifacts/PEBO_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/PEBO_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/PEBO_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/PEBO_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/pebo")
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
    "pebo": "#1d4ed8",
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
        (0.1, 0.7, 1.7, 1.6, "예금\n소매 78%", C["sand"]),
        (1.95, 0.7, 1.75, 1.6, "대출·리스\nC&I·CRE", C["pebo"]),
        (3.9, 0.7, 1.75, 1.6, "순이자마진\nNIM ~4.2%", C["teal"]),
        (5.85, 0.7, 1.75, 1.6, "수수료\n카드·신탁·보험", C["gold"]),
        (7.8, 0.7, 1.9, 1.6, "Citizens\n합병 대기", C["navy"]),
    ]
    for x, y, w, h, t, c in boxes:
        ax.add_patch(
            FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                           facecolor=c, edgecolor="white", lw=2)
        )
        tc = "white" if c in (C["pebo"], C["teal"], C["navy"], C["gold"]) else C["ink"]
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontproperties=PROP_B, fontsize=8.5, color=tc)
    for x in (1.85, 3.75, 5.7, 7.65):
        ax.annotate("", xy=(x + 0.08, 1.5), xytext=(x - 0.08, 1.5),
                    arrowprops=dict(arrowstyle="->", color=C["slate"], lw=1.6))
    ax.set_title("PEBO 가치사슬 — 예금 → 대출 → NII + 수수료 → (Citizens) 스케일", fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "01_business_flow.png")


def chart_revenue_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9))
    ax = axes[0]
    # Operating revenue: NII + fee ex G/L
    labels = ["순이자\n(NII)", "수수료\n(ex G/L)"]
    vals = [92.728, 29.005]
    colors = [C["pebo"], C["gold"]]
    ax.pie(vals, labels=labels, colors=colors, autopct=lambda p: f"{p:.0f}%",
           textprops={"fontproperties": PROP, "fontsize": 9}, startangle=90,
           wedgeprops=dict(width=0.45, edgecolor="white"))
    ax.set_title("Q2'26 운영 매출 믹스", fontproperties=PROP_B, fontsize=11)

    ax = axes[1]
    fee = [
        ("전자뱅킹", 6.543),
        ("신탁·투자", 5.986),
        ("리스", 4.977),
        ("예금수수료", 4.488),
        ("보험", 4.331),
        ("기타수수료", 2.680),
    ]
    # 29.005 - sum of first 5 = remainder
    names = [f[0] for f in fee]
    fvals = [f[1] for f in fee]
    bars = ax.barh(names[::-1], fvals[::-1], color=C["teal"], height=0.55)
    ax.set_xlabel("$M", fontproperties=PROP)
    ax.set_title("수수료 세부 (Q2'26)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, fvals[::-1]):
        ax.text(v + 0.08, b.get_y() + b.get_height() / 2, f"{v:.1f}", va="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "02_revenue_mix.png")


def chart_nii_nim() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    qs = ["Q2'25", "Q1'26", "Q2'26"]
    nii = [87.577, 90.420, 92.728]
    ax.bar(qs, nii, color=[C["sand"], C["teal"], C["pebo"]], width=0.55)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("순이자이익 (NII)", fontproperties=PROP_B, fontsize=11)
    for i, v in enumerate(nii):
        ax.text(i, v + 0.8, f"{v:.1f}", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    nim = [4.15, 4.16, 4.23]  # reported path (approx Q2'25 ~4.15 from presentation)
    ax.plot(qs, nim, marker="o", color=C["pebo"], lw=2)
    ax.fill_between(range(3), 4.10, 4.30, color=C["sand"], alpha=0.35)
    ax.set_ylabel("%", fontproperties=PROP)
    ax.set_title("NIM (FY26 가이드 4.1–4.3%)", fontproperties=PROP_B, fontsize=11)
    ax.set_ylim(4.0, 4.4)
    for i, v in enumerate(nim):
        ax.text(i, v + 0.02, f"{v:.2f}%", ha="center", fontproperties=PROP, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "03_nii_nim.png")


def chart_balance_sheet() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    cats = ["총자산", "대출·리스", "예금", "신탁AUM"]
    vals = [9.54, 6.82, 7.46, 2.52]
    colors = [C["navy"], C["pebo"], C["teal"], C["gold"]]
    bars = ax.bar(cats, vals, color=colors, width=0.55)
    ax.set_ylabel("$B", fontproperties=PROP)
    ax.set_title("Q2'26 밸런스시트 스케일 ($9.5B · $10B 미만 관리 · Citizens 합병)", fontproperties=PROP_B, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.12, f"${v:.2f}B", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.tight_layout()
    return save_fig(fig, "04_balance_sheet.png")


def chart_quality() -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(9.4, 3.5))
    ax = axes[0]
    ax.bar(["Q1'26", "Q2'26"], [9.7, 4.7], color=[C["red"], C["green"]], width=0.5)
    ax.set_title("대손충당 (Provision $M)", fontproperties=PROP_B, fontsize=10)
    for i, v in enumerate([9.7, 4.7]):
        ax.text(i, v + 0.2, f"{v:.1f}", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[1]
    ax.bar(["Q1'26", "Q2'26"], [6.6, 5.2], color=[C["sand"], C["teal"]], width=0.5)
    ax.set_title("순상각 (NCO $M)", fontproperties=PROP_B, fontsize=10)
    for i, v in enumerate([6.6, 5.2]):
        ax.text(i, v + 0.15, f"{v:.1f}", ha="center", fontproperties=PROP, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)

    ax = axes[2]
    ax.bar(["효율비율"], [58.3], color=C["pebo"], width=0.45)
    ax.set_ylim(0, 80)
    ax.set_title("Efficiency ~58.3%", fontproperties=PROP_B, fontsize=10)
    ax.text(0, 60, "58.3%", ha="center", fontproperties=PROP_B, fontsize=12, color="white")
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
    fig.suptitle("건전성·효율 — 충당금↓ · NCO↓ · 효율 소폭 개선", fontproperties=PROP_B, fontsize=11, y=1.02)
    fig.tight_layout()
    return save_fig(fig, "05_quality.png")


def chart_outlook() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    ax.axis("off")
    items = [
        (0.04, "NIM", "4.1–4.3%\nFY26", C["pebo"]),
        (0.28, "수수료", "분기\n$28–30M", C["gold"]),
        (0.52, "비용", "분기 OPEX\n$73–75M", C["teal"]),
        (0.76, "대출", "성장\n3–5% 하단", C["navy"]),
    ]
    for x, title, body, c in items:
        ax.add_patch(FancyBboxPatch((x, 0.28), 0.2, 0.5, boxstyle="round,pad=0.02,rounding_size=0.04",
                                    facecolor=c, edgecolor="white", lw=1.5, transform=ax.transAxes))
        ax.text(x + 0.1, 0.62, title, ha="center", transform=ax.transAxes, fontproperties=PROP_B, fontsize=11, color="white")
        ax.text(x + 0.1, 0.42, body, ha="center", transform=ax.transAxes, fontproperties=PROP, fontsize=8.5, color="white")
    ax.set_title("2026 가이던스 (non-core·Citizens 합병 영향 제외)", fontproperties=PROP_B, fontsize=12, pad=6)
    return save_fig(fig, "06_outlook.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    px = 42.0
    scenarios = [
        ("Bear", 32, 36, C["red"]),
        ("Base", 40, 45, C["teal"]),
        ("Bull", 46, 52, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}–{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(px, color=C["navy"], lw=1.5, ls="--")
    ax.text(px, 2.55, f"현재 ${px:.0f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(43.0, color=C["gold"], lw=1.2, ls=":")
    ax.text(43.0, -0.7, "PT평균~$43", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 밴드 (예시 · 투자권유 아님) · 배당~4%", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(28, 56)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    ax.axis("off")
    items = [
        (0.05, "08-03", "배당락", "배당 ~4%\nEx-div", C["gold"]),
        (0.28, "Citizens", "합병", "~$77M 거래\n$10B 미만 관리", C["navy"]),
        (0.52, "NIM", "금리", "예금비용↓\nFed +25bp → NIM+6–8bp", C["pebo"]),
        (0.76, "10-20", "실적", "다음 어닝\n가이던스 점검", C["teal"]),
    ]
    for x, tag, title, body, c in items:
        ax.add_patch(FancyBboxPatch((x, 0.25), 0.2, 0.55, boxstyle="round,pad=0.02,rounding_size=0.04",
                                    facecolor=c, edgecolor="white", lw=1.5, transform=ax.transAxes))
        ax.text(x + 0.1, 0.68, tag, ha="center", transform=ax.transAxes, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + 0.1, 0.55, title, ha="center", transform=ax.transAxes, fontproperties=PROP_B, fontsize=10, color="white")
        ax.text(x + 0.1, 0.38, body, ha="center", transform=ax.transAxes, fontproperties=PROP, fontsize=7.5, color="white")
    ax.set_title("촉매 — 합병·NIM·배당 · 이벤트 갭베팅 비추", fontproperties=PROP_B, fontsize=12, pad=8)
    return save_fig(fig, "08_catalysts.png")


def chart_position() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    rows = [
        (0.3, 1.6, 2.8, 1.0, "역할", "심층 워치\n방어·배당 성격", C["pebo"]),
        (3.4, 1.6, 2.8, 1.0, "사이즈", "코어 아님\n위성·소액만", C["teal"]),
        (6.5, 1.6, 3.2, 1.0, "트리거", "고점 근접\n눌림·배당락 후", C["gold"]),
        (0.3, 0.25, 4.5, 1.1, "주의", "52주 고점권 · PT 여유 얇음 · Citizens 통합 리스크", C["red"]),
        (5.1, 0.25, 4.6, 1.1, "품질", "NIM·수수료 안정 · 충당금 개선 · 배당~4%", C["navy"]),
    ]
    for x, y, w, h, title, body, c in rows:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    facecolor=c, edgecolor="white", lw=1.5))
        ax.text(x + 0.15, y + h - 0.28, title, fontproperties=PROP_B, fontsize=9, color="white")
        ax.text(x + w / 2, y + 0.35, body, ha="center", va="center", fontproperties=PROP, fontsize=8.5, color="white")
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
        mix_body.append(f"<tr><td>{r['name']}{tag}</td>{cells}<td class='small'>{r.get('note','')}</td></tr>")
    ttm_fig = fig_block(charts["ttm"], "TTM 매출 규모") if "ttm" in charts else ""
    return f"""
<h2>1-B. 심층 섹터 경쟁 점유율 · 변화</h2>
<p><b>섹터</b> {bundle.sector_ko}</p>
<div class="easy"><b>쉽게:</b> PEBO는 Huntington·Fifth Third 같은 <b>대형 지역은행</b>과 같은 주에서 싸우지만,
규모는 커뮤니티급. 점유율 자체보다 <b>NIM·수수료·배당·합병</b>으로 가치를 만든다.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>
{gloss([
    ("커뮤니티뱅크", "지역 예금·대출 중심. 전국 디지털뱅크와 고객층이 다름."),
    ("pp", "percentage points."),
])}

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> 은행은 대개 <b>이자(NII)</b>가 본체, <b>수수료</b>가 보조.
PEBO는 수수료 ~24%로 커뮤니티 치고는 다각화(카드·신탁·보험·리스)가 있는 편.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
{gloss([
    ("NII", "Net Interest Income — 대출이자 − 예금이자."),
    ("Fee ex G/L", "증권·자산매각 손익을 제외한 수수료 수익."),
])}
"""


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"PEBO 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #1d4ed8; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0f766e; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#dbeafe 0%,#e8eef5 55%,#f0fdf4 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#dbeafe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.good {{ background:#bbf7d0; }}
    .tag.bad {{ background:#fecdd3; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#eff6ff; border-left:4px solid #1d4ed8; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#1e3a5f; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#1d4ed8; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
      padding:8px 12px; margin:6px; min-width:105px; text-align:center; }}
    .kpi .l {{ font-size:7.5pt; color:#64748b; }}
    .kpi .v {{ font-size:12pt; font-weight:700; color:#1e3a5f; }}
    .kpi .s {{ font-size:7.5pt; color:#1d4ed8; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>PEBO 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>PEBO 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Peoples Bancorp · 오하이오 커뮤니티뱅크 · NII + 수수료 · 배당~4%</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 실적(7/21) · 다음 실적 ~10-20 · Citizens 합병 대기</p>
  <p style="margin-top:16px">
    <span class="kpi"><div class="l">현재가</div><div class="v">~$42</div><div class="s">시총 ~$1.5B</div></span>
    <span class="kpi"><div class="l">PT 평균</div><div class="v">~$43</div><div class="s">업사이드 ~+2%</div></span>
    <span class="kpi"><div class="l">Q2 NII</div><div class="v">$92.7M</div><div class="s">NIM 4.23%</div></span>
    <span class="kpi"><div class="l">총자산</div><div class="v">$9.5B</div><div class="s">$10B 미만 관리</div></span>
  </p>
  <p style="margin-top:18px">
    <span class="tag">Chase 중</span>
    <span class="tag warn">고점권 · PT여유薄</span>
    <span class="tag good">배당~4% · NIM안정</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>예금으로 조달해 대출·리스에 넣고, 순이자(NII) + 카드·신탁·보험·리스 수수료로 버는 중서부 커뮤니티뱅크.</b>
Q2'26: NII $92.7M · NIM 4.23% · 수수료(ex G/L) $29.0M(~매출의 24%) · GAAP EPS $0.78
(증권매각손실 −$0.18/주). Citizens(~$77M) 합병으로 스케일 확장 중, 자산은 <b>$10B 미만</b>으로 관리.</p>
{fig_block(charts['01'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 동네·지역 고객 예금을 모아 기업·개인에 빌려주고
이자 차이(NIM)로 먹고, 카드·신탁·보험으로 수수료를 보탠다. 지금은 큰 은행이 되기 직전($10B) 문턱에서
합병을 준비 중이다.</div>
{gloss([
    ("NIM", "Net Interest Margin — 이자수익자산 대비 순이자이익 비율."),
    ("Citizens merger", "KY Citizens National 인수(~$76.6M) · 2026-04 발표."),
    ("$10B threshold", "자산 $10B 초과 시 규제·비용 부담이 커져 미리 BS 정리."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['02'], '운영 매출 믹스 · 수수료 세부')}
{fig_block(charts['03'], 'NII · NIM 추이')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>QoQ / YoY</th><th>의미</th></tr>
  <tr><td><b>Net Interest Income</b></td><td>$92.7M</td><td>+$2.3M / +6%</td><td>예금비용 하락이 주동력</td></tr>
  <tr><td>NIM</td><td>4.23%</td><td>+7bp QoQ</td><td>FY26 가이드 4.1–4.3% 내</td></tr>
  <tr><td>Fee income (ex G/L)</td><td>$29.0M</td><td>+1% QoQ / +7% YoY</td><td>운영매출의 ~24%</td></tr>
  <tr><td>전자뱅킹</td><td>$6.5M</td><td>카드 인터체인지↑</td><td>수수료 1위 라인</td></tr>
  <tr><td>신탁·투자</td><td>$6.0M</td><td>AUM $2.52B</td><td>WM 성장</td></tr>
  <tr><td>보험</td><td>$4.3M</td><td>QoQ↓(계절)</td><td>Q1 성과수수료 반영 후 정상화</td></tr>
  <tr><td>Provision</td><td>$4.7M</td><td>QoQ 절반↓</td><td>고손실 세그먼트 잔액↓</td></tr>
  <tr><td>Net Income / EPS</td><td>$28.0M / $0.78</td><td>non-core −$0.18</td><td>AFS 매각손실 $8.2M</td></tr>
</table>
<p class="small">Q2 GAAP 비이자는 증권매각손실로 일시 왜곡. 운영 품질은 NII+Fee ex G/L로 보는 것이 맞다.</p>
<div class="easy"><b>쉽게:</b> 돈의 약 <b>3/4는 이자</b>, <b>1/4은 수수료</b>.
이번 분기 이익이 깎인 이유는 사업이 나빠져서가 아니라, 합병 앞두고 증권을 팔아
<b>일회성 손실</b>을 냈기 때문이다.</div>
{gloss([
    ("AFS restructure", "Available-for-sale 증권 $135M 매각 · $10B 미만 BS 관리."),
    ("Fee mix", "전자뱅킹·신탁·리스·예금수수료·보험이 주축."),
])}

{compete_html}

<h2>2. 밸런스시트 · 건전성</h2>
{fig_block(charts['04'], '스케일')}
{fig_block(charts['05'], '충당·상각·효율')}
<ul>
  <li>총자산 <b>$9.54B</b> · 대출 $6.82B · 예금 $7.46B (소매 78% / 상업 22%)</li>
  <li>대출 성장: QoQ 연율 ~3% · C&I·프리미엄파이낸스·건설 ↑ · 기타 CRE↓</li>
  <li>비보험예금 27% · 일부 담보화</li>
  <li>효율비율 ~58.3% · 양의 영업 레버리지 가이던스(FY26)</li>
</ul>

<h2>3. 가이던스 · 시나리오</h2>
{fig_block(charts['06'], '2026 가이던스')}
{fig_block(charts['07'], '주가 시나리오')}
<table>
  <tr><th>항목</th><th>가이던스</th></tr>
  <tr><td>NIM FY26</td><td>4.1–4.3% (Fed +25bp 시 NIM +6–8bp)</td></tr>
  <tr><td>분기 수수료</td><td>$28–30M</td></tr>
  <tr><td>분기 비이자비용</td><td>$73–75M (남은 2분기)</td></tr>
  <tr><td>대출성장</td><td>3–5% 범위 <b>하단</b> 예상</td></tr>
</table>

<h2>4. 촉매 · 포트 실행</h2>
{fig_block(charts['08'], '촉매')}
{fig_block(charts['09'], '포지션 맵')}
<div class="box">
<b>계좌 기준 실행</b><br/>
· 역할: 심층 <b>중</b> · 방어·배당 성격 워치 (코어 후보 아님)<br/>
· 가격: ~$42 · PT~$43 · <b>업사이드 얇음 · 52주 고점권</b> → 추격 비추<br/>
· 트리거: 배당락(08-03) 소화 · Citizens 진행 · NIM 유지 확인 후 눌림만<br/>
· 사이즈: 위성 소액 · 현금 높은 국면에서 우선순위는 RELY/APA 아래
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>안정 NII + 다각화 수수료</u>.
품질은 무난하나 <b>지금 주가에 이미 많이 반영</b>. 매수보다 관망·배당락 후 재평가.</div>

<h2>부록 · 출처</h2>
<p class="small">
Peoples Q2 2026 earnings release (2026-07-21) · SEC Exhibit 99.1 · conference call remarks ·
yfinance 가격·PT ({ASOF}). 시나리오·점유율은 예시/추정치(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 PEBO · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete</p>
</body></html>
"""


def main() -> None:
    charts = {
        "01": chart_business_flow(),
        "02": chart_revenue_mix(),
        "03": chart_nii_nim(),
        "04": chart_balance_sheet(),
        "05": chart_quality(),
        "06": chart_outlook(),
        "07": chart_scenarios(),
        "08": chart_catalysts(),
        "09": chart_position(),
    }
    bundle, cpaths = build_compete_charts("PEBO", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html = build_html(charts, compete_html=compete_html)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML {OUT_HTML} {OUT_HTML.stat().st_size}")
    doc = HTML(filename=str(OUT_HTML))
    for p in OUT_PDF:
        p.parent.mkdir(parents=True, exist_ok=True)
        doc.write_pdf(str(p))
        print(f"PDF {p} {p.stat().st_size}")


if __name__ == "__main__":
    main()
