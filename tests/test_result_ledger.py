"""Tests for result_ledger accumulation helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sepa.result_ledger import (
    TT_CONDITION_KEYS,
    append_log_row,
    compute_membership_event_forward,
    diagnostics_summary_row,
    file_sha256,
    fund_quantile_row,
    load_membership_change_events,
    save_diagnostics_summary,
    save_fund_quantile_log,
    save_params_snapshot,
)


def test_file_sha256_and_params_snapshot(tmp_path: Path):
    cfg = tmp_path / "params.yaml"
    cfg.write_text(
        "data:\n  cache_dir: data/raw\n"
        "trend_template:\n  rs_rank_min: 70\n"
        "vcp: {}\n"
        "fundamental:\n  rs_min: 70\n  rs_soft_max: 90\n"
        "report:\n  output_dir: reports\n"
    )
    digest = file_sha256(cfg)
    assert len(digest) == 64

    reports = tmp_path / "reports"
    pack = save_params_snapshot(cfg, reports, "20260803", publish=False)
    assert pack["ok"]
    assert Path(pack["yaml"]).exists()
    assert Path(pack["log"]).exists()
    log = pd.read_csv(pack["log"])
    assert log.iloc[0]["sha256"] == digest
    assert float(log.iloc[0]["rs_rank_min"]) == 70.0


def test_append_log_row_dedupes(tmp_path: Path):
    path = tmp_path / "log.csv"
    append_log_row(path, {"stamp": "20260801", "n": 1})
    append_log_row(path, {"stamp": "20260801", "n": 2})
    append_log_row(path, {"stamp": "20260802", "n": 3})
    out = pd.read_csv(path)
    assert len(out) == 2
    assert int(out.loc[out["stamp"].astype(str) == "20260801", "n"].iloc[0]) == 2


def test_fund_quantile_row_and_log(tmp_path: Path):
    df = pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D"],
            "fund_score": [10.0, 20.0, 30.0, 40.0],
            "rs_rank": [70.0, 80.0, 90.0, 95.0],
        }
    )
    row = fund_quantile_row(df, stamp="20260803")
    assert row["n"] == 4
    assert row["fund_median"] == pytest.approx(25.0)
    assert row["n_rs90_plus"] == 2

    pack = save_fund_quantile_log(df, tmp_path, "20260803", publish=False)
    assert Path(pack["daily"]).exists()
    assert Path(pack["log"]).exists()


def test_diagnostics_summary_pass_rates(tmp_path: Path):
    diag = pd.DataFrame(
        {
            "ticker": ["A", "B", "C"],
            "stage2": [True, False, False],
            "failed_conditions": [
                "",
                "8_rs_rank",
                "4_ma_stack,8_rs_rank",
            ],
        }
    )
    row = diagnostics_summary_row(diag, stamp="20260803", n_universe=100, n_history=80)
    assert row["n_screened"] == 3
    assert row["n_stage2"] == 1
    assert row["stage2_rate"] == pytest.approx(1 / 3)
    assert row["pass_8_rs_rank"] == pytest.approx(1 / 3)  # 2 failed
    assert row["pass_4_ma_stack"] == pytest.approx(2 / 3)
    assert row["pass_1_above_mid_long_ma"] == pytest.approx(1.0)
    for k in TT_CONDITION_KEYS:
        assert f"pass_{k}" in row

    pack = save_diagnostics_summary(diag, tmp_path, "20260803", publish=False)
    assert Path(pack["daily"]).exists()


def test_load_membership_change_events(tmp_path: Path):
    sepatop = tmp_path / "sepatop"
    sepatop.mkdir()
    pd.DataFrame(
        [
            {"stamp": "20260801", "as_of": "2026-08-01", "prev_stamp": "", "action": "enter", "ticker": "AAA"},
            {"stamp": "20260801", "as_of": "2026-08-01", "prev_stamp": "", "action": "exit", "ticker": "BBB"},
        ]
    ).to_csv(sepatop / "membership_changes_20260801.csv", index=False)
    pd.DataFrame(
        [
            {"stamp": "20260802", "as_of": "2026-08-02", "prev_stamp": "20260801", "action": "enter", "ticker": "CCC"},
        ]
    ).to_csv(sepatop / "membership_changes_20260802.csv", index=False)
    ev = load_membership_change_events(sepatop)
    assert len(ev) == 3
    assert set(ev["ticker"]) == {"AAA", "BBB", "CCC"}


def test_compute_membership_event_forward_empty():
    out = compute_membership_event_forward(pd.DataFrame(), cache_dir="data/raw")
    assert out.empty
    assert "fwd_5d" in out.columns
