"""Pick pool — '좋은 종목' first (Chase-led).

Buy signal = pick_pool (quality) ∩ timing_gate (GO).
Pick pool does **not** require A′/timing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sepa.chase_select import (
    ChaseRow,
    is_excluded,
    parse_chase_rows,
    select_buy_candidates,
)

# Max names kept as 본선 (watch + exec candidates)
MAX_PICK_POOL = 15


@dataclass(frozen=True)
class PickRow:
    ticker: str
    rank: int
    chase: str
    px: float | None = None
    upside: float | None = None
    earn_date: str | None = None
    sector: str | None = None
    source: str = "chase"  # chase | scenario_fallback


def build_pick_pool(
    chase: dict[str, Any] | None,
    scenarios: dict[str, Any] | None = None,
    *,
    max_n: int = MAX_PICK_POOL,
) -> list[PickRow]:
    """Build ordered pick pool.

    Primary: Chase include rules (최상/상/중상/…).
    Fallback (no chase file): scenario rows with upside≥0 (legacy/dev).
    """
    upside_map: dict[str, float] = {}
    sector_map: dict[str, str] = {}
    px_map: dict[str, float] = {}
    earn_map: dict[str, str] = {}
    if scenarios:
        for r in scenarios.get("rows") or []:
            t = str(r.get("t") or r.get("ticker") or "").upper()
            if not t:
                continue
            if r.get("upside") is not None:
                upside_map[t] = float(r["upside"])
            if r.get("sector"):
                sector_map[t] = str(r["sector"])
            px = r.get("last") if r.get("last") is not None else r.get("px")
            if px is not None:
                px_map[t] = float(px)
            ed = r.get("earnDate") or r.get("earn_date")
            if ed:
                earn_map[t] = str(ed)[:10]

    picks: list[PickRow] = []
    if chase and (chase.get("rows") or []):
        rows = parse_chase_rows(chase["rows"])
        selected = select_buy_candidates(rows, max_n=max_n)
        for cr in selected:
            picks.append(
                PickRow(
                    ticker=cr.ticker,
                    rank=cr.rank,
                    chase=cr.chase,
                    px=cr.px if cr.px is not None else px_map.get(cr.ticker),
                    upside=upside_map.get(cr.ticker),
                    earn_date=cr.earn_date or earn_map.get(cr.ticker),
                    sector=sector_map.get(cr.ticker),
                    source="chase",
                )
            )
        return picks

    # Fallback: scenario tickers (when Chase snapshot missing)
    if scenarios:
        for r in scenarios.get("rows") or []:
            t = str(r.get("t") or "").upper()
            if not t:
                continue
            ups = r.get("upside")
            if ups is not None and float(ups) < 0:
                continue
            scen = str(r.get("scenario") or "")
            # keep a synthetic chase label for downstream filters
            chase_lab = "중·시나리오폴백"
            picks.append(
                PickRow(
                    ticker=t,
                    rank=len(picks) + 1,
                    chase=chase_lab,
                    px=float(r["last"]) if r.get("last") is not None else (
                        float(r["px"]) if r.get("px") is not None else None
                    ),
                    upside=float(ups) if ups is not None else None,
                    earn_date=str(r.get("earnDate") or r.get("earn_date") or "")[:10] or None,
                    sector=str(r.get("sector") or "") or None,
                    source="scenario_fallback",
                )
            )
            if len(picks) >= max_n:
                break
    return picks


def chase_label_blocks_pick(chase: str) -> bool:
    """True if chase label should never be a pick (과열/중하/…)."""
    return is_excluded(chase or "")


def find_pick_go_hits(
    chase: dict[str, Any] | None,
    scenarios: dict[str, Any] | list[dict[str, Any]] | None,
    *,
    as_of: Any = None,
    max_n: int = MAX_PICK_POOL,
) -> list[dict[str, Any]]:
    """본선(pick_pool) ∩ 타이밍 GO — deep PDF / 포폴 강조용 (로컬만).

    Returns list of dicts: ticker, rank, chase, timing, scenario, px, limit note fields.
    Empty when no overlap (common on hot days).
    """
    from datetime import date as _date

    from sepa.timing_gate import timing_from_scenario_row

    if isinstance(scenarios, list):
        scen_payload: dict[str, Any] = {"rows": scenarios}
    else:
        scen_payload = scenarios or {"rows": []}

    asof = as_of or _date.today()
    if isinstance(asof, str):
        asof = _date.fromisoformat(asof[:10])

    picks = build_pick_pool(chase, scen_payload, max_n=max_n)
    scen_by: dict[str, dict[str, Any]] = {}
    for r in scen_payload.get("rows") or []:
        t = str(r.get("t") or r.get("ticker") or "").upper()
        if t:
            scen_by[t] = r

    hits: list[dict[str, Any]] = []
    for p in picks:
        sr = scen_by.get(p.ticker)
        if not sr:
            continue
        timing = timing_from_scenario_row(sr, as_of=asof)
        if not timing.is_go:
            continue
        px = p.px
        if px is None:
            raw = sr.get("last") if sr.get("last") is not None else sr.get("px")
            px = float(raw) if raw is not None else None
        hits.append(
            {
                "ticker": p.ticker,
                "rank": p.rank,
                "chase": p.chase,
                "timing": timing.status,
                "scenario": timing.legacy_scenario or sr.get("scenario") or "",
                "px": px,
                "rsi": timing.rsi,
                "pct_hi": timing.pct_hi,
                "reason": timing.reason,
                "earn_source": sr.get("earn_source"),
                "earnDate": sr.get("earnDate") or p.earn_date,
            }
        )
    return hits
