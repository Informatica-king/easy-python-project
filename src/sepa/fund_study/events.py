"""Earnings/filing event dates and return windows."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from sepa.data import store
from sepa.fund_study.config import (
    BENCHMARK,
    BENCHMARK_CACHE,
    BENCHMARK_STOOQ,
    EARNINGS_CACHE_DIR,
    EVENT_DOLLAR_VOL_BOTTOM_PCT,
    EVENT_DOLLAR_VOL_WINDOW,
    RET_POST_OFFSET,
    RET_PRE_OFFSET,
    STUDY_YEARS,
)

logger = logging.getLogger(__name__)

# Process-wide: after Yahoo rate-limits, prefer SEC filings for day0
_YF_RATE_LIMITED = False


def _ensure_naive(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    idx = pd.to_datetime(idx)
    if getattr(idx, "tz", None) is not None:
        return idx.tz_localize(None)
    return idx


def _mark_rate_limited(exc: BaseException | str) -> None:
    global _YF_RATE_LIMITED
    msg = str(exc).lower()
    if "rate" in msg or "too many" in msg or "429" in msg:
        _YF_RATE_LIMITED = True
        logger.warning("Yahoo rate limit detected — preferring SEC filing dates")


def is_yahoo_rate_limited() -> bool:
    return _YF_RATE_LIMITED


def _series_from_close(s: pd.Series) -> pd.Series:
    s = s.dropna().astype(float)
    s.index = _ensure_naive(pd.DatetimeIndex(s.index))
    s.name = "ixic"
    return s.sort_index()


def _load_benchmark_stooq(start, end) -> pd.Series:
    """NASDAQ Composite via Stooq index symbol ^ndq."""
    import io

    import requests
    from sepa.data.sources import normalize_ohlcv

    d1 = start.strftime("%Y%m%d")
    d2 = end.strftime("%Y%m%d")
    url = f"https://stooq.com/q/d/l/?s={BENCHMARK_STOOQ.lower()}&d1={d1}&d2={d2}&i=d"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    if "Date" not in resp.text[:120]:
        return pd.Series(dtype=float)
    raw = pd.read_csv(io.StringIO(resp.text), parse_dates=["Date"]).set_index("Date")
    df = normalize_ohlcv(raw)
    if df.empty:
        return pd.Series(dtype=float)
    return _series_from_close(df["close"])


def load_benchmark(cache_dir: str | Path, lookback_years: int) -> pd.Series:
    """NASDAQ composite close series (tz-naive), disk-cached with retries.

    Falls back to QQQ (local cache / Yahoo) when ^IXIC is unavailable — highly
    correlated Nasdaq market proxy for market-adjusted event returns.
    """
    cache_path = Path(BENCHMARK_CACHE)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    end = datetime.now().date()
    start = end - timedelta(days=int(365.25 * max(lookback_years, STUDY_YEARS) + 30))
    min_span_days = int(365.25 * max(lookback_years, STUDY_YEARS) * 0.8)

    if cache_path.exists():
        try:
            cached = pd.read_parquet(cache_path)["close"]
            cached = _series_from_close(cached)
            span = (cached.index.max() - cached.index.min()).days
            last = cached.index.max().date()
            if span >= min_span_days and last >= end - timedelta(days=7):
                logger.info("benchmark cache hit %s (%d bars)", cache_path, len(cached))
                return cached
        except Exception as exc:  # noqa: BLE001
            logger.warning("benchmark cache unreadable: %s", exc)

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            hist = yf.Ticker(BENCHMARK).history(
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                auto_adjust=True,
            )
            if hist is not None and not hist.empty and "Close" in hist.columns:
                s = _series_from_close(hist["Close"])
                pd.DataFrame({"close": s}).to_parquet(cache_path)
                return s
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            _mark_rate_limited(exc)
            logger.warning("benchmark yfinance ^IXIC attempt %d failed: %s", attempt + 1, exc)
            time.sleep(2 ** attempt)

    # QQQ proxy: prefer local parquet, then Yahoo
    qqq_path = Path(cache_dir) / "QQQ.parquet"
    if qqq_path.exists():
        try:
            q = pd.read_parquet(qqq_path)["close"]
            s = _series_from_close(q)
            if (s.index.max() - s.index.min()).days >= min_span_days * 0.5:
                pd.DataFrame({"close": s}).to_parquet(cache_path)
                logger.warning("benchmark using local QQQ as NASDAQ proxy (%d bars)", len(s))
                return s
        except Exception as exc:  # noqa: BLE001
            logger.warning("local QQQ read failed: %s", exc)

    for attempt in range(3):
        try:
            hist = yf.Ticker("QQQ").history(
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                auto_adjust=True,
            )
            if hist is not None and not hist.empty and "Close" in hist.columns:
                s = _series_from_close(hist["Close"])
                pd.DataFrame({"close": s}).to_parquet(cache_path)
                # also seed equity cache
                try:
                    out = hist.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
                    out.index = _ensure_naive(pd.DatetimeIndex(out.index))
                    out.to_parquet(qqq_path)
                except Exception:  # noqa: BLE001
                    pass
                logger.warning("benchmark using Yahoo QQQ as NASDAQ proxy (%d bars)", len(s))
                return s
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            _mark_rate_limited(exc)
            logger.warning("benchmark QQQ attempt %d failed: %s", attempt + 1, exc)
            time.sleep(2 ** attempt)

    # Stooq last resort (may 404 depending on region)
    try:
        s = _load_benchmark_stooq(start, end)
        if not s.empty:
            pd.DataFrame({"close": s}).to_parquet(cache_path)
            logger.info("benchmark loaded via Stooq (%d bars)", len(s))
            return s
    except Exception as exc:  # noqa: BLE001
        last_exc = exc
        logger.warning("benchmark Stooq failed: %s", exc)

    if cache_path.exists():
        try:
            cached = _series_from_close(pd.read_parquet(cache_path)["close"])
            logger.warning("using stale benchmark cache (%d bars)", len(cached))
            return cached
        except Exception:  # noqa: BLE001
            pass

    logger.error("benchmark load failed entirely: %s", last_exc)
    return pd.Series(dtype=float)


def _earnings_cache_path(ticker: str) -> Path:
    return Path(EARNINGS_CACHE_DIR) / f"{ticker.upper()}.parquet"


def fetch_earnings_dates(
    ticker: str,
    years: int = STUDY_YEARS,
    *,
    use_cache: bool = True,
    refresh: bool = False,
) -> pd.DatetimeIndex:
    """Return earnings announcement datetimes (date-normalized, naive)."""
    global _YF_RATE_LIMITED
    path = _earnings_cache_path(ticker)
    if use_cache and path.exists() and not refresh:
        try:
            df = pd.read_parquet(path)
            idx = _ensure_naive(pd.DatetimeIndex(df["day0"])).normalize()
            today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
            cutoff = today - pd.DateOffset(years=years)
            idx = idx[(idx >= cutoff) & (idx <= today)]
            return pd.DatetimeIndex(sorted(set(idx)))
        except Exception:  # noqa: BLE001
            pass

    if _YF_RATE_LIMITED:
        return pd.DatetimeIndex([])

    try:
        t = yf.Ticker(ticker)
        ed = t.get_earnings_dates(limit=max(years * 5, 20))
    except Exception as exc:  # noqa: BLE001
        _mark_rate_limited(exc)
        logger.warning("earnings dates failed %s: %s", ticker, exc)
        return pd.DatetimeIndex([])
    if ed is None or ed.empty:
        return pd.DatetimeIndex([])
    idx = _ensure_naive(pd.DatetimeIndex(ed.index)).normalize()
    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    cutoff = today - pd.DateOffset(years=years)
    idx = idx[(idx >= cutoff) & (idx <= today)]
    idx = pd.DatetimeIndex(sorted(set(idx)))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"day0": idx}).to_parquet(path, index=False)
        # Also cache surprise table if present
        sur_path = path.with_name(path.stem + "_table.parquet")
        ed2 = ed.copy()
        ed2.index = _ensure_naive(pd.DatetimeIndex(ed2.index)).normalize()
        ed2.to_parquet(sur_path)
    except Exception as exc:  # noqa: BLE001
        logger.debug("earnings cache write failed %s: %s", ticker, exc)
    return idx


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
