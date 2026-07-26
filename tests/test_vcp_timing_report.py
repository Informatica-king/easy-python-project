"""Tests for VCP timing report table / pack output."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from sepa.vcp_timing import (
    REPORT_COLUMNS,
    build_vcp_table_html,
    build_vcp_table_pngs,
    signal_summary,
    write_vcp_report_pack,
)


def _sample_report() -> pd.DataFrame:
    rows = [
        {
            "ticker": "AAA",
            "signal": "BREAKOUT",
            "close": 100.5,
            "pivot": 99.0,
            "dist_to_pivot_pct": 1.5,
            "trend_ok": True,
            "base_weeks": 6.2,
            "footprint": "6W 20/10/5 3T",
            "final_depth_pct": 5.0,
            "dryup_ratio": 0.45,
            "volume_vs_avg": 1.8,
            "note": "피벗 돌파 + 거래량 확인",
        },
        {
            "ticker": "BBB",
            "signal": "NONE",
            "close": 50.0,
            "pivot": None,
            "dist_to_pivot_pct": None,
            "trend_ok": True,
            "base_weeks": None,
            "footprint": "",
            "final_depth_pct": None,
            "dryup_ratio": None,
            "volume_vs_avg": None,
            "note": "베이스 기간 부족 (6일, 최소 5주)",
        },
        {
            "ticker": "CCC",
            "signal": "WATCHLIST",
            "close": 80.0,
            "pivot": 81.0,
            "dist_to_pivot_pct": -1.2,
            "trend_ok": False,
            "base_weeks": 5.0,
            "footprint": "5W 18/9/4 3T",
            "final_depth_pct": 4.0,
            "dryup_ratio": 0.5,
            "volume_vs_avg": 0.9,
            "note": "셋업 완료, 피벗 근접 (돌파 임박)",
        },
    ]
    return pd.DataFrame(rows, columns=REPORT_COLUMNS)


def test_signal_summary_counts():
    s = signal_summary(_sample_report())
    assert s == {"BREAKOUT": 1, "WATCHLIST": 1, "NONE": 1}


def test_build_vcp_table_html(tmp_path: Path):
    report = _sample_report()
    out = build_vcp_table_html(report, tmp_path / "vcp_test.html", stamp="20260726")
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "VCP 타이밍 리포트" in text
    assert "AAA" in text
    assert "베이스 기간 부족" in text
    assert "BREAKOUT" in text
    assert "비고 / 탈락사유" in text


def test_build_vcp_table_pngs(tmp_path: Path):
    report = _sample_report()
    paths = build_vcp_table_pngs(report, tmp_path, stamp="20260726")
    assert len(paths) == 1
    assert paths[0].exists()
    assert paths[0].stat().st_size > 1000


def test_build_vcp_table_pngs_paginates(tmp_path: Path):
    rows = []
    for i in range(35):
        rows.append({
            "ticker": f"T{i:02d}",
            "signal": "NONE",
            "close": 10.0,
            "pivot": None,
            "dist_to_pivot_pct": None,
            "trend_ok": True,
            "base_weeks": None,
            "footprint": "",
            "final_depth_pct": None,
            "dryup_ratio": None,
            "volume_vs_avg": None,
            "note": f"탈락 사유 {i}",
        })
    report = pd.DataFrame(rows, columns=REPORT_COLUMNS)
    paths = build_vcp_table_pngs(report, tmp_path, stamp="20260726", rows_per_page=20)
    assert len(paths) == 2
    assert all(p.exists() for p in paths)


def test_write_vcp_report_pack(tmp_path: Path, monkeypatch):
    # Avoid depending on /opt/cursor/artifacts being writable in CI.
    monkeypatch.setenv("SEPA_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    report = _sample_report()
    pack = write_vcp_report_pack(report, tmp_path / "reports", stamp="20260726")
    assert Path(pack["csv"]).exists()
    assert Path(pack["html"]).exists()
    assert len(pack["pngs"]) == 1
    assert Path(pack["pngs"][0]).exists()
    csv_text = Path(pack["csv"]).read_text(encoding="utf-8")
    assert "베이스 기간 부족" in csv_text
    # published into artifact dir
    assert (tmp_path / "artifacts" / "vcp_20260726.csv").exists()
    assert (tmp_path / "artifacts" / "vcp_20260726.html").exists()
