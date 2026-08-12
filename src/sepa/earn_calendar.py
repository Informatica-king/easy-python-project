"""Earnings date quality: confirmed vs estimate.

EARN_D5 hard-block applies only to **confirmed** dates (portfolio SSOT / IR).
Vendor estimates (yfinance calendar) are warnings, not hard blocks — avoids
false gates like ANAB 2026-08-12 (estimate, company unconfirmed).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

EarnSource = Literal["confirmed", "estimate", "unknown"]

D5_WINDOW_DAYS = 5


def parse_earn_date(raw: Any) -> date | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


@dataclass(frozen=True)
class EarnDateInfo:
    """Normalized earnings date with provenance."""

    earn_date: date | None
    source: EarnSource = "unknown"
    note: str = ""

    @property
    def is_confirmed(self) -> bool:
        return self.source == "confirmed" and self.earn_date is not None

    def days_to(self, as_of: date) -> int | None:
        if self.earn_date is None:
            return None
        return (self.earn_date - as_of).days

    def in_d5(self, as_of: date, *, window: int = D5_WINDOW_DAYS) -> bool:
        """True if as_of in [earn-window, earn] inclusive."""
        d = self.days_to(as_of)
        if d is None:
            return False
        return 0 <= d <= window

    def blocks_new_buys(self, as_of: date, *, window: int = D5_WINDOW_DAYS) -> bool:
        """Hard EARN_D5 block — confirmed dates only."""
        return self.is_confirmed and self.in_d5(as_of, window=window)

    def warn_estimate_window(self, as_of: date, *, window: int = D5_WINDOW_DAYS) -> bool:
        """Soft warning when estimate falls in D5 window."""
        return self.source == "estimate" and self.in_d5(as_of, window=window)


def earn_info_from_row(
    row: dict[str, Any] | None,
    *,
    default_source: EarnSource = "estimate",
) -> EarnDateInfo:
    """Build EarnDateInfo from scenario/rank/chase row dict."""
    if not row:
        return EarnDateInfo(None, "unknown")
    raw = row.get("earnDate") or row.get("earn_date") or row.get("earn")
    src_raw = str(row.get("earn_source") or row.get("earnSource") or "").strip().lower()
    if src_raw in ("confirmed", "confirm", "ir", "ssot", "official"):
        source: EarnSource = "confirmed"
    elif src_raw in ("estimate", "est", "yahoo", "vendor"):
        source = "estimate"
    elif row.get("earn_confirmed") is True:
        source = "confirmed"
    elif row.get("earn_confirmed") is False:
        source = "estimate"
    else:
        source = default_source
    note = str(row.get("earn_note") or "")
    return EarnDateInfo(parse_earn_date(raw), source, note)


def earn_info_from_holding(earn_date: date | None) -> EarnDateInfo:
    """Portfolio yaml earn_date is treated as SSOT confirmed."""
    if earn_date is None:
        return EarnDateInfo(None, "unknown")
    return EarnDateInfo(earn_date, "confirmed", "portfolio_watch SSOT")


def load_confirmed_earn_map(path: str | Path) -> dict[str, date]:
    """Read portfolio_watch.yaml holdings → {TICKER: earn_date} as confirmed SSOT.

    Watchlist/exited entries without earn_date are ignored. Holdings win on
    duplicate tickers. Empty/missing path → {}.
    """
    import yaml

    p = Path(path)
    if not p.exists():
        return {}
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    out: dict[str, date] = {}
    for h in raw.get("holdings") or []:
        if not h or h.get("role") == "exited":
            continue
        t = str(h.get("ticker") or "").strip().upper()
        ed = parse_earn_date(h.get("earn_date"))
        if t and ed is not None:
            out[t] = ed
    return out
