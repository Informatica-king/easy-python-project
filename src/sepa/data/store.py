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

    if not update:
        raise sources.DataFetchError(f"no cached data for {ticker} (running with update disabled)")
    df = sources.fetch_daily(ticker, start=start)
    _save(df, path)
    return df


def _save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def bulk_update(
    tickers: list[str],
    cache_dir: str | Path,
    lookback_years: int = 3,
    chunk_size: int = 100,
    pause_sec: float = 1.0,
) -> tuple[list[str], list[str]]:
    """Fetch/extend history for many tickers via chunked batch downloads.

    One yfinance request per chunk instead of one per ticker, which keeps the
    full-Nasdaq run (~3,300 tickers) down to a few dozen requests and avoids
    per-ticker rate limiting. Returns (ok_tickers, failed_tickers).
    """
    import time

    import yfinance as yf

    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    today = date.today()
    default_start = today - timedelta(days=int(lookback_years * 365.25))

    ok: list[str] = []
    failed: list[str] = []
    n_chunks = (len(tickers) + chunk_size - 1) // chunk_size
    for ci in range(n_chunks):
        chunk = tickers[ci * chunk_size : (ci + 1) * chunk_size]

        last_dates: dict[str, date | None] = {}
        for t in chunk:
            path = _cache_path(cache_dir, t)
            last_dates[t] = pd.read_parquet(path).index.max().date() if path.exists() else None

        # One request covers the whole chunk: start at the oldest gap.
        chunk_start = min(
            default_start if last is None else last + timedelta(days=1)
            for last in last_dates.values()
        )
        if chunk_start >= today and all(last is not None for last in last_dates.values()):
            ok.extend(chunk)
            continue

        try:
            raw = yf.download(
                chunk,
                start=chunk_start,
                auto_adjust=True,
                progress=False,
                group_by="ticker",
                threads=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("chunk %d/%d download failed: %s", ci + 1, n_chunks, exc)
            failed.extend(t for t in chunk if last_dates[t] is None)
            ok.extend(t for t in chunk if last_dates[t] is not None)
            continue

        for t in chunk:
            try:
                sub = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
                new = sources.normalize_ohlcv(sub.dropna(how="all"))
            except Exception:  # noqa: BLE001 - ticker missing from response
                new = pd.DataFrame()

            path = _cache_path(cache_dir, t)
            if last_dates[t] is not None:
                if not new.empty:
                    old = pd.read_parquet(path)
                    df = pd.concat([old, new])
                    df = df[~df.index.duplicated(keep="last")].sort_index()
                    _save(df, path)
                ok.append(t)
            elif not new.empty:
                _save(new, path)
                ok.append(t)
            else:
                failed.append(t)

        logger.info("bulk update chunk %d/%d done (ok=%d failed=%d)", ci + 1, n_chunks, len(ok), len(failed))
        if ci + 1 < n_chunks:
            time.sleep(pause_sec)
    return ok, failed


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


def _extract_ticker_ohlcv(raw: pd.DataFrame, ticker: str, chunk: list[str]) -> pd.DataFrame:
    """Normalize one ticker frame out of a yfinance multi-ticker download."""
    if raw is None or raw.empty:
        return pd.DataFrame()
    try:
        if isinstance(raw.columns, pd.MultiIndex):
            # group_by=ticker → level0 ticker; else Price/Ticker layout
            lvl0 = raw.columns.get_level_values(0)
            if ticker in set(lvl0):
                sub = raw[ticker]
            elif len(chunk) == 1:
                # single-ticker download often has (Price, Ticker) columns
                sub = raw.copy()
            else:
                try:
                    sub = raw.xs(ticker, axis=1, level=-1)
                except Exception:  # noqa: BLE001
                    return pd.DataFrame()
        else:
            sub = raw
        return sources.normalize_ohlcv(sub.dropna(how="all"))
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def backfill_history(
    tickers: list[str],
    cache_dir: str | Path,
    lookback_years: int = 11,
    chunk_size: int = 40,
    pause_sec: float = 1.5,
) -> tuple[list[str], list[str]]:
    """Re-download OHLCV from ``today - lookback_years`` and replace caches.

    Unlike :func:`bulk_update` (forward-only incremental), this always requests
    the full lookback window so older history missing from a short cache is
    filled in. Existing rows are union-merged; downloaded values win on overlap.
    """
    import time

    import yfinance as yf

    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    today = date.today()
    start = today - timedelta(days=int(lookback_years * 365.25))

    ok: list[str] = []
    failed: list[str] = []
    tickers = [t.upper() for t in tickers]
    n_chunks = (len(tickers) + chunk_size - 1) // chunk_size
    for ci in range(n_chunks):
        chunk = tickers[ci * chunk_size : (ci + 1) * chunk_size]
        logger.info(
            "backfill chunk %d/%d (%d tickers) start=%s",
            ci + 1,
            n_chunks,
            len(chunk),
            start.isoformat(),
        )
        try:
            raw = yf.download(
                chunk,
                start=start.isoformat(),
                end=(today + timedelta(days=1)).isoformat(),
                auto_adjust=True,
                progress=False,
                group_by="ticker",
                threads=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("backfill chunk %d/%d failed: %s", ci + 1, n_chunks, exc)
            # Per-ticker fallback
            for t in chunk:
                try:
                    df = sources.fetch_daily(t, start=start)
                    if df.empty:
                        failed.append(t)
                        continue
                    path = _cache_path(cache_dir, t)
                    if path.exists():
                        old = pd.read_parquet(path)
                        df = pd.concat([old, df])
                        df = df[~df.index.duplicated(keep="last")].sort_index()
                    _save(df, path)
                    ok.append(t)
                except Exception:  # noqa: BLE001
                    failed.append(t)
            if ci + 1 < n_chunks:
                time.sleep(pause_sec)
            continue

        for t in chunk:
            new = _extract_ticker_ohlcv(raw, t, chunk)
            path = _cache_path(cache_dir, t)
            if new.empty:
                # Keep existing cache if any; count as failed for backfill goal
                if path.exists():
                    logger.warning("backfill empty for %s; leaving existing cache", t)
                failed.append(t)
                continue
            if path.exists():
                try:
                    old = pd.read_parquet(path)
                    df = pd.concat([old, new])
                    # Prefer newly downloaded values on overlap
                    df = df[~df.index.duplicated(keep="last")].sort_index()
                except Exception:  # noqa: BLE001
                    df = new
            else:
                df = new
            _save(df, path)
            ok.append(t)

        logger.info(
            "backfill chunk %d/%d done (ok=%d failed=%d so far)",
            ci + 1,
            n_chunks,
            len(ok),
            len(failed),
        )
        if ci + 1 < n_chunks:
            time.sleep(pause_sec)
    return ok, failed
