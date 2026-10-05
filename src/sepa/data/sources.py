"""Daily OHLCV data sources with automatic fallback.

Primary: yfinance (adjusted prices, no API key).
Fallback: Stooq CSV endpoint (no API key).

All sources return a DataFrame with a tz-naive DatetimeIndex named 'date'
and columns: open, high, low, close, volume (split/dividend adjusted where
the source supports it).
"""

from __future__ import annotations

import io
import logging
from datetime import date

import pandas as pd
import requests

logger = logging.getLogger(__name__)

SCHEMA = ["open", "high", "low", "close", "volume"]

_STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}&d1={d1}&d2={d2}&i=d"


class DataFetchError(RuntimeError):
    pass


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=lambda c: str(c).lower())
    df = df[[c for c in SCHEMA if c in df.columns]]
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx.normalize()
    df.index.name = "date"
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df.dropna(subset=["close"]).astype(float)


def fetch_yfinance(ticker: str, start: date | None = None, end: date | None = None) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        raise DataFetchError(f"yfinance returned no data for {ticker}")
    return normalize_ohlcv(df)


def fetch_stooq(ticker: str, start: date | None = None, end: date | None = None) -> pd.DataFrame:
    symbol = f"{ticker.lower()}.us"
    d1 = (start or date(1990, 1, 1)).strftime("%Y%m%d")
    d2 = (end or date.today()).strftime("%Y%m%d")
    url = _STOOQ_URL.format(symbol=symbol, d1=d1, d2=d2)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    if "Date" not in resp.text[:100]:
        raise DataFetchError(f"stooq returned no data for {ticker}")
    df = pd.read_csv(io.StringIO(resp.text), parse_dates=["Date"]).set_index("Date")
    if df.empty:
        raise DataFetchError(f"stooq returned empty data for {ticker}")
    return normalize_ohlcv(df)


def fetch_daily(ticker: str, start: date | None = None, end: date | None = None) -> pd.DataFrame:
    """Fetch daily OHLCV, trying yfinance first and Stooq as a fallback."""
    errors = []
    for name, fetcher in (("yfinance", fetch_yfinance), ("stooq", fetch_stooq)):
        try:
            df = fetcher(ticker, start, end)
            if not df.empty:
                return df
        except Exception as exc:  # noqa: BLE001 - fall through to next source
            errors.append(f"{name}: {exc}")
            logger.warning("fetch failed for %s via %s: %s", ticker, name, exc)
    raise DataFetchError(f"all sources failed for {ticker} ({'; '.join(errors)})")
