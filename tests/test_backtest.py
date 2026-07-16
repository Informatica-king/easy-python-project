import numpy as np
import pandas as pd
import pytest

from sepa.backtest import ExitParams, PortfolioParams, buys_per_company, simulate, top_companies

PP = PortfolioParams(initial_capital=10_000.0, max_positions=2, slippage=0.0, max_gap_extension=0.05)


def make_df(bars: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    idx = pd.bdate_range("2025-01-06", periods=len(bars), name="date")
    o, h, l, c = zip(*bars)
    return pd.DataFrame(
        {"open": o, "high": h, "low": l, "close": c, "volume": np.full(len(bars), 1e6)}, index=idx
    )


def signal_on(df: pd.DataFrame, day_idx: int, ticker: str, pivot: float, fill_mode: str = "next_open") -> pd.DataFrame:
    return pd.DataFrame([{
        "date": df.index[day_idx], "ticker": ticker, "pivot": pivot,
        "trigger": pivot * 1.001, "rs_rank": 95.0, "fill_mode": fill_mode,
    }])


def test_entry_next_open_and_stop_loss():
    # 시그널 다음날 시가 100 진입, 이후 저가가 스탑(92)에 닿으면 스탑가 체결
    bars = [(100, 101, 99, 100)] * 3 + [(100, 102, 100, 101)] + [(100, 100, 90, 91)] + [(91, 92, 90, 91)] * 3
    df = make_df(bars)
    signals = signal_on(df, 2, "TST", pivot=100.0)
    res = simulate(signals, {"TST": df}, ExitParams(stop_loss=0.08, trail_ma=100, profit_target=None, free_roll=False), PP)
    assert len(res.trades) == 1
    t = res.trades.iloc[0]
    assert t["entry_price"] == pytest.approx(100.0)  # T+1 시가
    assert t["exit_price"] == pytest.approx(92.0)    # 스탑 가격 체결
    assert t["reason"] == "stop_loss"
    assert t["ret"] == pytest.approx(-0.08, abs=1e-6)


def test_profit_target_sell_into_strength():
    bars = [(100, 101, 99, 100)] * 3 + [(100, 101, 100, 101)] + [(105, 120, 104, 118)] + [(118, 119, 117, 118)] * 3
    df = make_df(bars)
    signals = signal_on(df, 2, "TST", pivot=100.0)
    res = simulate(signals, {"TST": df}, ExitParams(stop_loss=0.08, trail_ma=100, profit_target=0.15, free_roll=False), PP)
    t = res.trades.iloc[0]
    assert t["reason"] == "profit_target"
    assert t["exit_price"] == pytest.approx(100.0 * 1.15)


def test_gap_up_beyond_extension_skips_entry():
    # T+1 시가가 피벗 +5% 초과(106) -> 추격 금지
    bars = [(100, 101, 99, 100)] * 3 + [(106, 108, 105, 107)] + [(107, 108, 106, 107)] * 3
    df = make_df(bars)
    signals = signal_on(df, 2, "TST", pivot=100.0)
    res = simulate(signals, {"TST": df}, ExitParams(stop_loss=0.08, trail_ma=100), PP)
    assert res.trades.empty or (res.trades["reason"] == "end_of_backtest").all() is False


def test_free_roll_moves_stop_to_breakeven():
    # +8% 도달(종가 108) 후 하락 -> 본전(100)에서 청산되어 손실 없음
    bars = [(100, 101, 99, 100)] * 3 + [(100, 101, 100, 100.5)] + [(105, 109, 104, 108)] + [(104, 105, 99, 100)] + [(100, 101, 99, 100)]
    df = make_df(bars)
    signals = signal_on(df, 2, "TST", pivot=100.0)
    res = simulate(signals, {"TST": df}, ExitParams(stop_loss=0.08, trail_ma=100, free_roll=True), PP)
    t = res.trades.iloc[0]
    assert t["reason"] == "breakeven_stop"
    assert t["exit_price"] == pytest.approx(100.0)
    assert t["pnl"] == pytest.approx(0.0, abs=1e-6)


def test_trail_ma_exit_next_open():
    # 종가가 3일 이평선 아래로 -> 다음날 시가 청산
    bars = [(100, 101, 99, 100)] * 3 + [(100, 101, 100, 101)] + [(102, 103, 101, 102)] * 3 + [(95, 96, 94, 94.5)] + [(94, 95, 93, 94)]
    df = make_df(bars)
    signals = signal_on(df, 2, "TST", pivot=100.0)
    res = simulate(signals, {"TST": df}, ExitParams(stop_loss=0.20, trail_ma=3, free_roll=False), PP)
    t = res.trades.iloc[0]
    assert t["reason"] == "trail_ma"
    assert t["exit_price"] == pytest.approx(94.0)  # 다음날 시가


def test_stop_fill_same_day_at_trigger():
    # buy-stop 체결: 시그널 당일 트리거 가격(100.1)으로 진입
    bars = [(100, 101, 99, 100)] * 3 + [(99, 103, 98, 102)] + [(102, 104, 101, 103)] * 3
    df = make_df(bars)
    signals = signal_on(df, 3, "TST", pivot=100.0, fill_mode="stop")
    res = simulate(signals, {"TST": df}, ExitParams(stop_loss=0.08, trail_ma=100, free_roll=False), PP)
    t = res.trades.iloc[0]
    assert t["entry_date"] == df.index[3]
    assert t["entry_price"] == pytest.approx(100.1)


def test_report_helpers():
    trades = pd.DataFrame([
        {"ticker": "AAA", "pnl": 500.0, "ret": 0.10},
        {"ticker": "AAA", "pnl": -100.0, "ret": -0.05},
        {"ticker": "BBB", "pnl": 300.0, "ret": 0.08},
    ])
    top = top_companies(trades, n=2)
    assert list(top["ticker"]) == ["AAA", "BBB"]
    avg, dist = buys_per_company(trades)
    assert avg == pytest.approx(1.5)
    assert dist.set_index("매수횟수").loc[1, "기업수"] == 1
    assert dist.set_index("매수횟수").loc[2, "기업수"] == 1
