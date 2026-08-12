"""Earnings date quality: confirmed vs estimate.

EARN_D5 hard-block applies only to **confirmed** dates
(``config/earn_confirmed.yaml`` + portfolio holdings SSOT).
Vendor estimates (yfinance / rank calendar) are warnings, not hard blocks —
avoids false gates like ANAB 2026-08-12 (estimate, company unconfirmed).

Hot path: local YAML only. Collection CLI (``sepa.earn_confirm``) is on-demand
and does not scrape the web by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

EarnSource = Literal["confirmed", "estimate", "unknown"]

D5_WINDOW_DAYS = 5

_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PORTFOLIO_PATH = _ROOT / "config" / "portfolio_watch.yaml"
DEFAULT_CONFIRMED_PATH = _ROOT / "config" / "earn_confirmed.yaml"


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


def load_confirmed_earn_file(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Load ``earn_confirmed.yaml`` entries dict (ticker → {earn_date, note, …})."""
    import yaml

    p = Path(path) if path is not None else DEFAULT_CONFIRMED_PATH
    if not p.exists():
        return {}
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    entries = raw.get("entries") or {}
    out: dict[str, dict[str, Any]] = {}
    for k, v in entries.items():
        t = str(k).strip().upper()
        if not t or not isinstance(v, dict):
            continue
        ed = parse_earn_date(v.get("earn_date") or v.get("date"))
        if ed is None:
            continue
        out[t] = {
            "earn_date": ed.isoformat(),
            "note": str(v.get("note") or ""),
            "confirmed_on": str(v.get("confirmed_on") or ""),
        }
    return out


def save_confirmed_earn_file(
    path: str | Path,
    entries: dict[str, dict[str, Any]],
    *,
    as_of: str | None = None,
    note: str | None = None,
) -> None:
    """Write earn_confirmed.yaml (sorted tickers). Local I/O only."""
    import yaml

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    existing_note = note
    existing_asof = as_of
    if p.exists() and (note is None or as_of is None):
        prev = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if existing_note is None:
            existing_note = prev.get("note")
        if existing_asof is None:
            existing_asof = prev.get("as_of")
    payload: dict[str, Any] = {
        "as_of": existing_asof or date.today().isoformat(),
        "note": existing_note
        or "confirmed IR/portfolio SSOT · estimate 자동승격 금지",
        "entries": {t: entries[t] for t in sorted(entries)},
    }
    p.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_portfolio_confirmed_map(path: str | Path | None = None) -> dict[str, date]:
    """Holdings earn_date from portfolio_watch.yaml → confirmed."""
    import yaml

    p = Path(path) if path is not None else DEFAULT_PORTFOLIO_PATH
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


def load_confirmed_earn_map(
    path: str | Path | None = None,
    *,
    portfolio_path: str | Path | None = None,
    confirmed_path: str | Path | None = None,
) -> dict[str, date]:
    """Merge confirmed dates: portfolio holdings ∪ earn_confirmed.yaml.

    ``path`` is accepted as portfolio path for backward compat
    (``load_confirmed_earn_map(portfolio_path)``).

    Precedence on conflict: ``earn_confirmed.yaml`` wins (explicit IR entry).
    Missing files → ignored. Local I/O only — no network.
    """
    port = portfolio_path if portfolio_path is not None else path
    if port is None:
        port = DEFAULT_PORTFOLIO_PATH
    conf = confirmed_path if confirmed_path is not None else DEFAULT_CONFIRMED_PATH

    out = dict(load_portfolio_confirmed_map(port))
    for t, meta in load_confirmed_earn_file(conf).items():
        ed = parse_earn_date(meta.get("earn_date"))
        if ed is not None:
            out[t] = ed
    return out
