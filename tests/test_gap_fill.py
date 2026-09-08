"""Tests for lightweight gap-fill helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from sepa.gap_fill import (
    SOURCE_REBUILD,
    date_to_stamp,
    local_fundamental_stamps,
    parse_stamp,
    rebuild_panels,
    save_light_membership,
    trading_days,
    _write_source_meta,
)
from sepa.macro import _LOOKUP, parse_command


def test_trading_days_skips_weekend():
    days = trading_days(date(2026, 8, 7), date(2026, 8, 11))
    assert [date_to_stamp(d) for d in days] == [
        "20260807",
        "20260810",
        "20260811",
    ]


def test_parse_stamp_and_local_stamps(tmp_path: Path):
    assert parse_stamp("2026-08-10") == date(2026, 8, 10)
    report = tmp_path / "reports"
    report.mkdir()
    (report / "fundamental_20260804.csv").write_text("ticker\nA\n", encoding="utf-8")
    (report / "fundamental_notes.csv").write_text("x\n", encoding="utf-8")
    assert local_fundamental_stamps(report) == {"20260804"}


def test_save_light_membership_and_panels(tmp_path: Path):
    report = tmp_path / "reports"
    cache = tmp_path / "cache"
    report.mkdir()
    cache.mkdir()
    fund = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "name": ["a", "b"],
            "fund_score": [50.0, 40.0],
            "rs_rank": [80.0, 75.0],
            "market_cap": [2e9, 2e9],
        }
    )
    mem = save_light_membership(
        fund_df=fund,
        report_dir=report,
        cache_dir=cache,
        stamp="20260810",
        as_of="2026-08-10",
    )
    assert mem.exists()
    sepatop = report / "sepatop"
    assert (sepatop / "membership_20260810.csv").exists()
    assert (sepatop / "membership_changes_20260810.csv").exists()
    assert (sepatop / "membership_panel.csv").exists()
    assert (sepatop / "presence_20260810.csv").exists()

    # second day + rebuild_panels
    fund2 = fund.copy()
    fund2.loc[1, "ticker"] = "CCC"
    save_light_membership(
        fund_df=fund2,
        report_dir=report,
        cache_dir=cache,
        stamp="20260811",
        as_of="2026-08-11",
    )
    (report / "fundamental_20260810.csv").write_text(
        "ticker,fund_score,rs_rank,market_cap\nAAA,50,80,2000000000\nBBB,40,75,2000000000\n",
        encoding="utf-8",
    )
    (report / "fundamental_20260811.csv").write_text(
        "ticker,fund_score,rs_rank,market_cap\nAAA,50,80,2000000000\nCCC,40,75,2000000000\n",
        encoding="utf-8",
    )
    pack = rebuild_panels(report, cache)
    assert pack["membership_stamps"] == 2
    panel = pd.read_csv(sepatop / "membership_panel.csv")
    assert set(panel["stamp"].astype(str)) == {"20260810", "20260811"}


def test_source_meta(tmp_path: Path):
    report = tmp_path / "reports"
    report.mkdir()
    path = _write_source_meta(report, "20260810", SOURCE_REBUILD)
    text = path.read_text(encoding="utf-8")
    assert "asof_rebuild" in text


def test_macro_aliases_and_parse_fill_gaps():
    assert _LOOKUP["fill_gaps"] is _LOOKUP["sepa.fill_gaps"]
    assert _LOOKUP["gap_fill"] is _LOOKUP["sepa.fill_gaps"]
    name, args, kwargs = parse_command("!sepa.fill_gaps(dry_run=1, max_days=5)")
    assert name == "sepa.fill_gaps"
    assert kwargs["dry_run"] == 1
    assert kwargs["max_days"] == 5
    # reserved word `from` falls back to naive parser
    name2, _, kwargs2 = parse_command("!sepa.fill_gaps(from=20260804, to=20260811)")
    assert name2 == "sepa.fill_gaps"
    assert kwargs2.get("from") == "20260804"
    assert kwargs2.get("to") == "20260811"
    name3, _, kwargs3 = parse_command("!sepa.go(fill_gaps=1)")
    assert name3 == "sepa.go"
    assert kwargs3.get("fill_gaps") == 1
