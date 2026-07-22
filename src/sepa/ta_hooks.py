"""Portfolio hooks on top of raw TA actions.

Approved scope:
1. EARN_D5 — within 5 calendar days before earnings (incl. earn day) → block adds
2. BAND — price outside configured [lo, hi] → block adds; clip entry zone when inside
3. NO_ADD — portfolio policy blocks adds (``분할OK`` → ``대기``)
4. STOP — close ≤ stop → ``축소검토`` (손절/축소 시나리오)
5. TP — close ≥ tp1 → ``익절검토`` (tp2면 이유에 표기)

Hooks override add-like actions first; STOP/TP may set exit-review actions.
Scores are unchanged.
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
    stop: float | None = None
    tp1: float | None = None
    tp2: float | None = None
    no_add: bool = False


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


def _parse_float(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    return float(raw)


def _meta_from_mapping(item: dict[str, Any], *, sym_keys: tuple[str, ...] = ("symbol", "ticker")) -> TickerMeta:
    sym = ""
    for k in sym_keys:
        if item.get(k):
            sym = str(item[k]).strip().upper()
            break
    if not sym:
        raise ValueError(f"item missing symbol/ticker: {item!r}")
    lo, hi = _parse_band(item.get("band"))
    return TickerMeta(
        symbol=sym,
        earn_date=_parse_date(item.get("earn_date")),
        band_lo=lo,
        band_hi=hi,
        stop=_parse_float(item.get("stop")),
        tp1=_parse_float(item.get("tp1")),
        tp2=_parse_float(item.get("tp2")),
        no_add=bool(item.get("no_add", False)),
    )


def _merge_meta(base: TickerMeta, over: TickerMeta) -> TickerMeta:
    """Overlay non-default fields from ``over`` onto ``base`` (same symbol)."""
    return TickerMeta(
        symbol=base.symbol,
        earn_date=over.earn_date or base.earn_date,
        band_lo=over.band_lo if over.band_lo is not None else base.band_lo,
        band_hi=over.band_hi if over.band_hi is not None else base.band_hi,
        stop=over.stop if over.stop is not None else base.stop,
        tp1=over.tp1 if over.tp1 is not None else base.tp1,
        tp2=over.tp2 if over.tp2 is not None else base.tp2,
        no_add=over.no_add or base.no_add,
    )


def parse_watchlist(path: str | Path) -> dict[str, TickerMeta]:
    """Load watchlist YAML → {SYMBOL: TickerMeta}. Supports plain strings."""
    raw = yaml.safe_load(Path(path).read_text()) or {}
    items = raw.get("tickers") or []
    out: dict[str, TickerMeta] = {}
    for item in items:
        if isinstance(item, str):
            sym = item.strip().upper()
            out[sym] = TickerMeta(symbol=sym)
            continue
        if not isinstance(item, dict):
            raise ValueError(f"watchlist item must be str or mapping, got {item!r}")
        meta = _meta_from_mapping(item)
        out[meta.symbol] = meta
    if len(out) > 20:
        raise ValueError(f"ta watchlist too large ({len(out)}); keep ≤20")
    return out


def parse_portfolio_watch(path: str | Path) -> dict[str, TickerMeta]:
    """Load holdings+watchlist from portfolio_watch.yaml → {SYMBOL: TickerMeta}."""
    p = Path(path)
    if not p.exists():
        return {}
    raw = yaml.safe_load(p.read_text()) or {}
    out: dict[str, TickerMeta] = {}
    for key in ("holdings", "watchlist"):
        for item in raw.get(key) or []:
            if not isinstance(item, dict):
                continue
            meta = _meta_from_mapping(item)
            if meta.symbol in out:
                out[meta.symbol] = _merge_meta(out[meta.symbol], meta)
            else:
                out[meta.symbol] = meta
    return out


def load_hook_meta(
    watchlist_path: str | Path = "config/ta_watchlist.yaml",
    portfolio_path: str | Path = "config/portfolio_watch.yaml",
) -> dict[str, TickerMeta]:
    """Merge ta_watchlist + portfolio_watch (portfolio wins on conflicts)."""
    out: dict[str, TickerMeta] = {}
    wl = Path(watchlist_path)
    if wl.exists():
        out.update(parse_watchlist(wl))
    for sym, meta in parse_portfolio_watch(portfolio_path).items():
        out[sym] = _merge_meta(out[sym], meta) if sym in out else meta
    if len(out) > 20:
        # keep deterministic trim: holdings-like (with stop/no_add) first
        ranked = sorted(
            out.values(),
            key=lambda m: (0 if m.stop is not None or m.no_add or m.band_lo is not None else 1, m.symbol),
        )
        out = {m.symbol: m for m in ranked[:20]}
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

    # 2) Policy no-add
    if meta.no_add and action in ADD_ACTIONS:
        action = "대기"
        overrides.append("NO_ADD")
        reasons.append("포트 정책 추가금지")

    # 3) Price band — block adds outside; clip entry when inside
    if meta.band_lo is not None and meta.band_hi is not None:
        lo, hi = meta.band_lo, meta.band_hi
        px = result.close
        if px == px:  # not NaN
            if px < lo or px > hi:
                side = "상단초과" if px > hi else "하단미달"
                if action in ADD_ACTIONS or ta_action in ADD_ACTIONS:
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

    # 4) Stop — exit/reduce review (wins over add waits for action label)
    px = result.close
    if meta.stop is not None and px == px and px <= meta.stop:
        action = "축소검토"
        overrides.append("STOP")
        reasons.append(f"손절가 ${meta.stop:g} 이하 (종가 ${px:g})")

    # 5) Take-profit — prefer over plain hold/wait; STOP wins if both
    elif meta.tp1 is not None and px == px and px >= meta.tp1:
        action = "익절검토"
        overrides.append("TP")
        if meta.tp2 is not None and px >= meta.tp2:
            reasons.append(f"익절 tp2 ${meta.tp2:g}+ (종가 ${px:g})")
        else:
            tp2_note = f" · tp2 ${meta.tp2:g}" if meta.tp2 is not None else ""
            reasons.append(f"익절 tp1 ${meta.tp1:g}+ (종가 ${px:g}){tp2_note}")

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
