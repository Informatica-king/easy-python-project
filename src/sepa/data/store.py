"""Per-ticker Parquet cache with incremental updates.

Layout: {cache_dir}/{TICKER}.parquet — one file per ticker so the universe
can grow without touching existing data (docs/strategy_spec.md §6).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from sepa.data import sources

logger = logging.getLogger(__name__)


def _cache_path(cache_dir: str | Path, ticker: str) -> Path:
    return Path(cache_dir) / f"{ticker.upper()}.parquet"


def get_history(
    ticker: str,
    cache_dir: str | Path,
    lookback_years: int = 3,
    update: bool = True,
) -> pd.DataFrame:
    """Return cached history for ticker, fetching/extending it as needed."""
    path = _cache_path(cache_dir, ticker)
    start = date.today() - timedelta(days=int(lookback_years * 365.25))

    if path.exists():
        df = pd.read_parquet(path)
        if update:
            last = df.index.max().date()
            if last < date.today():
                try:
                    new = sources.fetch_daily(ticker, start=last + timedelta(days=1))
                    if not new.empty:
                        df = pd.concat([df, new])
                        df = df[~df.index.duplicated(keep="last")].sort_index()
                        _save(df, path)
                except sources.DataFetchError:
                    # Stale cache is still usable; a normal weekend/holiday gap
                    # also lands here because sources return no new rows.
                    logger.info("no incremental data for %s; using cache through %s", ticker, last)
        return df

    df = sources.fetch_daily(ticker, start=start)
    _save(df, path)
    return df


def _save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def load_universe_history(
    tickers: list[str],
    cache_dir: str | Path,
    lookback_years: int = 3,
    update: bool = True,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Load history for all tickers; returns (data, failed_tickers)."""
    data: dict[str, pd.DataFrame] = {}
    failed: list[str] = []
    for ticker in tickers:
        try:
            data[ticker] = get_history(ticker, cache_dir, lookback_years, update)
        except sources.DataFetchError as exc:
            logger.error("skipping %s: %s", ticker, exc)
            failed.append(ticker)
    return data, failed
