#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch Chase rank + qual stubs for 2026-08-01 deep universe (51 tickers)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import yfinance as yf

from sepa.share_gain import FORMULA_SHARE_SUFFIX, assess_share_gain, enrich_qual_fields, enrich_rank_row

ASOF = date(2026, 8, 1)
TICKERS = [
    "TXG", "CDNA", "TVTX", "LIND", "FTRE", "AMRX", "JAZZ", "ADPT", "KRYS", "CGNX",
    "INDV", "FA", "ROKU", "GPRE", "SHOO", "CMPR", "CRSR", "INCY", "STLD", "KNSA",
    "SBLK", "VTRS", "CASY", "ECPG", "NESR", "CBRL", "SENEA", "PEBO", "FTNT", "DDOG",
    "HST", "PGNY", "CHEF", "CNXN", "SCSC", "IESC", "PAGP", "LQDA", "DNTH", "CLMT",
    "PTGX", "ATLC", "SEPN", "RAPP", "BRKR", "ALKS", "DRH", "ACHC", "APA", "TFSL",
    "LAUR",
]
OUT = Path("/tmp/rank_20260801.json")
QUAL_SEEDS = [
    Path("/workspace/reports/qual_20260731.json"),
    Path("/tmp/qual_20260731.json"),
    Path("/tmp/qual_20260731_full.json"),
    Path("/workspace/reports/qual_20260730b.json"),
]
QUAL_OUT = Path("/tmp/qual_20260801_full.json")
FORMULA = (
    "epsBeat + upside - near_high - max(prem,0) + clip(avgSurp) "
    + FORMULA_SHARE_SUFFIX
)

SECTOR_KO = {
    "Technology": "IT·기술",
    "Healthcare": "헬스케어",
    "Financial Services": "금융",
    "Consumer Cyclical": "경기소비",
    "Consumer Defensive": "필수소비",
    "Energy": "에너지",
    "Industrials": "산업재",
    "Basic Materials": "소재",
    "Real Estate": "부동산",
    "Communication Services": "통신",
    "Utilities": "유틸리티",
}


def _earn_date(info, tk):
    try:
        cal = tk.calendar or {}
        ed = cal.get("Earnings Date")
        if isinstance(ed, list) and ed:
            d0 = ed[0]
            return d0.isoformat()[:10] if hasattr(d0, "isoformat") else str(d0)[:10]
    except Exception:
        pass
    ts = info.get("earningsTimestamp") or info.get("earningsTimestampStart")
    if ts:
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
        except Exception:
            pass
    return None


def _eps_stats(tk):
    try:
        eh = tk.earnings_history
        if eh is None or eh.empty:
            return 0, 0, None
        last = eh.tail(4)
        n = len(last)
        beats = int((last["surprisePercent"] > 0).sum())
        avg = float(last["surprisePercent"].mean())
        return beats, n, max(min(avg, 1.0), -0.5)
    except Exception:
        return 0, 0, None


def fetch_one(t):
    tk = yf.Ticker(t)
    info = tk.info or {}
    px = info.get("currentPrice") or info.get("regularMarketPrice")
    if px is None:
        h = tk.history(period="5d")
        if h is None or h.empty:
            return None, info
        px = float(h["Close"].iloc[-1])
    px = float(px)
    h52 = info.get("fiftyTwoWeekHigh")
    l52 = info.get("fiftyTwoWeekLow")
    if h52 is None or l52 is None:
        hist = tk.history(period="1y")
        if hist is not None and not hist.empty:
            h52 = float(hist["High"].max()) if h52 is None else h52
            l52 = float(hist["Low"].min()) if l52 is None else l52
    h52 = float(h52) if h52 else px
    l52 = float(l52) if l52 else px
    ptA = info.get("targetMeanPrice")
    ptL = info.get("targetLowPrice")
    ptH = info.get("targetHighPrice")
    ptA = float(ptA) if ptA else None
    upside = (ptA / px - 1.0) if ptA and px else None
    near_high = px / h52 if h52 else None
    prem = (px / ptA - 1.0) if ptA and px else None
    beats, n, avg_surp = _eps_stats(tk)
    row = {
        "t": t,
        "name": info.get("shortName") or info.get("longName") or t,
        "sector": info.get("sector") or "",
        "industry": info.get("industry") or "",
        "px": px,
        "h": h52,
        "l": l52,
        "ptA": ptA,
        "ptL": float(ptL) if ptL else None,
        "ptH": float(ptH) if ptH else None,
        "rec": info.get("recommendationKey") or "",
        "mcap": info.get("marketCap"),
        "earnDate": _earn_date(info, tk),
        "epsBeat": beats,
        "epsN": n,
        "avgSurp": avg_surp,
        "upside": upside,
        "near_high": near_high,
        "prem": prem,
    }
    ups = upside or 0.0
    near = near_high or 0.0
    pr = prem or 0.0
    sur = avg_surp if avg_surp is not None else 0.0
    sur = max(min(sur, 1.0), -0.5)
    row["chase_raw"] = float(beats) + ups - near - max(pr, 0.0) + sur
    enrich_rank_row(row)  # 경쟁점유 꾸준 상승 가산 (+마진악화 시 취소)
    return row, info


def stub_qual(t, row, info):
    sec = SECTOR_KO.get(row.get("sector") or "", row.get("sector") or "—")
    name = row.get("name") or t
    feat = row.get("industry") or "—"
    ups = row.get("upside")
    near = row.get("near_high") or 0
    beats = row.get("epsBeat") or 0
    if ups is not None and ups < -0.1 and near >= 0.92:
        chase, entry = "하·과열", "관망"
    elif ups is not None and ups > 0.2 and beats >= 3:
        chase, entry = "상", "분할검토"
    elif beats >= 3:
        chase, entry = "중", "눌림"
    else:
        chase, entry = "중하", "관망"
    summary = (info.get("longBusinessSummary") or name)[:120]
    pt = row.get("ptA") or row.get("px") or 0
    px = row.get("px") or pt
    return {
        "name": name,
        "sector": sec,
        "feat": feat,
        "item": f"{name}. 한줄: {summary}",
        "fin": (
            f"EPS {beats}/{row.get('epsN') or 0} · upside {ups*100:+.0f}%"
            if ups is not None
            else f"EPS {beats}/{row.get('epsN') or 0}"
        ),
        "strat": f"{chase} · 라이브 데이터 기반 초안",
        "news": "실적·가이던스·섹터 뉴스 모니터",
        "bull": f"${pt*1.1:.0f}–{pt*1.25:.0f}" if pt else "—",
        "base": f"${px*0.95:.0f}–{pt:.0f}" if pt else "—",
        "bear": f"${px*0.7:.0f}–{px*0.85:.0f}" if px else "—",
        "brk": "실적 미스·가이던스 컷·섹터 붕괴",
        "eps": f"{beats}/{row.get('epsN') or 0}",
        "entry": entry,
        "drop": "가이던스 컷",
        "chase": chase,
        "abc": f"${pt*0.9:.0f}/${pt:.0f}/${pt*1.15:.0f}" if pt else "—",
    }


def load_qual_base():
    base = {}
    for p in QUAL_SEEDS:
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for k, v in data.items():
            if k not in base or len(str(v.get("item", ""))) > len(str(base.get(k, {}).get("item", ""))):
                base[k] = v
    return base


def main():
    print("n tickers", len(TICKERS), "as_of", ASOF.isoformat())
    assert len(TICKERS) == 51, len(TICKERS)
    base = load_qual_base()
    rows, failed, qual = [], [], dict(base)
    for t in TICKERS:
        try:
            r, info = fetch_one(t)
            if r is None:
                failed.append(t)
                print("FAIL", t)
                continue
            rows.append(r)
            if t not in qual or not qual[t].get("item"):
                qual[t] = stub_qual(t, r, info)
            # 심층 코멘트: 점유 상승 가산 문구
            sg = assess_share_gain(t)
            if sg.strat_note:
                qual[t] = enrich_qual_fields(qual.get(t, {}), sg)
            ups = f"{r['upside']:+.1%}" if r["upside"] is not None else "—"
            bonus = r.get("share_bonus") or 0.0
            btxt = f" share+{bonus:.2f}" if bonus else ""
            print(
                f"OK {t:5} px={r['px']:.2f} ups={ups} beat={r['epsBeat']}/{r['epsN']} "
                f"raw={r['chase_raw']:.3f}{btxt} earn={r.get('earnDate')}"
            )
        except Exception as e:  # noqa: BLE001
            failed.append(t)
            print("ERR", t, e)
    rows.sort(key=lambda x: x["chase_raw"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    OUT.write_text(
        json.dumps(
            {"as_of": ASOF.isoformat(), "rows": rows, "failed": failed, "formula": FORMULA},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    QUAL_OUT.write_text(json.dumps(qual, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} n={len(rows)} failed={failed}")
    print("TOP15:")
    for r in rows[:15]:
        ups = f"{r['upside']:+.1%}" if r["upside"] is not None else "—"
        print(f"  #{r['rank']:2} {r['t']:5} raw={r['chase_raw']:.3f} ups={ups} earn={r.get('earnDate')}")


if __name__ == "__main__":
    main()
