"""Collect prior US regular-session market + news for 경제뉴스()."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
import pandas as pd
import yaml
import yfinance as yf

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

INDEX_TICKERS = {
    "SPY": "S&P500(ETF)",
    "QQQ": "나스닥100(ETF)",
    "IWM": "러셀2000(ETF)",
    "DIA": "다우(ETF)",
    "^VIX": "VIX 공포지수",
    "SMH": "반도체(ETF)",
}

SECTOR_ETFS = {
    "XLK": "기술",
    "XLF": "금융",
    "XLE": "에너지",
    "XLV": "헬스케어",
    "XLI": "산업",
    "XLY": "임의소비",
    "XLP": "필수소비",
    "XLU": "유틸리티",
    "XLB": "소재",
    "XLRE": "리츠",
    "XLC": "커뮤니케이션",
}

RSS_FEEDS = [
    ("Yahoo", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US"),
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
]

# crude keyword → sector tag for news linking
NEWS_SECTOR_KW = [
    ("반도체", ["semiconductor", "chip", "memory", "hbm", "nvidia", "micron", "ai chip", "foundry"]),
    ("기술", ["tech", "software", "cloud", "apple", "microsoft", "google", "meta"]),
    ("금융", ["bank", "fed", "treasury", "yield", "rate cut", "rate hike", "powell"]),
    ("에너지", ["oil", "crude", "opec", "energy", "gas"]),
    ("헬스케어", ["biotech", "pharma", "drug", "fda", "health"]),
    ("소비", ["retail", "consumer", "spending"]),
]


@dataclass
class BarSnap:
    ticker: str
    name: str
    close: float
    prev_close: float
    change_pct: float
    volume: float
    vol_avg20: float | None
    vol_ratio: float | None
    high: float
    low: float


@dataclass
class Headline:
    source: str
    title: str
    link: str
    published: str
    sector_tags: list[str] = field(default_factory=list)


@dataclass
class PortfolioRow:
    ticker: str
    role: str
    note: str
    close: float | None
    change_pct: float | None
    headlines: list[str] = field(default_factory=list)


@dataclass
class EconNewsBundle:
    session_date: date
    generated_at: str
    indices: list[BarSnap]
    sectors: list[BarSnap]
    headlines: list[Headline]
    portfolio: list[PortfolioRow]
    mood: str
    bullets: list[str]


def _last_session_date(as_of: date | None = None) -> date:
    """Pick the most recent weekday session date in ET (best-effort)."""
    now_et = datetime.now(ET)
    d = as_of or now_et.date()
    # If requesting today before market close ambiguity: use previous complete day
    if as_of is None:
        # early morning ET → prior weekday is the session to summarize
        if now_et.hour < 16:
            d = d - timedelta(days=1)
    while d.weekday() >= 5:  # Sat/Sun
        d -= timedelta(days=1)
    return d


def load_portfolio(path: str | Path = "config/portfolio_watch.yaml") -> list[dict[str, str]]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    rows = []
    for block in ("holdings", "watchlist"):
        for item in raw.get(block) or []:
            rows.append(
                {
                    "ticker": str(item["ticker"]).upper(),
                    "role": str(item.get("role") or ("hold" if block == "holdings" else "watch")),
                    "note": str(item.get("note") or ""),
                }
            )
    return rows


def _hist(ticker: str, days: int = 40) -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=f"{max(days, 30)}d", auto_adjust=True)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns=str.lower)
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:
        idx = idx.tz_convert(ET).tz_localize(None)
    df.index = idx.normalize()
    df.index.name = "date"
    return df


def _snap_from_hist(ticker: str, name: str, df: pd.DataFrame, session: date) -> BarSnap | None:
    if df.empty or len(df) < 2:
        return None
    # find row on/before session
    sub = df.loc[: pd.Timestamp(session)]
    if len(sub) < 2:
        sub = df
    if len(sub) < 2:
        return None
    last = sub.iloc[-1]
    prev = sub.iloc[-2]
    close = float(last["close"])
    prev_c = float(prev["close"])
    chg = (close / prev_c - 1.0) if prev_c else 0.0
    vol = float(last.get("volume") or 0)
    avg20 = float(sub["volume"].tail(20).mean()) if len(sub) >= 5 else None
    ratio = (vol / avg20) if avg20 and avg20 > 0 else None
    return BarSnap(
        ticker=ticker,
        name=name,
        close=close,
        prev_close=prev_c,
        change_pct=chg,
        volume=vol,
        vol_avg20=avg20,
        vol_ratio=ratio,
        high=float(last.get("high") or close),
        low=float(last.get("low") or close),
    )


def collect_bars(mapping: dict[str, str], session: date) -> list[BarSnap]:
    out = []
    for t, name in mapping.items():
        try:
            df = _hist(t)
            snap = _snap_from_hist(t, name, df, session)
            if snap:
                out.append(snap)
        except Exception as exc:  # noqa: BLE001
            logger.warning("bar fail %s: %s", t, exc)
    return out


def _tag_sectors(title: str) -> list[str]:
    low = title.lower()
    tags = []
    for sector, kws in NEWS_SECTOR_KW:
        if any(k in low for k in kws):
            tags.append(sector)
    return tags


def _parse_when(entry: Any) -> str:
    for key in ("published", "updated", "created"):
        if getattr(entry, key, None):
            return str(getattr(entry, key))[:25]
    return ""


def collect_rss(limit_per_feed: int = 12) -> list[Headline]:
    headlines: list[Headline] = []
    for source, url in RSS_FEEDS:
        try:
            parsed = feedparser.parse(url)
            for e in (parsed.entries or [])[:limit_per_feed]:
                title = str(getattr(e, "title", "") or "").strip()
                if not title:
                    continue
                link = str(getattr(e, "link", "") or "")
                headlines.append(
                    Headline(
                        source=source,
                        title=title,
                        link=link,
                        published=_parse_when(e),
                        sector_tags=_tag_sectors(title),
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("rss fail %s: %s", source, exc)
    # de-dupe by title
    seen = set()
    uniq = []
    for h in headlines:
        key = re.sub(r"\s+", " ", h.title.lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
    return uniq


def collect_ticker_news(tickers: list[str], limit_each: int = 4) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for t in tickers:
        titles = []
        try:
            raw = yf.Ticker(t).news or []
            for item in raw[: limit_each * 2]:
                content = item.get("content") if isinstance(item, dict) else None
                if isinstance(content, dict):
                    title = content.get("title") or content.get("summary") or ""
                else:
                    title = item.get("title") if isinstance(item, dict) else ""
                title = str(title).strip()
                if title and title not in titles:
                    titles.append(title)
                if len(titles) >= limit_each:
                    break
        except Exception as exc:  # noqa: BLE001
            logger.warning("ticker news fail %s: %s", t, exc)
        out[t] = titles
    return out


def infer_mood(indices: list[BarSnap], sectors: list[BarSnap]) -> tuple[str, list[str]]:
    by = {s.ticker: s for s in indices}
    spy = by.get("SPY")
    qqq = by.get("QQQ")
    iwm = by.get("IWM")
    vix = by.get("^VIX")
    smh = by.get("SMH")

    bullets: list[str] = []
    if spy:
        bullets.append(f"S&P(SPY) {spy.change_pct*100:+.2f}% · 거래량/20일평균 {spy.vol_ratio or 0:.2f}x")
    ranked = sorted(sectors, key=lambda x: x.change_pct, reverse=True)
    if ranked:
        hot, cold = ranked[0], ranked[-1]
        bullets.append(f"핫 섹터 {hot.name}({hot.ticker}) {hot.change_pct*100:+.2f}% · 콜드 {cold.name} {cold.change_pct*100:+.2f}%")
    if smh:
        bullets.append(f"반도체 SMH {smh.change_pct*100:+.2f}% (테마 온도계)")

    score = 0.0
    if spy:
        score += spy.change_pct
    if qqq:
        score += qqq.change_pct
    if vix:
        score -= vix.change_pct * 0.3
    if score > 0.004:
        mood = "위험선호(Risk-On) 기조"
    elif score < -0.004:
        mood = "위험회피(Risk-Off) 기조"
    else:
        mood = "혼조·방향성 약한 하루"
    if iwm and spy and abs(iwm.change_pct - spy.change_pct) > 0.005:
        lead = "소형주 상대강세" if iwm.change_pct > spy.change_pct else "대형주 우위"
        bullets.append(lead)
    return mood, bullets[:5]


def build_bundle(
    session: date | None = None,
    portfolio_path: str | Path = "config/portfolio_watch.yaml",
) -> EconNewsBundle:
    sess = _last_session_date(session)
    indices = collect_bars(INDEX_TICKERS, sess)
    sectors = collect_bars(SECTOR_ETFS, sess)
    headlines = collect_rss()
    port_cfg = load_portfolio(portfolio_path)
    tickers = [p["ticker"] for p in port_cfg]
    tnews = collect_ticker_news(tickers)

    portfolio: list[PortfolioRow] = []
    for p in port_cfg:
        t = p["ticker"]
        try:
            df = _hist(t)
            snap = _snap_from_hist(t, t, df, sess)
        except Exception:  # noqa: BLE001
            snap = None
        portfolio.append(
            PortfolioRow(
                ticker=t,
                role=p["role"],
                note=p["note"],
                close=snap.close if snap else None,
                change_pct=snap.change_pct if snap else None,
                headlines=tnews.get(t, []),
            )
        )

    mood, bullets = infer_mood(indices, sectors)
    # enrich bullets with top headline
    if headlines:
        bullets.append(f"헤드라인: {headlines[0].title[:80]}")

    return EconNewsBundle(
        session_date=sess,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        indices=indices,
        sectors=sorted(sectors, key=lambda x: x.change_pct, reverse=True),
        headlines=headlines[:40],
        portfolio=portfolio,
        mood=mood,
        bullets=bullets,
    )
