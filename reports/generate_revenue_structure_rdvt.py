#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석(RDVT) — Red Violet 신원인텔리전스(IDI+FOREWARN) + 경쟁점유/믹스 + WeasyPrint PDF."""

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
ASOF = "2026-10-08"
PX = 78.07
PT = 84.50
H52 = 81.80
L52 = 33.40
UPSIDE = PT / PX - 1.0
NEAR = PX / H52
EARN = "11-04"
OUT_PDF = [
    Path("/opt/cursor/artifacts/RDVT_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/reports/RDVT_Revenue_Structure_Analysis.pdf"),
    Path("/workspace/assets/RDVT_Revenue_Structure_Analysis.pdf"),
]
OUT_HTML = Path("/workspace/reports/RDVT_Revenue_Structure_Analysis.html")
CHART_DIR = Path("/workspace/reports/charts/rdvt")
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
    "idi": "#1d4ed8",
    "fw": "#c2410c",
    "cont": "#0e7490",
    "txn": "#7c3aed",
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
        (0.1, 0.7, 1.75, 1.6, "공공·상용\n데이터 수집", C["sand"]),
        (2.0, 0.7, 1.8, 1.6, "CORE™\n신원 그래프", C["navy"]),
        (3.95, 0.7, 1.8, 1.6, "IDI / idiCORE\n조사·사기방지", C["idi"]),
        (5.9, 0.7, 1.8, 1.6, "FOREWARN\n대면 안전앱", C["fw"]),
        (7.85, 0.7, 1.9, 1.6, "라이선스\nAdj.EBITDA", C["teal"]),
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
        "RDVT 가치사슬 — 데이터를 신원 그래프로 풀어 조회·구독 라이선스를 판다",
        fontproperties=PROP_B, fontsize=11, pad=6,
    )
    return save_fig(fig, "01_business_flow.png")


def chart_segment_mix() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    ax = axes[0]
    sizes = [77, 23]
    labels = ["Contractual\n약정·월정액\n77%", "Transactional\n건별 조회\n23%"]
    ax.pie(
        sizes, labels=labels, colors=[C["cont"], C["txn"]],
        startangle=90, wedgeprops=dict(width=0.72, edgecolor="white", linewidth=2),
        textprops=dict(fontproperties=PROP, fontsize=8.2),
    )
    ax.set_title("수익 인식 (Q2'26, 총 $26.7M)", fontproperties=PROP_B, fontsize=10.5)

    ax = axes[1]
    q = ["Q3'24", "Q4'24", "Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26", "Q2'26"]
    idi = [8.74, 8.93, 9.24, 9.55, 9.85, 10.02, 10.42, 10.87]
    fw = [285, 303, 325, 347, 372, 390, 418, 443]
    ax.plot(q, idi, marker="o", color=C["idi"], lw=2.0, label="IDI 고객(천)")
    ax2 = ax.twinx()
    ax2.plot(q, fw, marker="s", color=C["fw"], lw=2.0, label="FOREWARN 유저(천)")
    ax.set_title("브랜드 스케일 — IDI 1.09만 · FW 44.3만", fontproperties=PROP_B, fontsize=10)
    ax.set_ylabel("IDI 천 고객", fontproperties=PROP, color=C["idi"])
    ax2.set_ylabel("FOREWARN 천 유저", fontproperties=PROP, color=C["fw"])
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(7)
        lbl.set_rotation(30)
    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, prop=PROP, frameon=False, fontsize=7.5, loc="upper left")
    fig.tight_layout()
    return save_fig(fig, "02_revenue_mix.png")


def chart_growth_bridge() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    cats = ["매출", "Adj GP", "Adj EBITDA", "GAAP NI"]
    yoy = [23.0, 25.0, 48.0, 85.0]
    colors = [C["navy"], C["cont"], C["teal"], C["gold"]]
    for i, (v, c) in enumerate(zip(yoy, colors)):
        ax.bar(i, v, color=c, width=0.55)
        ax.text(i, v + 1.2, f"+{v:.0f}%", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_xticks(range(4))
    ax.set_xticklabels(cats, fontproperties=PROP, fontsize=8)
    ax.set_ylabel("YoY %", fontproperties=PROP)
    ax.set_title("성장 브리지 (Q2'26)", fontproperties=PROP_B, fontsize=10.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    labs = ["IDI\n고객", "FOREWARN\n유저", "계약\n매출", "GRR"]
    vals = [13.8, 27.8, 77.0, 95.0]
    cols = [C["idi"], C["fw"], C["cont"], C["teal"]]
    for i, (s, c) in enumerate(zip(vals, cols)):
        ax.bar(i, s, color=c, width=0.55)
        extra = "YoY" if i < 2 else ("Q2" if i == 2 else "TTM")
        ax.text(i, s + 1.5, f"{s:.0f}%\n{extra}", ha="center", fontproperties=PROP, fontsize=7.5)
    ax.set_xticks(list(range(4)))
    ax.set_xticklabels(labs, fontproperties=PROP, fontsize=8)
    ax.set_ylim(0, 115)
    ax.set_title("엔진 — 고객+유저 · 약정 77% · 잔존 95%", fontproperties=PROP_B, fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "03_growth_bridge.png")


def chart_pnl() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7))
    ax = axes[0]
    x = [0, 1]
    gm = [72, 76]
    agm = [84, 86]
    ebitda = [35, 42]
    ax.plot(x, gm, marker="o", color=C["gold"], lw=2.2, label="GAAP GP%")
    ax.plot(x, agm, marker="o", color=C["teal"], lw=2.2, label="Adj GP%")
    ax.plot(x, ebitda, marker="o", color=C["navy"], lw=2.2, label="Adj EBITDA%")
    ax.set_xticks(x)
    ax.set_xticklabels(["Q2'25", "Q2'26"], fontproperties=PROP)
    ax.set_ylabel("% of sales", fontproperties=PROP)
    ax.set_ylim(30, 95)
    ax.set_title("마진 확장 — GP 76% · Adj EBITDA 42%", fontproperties=PROP_B, fontsize=10)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    names = ["매출\n$M", "Adj EBITDA\n$M", "OCF\n$M"]
    q25 = [21.8, 7.6, 7.5]
    q26 = [26.7, 11.2, 10.6]
    w = 0.35
    ax.bar([i - w / 2 for i in range(3)], q25, w, color=C["sand"], label="Q2'25")
    ax.bar([i + w / 2 for i in range(3)], q26, w, color=C["navy"], label="Q2'26")
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(names, fontproperties=PROP, fontsize=8)
    ax.set_title("달러 실적 · OCF $10.6M (매출 40%)", fontproperties=PROP_B, fontsize=10.5)
    ax.legend(prop=PROP, frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return save_fig(fig, "04_pnl.png")


def chart_leverage() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
    ax = axes[0]
    ax.bar(["Q2'26 현금", "오퍼링 순액", "이후 추정"], [50.0, 109.0, 160.0],
           color=[C["navy"], C["gold"], C["teal"]], width=0.55)
    for i, v in enumerate([50.0, 109.0, 160.0]):
        ax.text(i, v + 3, f"${v:.0f}M", ha="center", fontproperties=PROP, fontsize=8)
    ax.set_ylabel("$M", fontproperties=PROP)
    ax.set_title("현금 — 무차입 + 8월 $109M 증자", fontproperties=PROP_B, fontsize=10.5)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(PROP)
        lbl.set_fontsize(8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    names = ["FCF Q2", "자사주 YTD", "리스부채"]
    vals = [7.2, 3.1, 2.6]
    cols = [C["teal"], C["fw"], C["muted"]]
    bars = ax.bar(names, vals, color=cols, width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15, f"${v:.1f}M",
                ha="center", fontproperties=PROP, fontsize=8)
    ax.set_title("FCF $7.2M · 레버리지 ≈ 0x", fontproperties=PROP_B, fontsize=10.5)
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
        (0.04, "Q3 컨센 매출", "$26.9–27.4M\n중간 ~$27.2M", C["navy"]),
        (0.28, "Q3 EPS", "평균 $0.42\n(논GAAP 이력 Beat)", C["teal"]),
        (0.52, "FY Adj EBITDA", "마진 high-30s\nQ4 보상 시즌↓", C["cont"]),
        (0.76, "런레이트", "Q2×4 ≈ $107M\n$100M+ 유지", C["gold"]),
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
    ax.set_title("가이던스 — 공식 숫자가이드 없음 · 컨센+콜 방향 (high-30s 마진)", fontproperties=PROP_B, fontsize=11, pad=6)
    return save_fig(fig, "06_guide.png")


def chart_scenarios() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    scenarios = [
        ("Bear", 45, 58, C["red"]),
        ("Base", 70, 88, C["teal"]),
        ("Bull", 95, 120, C["green"]),
    ]
    for i, (name, lo, hi, c) in enumerate(scenarios):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=c, alpha=0.85)
        ax.text((lo + hi) / 2, i, f"{name} ${lo}-{hi}", ha="center", va="center",
                fontproperties=PROP_B, fontsize=10, color="white")
    ax.axvline(PX, color=C["navy"], lw=1.5, ls="--")
    ax.text(PX, 2.55, f"현재 ${PX:.2f}", ha="center", fontproperties=PROP, fontsize=8, color=C["navy"])
    ax.axvline(PT, color=C["gold"], lw=1.2, ls=":")
    ax.text(PT, -0.7, f"PT평균 ${PT:.0f}", ha="center", fontproperties=PROP, fontsize=8, color=C["gold"])
    ax.set_yticks([])
    ax.set_xlabel("주가 ($)", fontproperties=PROP)
    ax.set_title("시나리오 밴드 (예시 · 투자권유 아님)", fontproperties=PROP_B, fontsize=12)
    ax.set_xlim(35, 130)
    fig.tight_layout()
    return save_fig(fig, "07_scenarios.png")


def chart_catalysts() -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    cards = [
        (0.2, 1.55, 3.0, 1.4, "실적 11-04", "Q3 · 컨센 $27.2M\n마진 유지 확인", C["navy"]),
        (3.5, 1.55, 3.0, 1.4, "FOREWARN 확장", "홈헬스케어 런칭\n부동산 네트워크", C["fw"]),
        (6.8, 1.55, 3.0, 1.4, "IDI 고객", "Q2 +447 기록\n10,869 종료", C["idi"]),
        (0.2, 0.15, 3.0, 1.2, "워체스트", "$109M 증자\nM&A 옵션", C["gold"]),
        (3.5, 0.15, 3.0, 1.2, "잔존·약정", "GRR 95% · 계약 77%\n협회 갱신 100%", C["teal"]),
        (6.8, 0.15, 3.0, 1.2, "리스크", "데이터 공급 46%\n고점 95% · 희석", C["red"]),
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
                       facecolor="#fff7ed", edgecolor=C["fw"], lw=2)
    )
    ax.text(
        5.0, 2.05,
        f"미보유 · 10-08 Chase 중 · 엔트리 눌림 · 고점 {NEAR*100:.0f}%",
        ha="center", va="center", fontproperties=PROP_B, fontsize=10, color=C["fw"],
    )
    ax.text(
        5.0, 1.1,
        f"현재 ${PX:.2f} · PT ${PT:.0f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}–${H52:.2f}\n"
        "추격보다 눌림 · 다음 실적 11-04 · 수익구조는 좋지만 자리(고점·업사이드 작음)는 추격 아님",
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
<div class="easy"><b>쉽게:</b> RDVT는 신용뷰로 거인(EFX·TRU) 옆의 <b>순수 신원인텔 SaaS</b>다.
조사·사기방지 오버레이 피어셋에서 스케일 점유 <b>~18% · Δ+1.5pp</b> 추정.
절대 신원시장 점유가 아니라 <u>상장 오버레이 피어 비교용</u>.</div>
{fig_block(charts['share'], bundle.share_title)}
{fig_block(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>
{gloss([
    ("idiCORE", "IDI 플래그십 — 실사·사기·규정준수·채권추심용 조사 솔루션."),
    ("Accurint / TLOxp", "LexisNexis·TransUnion의 공공기록 조사 툴. RDVT의 직접 경쟁 레이어."),
])}

<h2>1-C. 경쟁사 매출 구조 비율 비교</h2>
<div class="easy"><b>쉽게:</b> RDVT 매출의 <b>77%는 연간 약정(월정액+초과)</b>, 23%는 건별 조회.
뷰로 거인은 구독+배치가 섞이고, FICO는 스코어 조회 비중이 크다.
RDVT의 차별점은 <b>클라우드 네이티브 CORE 그래프 + FOREWARN 네트워크</b>다.</div>
{fig_block(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
{gloss([
    ("Contractual", "월정액이 있는 프라이싱 계약 + 초과 사용. 보통 1년+ 자동갱신."),
    ("GRR", "Gross revenue retention — 기존 고객 매출 잔존(확장 제외). Q2 TTM 95%."),
])}
"""


def build_html(charts: dict[str, Path], *, compete_html: str = "") -> str:
    css = f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"RDVT 수익구조분석 {ASOF} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 6px; color:#0e7490; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #0e7490; padding-bottom:3px; color:#1e3a5f; }}
    h3 {{ font-size:10.5pt; margin:10px 0 4px; color:#0e7490; }}
    .cover {{ page-break-after:always; min-height:230mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center;
      background:linear-gradient(165deg,#ecfeff 0%,#e0f2fe 50%,#ffedd5 100%);
      padding:24px; border-radius:8px; }}
    .tag {{ display:inline-block; background:#cffafe; padding:2px 7px; border-radius:3px; font-size:8pt; margin:2px; }}
    .tag.warn {{ background:#fde68a; }}
    .tag.bad {{ background:#fecdd3; }}
    .tag.good {{ background:#bbf7d0; }}
    table {{ width:100%; border-collapse:collapse; font-size:8.5pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:4px 6px; vertical-align:top; }}
    th {{ background:#0e7490; color:#fff; }}
    img {{ max-width:100%; height:auto; margin:6px 0 8px; }}
    figcaption {{ font-size:8pt; color:#57534e; margin-bottom:8px; }}
    .easy {{ background:#ecfeff; border-left:4px solid #0e7490; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
    .gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
    .gloss-title {{ font-weight:700; color:#0e7490; margin-bottom:4px; font-size:9pt; }}
    .gloss ul {{ margin:0 0 0 14px; }}
    .gloss .term {{ font-weight:700; color:#0e7490; }}
    .box {{ background:#fffbeb; border:1px solid #d97706; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    .kpis {{ width:92%; margin:18px auto 0; border-collapse:separate; border-spacing:8px; }}
    .kpis td {{ background:#fff; border:1px solid #cbd5e1; padding:8px 10px; width:25%;
      text-align:center; vertical-align:middle; }}
    .kpis .l {{ font-size:7.5pt; color:#64748b; }}
    .kpis .v {{ font-size:12pt; font-weight:700; color:#0e7490; }}
    .kpis .s {{ font-size:7.5pt; color:#c2410c; }}
    """

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>RDVT 수익구조분석</title><style>{css}</style></head>
<body>
<section class="cover">
  <h1>RDVT 수익구조분석</h1>
  <p style="font-size:12pt;color:#444;margin-top:10px">Red Violet · 신원 인텔리전스 (IDI / idiCORE + FOREWARN)</p>
  <p style="margin-top:18px;color:#555">기준일 {ASOF} · Q2'26 10-Q · 다음 실적 {EARN} · 시총 ~$1.25B</p>
  <table class="kpis">
    <tr>
      <td><div class="l">현재가</div><div class="v">${PX:.2f}</div><div class="s">52주고 ${H52:.2f}</div></td>
      <td><div class="l">PT 평균</div><div class="v">${PT:.0f}</div><div class="s">업사이드 {UPSIDE*100:+.1f}%</div></td>
      <td><div class="l">Q2 매출</div><div class="v">$26.7M</div><div class="s">+23% YoY</div></td>
      <td><div class="l">Adj EBITDA</div><div class="v">$11.2M</div><div class="s">마진 42%</div></td>
    </tr>
  </table>
  <p style="margin-top:18px">
    <span class="tag">Chase 중</span>
    <span class="tag warn">고점 {NEAR*100:.0f}% · 눌림</span>
    <span class="tag">다음 실적 {EARN}</span>
    <span class="tag">미보유</span>
  </p>
</section>

<h2>0. 한줄 Thesis</h2>
<p><b>돈은 클라우드 신원 그래프(CORE)를 IDI 조사 라이선스와 FOREWARN 안전앱으로 팔아, 약정 77%·잔존 95%의 반복 매출로 남긴다.</b>
Q2'26: 매출 $26.7M(+23%) · GAAP GP 76% · Adj GP 86% · Adj EBITDA $11.2M(42%) · GAAP NI $5.0M · 논GAAP EPS $0.50 (Est $0.34 Beat).
IDI 고객 10,869(+447 분기 기록) · FOREWARN 유저 443,173 · 협회 660곳(전미 ~절반) 100% 갱신.
무차입 · Q2 현금 $50M + 8월 증자 순 $109M ≈ $160M. 주가는 고점 −4.6% · PT +8.2% — <b>미보유 · 눌림 관찰</b>.</p>
{fig_block(charts['flow'], '비즈니스 플로우')}
<div class="easy"><b>쉽게:</b> 은행·보험·경찰·추심이 “상대가 누구인지”를 확인할 때, 부동산 중개인이 낯선 손님을 만나기 전에
RDVT가 사람·사업체·자산의 연결을 실시간으로 보여준다. 뷰로(신용점수)가 아니라 <b>신원 그래프 조회 구독</b>이 본체다.
상장 이후 31분기 연속 두 자릿수 성장(이 중 22분기는 +20%↑).</div>
{gloss([
    ("CORE", "클라우드 네이티브·AI 임베디드 신원 그래프. IDI와 FOREWARN의 공통 엔진."),
    ("IDI", "기업용 조사·실사·사기방지 브랜드. 플래그십은 idiCORE."),
    ("FOREWARN", "대면 전 신원·위험 확인 앱. 부동산이 본체, 홈헬스케어로 확장."),
])}

<h2>1. 어디서 돈이 오나</h2>
{fig_block(charts['segmix'], '계약 vs 거래 · 브랜드 스케일')}
{fig_block(charts['growth'], '성장 브리지')}
<table>
  <tr><th>항목</th><th>Q2'26</th><th>YoY / 메모</th><th>의미</th></tr>
  <tr><td><b>Total revenue</b></td><td>$26.7M</td><td>+23% vs $21.8M</td><td>분기 최고 · 31연속 두 자릿수</td></tr>
  <tr><td>계약(약정) 매출</td><td>77%</td><td>전년 동일 77%</td><td>연간+ 자동갱신 본체</td></tr>
  <tr><td>거래(건별) 매출</td><td>23%</td><td>idiVERIFIED &lt;3%</td><td>랜딩 후 약정 전환</td></tr>
  <tr><td>GAAP GP / 마진</td><td>$20.2M / 76%</td><td>전년 72%</td><td>+29% / +4pp</td></tr>
  <tr><td>Adj GP / 마진</td><td>$22.9M / 86%</td><td>전년 84%</td><td>내부SW 상각 가산</td></tr>
  <tr><td>GAAP OP / NI</td><td>$6.1M / $5.0M</td><td>OP 23% · NI 19%</td><td>전년 OP $2.8M · NI $2.7M</td></tr>
  <tr><td>Adj EBITDA</td><td>$11.2M</td><td>마진 42% (전년 35%)</td><td>+48% · 분기 최고</td></tr>
  <tr><td>Adj NI / EPS</td><td>$7.2M / $0.50</td><td>Est $0.34 · Beat +49%</td><td>희석 1,446만주</td></tr>
  <tr><td>OCF / FCF</td><td>$10.6M / $7.2M</td><td>OCF +42%</td><td>캡ex+자본화무형 $3.5M</td></tr>
</table>
<p class="small">GAAP 세그먼트는 단일(identity and information solutions). 브랜드 달러 스플릿은 미공시.
출처: RDVT 10-Q 기간종료 2026-06-30 · 8/10/26 earnings + EX-99.1/99.2.</p>
<div class="easy"><b>쉽게:</b> 이름표는 “소프트웨어”지만 성장 엔진은 두 갈래다.
<b>IDI</b>는 금융·보험·수사·추심 조직(고객 1.09만, 분기 +447 기록)이 워크플로에 붙는 구독.
<b>FOREWARN</b>은 부동산 협회 네트워크(유저 44.3만, 협회 660)가  vis-a-vis 안전을 표준으로 만드는 B2B2C.
콜: IDI 5개 버티컬 중 4개가 분기 최고 · 조사(Investigative)가 % 성장 1위 · 추심 +20% · IDI 부동산만 소폭 감소.</div>
{gloss([
    ("Land and expand", "시험·소액 거래로 들어가 부서·용도·지역으로 확장. 약정 전환이 목표."),
    ("K자 수요", "고소득 거래↑ → 금융·보험·스크리닝 / 스트레스↑ → 추심·수사. 양 끝 동시 수요."),
])}

{compete_html}

<h2>2. 마진 · 레버리지 · 현금</h2>
{fig_block(charts['pnl'], '마진')}
{fig_block(charts['leverage'], '현금·부채')}
<ul>
  <li>매출 $26.718M · COGS(감가상각 제외) $3.818M · S&amp;M $5.750M · G&amp;A $8.268M · D&amp;A $2.787M</li>
  <li>인건비(세그먼트) $8.635M · SBC $2.222M · 데이터 라이선스 원가 $2.443M</li>
  <li>최대 데이터 공급자 = 데이터 취득원가의 <b>46%</b> (Q2'25도 46%) · 계약 2031-04-30까지 연장(25-05-01 개정)</li>
  <li>현금 $50.0M (6/30) · 이자부 부채 0 · 리스 $2.6M · 순현금</li>
  <li>8월 증자 1,916,667주 순대금 ~$109M → 콜 기준 현금 <b>$160M+</b> · M&amp;A 워체스트</li>
  <li>YTD 자사주 74,500주 · 평균 $41.87 · 잔여 한도 $15.5M (증자 전 기준)</li>
  <li>1H 매출 $52.5M · NI $9.3M · 콜: FY Adj EBITDA 마진 <b>high-thirties</b> (Q4 인센티브 시즌↓)</li>
</ul>

<h2>3. 전망 · 시나리오</h2>
{fig_block(charts['guide'], 'Q3 컨센서스 · 마진 방향')}
{fig_block(charts['scen'], '주가 시나리오')}
<table>
  <tr><th>드라이버</th><th>내용</th></tr>
  <tr><td>Q3 컨센</td><td>매출 $26.9–27.4M (평균 $27.2M) · EPS $0.42 · 실적일 2026-11-04</td></tr>
  <tr><td>IDI</td><td>금융·기업리스크 분산성장 · 백그라운드 스크리닝 아웃사이즈 · 수사 전 산업 두 자릿수</td></tr>
  <tr><td>FOREWARN</td><td>부동산 표준 + 홈헬스케어(케어기버 ~4M, Medicare 인증기관 1.2만+) · 협회 갱신 100%</td></tr>
  <tr><td>AI 5축</td><td>리스크시그널 · 비정형 수집 · NL 인터페이스 · 내부 자동화 · 개발가속 (콜)</td></tr>
  <tr><td>밸류</td><td>${PX:.2f} · PT ${PT:.0f} (H $90 / L $73) · 52주 ${L52:.2f}–${H52:.2f} · 업사이드 {UPSIDE*100:+.1f}% · EV/S ~10–12x</td></tr>
</table>
<table>
  <tr><th>시나리오</th><th>밴드</th><th>가정</th></tr>
  <tr><td>Bear</td><td>$45–58</td><td>GRR 추가 하락 · 데이터 공급 충격 · 증자 희석 + 멀티플 수축</td></tr>
  <tr><td>Base</td><td>$70–88</td><td>Q3 컨센 근접 · 마진 high-30s · 현재가가 이 밴드 안</td></tr>
  <tr><td>Bull</td><td>$95–120</td><td>홈헬스케어 트래션 · 전략 M&amp;A · PT 재평가</td></tr>
</table>

<h2>4. 촉매 · 포트 실행</h2>
{fig_block(charts['cat'], '촉매')}
{fig_block(charts['pos'], '포지션 맵')}
<div class="box">
<b>OS 메모 (10-05 포폴 · 10-08 심층)</b><br/>
<b>미보유</b> · 10-08 심층 Chase <b>중</b> · 엔트리 <b>눌림</b>.<br/>
현재 ${PX:.2f} · 컨센서스 PT ${PT:.0f} (업사이드 {UPSIDE*100:+.1f}%) · 52주 ${L52:.2f}–${H52:.2f} (고점 −{(1-PX/H52)*100:.1f}%).<br/>
실행: <b>추격보다 눌림</b>. 다음 실적 <b>2026-11-04</b> (아직 EARN_D5 아님).<br/>
게이트: Q3 매출/마진 · FOREWARN 홈헬스 · IDI 고객 순증 · GRR · 데이터 공급 안정 · 증자 이후 자본배분.
</div>
<div class="easy"><b>한줄 결론:</b> 수익구조는 <u>약정 77% + 잔존 95% + 높은 한계이익(Adj GP 86%)</u>.
Q2는 성장·마진·현금이 같이 올랐다. 다만 <b>지금 자리(고점 95% · 업사이드 +8% · Chase 중)</b>는 추격 자리가 아니다. 관망·눌림.</div>

<h2>부록 · 출처</h2>
<p class="small">
Red Violet Q2 2026 10-Q (기간 종료 2026-06-30) / Exhibit 99.1 earnings / Exhibit 99.2 call (발표 2026-08-10) ·
yfinance 가격·PT·Q3 컨센 ({ASOF}). 피어 믹스·점유는 추정(투자 권유 아님).
</p>
<p class="small">생성: 수익구조분석() · 티커 RDVT · 기준 {ASOF} · WeasyPrint + NanumGothic · sepa.rev_compete · sepa.rev_price_chart</p>
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
    bundle, cpaths = build_compete_charts("RDVT", CHART_DIR)
    charts.update(cpaths)
    compete_html = _compete_section(charts, bundle)
    html_doc = build_html(charts, compete_html=compete_html)
    html_doc, _px = build_and_insert_price("RDVT", CHART_DIR, html_doc)
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

        tag = "sepa-rev-rdvt"
        notes = (
            f"## RDVT 수익구조분석 ({ASOF})\n\n"
            f"Red Violet · 신원 인텔리전스 (IDI + FOREWARN) · Q2'26.\n\n"
            f"- Rev $26.7M (+23%) · GP 76% · Adj EBITDA $11.2M (42%)\n"
            f"- 계약 77% / 거래 23% · GRR 95% · IDI 10,869 · FOREWARN 443k\n"
            f"- 무차입 · 현금 $50M + 8월 증자 $109M ≈ $160M\n"
            f"- 미보유 · Chase 중 · 업사이드 {UPSIDE*100:+.1f}% "
            f"(PT ${PT:.0f} · px ${PX:.2f})\n"
            f"- 눌림 관찰 · 다음 실적 2026-11-04\n"
        )
        rel = publish_github_release_asset(
            OUT_PDF[1],
            tag=tag,
            title="SEPA Revenue Structure — RDVT",
            notes=notes,
        )
        print_release_result(rel, label="수익구조분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
