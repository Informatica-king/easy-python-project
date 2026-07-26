"""Smoke tests for VCP parameter study helpers."""

from __future__ import annotations

import pandas as pd

from sepa.config import VCPParams
from sepa.vcp_study import funnel_counts, presets, reason_category, summarize_events


def test_reason_category():
    assert reason_category("베이스 기간 부족 (6일, 최소 5주)", "NONE", False) == "베이스 기간 부족"
    assert reason_category("셋업 완료, 피벗 근접 (돌파 임박)", "WATCHLIST", True) == "OK:WATCHLIST"


def test_presets_include_live():
    live = VCPParams()
    p = presets(live)
    assert "live" in p and "base3" in p and "minervini_strict" in p
    assert p["live"].base_min_weeks == 5
    assert p["base3"].base_min_weeks == 3
    assert p["minervini_strict"].contraction_decay == 0.5


def test_funnel_and_edge_summary():
    rep = pd.DataFrame({
        "reason_cat": ["베이스 기간 부족", "베이스 기간 부족", "OK:WATCHLIST"],
        "signal": ["NONE", "NONE", "WATCHLIST"],
        "valid": [False, False, True],
    })
    f = funnel_counts(rep)
    assert f.iloc[0]["reason_cat"] == "베이스 기간 부족"
    assert f.iloc[0]["n"] == 2

    events = pd.DataFrame({
        "signal": ["WATCHLIST", "WATCHLIST", "BREAKOUT"],
        "fwd5": [0.01, 0.02, 0.03],
        "fwd10": [0.05, 0.07, 0.10],
        "fwd20": [0.08, 0.09, 0.12],
    })
    edge = summarize_events(events, baseline_med=0.03)
    assert set(edge["signal"]) == {"WATCHLIST", "BREAKOUT"}
    wl = edge[edge["signal"] == "WATCHLIST"].iloc[0]
    assert wl["n"] == 2
    assert wl["edge_vs_base_med_fwd10"] == 3.0  # 6% med - 3% base
