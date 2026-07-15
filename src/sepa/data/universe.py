"""Nasdaq universe listing (Phase 4: full Nasdaq, ETFs excluded).

Uses the official Nasdaq Trader symbol directory, which carries explicit
ETF and test-issue flags.
"""

from __future__ import annotations

import io

import pandas as pd
import requests

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"


def fetch_nasdaq_listed() -> pd.DataFrame:
    """Fetch the raw Nasdaq symbol directory as a DataFrame."""
    resp = requests.get(NASDAQ_LISTED_URL, timeout=30)
    resp.raise_for_status()
    lines = resp.text.splitlines()
    # Last line is a "File Creation Time" footer.
    body = "\n".join(line for line in lines if not line.startswith("File Creation Time"))
    df = pd.read_csv(io.StringIO(body), sep="|")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


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
