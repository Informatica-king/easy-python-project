"""Timing gate (GO / WAIT / BLOCK) — former A′/B/SOFT, role narrowed.

Timing answers only: *is the entry seat OK right now?*
It does **not** select which stock is good (that is pick_pool / Chase).

Statuses:
- GO_A  — shallow pullback (legacy A′)
- GO_B  — breakout+volume (legacy B); default OFF for soldier premkt OS
- WAIT  — directionally close / extended / soft miss
- BLOCK — confirmed EARN_D5 or explicit block

Soldier note: user can trade KR 17:30–20:55 only (= US pre-market).
GO_B chase-into-RTH is usually not executable → prefer GO_A + limit plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from sepa.earn_calendar import EarnDateInfo, earn_info_from_row

TimingStatus = Literal["GO_A", "GO_B", "WAIT", "BLOCK"]

# Thresholds (aligned with former RS≥70 A′ agreement — name only; RS not computed here)
NEAR_MA20_PCT = 3.0
NEAR_SWING_L_PCT = 3.0
SWING_LOOKBACK = 20
BREAKOUT_PCT = 0.0  # close >= swing high
VOL_OK_RATIO = 0.8
VOL_HOT_RATIO = 1.5
RSI_A_LO, RSI_A_HI = 42.0, 62.0
PCT_HI_LO, PCT_HI_HI = -0.08, -0.01

# Soldier / premkt OS: breakout GO_B does not create 실행 by default
ALLOW_GO_B_EXEC = False


@dataclass(frozen=True)
class TimingResult:
    ticker: str
    status: TimingStatus
    legacy_scenario: str  # A | B | SOFT | "" for debug/compat
    reason: str
    rsi: float | None = None
    pct_hi: float | None = None
    vs_ma20: float | None = None
    earn_d5_confirmed: bool = False
    earn_estimate_warn: bool = False

    @property
    def is_go(self) -> bool:
        if self.status == "GO_A":
            return True
        if self.status == "GO_B":
            return ALLOW_GO_B_EXEC
        return False

    @property
    def is_wait(self) -> bool:
        return self.status == "WAIT" or (self.status == "GO_B" and not ALLOW_GO_B_EXEC)


def legacy_scenario_to_timing(scenario: str) -> TimingStatus:
    s = (scenario or "").strip().upper()
    if s in ("A", "A'"):
        return "GO_A"
    if s == "B":
        return "GO_B"
    if s == "SOFT":
        return "WAIT"
    return "WAIT"


def timing_from_scenario_row(
    row: dict[str, Any],
    *,
    as_of: date | None = None,
) -> TimingResult:
    """Map a buy_scenarios_*.json row into TimingResult (no network)."""
    t = str(row.get("t") or row.get("ticker") or "").upper()
    scen = str(row.get("scenario") or "")
    status = legacy_scenario_to_timing(scen)
    earn = earn_info_from_row(row, default_source="estimate")
    asof = as_of or date.today()
    earn_block = earn.blocks_new_buys(asof)
    earn_warn = earn.warn_estimate_window(asof)
    if earn_block:
        status = "BLOCK"
        reason = f"EARN_D5 확정 · {earn.earn_date}"
    elif status == "GO_A":
        reason = "타이밍 GO_A(눌림)"
    elif status == "GO_B":
        if ALLOW_GO_B_EXEC:
            reason = "타이밍 GO_B(돌파)"
        else:
            status = "WAIT"
            reason = "타이밍 WAIT(돌파·프리마켓비실행)"
    elif scen.upper() == "SOFT":
        reason = "타이밍 WAIT(SOFT 근접)"
    else:
        reason = "타이밍 WAIT(미분류)"
    if earn_warn and status != "BLOCK":
        reason += f" · 추정실적창주의({earn.earn_date})"
    return TimingResult(
        ticker=t,
        status=status,
        legacy_scenario=scen if scen else "",
        reason=reason,
        rsi=float(row["rsi"]) if row.get("rsi") is not None else None,
        pct_hi=float(row["pct_hi"]) if row.get("pct_hi") is not None else None,
        vs_ma20=float(row["vs_ma20"]) if row.get("vs_ma20") is not None else None,
        earn_d5_confirmed=earn_block,
        earn_estimate_warn=earn_warn,
    )


def evaluate_timing_metrics(
    *,
    ticker: str,
    above200: bool,
    align: bool,
    near_ma20: bool,
    near_swing_l: bool,
    rsi: float,
    pct_hi: float,
    vol_ok: bool,
    vol_hot: bool,
    breakout: bool,
    earn: EarnDateInfo | None = None,
    as_of: date | None = None,
) -> TimingResult:
    """Compute timing from raw metrics (shared with scanners)."""
    asof = as_of or date.today()
    earn = earn or EarnDateInfo(None, "unknown")
    if earn.blocks_new_buys(asof):
        return TimingResult(
            ticker=ticker.upper(),
            status="BLOCK",
            legacy_scenario="",
            reason=f"EARN_D5 확정 · {earn.earn_date}",
            rsi=rsi,
            pct_hi=pct_hi,
            earn_d5_confirmed=True,
        )

    a_ok = (
        above200
        and align
        and (near_ma20 or near_swing_l)
        and (RSI_A_LO <= rsi <= RSI_A_HI)
        and (PCT_HI_LO <= pct_hi <= PCT_HI_HI)
        and vol_ok
    )
    b_ok = breakout and vol_hot and rsi < 70

    if a_ok:
        status: TimingStatus = "GO_A"
        legacy = "A"
        reason = "타이밍 GO_A(눌림)"
    elif b_ok:
        status = "GO_B" if ALLOW_GO_B_EXEC else "WAIT"
        legacy = "B"
        reason = "타이밍 GO_B(돌파)" if ALLOW_GO_B_EXEC else "타이밍 WAIT(돌파·프리마켓비실행)"
    else:
        # SOFT-like: trend ok, miss 1–2 of rsi/pct_hi/vol
        soft = False
        if above200 and align and (near_ma20 or near_swing_l):
            misses = 0
            if not (RSI_A_LO <= rsi <= RSI_A_HI):
                misses += 1
            if not (PCT_HI_LO <= pct_hi <= PCT_HI_HI):
                misses += 1
            if not vol_ok:
                misses += 1
            soft = 1 <= misses <= 2
        status = "WAIT"
        legacy = "SOFT" if soft else ""
        reason = "타이밍 WAIT(근접)" if soft else "타이밍 WAIT(자리아님)"

    if earn.warn_estimate_window(asof):
        reason += f" · 추정실적창주의({earn.earn_date})"

    return TimingResult(
        ticker=ticker.upper(),
        status=status,
        legacy_scenario=legacy,
        reason=reason,
        rsi=rsi,
        pct_hi=pct_hi,
        earn_d5_confirmed=False,
        earn_estimate_warn=earn.warn_estimate_window(asof),
    )
