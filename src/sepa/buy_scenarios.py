"""Shared timing-scenario scanner (replaces per-day scan_buy_scenarios_*.py copies).

Produces ``reports/buy_scenarios_YYYYMMDD.json`` rows with legacy scenario labels
(A/B/SOFT) for compat, plus ``earn_source`` / ``timing`` fields.

Pick pool (good stock) is **not** decided here — see ``sepa.pick_pool``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from sepa.earn_calendar import (
    EarnDateInfo,
    load_confirmed_earn_map,
    parse_earn_date,
)
from sepa.timing_gate import (
    BREAKOUT_PCT,
    NEAR_MA20_PCT,
    NEAR_SWING_L_PCT,
    SWING_LOOKBACK,
    VOL_HOT_RATIO,
    VOL_OK_RATIO,
    evaluate_timing_metrics,
)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DEFAULT_PORTFOLIO = ROOT / "config" / "portfolio_watch.yaml"


def rsi_series(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(alpha=1 / n, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / n, adjust=False).mean()
    rs = ma_up / ma_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def resolve_earn(
    ticker: str,
    meta: dict[str, Any],
    *,
    confirmed_map: dict[str, date],
) -> EarnDateInfo:
    """Prefer portfolio SSOT confirmed date; else meta date as estimate."""
    t = ticker.upper()
    if t in confirmed_map:
        return EarnDateInfo(confirmed_map[t], "confirmed", "portfolio_watch SSOT")
    raw = meta.get("earnDate") or meta.get("earn_date")
    # Explicit override on meta
    if meta.get("earn_source") or meta.get("earn_confirmed") is not None:
        from sepa.earn_calendar import earn_info_from_row

        return earn_info_from_row(meta, default_source="estimate")
    return EarnDateInfo(parse_earn_date(raw), "estimate", "rank/yfinance calendar")


def analyze_ticker(
    ticker: str,
    meta: dict[str, Any],
    *,
    as_of: date,
    confirmed_map: dict[str, date] | None = None,
    history: pd.DataFrame | None = None,
) -> dict[str, Any] | None:
    """Fetch (or use) history and return timing scenario row or None if too short."""
    import yfinance as yf

    t = ticker.upper()
    confirmed_map = confirmed_map or {}
    if history is None:
        hist = yf.Ticker(t).history(period="1y", auto_adjust=True)
    else:
        hist = history
    if hist is None or hist.empty:
        logger.info("SKIP empty hist %s", t)
        return None
    # Drop incomplete session bars (OHLC NaN) so MA/RSI use last good close
    hist = hist.dropna(subset=["Close", "High", "Low"])
    if len(hist) < 210:
        logger.info("SKIP short hist %s %s", t, len(hist))
        return None

    close = hist["Close"].astype(float)
    vol = hist["Volume"].astype(float)
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    ma200 = close.rolling(200).mean()
    rsi = rsi_series(close)

    last = float(close.iloc[-1])
    m20 = float(ma20.iloc[-1])
    m60 = float(ma60.iloc[-1])
    m200 = float(ma200.iloc[-1])
    rsi_v = float(rsi.iloc[-1])

    swing = hist.iloc[-SWING_LOOKBACK:]
    swing_hi = float(swing["High"].max())
    swing_lo = float(swing["Low"].min())

    vs_ma20 = (last / m20 - 1.0) * 100.0
    vs_ma200 = (last / m200 - 1.0) * 100.0
    pct_hi = last / swing_hi - 1.0

    near_ma20 = abs(vs_ma20) <= NEAR_MA20_PCT
    near_l = (last / swing_lo - 1.0) * 100.0 <= NEAR_SWING_L_PCT and last >= swing_lo * 0.995
    above200 = last > m200
    align = m20 >= m60

    vol20 = float(vol.iloc[-20:].mean())
    vol_last = float(vol.iloc[-1])
    vol_ratio = (vol_last / vol20) if vol20 > 0 else 0.0
    vol_ok = vol_ratio >= VOL_OK_RATIO
    vol_hot = vol_ratio >= VOL_HOT_RATIO
    vol_recover = vol_ratio >= 1.0
    breakout = last >= swing_hi * (1.0 + BREAKOUT_PCT)

    earn = resolve_earn(t, meta, confirmed_map=confirmed_map)
    timing = evaluate_timing_metrics(
        ticker=t,
        above200=above200,
        align=align,
        near_ma20=near_ma20,
        near_swing_l=near_l,
        rsi=rsi_v,
        pct_hi=pct_hi,
        vol_ok=vol_ok,
        vol_hot=vol_hot,
        breakout=breakout,
        earn=earn,
        as_of=as_of,
    )

    scenario = timing.legacy_scenario  # A | B | SOFT | ""
    caution = ""
    if scenario == "B" and rsi_v >= 68:
        caution = "고점·RSI주의"
    if earn.warn_estimate_window(as_of):
        caution = (caution + " · " if caution else "") + f"추정실적창({earn.earn_date})"

    edays = earn.days_to(as_of)
    # earn_d5 flag: confirmed hard window only (compat field name)
    earn_d5 = earn.blocks_new_buys(as_of)

    row = {
        **meta,
        "t": t,
        "last": last,
        "rsi": rsi_v,
        "above200": above200,
        "align": align,
        "pct_hi": pct_hi,
        "near_l": near_l,
        "near_ma20": near_ma20,
        "breakout": breakout,
        "vol_ok": vol_ok,
        "vol_hot": vol_hot,
        "vol_recover": vol_recover,
        "vol_ratio": vol_ratio,
        "swing_lo": swing_lo,
        "swing_hi": swing_hi,
        "vs_ma20": vs_ma20,
        "vs_ma200": vs_ma200,
        "edays": edays,
        "earn_d5": earn_d5,
        "earnDate": earn.earn_date.isoformat() if earn.earn_date else meta.get("earnDate"),
        "earn_source": earn.source,
        "earn_note": earn.note,
        "timing": timing.status,
        "scenario": scenario,
        "caution": caution,
        "gate": "timing",
    }
    return row


def run_scan(
    *,
    as_of: date,
    rank_path: Path,
    out_path: Path,
    portfolio_path: Path | None = DEFAULT_PORTFOLIO,
    hits_only: bool = True,
) -> dict[str, Any]:
    """Scan all tickers in rank JSON; write buy_scenarios payload."""
    rank = json.loads(Path(rank_path).read_text(encoding="utf-8"))
    meta_by = {str(r["t"]).upper(): r for r in rank.get("rows") or []}
    confirmed = load_confirmed_earn_map(portfolio_path) if portfolio_path else {}

    hits: list[dict[str, Any]] = []
    for t, meta in meta_by.items():
        try:
            row = analyze_ticker(t, meta, as_of=as_of, confirmed_map=confirmed)
        except Exception as exc:  # noqa: BLE001
            print(f"ERR {t} {exc}")
            continue
        if row is None:
            continue
        if hits_only and not row.get("scenario"):
            print(
                f"---- {t:5} rsi={row['rsi']:.1f} vs20={row['vs_ma20']:+.1f}% "
                f"earn={row.get('earn_source')} d5={row['earn_d5']}"
            )
            continue
        hits.append(row)
        print(
            f"{row['scenario']:4} {t:5} timing={row.get('timing')} "
            f"rsi={row['rsi']:.1f} vs20={row['vs_ma20']:+.1f}% "
            f"pct_hi={row['pct_hi']*100:+.1f}% earn={row.get('earn_source')} "
            f"{row.get('caution') or ''}"
        )

    order = {"A": 0, "B": 1, "SOFT": 2}
    hits.sort(key=lambda r: (order.get(str(r.get("scenario") or ""), 9), r.get("rank") or 99))

    payload = {
        "as_of": as_of.isoformat(),
        "gate": "timing GO_A/GO_B/WAIT (pick_pool=Chase separate)",
        "rules": {
            "pick": "Chase 본선 (sepa.pick_pool) — 좋은 종목",
            "A": "타이밍 GO_A 눌림",
            "B": "타이밍 GO_B 돌파 — 프리마켓OS 기본 WAIT",
            "SOFT": "타이밍 WAIT 근접",
            "earn": "earn_confirmed.yaml∪portfolio=confirmed; rank/yfinance=estimate",
            "exec_window": "KR 17:30-20:55 premkt limit only",
        },
        "rows": hits,
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    a = [r["t"] for r in hits if r.get("scenario") == "A"]
    b = [r["t"] for r in hits if r.get("scenario") == "B"]
    soft = [r["t"] for r in hits if r.get("scenario") == "SOFT"]
    print(f"wrote {out_path} A={a} B={b} SOFT={soft}")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Timing scenario scan → buy_scenarios_*.json")
    ap.add_argument("--asof", required=True, help="YYYY-MM-DD")
    ap.add_argument("--rank", required=True, help="path to rank_YYYYMMDD.json")
    ap.add_argument("--out", default="", help="output json (default reports/buy_scenarios_<asof>.json)")
    ap.add_argument("--portfolio", default=str(DEFAULT_PORTFOLIO), help="SSOT yaml for confirmed earns")
    args = ap.parse_args(argv)
    as_of = date.fromisoformat(args.asof)
    stamp = as_of.strftime("%Y%m%d")
    rank_path = Path(args.rank)
    out = Path(args.out) if args.out else REPORTS / f"buy_scenarios_{stamp}.json"
    port = Path(args.portfolio) if args.portfolio else None
    run_scan(as_of=as_of, rank_path=rank_path, out_path=out, portfolio_path=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
