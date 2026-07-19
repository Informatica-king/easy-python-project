"""분기 재무 데이터 수집 — SEC EDGAR(1순위) + yfinance 폴백.

캐시: data/fundamentals/{TICKER}.parquet, data/fundamentals/_sec_tickers.json
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

SEC_UA = "SEPA-Screener personal-noncommercial research (sepa-bot@localhost)"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

FRAME_RE = re.compile(r"^CY(\d{4})Q([1-4])$")

# Preferred US-GAAP tags (first hit wins per metric family)
EPS_TAGS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")
REVENUE_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
)
NET_INCOME_TAGS = ("NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic")
OP_INCOME_TAGS = (
    "OperatingIncomeLoss",
    "OperatingIncomeLossAvailableToCommonStockholdersBasic",
)


def _headers() -> dict[str, str]:
    return {"User-Agent": SEC_UA, "Accept-Encoding": "gzip, deflate"}


def cache_dir(root: str | Path) -> Path:
    """Return fundamentals cache dir (sibling of price cache when root is data/raw)."""
    root = Path(root)
    # params.data.cache_dir is typically data/raw → store fundamentals in data/fundamentals
    if root.name == "raw":
        return root.parent / "fundamentals"
    return root / "fundamentals"


def load_cik_map(fund_dir: Path, refresh: bool = False) -> dict[str, str]:
    """Ticker -> zero-padded CIK."""
    fund_dir.mkdir(parents=True, exist_ok=True)
    path = fund_dir / "_sec_tickers.json"
    if path.exists() and not refresh:
        raw = json.loads(path.read_text())
        return {k.upper(): v for k, v in raw.items()}

    logger.info("downloading SEC ticker→CIK map")
    r = requests.get(SEC_TICKERS_URL, headers=_headers(), timeout=60)
    r.raise_for_status()
    mapping = {
        str(v["ticker"]).upper(): str(v["cik_str"]).zfill(10)
        for v in r.json().values()
    }
    path.write_text(json.dumps(mapping, indent=0))
    return mapping


def _frames_from_tag(usgaap: dict, tags: tuple[str, ...]) -> dict[str, float]:
    """Extract CY####Qn -> value from the first available tag."""
    for tag in tags:
        node = usgaap.get(tag)
        if not node:
            continue
        best: dict[str, tuple[str, float]] = {}
        for _unit, rows in node.get("units", {}).items():
            for row in rows:
                frame = row.get("frame")
                if not frame or not FRAME_RE.match(frame):
                    continue
                if len(frame) != 8:  # drop dimensional frames like CY2024Q1I...
                    continue
                val = row.get("val")
                if val is None:
                    continue
                filed = row.get("filed") or ""
                prev = best.get(frame)
                if prev is None or filed >= prev[0]:
                    best[frame] = (filed, float(val))
        if best:
            return {f: v for f, (_filed, v) in best.items()}
    return {}


def _frames_to_series(frames: dict[str, float]) -> pd.Series:
    if not frames:
        return pd.Series(dtype=float)
    items = sorted(frames.items(), key=lambda kv: (int(kv[0][2:6]), int(kv[0][7])))
    idx = pd.Index([k for k, _ in items], name="frame")
    return pd.Series([v for _, v in items], index=idx, dtype=float)


def fetch_sec_quarterly(cik: str) -> pd.DataFrame:
    """Return DataFrame indexed by frame with eps, revenue, net_income, npm, opm."""
    url = SEC_FACTS_URL.format(cik=cik)
    r = requests.get(url, headers=_headers(), timeout=90)
    if r.status_code == 404:
        return pd.DataFrame()
    r.raise_for_status()
    usgaap = r.json().get("facts", {}).get("us-gaap", {})

    eps = _frames_to_series(_frames_from_tag(usgaap, EPS_TAGS))
    rev = _frames_to_series(_frames_from_tag(usgaap, REVENUE_TAGS))
    ni = _frames_to_series(_frames_from_tag(usgaap, NET_INCOME_TAGS))
    oi = _frames_to_series(_frames_from_tag(usgaap, OP_INCOME_TAGS))

    df = pd.DataFrame({"eps": eps, "revenue": rev, "net_income": ni, "op_income": oi})
    df = df.dropna(how="all")
    if not df.empty and "revenue" in df.columns:
        rev_nz = df["revenue"].replace(0, pd.NA)
        if "net_income" in df.columns:
            df["npm"] = df["net_income"] / rev_nz
        if "op_income" in df.columns:
            df["opm"] = df["op_income"] / rev_nz
    return df


def fetch_yfinance_quarterly(ticker: str) -> pd.DataFrame:
    """Fallback: up to ~5 quarters from yfinance income statement."""
    import yfinance as yf

    t = yf.Ticker(ticker)
    qi = t.quarterly_income_stmt
    if qi is None or qi.empty:
        return pd.DataFrame()

    def row(*names: str) -> pd.Series | None:
        for n in names:
            if n in qi.index:
                s = qi.loc[n].astype(float)
                s.index = pd.to_datetime(s.index)
                return s.sort_index()
        return None

    eps = row("Diluted EPS", "Basic EPS")
    rev = row("Total Revenue", "Operating Revenue")
    ni = row("Net Income", "Net Income Common Stockholders")
    oi = row("Operating Income", "Operating Income Loss")
    parts = {}
    if eps is not None:
        parts["eps"] = eps
    if rev is not None:
        parts["revenue"] = rev
    if ni is not None:
        parts["net_income"] = ni
    if oi is not None:
        parts["op_income"] = oi
    if not parts:
        return pd.DataFrame()
    df = pd.DataFrame(parts).sort_index()
    # Synthesize pseudo-frames from quarter-end dates for YoY pairing
    frames = []
    for ts in df.index:
        q = (ts.month - 1) // 3 + 1
        frames.append(f"CY{ts.year}Q{q}")
    df.index = pd.Index(frames, name="frame")
    df = df[~df.index.duplicated(keep="last")]
    if "revenue" in df.columns:
        rev_nz = df["revenue"].replace(0, pd.NA)
        if "net_income" in df.columns:
            df["npm"] = df["net_income"] / rev_nz
        if "op_income" in df.columns:
            df["opm"] = df["op_income"] / rev_nz
    return df


def fetch_roe(ticker: str) -> float | None:
    """Trailing ROE as a fraction (e.g. 0.17 = 17%)."""
    import yfinance as yf

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:  # noqa: BLE001
        logger.debug("ROE fetch failed for %s: %s", ticker, exc)
        return None
    roe = info.get("returnOnEquity")
    if roe is None:
        return None
    return float(roe)


def load_quarterly(
    ticker: str,
    fund_dir: Path,
    cik_map: dict[str, str],
    *,
    refresh: bool = False,
    sleep_s: float = 0.12,
) -> tuple[pd.DataFrame, float | None, str]:
    """Load quarterly fundamentals + ROE. Returns (df, roe, source)."""
    fund_dir.mkdir(parents=True, exist_ok=True)
    path = fund_dir / f"{ticker.upper()}.parquet"
    meta_path = fund_dir / f"{ticker.upper()}.meta.json"

    if path.exists() and meta_path.exists() and not refresh:
        df = pd.read_parquet(path)
        meta = json.loads(meta_path.read_text())
        return df, meta.get("roe"), meta.get("source", "cache")

    source = "none"
    df = pd.DataFrame()
    cik = cik_map.get(ticker.upper())
    if cik:
        try:
            time.sleep(sleep_s)
            df = fetch_sec_quarterly(cik)
            if not df.empty:
                source = "sec"
        except Exception as exc:  # noqa: BLE001
            logger.warning("SEC fetch failed for %s (CIK %s): %s", ticker, cik, exc)

    if df.empty or df.dropna(how="all").empty:
        try:
            df = fetch_yfinance_quarterly(ticker)
            if not df.empty:
                source = "yfinance"
        except Exception as exc:  # noqa: BLE001
            logger.warning("yfinance fundamentals failed for %s: %s", ticker, exc)

    roe = None
    try:
        roe = fetch_roe(ticker)
    except Exception as exc:  # noqa: BLE001
        logger.debug("ROE failed for %s: %s", ticker, exc)

    if not df.empty:
        df.to_parquet(path)
    meta_path.write_text(json.dumps({"roe": roe, "source": source, "ticker": ticker.upper()}))
    return df, roe, source
