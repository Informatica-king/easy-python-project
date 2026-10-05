"""Universe: Nasdaq common, mcap>=$1B, ADV>=$5M, no ADR/ETF."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import yfinance as yf

from sepa.data import store, universe
from sepa.fund_study.config import ADV_LOOKBACK_DAYS, MIN_ADV, MIN_MARKET_CAP

logger = logging.getLogger(__name__)

# Heuristic ADR name markers in Nasdaq security_name
_ADR_MARKERS = (
    "ADR",
    "ADS",
    "American Depositary",
    "American Depository",
)


def _is_adr_name(name: str) -> bool:
    u = str(name).upper()
    return any(m.upper() in u for m in _ADR_MARKERS)


def compute_adv(ticker: str, cache_dir: str | Path, lookback_years: int) -> float | None:
    try:
        df = store.get_history(ticker, cache_dir, lookback_years, update=False)
    except Exception:  # noqa: BLE001
        return None
    if df is None or len(df) < 20:
        return None
    tail = df.tail(ADV_LOOKBACK_DAYS)
    if "volume" not in tail.columns or "close" not in tail.columns:
        return None
    dv = (tail["close"].astype(float) * tail["volume"].astype(float)).dropna()
    if len(dv) < 10:
        return None
    return float(dv.mean())


def fetch_mcap(ticker: str) -> float | None:
    try:
        info = yf.Ticker(ticker).info or {}
        mc = info.get("marketCap")
        return float(mc) if mc is not None else None
    except Exception:  # noqa: BLE001
        return None


def build_universe(
    *,
    cache_dir: str | Path,
    lookback_years: int,
    out_path: Path | None = None,
    max_workers: int = 12,
    refresh_mcap: bool = False,
    target_n: int | None = None,
    prefer_tickers: list[str] | None = None,
) -> pd.DataFrame:
    """Return filtered universe DataFrame: ticker, name, adv, market_cap.

    If ``target_n`` is set (pilot), stop mcap fetching once we have enough
    qualifying names (over-fetch ~2x then trim by mcap). Prefer tickers with
    existing price/fundamentals cache first for speed.
    """
    listed = universe.fetch_nasdaq_listed(cache_dir=cache_dir)
    names = universe.security_names(listed, cache_dir=cache_dir)
    common = universe.common_stock_tickers(listed)

    # Drop ADR by name heuristic
    tickers = [t for t in common if not _is_adr_name(names.get(t, ""))]
    # Prefer cached fundamentals / requested seeds so pilot is useful quickly
    fund_dir = Path(cache_dir).parent / "fundamentals"
    cached_fund = set()
    if fund_dir.exists():
        cached_fund = {p.stem.upper() for p in fund_dir.glob("*.parquet")}
    prefer = {t.upper() for t in (prefer_tickers or [])}
    tickers.sort(
        key=lambda t: (
            0 if t.upper() in prefer else 1,
            0 if t.upper() in cached_fund else 1,
            t,
        )
    )
    logger.info("common non-ADR candidates: %d", len(tickers))

    mcap_cache_path = Path(cache_dir).parent / "fund_study" / "_mcaps.json"
    if Path(cache_dir).name != "raw":
        mcap_cache_path = Path(cache_dir) / "fund_study" / "_mcaps.json"
    mcap_cache_path.parent.mkdir(parents=True, exist_ok=True)
    mcaps: dict[str, float] = {}
    if mcap_cache_path.exists() and not refresh_mcap:
        try:
            mcaps = {k: float(v) for k, v in json.loads(mcap_cache_path.read_text()).items() if v is not None}
        except Exception:  # noqa: BLE001
            mcaps = {}

    rows = []
    need_mcap = []
    adv_checked = 0
    # For pilot, we may not need every ADV survivor — scan until enough candidates
    stop_after_adv = None if target_n is None else max(target_n * 8, 200)
    for t in tickers:
        adv = compute_adv(t, cache_dir, lookback_years)
        adv_checked += 1
        if adv is None or adv < MIN_ADV:
            if target_n is not None and adv_checked >= stop_after_adv and len(need_mcap) + len(rows) >= target_n * 3:
                break
            continue
        if t in mcaps:
            mc = mcaps[t]
            if mc >= MIN_MARKET_CAP:
                rows.append({"ticker": t, "name": names.get(t, t), "adv": adv, "market_cap": mc})
        else:
            need_mcap.append((t, adv))
        if target_n is not None and len(rows) + len(need_mcap) >= max(target_n * 4, 80):
            break

    logger.info(
        "ADV>=$5M survivors pending mcap: %d (cached hits so far %d, adv_checked=%d)",
        len(need_mcap),
        len(rows),
        adv_checked,
    )

    def _job(item: tuple[str, float]) -> tuple[str, float, float | None]:
        t, adv = item
        return t, adv, fetch_mcap(t)

    want = None if target_n is None else max(target_n * 2, target_n + 10)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_job, item) for item in need_mcap]
        for i, fut in enumerate(as_completed(futs), 1):
            t, adv, mc = fut.result()
            if mc is not None:
                mcaps[t] = mc
            if mc is not None and mc >= MIN_MARKET_CAP:
                rows.append({"ticker": t, "name": names.get(t, t), "adv": adv, "market_cap": mc})
            if i % 50 == 0:
                logger.info("mcap fetch %d/%d (qualified=%d)", i, len(need_mcap), len(rows))
            if want is not None and len(rows) >= want:
                break

    mcap_cache_path.write_text(json.dumps(mcaps, indent=0))
    df = pd.DataFrame(rows)
    if df.empty:
        logger.warning("universe empty")
        return df
    df = df.sort_values("market_cap", ascending=False).reset_index(drop=True)
    if target_n is not None:
        df = df.head(target_n).reset_index(drop=True)
    logger.info("universe size: %d", len(df))
    if out_path is not None and target_n is None:
        # Only persist full universe; pilot slices stay ephemeral
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_path, index=False)
        df.to_csv(out_path.with_suffix(".csv"), index=False)
    return df


def load_or_build_universe(
    *,
    cache_dir: str | Path,
    lookback_years: int,
    out_path: Path,
    refresh: bool = False,
    target_n: int | None = None,
) -> pd.DataFrame:
    if out_path.exists() and not refresh and target_n is None:
        return pd.read_parquet(out_path)
    if out_path.exists() and not refresh and target_n is not None:
        full = pd.read_parquet(out_path)
        if len(full) >= target_n:
            return full.head(target_n).reset_index(drop=True)
    return build_universe(
        cache_dir=cache_dir,
        lookback_years=lookback_years,
        out_path=out_path if target_n is None else None,
        target_n=target_n,
    )
