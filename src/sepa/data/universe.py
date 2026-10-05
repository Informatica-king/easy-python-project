"""Nasdaq universe listing (Phase 4: full Nasdaq, ETFs excluded).

Uses the official Nasdaq Trader symbol directory, which carries explicit
ETF and test-issue flags.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
# Leading underscore so the file can never collide with a {TICKER}.parquet.
LISTING_CACHE_NAME = "_nasdaq_listed.csv"


def fetch_nasdaq_listed(cache_dir: str | Path | None = None) -> pd.DataFrame:
    """Fetch the raw Nasdaq symbol directory as a DataFrame.

    If cache_dir is given, a successful fetch is cached there and the cache
    is used as a fallback when the fetch fails (offline runs).
    """
    cache_path = Path(cache_dir) / LISTING_CACHE_NAME if cache_dir else None
    try:
        resp = requests.get(NASDAQ_LISTED_URL, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        if cache_path is not None and cache_path.exists():
            logger.warning("nasdaqlisted fetch failed (%s); using cached listing", exc)
            return pd.read_csv(cache_path)
        raise
    lines = resp.text.splitlines()
    # Last line is a "File Creation Time" footer.
    body = "\n".join(line for line in lines if not line.startswith("File Creation Time"))
    df = pd.read_csv(io.StringIO(body), sep="|")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_path, index=False)
    return df


def clean_security_name(name: str) -> str:
    """Strip the security-type suffix from a Nasdaq security name.

    'Apple Inc. - Common Stock' -> 'Apple Inc.'
    """
    return str(name).split(" - ")[0].strip()


def security_names(
    listed: pd.DataFrame | None = None,
    cache_dir: str | Path | None = None,
) -> dict[str, str]:
    """Map ticker -> cleaned company name from the Nasdaq symbol directory."""
    df = listed if listed is not None else fetch_nasdaq_listed(cache_dir)
    pairs = df[["symbol", "security_name"]].dropna()
    return {
        str(sym).strip(): clean_security_name(name)
        for sym, name in zip(pairs["symbol"], pairs["security_name"])
    }


def common_stock_tickers(listed: pd.DataFrame | None = None) -> list[str]:
    """Nasdaq tickers excluding ETFs, test issues and non-normal status."""
    df = listed if listed is not None else fetch_nasdaq_listed()
    mask = (
        (df["etf"] == "N")
        & (df["test_issue"] == "N")
        & (df["financial_status"].fillna("N").isin(["N"]))
    )
    tickers = df.loc[mask, "symbol"].dropna().astype(str).str.strip()
    tickers = tickers[tickers != ""]
    # Skip anything with special suffixes.
    tickers = tickers[~tickers.str.contains(r"[\.\$\+\=]", regex=True)]
    # Nasdaq 5th-letter convention: R=right, U=unit, W=warrant.
    tickers = tickers[~((tickers.str.len() == 5) & tickers.str[-1].isin(["R", "U", "W"]))]
    return sorted(tickers.tolist())
