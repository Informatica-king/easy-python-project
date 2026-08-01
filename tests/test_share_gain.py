"""Tests for competitive share-gain bonus + deep-analysis notes."""

from sepa.rev_compete import is_subject_share_name, subject_share_delta
from sepa.share_gain import (
    BASE_BONUS,
    MARGIN_HOLD_BONUS,
    annotate_text,
    apply_share_bonus,
    assess_share_gain,
    enrich_qual_fields,
    enrich_rank_row,
)


def test_subject_aliases():
    assert is_subject_share_name("AMRX", "Amneal")
    assert is_subject_share_name("ECPG", "Encore (ECPG)")
    assert is_subject_share_name("TXG", "10x Genomics")
    assert not is_subject_share_name("AMRX", "Teva")


def test_rising_tickers_get_bonus():
    for t, expected_delta in [
        ("ECPG", 3.0),
        ("AMRX", 1.5),
        ("TXG", 3.0),
        ("SBLK", 2.0),
        ("NESR", 1.5),
        ("CLMT", 2.0),
        ("LASR", 1.5),
        ("RELY", 0.4),
    ]:
        a = assess_share_gain(t)
        assert abs(a.delta_pp - expected_delta) < 1e-9
        assert a.rising is True
        assert abs(a.bonus - BASE_BONUS) < 1e-9
        assert "가산" in a.strat_note
        assert "점유율 꾸준" in a.chase_note


def test_margin_hold_extra_bonus():
    a = assess_share_gain("ECPG", margin_delta_pp=1.0)
    assert abs(a.bonus - (BASE_BONUS + MARGIN_HOLD_BONUS)) < 1e-9
    assert "마진유지" in a.strat_note


def test_margin_deteriorate_cancels_bonus():
    a = assess_share_gain("ECPG", margin_delta_pp=-2.0)
    assert a.cancelled_margin is True
    assert a.bonus == 0.0
    assert "가산취소" in a.strat_note


def test_falling_share_no_bonus():
    a = assess_share_gain("ROKU")
    assert a.delta_pp == -2.0
    assert a.rising is False
    assert a.bonus == 0.0
    assert "하락" in a.strat_note

    a2 = assess_share_gain("ACHC")
    assert a2.delta_pp == -1.0
    assert a2.bonus == 0.0


def test_tiny_delta_no_bonus():
    # PEBO +0.1pp < 0.3 threshold
    a = assess_share_gain("PEBO")
    assert abs(a.delta_pp - 0.1) < 1e-9
    assert a.rising is False
    assert a.bonus == 0.0


def test_unknown_ticker():
    a = assess_share_gain("ZZZZ")
    assert a.delta_pp is None
    assert a.bonus == 0.0


def test_enrich_rank_row_idempotent():
    row = {"t": "TXG", "chase_raw": 4.0}
    enrich_rank_row(row)
    assert abs(row["chase_raw"] - (4.0 + BASE_BONUS)) < 1e-9
    enrich_rank_row(row)
    assert abs(row["chase_raw"] - (4.0 + BASE_BONUS)) < 1e-9
    assert row["share_rising"] is True


def test_enrich_qual_and_annotate():
    q = enrich_qual_fields({"strat": "위성·눌림"}, assess_share_gain("AMRX"))
    assert "경쟁점유" in q["strat"]
    assert "가산" in q["strat"]
    # idempotent
    q2 = enrich_qual_fields(q, assess_share_gain("AMRX"))
    assert q2["strat"].count("경쟁점유") == 1
    assert annotate_text("상 — RR", "점유율 꾸준 상승(+1.5pp) — 경쟁력 가산").endswith("가산")


def test_apply_share_bonus_math():
    a = assess_share_gain("SBLK")
    assert apply_share_bonus(2.0, a) == 2.0 + BASE_BONUS


def test_subject_share_delta_helper():
    assert subject_share_delta("ECPG") == 3.0
    assert subject_share_delta("ROKU") == -2.0
