"""Fund score bucket trend chart for ``!sepa.anal`` / ``!sepa.go``.

Equal-weight, half-open 10-point Fund buckets vs S&P500 over ~1y closes,
rebased to 1000 at a common base date (same pattern as sepaTop / SPX).
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd

from sepa.artifacts import publish
from sepa.fonts import korean_fontproperties, savefig_korean, setup_korean_matplotlib
from sepa.model_metrics import _ensure_benchmark
from sepa.sepatop import BASE_LEVEL, load_price_panel, rebase_to

logger = logging.getLogger(__name__)

# Half-open [0,10), [10,20), …, [80,90), last [90,100] (includes 100)
BUCKET_EDGES = list(range(0, 100, 10)) + [100]
BUCKET_LABELS = [f"{lo}-{hi}" for lo, hi in zip(BUCKET_EDGES[:-1], BUCKET_EDGES[1:])]

LOOKBACK_DAYS = 252  # ~1 trading year
MIN_BUCKET_N = 1  # draw line if at least one ticker; legend shows n
MIN_COVERAGE = 0.5  # fraction of bucket members with a price that day


def fund_bucket_label(score: float) -> str | None:
    """Map Fund score to half-open 10-pt label; ``100`` → ``90-100``."""
    if score is None or score != score:
        return None
    s = float(score)
    if s < 0:
        return None
    if s >= 100:
        return "90-100"
    lo = int(s // 10) * 10
    if lo >= 90:
        return "90-100"
    return f"{lo}-{lo + 10}"


def assign_fund_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """Return copy with ``fund_bucket`` column (ordered categorical)."""
    out = df.copy()
    if "fund_score" not in out.columns:
        out["fund_bucket"] = pd.Categorical([], categories=BUCKET_LABELS)
        return out
    scores = pd.to_numeric(out["fund_score"], errors="coerce")
    out["fund_bucket"] = scores.map(fund_bucket_label)
    out["fund_bucket"] = pd.Categorical(out["fund_bucket"], categories=BUCKET_LABELS, ordered=True)
    if "ticker" in out.columns:
        out["ticker"] = out["ticker"].astype(str).str.upper()
    return out


def equal_weight_rebased_index(
    panel: pd.DataFrame,
    tickers: list[str],
    *,
    base_date: pd.Timestamp | None = None,
    base_level: float = BASE_LEVEL,
    min_coverage: float = MIN_COVERAGE,
) -> pd.Series:
    """Equal-weight index of closes, rebased to ``base_level`` at ``base_date``.

    Each name uses ``rebase_to`` (same helper as S&P500 in sepaTop), then the
    cross-sectional mean is taken each day among names with a valid level.
    """
    cols = [t for t in tickers if t in panel.columns]
    if not cols:
        return pd.Series(dtype=float)
    sub = panel[cols].sort_index().copy().dropna(how="all")
    if sub.empty:
        return pd.Series(dtype=float)

    if base_date is None:
        base_date = sub.index[0]

    rebased = pd.DataFrame(index=sub.index)
    for c in cols:
        s = sub[c].astype(float).dropna()
        if s.empty:
            continue
        rebased[c] = rebase_to(s, base_level, base_date)

    if rebased.empty or rebased.isna().all().all():
        return pd.Series(dtype=float)

    n = len(rebased.columns)
    coverage = rebased.notna().sum(axis=1) / max(n, 1)
    mean = rebased.mean(axis=1, skipna=True)
    mean = mean.loc[coverage >= min_coverage]
    # Drop leading NaNs before any member had a base price
    mean = mean.dropna()
    mean.name = "eq_index"
    return mean


def build_bucket_trends(
    fund_df: pd.DataFrame,
    *,
    cache_dir: str | Path,
    lookback_days: int = LOOKBACK_DAYS,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Build equal-weight rebased series per Fund bucket + S&P500.

    Returns ``(wide DataFrame of levels, bucket_counts)``.
    """
    tagged = assign_fund_buckets(fund_df)
    if tagged.empty or "ticker" not in tagged.columns:
        return pd.DataFrame(), {}

    counts: dict[str, int] = {}
    members: dict[str, list[str]] = {}
    for label in BUCKET_LABELS:
        tickers = (
            tagged.loc[tagged["fund_bucket"] == label, "ticker"]
            .astype(str)
            .str.upper()
            .dropna()
            .unique()
            .tolist()
        )
        counts[label] = len(tickers)
        members[label] = tickers

    all_tickers = sorted({t for ts in members.values() for t in ts})
    if not all_tickers:
        return pd.DataFrame(), counts

    panel = load_price_panel(all_tickers, cache_dir, lookback_years=2)
    if panel.empty:
        return pd.DataFrame(), counts
    if len(panel) > lookback_days:
        panel = panel.iloc[-lookback_days:]

    base_date = panel.index[0]
    series_map: dict[str, pd.Series] = {}
    for label in BUCKET_LABELS:
        tickers = members[label]
        if len(tickers) < MIN_BUCKET_N:
            continue
        idx = equal_weight_rebased_index(panel, tickers, base_date=base_date)
        if not idx.empty:
            series_map[label] = idx

    bench = _ensure_benchmark(cache_dir, "^GSPC")
    if bench.empty:
        bench = _ensure_benchmark(cache_dir, "SPY")
    if not bench.empty:
        bench = bench.loc[(bench.index >= base_date) & (bench.index <= panel.index[-1])]
        if not bench.empty:
            series_map["S&P500"] = rebase_to(bench, BASE_LEVEL, base_date)

    if not series_map:
        return pd.DataFrame(), counts

    combined = pd.DataFrame(series_map).sort_index()
    combined = combined.ffill(limit=3)
    return combined, counts


def plot_fund_score_trend(
    combined: pd.DataFrame,
    counts: dict[str, int],
    out_path: Path,
    *,
    stamp: str,
) -> Path | None:
    """Multi-line chart: Fund buckets + S&P500, base=1000."""
    if combined.empty:
        return None
    setup_korean_matplotlib(allow_install=True)
    import matplotlib.dates as mdates

    fig, ax = plt.subplots(figsize=(12, 7.0))

    # Distinct colors for buckets; SPX thick dark
    cmap = plt.get_cmap("tab10")
    bucket_cols = [c for c in BUCKET_LABELS if c in combined.columns]
    for i, label in enumerate(bucket_cols):
        n = counts.get(label, 0)
        ax.plot(
            combined.index,
            combined[label],
            color=cmap(i % 10),
            lw=1.8,
            alpha=0.9,
            label=f"Fund {label} (n={n})",
        )
    if "S&P500" in combined.columns:
        ax.plot(
            combined.index,
            combined["S&P500"],
            color="#1a1a1a",
            lw=2.8,
            alpha=0.95,
            label="S&P500",
            zorder=5,
        )

    start = pd.Timestamp(combined.index[0]).strftime("%Y-%m-%d")
    end = pd.Timestamp(combined.index[-1]).strftime("%Y-%m-%d")
    n_days = len(combined)
    empty = [lab for lab in BUCKET_LABELS if counts.get(lab, 0) == 0]
    empty_note = (
        f"비어 있음: {', '.join(empty)}" if empty else "전 구간 종목 있음"
    )
    count_line = " · ".join(f"{lab}={counts.get(lab, 0)}" for lab in BUCKET_LABELS)

    ax.axhline(BASE_LEVEL, color="#888", lw=0.8, ls="--", alpha=0.7)
    ax.set_ylabel(f"지수 수준 (기준일={BASE_LEVEL:.0f})", fontproperties=korean_fontproperties(size=10))
    ax.set_title(
        f"Fund 점수 구간별 최근 1년 종가 추세 (등가 · vs S&P500) — {stamp}",
        fontproperties=korean_fontproperties(bold=True, size=13),
    )
    ax.text(
        0.5, 1.02,
        f"기간 {start} ~ {end}  ({n_days} 거래일)  |  {empty_note}",
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontproperties=korean_fontproperties(size=9),
        color="#444",
    )
    ax.text(
        0.0, -0.14,
        f"구간 n: {count_line}",
        transform=ax.transAxes,
        ha="left", va="top",
        fontproperties=korean_fontproperties(size=8),
        color="#555",
    )
    ax.set_xlim(combined.index[0], combined.index[-1])
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(True, alpha=0.3)
    ax.legend(
        loc="upper left",
        fontsize=8,
        frameon=True,
        fancybox=False,
        framealpha=0.9,
        prop=korean_fontproperties(size=8),
        ncol=2,
    )
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(korean_fontproperties(size=8))
    fig.autofmt_xdate(rotation=30, ha="right")
    fig.tight_layout(rect=(0, 0.06, 1, 0.96))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    savefig_korean(fig, out_path, dpi=140)
    plt.close(fig)
    return out_path


def run_fund_score_trend(
    fund_df: pd.DataFrame,
    *,
    chart_dir: str | Path,
    stamp: str,
    cache_dir: str | Path,
    report_dir: str | Path | None = None,
    lookback_days: int = LOOKBACK_DAYS,
) -> dict:
    """Compute + plot Fund bucket 1y trends; return paths and meta."""
    chart_dir = Path(chart_dir)
    chart_dir.mkdir(parents=True, exist_ok=True)
    combined, counts = build_bucket_trends(
        fund_df, cache_dir=cache_dir, lookback_days=lookback_days
    )
    nonempty = {k: v for k, v in counts.items() if v > 0}
    empty = [k for k, v in counts.items() if v == 0]
    print(f"  fund-trend buckets with names: {nonempty or '{}'}")
    if empty:
        print(f"  fund-trend empty buckets: {empty}")
    if not combined.empty:
        print(
            f"  fund-trend span: {combined.index[0].date()} → {combined.index[-1].date()} "
            f"({len(combined)} trading days)"
        )

    chart = plot_fund_score_trend(
        combined,
        counts,
        chart_dir / f"analyze_fund_trend_{stamp}.png",
        stamp=stamp,
    )
    csv_path: Path | None = None
    if not combined.empty:
        out_csv_dir = Path(report_dir) if report_dir else chart_dir.parent
        out_csv_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_csv_dir / f"fund_score_trend_{stamp}.csv"
        combined.to_csv(csv_path)
        publish(csv_path)

    if chart:
        publish(chart)
        print(f"  fund-trend chart: {chart}")
    else:
        print("  fund-trend chart: skipped (insufficient price data)")

    return {
        "ok": chart is not None,
        "chart": chart,
        "csv": csv_path,
        "counts": counts,
        "combined": combined,
    }
