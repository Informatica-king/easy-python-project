"""Tests for flat name-cap (20%) position sizing — A/B/C grades removed."""

from sepa.position_grade import (
    MAX_PCT_A,
    MAX_PCT_BAN,
    NAME_CAP,
    assign_from_buy_score,
    assign_position_grade,
    quality_grade_from_scores,
    top3_over_cap,
    weight_status,
)


def test_quality_grade_deprecated_returns_dash():
    assert quality_grade_from_scores(l1=2, l2=1, l3=1, total=4) == "—"
    assert quality_grade_from_scores(l1=1, l2=1, l3=0, total=2) == "—"
    assert quality_grade_from_scores(l1=0, l2=2, l3=0, total=2) == "—"


def test_hard_gate_no_add_forces_ban():
    pg = assign_position_grade(
        l1=2, l2=1, l3=1, total=4, no_add=True, has_stop=True
    )
    assert pg.grade == "금지"
    assert pg.max_pct == MAX_PCT_BAN
    assert pg.quality_grade == "—"
    assert "NO_ADD" in pg.reasons


def test_hard_gate_earn_d5_and_no_stop():
    pg = assign_position_grade(yaml_grade="B", earn_d5=True, has_stop=False)
    assert pg.grade == "금지"
    assert "EARN_D5" in pg.reasons
    assert "손절없음" in pg.reasons
    assert pg.quality_grade == "—"


def test_clear_gates_return_name_cap():
    a = assign_position_grade(l1=2, l2=1, l3=1, total=4, has_stop=True)
    assert a.grade == "OK" and a.max_pct == NAME_CAP
    b = assign_position_grade(l1=1, l2=1, l3=0, total=2, has_stop=True)
    assert b.grade == "OK" and b.max_pct == NAME_CAP
    c = assign_position_grade(yaml_grade="C", has_stop=True)
    assert c.grade == "OK" and c.max_pct == NAME_CAP
    # Legacy aliases collapse to the same 20% cap
    assert MAX_PCT_A == NAME_CAP == 0.20


def test_assign_from_buy_score_none_ignores_yaml_grade():
    pg = assign_from_buy_score(None, yaml_grade="A", has_stop=True)
    assert pg.grade == "OK"
    assert pg.max_pct == NAME_CAP
    assert pg.quality_grade == "—"


def test_weight_status_vs_name_cap():
    assert weight_status(0.19, NAME_CAP) is None
    assert weight_status(0.20, NAME_CAP) == "비중OVER"  # at/over flat 20% ceiling
    assert weight_status(0.21, NAME_CAP) == "비중OVER"
    assert weight_status(0.09, NAME_CAP) is None
    assert weight_status(0.15, 0.0) == "비중주의"


def test_name_cap_uses_liquid_not_equity():
    """21% of equity can be <20% of liquid (stocks+cash) — must not flag OVER."""
    # TXG-like: ~21% equity, ~17% liquid with ~15% cash
    assert weight_status(0.211, NAME_CAP) == "비중OVER"  # equity basis would OVER
    assert weight_status(0.173, NAME_CAP) is None  # liquid basis OK


def test_top3_cap():
    assert top3_over_cap([0.21, 0.18, 0.15, 0.10]) is True
    assert top3_over_cap([0.10, 0.10, 0.10, 0.10]) is False
    # Current snap-like liquid top3 ~46.8% — under 50%
    assert top3_over_cap([0.173, 0.161, 0.134, 0.095]) is False
