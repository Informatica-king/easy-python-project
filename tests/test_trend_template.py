import numpy as np

from sepa.config import TrendTemplateParams
from sepa.indicators import add_indicators
from sepa.trend_template import evaluate
from synthetic import frame_from_close

TP = TrendTemplateParams()


def _steady_trend(start: float, end: float, days: int = 320):
    close = np.linspace(start, end, days)
    volume = np.full(days, 1_000_000.0)
    return frame_from_close(close, volume, spread=0.01)


def test_uptrend_passes_all_conditions():
    df = add_indicators(_steady_trend(40.0, 100.0), TP)
    res = evaluate(df, TP, rs_rank=90.0)
    assert res.passed, res.conditions
    assert all(res.conditions.values())


def test_downtrend_fails():
    df = add_indicators(_steady_trend(100.0, 40.0), TP)
    res = evaluate(df, TP, rs_rank=90.0)
    assert not res.passed
    assert not res.conditions["4_ma_stack"]
    assert not res.conditions["3_long_ma_rising"]


def test_low_rs_rank_fails_condition_8():
    df = add_indicators(_steady_trend(40.0, 100.0), TP)
    res = evaluate(df, TP, rs_rank=50.0)
    assert not res.passed
    assert not res.conditions["8_rs_rank"]
    assert res.conditions["1_above_mid_long_ma"]


def test_short_history_fails_safely():
    df = add_indicators(_steady_trend(40.0, 100.0, days=100), TP)
    res = evaluate(df, TP, rs_rank=90.0)
    assert not res.passed
