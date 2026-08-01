"""Competitive share-gain bonus for Chase RR scoring + deep-analysis comments.

Rule (v1 — two-period curated share panels in ``sepa.rev_compete``):

* Subject share Δ ≥ ``MIN_DELTA_PP`` → base 가산점 + 심층 코멘트
* Same + operating/net margin YoY Δ ≥ 0 → extra 가산점
* Share ↑ but margin ↓ → **no** bonus (가격경쟁·저마진 수주 가드)

Multi-year "steadily" series can extend ``share_rows`` later; today Δ>0 vs prior
period is the steady-rise proxy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sepa.rev_compete import (
    PEER_PROFILES,
    get_profile,
    subject_share_row_from_profile,
)

# Ignore tiny noise (e.g. +0.1pp community-bank deposit share).
MIN_DELTA_PP = 0.3
BASE_BONUS = 0.35
MARGIN_HOLD_BONUS = 0.15


@dataclass(frozen=True)
class ShareGainAssessment:
    ticker: str
    delta_pp: float | None
    current: float | None
    prior: float | None
    rising: bool
    margin_hold: bool | None
    cancelled_margin: bool
    bonus: float
    strat_note: str
    chase_note: str

    def as_rank_fields(self) -> dict[str, Any]:
        return {
            "share_delta_pp": self.delta_pp,
            "share_bonus": self.bonus,
            "share_rising": self.rising,
            "share_margin_hold": self.margin_hold,
            "share_bonus_cancelled": self.cancelled_margin,
        }


def _empty(ticker: str) -> ShareGainAssessment:
    return ShareGainAssessment(
        ticker=ticker.upper(),
        delta_pp=None,
        current=None,
        prior=None,
        rising=False,
        margin_hold=None,
        cancelled_margin=False,
        bonus=0.0,
        strat_note="",
        chase_note="",
    )


def assess_share_gain(
    ticker: str,
    *,
    margin_delta_pp: float | None = None,
    min_delta_pp: float = MIN_DELTA_PP,
    base_bonus: float = BASE_BONUS,
    margin_bonus: float = MARGIN_HOLD_BONUS,
) -> ShareGainAssessment:
    """Return share-gain assessment for *ticker* (offline; uses PEER_PROFILES)."""
    t = ticker.upper()
    prof = get_profile(t)
    if not prof:
        return _empty(t)
    row = subject_share_row_from_profile(t, prof)
    if row is None:
        return _empty(t)

    delta = float(row.delta_pp)
    rising = delta >= min_delta_pp
    margin_hold: bool | None
    if margin_delta_pp is None:
        margin_hold = None
    else:
        margin_hold = float(margin_delta_pp) >= 0.0

    cancelled = bool(rising and margin_hold is False)
    bonus = 0.0
    if rising and not cancelled:
        bonus = base_bonus
        if margin_hold is True:
            bonus += margin_bonus

    strat_note = ""
    chase_note = ""
    if rising and cancelled:
        strat_note = (
            f"경쟁점유 +{delta:.1f}pp이나 마진악화 → 가산취소"
            .replace("\u2212", "-")
        )
        chase_note = strat_note
    elif rising:
        if margin_hold is True:
            strat_note = (
                f"경쟁점유 +{delta:.1f}pp 가산(+{bonus:.2f}) · 마진유지"
                .replace("\u2212", "-")
            )
        else:
            strat_note = (
                f"경쟁점유 +{delta:.1f}pp 가산(+{bonus:.2f})"
                .replace("\u2212", "-")
            )
        chase_note = (
            f"점유율 꾸준 상승(+{delta:.1f}pp) — 경쟁력 가산"
            .replace("\u2212", "-")
        )
    elif delta < -min_delta_pp:
        # Soft note only — no score penalty in v1 (감점은 별도 룰).
        strat_note = f"경쟁점유 {delta:+.1f}pp (하락 모니터)".replace("\u2212", "-")
        chase_note = strat_note

    return ShareGainAssessment(
        ticker=t,
        delta_pp=delta,
        current=float(row.current),
        prior=float(row.prior),
        rising=rising,
        margin_hold=margin_hold,
        cancelled_margin=cancelled,
        bonus=float(bonus),
        strat_note=strat_note,
        chase_note=chase_note,
    )


def apply_share_bonus(chase_raw: float, assessment: ShareGainAssessment) -> float:
    """Add share-gain bonus to Chase RR raw score."""
    return float(chase_raw) + float(assessment.bonus)


def annotate_text(existing: str | None, note: str) -> str:
    """Append share note once (idempotent)."""
    base = (existing or "").strip()
    note = (note or "").strip()
    if not note:
        return base or "—"
    if "경쟁점유" in base or "점유율 꾸준" in base:
        return base
    if not base or base == "—":
        return note
    return f"{base} · {note}"


def enrich_rank_row(row: dict[str, Any], *, margin_delta_pp: float | None = None) -> ShareGainAssessment:
    """Mutate *row* with share fields and bump ``chase_raw``."""
    t = str(row.get("t") or row.get("ticker") or "")
    assessment = assess_share_gain(t, margin_delta_pp=margin_delta_pp)
    row.update(assessment.as_rank_fields())
    if "chase_raw" in row and assessment.bonus:
        # Avoid double-application if already enriched.
        if not row.get("_share_bonus_applied"):
            row["chase_raw"] = apply_share_bonus(float(row["chase_raw"]), assessment)
            row["_share_bonus_applied"] = True
    return assessment


def enrich_qual_fields(qual: dict[str, Any], assessment: ShareGainAssessment) -> dict[str, Any]:
    """Append share-gain notes into deep-analysis qual ``strat`` / optional tag."""
    out = dict(qual)
    if assessment.strat_note:
        out["strat"] = annotate_text(out.get("strat"), assessment.strat_note)
        out["share_gain_note"] = assessment.strat_note
    if assessment.rising and assessment.bonus > 0:
        out["share_rising"] = True
        out["share_delta_pp"] = assessment.delta_pp
        out["share_bonus"] = assessment.bonus
    return out


FORMULA_SHARE_SUFFIX = "+ share_gain_bonus(≥+0.3pp, 마진악화시 취소)"


def profiled_tickers() -> list[str]:
    return sorted(PEER_PROFILES.keys())


# Re-export for callers that only need the row finder via share_gain
def subject_share_delta(ticker: str) -> float | None:
    a = assess_share_gain(ticker)
    return a.delta_pp
