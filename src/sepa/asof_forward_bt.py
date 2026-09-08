"""As-of sepaTop forward backtest (month-end grid, current cache).

For each eligible as-of date:
  1) Stage2 + Fund + soft ceiling with data ≤ as_of
  2) sepaTop = filtered fund pool
  3) Forward returns from as_of for 1M / 3M / 6M / 1Y vs SPX / QQQ

Usage:
  python -m sepa.asof_forward_bt
  python -m sepa.asof_forward_bt --freq month --horizon 1y --skip-existing
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd
import yfinance as yf

from sepa.analyze import enrich_with_sectors
from sepa.candidates import apply_candidate_filters
from sepa.config import load_params
from sepa.fonts import savefig_korean, setup_korean_matplotlib
from sepa.gap_fill import rebuild_day_asof
from sepa.sepatop import load_price_panel, save_membership, sepatop_dirs

logger = logging.getLogger(__name__)

PERIODS: list[tuple[str, pd.DateOffset]] = [
    ("1M", pd.DateOffset(months=1)),
    ("3M", pd.DateOffset(months=3)),
    ("6M", pd.DateOffset(months=6)),
    ("1Y", pd.DateOffset(years=1)),
]

HORIZON_TD = {"1m": 21, "3m": 63, "6m": 126, "1y": 252}


def _load_calendar(cache_dir: Path) -> pd.DatetimeIndex:
    best: pd.DatetimeIndex | None = None
    for path in cache_dir.glob("*.parquet"):
        df = pd.read_parquet(path)
        if not isinstance(df.index, pd.DatetimeIndex):
            if "date" in df.columns:
                df = df.set_index(pd.to_datetime(df["date"]))
            else:
                continue
        ix = pd.to_datetime(df.index).tz_localize(None).sort_values()
        if best is None or len(ix) > len(best):
            best = ix
    if best is None or best.empty:
        raise RuntimeError(f"no price calendar in {cache_dir}")
    return pd.DatetimeIndex(best)


def _load_index_metas(cache_dir: Path) -> list[pd.DatetimeIndex]:
    metas: list[pd.DatetimeIndex] = []
    for path in cache_dir.glob("*.parquet"):
        try:
            df = pd.read_parquet(path)
            if not isinstance(df.index, pd.DatetimeIndex):
                if "date" in df.columns:
                    df = df.set_index(pd.to_datetime(df["date"]))
                else:
                    continue
            ix = pd.to_datetime(df.index).tz_localize(None).sort_values()
            metas.append(pd.DatetimeIndex(ix))
        except Exception:  # noqa: BLE001
            continue
    return metas


def _eligible_count(metas: list[pd.DatetimeIndex], as_of: pd.Timestamp, min_hist: int) -> int:
    return sum(1 for ix in metas if int(ix.searchsorted(as_of, side="right")) >= min_hist)


def _td_after(cal: pd.DatetimeIndex, as_of: pd.Timestamp) -> int:
    i = int(cal.searchsorted(as_of, side="right")) - 1
    if i < 0:
        return 0
    return int(len(cal) - i - 1)


def month_end_asofs(cal: pd.DatetimeIndex) -> list[pd.Timestamp]:
    s = pd.Series(1, index=cal)
    vals = s.groupby([cal.year, cal.month]).apply(lambda x: x.index.max()).values
    return [pd.Timestamp(x) for x in vals]


def friday_asofs(cal: pd.DatetimeIndex) -> list[pd.Timestamp]:
    return [pd.Timestamp(x) for x in cal[cal.dayofweek == 4]]


def select_asofs(
    cal: pd.DatetimeIndex,
    cache_dir: Path,
    *,
    freq: str,
    horizon: str,
    min_hist: int,
    elig_frac: float = 0.5,
) -> list[pd.Timestamp]:
    need = HORIZON_TD[horizon]
    dates = month_end_asofs(cal) if freq == "month" else friday_asofs(cal)
    metas = _load_index_metas(cache_dir)
    thresh = int(elig_frac * len(metas))
    out: list[pd.Timestamp] = []
    for d in dates:
        if _td_after(cal, d) < need:
            continue
        if _eligible_count(metas, d, min_hist) < thresh:
            continue
        out.append(d)
    return out


def px_on_or_before(s: pd.Series, dt: pd.Timestamp) -> float | None:
    s = s.dropna()
    if s.empty:
        return None
    s = s.loc[:dt]
    return float(s.iloc[-1]) if not s.empty else None


def load_benches(start: pd.Timestamp, end: pd.Timestamp) -> dict[str, pd.Series]:
    syms = {"SPX": "^GSPC", "QQQ": "QQQ"}
    raw = yf.download(
        list(syms.values()),
        start=(start - pd.Timedelta(days=7)).date().isoformat(),
        end=(end + pd.Timedelta(days=7)).date().isoformat(),
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )

    def one(name: str) -> pd.Series:
        yf_sym = syms[name]
        if isinstance(raw.columns, pd.MultiIndex):
            lvl0 = raw.columns.get_level_values(0)
            if yf_sym in lvl0:
                sub = raw[yf_sym]
                s = sub["Close"] if "Close" in sub.columns else sub.iloc[:, 0]
            else:
                s = raw["Close"][yf_sym]
        else:
            s = raw["Close"]
        return (
            pd.Series(s.astype(float).values, index=pd.to_datetime(s.index).tz_localize(None))
            .dropna()
            .sort_index()
        )

    return {k: one(k) for k in syms}


def series_ret(s: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> float | None:
    p0 = px_on_or_before(s, start)
    p1 = px_on_or_before(s, end)
    if p0 is None or p1 is None or p0 <= 0:
        return None
    return float(p1 / p0 - 1.0)


def ensure_asof_fundamental(
    as_of: str,
    *,
    config: str,
    report_dir: Path,
    skip_existing: bool,
) -> Path | None:
    stamp = as_of.replace("-", "")
    fund_path = report_dir / f"fundamental_{stamp}.csv"
    stage2_path = report_dir / f"stage2_{stamp}.csv"
    if skip_existing and fund_path.exists() and stage2_path.exists():
        logger.info("reuse existing %s", fund_path.name)
        return fund_path
    ok = rebuild_day_asof(as_of, config=config, report_dir=report_dir)
    if not ok or not fund_path.exists():
        return None
    return fund_path


def constituents_from_fund(fund_path: Path, cache_dir: Path, as_of: str) -> pd.DataFrame:
    fund = pd.read_csv(fund_path)
    if "market_cap" not in fund.columns or pd.to_numeric(
        fund.get("market_cap"), errors="coerce"
    ).isna().all():
        fund = enrich_with_sectors(fund, cache_dir, refresh=False)
    fund, _ = apply_candidate_filters(fund)
    reports_st, _ = sepatop_dirs(fund_path.parent, cache_dir)
    save_membership(reports_st / f"membership_{as_of.replace('-', '')}.csv", fund, as_of)
    return fund


def evaluate_asof(
    as_of: pd.Timestamp,
    constituents: pd.DataFrame,
    panel: pd.DataFrame,
    benches: dict[str, pd.Series],
) -> list[dict]:
    rows: list[dict] = []
    tickers = constituents["ticker"].astype(str).str.upper().tolist()
    for label, offset in PERIODS:
        end = as_of + offset
        rets: list[float] = []
        for t in tickers:
            if t not in panel.columns:
                continue
            p0 = px_on_or_before(panel[t], as_of)
            p1 = px_on_or_before(panel[t], end)
            if p0 is None or p1 is None or p0 <= 0:
                continue
            rets.append(p1 / p0 - 1.0)
        vals = np.array(rets, dtype=float)
        spx = series_ret(benches["SPX"], as_of, end)
        qqq = series_ret(benches["QQQ"], as_of, end)
        if len(vals) == 0:
            continue
        med = float(np.median(vals))
        mean = float(np.mean(vals))
        rows.append(
            {
                "as_of": as_of.date().isoformat(),
                "period": label,
                "end": end.date().isoformat(),
                "n": int(len(vals)),
                "median": med,
                "mean_ew": mean,
                "spx": spx,
                "qqq": qqq,
                "excess_med_spx": med - spx if spx is not None else None,
                "excess_ew_spx": mean - spx if spx is not None else None,
                "excess_med_qqq": med - qqq if qqq is not None else None,
                "excess_ew_qqq": mean - qqq if qqq is not None else None,
                "pct_pos": float((vals > 0).mean()),
                "pct_beat_spx": float((vals > spx).mean()) if spx is not None else None,
                "pct_beat_qqq": float((vals > qqq).mean()) if qqq is not None else None,
                "p10": float(np.percentile(vals, 10)),
                "p90": float(np.percentile(vals, 90)),
            }
        )
    return rows


def plot_aggregate(summary: pd.DataFrame, out_path: Path) -> None:
    setup_korean_matplotlib(allow_install=True)
    periods = [p for p, _ in PERIODS]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    fig.suptitle(
        "As-of sepaTop 전방 백테스트 (월말 격자 · 현재 캐시)\n"
        "등가/중앙값 vs SPX·QQQ · 룩어헤드 멤버십 제거 · 생존편향 잔존",
        fontsize=13,
    )
    for ax, period in zip(axes.ravel(), periods):
        sub = summary[summary["period"] == period].sort_values("as_of")
        x = np.arange(len(sub))
        w = 0.2
        ax.bar(x - 1.5 * w, sub["mean_ew"] * 100, w, label="등가", color="#1e8449")
        ax.bar(x - 0.5 * w, sub["median"] * 100, w, label="중앙값", color="#27ae60")
        ax.bar(x + 0.5 * w, sub["spx"] * 100, w, label="SPX", color="#2980b9")
        ax.bar(x + 1.5 * w, sub["qqq"] * 100, w, label="QQQ", color="#8e44ad")
        ax.axhline(0, color="black", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([a[2:] for a in sub["as_of"]], rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("전방 수익률 (%)")
        ew_ex = (sub["mean_ew"] - sub["spx"]).mean() * 100
        md_ex = (sub["median"] - sub["spx"]).mean() * 100
        beat = (sub["mean_ew"] > sub["spx"]).mean() * 100
        ax.set_title(
            f"{period}  ·  as-of {len(sub)}회  ·  "
            f"등가−SPX 평균 {ew_ex:+.1f}%p  ·  중앙−SPX 평균 {md_ex:+.1f}%p  ·  "
            f"등가>SPX {beat:.0f}%",
            fontsize=9,
        )
        ax.grid(axis="y", alpha=0.3)
        ax.legend(fontsize=8, loc="upper left")
    savefig_korean(fig, out_path, dpi=140)
    plt.close(fig)


def plot_hit_rates(summary: pd.DataFrame, out_path: Path) -> None:
    setup_korean_matplotlib(allow_install=True)
    periods = [p for p, _ in PERIODS]
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    x = np.arange(len(periods))
    w = 0.25
    ew_spx = [
        (summary[summary.period == p]["mean_ew"] > summary[summary.period == p]["spx"]).mean() * 100
        for p in periods
    ]
    med_spx = [
        (summary[summary.period == p]["median"] > summary[summary.period == p]["spx"]).mean() * 100
        for p in periods
    ]
    ew_qqq = [
        (summary[summary.period == p]["mean_ew"] > summary[summary.period == p]["qqq"]).mean() * 100
        for p in periods
    ]
    ax.bar(x - w, ew_spx, w, label="등가 > SPX", color="#1e8449")
    ax.bar(x, med_spx, w, label="중앙값 > SPX", color="#27ae60")
    ax.bar(x + w, ew_qqq, w, label="등가 > QQQ", color="#8e44ad")
    ax.axhline(50, color="gray", ls="--", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(periods)
    ax.set_ylim(0, 100)
    ax.set_ylabel("as-of 중 비율 (%)")
    ax.set_title("전방 구간별 벤치 상회 빈도 (as-of 단위)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    savefig_korean(fig, out_path, dpi=140)
    plt.close(fig)


def run(
    *,
    config: str = "config/params.yaml",
    freq: str = "month",
    horizon: str = "1y",
    skip_existing: bool = True,
    include_extra: list[str] | None = None,
) -> pd.DataFrame:
    params = load_params(config)
    report_dir = Path(params.report_dir)
    cache_dir = Path(params.data.cache_dir)
    out_dir = report_dir / "asof_forward_bt"
    out_dir.mkdir(parents=True, exist_ok=True)

    cal = _load_calendar(cache_dir)
    asofs = select_asofs(
        cal,
        cache_dir,
        freq=freq,
        horizon=horizon,
        min_hist=int(params.data.min_history_days),
    )
    extras = [pd.Timestamp(x) for x in (include_extra or [])]
    for e in extras:
        if e not in asofs and _td_after(cal, e) >= HORIZON_TD[horizon] - 1:
            asofs.append(e)
    asofs = sorted(set(asofs))
    print(f"as-of grid ({freq}, horizon≥{horizon}): {len(asofs)} dates")
    for d in asofs:
        print(f"  - {d.date()}")

    benches = load_benches(asofs[0], cal.max())
    all_rows: list[dict] = []
    member_counts: list[tuple[str, int]] = []

    for i, as_of in enumerate(asofs, 1):
        iso = as_of.date().isoformat()
        print(f"\n======== [{i}/{len(asofs)}] as-of {iso} ========")
        fund_path = ensure_asof_fundamental(
            iso,
            config=config,
            report_dir=report_dir,
            skip_existing=skip_existing,
        )
        if fund_path is None:
            logger.error("failed fundamental for %s", iso)
            continue
        cons = constituents_from_fund(fund_path, cache_dir, iso)
        member_counts.append((iso, len(cons)))
        print(f"sepaTop n={len(cons)}")
        panel = load_price_panel(
            cons["ticker"].astype(str).str.upper().tolist(),
            cache_dir,
            lookback_years=max(3, int(params.data.lookback_years)),
        )
        rows = evaluate_asof(as_of, cons, panel, benches)
        all_rows.extend(rows)
        # per-asof snapshot
        pd.DataFrame(rows).to_csv(out_dir / f"forward_{as_of.strftime('%Y%m%d')}.csv", index=False)

    summary = pd.DataFrame(all_rows)
    if summary.empty:
        raise RuntimeError("no backtest rows produced")
    summary_path = out_dir / "forward_summary.csv"
    summary.to_csv(summary_path, index=False)
    pd.DataFrame(member_counts, columns=["as_of", "n_members"]).to_csv(
        out_dir / "membership_counts.csv", index=False
    )

    chart1 = out_dir / "asof_forward_bt_bars.png"
    chart2 = out_dir / "asof_forward_bt_hitrate.png"
    plot_aggregate(summary, chart1)
    plot_hit_rates(summary, chart2)

    # rollup table
    roll = []
    for period, _ in PERIODS:
        sub = summary[summary["period"] == period]
        roll.append(
            {
                "period": period,
                "n_asof": len(sub),
                "mean_ew_avg": sub["mean_ew"].mean(),
                "median_avg": sub["median"].mean(),
                "spx_avg": sub["spx"].mean(),
                "qqq_avg": sub["qqq"].mean(),
                "excess_ew_spx_avg": sub["excess_ew_spx"].mean(),
                "excess_med_spx_avg": sub["excess_med_spx"].mean(),
                "excess_ew_qqq_avg": sub["excess_ew_qqq"].mean(),
                "pct_asof_ew_gt_spx": (sub["mean_ew"] > sub["spx"]).mean(),
                "pct_asof_med_gt_spx": (sub["median"] > sub["spx"]).mean(),
                "pct_asof_ew_gt_qqq": (sub["mean_ew"] > sub["qqq"]).mean(),
                "pct_asof_med_gt_qqq": (sub["median"] > sub["qqq"]).mean(),
            }
        )
    roll_df = pd.DataFrame(roll)
    roll_df.to_csv(out_dir / "forward_rollup.csv", index=False)
    print("\n=== ROLLUP ===")
    print(roll_df.to_string(index=False))
    print(f"\nsummary: {summary_path}")
    print(f"charts:  {chart1}")
    print(f"         {chart2}")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="As-of sepaTop forward backtest")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--freq", choices=["month", "week"], default="month")
    parser.add_argument("--horizon", choices=["1m", "3m", "6m", "1y"], default="1y")
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="rebuild stage2/fund even if CSV exists",
    )
    parser.add_argument(
        "--include",
        default="",
        help="comma-separated extra as-of dates YYYY-MM-DD",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    extras = [x.strip() for x in args.include.split(",") if x.strip()]
    run(
        config=args.config,
        freq=args.freq,
        horizon=args.horizon,
        skip_existing=not args.no_skip_existing,
        include_extra=extras,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
