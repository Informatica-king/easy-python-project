"""Lean technical-analysis scores for a small ticker shortlist.

Efficiency rules (docs/ta_bot_spec.md):
- Never scan full Nasdaq
- Reuse data/raw parquet; prefer --no-update
- Score only the last ``tail_bars`` (default 280)
- No cross-sectional RS (would require full universe)
- Charts optional and off by default
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TAIL_BARS_DEFAULT = 280
EMA_FAST = 20
EMA_SLOW = 50
RSI_N = 14
ATR_N = 14
MOM_N = 20
VOL_AVG_N = 20


@dataclass(frozen=True)
class TAResult:
    ticker: str
    close: float
    as_of: str
    trend: int
    momentum: int
    volatility: int
    setup: int
    total: int
    status: str
    action: str
    entry_lo: float
    entry_hi: float
    stop: float
    atr_pct: float
    rsi: float
    note: str


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _rsi(close: pd.Series, n: int = RSI_N) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(df: pd.DataFrame, n: int = ATR_N) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()


def _macd_hist(close: pd.Series) -> pd.Series:
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd - signal


def _clip_score(x: float) -> int:
    return int(max(0, min(100, round(x))))


def score_frame(df: pd.DataFrame, ticker: str, tail_bars: int = TAIL_BARS_DEFAULT) -> TAResult:
    """Compute 4-axis TA scores from an OHLCV frame (last row = signal bar)."""
    if df is None or df.empty:
        return TAResult(
            ticker=ticker,
            close=float("nan"),
            as_of="",
            trend=0,
            momentum=0,
            volatility=0,
            setup=0,
            total=0,
            status="NO_DATA",
            action="대기",
            entry_lo=float("nan"),
            entry_hi=float("nan"),
            stop=float("nan"),
            atr_pct=float("nan"),
            rsi=float("nan"),
            note="empty frame",
        )

    work = df.iloc[-tail_bars:].copy() if len(df) > tail_bars else df.copy()
    min_need = max(EMA_SLOW, RSI_N, ATR_N, MOM_N, VOL_AVG_N) + 5
    if len(work) < min_need:
        return TAResult(
            ticker=ticker,
            close=float(work["close"].iloc[-1]) if len(work) else float("nan"),
            as_of=str(work.index[-1].date()) if len(work) else "",
            trend=0,
            momentum=0,
            volatility=0,
            setup=0,
            total=0,
            status="NO_DATA",
            action="대기",
            entry_lo=float("nan"),
            entry_hi=float("nan"),
            stop=float("nan"),
            atr_pct=float("nan"),
            rsi=float("nan"),
            note=f"need>={min_need} bars, have {len(work)}",
        )

    close = work["close"]
    ema20 = _ema(close, EMA_FAST)
    ema50 = _ema(close, EMA_SLOW)
    rsi = _rsi(close, RSI_N)
    atr = _atr(work, ATR_N)
    macd_h = _macd_hist(close)
    vol_sma = work["volume"].rolling(VOL_AVG_N).mean()

    c = float(close.iloc[-1])
    e20 = float(ema20.iloc[-1])
    e50 = float(ema50.iloc[-1])
    e20_prev = float(ema20.iloc[-6]) if len(ema20) >= 6 else e20
    rsi_v = float(rsi.iloc[-1])
    atr_v = float(atr.iloc[-1])
    atr_pct = atr_v / c * 100.0 if c else float("nan")
    mom20 = float(close.iloc[-1] / close.iloc[-1 - MOM_N] - 1.0) * 100.0
    macd_v = float(macd_h.iloc[-1])
    vol_ratio = float(work["volume"].iloc[-1] / vol_sma.iloc[-1]) if vol_sma.iloc[-1] else 1.0
    gap20 = (c / e20 - 1.0) * 100.0

    # --- Trend 0–100 ---
    trend = 40.0
    if c > e20:
        trend += 20
    if c > e50:
        trend += 20
    if e20 > e50:
        trend += 15
    if e20 > e20_prev:
        trend += 5
    trend_s = _clip_score(trend)

    # --- Momentum 0–100 ---
    # RSI 45–65 sweet; <30 oversold boost small; >70 overbought penalty handled in action
    if rsi_v < 30:
        mom = 35 + (30 - rsi_v)
    elif rsi_v <= 65:
        mom = 50 + (rsi_v - 45)
    else:
        mom = 70 - (rsi_v - 65) * 1.5
    mom += np.clip(mom20, -15, 15)
    if macd_v > 0:
        mom += 8
    else:
        mom -= 5
    mom_s = _clip_score(mom)

    # --- Volatility 0–100 (higher = calmer / more tradeable for sizing) ---
    # ATR% 1.5–3.5 typical midcap; very high ATR → lower score
    if atr_pct <= 2.0:
        vol_s = 85
    elif atr_pct <= 3.5:
        vol_s = 70
    elif atr_pct <= 5.0:
        vol_s = 50
    elif atr_pct <= 7.0:
        vol_s = 35
    else:
        vol_s = 20
    vol_s = _clip_score(vol_s)

    # --- Setup 0–100 ---
    setup = 40.0
    # pullback to EMA20 band (±2%): good for add
    if -2.5 <= gap20 <= 1.0 and c > e50:
        setup += 35
    elif 1.0 < gap20 <= 4.0 and vol_ratio >= 1.3 and c > e20:
        setup += 25  # mild breakout + volume
    elif gap20 > 8.0:
        setup -= 20  # extended
    if vol_ratio >= 1.5 and c > e20:
        setup += 10
    if -1.0 <= gap20 <= 0.5:
        setup += 5
    setup_s = _clip_score(setup)

    total = _clip_score(0.35 * trend_s + 0.25 * mom_s + 0.15 * vol_s + 0.25 * setup_s)

    # Status / action
    if trend_s < 45 or c < e50:
        status, action = "약세/비정렬", "신규금지"
        note = "EMA50 하회 또는 추세 약함"
    elif rsi_v >= 72 or gap20 >= 8.0:
        status, action = "과열", "신규금지"
        note = "RSI과열 또는 EMA20 과이격"
    elif trend_s >= 70 and 45 <= rsi_v <= 62 and -2.5 <= gap20 <= 1.5:
        status, action = "상승·눌림", "분할OK"
        note = "추세 정렬 + EMA20 부근 셋업"
    elif trend_s >= 65 and setup_s >= 60:
        status, action = "상승정렬", "홀드"
        note = "추세 유효, 무리한 추격 불필요"
    elif trend_s >= 55:
        status, action = "중립·대기", "대기"
        note = "셋업 대기"
    else:
        status, action = "혼조", "축소검토"
        note = "추세·모멘텀 약화"

    entry_lo = round(e20 - 0.5 * atr_v, 2)
    entry_hi = round(e20 + 0.3 * atr_v, 2)
    stop = round(min(e50, c) - 0.8 * atr_v, 2)

    return TAResult(
        ticker=ticker.upper(),
        close=round(c, 2),
        as_of=str(work.index[-1].date()),
        trend=trend_s,
        momentum=mom_s,
        volatility=vol_s,
        setup=setup_s,
        total=total,
        status=status,
        action=action,
        entry_lo=entry_lo,
        entry_hi=entry_hi,
        stop=stop,
        atr_pct=round(atr_pct, 2),
        rsi=round(rsi_v, 1),
        note=note,
    )


def results_to_frame(rows: list[TAResult]) -> pd.DataFrame:
    records = [r.__dict__ for r in rows]
    df = pd.DataFrame.from_records(records)
    if df.empty:
        return df
    return df.sort_values(["action", "total"], ascending=[True, False]).reset_index(drop=True)
