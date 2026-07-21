"""Portfolio hooks on top of raw TA actions.

Approved scope (2026-07-21):
1. EARN_D5 — within 5 calendar days before earnings (incl. earn day) → block adds
2. BAND — price outside configured [lo, hi] → block adds; clip entry zone when inside

Hooks only override add-like actions (``분할OK``). Scores are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from sepa.ta_score import TAResult

ADD_ACTIONS = frozenset({"분할OK"})
D5_WINDOW_DAYS = 5


@dataclass(frozen=True)
class TickerMeta:
    symbol: str
    earn_date: date | None = None
    band_lo: float | None = None
    band_hi: float | None = None


def _parse_date(raw: Any) -> date | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(str(raw)[:10])


def _parse_band(raw: Any) -> tuple[float | None, float | None]:
    if raw is None:
        return None, None
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        lo, hi = float(raw[0]), float(raw[1])
        if lo > hi:
            lo, hi = hi, lo
        return lo, hi
    raise ValueError(f"band must be [lo, hi], got {raw!r}")


def parse_watchlist(path: str | Path) -> dict[str, TickerMeta]:
    """Load watchlist YAML → {SYMBOL: TickerMeta}. Supports plain strings."""
    raw = yaml.safe_load(Path(path).read_text())
    items = raw.get("tickers") or []
    out: dict[str, TickerMeta] = {}
    for item in items:
        if isinstance(item, str):
            sym = item.strip().upper()
            out[sym] = TickerMeta(symbol=sym)
            continue
        if not isinstance(item, dict):
            raise ValueError(f"watchlist item must be str or mapping, got {item!r}")
        sym = str(item.get("symbol") or item.get("ticker") or "").strip().upper()
        if not sym:
            raise ValueError(f"watchlist item missing symbol: {item!r}")
        lo, hi = _parse_band(item.get("band"))
        out[sym] = TickerMeta(
            symbol=sym,
            earn_date=_parse_date(item.get("earn_date")),
            band_lo=lo,
            band_hi=hi,
        )
    if len(out) > 20:
        raise ValueError(f"ta watchlist too large ({len(out)}); keep ≤20")
    return out


def watchlist_symbols(meta: dict[str, TickerMeta]) -> list[str]:
    return list(meta.keys())


def in_earn_d5(as_of: date, earn: date | None, window: int = D5_WINDOW_DAYS) -> bool:
    """True if as_of is in [earn - window, earn] inclusive (pre-report window)."""
    if earn is None:
        return False
    return earn - timedelta(days=window) <= as_of <= earn


def apply_hooks(
    result: TAResult,
    meta: TickerMeta | None,
    *,
    as_of: date | None = None,
) -> TAResult:
    """Return new TAResult with action/note possibly overridden; scores intact."""
    ta_action = result.action
    if meta is None:
        return replace(result, ta_action=ta_action or result.action, override="—", reason="")

    action = result.action
    overrides: list[str] = []
    reasons: list[str] = []
    entry_lo, entry_hi = result.entry_lo, result.entry_hi

    ref = as_of
    if ref is None and result.as_of:
        ref = date.fromisoformat(result.as_of[:10])
    if ref is None:
        ref = date.today()

    # 1) Earnings D-5 — block add signals only
    if in_earn_d5(ref, meta.earn_date):
        assert meta.earn_date is not None
        days_left = (meta.earn_date - ref).days
        tag = f"실적 D-{days_left} ({meta.earn_date.isoformat()})"
        if action in ADD_ACTIONS:
            action = "대기"
            overrides.append("EARN_D5")
            reasons.append(f"{tag} 분할 차단")
        else:
            overrides.append("EARN_D5")
            reasons.append(f"{tag} 구간")

    # 2) Price band — block adds outside; clip entry when inside
    if meta.band_lo is not None and meta.band_hi is not None:
        lo, hi = meta.band_lo, meta.band_hi
        px = result.close
        if px == px:  # not NaN
            if px < lo or px > hi:
                side = "상단초과" if px > hi else "하단미달"
                if ta_action in ADD_ACTIONS:
                    action = "대기"
                overrides.append("BAND")
                reasons.append(f"밴드 ${lo:g}–${hi:g} 밖 ({side} ${px:g})")
            else:
                if entry_lo == entry_lo and entry_hi == entry_hi:
                    new_lo = max(float(entry_lo), lo)
                    new_hi = min(float(entry_hi), hi)
                    if new_lo <= new_hi:
                        entry_lo, entry_hi = round(new_lo, 2), round(new_hi, 2)
                    else:
                        entry_lo, entry_hi = lo, hi
                        reasons.append("TA진입존∩밴드 공집합→밴드사용")

    # de-dupe override tags while preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for o in overrides:
        if o not in seen:
            seen.add(o)
            uniq.append(o)

    override = "+".join(uniq) if uniq else "—"
    reason = " · ".join(reasons)
    note = result.note
    if reason:
        note = f"{result.note} | {reason}" if result.note else reason

    return replace(
        result,
        action=action,
        entry_lo=entry_lo,
        entry_hi=entry_hi,
        note=note,
        ta_action=ta_action,
        override=override,
        reason=reason,
    )
