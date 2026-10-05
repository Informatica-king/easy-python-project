"""Technical indicators: SMAs, 52-week high/low, volume average, RS ranks."""

from __future__ import annotations

import pandas as pd

from sepa.config import TrendTemplateParams

WEEK_52_DAYS = 252

# IBD-style weighted momentum: recent quarter counts double.
RS_WINDOWS = ((63, 0.4), (126, 0.2), (189, 0.2), (252, 0.2))
RS_MIN_HISTORY = 253


def add_indicators(df: pd.DataFrame, tp: TrendTemplateParams) -> pd.DataFrame:
    out = df.copy()
    close = out["close"]
    for n in (tp.sma_short, tp.sma_mid, tp.sma_long):
        out[f"sma{n}"] = close.rolling(n).mean()
    out["high_52w"] = out["high"].rolling(WEEK_52_DAYS).max()
    out["low_52w"] = out["low"].rolling(WEEK_52_DAYS).min()
    out["vol_sma50"] = out["volume"].rolling(50).mean()
    return out


def rs_score(close: pd.Series) -> float | None:
    if len(close) < RS_MIN_HISTORY:
        return None
    last = close.iloc[-1]
    score = 0.0
    for window, weight in RS_WINDOWS:
        score += weight * (last / close.iloc[-1 - window] - 1.0)
    return float(score)


def compute_rs_ranks(data: dict[str, pd.DataFrame]) -> dict[str, float]:
    """Percentile rank (0-100) of the weighted momentum score within the universe."""
    scores = {}
    for ticker, df in data.items():
        s = rs_score(df["close"])
        if s is not None:
            scores[ticker] = s
    if not scores:
        return {}
    ranks = pd.Series(scores).rank(pct=True) * 100.0
    return ranks.to_dict()
