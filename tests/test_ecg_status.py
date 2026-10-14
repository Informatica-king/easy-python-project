"""Tests for ECG/CSS B2 status one-liners."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from sepa.ecg_status import (
    format_ecg_b2_summary_line,
    load_css_ecg_vs_sepatop,
    load_ecg_ledger_counts,
    load_ecg_recommend_line,
)


def test_load_ecg_recommend_line(tmp_path: Path):
    p = tmp_path / "ecg_recommend_tickers_20261005.txt"
    p.write_text("AAA,BBB,CCC\n", encoding="utf-8")
    n, line, path = load_ecg_recommend_line(tmp_path, stamp="20261005")
    assert n == 3
    assert line == "AAA,BBB,CCC"
    assert path == p


def test_format_line_with_css_rollup(tmp_path: Path):
    (tmp_path / "ecg_recommend_tickers_20261005.txt").write_text("A,B\n", encoding="utf-8")
    bt = tmp_path / "asof_forward_bt"
    bt.mkdir()
    pd.DataFrame(
        [
            {"rule": "sepaTop", "n_asof": 11, "CSS": 48.3, "sample_note": "ok"},
            {"rule": "ecg_top", "n_asof": 11, "CSS": 50.8, "sample_note": "ok"},
        ]
    ).to_csv(bt / "css_rollup.csv", index=False)
    pd.DataFrame(
        [
            {
                "rule": "ecg_top",
                "delta_css_vs_sepaTop": 2.5,
                "d_S2_median_excess": 12.2,
                "d_S4_tail_penalty": 5.1,
            }
        ]
    ).to_csv(bt / "css_delta.csv", index=False)
    line = format_ecg_b2_summary_line(tmp_path, stamp="20261005")
    assert "오늘 추천 2종" in line
    assert "Δ+2.5" in line or "Δ+2.5" in line.replace("+", "+")
    assert "자료 부족" in line
    assert load_css_ecg_vs_sepatop(tmp_path)["ok"] is True


def test_format_line_without_artifacts(tmp_path: Path):
    line = format_ecg_b2_summary_line(tmp_path)
    assert "본선" in line
    assert "CSS 롤업 없음" in line
    assert "ledger ECG 바스켓 대기" in line


def test_load_ecg_ledger_counts(tmp_path: Path):
    perf = tmp_path / "perf"
    perf.mkdir()
    pd.DataFrame(
        [
            {"stamp": "20261005", "n_ecg_recommend": 17},
            {"stamp": "20261008", "n_ecg_recommend": 0},
        ]
    ).to_csv(perf / "daily_pool_log.csv", index=False)
    counts = load_ecg_ledger_counts(tmp_path)
    assert counts["ok"] is True
    assert counts["n_stamps"] == 1
    assert counts["n_rows"] == 2
    line = format_ecg_b2_summary_line(tmp_path, stamp="20261005")
    assert "ledger 추천 스냅샷 1일" in line
