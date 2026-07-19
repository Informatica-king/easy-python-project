"""Tests for sector share time-series helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sepa.sector_share import (
    OTHER_LABEL,
    build_share_panel,
    compute_delta_vs_baseline,
    compute_deltas,
    membership_flow_by_sector,
    nearest_snapshot_on_or_before,
    pivot_share,
    previous_month_end,
    previous_week_friday,
    resolve_period_baselines,
    run_sector_share,
)


def _snap(tickers, tags, scores, mcaps, stamp_extra=None):
    return pd.DataFrame(
        {
            "ticker": tickers,
            "primary_tag": tags,
            "fund_score": scores,
            "market_cap": mcaps,
        }
    )


def test_previous_week_friday_and_month_end():
    # Wed 2026-07-18 → last week Friday = 2026-07-10? 
    # Mon of that week = 2026-07-13, last Friday = 2026-07-10
    # Wait: Jul 18 2026 is Saturday actually? Let's check...
    # User_info said Sunday Jul 19, 2026. So Jul 18 = Saturday.
    # Saturday Jul 18: weekday=5, this_monday = Jul 13, last_friday = Jul 10.
    assert previous_week_friday("2026-07-18").strftime("%Y-%m-%d") == "2026-07-10"
    # Friday itself still points to previous week
    assert previous_week_friday("2026-07-17").strftime("%Y-%m-%d") == "2026-07-10"
    assert previous_month_end("2026-07-18").strftime("%Y-%m-%d") == "2026-06-30"


def test_resolve_period_baselines_auto_and_force():
    # span 2 days — week/month auto off
    short = ["2026-07-16", "2026-07-17", "2026-07-18"]
    info = resolve_period_baselines(short)
    assert info["week"]["eligible_auto"] is False
    assert info["week"]["show"] is False
    assert info["month"]["show"] is False
    # force week still needs snapshot ≤ last Friday (2026-07-10) — none
    forced = resolve_period_baselines(short, force_week=True)
    assert forced["week"]["show"] is False

    # include Jul 10 Friday and span ≥ 7
    weekish = ["2026-07-10", "2026-07-13", "2026-07-16", "2026-07-18"]
    info2 = resolve_period_baselines(weekish)
    assert info2["span_days"] >= 7
    assert info2["week"]["eligible_auto"] is True
    assert info2["week"]["show"] is True
    assert info2["week"]["snapshot"] == "2026-07-10"

    # month: need span ≥ 28 and snap ≤ Jun 30
    monthish = ["2026-06-30", "2026-07-10", "2026-07-18", "2026-07-31"]
    info3 = resolve_period_baselines(monthish)
    assert info3["span_days"] >= 28
    assert info3["month"]["eligible_auto"] is True
    assert info3["month"]["snapshot"] == "2026-06-30"

    # force month with span < 28 but baseline exists
    early = ["2026-06-30", "2026-07-05"]
    info4 = resolve_period_baselines(early, force_month=True)
    assert info4["month"]["eligible_auto"] is False
    assert info4["month"]["show"] is True
    assert info4["month"]["snapshot"] == "2026-06-30"


def test_nearest_snapshot_on_or_before():
    dates = ["2026-07-10", "2026-07-14", "2026-07-18"]
    assert nearest_snapshot_on_or_before(dates, pd.Timestamp("2026-07-11")) == "2026-07-10"
    assert nearest_snapshot_on_or_before(dates, pd.Timestamp("2026-07-09")) is None


def test_compute_delta_vs_baseline():
    d1 = _snap(["A", "B"], ["기술", "헬스케어"], [50, 40], [1e9, 1e9])
    d2 = _snap(["A", "C"], ["기술", "금융"], [50, 45], [1e9, 1e9])
    panel, _ = build_share_panel([("20260710", d1), ("20260718", d2)])
    out = compute_delta_vs_baseline(
        panel, baseline_date="2026-07-10", as_of="2026-07-18", baseline_label="week"
    )
    health = out[out["primary_tag"] == "헬스케어"].iloc[0]
    assert health["delta_pp"] == pytest.approx(-50.0)


def test_share_panel_sums_to_one():
    d1 = _snap(["A", "B", "C"], ["기술", "헬스케어", "기술"], [50, 30, 45], [1e9, 2e9, 1e9])
    d2 = _snap(["A", "B", "D"], ["기술", "헬스케어", "금융"], [50, 30, 42], [1e9, 2e9, 3e9])
    panel, panel_hi = build_share_panel([("20260716", d1), ("20260717", d2)], fund_high=40)
    for day, g in panel.groupby("date"):
        assert g["share_n"].sum() == pytest.approx(1.0)
        assert g["share_mcap"].sum() == pytest.approx(1.0)
    # fund_high on day1: A,C (기술 only)
    hi1 = panel_hi[panel_hi["date"] == "2026-07-16"]
    assert set(hi1["primary_tag"]) == {"기술"}
    assert hi1["n"].sum() == 2


def test_pivot_top_n_collapses_other():
    rows = []
    for i, tag in enumerate(["A", "B", "C", "D", "E"]):
        rows.append({"date": "2026-07-16", "primary_tag": tag, "share_n": 0.3 if i == 0 else 0.175, "n": 1})
    panel = pd.DataFrame(rows)
    # fix shares to sum 1: A=0.4, others 0.15
    panel.loc[panel["primary_tag"] == "A", "share_n"] = 0.4
    panel.loc[panel["primary_tag"] != "A", "share_n"] = 0.15
    wide = pivot_share(panel, "share_n", top_n=2)
    assert OTHER_LABEL in wide.columns
    assert wide.loc["2026-07-16"].sum() == pytest.approx(1.0)


def test_deltas_and_flow():
    d1 = _snap(["A", "B"], ["기술", "헬스케어"], [50, 40], [1e9, 1e9])
    d2 = _snap(["A", "C"], ["기술", "금융"], [50, 45], [1e9, 1e9])
    panel, _ = build_share_panel([("20260716", d1), ("20260717", d2)])
    deltas = compute_deltas(panel)
    tech = deltas[deltas["primary_tag"] == "기술"].iloc[0]
    # day1 50% → day2 50%
    assert tech["delta_vs_first_pp"] == pytest.approx(0.0)
    health = deltas[deltas["primary_tag"] == "헬스케어"].iloc[0]
    assert health["delta_vs_first_pp"] == pytest.approx(-50.0)

    flows = membership_flow_by_sector([("20260716", d1), ("20260717", d2)])
    assert not flows.empty
    # C entered under 금융, B exited under 헬스케어
    assert int(flows.loc[flows["primary_tag"] == "금융", "entered"].sum()) == 1
    assert int(flows.loc[flows["primary_tag"] == "헬스케어", "exited"].sum()) == 1


def test_run_sector_share_week_chart_when_eligible(tmp_path: Path):
    report = tmp_path / "reports"
    report.mkdir()
    charts = report / "charts"
    # Fri Jul 10 → Sat Jul 18 (span 8d) with sector shift
    specs = [
        ("20260710", ["기술", "헬스케어", "기술"]),
        ("20260714", ["기술", "헬스케어", "금융"]),
        ("20260718", ["헬스케어", "헬스케어", "금융", "산업재"]),
    ]
    for stamp, tags in specs:
        n = len(tags)
        pd.DataFrame(
            {
                "ticker": [f"T{stamp}_{i}" for i in range(n)],
                "primary_tag": tags,
                "fund_score": [50] * n,
                "market_cap": [1e9] * n,
                "rs_rank": [90] * n,
                "name": [f"N{i}" for i in range(n)],
            }
        ).to_csv(report / f"analyze_{stamp}.csv", index=False)

    result = run_sector_share(report_dir=report, stamp="20260718", chart_dir=charts, top_n=5)
    assert result["ok"]
    assert result["week"]["show"] is True
    week_charts = [p for p in result["charts"] if "vs_week" in Path(p).name]
    assert week_charts
    line_all = [p for p in result["charts"] if "lines_n_all" in Path(p).name]
    line_hi = [p for p in result["charts"] if "lines_n_fundhi" in Path(p).name]
    assert line_all and line_hi
    assert result["month"]["show"] is False
