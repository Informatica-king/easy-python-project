"""Synthetic price series builders for tests."""

from __future__ import annotations

import numpy as np
import pandas as pd


def frame_from_close(close: np.ndarray, volume: np.ndarray, spread: float = 0.0) -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    idx = pd.bdate_range("2024-01-02", periods=len(close))
    return pd.DataFrame(
        {
            "open": close,
            "high": close * (1 + spread),
            "low": close * (1 - spread),
            "close": close,
            "volume": np.asarray(volume, dtype=float),
        },
        index=idx.rename("date"),
    )


def _leg(start: float, end: float, days: int) -> np.ndarray:
    """Linear price leg of `days` bars ending at `end`, excluding `start`."""
    return np.linspace(start, end, days + 1)[1:]


def make_vcp_frame(
    depths: tuple[float, ...] = (0.20, 0.10, 0.05),
    last_rally_to: float = 94.0,
    base_volume_dryup: bool = True,
) -> pd.DataFrame:
    """250-day uptrend to 100, then a base with the given contraction depths.

    Each contraction: decline from a swing high by `depth`, then a rally to a
    lower high (97, 95, ... hard-coded highs for 3 contractions max realism).
    The final rally stops at `last_rally_to` (pivot = last swing high).
    """
    uptrend = np.linspace(40.0, 99.5, 250)
    closes = [uptrend, np.array([100.0])]  # base high (left peak)

    highs = [100.0, 97.0, 95.0, 94.0, 93.5, 93.0][: len(depths)]
    path_points = []
    for i, depth in enumerate(depths):
        swing_high = highs[i]
        swing_low = swing_high * (1 - depth)
        path_points.append((swing_high, swing_low))

    prev = 100.0
    for i, (swing_high, swing_low) in enumerate(path_points):
        closes.append(_leg(prev, swing_low, 10))
        target = highs[i + 1] if i + 1 < len(path_points) else last_rally_to
        closes.append(_leg(swing_low, target, 7))
        prev = target

    close = np.concatenate(closes)
    n_base = len(close) - 250
    up_vol = np.full(250, 1_000_000.0)
    if base_volume_dryup:
        base_vol = np.linspace(900_000.0, 300_000.0, n_base)
    else:
        base_vol = np.full(n_base, 1_000_000.0)
    volume = np.concatenate([up_vol, base_vol])
    df = frame_from_close(close, volume)
    df["vol_sma50"] = df["volume"].rolling(50).mean()
    return df


def add_breakout_day(df: pd.DataFrame, close: float, volume_mult: float = 2.0) -> pd.DataFrame:
    vol = float(df["vol_sma50"].iloc[-1]) * volume_mult
    row = pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": vol},
        index=pd.DatetimeIndex([df.index[-1] + pd.offsets.BDay(1)], name="date"),
    )
    out = pd.concat([df.drop(columns=["vol_sma50"]), row])
    out["vol_sma50"] = out["volume"].rolling(50).mean()
    return out
