"""1-year price analysis panels for 수익구조분석() early pages.

Option C (peers excluded), readability-first chart layout:
  - 1y close **line** + MA20/60/150/200 (not full-year daily candles)
  - Recent ~90 sessions as candles (detail zoom)
  - Weekly volume bars
  - Earnings markers, SPY relative strength, RSI(14), swing highs/lows
  - KPI strip + short auto commentary

Usage::

    from sepa.rev_price_chart import build_price_analysis, insert_price_html

    section = build_price_analysis("SBLK", chart_dir)
    html = insert_price_html(html, section.html)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

MA_WINDOWS = (20, 60, 150, 200)
RSI_PERIOD = 14
LOOKBACK_CALENDAR_DAYS = 400  # ~1y trading days after dropna
SWING_ORDER = 5
MAX_SWINGS = 3

C_UP = "#b91c1c"  # KR convention: red up
C_DN = "#1d4ed8"  # blue down
C_MA = {20: "#0ea5e9", 60: "#ca8a04", 150: "#7c3aed", 200: "#0f172a"}
C_VOL = "#94a3b8"
C_VOL_HOT = "#f59e0b"
C_SWING_HI = "#9f1239"
C_SWING_LO = "#166534"
C_EARN = "#c2410c"
C_BENCH = "#64748b"


@dataclass
class PriceKpis:
    last: float
    high_52w: float
    low_52w: float
    pct_from_high: float
    pct_from_low: float
    vs_ma20_pct: float
    vs_ma200_pct: float
    rsi: float
    rel_spy_1y_pct: float
    ticker_1y_pct: float
    spy_1y_pct: float
    above_ma200: bool
    ma20_above_ma60: bool
    next_earn: str | None = None
    vol_surge: bool = False


@dataclass
class PriceSection:
    ticker: str
    html: str
    candle_path: Path | None = None
    momentum_path: Path | None = None
    kpis: PriceKpis | None = None
    commentary: list[str] = field(default_factory=list)
    ok: bool = False
    error: str | None = None


def _setup_font():
    try:
        fm.fontManager.addfont(FONT_REG)
        fm.fontManager.addfont(FONT_BOLD)
        prop = fm.FontProperties(fname=FONT_REG)
        prop_b = fm.FontProperties(fname=FONT_BOLD)
        plt.rcParams["font.family"] = prop.get_name()
    except Exception:  # noqa: BLE001
        prop = fm.FontProperties()
        prop_b = fm.FontProperties(weight="bold")
    plt.rcParams["axes.unicode_minus"] = False
    return prop, prop_b


def _rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _swing_levels(high: pd.Series, low: pd.Series, order: int = SWING_ORDER) -> tuple[list[tuple[pd.Timestamp, float]], list[tuple[pd.Timestamp, float]]]:
    """Simple fractal swings: local max/min over +/- order bars.

    Keeps up to MAX_SWINGS recent levels that are spaced apart in price
    (avoid stacking nearly identical highs/lows).
    """
    hi_vals = high.values
    lo_vals = low.values
    idx = high.index
    swings_hi: list[tuple[pd.Timestamp, float]] = []
    swings_lo: list[tuple[pd.Timestamp, float]] = []
    n = len(hi_vals)
    for i in range(order, n - order):
        window_hi = hi_vals[i - order : i + order + 1]
        window_lo = lo_vals[i - order : i + order + 1]
        if hi_vals[i] == window_hi.max():
            swings_hi.append((idx[i], float(hi_vals[i])))
        if lo_vals[i] == window_lo.min():
            swings_lo.append((idx[i], float(lo_vals[i])))

    def _space(levels: list[tuple[pd.Timestamp, float]], *, descending: bool) -> list[tuple[pd.Timestamp, float]]:
        if not levels:
            return []
        # newest first
        ordered = list(reversed(levels))
        picked: list[tuple[pd.Timestamp, float]] = []
        for ts, price in ordered:
            if not picked:
                picked.append((ts, price))
                continue
            # require >= 3% separation from already picked levels
            if all(abs(price / p - 1.0) >= 0.03 for _, p in picked):
                picked.append((ts, price))
            if len(picked) >= MAX_SWINGS:
                break
        # chronological for labeling stability
        return sorted(picked, key=lambda t: t[0])

    return _space(swings_hi, descending=True), _space(swings_lo, descending=False)


def _fetch_history(ticker: str) -> pd.DataFrame:
    tk = yf.Ticker(ticker)
    hist = tk.history(period="1y", interval="1d", auto_adjust=True)
    if hist is None or hist.empty:
        hist = tk.history(period="18mo", interval="1d", auto_adjust=True)
    if hist is None or hist.empty:
        raise RuntimeError(f"no history for {ticker}")
    hist = hist.rename(columns=str.title)
    need = ["Open", "High", "Low", "Close", "Volume"]
    for c in need:
        if c not in hist.columns:
            raise RuntimeError(f"missing column {c} for {ticker}")
    hist = hist[need].dropna()
    # timezone-naive for matplotlib
    if getattr(hist.index, "tz", None) is not None:
        hist.index = hist.index.tz_localize(None)
    return hist


def _earnings_dates(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> tuple[list[pd.Timestamp], pd.Timestamp | None]:
    past: list[pd.Timestamp] = []
    nxt: pd.Timestamp | None = None
    tk = yf.Ticker(ticker)
    try:
        ed = tk.get_earnings_dates(limit=12)
        if ed is not None and not ed.empty:
            for ts in ed.index:
                t = pd.Timestamp(ts)
                if getattr(t, "tz", None) is not None:
                    t = t.tz_localize(None)
                t = t.normalize()
                if start <= t <= end:
                    past.append(t)
                elif t > end and (nxt is None or t < nxt):
                    nxt = t
    except Exception as exc:  # noqa: BLE001
        logger.warning("earnings_dates fail %s: %s", ticker, exc)
    try:
        cal = tk.calendar
        if isinstance(cal, dict):
            raw = cal.get("Earnings Date")
            if isinstance(raw, list) and raw:
                t = pd.Timestamp(raw[0]).normalize()
                if getattr(t, "tzinfo", None) is not None:
                    t = t.tz_localize(None) if hasattr(t, "tz_localize") else t.replace(tzinfo=None)
                if t > end:
                    nxt = t if nxt is None else min(nxt, t)
                elif start <= t <= end and t not in past:
                    past.append(t)
        elif isinstance(cal, pd.DataFrame) and not cal.empty:
            # older yfinance shape
            if "Earnings Date" in cal.index:
                val = cal.loc["Earnings Date"].iloc[0]
                t = pd.Timestamp(val).normalize()
                if t > end:
                    nxt = t if nxt is None else min(nxt, t)
    except Exception as exc:  # noqa: BLE001
        logger.warning("calendar fail %s: %s", ticker, exc)
    past = sorted(set(past))
    return past, nxt


def _prepare_frame(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame, list[pd.Timestamp], pd.Timestamp | None]:
    px = _fetch_history(ticker)
    spy = _fetch_history("SPY")
    # align spy to px index (ffill)
    spy = spy.reindex(px.index, method="ffill")
    for w in MA_WINDOWS:
        px[f"MA{w}"] = px["Close"].rolling(w).mean()
    px["RSI"] = _rsi(px["Close"])
    px["VolMA20"] = px["Volume"].rolling(20).mean()
    # relative strength: cumulative return ratio vs first common valid
    base_px = float(px["Close"].iloc[0])
    base_spy = float(spy["Close"].iloc[0]) if not spy["Close"].isna().all() else np.nan
    px["Ret"] = px["Close"] / base_px - 1.0
    spy["Ret"] = spy["Close"] / base_spy - 1.0
    px["RelSPY"] = (1 + px["Ret"]) / (1 + spy["Ret"]) - 1.0
    past_e, next_e = _earnings_dates(ticker, px.index[0], px.index[-1])
    return px, spy, past_e, next_e


def compute_kpis(
    px: pd.DataFrame,
    spy: pd.DataFrame,
    next_earn: pd.Timestamp | None,
) -> PriceKpis:
    last = float(px["Close"].iloc[-1])
    hi = float(px["High"].max())
    lo = float(px["Low"].min())
    ma20 = float(px["MA20"].iloc[-1]) if pd.notna(px["MA20"].iloc[-1]) else last
    ma60 = float(px["MA60"].iloc[-1]) if pd.notna(px["MA60"].iloc[-1]) else last
    ma200 = float(px["MA200"].iloc[-1]) if pd.notna(px["MA200"].iloc[-1]) else last
    rsi = float(px["RSI"].iloc[-1]) if pd.notna(px["RSI"].iloc[-1]) else 50.0
    t_ret = float(px["Ret"].iloc[-1]) * 100
    s_ret = float(spy["Ret"].iloc[-1]) * 100 if pd.notna(spy["Ret"].iloc[-1]) else 0.0
    rel = float(px["RelSPY"].iloc[-1]) * 100 if pd.notna(px["RelSPY"].iloc[-1]) else t_ret - s_ret
    vol_surge = False
    if pd.notna(px["VolMA20"].iloc[-1]) and px["VolMA20"].iloc[-1] > 0:
        vol_surge = float(px["Volume"].iloc[-1]) > 1.5 * float(px["VolMA20"].iloc[-1])
    nxt = next_earn.strftime("%Y-%m-%d") if next_earn is not None else None
    return PriceKpis(
        last=last,
        high_52w=hi,
        low_52w=lo,
        pct_from_high=(last / hi - 1.0) * 100,
        pct_from_low=(last / lo - 1.0) * 100,
        vs_ma20_pct=(last / ma20 - 1.0) * 100,
        vs_ma200_pct=(last / ma200 - 1.0) * 100,
        rsi=rsi,
        rel_spy_1y_pct=rel,
        ticker_1y_pct=t_ret,
        spy_1y_pct=s_ret,
        above_ma200=last >= ma200,
        ma20_above_ma60=ma20 >= ma60,
        next_earn=nxt,
        vol_surge=vol_surge,
    )


def build_commentary(k: PriceKpis, swings_hi, swings_lo) -> list[str]:
    lines: list[str] = []
    trend = "장기 이평(MA200) 위 — 대세 상승 구간" if k.above_ma200 else "장기 이평(MA200) 아래 — 대세 약세/회복 대기"
    mid = "MA20 > MA60 (중기 상승 정렬)" if k.ma20_above_ma60 else "MA20 < MA60 (중기 하락/조정)"
    lines.append(f"추세: {trend}. {mid}.")
    lines.append(
        f"위치: 현재 ${k.last:.2f} · 1년 고점 대비 {k.pct_from_high:+.1f}% · "
        f"MA20 {k.vs_ma20_pct:+.1f}% · MA200 {k.vs_ma200_pct:+.1f}%."
    )
    rsi_note = "과열권 근접" if k.rsi >= 70 else ("과매도권 근접" if k.rsi <= 30 else "중립 구간")
    lines.append(
        f"모멘텀: RSI {k.rsi:.0f} ({rsi_note}). "
        f"1년 수익률 종목 {k.ticker_1y_pct:+.1f}% / SPY {k.spy_1y_pct:+.1f}% "
        f"(상대 {k.rel_spy_1y_pct:+.1f}%p)."
    )
    if swings_hi or swings_lo:
        parts = []
        if swings_hi:
            parts.append("저항 " + ", ".join(f"${p:.2f}" for _, p in swings_hi))
        if swings_lo:
            parts.append("지지 " + ", ".join(f"${p:.2f}" for _, p in swings_lo))
        lines.append("스윙 레벨: " + " · ".join(parts) + ".")
    if k.next_earn:
        lines.append(f"다음 실적(추정): {k.next_earn}. 이벤트 직전 추격은 리스크 큼.")
    if abs(k.pct_from_high) <= 5:
        lines.append("주의: 52주(1년) 고점 근접 — 수익구조와 별개로 추격 진입 비추.")
    if k.vol_surge:
        lines.append("참고: 최근 일 거래량이 20일 평균 대비 급증.")
    return lines


RECENT_CANDLE_DAYS = 90


def _draw_candles(ax, df: pd.DataFrame, *, width: float = 0.6) -> None:
    x = mdates.date2num(df.index.to_pydatetime())
    for i, (_, row) in enumerate(df.iterrows()):
        o, h, l, c = float(row.Open), float(row.High), float(row.Low), float(row.Close)
        col = C_UP if c >= o else C_DN
        ax.vlines(x[i], l, h, color=col, linewidth=0.8, zorder=2)
        bottom = min(o, c)
        height = abs(c - o) or (h - l) * 0.02 or 0.01
        ax.add_patch(
            plt.Rectangle(
                (x[i] - width / 2, bottom), width, height,
                facecolor=col, edgecolor=col, linewidth=0.35, zorder=3,
            )
        )
    return x


def _weekly_volume(px: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily volume to weekly bars (Fri). Color by week close vs open."""
    w = pd.DataFrame(
        {
            "Volume": px["Volume"].resample("W-FRI").sum(),
            "Open": px["Open"].resample("W-FRI").first(),
            "Close": px["Close"].resample("W-FRI").last(),
        }
    ).dropna(subset=["Volume"])
    return w


def chart_candle_volume(
    px: pd.DataFrame,
    past_earnings: list[pd.Timestamp],
    next_earn: pd.Timestamp | None,
    swings_hi,
    swings_lo,
    out: Path,
    *,
    ticker: str,
    prop,
    prop_b,
) -> Path:
    """1y line+MA overview, recent candles zoom, weekly volume."""
    fig = plt.figure(figsize=(9.4, 7.2))
    gs = fig.add_gridspec(3, 1, height_ratios=[2.6, 1.6, 0.9], hspace=0.08)
    ax = fig.add_subplot(gs[0])
    ax_c = fig.add_subplot(gs[1])
    ax_v = fig.add_subplot(gs[2], sharex=ax)

    x = mdates.date2num(px.index.to_pydatetime())
    close = px["Close"].values
    ax.plot(x, close, color="#0c4a6e", lw=1.6, label="종가", zorder=5)
    ax.fill_between(x, close, close.min() * 0.995, color="#0c4a6e", alpha=0.08, zorder=0)

    for w, col in C_MA.items():
        s = px[f"MA{w}"]
        ax.plot(x, s.values, color=col, lw=1.2 if w >= 150 else 1.05, label=f"MA{w}", zorder=4)

    for _, price in swings_hi:
        ax.axhline(price, color=C_SWING_HI, lw=0.8, ls="--", alpha=0.7, zorder=1)
        ax.text(x[-1], price, f"  H ${price:.2f}", color=C_SWING_HI, fontsize=7, fontproperties=prop, va="bottom")
    for _, price in swings_lo:
        ax.axhline(price, color=C_SWING_LO, lw=0.8, ls="--", alpha=0.7, zorder=1)
        ax.text(x[-1], price, f"  L ${price:.2f}", color=C_SWING_LO, fontsize=7, fontproperties=prop, va="top")

    for ed in past_earnings:
        if ed < px.index[0] or ed > px.index[-1]:
            continue
        loc = px.index.searchsorted(ed)
        if loc >= len(x):
            continue
        ax.axvline(x[min(loc, len(x) - 1)], color=C_EARN, lw=0.7, alpha=0.5, zorder=1)
    if past_earnings:
        ax.plot([], [], color=C_EARN, lw=1.2, label="실적일")

    ax.set_ylabel("가격 ($)", fontproperties=prop)
    ax.set_title(
        f"{ticker} 최근 1년 종가·이평 (일봉 풀캔들 대신 라인) · 스윙 고저",
        fontproperties=prop_b, fontsize=11,
    )
    ax.legend(loc="upper left", fontsize=7, prop=prop, ncol=3, framealpha=0.9)
    ax.grid(True, alpha=0.25)
    plt.setp(ax.get_xticklabels(), visible=False)

    # --- recent candles (readable zoom) ---
    recent = px.iloc[-RECENT_CANDLE_DAYS:]
    _draw_candles(ax_c, recent, width=0.55)
    xr = mdates.date2num(recent.index.to_pydatetime())
    for w, col in C_MA.items():
        ax_c.plot(xr, recent[f"MA{w}"].values, color=col, lw=1.0, alpha=0.95)
    # shade recent window on overview via vertical span hint
    ax.axvspan(xr[0], xr[-1], color="#0369a1", alpha=0.06, zorder=0)
    ax_c.set_ylabel("가격 ($)", fontproperties=prop)
    ax_c.set_title(
        f"최근 {len(recent)}거래일 일봉 확대 (단기 진입·손절 감각)",
        fontproperties=prop_b, fontsize=10,
    )
    ax_c.grid(True, alpha=0.25)
    ax_c.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax_c.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    for lbl in ax_c.get_xticklabels():
        lbl.set_fontproperties(prop)
        lbl.set_fontsize(7)

    # --- weekly volume ---
    weekly = _weekly_volume(px)
    xw = mdates.date2num(weekly.index.to_pydatetime())
    vol_colors = [
        C_UP if float(r.Close) >= float(r.Open) else C_DN
        for _, r in weekly.iterrows()
    ]
    ax_v.bar(xw, weekly["Volume"].values, width=4.0, color=vol_colors, alpha=0.75, align="center")
    # weekly vol MA (~20 weeks ≈ 100 trading days — use 8w for short signal)
    vol_ma = weekly["Volume"].rolling(8, min_periods=3).mean()
    ax_v.plot(xw, vol_ma.values, color="#334155", lw=0.95, label="Vol MA8w")
    ax_v.set_ylabel("주간 거래량", fontproperties=prop)
    ax_v.legend(loc="upper left", fontsize=7, prop=prop)
    ax_v.grid(True, alpha=0.2)
    ax_v.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax_v.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    for lbl in ax_v.get_xticklabels():
        lbl.set_fontproperties(prop)
        lbl.set_fontsize(8)
    ax_v.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K")
    )

    if next_earn is not None:
        fig.text(
            0.99, 0.01, f"다음 실적(추정) {next_earn.strftime('%Y-%m-%d')}",
            ha="right", fontsize=7, fontproperties=prop, color=C_EARN,
        )

    fig.subplots_adjust(left=0.08, right=0.98, top=0.94, bottom=0.06)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def chart_momentum(
    px: pd.DataFrame,
    spy: pd.DataFrame,
    out: Path,
    *,
    ticker: str,
    prop,
    prop_b,
) -> Path:
    fig, axes = plt.subplots(2, 1, figsize=(9.4, 4.8), sharex=True, gridspec_kw={"height_ratios": [1.1, 1.1], "hspace": 0.12})
    x = mdates.date2num(px.index.to_pydatetime())

    ax = axes[0]
    ax.plot(x, px["RSI"].values, color="#7c3aed", lw=1.2, label="RSI(14)")
    ax.axhline(70, color=C_UP, lw=0.8, ls="--", alpha=0.7)
    ax.axhline(30, color=C_DN, lw=0.8, ls="--", alpha=0.7)
    ax.axhline(50, color="#94a3b8", lw=0.6, alpha=0.6)
    ax.fill_between(x, 70, 100, color=C_UP, alpha=0.06)
    ax.fill_between(x, 0, 30, color=C_DN, alpha=0.06)
    ax.set_ylim(0, 100)
    ax.set_ylabel("RSI", fontproperties=prop)
    ax.set_title(f"{ticker} 모멘텀 · RSI & SPY 상대강도", fontproperties=prop_b, fontsize=11)
    ax.legend(loc="upper left", fontsize=7, prop=prop)
    ax.grid(True, alpha=0.25)

    ax = axes[1]
    ax.plot(x, px["Ret"].values * 100, color="#0c4a6e", lw=1.3, label=f"{ticker} 누적%")
    ax.plot(x, spy["Ret"].values * 100, color=C_BENCH, lw=1.1, label="SPY 누적%")
    ax.fill_between(x, px["Ret"].values * 100, spy["Ret"].values * 100, where=(px["Ret"] >= spy["Ret"]), color=C_UP, alpha=0.12)
    ax.fill_between(x, px["Ret"].values * 100, spy["Ret"].values * 100, where=(px["Ret"] < spy["Ret"]), color=C_DN, alpha=0.10)
    ax.axhline(0, color="#94a3b8", lw=0.7)
    ax.set_ylabel("1년 누적 수익률 %", fontproperties=prop)
    ax.legend(loc="upper left", fontsize=7, prop=prop)
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(prop)
        lbl.set_fontsize(8)

    fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.10)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def _img_b64(path: Path) -> str:
    import base64

    return base64.b64encode(path.read_bytes()).decode()


def _fig_block(path: Path, caption: str) -> str:
    return (
        f"<figure><img src='data:image/png;base64,{_img_b64(path)}'/>"
        f"<figcaption>{caption}</figcaption></figure>"
    )


def render_price_html(
    ticker: str,
    k: PriceKpis,
    commentary: list[str],
    candle: Path,
    momentum: Path,
) -> str:
    comment_lis = "".join(f"<li>{c}</li>" for c in commentary)
    earn = k.next_earn or "—"
    ma_flag = "MA200 위" if k.above_ma200 else "MA200 아래"
    # Self-contained styles so older generators without .kpi/.easy still render cleanly.
    return f"""
<style>
  .px-easy {{ background:#eff6ff; border-left:4px solid #0369a1; padding:8px 10px; margin:8px 0; font-size:8.5pt; }}
  .px-kpi {{ display:inline-block; background:#fff; border:1px solid #cbd5e1; border-radius:6px;
    padding:8px 12px; margin:6px; min-width:100px; text-align:center; }}
  .px-kpi .l {{ font-size:7.5pt; color:#64748b; }}
  .px-kpi .v {{ font-size:12pt; font-weight:700; color:#0c4a6e; }}
  .px-kpi .s {{ font-size:7.5pt; color:#0369a1; }}
  .px-box {{ background:#fffbeb; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
  .px-gloss {{ background:#fafaf9; border:1px solid #e7e5e4; padding:8px 12px; margin:6px 0 14px; font-size:8.5pt; color:#44403c; }}
  .px-gloss .term {{ font-weight:700; color:#0369a1; }}
  .px-small {{ font-size:8pt; color:#555; }}
</style>
<h2>0-A. 최근 1년 주가 · 기술 위치</h2>
<div class="px-easy"><b>쉽게:</b> 1년 전체는 <b>종가 라인+이평</b>으로 추세를 보고,
최근 ~90일은 <b>일봉 확대</b>로 단기 모양을 본다. (1년 풀 캔들은 너무 빽빽해서 쓰지 않음)</div>
<p>
  <span class="px-kpi"><div class="l">현재가</div><div class="v">${k.last:.2f}</div><div class="s">1Y {k.ticker_1y_pct:+.1f}%</div></span>
  <span class="px-kpi"><div class="l">고점 대비</div><div class="v">{k.pct_from_high:+.1f}%</div><div class="s">저점 +{k.pct_from_low:.1f}%</div></span>
  <span class="px-kpi"><div class="l">vs MA20 / 200</div><div class="v">{k.vs_ma20_pct:+.1f}% / {k.vs_ma200_pct:+.1f}%</div><div class="s">{ma_flag}</div></span>
  <span class="px-kpi"><div class="l">RSI(14)</div><div class="v">{k.rsi:.0f}</div><div class="s">상대 SPY {k.rel_spy_1y_pct:+.1f}%p</div></span>
  <span class="px-kpi"><div class="l">다음 실적</div><div class="v" style="font-size:10pt">{earn}</div><div class="s">추정</div></span>
</p>
{_fig_block(candle, f"{ticker} 1년 종가·이평 + 최근 90일 일봉 확대 + 주간 거래량")}
{_fig_block(momentum, f"{ticker} RSI(14) · SPY 대비 1년 누적 수익률")}
<div class="px-box"><b>차트 자동 해석</b><ul style="margin:6px 0 0 16px">{comment_lis}</ul></div>
<div class="px-gloss"><div style="font-weight:700;color:#0c4a6e;margin-bottom:4px">이 블록 용어 주석</div>
<ul>
<li><span class="term">1년 종가 라인</span> — 풀 일봉 대신 추세·이평 위치 가독성 우선.</li>
<li><span class="term">최근 90일 일봉</span> — 단기 고저·캔들 패턴 확인용 확대 창.</li>
<li><span class="term">MA20/60/150/200</span> — 일 기준 이동평균. 단기→장기 추세.</li>
<li><span class="term">RSI(14)</span> — 상대강도지수. 보통 70↑ 과열, 30↓ 과매도 참고.</li>
<li><span class="term">스윙 고저</span> — 최근 국소 고점·저점. 저항·지지 후보(확정 아님).</li>
<li><span class="term">상대강도 vs SPY</span> — 같은 기간 시장 대비 초과/미달 수익.</li>
</ul></div>
<p class="px-small">데이터: yfinance 일봉(adjusted) · 거래량은 주간 합산 · 실적일은 calendar/earnings_dates 추정 · 투자 권유 아님.</p>
"""

def build_price_analysis(ticker: str, chart_dir: str | Path) -> PriceSection:
    """Build charts + HTML for ticker. On failure returns ok=False with empty html."""
    ticker = ticker.upper().strip()
    chart_dir = Path(chart_dir)
    chart_dir.mkdir(parents=True, exist_ok=True)
    try:
        prop, prop_b = _setup_font()
        px, spy, past_e, next_e = _prepare_frame(ticker)
        swings_hi, swings_lo = _swing_levels(px["High"], px["Low"])
        kpis = compute_kpis(px, spy, next_e)
        commentary = build_commentary(kpis, swings_hi, swings_lo)
        candle = chart_candle_volume(
            px, past_e, next_e, swings_hi, swings_lo,
            chart_dir / "00a_price_candle.png",
            ticker=ticker, prop=prop, prop_b=prop_b,
        )
        momentum = chart_momentum(
            px, spy, chart_dir / "00b_price_momentum.png",
            ticker=ticker, prop=prop, prop_b=prop_b,
        )
        html = render_price_html(ticker, kpis, commentary, candle, momentum)
        return PriceSection(
            ticker=ticker,
            html=html,
            candle_path=candle,
            momentum_path=momentum,
            kpis=kpis,
            commentary=commentary,
            ok=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("price analysis failed for %s", ticker)
        return PriceSection(ticker=ticker, html="", ok=False, error=str(exc))


def insert_price_html(full_html: str, price_html: str) -> str:
    """Insert price section before thesis heading, else after first </section>."""
    if not price_html:
        return full_html
    markers = [
        "<h2>0. 한줄 Thesis</h2>",
        "<h2>0. 한 줄 Thesis</h2>",
        "<h2>1. 어디서 돈이 오나</h2>",
        "<h2>1.",
    ]
    for m in markers:
        if m in full_html:
            return full_html.replace(m, price_html + "\n" + m, 1)
    # fallback: after cover section
    m = re.search(r"</section>", full_html)
    if m:
        i = m.end()
        return full_html[:i] + "\n" + price_html + full_html[i:]
    return price_html + full_html


def build_and_insert_price(ticker: str, chart_dir: str | Path, full_html: str) -> tuple[str, PriceSection]:
    section = build_price_analysis(ticker, chart_dir)
    return insert_price_html(full_html, section.html), section
