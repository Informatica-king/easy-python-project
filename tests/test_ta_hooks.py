"""Tests for EARN_D5 / BAND / NO_ADD / STOP / TP portfolio hooks."""

from __future__ import annotations

from datetime import date

from sepa.ta_hooks import (
    TickerMeta,
    apply_hooks,
    in_earn_d5,
    load_hook_meta,
    parse_portfolio_watch,
    parse_watchlist,
)
from sepa.ta_score import TAResult


def _raw(**kwargs) -> TAResult:
    base = dict(
        ticker="TEST",
        close=26.0,
        as_of="2026-07-21",
        trend=80,
        momentum=60,
        volatility=70,
        setup=75,
        total=70,
        status="상승·눌림",
        action="분할OK",
        entry_lo=25.5,
        entry_hi=26.8,
        stop=24.0,
        atr_pct=4.0,
        rsi=52.0,
        note="추세 정렬",
    )
    base.update(kwargs)
    return TAResult(**base)


def test_earn_d5_window():
    earn = date(2026, 7, 28)
    assert in_earn_d5(date(2026, 7, 23), earn)
    assert in_earn_d5(date(2026, 7, 28), earn)
    assert not in_earn_d5(date(2026, 7, 22), earn)
    assert not in_earn_d5(date(2026, 7, 29), earn)


def test_earn_d5_blocks_split():
    meta = TickerMeta(symbol="NEO", earn_date=date(2026, 7, 28))
    out = apply_hooks(_raw(ticker="NEO", close=14.5), meta, as_of=date(2026, 7, 24))
    assert out.ta_action == "분할OK"
    assert out.action == "대기"
    assert out.override == "EARN_D5"
    assert "D-4" in out.reason


def test_earn_d5_outside_window_no_block():
    meta = TickerMeta(symbol="NEO", earn_date=date(2026, 7, 28))
    out = apply_hooks(_raw(ticker="NEO"), meta, as_of=date(2026, 7, 20))
    assert out.action == "분할OK"
    assert out.override == "—"


def test_band_blocks_above():
    meta = TickerMeta(symbol="NESR", band_lo=25.0, band_hi=27.0)
    out = apply_hooks(_raw(ticker="NESR", close=28.1), meta, as_of=date(2026, 7, 21))
    assert out.ta_action == "분할OK"
    assert out.action == "대기"
    assert "BAND" in out.override
    assert "상단초과" in out.reason


def test_band_clips_entry_inside():
    meta = TickerMeta(symbol="NESR", band_lo=25.0, band_hi=27.0)
    out = apply_hooks(
        _raw(ticker="NESR", close=26.2, entry_lo=24.5, entry_hi=27.5),
        meta,
        as_of=date(2026, 7, 21),
    )
    assert out.action == "분할OK"
    assert out.entry_lo == 25.0
    assert out.entry_hi == 27.0


def test_band_and_d5_both_tag():
    meta = TickerMeta(symbol="X", earn_date=date(2026, 7, 25), band_lo=10.0, band_hi=12.0)
    out = apply_hooks(_raw(ticker="X", close=13.0), meta, as_of=date(2026, 7, 21))
    assert out.action == "대기"
    assert "EARN_D5" in out.override
    assert "BAND" in out.override


def test_no_add_blocks_split():
    meta = TickerMeta(symbol="ECPG", no_add=True)
    out = apply_hooks(_raw(ticker="ECPG", close=88.0), meta, as_of=date(2026, 7, 22))
    assert out.action == "대기"
    assert "NO_ADD" in out.override


def test_stop_triggers_reduce():
    meta = TickerMeta(symbol="NEO", stop=12.0, tp1=16.0)
    out = apply_hooks(_raw(ticker="NEO", close=11.5, action="홀드"), meta, as_of=date(2026, 7, 22))
    assert out.action == "축소검토"
    assert "STOP" in out.override
    assert "손절가" in out.reason


def test_tp_triggers_take_profit():
    meta = TickerMeta(symbol="NEO", stop=12.0, tp1=16.0, tp2=18.0)
    out = apply_hooks(_raw(ticker="NEO", close=16.2, action="홀드"), meta, as_of=date(2026, 7, 22))
    assert out.action == "익절검토"
    assert out.override == "TP"
    assert "tp1" in out.reason


def test_tp2_note():
    meta = TickerMeta(symbol="NEO", tp1=16.0, tp2=18.0)
    out = apply_hooks(_raw(ticker="NEO", close=18.5, action="홀드"), meta, as_of=date(2026, 7, 22))
    assert out.action == "익절검토"
    assert "tp2" in out.reason


def test_stop_wins_over_tp():
    meta = TickerMeta(symbol="X", stop=20.0, tp1=10.0)
    out = apply_hooks(_raw(ticker="X", close=9.0, action="홀드"), meta, as_of=date(2026, 7, 22))
    assert out.action == "축소검토"
    assert "STOP" in out.override


def test_parse_watchlist_file():
    meta = parse_watchlist("config/ta_watchlist.yaml")
    assert "NESR" in meta
    assert meta["NESR"].band_lo == 25.0
    assert meta["NESR"].band_hi == 27.0
    assert meta["NEO"].earn_date == date(2026, 7, 28)
    assert meta["AMRX"].earn_date == date(2026, 7, 30)
    assert meta["NEO"].stop == 12.0
    assert meta["ECPG"].no_add is True


def test_parse_portfolio_and_merge():
    port = parse_portfolio_watch("config/portfolio_watch.yaml")
    assert port["NEO"].tp1 == 16.0
    assert port["NEO"].no_add is True
    assert port["MU"].stop == 830.0
    assert port["ASTH"].no_add is True  # exited
    assert port["AMAT"].tp1 == 623.0
    merged = load_hook_meta()
    assert merged["AMRX"].no_add is True
    assert merged["NESR"].band_lo == 25.0
    assert merged["INDV"].earn_date == date(2026, 8, 6)
    assert merged["CRDO"].no_add is True
