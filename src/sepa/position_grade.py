"""기계적 비중 등급 (A/B/C/금지) — 코어·위성 대체.

감정·라벨 없이 L1/L2/L3 + 하드게이트로 max_pct만 결정.
See reports/POSITION_GRADE_SIZING.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Stock-weight caps (vs equity, cash excluded)
MAX_PCT_A = 0.18
MAX_PCT_B = 0.10
MAX_PCT_C = 0.06
MAX_PCT_BAN = 0.0
ABSOLUTE_CEILING = 0.20  # hard ceiling even for A
TOP3_CAP = 0.50

GRADE_MAX: dict[str, float] = {
    "A": MAX_PCT_A,
    "B": MAX_PCT_B,
    "C": MAX_PCT_C,
    "금지": MAX_PCT_BAN,
}


@dataclass
class PositionGrade:
    grade: str  # A | B | C | 금지
    max_pct: float
    quality_grade: str  # A|B|C before hard gates (금지 시에도 품질 힌트)
    reasons: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.grade}·맥스{self.max_pct*100:.0f}%"


def quality_grade_from_scores(
    *,
    l1: int,
    l2: int,
    l3: int,
    total: int,
    l3_grade: str = "N/A",
    shrink: bool = False,
) -> str:
    """Quality only (no hard gates). C is weakest tradeable quality."""
    if shrink or str(l3_grade).upper() == "C":
        return "C"
    if l1 >= 2 and l2 >= 1 and str(l3_grade).upper() != "C":
        return "A"
    if l1 >= 1 and (l2 >= 1 or total >= 2):
        return "B"
    if l1 >= 1:
        return "C"
    return "C"


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
    """Return effective sizing grade.

    Hard gates → 금지 (max 0% add) regardless of quality.
    If scores missing, fall back to yaml_grade or C.
    """
    reasons: list[str] = []

    if l1 is None or l2 is None:
        q = (yaml_grade or "C").upper().replace("금", "금지")
        if q not in ("A", "B", "C", "금지"):
            q = "C"
        quality = q if q != "금지" else "C"
    else:
        quality = quality_grade_from_scores(
            l1=int(l1),
            l2=int(l2),
            l3=int(l3 or 0),
            total=int(total if total is not None else (l1 or 0) + (l2 or 0) + (l3 or 0)),
            l3_grade=l3_grade,
            shrink=shrink,
        )

    # Hard gates
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
            quality_grade=quality,
            reasons=reasons,
        )

    max_pct = GRADE_MAX.get(quality, MAX_PCT_C)
    return PositionGrade(
        grade=quality,
        max_pct=max_pct,
        quality_grade=quality,
        reasons=["품질통과"],
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


def weight_status(w_stock: float | None, max_pct: float) -> str | None:
    """Return OVER / 상단 / None vs allowed max."""
    if w_stock is None:
        return None
    if max_pct <= 0:
        if w_stock >= ABSOLUTE_CEILING:
            return "천장OVER"
        if w_stock > 0.12:
            return "비중주의"
        return None
    if w_stock >= ABSOLUTE_CEILING or w_stock > max_pct + 0.02:
        return "비중OVER"
    if w_stock > max_pct:
        return "비증상단"
    return None


def top3_over_cap(weights: list[float], *, cap: float = TOP3_CAP) -> bool:
    top = sorted((w for w in weights if w is not None), reverse=True)[:3]
    return sum(top) > cap + 1e-9
