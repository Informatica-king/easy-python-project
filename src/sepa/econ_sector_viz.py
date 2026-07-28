"""Sector weight + daily change treemap for 경제뉴스() PDF.

Visual: left ranking table (비중·등락) + right treemap (area=AUM weight, color=chg%).
Color convention matches Korean market heatmaps: red=up, blue=down.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import squarify
import yfinance as yf

from sepa.econ_news_data import SECTOR_ETFS, BarSnap, _hist, _snap_from_hist

logger = logging.getLogger(__name__)

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

# Fallback AUM (USD) if yfinance totalAssets missing — relative scale only
_FALLBACK_AUM = {
    "XLK": 1.24e11,
    "XLF": 5.14e10,
    "XLE": 3.57e10,
    "XLV": 4.06e10,
    "XLI": 3.40e10,
    "XLY": 2.26e10,
    "XLP": 1.36e10,
    "XLU": 2.31e10,
    "XLB": 8.17e9,
    "XLRE": 8.10e9,
    "XLC": 2.23e10,
}


@dataclass
class SectorBoardRow:
    ticker: str
    name: str
    close: float
    change_pct: float
    aum: float
    weight: float  # 0–1 share of total AUM in board


def _setup_font() -> tuple:
    fm.fontManager.addfont(FONT_REG)
    fm.fontManager.addfont(FONT_BOLD)
    prop = fm.FontProperties(fname=FONT_REG)
    prop_b = fm.FontProperties(fname=FONT_BOLD)
    plt.rcParams["font.family"] = prop.get_name()
    plt.rcParams["axes.unicode_minus"] = False
    return prop, prop_b


def _fetch_aum(ticker: str) -> float:
    try:
        info = yf.Ticker(ticker).info or {}
        aum = info.get("totalAssets")
        if aum and float(aum) > 0:
            return float(aum)
    except Exception as exc:  # noqa: BLE001
        logger.debug("aum fail %s: %s", ticker, exc)
    return float(_FALLBACK_AUM.get(ticker, 1e10))


def collect_sector_board(session: date, mapping: dict[str, str] | None = None) -> list[SectorBoardRow]:
    """GICS Select Sector ETFs: latest-session change + AUM weight."""
    mapping = mapping or SECTOR_ETFS
    rows: list[SectorBoardRow] = []
    for t, name in mapping.items():
        try:
            df = _hist(t)
            snap = _snap_from_hist(t, name, df, session)
            if snap is None:
                continue
            aum = _fetch_aum(t)
            rows.append(
                SectorBoardRow(
                    ticker=t,
                    name=name,
                    close=snap.close,
                    change_pct=snap.change_pct,
                    aum=aum,
                    weight=0.0,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("sector board fail %s: %s", t, exc)
    total = sum(r.aum for r in rows) or 1.0
    for r in rows:
        r.weight = r.aum / total
    rows.sort(key=lambda x: x.weight, reverse=True)
    return rows


def _kr_heat_cmap() -> mcolors.LinearSegmentedColormap:
    """Korean heatmap: blue (down) → gray (flat) → red (up)."""
    return mcolors.LinearSegmentedColormap.from_list(
        "kr_heat",
        [
            "#08306b",  # -10
            "#2171b5",  # -5
            "#6baed6",  # -3
            "#c6dbef",  # -1
            "#e8e8e8",  # 0
            "#fcae91",  # +1
            "#fb6a4a",  # +3
            "#cb181d",  # +5
            "#67000d",  # +10
        ],
    )


def _chg_to_color(chg_pct: float, vmax: float = 0.05) -> str:
    """Map daily return to hex; clip at ±vmax (default ±5%)."""
    cmap = _kr_heat_cmap()
    x = max(-vmax, min(vmax, chg_pct)) / vmax  # -1..1
    # cmap expects 0..1; map -1→0, 0→0.5, +1→1
    return mcolors.to_hex(cmap((x + 1) / 2))


def _fmt_aum_krw_style(total_usd: float) -> str:
    """Human label for total board AUM in USD trillions."""
    if total_usd >= 1e12:
        return f"${total_usd / 1e12:.2f}T"
    if total_usd >= 1e9:
        return f"${total_usd / 1e9:.1f}B"
    return f"${total_usd:,.0f}"


def render_sector_board_figure(
    board: list[SectorBoardRow],
    session: date,
    out_path: Path,
    *,
    top_n: int = 11,
) -> Path:
    """Table (left) + treemap (right) → PNG for PDF embed."""
    prop, prop_b = _setup_font()
    board = board[:top_n]
    if not board:
        raise ValueError("empty sector board")

    fig = plt.figure(figsize=(11.2, 5.6), facecolor="#f7f8fa")
    # left table axes, right treemap
    ax_t = fig.add_axes([0.04, 0.12, 0.38, 0.78])
    ax_m = fig.add_axes([0.46, 0.12, 0.50, 0.78])
    ax_leg = fig.add_axes([0.46, 0.02, 0.50, 0.07])

    total_aum = sum(r.aum for r in board)
    ax_t.axis("off")
    ax_t.set_xlim(0, 10)
    ax_t.set_ylim(-0.5, len(board) + 1.8)
    ax_t.text(
        0,
        len(board) + 1.2,
        "GICS 섹터 시총(ETF AUM) TOP",
        fontproperties=prop_b,
        fontsize=11,
        color="#1e3a5f",
    )
    ax_t.text(
        0,
        len(board) + 0.55,
        f"전체 섹터ETF 합계 {_fmt_aum_krw_style(total_aum)} · 세션 {session.isoformat()}",
        fontproperties=prop,
        fontsize=7.5,
        color="#57534e",
    )
    # header
    headers = [(0.1, "#"), (1.0, "업종"), (4.2, "비중"), (7.2, "등락률")]
    for x, h in headers:
        ax_t.text(x, len(board) + 0.05, h, fontproperties=prop_b, fontsize=8, color="#64748b")

    for i, r in enumerate(board):
        y = len(board) - 1 - i
        chg = r.change_pct * 100
        col = "#cb181d" if chg >= 0 else "#2171b5"
        ax_t.text(0.1, y, str(i + 1), fontproperties=prop, fontsize=8, va="center", color="#334155")
        ax_t.text(1.0, y, r.name, fontproperties=prop_b, fontsize=8.5, va="center", color="#1c1917")
        ax_t.text(1.0, y - 0.28, r.ticker, fontproperties=prop, fontsize=6.5, va="center", color="#94a3b8")
        # weight bar
        bar_w = max(0.15, r.weight * 2.6)
        ax_t.add_patch(
            plt.Rectangle((4.2, y - 0.18), bar_w, 0.36, facecolor="#94a3b8", edgecolor="none", alpha=0.85)
        )
        ax_t.text(4.2 + bar_w + 0.12, y, f"{r.weight * 100:.1f}%", fontproperties=prop, fontsize=8, va="center")
        ax_t.text(7.2, y, f"{chg:+.2f}%", fontproperties=prop_b, fontsize=9, va="center", color=col)

    # treemap
    sizes = [max(r.weight, 0.005) for r in board]
    labels = [f"{r.name}\n{r.change_pct * 100:+.2f}%" for r in board]
    colors = [_chg_to_color(r.change_pct) for r in board]
    normed = squarify.normalize_sizes(sizes, 100, 100)
    rects = squarify.squarify(normed, 0, 0, 100, 100)
    ax_m.set_xlim(0, 100)
    ax_m.set_ylim(0, 100)
    ax_m.set_aspect("equal")
    ax_m.axis("off")
    ax_m.set_title("등락 히트맵 (면적=AUM 비중)", fontproperties=prop_b, fontsize=10, color="#1e3a5f", pad=4)
    for rect, label, color, r in zip(rects, labels, colors, board):
        x, y, dx, dy = rect["x"], rect["y"], rect["dx"], rect["dy"]
        ax_m.add_patch(
            plt.Rectangle((x, y), dx, dy, facecolor=color, edgecolor="white", linewidth=2.2)
        )
        if dx * dy > 35:  # enough area for text
            tc = "white" if abs(r.change_pct) >= 0.015 else "#1c1917"
            fs = 8 if dx * dy > 80 else 6.5
            ax_m.text(
                x + dx / 2,
                y + dy / 2,
                label,
                ha="center",
                va="center",
                fontproperties=prop_b,
                fontsize=fs,
                color=tc,
            )

    # legend strip
    ax_leg.axis("off")
    stops = [-0.10, -0.05, -0.03, -0.01, -0.005, 0.0, 0.005, 0.01, 0.03, 0.05, 0.10]
    n = len(stops) - 1
    for i in range(n):
        mid = (stops[i] + stops[i + 1]) / 2
        ax_leg.add_patch(
            plt.Rectangle((i / n, 0.35), 1 / n, 0.45, facecolor=_chg_to_color(mid, vmax=0.10), edgecolor="white", lw=0.5)
        )
        if i % 2 == 0 or stops[i] == 0:
            ax_leg.text(i / n, 0.05, f"{stops[i] * 100:.0f}%", fontproperties=prop, fontsize=6, ha="left", color="#57534e")
    ax_leg.text(1.0, 0.05, "+10%", fontproperties=prop, fontsize=6, ha="right", color="#57534e")
    ax_leg.set_xlim(0, 1)
    ax_leg.set_ylim(0, 1)
    ax_leg.text(0.0, 0.88, "파랑=하락 · 회색=보합 · 빨강=상승 (한국형 히트맵)", fontproperties=prop, fontsize=7, color="#64748b")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def board_to_data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def bars_from_board(board: list[SectorBoardRow]) -> list[BarSnap]:
    """Compatibility helper if callers want BarSnap-sorted-by-change."""
    out = []
    for r in board:
        out.append(
            BarSnap(
                ticker=r.ticker,
                name=r.name,
                close=r.close,
                prev_close=r.close / (1 + r.change_pct) if r.change_pct != -1 else r.close,
                change_pct=r.change_pct,
                volume=0.0,
                vol_avg20=None,
                vol_ratio=None,
                high=r.close,
                low=r.close,
            )
        )
    return sorted(out, key=lambda x: x.change_pct, reverse=True)
