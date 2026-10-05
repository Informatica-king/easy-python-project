import numpy as np

from sepa.indicators import compute_rs_ranks, rs_score
from synthetic import frame_from_close


def _frame(start: float, end: float, days: int = 300):
    return frame_from_close(np.linspace(start, end, days), np.full(days, 1e6))


def test_rs_score_positive_for_uptrend():
    assert rs_score(_frame(50, 100)["close"]) > 0
    assert rs_score(_frame(100, 50)["close"]) < 0


def test_rs_score_requires_min_history():
    assert rs_score(_frame(50, 100, days=100)["close"]) is None


def test_rs_ranks_order_strong_over_weak():
    data = {
        "STRONG": _frame(50, 150),
        "FLAT": _frame(100, 101),
        "WEAK": _frame(100, 60),
    }
    ranks = compute_rs_ranks(data)
    assert ranks["STRONG"] > ranks["FLAT"] > ranks["WEAK"]
    assert ranks["STRONG"] == 100.0
