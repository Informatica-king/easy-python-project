#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A′ / B / SOFT buy-scenario scanner for 2026-08-12 deep universe."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ASOF = date(2026, 8, 12)
RANK_PATH = Path("/workspace/reports/rank_20260812.json")
OUT = Path("/workspace/reports/buy_scenarios_20260812.json")

# Thresholds aligned with RS≥70 A′ agreement
NEAR_MA20_PCT = 3.0          # |vs_ma20| ≤ 3%
NEAR_SWING_L_PCT = 3.0       # within 3% of swing low
SWING_LOOKBACK = 20
VOL_OK_RATIO = 0.8           # vol / 20d avg
VOL_HOT_RATIO = 1.5
BREAKOUT_PCT = 0.0           # close >= swing high
RSI_A_LO, RSI_A_HI = 42.0, 62.0
PCT_HI_LO, PCT_HI_HI = -0.08, -0.01
D5_WINDOW_DAYS = 5


def rsi_series(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(alpha=1 / n, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / n, adjust=False).mean()
    rs = ma_up / ma_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def in_earn_d5(earn: str | None, as_of: date) -> tuple[bool, int | None]:
    """True if as_of in [earn-5, earn] inclusive. edays = earn - as_of (neg = post)."""
    if not earn:
        return False, None
    try:
        ed = date.fromisoformat(str(earn)[:10])
    except ValueError:
        return False, None
    edays = (ed - as_of).days
    blocked = 0 <= edays <= D5_WINDOW_DAYS
    return blocked, edays


def analyze(t: str, meta: dict) -> dict | None:
    tk = yf.Ticker(t)
    hist = tk.history(period="1y", auto_adjust=True)
    if hist is None or len(hist) < 210:
        print("SKIP short hist", t, 0 if hist is None else len(hist))
        return None
    close = hist["Close"].astype(float)
    high = hist["High"].astype(float)
    low = hist["Low"].astype(float)
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

    earn = meta.get("earnDate")
    earn_d5, edays = in_earn_d5(earn, ASOF)

    # A′ gate
    a_ok = (
        above200
        and align
        and (near_ma20 or near_l)
        and (RSI_A_LO <= rsi_v <= RSI_A_HI)
        and (PCT_HI_LO <= pct_hi <= PCT_HI_HI)
        and vol_ok
        and not earn_d5
    )
    # B gate
    b_ok = breakout and vol_hot and rsi_v < 70 and not earn_d5
    caution = ""
    if b_ok and rsi_v >= 68:
        caution = "고점·RSI주의"

    # SOFT: directionally close to A′
    soft = False
    if not a_ok and not b_ok and above200 and align and (near_ma20 or near_l) and not earn_d5:
        soft_misses = 0
        if not (RSI_A_LO <= rsi_v <= RSI_A_HI):
            soft_misses += 1
        if not (PCT_HI_LO <= pct_hi <= PCT_HI_HI):
            soft_misses += 1
        if not vol_ok:
            soft_misses += 1
        soft = soft_misses <= 2 and soft_misses >= 1

    scenario = ""
    if a_ok:
        scenario = "A"
    elif b_ok:
        scenario = "B"
    elif soft:
        scenario = "SOFT"

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
        "earn_source": "estimate",  # yfinance calendar — not IR-confirmed
        "scenario": scenario,
        "caution": caution,
        "gate": "timing",  # was A' — timing only; pick_pool is Chase
    }
    return row


def main():
    rank = json.loads(RANK_PATH.read_text(encoding="utf-8"))
    meta_by = {r["t"]: r for r in rank["rows"]}
    hits = []
    for t, meta in meta_by.items():
        try:
            row = analyze(t, meta)
        except Exception as exc:  # noqa: BLE001
            print("ERR", t, exc)
            continue
        if row is None:
            continue
        if row["scenario"]:
            hits.append(row)
            print(
                f"{row['scenario']:4} {t:5} rsi={row['rsi']:.1f} vs20={row['vs_ma20']:+.1f}% "
                f"pct_hi={row['pct_hi']*100:+.1f}% near20={row['near_ma20']} nearL={row['near_l']} "
                f"bo={row['breakout']} vh={row['vol_hot']} earn_d5={row['earn_d5']} {row['caution']}"
            )
        else:
            print(f"---- {t:5} rsi={row['rsi']:.1f} vs20={row['vs_ma20']:+.1f}% earn_d5={row['earn_d5']}")

    # Prefer A > B > SOFT; within group by chase rank
    order = {"A": 0, "B": 1, "SOFT": 2}
    hits.sort(key=lambda r: (order.get(r["scenario"], 9), r.get("rank") or 99))

    payload = {
        "as_of": ASOF.isoformat(),
        "gate": "timing GO_A/GO_B/WAIT (pick_pool=Chase separate)",
        "rules": {
            "pick": "Chase 본선 (sepa.pick_pool) — 좋은 종목",
            "A": "타이밍 GO_A 눌림 — MA200↑ + MA20≥MA60 + (near MA20|swingL) + RSI42-62 + high -1%~-8% + volOK",
            "B": "타이밍 GO_B 돌파 — 프리마켓OS 기본 WAIT(비실행)",
            "SOFT": "타이밍 WAIT 근접",
            "earn": "earn_source=estimate by default; confirmed EARN_D5 only hard-blocks",
        },
        "rows": hits,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    a = [r["t"] for r in hits if r["scenario"] == "A"]
    b = [r["t"] for r in hits if r["scenario"] == "B"]
    soft = [r["t"] for r in hits if r["scenario"] == "SOFT"]
    print(f"wrote {OUT} A={a} B={b} SOFT={soft}")


if __name__ == "__main__":
    main()
