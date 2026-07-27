import pytest

from sepa.config import VCPParams
from sepa.vcp import Contraction, Signal, detect_vcp, zigzag_from_high, _merge_minor_contractions
from synthetic import add_breakout_day, make_vcp_frame

P = VCPParams()


def test_merge_minor_contractions_absorbs_noise_wiggles():
    # 100->80, weak bounce to 84 (retrace 20% < 50%), then deeper low 78:
    # the second leg is noise inside the first contraction.
    contractions = [
        Contraction(0, 100.0, 10, 80.0),
        Contraction(15, 84.0, 20, 78.0),
        Contraction(30, 95.0, 35, 88.0),  # rally retraced >50% -> distinct
    ]
    merged = _merge_minor_contractions(contractions, min_retrace=0.5)
    assert len(merged) == 2
    assert merged[0].high == 100.0 and merged[0].low == 78.0
    assert merged[1].high == 95.0


def test_zigzag_confirms_alternating_swings():
    df = make_vcp_frame()
    base = df.iloc[250:]
    swings = zigzag_from_high(base["high"], base["low"], threshold=0.03)
    kinds = [s.kind for s in swings]
    assert kinds[0] == "H"
    assert all(a != b for a, b in zip(kinds, kinds[1:])), "swings must alternate"
    assert swings[0].price == pytest.approx(100.0)


def test_watchlist_setup_detected():
    df = make_vcp_frame(depths=(0.20, 0.10, 0.05), last_rally_to=94.0)
    res = detect_vcp(df, P)
    assert res.valid, res.reason
    assert res.signal == Signal.WATCHLIST
    assert res.pivot == pytest.approx(95.0, abs=0.1)
    assert len(res.contractions) == 3
    depths = [c.depth for c in res.contractions]
    assert depths == sorted(depths, reverse=True), "depths must tighten"
    assert res.footprint.endswith("3T")
    # Phase-1 UX fields
    assert res.stop == pytest.approx(res.contractions[-1].low, abs=0.05)
    assert res.risk_pct is not None and res.risk_pct > 0
    assert res.quality_score is not None and 0 <= res.quality_score <= 100


def test_quality_score_rewards_tighter_dryer_setups():
    from sepa.vcp import compute_quality_score

    tight = compute_quality_score(
        [0.20, 0.10, 0.05], dryup_ratio=0.35, dist_to_pivot_pct=-1.0, p=P
    )
    loose = compute_quality_score(
        [0.20, 0.14, 0.10], dryup_ratio=0.70, dist_to_pivot_pct=-12.0, p=P
    )
    assert tight > loose
    assert tight >= 70
    extended = compute_quality_score(
        [0.20, 0.10, 0.05], dryup_ratio=0.35, dist_to_pivot_pct=8.0, p=P
    )
    assert extended < tight  # proximity component collapses when extended


def test_breakout_with_volume_confirmation():
    df = make_vcp_frame(depths=(0.20, 0.10, 0.05), last_rally_to=94.0)
    df = add_breakout_day(df, close=95.5, volume_mult=2.0)
    res = detect_vcp(df, P)
    assert res.valid, res.reason
    assert res.signal == Signal.BREAKOUT


def test_extended_beyond_max_chase_zone():
    df = make_vcp_frame(depths=(0.20, 0.10, 0.05), last_rally_to=94.0)
    df = add_breakout_day(df, close=95.0 * 1.08, volume_mult=2.0)
    res = detect_vcp(df, P)
    assert res.valid
    assert res.signal == Signal.EXTENDED


def test_rejects_non_tightening_contractions():
    df = make_vcp_frame(depths=(0.20, 0.18), last_rally_to=94.0)
    res = detect_vcp(df, P)
    assert not res.valid
    assert "수축이 점점 얕아지지 않음" in res.reason


def test_rejects_without_volume_dryup():
    df = make_vcp_frame(depths=(0.20, 0.10, 0.05), base_volume_dryup=False)
    res = detect_vcp(df, P)
    assert not res.valid
    assert "거래량 고갈 부족" in res.reason
    # Phase-1: still expose stop/quality when structure passed but dry-up failed
    assert res.stop is not None
    assert res.quality_score is not None


def test_rejects_too_deep_base():
    df = make_vcp_frame(depths=(0.40, 0.10), last_rally_to=90.0)
    res = detect_vcp(df, P)
    assert not res.valid
    assert "베이스 낙폭 과다" in res.reason
