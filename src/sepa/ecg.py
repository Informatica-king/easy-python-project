"""Early-Confirmed Growth (ECG) lens — D34 Phase A1.

Fund formula is NOT modified. Reads existing fundamental (+ optional price cache)
and emits ECG scores for "confirmed + early" growth candidates.

Confirmed (AND):
  Stage-2 pool (input already Stage2-filtered) AND
  (fund_score >= pool median OR S/B/D positive contribution)

Early factors (weights sum 100; E5 VCP deferred):
  E1 RS band 25 · E3 accel turn-up/earliness 30 · E2 52w proximity 20 · E4 SMA200 turn 25
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from sepa.config import TrendTemplateParams, load_params
from sepa.data import store
from sepa.indicators import add_indicators

logger = logging.getLogger(__name__)

# Approved A0 defaults (user 2026-10-05)
W_E1 = 25.0
W_E2 = 20.0
W_E3 = 30.0
W_E4 = 25.0
# E5 reserved for later (VCP); weights already sum to 100 without it.

RS_EARLY_LO = 70.0
RS_EARLY_HI = 90.0
RS_MID_HI = 95.0


def pool_fund_median(fund_score: pd.Series) -> float:
    s = pd.to_numeric(fund_score, errors="coerce").dropna()
    if s.empty:
        return float("nan")
    return float(s.median())


def confirmed_mask(df: pd.DataFrame, median: float | None = None) -> pd.Series:
    """Stage2 assumed for input rows. Realized growth confirmation gate."""
    fund = pd.to_numeric(df.get("fund_score"), errors="coerce")
    if median is None or (isinstance(median, float) and np.isnan(median)):
        median = pool_fund_median(fund)
    s = pd.to_numeric(df.get("s_surprise"), errors="coerce").fillna(0.0)
    b = pd.to_numeric(df.get("b_raw"), errors="coerce").fillna(0.0)
    d = pd.to_numeric(df.get("d_raw"), errors="coerce").fillna(0.0)
    path_a = fund >= median
    path_b = (s > 0) | (b > 0) | (d > 0)
    return (path_a | path_b).fillna(False)


def score_e1_rs_band(rs: float) -> float:
    """Higher in [70, 90); taper through [90, 95); soft penalty ≥95."""
    if pd.isna(rs):
        return 0.0
    r = float(rs)
    if r < RS_EARLY_LO:
        return 0.0
    if r < RS_EARLY_HI:
        # peak at mid of band (~80)
        return float(100.0 - abs(r - 80.0) * 1.5)  # 70→85, 80→100, 89.9→85.15
    if r < RS_MID_HI:
        # 90 → 60, 95 → 30 linear
        return float(60.0 - (r - 90.0) * (30.0 / 5.0))
    # ≥95: 30 down to 10 at 100
    return float(max(10.0, 30.0 - (r - 95.0) * 4.0))


def score_e2_52w_proximity(close: float, high_52w: float) -> float:
    """Best near 52w high but not extended; deep below high scores low."""
    if pd.isna(close) or pd.isna(high_52w) or high_52w <= 0:
        return float("nan")
    dist = float(close) / float(high_52w) - 1.0
    # sweet spot [-25%, +5%]
    if -0.25 <= dist <= 0.05:
        # peak at 0 (at highs)
        return float(100.0 - abs(dist) / 0.25 * 20.0)  # at -25% → 80, at 0 → 100, at +5% → 96
    if 0.05 < dist <= 0.15:
        # getting extended
        return float(70.0 - (dist - 0.05) / 0.10 * 40.0)  # 5%→70, 15%→30
    if dist > 0.15:
        return float(max(5.0, 30.0 - (dist - 0.15) * 100.0))
    # below -25%
    return float(max(0.0, 80.0 + (dist + 0.25) / 0.25 * 80.0))  # -50% → 0


def score_e3_accel_earliness(
    b_raw: float,
    d_raw: float,
    eps_accel_n: float,
    sales_accel_n: float,
) -> float:
    """Proxy for 'just turned up': positive B/D with shallow accel depth.

    True prior-quarter turn-up needs history; A1 uses accel_n as earliness proxy
    once B or D contributes positively.
    """
    b = 0.0 if pd.isna(b_raw) else float(b_raw)
    d = 0.0 if pd.isna(d_raw) else float(d_raw)
    if b <= 0 and d <= 0:
        return 0.0
    n_b = 0.0 if pd.isna(eps_accel_n) else float(eps_accel_n)
    n_d = 0.0 if pd.isna(sales_accel_n) else float(sales_accel_n)
    # depth of the positive leg(s)
    depths = []
    if b > 0:
        depths.append(n_b)
    if d > 0:
        depths.append(n_d)
    n = max(depths) if depths else 0.0
    if n <= 1:
        return 100.0
    if n <= 2:
        return 70.0
    if n <= 3:
        return 45.0
    return 25.0


def score_e4_sma200_turn(
    sma200: pd.Series,
    *,
    trend_days: int = 21,
    lookback: int = 126,
) -> float:
    """High if SMA200 is rising and the turn from decline/flat is recent."""
    s = sma200.dropna()
    if len(s) < lookback + trend_days + 5:
        return float("nan")
    now = float(s.iloc[-1])
    past = float(s.iloc[-1 - trend_days])
    rising = now > past
    if not rising:
        return 15.0
    window = s.iloc[-(lookback + 1) :]
    # index of minimum in window (relative)
    rel_min = int(window.values.argmin())
    days_since_trough = len(window) - 1 - rel_min
    if days_since_trough <= 21:
        return 100.0
    if days_since_trough <= 42:
        return 80.0
    if days_since_trough <= 63:
        return 55.0
    if days_since_trough <= 84:
        return 35.0
    return 20.0  # rising but trough was long ago → mature uptrend


def _weighted_early(e1: float, e2: float, e3: float, e4: float) -> float:
    """Renormalize over available (non-NaN) early factors."""
    parts = [
        (W_E1, e1),
        (W_E2, e2),
        (W_E3, e3),
        (W_E4, e4),
    ]
    avail = [(w, v) for w, v in parts if not pd.isna(v)]
    if not avail:
        return float("nan")
    wsum = sum(w for w, _ in avail)
    return float(sum(w * v for w, v in avail) / wsum)


def enrich_price_features(
    tickers: list[str],
    cache_dir: str | Path,
    *,
    as_of: str | None = None,
    lookback_years: int = 3,
    tp: TrendTemplateParams | None = None,
) -> pd.DataFrame:
    """Load cache prices and compute close, high_52w, E4 score per ticker."""
    tp = tp or TrendTemplateParams()
    cutoff = pd.Timestamp(as_of) if as_of else None
    rows: list[dict] = []
    for t in tickers:
        try:
            raw = store.get_history(t, cache_dir, lookback_years, update=False)
        except Exception as exc:  # noqa: BLE001
            logger.debug("price skip %s: %s", t, exc)
            rows.append({"ticker": t, "px_close": np.nan, "high_52w": np.nan, "e4_sma200_turn": np.nan})
            continue
        if raw is None or raw.empty:
            rows.append({"ticker": t, "px_close": np.nan, "high_52w": np.nan, "e4_sma200_turn": np.nan})
            continue
        df = raw.copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        if cutoff is not None:
            df = df.loc[:cutoff]
        if df.empty:
            rows.append({"ticker": t, "px_close": np.nan, "high_52w": np.nan, "e4_sma200_turn": np.nan})
            continue
        ind = add_indicators(df, tp)
        last = ind.iloc[-1]
        e4 = score_e4_sma200_turn(ind["sma200"], trend_days=int(tp.trend_days))
        rows.append(
            {
                "ticker": str(t).upper(),
                "px_close": float(last["close"]) if pd.notna(last.get("close")) else np.nan,
                "high_52w": float(last["high_52w"]) if pd.notna(last.get("high_52w")) else np.nan,
                "e4_sma200_turn": e4,
            }
        )
    return pd.DataFrame(rows)


def compute_ecg_table(
    fund: pd.DataFrame,
    *,
    price_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return ECG scored table. Does not alter fund_score."""
    df = fund.copy()
    df["ticker"] = df["ticker"].astype(str).str.upper()
    if "rs_rank" not in df.columns:
        raise ValueError("fundamental frame needs rs_rank")
    if "fund_score" not in df.columns:
        raise ValueError("fundamental frame needs fund_score")

    med = pool_fund_median(df["fund_score"])
    df["pool_fund_median"] = med
    df["confirmed"] = confirmed_mask(df, med)

    rs = pd.to_numeric(df["rs_rank"], errors="coerce")
    df["e1_rs_band"] = rs.map(score_e1_rs_band)

    b_raw = pd.to_numeric(df.get("b_raw"), errors="coerce")
    d_raw = pd.to_numeric(df.get("d_raw"), errors="coerce")
    n_b = pd.to_numeric(df.get("eps_accel_n"), errors="coerce")
    n_d = pd.to_numeric(df.get("sales_accel_n"), errors="coerce")
    df["e3_accel_early"] = [
        score_e3_accel_earliness(b, d, nb, nd)
        for b, d, nb, nd in zip(b_raw, d_raw, n_b, n_d)
    ]

    if price_features is not None and not price_features.empty:
        px = price_features.copy()
        px["ticker"] = px["ticker"].astype(str).str.upper()
        df = df.merge(px, on="ticker", how="left")
    else:
        df["px_close"] = pd.to_numeric(df.get("close"), errors="coerce")
        df["high_52w"] = np.nan
        df["e4_sma200_turn"] = np.nan

    close = pd.to_numeric(df.get("px_close"), errors="coerce")
    # fallback to fundamental close if px_close missing
    if close.isna().all() and "close" in df.columns:
        close = pd.to_numeric(df["close"], errors="coerce")
    hi = pd.to_numeric(df.get("high_52w"), errors="coerce")
    df["e2_52w_prox"] = [
        score_e2_52w_proximity(c, h) for c, h in zip(close, hi)
    ]
    if "e4_sma200_turn" not in df.columns:
        df["e4_sma200_turn"] = np.nan

    early = [
        _weighted_early(e1, e2, e3, e4)
        for e1, e2, e3, e4 in zip(
            df["e1_rs_band"],
            df["e2_52w_prox"],
            df["e3_accel_early"],
            df["e4_sma200_turn"],
        )
    ]
    df["early_score"] = early
    df["ecg_score"] = np.where(df["confirmed"], df["early_score"], 0.0)
    df["ecg_score"] = pd.to_numeric(df["ecg_score"], errors="coerce").fillna(0.0)

    df = df.sort_values(["ecg_score", "fund_score", "rs_rank"], ascending=False)
    df["ecg_rank"] = range(1, len(df) + 1)
    return df.reset_index(drop=True)


def latest_fundamental_csv(report_dir: str | Path) -> Path | None:
    paths = sorted(Path(report_dir).glob("fundamental_*.csv"))
    return paths[-1] if paths else None


def stamp_from_fundamental_path(path: Path) -> str:
    stem = path.stem  # fundamental_YYYYMMDD
    parts = stem.split("_")
    return parts[-1] if parts else datetime.now().strftime("%Y%m%d")


def run_ecg(
    *,
    fund_path: Path,
    cache_dir: str | Path,
    report_dir: str | Path,
    as_of: str | None = None,
    lookback_years: int = 3,
    enrich_prices: bool = True,
) -> tuple[pd.DataFrame, Path]:
    fund = pd.read_csv(fund_path)
    tickers = fund["ticker"].astype(str).str.upper().tolist()
    px = None
    if enrich_prices:
        px = enrich_price_features(
            tickers,
            cache_dir,
            as_of=as_of,
            lookback_years=lookback_years,
        )
    table = compute_ecg_table(fund, price_features=px)
    stamp = stamp_from_fundamental_path(fund_path)
    if as_of:
        stamp = as_of.replace("-", "")
    out_dir = Path(report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"ecg_{stamp}.csv"
    # keep a readable column subset first, then extras
    prefer = [
        "ticker",
        "name",
        "rs_rank",
        "fund_score",
        "pool_fund_median",
        "confirmed",
        "e1_rs_band",
        "e2_52w_prox",
        "e3_accel_early",
        "e4_sma200_turn",
        "early_score",
        "ecg_score",
        "ecg_rank",
        "s_surprise",
        "b_raw",
        "d_raw",
        "eps_accel_n",
        "sales_accel_n",
        "px_close",
        "high_52w",
        "market_cap",
        "sector",
    ]
    cols = [c for c in prefer if c in table.columns] + [
        c for c in table.columns if c not in prefer
    ]
    table[cols].to_csv(out, index=False)
    return table, out


def print_ecg_summary(table: pd.DataFrame, *, top_n: int = 25) -> None:
    n = len(table)
    n_conf = int(table["confirmed"].sum()) if "confirmed" in table.columns else 0
    med = table["pool_fund_median"].iloc[0] if n else float("nan")
    print(f"\n=== ECG (Early-Confirmed Growth) — n={n} confirmed={n_conf} pool_median={med:.1f} ===\n")
    print("  (Fund formula unchanged · E5/VCP deferred · price E2/E4 use cache when available)\n")
    def _fmt(v: object) -> str:
        try:
            x = float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return "n/a"
        return "n/a" if pd.isna(x) else f"{x:.0f}"

    show = table.head(top_n)
    for _, r in show.iterrows():
        name = str(r.get("name", ""))[:36]
        flag = "Y" if r.get("confirmed") else "N"
        print(
            f"  #{int(r['ecg_rank']):02d} {name}-{r['ticker']}  "
            f"ECG {r['ecg_score']:.1f}  conf={flag}  "
            f"RS {r['rs_rank']:.1f}  Fund {r['fund_score']:.1f}  "
            f"E1={_fmt(r['e1_rs_band'])} E2={_fmt(r['e2_52w_prox'])} "
            f"E3={_fmt(r['e3_accel_early'])} E4={_fmt(r['e4_sma200_turn'])}"
        )
    # copy string: confirmed + ECG rank order
    conf = table[table["confirmed"]].sort_values("ecg_score", ascending=False)
    line = ",".join(conf["ticker"].astype(str).tolist())
    print(
        f"\n================================================================\n"
        f"  [ECG] Confirmed 복사용 전체 문자열 — {len(conf)}종 (ECG 점수 내림차순)\n"
        f"================================================================\n"
        f"{line}\n"
        f"================================================================\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ECG early-confirmed growth lens (D34 A1)")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument(
        "--from-fundamental",
        default=None,
        help="fundamental_YYYYMMDD.csv (default: latest in report_dir)",
    )
    parser.add_argument("--as-of", default=None, help="YYYY-MM-DD price cutoff")
    parser.add_argument("--no-price", action="store_true", help="skip cache enrich (E2/E4 NaN)")
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    params = load_params(args.config)
    report_dir = Path(params.report_dir)
    fund_path = Path(args.from_fundamental) if args.from_fundamental else latest_fundamental_csv(report_dir)
    if fund_path is None or not fund_path.exists():
        print("fundamental CSV not found — run !sepa.fund / !go first")
        return 1

    as_of = args.as_of
    if as_of is None:
        stamp = stamp_from_fundamental_path(fund_path)
        if len(stamp) == 8 and stamp.isdigit():
            as_of = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"

    table, out = run_ecg(
        fund_path=fund_path,
        cache_dir=params.data.cache_dir,
        report_dir=report_dir,
        as_of=as_of,
        lookback_years=int(params.data.lookback_years),
        enrich_prices=not args.no_price,
    )
    print_ecg_summary(table, top_n=args.top)
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
