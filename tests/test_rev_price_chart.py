"""Tests for sepa.rev_price_chart (offline with synthetic OHLCV)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sepa.rev_price_chart import (
    build_commentary,
    compute_kpis,
    insert_price_html,
    _rsi,
    _swing_levels,
    chart_candle_volume,
    chart_momentum,
    render_price_html,
    _setup_font,
)


def _synthetic_px(n: int = 260) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(42)
    idx = pd.bdate_range("2025-07-01", periods=n)
    # mild uptrend
    close = 20 + np.cumsum(rng.normal(0.03, 0.4, size=n))
    open_ = close + rng.normal(0, 0.15, size=n)
    high = np.maximum(open_, close) + rng.uniform(0.05, 0.4, size=n)
    low = np.minimum(open_, close) - rng.uniform(0.05, 0.4, size=n)
    vol = rng.integers(200_000, 800_000, size=n).astype(float)
    px = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=idx,
    )
    for w in (20, 60, 150, 200):
        px[f"MA{w}"] = px["Close"].rolling(w).mean()
    px["RSI"] = _rsi(px["Close"])
    px["VolMA20"] = px["Volume"].rolling(20).mean()
    px["Ret"] = px["Close"] / px["Close"].iloc[0] - 1.0

    spy_close = 400 + np.cumsum(rng.normal(0.02, 0.3, size=n))
    spy = pd.DataFrame({"Close": spy_close}, index=idx)
    spy["Ret"] = spy["Close"] / spy["Close"].iloc[0] - 1.0
    px["RelSPY"] = (1 + px["Ret"]) / (1 + spy["Ret"]) - 1.0
    return px, spy


def test_rsi_bounds():
    px, _ = _synthetic_px(80)
    r = _rsi(px["Close"]).dropna()
    assert r.min() >= 0
    assert r.max() <= 100


def test_swing_levels_return_recent():
    px, _ = _synthetic_px()
    hi, lo = _swing_levels(px["High"], px["Low"], order=5)
    assert len(hi) <= 3
    assert len(lo) <= 3


def test_kpis_and_commentary():
    px, spy = _synthetic_px()
    k = compute_kpis(px, spy, next_earn=pd.Timestamp("2026-08-05"))
    assert k.last > 0
    assert k.next_earn == "2026-08-05"
    lines = build_commentary(k, [("2026-01-01", k.high_52w)], [("2025-09-01", k.low_52w)])
    assert any("추세" in x for x in lines)
    assert any("실적" in x for x in lines)


def test_charts_and_html(tmp_path: Path):
    px, spy = _synthetic_px()
    prop, prop_b = _setup_font()
    hi, lo = _swing_levels(px["High"], px["Low"])
    candle = chart_candle_volume(
        px, [px.index[100]], pd.Timestamp("2026-08-05"), hi, lo,
        tmp_path / "00a.png", ticker="TEST", prop=prop, prop_b=prop_b,
    )
    mom = chart_momentum(px, spy, tmp_path / "00b.png", ticker="TEST", prop=prop, prop_b=prop_b)
    assert candle.is_file() and candle.stat().st_size > 1000
    assert mom.is_file() and mom.stat().st_size > 1000
    k = compute_kpis(px, spy, pd.Timestamp("2026-08-05"))
    html = render_price_html("TEST", k, build_commentary(k, hi, lo), candle, mom)
    assert "0-A. 최근 1년 주가" in html
    assert "RSI" in html


def test_insert_before_thesis():
    base = "<section class='cover'>X</section>\n<h2>0. 한줄 Thesis</h2>\n<p>t</p>"
    out = insert_price_html(base, "<h2>0-A. PRICE</h2>")
    assert out.index("0-A. PRICE") < out.index("한줄 Thesis")
