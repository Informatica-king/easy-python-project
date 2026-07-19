"""Tests for sector share time-series helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sepa.sector_share import (
    OTHER_LABEL,
    build_share_panel,
    compute_deltas,
    membership_flow_by_sector,
    pivot_share,
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


def test_run_sector_share_writes_artifacts(tmp_path: Path):
    report = tmp_path / "reports"
    report.mkdir()
    charts = report / "charts"
    for stamp, tags in [("20260716", ["기술", "헬스케어"]), ("20260717", ["기술", "금융", "기술"])]:
        n = len(tags)
        df = pd.DataFrame(
            {
                "ticker": [f"T{i}" for i in range(n)],
                "primary_tag": tags,
                "fund_score": [50] * n,
                "market_cap": [1e9] * n,
                "rs_rank": [90] * n,
                "name": [f"N{i}" for i in range(n)],
            }
        )
        df.to_csv(report / f"analyze_{stamp}.csv", index=False)

    result = run_sector_share(
        report_dir=report,
        stamp="20260717",
        chart_dir=charts,
        top_n=5,
        fund_high=40,
    )
    assert result["ok"]
    assert result["n_snapshots"] == 2
    assert Path(result["panel"]).exists()
    assert Path(result["history"]).exists()
    for p in result["charts"]:
        assert Path(p).exists()
        assert Path(p).stat().st_size > 0
