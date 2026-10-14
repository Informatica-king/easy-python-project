"""Tests for lightweight gap-fill helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from sepa.gap_fill import (
    SOURCE_REBUILD,
    date_to_stamp,
    ensure_ecg_asof_layer,
    is_us_equity_holiday,
    local_fundamental_stamps,
    nyse_full_close_dates,
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


def test_nyse_holidays_2026_match_nasdaq_calendar():
    expected = {
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 2, 16),
        date(2026, 4, 3),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 3),
        date(2026, 9, 7),
        date(2026, 11, 26),
        date(2026, 12, 25),
    }
    assert nyse_full_close_dates(2026) == expected
    assert not is_us_equity_holiday(date(2026, 10, 12))
    assert not is_us_equity_holiday(date(2026, 11, 11))


def test_trading_days_skips_labor_day_keeps_columbus_day():
    labor_week = trading_days(date(2026, 9, 4), date(2026, 9, 8))
    assert [date_to_stamp(d) for d in labor_week] == ["20260904", "20260908"]
    oct_window = trading_days(date(2026, 10, 5), date(2026, 10, 14))
    assert [date_to_stamp(d) for d in oct_window] == [
        "20261005",
        "20261006",
        "20261007",
        "20261008",
        "20261009",
        "20261012",
        "20261013",
        "20261014",
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


def _synthetic_fund(n: int = 12) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [f"T{i:02d}" for i in range(n)],
            "name": [f"n{i}" for i in range(n)],
            "rs_rank": [80.0] * n,
            "fund_score": [60.0] * n,
            "s_surprise": [0.0] * n,
            "b_raw": [10.0] * n,
            "d_raw": [0.0] * n,
            "eps_accel_n": [1] * n,
            "sales_accel_n": [0] * n,
            "close": [100.0] * n,
            "market_cap": [2e9] * n,
        }
    )


def test_ensure_ecg_asof_writes_recommend(tmp_path: Path):
    report = tmp_path / "reports"
    cache = tmp_path / "cache"
    report.mkdir()
    cache.mkdir()
    stamp = "20261006"
    _synthetic_fund().to_csv(report / f"fundamental_{stamp}.csv", index=False)
    ok = ensure_ecg_asof_layer(
        report_dir=report,
        cache_dir=cache,
        stamp=stamp,
        as_of="2026-10-06",
        force=False,
        quiet=True,
    )
    assert ok
    rec = report / f"ecg_recommend_{stamp}.csv"
    txt = report / f"ecg_recommend_tickers_{stamp}.txt"
    table = report / f"ecg_{stamp}.csv"
    assert rec.exists() and txt.exists() and table.exists()
    line = txt.read_text(encoding="utf-8").strip()
    assert line
    assert len(pd.read_csv(rec)) >= 10

    # second call skips recompute when file exists
    mtime = rec.stat().st_mtime
    ok2 = ensure_ecg_asof_layer(
        report_dir=report,
        cache_dir=cache,
        stamp=stamp,
        as_of="2026-10-06",
        force=False,
        quiet=True,
    )
    assert ok2
    assert rec.stat().st_mtime == mtime


def test_ensure_ecg_asof_missing_fundamental(tmp_path: Path):
    report = tmp_path / "reports"
    cache = tmp_path / "cache"
    report.mkdir()
    cache.mkdir()
    assert not ensure_ecg_asof_layer(
        report_dir=report,
        cache_dir=cache,
        stamp="20261006",
        as_of="2026-10-06",
        quiet=True,
    )


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
