"""Tests for mechanical A/B/C/금지 position grading."""

from sepa.position_grade import (
    MAX_PCT_A,
    MAX_PCT_B,
    MAX_PCT_BAN,
    MAX_PCT_C,
    assign_from_buy_score,
    assign_position_grade,
    quality_grade_from_scores,
    top3_over_cap,
    weight_status,
)


def test_quality_a_b_c():
    assert quality_grade_from_scores(l1=2, l2=1, l3=1, total=4) == "A"
    assert quality_grade_from_scores(l1=1, l2=1, l3=0, total=2) == "B"
    assert quality_grade_from_scores(l1=1, l2=0, l3=0, total=1) == "C"
    assert quality_grade_from_scores(l1=0, l2=2, l3=0, total=2) == "C"
    assert quality_grade_from_scores(l1=2, l2=1, l3=0, total=3, l3_grade="C") == "C"


def test_hard_gate_no_add_forces_ban():
    pg = assign_position_grade(
        l1=2, l2=1, l3=1, total=4, no_add=True, has_stop=True
    )
    assert pg.grade == "금지"
    assert pg.max_pct == MAX_PCT_BAN
    assert pg.quality_grade == "A"
    assert "NO_ADD" in pg.reasons


def test_hard_gate_earn_d5_and_no_stop():
    pg = assign_position_grade(yaml_grade="B", earn_d5=True, has_stop=False)
    assert pg.grade == "금지"
    assert "EARN_D5" in pg.reasons
    assert "손절없음" in pg.reasons
    assert pg.quality_grade == "B"


def test_quality_pass_returns_caps():
    a = assign_position_grade(l1=2, l2=1, l3=1, total=4, has_stop=True)
    assert a.grade == "A" and a.max_pct == MAX_PCT_A
    b = assign_position_grade(l1=1, l2=1, l3=0, total=2, has_stop=True)
    assert b.grade == "B" and b.max_pct == MAX_PCT_B
    c = assign_position_grade(yaml_grade="C", has_stop=True)
    assert c.grade == "C" and c.max_pct == MAX_PCT_C


def test_assign_from_buy_score_none_uses_yaml():
    pg = assign_from_buy_score(None, yaml_grade="A", has_stop=True)
    assert pg.grade == "A"
    assert pg.max_pct == MAX_PCT_A


def test_weight_status_vs_cap():
    assert weight_status(0.19, 0.18) == "비증상단"
    assert weight_status(0.21, 0.18) == "비중OVER"
    assert weight_status(0.09, 0.10) is None
    assert weight_status(0.15, 0.0) == "비중주의"


def test_top3_cap():
    assert top3_over_cap([0.21, 0.18, 0.15, 0.10]) is True
    assert top3_over_cap([0.10, 0.10, 0.10, 0.10]) is False
