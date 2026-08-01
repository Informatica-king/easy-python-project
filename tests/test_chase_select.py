"""Tests for Chase buy-candidate selection."""

from __future__ import annotations

import json
from pathlib import Path

from sepa.chase_select import (
    ChaseRow,
    is_excluded,
    is_included,
    select_buy_candidates,
    write_chase_snapshot,
    load_chase_snapshot,
)


def test_exclude_overheated_and_sell():
    assert is_excluded("중하·07-29과열")
    assert is_excluded("매도·07-31추격금지")
    assert is_excluded("하·과열")
    assert is_excluded("관망·비적합")
    assert not is_excluded("상·분할보유")
    assert not is_excluded("중상·07-30반만")


def test_include_tiers_and_split():
    assert is_included(ChaseRow(1, "NEO", "최상"))
    assert is_included(ChaseRow(5, "ALKS", "상·07-28"))
    assert is_included(ChaseRow(12, "AMRX", "중상·07-30반만"))
    assert is_included(ChaseRow(7, "NESR", "상·분할보유"))
    assert is_included(ChaseRow(8, "TXG", "중·고점눌림"))  # rank<=10
    assert not is_included(ChaseRow(15, "ZZ", "중·눌림"))  # rank>10
    assert not is_included(ChaseRow(3, "FTNT", "하·과열"))


def test_select_orders_and_caps(tmp_path: Path):
    rows = [
        ChaseRow(1, "NEO", "최상", 14.0),
        ChaseRow(2, "ECPG", "최상·코어", 88.0),
        ChaseRow(3, "SLS", "상·위성", 13.0),
        ChaseRow(4, "DAVE", "최하·과열", 200.0),
        ChaseRow(5, "BAND", "중하·과열", 70.0),
        ChaseRow(6, "NESR", "상·분할보유", 27.2),
        ChaseRow(7, "AMRX", "중상·07-30반만", 17.5),
        ChaseRow(11, "MID", "중·대기", 10.0),  # rank>10 mid → drop
    ]
    picked = select_buy_candidates(rows, max_n=12)
    tickers = [r.ticker for r in picked]
    assert tickers == ["NEO", "ECPG", "SLS", "NESR", "AMRX"]
    assert "DAVE" not in tickers
    assert "BAND" not in tickers
    assert "MID" not in tickers


def test_snapshot_roundtrip(tmp_path: Path):
    path = tmp_path / "chase_rr_20260721.json"
    write_chase_snapshot(
        [
            {"rank": 1, "ticker": "neo", "chase": "최상", "px": 14.2, "earn_date": "2026-07-28"},
            {"rank": 2, "ticker": "NESR", "chase": "상·분할보유", "px": 27.2},
        ],
        path,
        as_of="2026-07-21",
    )
    as_of, rows = load_chase_snapshot(path)
    assert as_of == "2026-07-21"
    assert rows[0].ticker == "NEO"
    assert rows[0].earn_date == "2026-07-28"
    picked = select_buy_candidates(rows)
    assert [r.ticker for r in picked] == ["NEO", "NESR"]
