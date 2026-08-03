"""Unit tests for sepaTop index / membership helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sepa.sepatop import (
    BASE_LEVEL,
    append_membership_panel,
    build_cap_weighted_index,
    estimate_shares,
    load_membership_history,
    membership_changes_frame,
    membership_diff,
    presence_table,
    previous_membership,
    rebase_to,
    tenure_table,
    update_first_seen,
)


def test_membership_diff():
    entered, exited = membership_diff({"A", "B"}, {"B", "C"})
    assert entered == ["C"]
    assert exited == ["A"]


def test_update_first_seen_keeps_earliest():
    fs = update_first_seen({}, ["AAA", "BBB"], "2026-07-16")
    fs = update_first_seen(fs, ["AAA", "CCC"], "2026-07-18")
    assert fs["AAA"] == "2026-07-16"
    assert fs["BBB"] == "2026-07-16"
    assert fs["CCC"] == "2026-07-18"


def test_tenure_table_days():
    cons = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "name": ["A Inc", "B Inc"],
            "fund_score": [50.0, 40.0],
            "rs_rank": [90.0, 85.0],
        }
    )
    first = {"AAA": "2026-07-16", "BBB": "2026-07-18"}
    out = tenure_table(cons, first, "2026-07-18")
    assert int(out.loc[out["ticker"] == "AAA", "days_in_sepaTop"].iloc[0]) == 3
    assert int(out.loc[out["ticker"] == "BBB", "days_in_sepaTop"].iloc[0]) == 1


def test_cap_weighted_index_respects_weights():
    idx = pd.date_range("2026-01-01", periods=5, freq="B")
    # A doubles, B flat — equal shares → equal dollar weight at t0 if same price
    panel = pd.DataFrame(
        {
            "A": [10.0, 12.0, 14.0, 16.0, 20.0],
            "B": [10.0, 10.0, 10.0, 10.0, 10.0],
        },
        index=idx,
    )
    shares = {"A": 100.0, "B": 100.0}  # equal cap at t0
    series = build_cap_weighted_index(panel, shares, base_level=1000.0, min_coverage=1.0)
    assert abs(float(series.iloc[0]) - 1000.0) < 1e-6
    # End: A=20 B=10 → market value 3000 vs base 2000 → 1500
    assert abs(float(series.iloc[-1]) - 1500.0) < 1e-6


def test_estimate_shares_from_mcap():
    cons = pd.DataFrame({"ticker": ["X"], "market_cap": [1_000_000.0], "close": [10.0]})
    shares = estimate_shares(cons, {"X": 10.0})
    assert shares["X"] == pytest.approx(100_000.0)


def test_rebase_to():
    s = pd.Series(
        [200.0, 220.0, 240.0],
        index=pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-06"]),
    )
    out = rebase_to(s, BASE_LEVEL, pd.Timestamp("2026-01-02"))
    assert float(out.iloc[0]) == pytest.approx(BASE_LEVEL)
    assert float(out.iloc[-1]) == pytest.approx(BASE_LEVEL * 1.2)


def test_previous_membership(tmp_path: Path):
    report = tmp_path / "sepatop"
    report.mkdir()
    pd.DataFrame({"ticker": ["A", "B"]}).to_csv(report / "membership_20260716.csv", index=False)
    pd.DataFrame({"ticker": ["B", "C"]}).to_csv(report / "membership_20260717.csv", index=False)
    prev, stamp = previous_membership(report, "20260718")
    assert stamp == "20260717"
    assert prev == {"B", "C"}
    prev2, stamp2 = previous_membership(report, "20260716")
    assert stamp2 is None
    assert prev2 == set()


def test_presence_table_always_and_streak():
    history = [
        ("20260716", {"A", "B", "C"}),
        ("20260717", {"A", "B"}),
        ("20260718", {"A", "D"}),
    ]
    out = presence_table(history)
    a = out.loc[out["ticker"] == "A"].iloc[0]
    assert bool(a["always_present"]) is True
    assert int(a["streak_from_end"]) == 3
    assert float(a["presence_rate"]) == pytest.approx(1.0)

    b = out.loc[out["ticker"] == "B"].iloc[0]
    assert bool(b["always_present"]) is False
    assert int(b["streak_from_end"]) == 0
    assert int(b["n_present"]) == 2

    d = out.loc[out["ticker"] == "D"].iloc[0]
    assert int(d["streak_from_end"]) == 1


def test_membership_changes_frame():
    df = membership_changes_frame(
        stamp="20260718",
        as_of="2026-07-18",
        prev_stamp="20260717",
        entered=["X"],
        exited=["Y", "Z"],
    )
    assert list(df["action"]) == ["enter", "exit", "exit"]
    assert set(df.loc[df["action"] == "exit", "ticker"]) == {"Y", "Z"}


def test_append_membership_panel_dedupes_stamp(tmp_path: Path):
    path = tmp_path / "membership_panel.csv"
    cons = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "name": ["A"],
            "fund_score": [10.0],
            "rs_rank": [80.0],
            "market_cap": [2e9],
        }
    )
    append_membership_panel(path, cons, stamp="20260718", as_of="2026-07-18")
    cons2 = cons.copy()
    cons2["fund_score"] = [12.0]
    panel = append_membership_panel(path, cons2, stamp="20260718", as_of="2026-07-18")
    assert len(panel) == 1
    assert float(panel.iloc[0]["fund_score"]) == 12.0

    cons3 = pd.DataFrame(
        {
            "ticker": ["BBB"],
            "name": ["B"],
            "fund_score": [9.0],
            "rs_rank": [75.0],
            "market_cap": [3e9],
        }
    )
    panel2 = append_membership_panel(path, cons3, stamp="20260719", as_of="2026-07-19")
    assert len(panel2) == 2
    assert set(panel2["stamp"].astype(str)) == {"20260718", "20260719"}


def test_load_membership_history(tmp_path: Path):
    report = tmp_path / "sepatop"
    report.mkdir()
    pd.DataFrame({"ticker": ["A"]}).to_csv(report / "membership_20260716.csv", index=False)
    pd.DataFrame({"ticker": ["A", "B"]}).to_csv(report / "membership_20260717.csv", index=False)
    hist = load_membership_history(report)
    assert [s for s, _ in hist] == ["20260716", "20260717"]
    assert hist[1][1] == {"A", "B"}
