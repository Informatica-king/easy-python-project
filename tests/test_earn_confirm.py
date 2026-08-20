"""Tests for earn_confirmed SSOT + earn_confirm CLI (local I/O only)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from sepa.earn_calendar import (
    load_confirmed_earn_file,
    load_confirmed_earn_map,
    save_confirmed_earn_file,
)
from sepa.earn_confirm import main as earn_confirm_main
from sepa.portfolio_ops import HoldingRow, PortfolioBook, filter_buy_ideas


def test_confirmed_file_overrides_portfolio(tmp_path: Path):
    port = tmp_path / "port.yaml"
    conf = tmp_path / "earn_confirmed.yaml"
    port.write_text(
        yaml.safe_dump(
            {
                "as_of": "2026-08-12",
                "holdings": [
                    {"ticker": "SCSC", "earn_date": "2026-08-20", "role": "hold"},
                ],
            }
        ),
        encoding="utf-8",
    )
    save_confirmed_earn_file(
        conf,
        {
            "SCSC": {"earn_date": "2026-08-21", "note": "IR override", "confirmed_on": "2026-08-12"},
            "ANAB": {"earn_date": "2026-09-10", "note": "IR", "confirmed_on": "2026-08-12"},
        },
        as_of="2026-08-12",
    )
    m = load_confirmed_earn_map(portfolio_path=port, confirmed_path=conf)
    assert m["SCSC"] == date(2026, 8, 21)  # confirmed file wins
    assert m["ANAB"] == date(2026, 9, 10)  # non-holding from file


def test_earn_confirm_set_and_show(tmp_path: Path):
    conf = tmp_path / "earn_confirmed.yaml"
    rc = earn_confirm_main(["--confirmed", str(conf), "set", "ZD", "2026-10-01", "--note", "IR"])
    assert rc == 0
    entries = load_confirmed_earn_file(conf)
    assert entries["ZD"]["earn_date"] == "2026-10-01"
    rc2 = earn_confirm_main(["--confirmed", str(conf), "show"])
    assert rc2 == 0


def test_earn_confirm_diff_local(tmp_path: Path):
    conf = tmp_path / "earn_confirmed.yaml"
    port = tmp_path / "port.yaml"
    rank = tmp_path / "rank.json"
    port.write_text(yaml.safe_dump({"holdings": []}), encoding="utf-8")
    save_confirmed_earn_file(
        conf,
        {"SCSC": {"earn_date": "2026-08-20", "note": "x", "confirmed_on": "2026-08-12"}},
        as_of="2026-08-12",
    )
    rank.write_text(
        '{"rows":[{"t":"SCSC","earnDate":"2026-08-22"},{"t":"ANAB","earnDate":"2026-08-12"}]}',
        encoding="utf-8",
    )
    rc = earn_confirm_main(
        [
            "--confirmed",
            str(conf),
            "--portfolio",
            str(port),
            "diff",
            "--rank",
            str(rank),
            "--all",
        ]
    )
    assert rc == 0


def test_filter_blocks_confirmed_non_holding():
    """Candidate in earn_confirmed D5 → BLOCK even if not held."""
    book = PortfolioBook(
        as_of=date(2026, 8, 18),
        source="test",
        cash_usd=300.0,
        cash_floor_usd=150.0,
        cash_krw=0,
        note="",
        holdings=[],
    )
    # SCSC is in repo earn_confirmed.yaml with 2026-08-20
    chase = {"rows": [{"rank": 1, "ticker": "SCSC", "chase": "상", "px": 52.0}]}
    scenarios = {
        "rows": [
            {
                "t": "SCSC",
                "scenario": "A",
                "upside": 0.1,
                "px": 52.0,
                "rsi": 50,
                "pct_hi": -0.05,
                "earnDate": "2026-08-20",
                "earn_source": "estimate",
            }
        ]
    }
    ideas = filter_buy_ideas(book, scenarios, chase, policy_no_add=set())
    by = {i.ticker: i for i in ideas}
    assert by["SCSC"].bucket == "금지"
    assert by["SCSC"].timing == "BLOCK"
