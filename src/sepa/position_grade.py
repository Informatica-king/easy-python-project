"""종목 비중 천장 — 품질등급(A/B/C) 폐기 후 단일 캡.

정책 (2026-09-23+):
  * 종목당 최대 보유 비중 = 20% (유동자산=주식+현금 대비)
  * 하드게이트/NO_ADD → ADD 0%
  * Top-3 합 ≤ 50% (동일하게 유동자산 대비)
  * 현금바닥 $150 (portfolio_ops)

See reports/POSITION_GRADE_SIZING.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Single per-name cap (vs liquid assets = equity + cash)
NAME_CAP = 0.20
MAX_PCT_BAN = 0.0
ABSOLUTE_CEILING = NAME_CAP  # alias — ceiling == name cap
TOP3_CAP = 0.50

# Backward-compat aliases (all tradeable grades collapse to 20%)
MAX_PCT_A = NAME_CAP
MAX_PCT_B = NAME_CAP
MAX_PCT_C = NAME_CAP
GRADE_MAX: dict[str, float] = {
    "A": NAME_CAP,
    "B": NAME_CAP,
    "C": NAME_CAP,
    "OK": NAME_CAP,
    "금지": MAX_PCT_BAN,
}


@dataclass
class PositionGrade:
    grade: str  # OK | 금지  (legacy A/B/C may appear only as unused hints)
    max_pct: float
    quality_grade: str = "—"  # deprecated; kept for API compat
    reasons: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        if self.grade == "금지" or self.max_pct <= 0:
            return "금지·ADD0"
        return f"종목천장{self.max_pct*100:.0f}%"


def quality_grade_from_scores(
    *,
    l1: int,
    l2: int,
    l3: int,
    total: int,
    l3_grade: str = "N/A",
    shrink: bool = False,
) -> str:
    """Deprecated — quality grades removed. Always returns unused hint '—'."""
    return "—"


def assign_position_grade(
    *,
    l1: int | None = None,
    l2: int | None = None,
    l3: int | None = None,
    total: int | None = None,
    l3_grade: str = "N/A",
    pass_forced: bool = False,
    shrink: bool = False,
    earn_d5: bool = False,
    no_add: bool = False,
    upside: float | None = None,
    has_stop: bool = True,
    overheated: bool = False,
    yaml_grade: str | None = None,
) -> PositionGrade:
    """Return ADD cap: 20% if clear, else 금지/0%.

    Quality yaml_grade / BuyScore tiers no longer change the size cap.
    Hard gates still force ADD 0%.
    """
    del l2, l3, total, yaml_grade  # unused after grade removal
    reasons: list[str] = []

    if earn_d5:
        reasons.append("EARN_D5")
    if no_add:
        reasons.append("NO_ADD")
    if pass_forced or (l1 is not None and l1 == 0):
        reasons.append("L1=0/강제패스")
    if shrink or str(l3_grade).upper() == "C":
        reasons.append("가이드C")
    if upside is not None and upside < 0:
        reasons.append("업사이드음수")
    if not has_stop:
        reasons.append("손절없음")
    if overheated:
        reasons.append("과열")

    if reasons:
        return PositionGrade(
            grade="금지",
            max_pct=MAX_PCT_BAN,
            quality_grade="—",
            reasons=reasons,
        )

    return PositionGrade(
        grade="OK",
        max_pct=NAME_CAP,
        quality_grade="—",
        reasons=["천장20%"],
    )


def assign_from_buy_score(
    sc: Any | None,
    *,
    earn_d5: bool = False,
    no_add: bool = False,
    upside: float | None = None,
    has_stop: bool = True,
    overheated: bool = False,
    yaml_grade: str | None = None,
) -> PositionGrade:
    if sc is None:
        return assign_position_grade(
            earn_d5=earn_d5,
            no_add=no_add,
            upside=upside,
            has_stop=has_stop,
            overheated=overheated,
            yaml_grade=yaml_grade,
        )
    return assign_position_grade(
        l1=getattr(sc, "l1", None),
        l2=getattr(sc, "l2", None),
        l3=getattr(sc, "l3", None),
        total=getattr(sc, "total", None),
        l3_grade=getattr(sc, "l3_grade", "N/A") or "N/A",
        pass_forced=bool(getattr(sc, "pass_forced", False)),
        shrink=getattr(sc, "recommend", "") == "축소후보",
        earn_d5=earn_d5,
        no_add=no_add,
        upside=upside,
        has_stop=has_stop,
        overheated=overheated,
        yaml_grade=yaml_grade,
    )


def weight_status(w_liquid: float | None, max_pct: float) -> str | None:
    """Return OVER / 상단 / None vs allowed max (weight is vs liquid assets)."""
    if w_liquid is None:
        return None
    if max_pct <= 0:
        if w_liquid >= ABSOLUTE_CEILING:
            return "천장OVER"
        if w_liquid > 0.12:
            return "비중주의"
        return None
    if w_liquid >= ABSOLUTE_CEILING or w_liquid > max_pct + 0.02:
        return "비중OVER"
    if w_liquid > max_pct:
        return "비증상단"
    return None


def top3_over_cap(weights: list[float], *, cap: float = TOP3_CAP) -> bool:
    """True if top-3 liquid weights sum above cap (default 50%)."""
    top = sorted((w for w in weights if w is not None), reverse=True)[:3]
    return sum(top) > cap + 1e-9
