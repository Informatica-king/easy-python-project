"""Tests for D29 Phase 1 perf_study modules A–D."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sepa.perf_ledger import BASKET_RS90_OK, BASKET_SOFT_DROP
from sepa.perf_study import (
    GATE_INSUFFICIENT,
    GATE_INTERPRET,
    GATE_MONITOR,
    aggregate_basket_excess,
    run_perf_study,
    sample_gate,
    streak_excess_frame,
    study_event_forward,
    study_soft_vs_rs90,
    study_streak_buckets,
)


def _fwd_frame() -> pd.DataFrame:
    rows = []
    # soft_drop weaker than rs90_ok on 5d
    for i, t in enumerate(["S1", "S2", "S3"]):
        rows.append(
            {
                "stamp": "20260801",
                "basket": BASKET_SOFT_DROP,
                "ticker": t,
                "ready_5d": True,
                "excess_5d": -0.02 - 0.01 * i,
                "ready_10d": False,
                "excess_10d": np.nan,
                "ready_21d": False,
                "excess_21d": np.nan,
            }
        )
    for i, t in enumerate(["R1", "R2", "R3", "R4"]):
        rows.append(
            {
                "stamp": "20260801",
                "basket": BASKET_RS90_OK,
                "ticker": t,
                "ready_5d": True,
                "excess_5d": 0.03 + 0.01 * i,
                "ready_10d": False,
                "excess_10d": np.nan,
                "ready_21d": False,
                "excess_21d": np.nan,
            }
        )
    # median_plus for streak join
    for t, exc, streak_stamp in [("A", 0.05, "20260804"), ("B", -0.01, "20260805")]:
        rows.append(
            {
                "stamp": streak_stamp,
                "basket": "median_plus",
                "ticker": t,
                "ready_5d": True,
                "excess_5d": exc,
                "ready_10d": True,
                "excess_10d": exc,
                "ready_21d": True,
                "excess_21d": exc,
            }
        )
    return pd.DataFrame(rows)


def test_sample_gate_thresholds():
    assert sample_gate(n_ready=10, n_stamps=2, kind="basket") == GATE_INSUFFICIENT
    assert sample_gate(n_ready=40, n_stamps=6, kind="basket") == GATE_MONITOR
    assert sample_gate(n_ready=250, n_stamps=45, kind="basket") == GATE_INTERPRET
    assert sample_gate(n_ready=10, kind="event") == GATE_INSUFFICIENT
    assert sample_gate(n_ready=25, kind="event") == GATE_MONITOR
    assert sample_gate(n_ready=20, n_stamps=6, kind="soft_vs") == GATE_MONITOR


def test_aggregate_and_soft_vs():
    fwd = _fwd_frame()
    agg = aggregate_basket_excess(fwd)
    assert not agg.empty
    assert "sample_gate" in agg.columns
    assert "std_excess" in agg.columns
    soft = study_soft_vs_rs90(fwd)
    assert not soft.empty
    row5 = soft.loc[soft["horizon"] == "5d"].iloc[0]
    assert row5["n_soft_drop"] == 3
    assert row5["n_rs90_ok"] == 4
    assert row5["mean_soft_drop"] < row5["mean_rs90_ok"]
    assert row5["delta_soft_minus_rs90"] < 0


def test_event_forward_agg():
    events = pd.DataFrame(
        [
            {"action": "enter", "stamp": "20260801", "ready_5d": True, "excess_5d": 0.02},
            {"action": "enter", "stamp": "20260802", "ready_5d": True, "excess_5d": 0.04},
            {"action": "exit", "stamp": "20260801", "ready_5d": True, "excess_5d": -0.01},
            {"action": "exit", "stamp": "20260802", "ready_5d": False, "excess_5d": 0.5},
        ]
    )
    agg = study_event_forward(events)
    enter = agg.loc[(agg["action"] == "enter") & (agg["horizon"] == "5d")].iloc[0]
    assert enter["n_ready"] == 2
    assert abs(enter["mean_excess"] - 0.03) < 1e-9
    exit_row = agg.loc[(agg["action"] == "exit") & (agg["horizon"] == "5d")].iloc[0]
    assert exit_row["n_ready"] == 1


def test_streak_buckets():
    presence = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "streak_from_end": [1, 6],
            "n_present": [1, 6],
            "presence_rate": [0.2, 1.0],
            "always_present": [False, True],
        }
    )
    fwd = _fwd_frame()
    streak = streak_excess_frame(presence, fwd, basket="median_plus", horizon="21d")
    assert not streak.empty
    assert "streak_bucket" in streak.columns
    buckets = study_streak_buckets(streak, horizon="21d")
    assert set(buckets["bucket"]) >= {"1", "5+", "always_present"}


def test_run_perf_study_empty_safe(tmp_path: Path):
    report = tmp_path / "reports"
    report.mkdir()
    (report / "perf").mkdir()
    pack = run_perf_study(
        report_dir=report,
        cache_dir=tmp_path / "cache",
        stamp="20260814",
        skip_github_release=True,
    )
    assert pack["ok"]
    assert pack["pdf"] is not None
    assert Path(pack["pdf"]).exists()
    assert Path(pack["pdf"]).stat().st_size > 1000
    assert not (report / "perf" / "study_20260814.md").exists()


def test_run_perf_study_with_fwd(tmp_path: Path):
    report = tmp_path / "reports"
    perf = report / "perf"
    perf.mkdir(parents=True)
    cache = tmp_path / "cache"
    cache.mkdir()
    fwd = _fwd_frame()
    fwd.to_csv(perf / "security_forward_panel.csv", index=False)
    pd.DataFrame(
        [
            {
                "stamp": "20260801",
                "n_fund_pool": 10,
                "n_median_plus": 5,
                "n_fund_q4": 2,
                "fund_median": 47.0,
            }
        ]
    ).to_csv(perf / "daily_pool_log.csv", index=False)
    pack = run_perf_study(
        report_dir=report,
        cache_dir=cache,
        stamp="20260814",
        skip_github_release=True,
    )
    assert pack["ok"]
    assert not pack["soft_cmp"].empty
    assert Path(pack["pdf"]).exists()
    assert pack["pdf"].name == "검증보고서_20260814.pdf"
    assert not (perf / "study_20260814.md").exists()
    assert "자료 부족" in pack["summary"] or "관측" in pack["summary"]


def test_verify_helpers():
    from sepa.verify_report import (
        GATE_INSUFFICIENT,
        interpret_soft_delta,
        verify_pdf_name,
        verify_release_tag,
    )

    assert verify_release_tag("20260814") == "sepa-검증-20260814"
    assert verify_pdf_name("20260814") == "검증보고서_20260814.pdf"
    assert "판단 보류" in interpret_soft_delta(-0.01, GATE_INSUFFICIENT)
    assert "도움이 되는" in interpret_soft_delta(-0.01, "interpret")
    assert "잘못 잘랐" in interpret_soft_delta(0.02, "monitor")
