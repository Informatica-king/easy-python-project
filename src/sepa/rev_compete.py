"""Competitor share + revenue-mix helpers for 수익구조분석().

Two layers (ticker configs in PEER_PROFILES):

1) **Industry share** — curated market-share panels (e.g. CTV device SOV)
   with period-over-period change (pp). Sources cited in profile.

2) **Peer revenue mix** — comparable segment buckets (%) for the ticker
   vs named peers, plus optional TTM revenue scale from yfinance.

Usage::

    from sepa.rev_compete import build_compete_charts, get_profile
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

# ---------------------------------------------------------------------------
# Profiles — extend per ticker used in 수익구조분석
# ---------------------------------------------------------------------------

PEER_PROFILES: dict[str, dict[str, Any]] = {
    "ROKU": {
        "sector_ko": "CTV·스트리밍 플랫폼 (심층: 통신·엔터테인먼트)",
        "share_title": "북미 CTV 디바이스 Share of Voice (프로그램매틱)",
        "share_as_of": "Q1'26 vs Q1'25 · Pixalate",
        "share_note": (
            "Pixalate CTV Device Market Share (프로그램매틱 SOV). "
            "Amazon/Samsung/Apple/LG는 비상장 사업부·복합기업이라 매출점유와 다름 — "
            "OS·디바이스 레이어 경쟁 점유율."
        ),
        "share_rows": [
            # name, current_pct, prior_pct
            ("Roku", 36.0, 38.0),
            ("Amazon Fire TV", 19.0, 18.0),
            ("Samsung Smart TV", 15.0, 12.0),
            ("Apple TV", 13.0, 13.0),
            ("LG", 10.0, 5.0),
        ],
        "share_source": "Pixalate Q1 2026 / Q1 2025 CTV Device Market Share",
        # Revenue mix: same bucket keys for stacked comparison
        "mix_buckets": ["Advertising", "Subscriptions", "Devices/Other"],
        "mix_as_of": "Q1'26 (또는 최근 공시 근사)",
        "mix_rows": [
            # ticker_or_name, display, is_subject, mix dict (must sum ~100), optional yf ticker for TTM
            {
                "key": "ROKU",
                "name": "ROKU",
                "subject": True,
                "yf": "ROKU",
                "mix": {"Advertising": 49.1, "Subscriptions": 41.5, "Devices/Other": 9.4},
                "note": "Q1'26 Ad $613M / Sub $519M / Dev $118M",
            },
            {
                "key": "SPOT",
                "name": "SPOT",
                "subject": False,
                "yf": "SPOT",
                "mix": {"Advertising": 8.5, "Subscriptions": 91.5, "Devices/Other": 0.0},
                "note": "Q1'26 Premium 중심 · Ad-supported 소비중 (근사)",
            },
            {
                "key": "NFLX",
                "name": "NFLX",
                "subject": False,
                "yf": "NFLX",
                "mix": {"Advertising": 6.0, "Subscriptions": 94.0, "Devices/Other": 0.0},
                "note": "구독 본체 · 광고 티어 성장 중(연간 광고~$3B 가이던스 대비 소비중 근사)",
            },
            {
                "key": "FUBO",
                "name": "FUBO",
                "subject": False,
                "yf": "FUBO",
                "mix": {"Advertising": 18.0, "Subscriptions": 82.0, "Devices/Other": 0.0},
                "note": "라이브TV 구독+광고 하이브리드 근사",
            },
        ],
        "mix_note": (
            "버킷은 비교를 위해 Advertising / Subscriptions / Devices·Other로 정규화. "
            "피어는 공시 세그먼트가 달라 근사치 — 방향 비교용."
        ),
    },
    "RELY": {
        "sector_ko": "핀테크·크로스보더 송금 (심층: 금융)",
        "share_title": "글로벌 송금 시장 점유율 (추정)",
        "share_as_of": "2026 est. vs 2025 est. · VMR 계열 근사",
        "share_note": (
            "전 세계 송금(현금·디지털 혼재) 추정 점유율. "
            "정의가 리포트마다 달라 절대치보다 Δpp·상대 순위 비교용. "
            "Remitly는 디지털·지갑 지급 강세, WU는 에이전트 네트워크 규모."
        ),
        "share_rows": [
            ("Western Union", 11.5, 12.0),
            ("Wise", 4.0, 4.2),
            ("Remitly", 2.3, 1.9),
            ("MoneyGram", 2.1, 2.2),
            ("WorldRemit", 1.1, 1.3),
        ],
        "share_source": "Verified Market Research digital remittance share estimates (2026 vs prior)",
        "mix_buckets": ["Consumer Remittance", "Business/Platform", "Other"],
        "mix_as_of": "Q1'26 / 최근 공시 근사",
        "mix_rows": [
            {
                "key": "RELY",
                "name": "RELY",
                "subject": True,
                "yf": "RELY",
                "mix": {"Consumer Remittance": 95.0, "Business/Platform": 5.0, "Other": 0.0},
                "note": "단일세그먼트 · Growth Accelerators(~5% FY26 가이던스) 포함",
            },
            {
                "key": "TW",
                "name": "TW",
                "subject": False,
                "yf": "TW",
                "mix": {"Consumer Remittance": 62.0, "Business/Platform": 38.0, "Other": 0.0},
                "note": "Personal vs Platform/Business 근사 (공시 혼합)",
            },
            {
                "key": "WU",
                "name": "WU",
                "subject": False,
                "yf": "WU",
                "mix": {"Consumer Remittance": 78.0, "Business/Platform": 22.0, "Other": 0.0},
                "note": "Consumer Money Transfer 중심 · B2B/기타 근사",
            },
        ],
        "mix_note": (
            "버킷은 Consumer Remittance / Business·Platform / Other로 정규화. "
            "RELY Growth Accelerators(고액송금·비즈니스·리시버 등)~5%를 Business/Platform에 배치."
        ),
    },
}


@dataclass
class ShareRow:
    name: str
    current: float
    prior: float

    @property
    def delta_pp(self) -> float:
        return self.current - self.prior


@dataclass
class CompeteBundle:
    ticker: str
    sector_ko: str
    share_title: str
    share_as_of: str
    share_note: str
    share_source: str
    share_rows: list[ShareRow]
    mix_buckets: list[str]
    mix_as_of: str
    mix_note: str
    mix_rows: list[dict[str, Any]]
    ttm_revenue: dict[str, float] = field(default_factory=dict)


def get_profile(ticker: str) -> dict[str, Any] | None:
    return PEER_PROFILES.get(ticker.upper())


def _setup_font():
    fm.fontManager.addfont(FONT_REG)
    fm.fontManager.addfont(FONT_BOLD)
    prop = fm.FontProperties(fname=FONT_REG)
    prop_b = fm.FontProperties(fname=FONT_BOLD)
    plt.rcParams["font.family"] = prop.get_name()
    plt.rcParams["axes.unicode_minus"] = False
    return prop, prop_b


def _ttm_revenue(yf_ticker: str) -> float | None:
    try:
        tk = yf.Ticker(yf_ticker)
        # prefer income statement trailing
        fin = tk.financials
        if fin is not None and not fin.empty:
            # first column = most recent annual
            for idx in fin.index:
                if "Total Revenue" in str(idx) or str(idx).lower() == "total revenue":
                    val = fin.loc[idx].iloc[0]
                    if val is not None and not (isinstance(val, float) and np.isnan(val)):
                        return float(val)
        info = tk.info or {}
        # totalRevenue often TTM
        tr = info.get("totalRevenue")
        if tr:
            return float(tr)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ttm revenue fail %s: %s", yf_ticker, exc)
    return None


def load_compete_bundle(ticker: str) -> CompeteBundle | None:
    prof = get_profile(ticker)
    if not prof:
        return None
    share_rows = [ShareRow(n, c, p) for n, c, p in prof["share_rows"]]
    mix_rows = list(prof["mix_rows"])
    ttm: dict[str, float] = {}
    for row in mix_rows:
        yft = row.get("yf")
        if not yft:
            continue
        rev = _ttm_revenue(yft)
        if rev is not None:
            ttm[row["name"]] = rev
    return CompeteBundle(
        ticker=ticker.upper(),
        sector_ko=prof["sector_ko"],
        share_title=prof["share_title"],
        share_as_of=prof["share_as_of"],
        share_note=prof["share_note"],
        share_source=prof["share_source"],
        share_rows=share_rows,
        mix_buckets=list(prof["mix_buckets"]),
        mix_as_of=prof["mix_as_of"],
        mix_note=prof["mix_note"],
        mix_rows=mix_rows,
        ttm_revenue=ttm,
    )


def chart_share_level(bundle: CompeteBundle, out: Path, *, prop, prop_b) -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 4.0))
    names = [r.name for r in bundle.share_rows]
    vals = [r.current for r in bundle.share_rows]
    colors = []
    for n in names:
        hit = (
            n.upper() == bundle.ticker
            or ("Roku" in n and bundle.ticker == "ROKU")
            or ("Remitly" in n and bundle.ticker == "RELY")
        )
        colors.append(("#6c2bd9" if bundle.ticker == "ROKU" else "#0ea5e9") if hit else "#64748b")
    bars = ax.barh(names[::-1], vals[::-1], color=colors[::-1], height=0.55)
    ax.set_xlabel("%", fontproperties=prop)
    ax.set_title(bundle.share_title, fontproperties=prop_b, fontsize=11)
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 0.4, b.get_y() + b.get_height() / 2, f"{v:.0f}%", va="center", fontproperties=prop, fontsize=8)
    ax.set_xlim(0, max(vals) * 1.25)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(prop)
    ax.text(0.99, -0.12, bundle.share_as_of, transform=ax.transAxes, ha="right", fontproperties=prop, fontsize=7, color="#64748b")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def chart_share_delta(bundle: CompeteBundle, out: Path, *, prop, prop_b) -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    names = [r.name for r in bundle.share_rows]
    deltas = [r.delta_pp for r in bundle.share_rows]
    colors = ["#cb181d" if d >= 0 else "#2171b5" for d in deltas]  # KR: red up / blue down
    y = np.arange(len(names))
    ax.barh(y, deltas, color=colors, height=0.55)
    ax.axvline(0, color="#94a3b8", lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontproperties=prop)
    ax.set_xlabel("점유율 변화 (pp)", fontproperties=prop)
    ax.set_title("경쟁 점유율 변화 (현재 - 전년동기)", fontproperties=prop_b, fontsize=11)
    ax.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x:g}".replace("\u2212", "-"))
    )
    for i, d in enumerate(deltas):
        label = f"{d:+.0f}pp".replace("\u2212", "-")
        ax.text(d + (0.15 if d >= 0 else -0.15), i, label, va="center",
                ha="left" if d >= 0 else "right", fontproperties=prop, fontsize=8)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def chart_mix_compare(bundle: CompeteBundle, out: Path, *, prop, prop_b) -> Path:
    buckets = bundle.mix_buckets
    palette = ["#0e7490", "#047857", "#a16207", "#64748b"]
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    labels = [r["name"] for r in bundle.mix_rows]
    x = np.arange(len(labels))
    bottom = np.zeros(len(labels))
    for i, b in enumerate(buckets):
        vals = np.array([float(r["mix"].get(b, 0.0)) for r in bundle.mix_rows])
        ax.bar(x, vals, bottom=bottom, width=0.55, color=palette[i % len(palette)], label=b, edgecolor="white", linewidth=0.6)
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontproperties=prop_b, fontsize=9)
    ax.set_ylabel("매출 구성 %", fontproperties=prop)
    ax.set_ylim(0, 105)
    ax.set_title(f"경쟁사 매출 구조 비율 비교 · {bundle.mix_as_of}", fontproperties=prop_b, fontsize=11)
    ax.legend(prop=prop, fontsize=8, loc="upper right")
    # highlight subject tick label color
    for i, r in enumerate(bundle.mix_rows):
        if r.get("subject"):
            ax.get_xticklabels()[i].set_color("#6c2bd9")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def chart_ttm_scale(bundle: CompeteBundle, out: Path, *, prop, prop_b) -> Path | None:
    if not bundle.ttm_revenue:
        return None
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    names = [r["name"] for r in bundle.mix_rows if r["name"] in bundle.ttm_revenue]
    vals = [bundle.ttm_revenue[n] / 1e9 for n in names]
    colors = ["#6c2bd9" if n == bundle.ticker or any(r["name"] == n and r.get("subject") for r in bundle.mix_rows) else "#94a3b8" for n in names]
    bars = ax.bar(names, vals, color=colors, width=0.55)
    ax.set_ylabel("TTM 매출 ($B)", fontproperties=prop)
    ax.set_title("규모 감각 — TTM 매출 (피어 대비)", fontproperties=prop_b, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.02, f"{v:.1f}", ha="center", fontproperties=prop, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(prop_b)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def build_compete_charts(ticker: str, chart_dir: str | Path) -> tuple[CompeteBundle | None, dict[str, Path]]:
    """Return bundle + chart paths (share, delta, mix, optional ttm)."""
    bundle = load_compete_bundle(ticker)
    if bundle is None:
        return None, {}
    prop, prop_b = _setup_font()
    chart_dir = Path(chart_dir)
    paths = {
        "share": chart_share_level(bundle, chart_dir / "10_compete_share.png", prop=prop, prop_b=prop_b),
        "delta": chart_share_delta(bundle, chart_dir / "11_compete_delta.png", prop=prop, prop_b=prop_b),
        "mix": chart_mix_compare(bundle, chart_dir / "12_compete_mix.png", prop=prop, prop_b=prop_b),
    }
    ttm = chart_ttm_scale(bundle, chart_dir / "13_compete_ttm.png", prop=prop, prop_b=prop_b)
    if ttm is not None:
        paths["ttm"] = ttm
    return bundle, paths
