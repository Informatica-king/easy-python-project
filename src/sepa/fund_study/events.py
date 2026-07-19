"""Earnings/filing event dates and return windows."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from sepa.data import store
from sepa.fund_study.config import (
    BENCHMARK,
    EVENT_DOLLAR_VOL_BOTTOM_PCT,
    EVENT_DOLLAR_VOL_WINDOW,
    RET_POST_OFFSET,
    RET_PRE_OFFSET,
    STUDY_YEARS,
)

logger = logging.getLogger(__name__)


def _ensure_naive(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    idx = pd.to_datetime(idx)
    if getattr(idx, "tz", None) is not None:
        return idx.tz_localize(None)
    return idx


def load_benchmark(cache_dir: str | Path, lookback_years: int) -> pd.Series:
    """NASDAQ composite close series (tz-naive)."""
    end = datetime.now().date()
    start = end - timedelta(days=int(365.25 * max(lookback_years, STUDY_YEARS) + 30))
    # Prefer Ticker.history — flatter columns than download() MultiIndex
    try:
        hist = yf.Ticker(BENCHMARK).history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            auto_adjust=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("benchmark history failed: %s", exc)
        hist = None
    if hist is not None and not hist.empty and "Close" in hist.columns:
        s = hist["Close"].dropna().astype(float)
        s.index = _ensure_naive(pd.DatetimeIndex(s.index))
        s.name = "ixic"
        return s.sort_index()

    raw = yf.download(
        BENCHMARK,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        auto_adjust=True,
        progress=False,
    )
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    if isinstance(raw.columns, pd.MultiIndex):
        if ("Close", BENCHMARK) in raw.columns:
            s = raw[("Close", BENCHMARK)]
        elif (BENCHMARK, "Close") in raw.columns:
            s = raw[(BENCHMARK, "Close")]
        else:
            # yfinance often uses level0=Price, level1=Ticker
            try:
                s = raw.xs("Close", axis=1, level=0).iloc[:, 0]
            except Exception:  # noqa: BLE001
                s = raw.xs("Close", axis=1, level=-1).iloc[:, 0]
    else:
        s = raw["Close"]
    s = s.dropna().astype(float)
    s.index = _ensure_naive(pd.DatetimeIndex(s.index))
    s.name = "ixic"
    return s.sort_index()


def fetch_earnings_dates(ticker: str, years: int = STUDY_YEARS) -> pd.DatetimeIndex:
    """Return earnings announcement datetimes (date-normalized, naive)."""
    try:
        t = yf.Ticker(ticker)
        # limit ~4 per year
        ed = t.get_earnings_dates(limit=max(years * 5, 20))
    except Exception as exc:  # noqa: BLE001
        logger.warning("earnings dates failed %s: %s", ticker, exc)
        return pd.DatetimeIndex([])
    if ed is None or ed.empty:
        return pd.DatetimeIndex([])
    idx = _ensure_naive(pd.DatetimeIndex(ed.index)).normalize()
    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    cutoff = today - pd.DateOffset(years=years)
    idx = idx[idx >= cutoff]
    # drop future
    idx = idx[idx <= today]
    return pd.DatetimeIndex(sorted(set(idx)))


def fetch_sec_filing_dates(
    ticker: str,
    *,
    cik_map: dict[str, str],
    years: int = STUDY_YEARS,
) -> pd.DatetimeIndex:
    """Fallback day0 dates from SEC companyfacts `filed` on EPS tags."""
    cik = cik_map.get(str(ticker).upper())
    if not cik:
        return pd.DatetimeIndex([])
    try:
        import requests
        from sepa.data.fundamentals import EPS_TAGS, SEC_FACTS_URL, _headers

        r = requests.get(SEC_FACTS_URL.format(cik=cik), headers=_headers(), timeout=90)
        if r.status_code != 200:
            return pd.DatetimeIndex([])
        usgaap = r.json().get("facts", {}).get("us-gaap", {})
        filed_dates: set[pd.Timestamp] = set()
        today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
        cutoff = today - pd.DateOffset(years=years)
        for tag in EPS_TAGS:
            node = usgaap.get(tag)
            if not node:
                continue
            for _unit, rows in node.get("units", {}).items():
                for row in rows:
                    frame = row.get("frame") or ""
                    if len(frame) != 8:
                        continue
                    filed = row.get("filed")
                    if not filed:
                        continue
                    ts = pd.Timestamp(filed).normalize()
                    if cutoff <= ts <= today:
                        filed_dates.add(ts)
            if filed_dates:
                break
        return pd.DatetimeIndex(sorted(filed_dates))
    except Exception as exc:  # noqa: BLE001
        logger.debug("SEC filing dates failed %s: %s", ticker, exc)
        return pd.DatetimeIndex([])


def event_dates_for_ticker(
    ticker: str,
    *,
    years: int = STUDY_YEARS,
    cik_map: dict[str, str] | None = None,
) -> tuple[pd.DatetimeIndex, str]:
    """Prefer earnings dates; fall back to SEC filing dates. Returns (dates, source)."""
    ed = fetch_earnings_dates(ticker, years=years)
    if len(ed) > 0:
        return ed, "earnings"
    if cik_map:
        fd = fetch_sec_filing_dates(ticker, cik_map=cik_map, years=years)
        if len(fd) > 0:
            return fd, "sec_filed"
    return pd.DatetimeIndex([]), "none"


def trading_day_offset(index: pd.DatetimeIndex, day0: pd.Timestamp, offset: int) -> pd.Timestamp | None:
    """Map announcement calendar day0 to a trading-session date.

    offset = -1 → last trading session *strictly before* day0 (close before announcement day)
    offset = +N (N>0) → N-th trading session *strictly after* day0
    """
    index = _ensure_naive(index).sort_values().unique()
    index = pd.DatetimeIndex(index)
    day0 = pd.Timestamp(day0).normalize()
    if offset == 0:
        # session on day0 if exists else None
        if day0 in index:
            return day0
        return None
    if offset < 0:
        # last session < day0, then step back further if offset < -1
        strict_before = int(index.searchsorted(day0, side="left")) - 1
        target = strict_before + (offset + 1)  # -1 → strict_before
    else:
        first_after = int(index.searchsorted(day0, side="right"))
        target = first_after + (offset - 1)  # +1 → first_after, +3 → first_after+2
    if target < 0 or target >= len(index):
        return None
    return pd.Timestamp(index[target]).normalize()


def event_return_pair(
    prices: pd.Series,
    day0: pd.Timestamp,
    *,
    pre: int = RET_PRE_OFFSET,
    post: int = RET_POST_OFFSET,
) -> tuple[float | None, pd.Timestamp | None, pd.Timestamp | None]:
    """Return (simple_return, start_date, end_date) for close(day0-pre)..close(day0+post)."""
    prices = prices.dropna().astype(float).sort_index()
    prices.index = _ensure_naive(pd.DatetimeIndex(prices.index))
    start = trading_day_offset(prices.index, day0, -pre)
    end = trading_day_offset(prices.index, day0, post)
    if start is None or end is None:
        return None, start, end
    if start not in prices.index or end not in prices.index:
        return None, start, end
    p0 = float(prices.loc[start])
    p1 = float(prices.loc[end])
    if p0 == 0:
        return None, start, end
    return p1 / p0 - 1.0, start, end


def dollar_volume_around(
    df: pd.DataFrame,
    day0: pd.Timestamp,
    window: int = EVENT_DOLLAR_VOL_WINDOW,
) -> float | None:
    """Mean dollar volume over sessions in [day0-window, day0+window]."""
    if df is None or df.empty or "volume" not in df.columns:
        return None
    idx = _ensure_naive(pd.DatetimeIndex(df.index))
    work = df.copy()
    work.index = idx
    day0 = pd.Timestamp(day0).normalize()
    # approximate calendar window then filter trading days
    lo = day0 - pd.Timedelta(days=window * 2 + 5)
    hi = day0 + pd.Timedelta(days=window * 2 + 5)
    sub = work.loc[(work.index >= lo) & (work.index <= hi)]
    if sub.empty:
        return None
    # keep nearest 2*window+1 sessions around day0
    pos = sub.index.searchsorted(day0)
    left = max(0, pos - window)
    right = min(len(sub), pos + window + 1)
    band = sub.iloc[left:right]
    dv = (band["close"].astype(float) * band["volume"].astype(float)).dropna()
    if dv.empty:
        return None
    return float(dv.mean())


def apply_liquidity_filter(events: pd.DataFrame) -> pd.DataFrame:
    """Drop bottom EVENT_DOLLAR_VOL_BOTTOM_PCT by event_adv."""
    if events.empty or "event_adv" not in events.columns:
        return events
    work = events.dropna(subset=["event_adv"]).copy()
    if work.empty:
        return work
    thr = work["event_adv"].quantile(EVENT_DOLLAR_VOL_BOTTOM_PCT)
    return work.loc[work["event_adv"] >= thr].reset_index(drop=True)


def build_event_returns_for_ticker(
    ticker: str,
    *,
    cache_dir: str | Path,
    lookback_years: int,
    bench: pd.Series,
    years: int = STUDY_YEARS,
    cik_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """One row per earnings event with raw/mkt-adj returns."""
    dates, source = event_dates_for_ticker(ticker, years=years, cik_map=cik_map)
    if len(dates) == 0:
        return pd.DataFrame()
    try:
        hist = store.get_history(ticker, cache_dir, max(lookback_years, years + 1), update=False)
    except Exception:  # noqa: BLE001
        return pd.DataFrame()
    if hist is None or hist.empty:
        return pd.DataFrame()
    px = hist["close"].astype(float).copy()
    px.index = _ensure_naive(pd.DatetimeIndex(px.index))

    rows = []
    for day0 in dates:
        ret, start, end = event_return_pair(px, day0)
        if ret is None or start is None or end is None:
            continue
        # benchmark same window
        b0 = float(bench.loc[start]) if start in bench.index else np.nan
        b1 = float(bench.loc[end]) if end in bench.index else np.nan
        if not np.isfinite(b0) or not np.isfinite(b1) or b0 == 0:
            # try reindex asof
            try:
                b0 = float(bench.asof(start))
                b1 = float(bench.asof(end))
            except Exception:  # noqa: BLE001
                continue
        if not np.isfinite(b0) or not np.isfinite(b1) or b0 == 0:
            continue
        bret = b1 / b0 - 1.0
        eadv = dollar_volume_around(hist, day0)
        rows.append(
            {
                "ticker": ticker,
                "day0": pd.Timestamp(day0).normalize(),
                "day0_source": source,
                "start": start,
                "end": end,
                "ret_raw": float(ret),
                "ret_mkt": float(ret - bret),
                "ret_bench": float(bret),
                "event_adv": eadv,
            }
        )
    return pd.DataFrame(rows)
