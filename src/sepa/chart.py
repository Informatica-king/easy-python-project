"""SEPA analysis chart for a single ticker.

Renders a daily candlestick chart with the trend lines the SEPA strategy
uses (SMA 50/150/200, rolling 52-week high/low), the ZigZag swing structure
of the current base, the VCP pivot when a valid setup exists, and a Trend
Template scorecard.

Usage:
    python -m sepa.chart --ticker SNDK [--months 18] [--as-of YYYY-MM-DD]
                         [--out reports/charts] [--no-update]
"""

from __future__ import annotations

import argparse
import glob
import logging
from datetime import datetime
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402

from sepa import indicators, trend_template, vcp  # noqa: E402
from sepa.config import Params, load_params  # noqa: E402
from sepa.data import store, universe  # noqa: E402

logger = logging.getLogger(__name__)

CONDITION_LABELS = {
    "1_above_mid_long_ma": "1. 주가 > SMA150 & SMA200",
    "2_mid_above_long": "2. SMA150 > SMA200",
    "3_long_ma_rising": "3. SMA200 상승 중",
    "4_ma_stack": "4. 정배열 (50>150>200)",
    "5_above_short_ma": "5. 주가 > SMA50",
    "6_above_52w_low": "6. 52주 저점 +30% 이상",
    "7_near_52w_high": "7. 52주 고점 -25% 이내",
    "8_rs_rank": "8. RS 순위 기준 이상",
}


def _setup_korean_font() -> None:
    for path in glob.glob("/usr/share/fonts/truetype/nanum/NanumGothic*.ttf"):
        fm.fontManager.addfont(path)
    if any("NanumGothic" == f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = "NanumGothic"
    plt.rcParams["axes.unicode_minus"] = False


def _latest_rs_rank(ticker: str, report_dir: str) -> float | None:
    """Look up the ticker's RS rank from the most recent diagnostics report."""
    paths = sorted(Path(report_dir).glob("diagnostics_*.csv"))
    if not paths:
        return None
    diag = pd.read_csv(paths[-1])
    row = diag[diag["ticker"] == ticker.upper()]
    if row.empty or pd.isna(row["rs_rank"].iloc[0]):
        return None
    return float(row["rs_rank"].iloc[0])


def _candles(ax: plt.Axes, df: pd.DataFrame) -> None:
    x = np.arange(len(df))
    up = df["close"].to_numpy() >= df["open"].to_numpy()
    colors = np.where(up, "#c0392b", "#2471a3")  # 한국식: 상승=빨강, 하락=파랑
    ax.vlines(x, df["low"], df["high"], color=colors, lw=0.7)
    body_bottom = np.minimum(df["open"], df["close"])
    body_height = (df["close"] - df["open"]).abs()
    body_height = body_height.mask(body_height == 0, df["close"] * 1e-4)
    ax.bar(x, body_height, bottom=body_bottom, width=0.65, color=colors, edgecolor=colors)


def render_chart(
    ticker: str,
    params: Params,
    months: int = 18,
    as_of: str | None = None,
    update: bool = True,
    out_dir: str | Path = "reports/charts",
) -> Path:
    _setup_korean_font()
    ticker = ticker.upper()

    df = store.get_history(ticker, params.data.cache_dir, params.data.lookback_years, update)
    if as_of:
        df = df.loc[: pd.Timestamp(as_of)]
    full = indicators.add_indicators(df, params.trend_template)

    rs_rank = _latest_rs_rank(ticker, params.report_dir) if not as_of else None
    tt = trend_template.evaluate(full, params.trend_template, rs_rank)
    vcp_res = vcp.detect_vcp(full, params.vcp)

    try:
        name = universe.security_names(cache_dir=params.data.cache_dir).get(ticker, ticker)
    except Exception:  # noqa: BLE001 - cosmetic only
        name = ticker

    view = full.tail(int(months * 21)).copy()
    x = np.arange(len(view))
    offset = len(full) - len(view)  # full-frame position -> view position

    fig, (ax, axv) = plt.subplots(
        2, 1, figsize=(16, 9.5), sharex=True, height_ratios=[3.2, 1],
        gridspec_kw={"hspace": 0.06}, facecolor="white",
    )

    # ── 가격 패널: 일봉 + SEPA 추세선 ─────────────────────────────
    _candles(ax, view)
    tp = params.trend_template
    ax.plot(x, view[f"sma{tp.sma_short}"], color="#1f77b4", lw=1.4, label=f"SMA{tp.sma_short}")
    ax.plot(x, view[f"sma{tp.sma_mid}"], color="#ff9900", lw=1.4, label=f"SMA{tp.sma_mid}")
    ax.plot(x, view[f"sma{tp.sma_long}"], color="#9467bd", lw=1.6, label=f"SMA{tp.sma_long}")
    ax.plot(x, view["high_52w"], color="#2ca02c", lw=1.0, ls=":", label="52주 최고가(롤링)")
    ax.plot(x, view["low_52w"], color="#7f7f7f", lw=1.0, ls=":", label="52주 최저가(롤링)")

    # ── 현재 베이스의 스윙 구조 (ZigZag) ──────────────────────────
    scan_days = params.vcp.base_max_weeks * vcp.TRADING_DAYS_PER_WEEK
    window = full.tail(scan_days)
    if len(window) > vcp.BASE_PEAK_EXCLUDE_DAYS:
        peak_search = window.iloc[: -vcp.BASE_PEAK_EXCLUDE_DAYS]
        peak_pos = int(peak_search["high"].argmax())
        base = window.iloc[peak_pos:]
        swings = vcp.build_swings(base, params.vcp, full_df=full)
        mode = (params.vcp.swing_mode or "pct").lower()
        zz_label = f"베이스 스윙 구조(ZigZag/{mode})"
        base_start_full = len(full) - len(window) + peak_pos
        sx = [base_start_full + s.pos - offset for s in swings]
        sy = [s.price for s in swings]
        # 마지막 미확정 구간까지 이어 그리기
        tail = base["close"].iloc[-1]
        if sx and sx[-1] < len(view) - 1:
            sx.append(len(view) - 1)
            sy.append(float(tail))
        in_view = [(px, py) for px, py in zip(sx, sy) if px >= 0]
        if len(in_view) >= 2:
            ax.plot(*zip(*in_view), color="black", lw=1.1, ls="--", marker="o",
                    ms=4, label=zz_label)

    if vcp_res.pivot is not None:
        sig = vcp_res.signal.value if vcp_res.valid else "NONE"
        ax.axhline(vcp_res.pivot, color="crimson", lw=1.4, ls="-.",
                   label=f"VCP 피벗 {vcp_res.pivot:,.0f} ({sig})")
    if vcp_res.stop is not None:
        risk = f" (리스크 {vcp_res.risk_pct:.1f}%)" if vcp_res.risk_pct is not None else ""
        ax.axhline(vcp_res.stop, color="#8e44ad", lw=1.2, ls=":",
                   label=f"손절 {vcp_res.stop:,.0f}{risk}")

    last = full.iloc[-1]
    # 큰 폭의 상승/하락 구간은 로그 스케일이 추세 판독에 유리
    lo, hi = float(view["low"].min()), float(view["high"].max())
    if lo > 0 and hi / lo > 4:
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_ylabel("주가 (USD, 수정주가 · 로그 스케일)")
    else:
        ax.set_ylabel("주가 (USD, 수정주가)")
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    ax.grid(alpha=0.25)

    # ── Trend Template 스코어카드 ────────────────────────────────
    lines = []
    for key, label in CONDITION_LABELS.items():
        if key not in tt.conditions:
            continue
        note = ""
        if key == "8_rs_rank":
            note = f" (RS={rs_rank:.0f})" if rs_rank is not None else " (RS 미산출)"
        lines.append(f"{'O' if tt.conditions[key] else 'X'}  {label}{note}")
    n_pass = sum(tt.conditions.values())
    verdict = "Stage 2 (Trend Template 통과)" if tt.passed else f"Stage 2 아님 ({n_pass}/{len(tt.conditions)} 통과)"
    if vcp_res.valid:
        q = f" · 품질 {vcp_res.quality_score:.0f}" if vcp_res.quality_score is not None else ""
        stop_s = f" · 손절 {vcp_res.stop:,.0f}" if vcp_res.stop is not None else ""
        vcp_line = f"VCP: {vcp_res.signal.value} — {vcp_res.footprint}{q}{stop_s}"
    else:
        extra = ""
        if vcp_res.stop is not None and vcp_res.quality_score is not None:
            extra = f" (손절 {vcp_res.stop:,.0f} · 품질 {vcp_res.quality_score:.0f})"
        vcp_line = f"VCP 셋업 없음: {vcp_res.reason}{extra}"
    box_text = f"[{verdict}]\n" + "\n".join(lines) + f"\n\n{vcp_line}"
    ax.text(0.995, 0.02, box_text, transform=ax.transAxes, fontsize=9,
            va="bottom", ha="right", family="NanumGothicCoding",
            bbox=dict(boxstyle="round,pad=0.5", fc="#fffbe6", ec="#999999", alpha=0.95))

    # ── 거래량 패널 ──────────────────────────────────────────────
    vol_colors = np.where(view["close"].to_numpy() >= view["open"].to_numpy(), "#c0392b", "#2471a3")
    axv.bar(x, view["volume"] / 1e6, color=vol_colors, width=0.65, alpha=0.75)
    axv.plot(x, view["vol_sma50"] / 1e6, color="black", lw=1.1, label="거래량 SMA50")
    axv.set_ylabel("거래량 (백만주)")
    axv.legend(loc="upper left", fontsize=9)
    axv.grid(alpha=0.25)

    ticks = np.linspace(0, len(view) - 1, 8).astype(int)
    axv.set_xticks(ticks)
    axv.set_xticklabels([view.index[i].strftime("%Y-%m") for i in ticks])
    ax.set_xlim(-1, len(view))

    stamp = (as_of or str(full.index[-1].date()))
    fig.suptitle(
        f"{name} ({ticker}) — SEPA 일봉 분석  |  기준일 {stamp}  |  종가 {last['close']:,.2f}",
        fontsize=14, fontweight="bold", y=0.965,
    )

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{ticker}_sepa_{stamp.replace('-', '')}.png"
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    logger.info("chart saved: %s", path)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SEPA analysis chart for one ticker")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--months", type=int, default=18, help="chart window in months")
    parser.add_argument("--as-of", default=None, help="analyze as of date YYYY-MM-DD")
    parser.add_argument("--out", default="reports/charts")
    parser.add_argument("--no-update", action="store_true")
    parser.add_argument("--swing-mode", choices=["pct", "atr"], default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    params = load_params(args.config)
    if args.swing_mode:
        import dataclasses

        params = dataclasses.replace(
            params,
            vcp=dataclasses.replace(params.vcp, swing_mode=args.swing_mode),
        )
    path = render_chart(
        args.ticker, params, months=args.months,
        as_of=args.as_of, update=not args.no_update, out_dir=args.out,
    )
    print(f"chart: {path}  (swing_mode={params.vcp.swing_mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
