"""SEPA 백테스트 엔진 (Phase 5).

2단계 구조:
  1. `precompute_entry_signals` — 전 기간·전 종목에 대해 Stage 2(Trend
     Template) + VCP BREAKOUT 진입 시그널을 한 번만 계산 (느린 부분, 캐시됨).
  2. `simulate` — 사전 계산된 시그널 위에서 청산·자금관리 파라미터로
     가상투자를 실행 (빠름 → 그리드 탐색 가능).

체결 원칙 (look-ahead 방지):
  - 시그널은 T일 종가 기준으로 판정, 진입은 T+1일 시가 (+슬리피지)
  - T+1 시가가 피벗 대비 max_extension 초과 갭업이면 추격 금지(진입 취소)
  - 손절: 장중 저가가 스탑 가격 도달 시 스탑 가격 체결 (갭다운이면 시가)
  - 목표 익절: 장중 고가가 목표가 도달 시 목표가 체결 (강세에 매도)
  - 추세 이탈: T일 종가가 추적 이평선 하회 시 T+1일 시가 청산
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd

from sepa import indicators, vcp
from sepa.config import Params
from sepa.data import store

logger = logging.getLogger(__name__)

SIGNALS_CACHE = "reports/backtest/entry_signals.parquet"


# ──────────────────────────────────────────────────────────────────
# 1단계: 진입 시그널 사전 계산
# ──────────────────────────────────────────────────────────────────

def _panel(data: dict[str, pd.DataFrame], col: str) -> pd.DataFrame:
    return pd.DataFrame({t: df[col] for t, df in data.items()})


def _rs_rank_panel(close: pd.DataFrame) -> pd.DataFrame:
    """일자별 크로스섹션 RS 백분위 순위 (0~100), look-ahead 없음."""
    score = sum(
        w * (close / close.shift(n) - 1.0) for n, w in indicators.RS_WINDOWS
    )
    return score.rank(axis=1, pct=True) * 100.0


def stage2_panel(data: dict[str, pd.DataFrame], params: Params) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(일자 × 종목) Stage 2 통과 bool 패널과 RS 순위 패널을 리턴."""
    tp = params.trend_template
    close, high, low = _panel(data, "close"), _panel(data, "high"), _panel(data, "low")
    volume = _panel(data, "volume")

    sma_s = close.rolling(tp.sma_short).mean()
    sma_m = close.rolling(tp.sma_mid).mean()
    sma_l = close.rolling(tp.sma_long).mean()
    high52 = high.rolling(indicators.WEEK_52_DAYS).max()
    low52 = low.rolling(indicators.WEEK_52_DAYS).min()
    rs = _rs_rank_panel(close)

    ok = (
        (close > sma_m) & (close > sma_l)
        & (sma_m > sma_l)
        & (sma_l > sma_l.shift(tp.trend_days))
        & (sma_s > sma_m)
        & (close > sma_s)
        & (close >= low52 * (1 + tp.low_52w_min_pct))
        & (close >= high52 * (1 - tp.high_52w_max_pct))
    )
    if tp.rs_enabled:
        ok &= rs >= tp.rs_rank_min

    # 유동성 필터 (as-of, look-ahead 없음)
    uf = params.universe_filter
    dollar_vol = (close * volume).rolling(50).mean()
    ok &= (close >= uf.min_price) & (dollar_vol >= uf.min_avg_dollar_volume)
    return ok.fillna(False), rs


# 셋업(WATCHLIST/FORMING) 확인 후 피벗 buy-stop 주문의 유효 기간 (거래일)
SIGNAL_TTL_DAYS = 10


def precompute_entry_signals(
    data: dict[str, pd.DataFrame],
    params: Params,
    cache_path: str | Path = SIGNALS_CACHE,
    use_cache: bool = True,
) -> pd.DataFrame:
    """진입 시그널 테이블: [date, ticker, pivot, rs_rank, fill_mode].

    미너비니의 실전 방식을 따른다: 유효한 VCP 셋업(WATCHLIST/FORMING)이
    확인되면 피벗에 buy-stop 주문을 건다(유효기간 SIGNAL_TTL_DAYS). 이후
    장중 고가가 피벗을 넘고 당일 거래량이 조건을 충족하면 그날 체결
    (fill_mode='stop'). 셋업 확인과 돌파가 같은 날인 경우(종가 돌파 확인)는
    다음날 시가 진입(fill_mode='next_open').
    """
    cache = Path(cache_path)
    if use_cache and cache.exists():
        logger.info("using cached entry signals: %s", cache)
        return pd.read_parquet(cache)

    ok_panel, rs_panel = stage2_panel(data, params)
    p = params.vcp
    rows = []

    for ticker, df in data.items():
        if ticker not in ok_panel.columns:
            continue
        enriched = indicators.add_indicators(df, params.trend_template)
        ok = ok_panel[ticker].reindex(df.index, fill_value=False).to_numpy()
        high = df["high"].to_numpy()
        volume = df["volume"].to_numpy()
        vol50 = enriched["vol_sma50"].to_numpy()

        armed_pivot: float | None = None
        armed_expiry = -1

        for pos in range(len(df)):
            day = df.index[pos]
            # 1) 걸려 있는 buy-stop 주문의 돌파 체결 판정
            if armed_pivot is not None:
                if pos > armed_expiry:
                    armed_pivot = None
                else:
                    trigger = armed_pivot * (1 + p.pivot_buffer)
                    vol_ok = vol50[pos] > 0 and volume[pos] >= p.breakout_vol_mult * vol50[pos]
                    if high[pos] >= trigger and vol_ok:
                        rows.append({
                            "date": day, "ticker": ticker, "pivot": armed_pivot,
                            "trigger": trigger,
                            "rs_rank": _rs_at(rs_panel, day, ticker), "fill_mode": "stop",
                        })
                        armed_pivot = None

            # 2) Stage 2인 날에만 셋업 탐지/갱신
            if not ok[pos]:
                continue
            res = vcp.detect_vcp(enriched.iloc[: pos + 1], p)
            if not res.valid:
                continue
            if res.signal in (vcp.Signal.WATCHLIST, vcp.Signal.FORMING):
                if res.pivot is not None and float(df["close"].iloc[pos]) < res.pivot:
                    armed_pivot = float(res.pivot)   # 최신 구조의 피벗으로 갱신
                    armed_expiry = pos + SIGNAL_TTL_DAYS
            elif res.signal == vcp.Signal.BREAKOUT and armed_pivot is None:
                # 사전 예약 없이 당일 종가로 돌파 확인 -> 다음날 시가 진입
                rows.append({
                    "date": day, "ticker": ticker, "pivot": float(res.pivot),
                    "trigger": float(res.pivot) * (1 + p.pivot_buffer),
                    "rs_rank": _rs_at(rs_panel, day, ticker), "fill_mode": "next_open",
                })

    signals = pd.DataFrame(rows, columns=["date", "ticker", "pivot", "trigger", "rs_rank", "fill_mode"])
    signals = signals.drop_duplicates(subset=["date", "ticker"])
    signals = signals.sort_values(["date", "rs_rank"], ascending=[True, False]).reset_index(drop=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    signals.to_parquet(cache)
    logger.info("entry signals computed: %d rows -> %s", len(signals), cache)
    return signals


def _rs_at(rs_panel: pd.DataFrame, day: pd.Timestamp, ticker: str) -> float:
    try:
        v = float(rs_panel.at[day, ticker])
        return round(v, 1) if not np.isnan(v) else 0.0
    except KeyError:
        return 0.0


# ──────────────────────────────────────────────────────────────────
# 2단계: 가상투자 시뮬레이션
# ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExitParams:
    stop_loss: float = 0.08          # 매수가 대비 손절 폭
    trail_ma: int = 50               # 종가 이탈 시 청산할 이평선 (20 또는 50)
    profit_target: float | None = None  # 강세 매도 목표 (None=계속 보유)
    free_roll: bool = True           # +손절폭만큼 수익 시 스탑을 본전으로 이동


@dataclass(frozen=True)
class PortfolioParams:
    initial_capital: float = 100_000.0
    max_positions: int = 10
    slippage: float = 0.001          # 진입/청산 각 0.1%
    max_gap_extension: float = 0.05  # T+1 시가가 피벗 +5% 초과 갭업이면 진입 취소


@dataclass
class Position:
    ticker: str
    entry_date: pd.Timestamp
    entry_price: float
    shares: float
    stop_price: float
    pivot: float


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity: pd.Series
    exit_params: ExitParams
    metrics: dict = field(default_factory=dict)

    def compute_metrics(self) -> dict:
        eq = self.equity
        total_return = eq.iloc[-1] / eq.iloc[0] - 1.0
        daily = eq.pct_change().dropna()
        sharpe = float(daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else 0.0
        mdd = float((eq / eq.cummax() - 1.0).min())
        closed = self.trades
        wins = (closed["pnl"] > 0).sum() if not closed.empty else 0
        self.metrics = {
            "total_return": float(total_return),
            "sharpe": sharpe,
            "mdd": mdd,
            "n_trades": int(len(closed)),
            "win_rate": float(wins / len(closed)) if len(closed) else 0.0,
        }
        return self.metrics


def simulate(
    signals: pd.DataFrame,
    data: dict[str, pd.DataFrame],
    ep: ExitParams,
    pp: PortfolioParams = PortfolioParams(),
    start: str | None = None,
    trail: pd.DataFrame | None = None,
) -> BacktestResult:
    """사전 계산된 진입 시그널로 T+1 체결 가상투자를 실행."""
    close = _panel(data, "close")
    if trail is None:
        trail = close.rolling(ep.trail_ma).mean()
    calendar = close.index
    if start:
        calendar = calendar[calendar >= pd.Timestamp(start)]

    sig_by_day: dict[pd.Timestamp, pd.DataFrame] = {
        d: g for d, g in signals.groupby("date")
    }

    cash = pp.initial_capital
    positions: dict[str, Position] = {}
    pending_entries: list[dict] = []   # T일 시그널 -> T+1일 시가 진입
    pending_exits: list[str] = []      # 추세 이탈 -> T+1일 시가 청산
    trades: list[dict] = []
    equity_curve = {}

    def close_position(t: str, date: pd.Timestamp, price: float, reason: str) -> None:
        pos = positions.pop(t)
        proceeds = pos.shares * price * (1 - pp.slippage)
        cost = pos.shares * pos.entry_price
        nonlocal cash
        cash += proceeds
        trades.append({
            "ticker": t,
            "entry_date": pos.entry_date,
            "exit_date": date,
            "entry_price": round(pos.entry_price, 4),
            "exit_price": round(price, 4),
            "shares": pos.shares,
            "pnl": round(proceeds - cost, 2),
            "ret": round(price * (1 - pp.slippage) / pos.entry_price - 1.0, 4),
            "reason": reason,
        })

    def open_position(t: str, day: pd.Timestamp, base_price: float, pivot: float) -> None:
        nonlocal cash
        if t in positions or len(positions) >= pp.max_positions:
            return
        budget = min(cash, (cash + _positions_value(positions, data, day)) / pp.max_positions)
        price = base_price * (1 + pp.slippage)
        if price <= 0 or budget < 100:
            return
        shares = budget / price
        cash -= shares * price
        positions[t] = Position(
            ticker=t, entry_date=day, entry_price=price, shares=shares,
            stop_price=price * (1 - ep.stop_loss), pivot=pivot,
        )

    for day in calendar:
        # ── 1) 예약된 청산 (전일 추세 이탈) — 시가 체결
        for t in pending_exits:
            if t in positions and day in data[t].index:
                close_position(t, day, float(data[t].at[day, "open"]), "trail_ma")
        pending_exits = []

        # ── 2) 예약된 진입 (전일 종가 확인 시그널) — 시가 체결
        for entry in pending_entries:
            t = entry["ticker"]
            if t not in data or day not in data[t].index:
                continue
            o = float(data[t].at[day, "open"])
            if o > entry["pivot"] * (1 + pp.max_gap_extension):
                continue  # 추격 금지 갭업
            open_position(t, day, o, entry["pivot"])
        pending_entries = []

        # ── 3) 보유 포지션 관리 (당일 봉으로 스탑/목표/본전 판정)
        for t in list(positions):
            if day not in data[t].index:
                continue
            pos = positions[t]
            if pos.entry_date == day:
                continue  # 진입 당일은 관리하지 않음 (스탑은 다음날부터)
            bar = data[t].loc[day]
            o, h, l, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])

            if l <= pos.stop_price:  # 스탑 (갭다운이면 시가 체결)
                fill = min(o, pos.stop_price)
                reason = "stop_loss" if pos.stop_price < pos.entry_price else "breakeven_stop"
                close_position(t, day, fill, reason)
                continue
            if ep.profit_target and h >= pos.entry_price * (1 + ep.profit_target):
                close_position(t, day, pos.entry_price * (1 + ep.profit_target), "profit_target")
                continue
            if ep.free_roll and pos.stop_price < pos.entry_price and c >= pos.entry_price * (1 + ep.stop_loss):
                pos.stop_price = pos.entry_price  # 본전 스탑 (free roll)
            t_ma = trail.at[day, t] if t in trail.columns else np.nan
            if not np.isnan(t_ma) and c < t_ma:
                pending_exits.append(t)

        # ── 4) 신규 시그널 처리 (RS 내림차순 정렬 전제)
        #    - fill_mode='stop': buy-stop 주문이 당일 장중 체결된 것 → 당일 체결
        #    - fill_mode='next_open': 종가 확인 → T+1 시가 진입 예약
        if day in sig_by_day:
            for _, row in sig_by_day[day].iterrows():
                t = row["ticker"]
                if t in positions or t not in data or day not in data[t].index:
                    continue
                if row["fill_mode"] == "stop":
                    o = float(data[t].at[day, "open"])
                    if o > row["pivot"] * (1 + pp.max_gap_extension):
                        continue  # 갭업으로 추격 구간 초과 → 주문 취소로 간주
                    open_position(t, day, max(o, float(row["trigger"])), float(row["pivot"]))
                else:
                    pending_entries.append({"ticker": t, "pivot": float(row["pivot"])})

        equity_curve[day] = cash + _positions_value(positions, data, day)

    # 종료 시점 미청산 포지션은 마지막 종가로 강제 청산
    last_day = calendar[-1]
    for t in list(positions):
        series = data[t]["close"]
        last_price = float(series.loc[:last_day].iloc[-1])
        close_position(t, last_day, last_price, "end_of_backtest")

    trades_df = pd.DataFrame(trades)
    equity = pd.Series(equity_curve).sort_index()
    result = BacktestResult(trades=trades_df, equity=equity, exit_params=ep)
    result.compute_metrics()
    return result


def _positions_value(positions: dict[str, Position], data: dict[str, pd.DataFrame], day: pd.Timestamp) -> float:
    total = 0.0
    for t, pos in positions.items():
        series = data[t]["close"]
        sliced = series.loc[:day]
        if not sliced.empty:
            total += pos.shares * float(sliced.iloc[-1])
    return total


# ──────────────────────────────────────────────────────────────────
# 그리드 탐색 — 목적함수별 최적 모델
# ──────────────────────────────────────────────────────────────────

# 진입(VCP 엄격도) 변형 — strategy_spec §4.4의 "합리적 범위" 내에서 3단계
ENTRY_VARIANTS: dict[str, dict] = {
    "strict": {},  # 권장 기본값 그대로
    "medium": {"contraction_decay": 0.9, "dryup_ratio": 0.75,
               "breakout_vol_mult": 1.3, "final_contraction_max": 0.12},
    "loose": {"contraction_decay": 1.0, "dryup_ratio": 0.9,
              "breakout_vol_mult": 1.2, "final_contraction_max": 0.15,
              "base_min_weeks": 4},
}

GRID: dict[str, list] = {
    "stop_loss": [0.04, 0.06, 0.08],
    "trail_ma": [20, 50],
    "profit_target": [None, 0.15, 0.25],
    "free_roll": [False, True],
}

OBJECTIVES = {
    "return": ("총수익률 극대화", lambda m: m["total_return"]),
    "sharpe": ("샤프비율 극대화", lambda m: m["sharpe"]),
    "mdd": ("최대낙폭 최소화", lambda m: m["mdd"]),  # mdd는 음수 → 최댓값이 최소 낙폭
}


def grid_search(
    signal_sets: dict[str, pd.DataFrame],
    data: dict[str, pd.DataFrame],
    pp: PortfolioParams = PortfolioParams(),
    start: str | None = None,
) -> tuple[pd.DataFrame, dict[str, tuple[str, BacktestResult]]]:
    """(진입 변형 × 청산 그리드) 전체를 실행하고 목적함수별 최적 결과를 리턴."""
    close = _panel(data, "close")
    trails = {n: close.rolling(n).mean() for n in GRID["trail_ma"]}

    rows = []
    results: list[tuple[str, BacktestResult]] = []
    combos = list(itertools.product(*GRID.values()))
    for variant, signals in signal_sets.items():
        for i, combo in enumerate(combos):
            ep = ExitParams(**dict(zip(GRID.keys(), combo)))
            res = simulate(signals, data, ep, pp, start=start, trail=trails[ep.trail_ma])
            rows.append({
                "entry": variant,
                "stop_loss": ep.stop_loss, "trail_ma": ep.trail_ma,
                "profit_target": ep.profit_target, "free_roll": ep.free_roll,
                **res.metrics,
            })
            results.append((variant, res))
        logger.info("grid done for entry=%s (%d combos)", variant, len(combos))

    table = pd.DataFrame(rows)
    best: dict[str, tuple[str, BacktestResult]] = {}
    for key, (_, score) in OBJECTIVES.items():
        idx = int(np.argmax([score(r.metrics) for _, r in results]))
        best[key] = results[idx]
    return table, best


# ──────────────────────────────────────────────────────────────────
# 종합 평가 리포트 (사용자 지정 4가지 기준)
# ──────────────────────────────────────────────────────────────────

def top_companies(trades: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """실현 손익 기준 상위 기업 (기준 3)."""
    if trades.empty:
        return pd.DataFrame(columns=["ticker", "total_pnl", "n_trades", "avg_ret"])
    g = trades.groupby("ticker").agg(
        total_pnl=("pnl", "sum"), n_trades=("pnl", "size"), avg_ret=("ret", "mean")
    ).sort_values("total_pnl", ascending=False).head(n).reset_index()
    g["avg_ret"] = (g["avg_ret"] * 100).round(1)
    g["total_pnl"] = g["total_pnl"].round(0)
    return g


def buys_per_company(trades: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    """기업당 평균 매수 횟수와 횟수 분포표 (기준 4)."""
    if trades.empty:
        return 0.0, pd.DataFrame(columns=["매수횟수", "기업수"])
    counts = trades.groupby("ticker").size()
    dist = counts.value_counts().sort_index().rename_axis("매수횟수").reset_index(name="기업수")
    return float(counts.mean()), dist


def build_model_report(name: str, desc: str, res: BacktestResult, entry_variant: str = "strict") -> str:
    m = res.metrics
    ep = res.exit_params
    avg_buys, dist = buys_per_company(res.trades)
    top10 = top_companies(res.trades)

    lines = [
        f"=== 모델 [{name}] — {desc} ===",
        f"진입 변형: {entry_variant} | "
        f"청산 파라미터: 손절 -{ep.stop_loss:.0%} | 추세이탈 SMA{ep.trail_ma} | "
        f"목표익절 {f'{ep.profit_target:+.0%}' if ep.profit_target else '없음(계속 보유)'} | "
        f"본전스탑 {'ON' if ep.free_roll else 'OFF'}",
        "",
        f"[기준1] 전체 기간 수익률: {m['total_return']:+.1%}   "
        f"(참고: 샤프 {m['sharpe']:.2f}, MDD {m['mdd']:.1%})",
        f"[기준2] 매수 승률(익절 비율): {m['win_rate']:.1%}  ({int(m['win_rate']*m['n_trades'])}승 / {m['n_trades']}회)",
        "",
        "[기준3] 수익 상위 10개 기업 (실현손익 $):",
        top10.to_string(index=False),
        "",
        f"[기준4] 매수 시도 기업 수: {res.trades['ticker'].nunique() if not res.trades.empty else 0}개, "
        f"기업당 평균 매수 횟수: {avg_buys:.2f}회",
        "매수 횟수 분포:",
        dist.to_string(index=False),
        "",
    ]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────

def load_backtest_data(params: Params) -> dict[str, pd.DataFrame]:
    """캐시된 전 종목 데이터 로드 (업데이트 없음, 히스토리 충분한 종목만)."""
    tickers = [p.stem for p in Path(params.data.cache_dir).glob("*.parquet") if not p.stem.startswith("_")]
    data, _ = store.load_universe_history(tickers, params.data.cache_dir, params.data.lookback_years, update=False)
    return {t: df for t, df in data.items() if len(df) >= params.data.min_history_days}


def main(argv: list[str] | None = None) -> int:
    import argparse

    from sepa.config import load_params

    parser = argparse.ArgumentParser(description="SEPA backtest & model comparison")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--start", default=None, help="백테스트 시작일 (기본: 지표 웜업 직후)")
    parser.add_argument("--recompute-signals", action="store_true")
    parser.add_argument("--out", default="reports/backtest")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    params = load_params(args.config)

    logger.info("loading cached data...")
    data = load_backtest_data(params)
    logger.info("loaded %d tickers", len(data))

    signal_sets: dict[str, pd.DataFrame] = {}
    for variant, overrides in ENTRY_VARIANTS.items():
        v_params = replace(params, vcp=replace(params.vcp, **overrides))
        cache = Path(args.out) / f"entry_signals_{variant}.parquet"
        signals = precompute_entry_signals(data, v_params, cache_path=cache,
                                           use_cache=not args.recompute_signals)
        signal_sets[variant] = signals
        logger.info("entry=%s signals: %d", variant, len(signals))

    table, best = grid_search(signal_sets, data, start=args.start)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "grid_results.csv", index=False)

    n_sig = {v: len(s) for v, s in signal_sets.items()}
    report_parts = [
        f"SEPA 백테스트 종합 리포트 (생성: {pd.Timestamp.now():%Y-%m-%d %H:%M})",
        f"유니버스: 캐시 {len(data)}종목 | 진입 변형별 시그널 수: {n_sig}",
        f"자금 규칙: 초기 ${PortfolioParams.initial_capital:,.0f}, 최대 {PortfolioParams.max_positions}종목, "
        f"슬리피지 {PortfolioParams.slippage:.1%}/편도, T+1 시가 체결",
        "=" * 70, "",
    ]
    for key, (desc, _) in OBJECTIVES.items():
        variant, res = best[key]
        res.trades.to_csv(out / f"trades_{key}.csv", index=False)
        res.equity.rename("equity").to_csv(out / f"equity_{key}.csv")
        report_parts.append(build_model_report(key.upper(), desc, res, entry_variant=variant))

    report = "\n".join(report_parts)
    (out / "summary.txt").write_text(report)
    print(report)
    print(f"reports: {out}/summary.txt, grid_results.csv, trades_*.csv, equity_*.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
