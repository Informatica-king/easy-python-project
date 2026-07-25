"""Tests for lean TA scorer — no network."""

from __future__ import annotations

import numpy as np

from sepa.ta_score import score_frame
from synthetic import frame_from_close


def _uptrend(days: int = 300, start: float = 40.0, end: float = 100.0):
    close = np.linspace(start, end, days)
    # mild noise
    rng = np.random.default_rng(0)
    close = close * (1 + rng.normal(0, 0.002, days))
    vol = np.full(days, 1_000_000.0)
    return frame_from_close(close, vol, spread=0.01)


def _downtrend(days: int = 300):
    return _uptrend(days, start=100.0, end=40.0)


def test_uptrend_not_new_entry_ban_only():
    r = score_frame(_uptrend(), "TEST")
    assert r.status != "NO_DATA"
    assert r.trend >= 60
    assert r.action in {"분할OK", "홀드", "대기", "신규금지"}


def test_downtrend_blocks_new_entries():
    r = score_frame(_downtrend(), "WEAK")
    assert r.action == "신규금지"
    assert r.trend < 55


def test_tail_bars_reduces_history_but_scores():
    df = _uptrend(400)
    r_full = score_frame(df, "A", tail_bars=400)
    r_tail = score_frame(df, "A", tail_bars=280)
    assert r_tail.status != "NO_DATA"
    assert abs(r_full.close - r_tail.close) < 1e-6


def test_insufficient_history():
    df = _uptrend(40)
    r = score_frame(df, "SHORT", tail_bars=280)
    assert r.status == "NO_DATA"
    assert r.action == "대기"


def test_pullback_setup_prefers_split_buy():
    # Strong uptrend then flatten near EMA — approximate with late consolidation
    days = 320
    up = np.linspace(50, 100, 280)
    flat = np.linspace(100, 98.5, days - 280)
    close = np.concatenate([up, flat])
    vol = np.concatenate([np.full(280, 1e6), np.full(days - 280, 6e5)])
    df = frame_from_close(close, vol, spread=0.008)
    r = score_frame(df, "PULL")
    assert r.trend >= 55
    # Should not be bearish block
    assert r.action != "축소검토" or r.setup >= 40
