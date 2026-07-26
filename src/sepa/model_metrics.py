"""Model-metric visualizations for SEPA analyze PDF (charts 1–7).

1. Fund factor decomposition (S/B/D/E stacked) — top N
2. Factor score distributions (4 panels)
3. RS vs factors scatter matrix
4. Rank stability / turnover (vs prior fund CSVs)
5. sepaTop contribution attribution (stock / sector)
6. Fund quantile forward returns (vs NASDAQ)
7. Data coverage panel
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
import glob
import numpy as np
import pandas as pd

from sepa.artifacts import publish_many

logger = logging.getLogger(__name__)

FACTOR_COLS = [
    ("s_surprise", "S Surprise", "#2E86AB"),
    ("b_eps_dyoy", "B EPS ΔYoY", "#A23B72"),
    ("d_sales_dyoy", "D Sales ΔYoY", "#F18F01"),
    ("e_opm_delta", "E OPM Δ", "#C73E1D"),
]

HORIZONS = (1, 5, 20)


def _setup_korean_font() -> None:
    for path in glob.glob("/usr/share/fonts/truetype/nanum/NanumGothic*.ttf"):
        fm.fontManager.addfont(path)
    if any(f.name == "NanumGothic" for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = "NanumGothic"
        plt.rcParams["axes.unicode_minus"] = False


def _stamp_from_fundamental_name(name: str) -> str | None:
    m = re.search(r"fundamental_(\d{8})", name)
    return m.group(1) if m else None


def list_fundamental_csvs(report_dir: str | Path) -> list[Path]:
    """Dated fund CSVs only (skip cmp_* etc.)."""
    out: list[Path] = []
    for p in sorted(Path(report_dir).glob("fundamental_*.csv")):
        if _stamp_from_fundamental_name(p.name):
            out.append(p)
    return out


def _spearman(a: pd.Series, b: pd.Series) -> float:
    """Spearman ρ without scipy (rank → Pearson)."""
    x = pd.to_numeric(a, errors="coerce")
    y = pd.to_numeric(b, errors="coerce")
    mask = x.notna() & y.notna()
    if mask.sum() < 3:
        return float("nan")
    rx = x[mask].rank()
    ry = y[mask].rank()
    return float(rx.corr(ry))


def _ensure_factor_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col, _, _ in FACTOR_COLS:
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    if "fund_score" in out.columns:
        out["fund_score"] = pd.to_numeric(out["fund_score"], errors="coerce")
    if "rs_rank" in out.columns:
        out["rs_rank"] = pd.to_numeric(out["rs_rank"], errors="coerce")
    if "ticker" in out.columns:
        out["ticker"] = out["ticker"].astype(str).str.upper()
    return out


def plot_factor_decomposition(
    df: pd.DataFrame,
    out_path: Path,
    *,
    top_n: int = 25,
) -> Path | None:
    """1. Stacked S/B/D/E contribution for top-N by fund_score."""
    _setup_korean_font()
    d = _ensure_factor_cols(df)
    if d.empty or "fund_score" not in d.columns:
        return None
    top = d.nlargest(top_n, "fund_score").iloc[::-1]  # bottom→top for barh
    if top.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, max(5.5, 0.28 * len(top) + 1.5)))
    left = np.zeros(len(top))
    y = np.arange(len(top))
    for col, label, color in FACTOR_COLS:
        vals = top[col].to_numpy(dtype=float)
        ax.barh(y, vals, left=left, color=color, label=label, height=0.72)
        left = left + vals
    ax.set_yticks(y)
    ax.set_yticklabels(top["ticker"].tolist(), fontsize=8)
    ax.set_xlabel("Factor contribution (points)")
    ax.set_title(f"1. Fund factor decomposition — top {len(top)} by fund_score")
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    ax.set_xlim(0, max(105, float(left.max()) * 1.05))
    ax.axvline(100, color="#999", ls="--", lw=0.8, alpha=0.7)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_factor_distributions(df: pd.DataFrame, out_path: Path) -> Path | None:
    """2. Four-panel histograms of factor scores."""
    _setup_korean_font()
    d = _ensure_factor_cols(df)
    if d.empty:
        return None
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.5))
    for ax, (col, label, color) in zip(axes.ravel(), FACTOR_COLS):
        vals = d[col].astype(float)
        ax.hist(vals, bins=20, color=color, edgecolor="white", alpha=0.9)
        ax.axvline(vals.mean(), color="#222", ls="--", lw=1, label=f"mean={vals.mean():.1f}")
        ax.set_title(label)
        ax.set_xlabel("score")
        ax.set_ylabel("count")
        ax.legend(fontsize=7, frameon=False)
    fig.suptitle("2. Factor score distributions", fontsize=13, fontweight="bold", y=1.01)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_rs_factor_scatter_matrix(df: pd.DataFrame, out_path: Path) -> Path | None:
    """3. RS rank vs each factor + vs fund_score."""
    _setup_korean_font()
    d = _ensure_factor_cols(df)
    if d.empty or "rs_rank" not in d.columns:
        return None
    panels = FACTOR_COLS + [("fund_score", "Fund score", "#1B1B1E")]
    fig, axes = plt.subplots(2, 3, figsize=(11, 7))
    axes_flat = list(axes.ravel())
    rs = d["rs_rank"].astype(float)
    for i, (col, label, color) in enumerate(panels):
        ax = axes_flat[i]
        y = d[col].astype(float)
        ax.scatter(rs, y, s=18, alpha=0.65, c=color, edgecolors="none")
        mask = rs.notna() & y.notna()
        if mask.sum() >= 5:
            rho = _spearman(rs[mask], y[mask])
            ax.set_title(f"{label}  ρ={rho:.2f}", fontsize=10)
        else:
            ax.set_title(label, fontsize=10)
        ax.set_xlabel("RS rank")
        ax.set_ylabel(label)
    # hide unused last axis if any
    for j in range(len(panels), len(axes_flat)):
        axes_flat[j].axis("off")
    fig.suptitle("3. RS vs factors scatter matrix", fontsize=13, fontweight="bold")
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def compute_rank_stability(
    report_dir: str | Path,
    *,
    current_stamp: str | None = None,
    top_n: int = 30,
) -> pd.DataFrame:
    """Per consecutive fund snapshot: Spearman ρ, top-N retention, turnover."""
    paths = list_fundamental_csvs(report_dir)
    if current_stamp:
        paths = [p for p in paths if (_stamp_from_fundamental_name(p.name) or "") <= current_stamp]
    rows = []
    for prev, curr in zip(paths, paths[1:]):
        ps = _stamp_from_fundamental_name(prev.name)
        cs = _stamp_from_fundamental_name(curr.name)
        if not ps or not cs:
            continue
        try:
            a = pd.read_csv(prev)
            b = pd.read_csv(curr)
        except Exception as exc:  # noqa: BLE001
            logger.warning("rank stability skip %s→%s: %s", prev.name, curr.name, exc)
            continue
        if "ticker" not in a.columns or "fund_score" not in a.columns:
            continue
        if "ticker" not in b.columns or "fund_score" not in b.columns:
            continue
        a = a[["ticker", "fund_score"]].copy()
        b = b[["ticker", "fund_score"]].copy()
        a["ticker"] = a["ticker"].astype(str).str.upper()
        b["ticker"] = b["ticker"].astype(str).str.upper()
        a["fund_score"] = pd.to_numeric(a["fund_score"], errors="coerce")
        b["fund_score"] = pd.to_numeric(b["fund_score"], errors="coerce")
        merged = a.merge(b, on="ticker", suffixes=("_prev", "_curr"))
        rho = (
            _spearman(merged["fund_score_prev"], merged["fund_score_curr"])
            if len(merged) >= 5
            else np.nan
        )
        top_a = set(a.nlargest(top_n, "fund_score")["ticker"])
        top_b = set(b.nlargest(top_n, "fund_score")["ticker"])
        retention = len(top_a & top_b) / top_n if top_n else np.nan
        union = top_a | top_b
        turnover = 1.0 - (len(top_a & top_b) / len(union)) if union else np.nan
        set_a = set(a["ticker"])
        set_b = set(b["ticker"])
        univ_jaccard = len(set_a & set_b) / len(set_a | set_b) if (set_a | set_b) else np.nan
        rows.append(
            {
                "from": ps,
                "to": cs,
                "label": f"{ps[4:6]}/{ps[6:8]}→{cs[4:6]}/{cs[6:8]}",
                "spearman": rho,
                "top_n_retention": retention,
                "top_n_turnover": turnover,
                "universe_jaccard": univ_jaccard,
                "n_overlap": len(merged),
            }
        )
    return pd.DataFrame(rows)


def plot_rank_stability(
    report_dir: str | Path,
    out_path: Path,
    *,
    current_stamp: str | None = None,
    top_n: int = 30,
) -> Path | None:
    """4. Rank stability / turnover across fund snapshots."""
    _setup_korean_font()
    stats = compute_rank_stability(report_dir, current_stamp=current_stamp, top_n=top_n)
    if stats.empty:
        return None

    fig, axes = plt.subplots(2, 1, figsize=(10, 7.5), sharex=True)
    x = np.arange(len(stats))
    axes[0].plot(x, stats["spearman"], "o-", color="#2E86AB", label="Spearman ρ (overlap)")
    axes[0].plot(
        x, stats["universe_jaccard"], "s--", color="#888", label="Universe Jaccard", alpha=0.85
    )
    axes[0].set_ylabel("correlation / overlap")
    axes[0].set_ylim(-0.05, 1.05)
    axes[0].set_title(f"4. Rank stability / turnover (top {top_n})")
    axes[0].legend(fontsize=8, frameon=False, loc="lower left")
    axes[0].axhline(0.8, color="#ccc", ls=":", lw=0.8)

    axes[1].bar(x - 0.18, stats["top_n_retention"], width=0.36, color="#2A9D8F", label="Top-N retention")
    axes[1].bar(x + 0.18, stats["top_n_turnover"], width=0.36, color="#E76F51", label="Top-N turnover")
    axes[1].set_ylabel("fraction")
    axes[1].set_ylim(0, 1.05)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(stats["label"].tolist(), rotation=30, ha="right", fontsize=8)
    axes[1].legend(fontsize=8, frameon=False, loc="upper right")
    axes[1].set_xlabel("snapshot transition")
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def _ensure_benchmark(cache_dir: str | Path, symbol: str = "QQQ") -> pd.Series:
    """Load benchmark closes; fetch once into cache if missing."""
    series = _load_close_series(symbol, cache_dir)
    if not series.empty:
        return series
    # try NASDAQ composite under yfinance symbol
    alt = "^IXIC" if symbol.upper() != "^IXIC" else "QQQ"
    series = _load_close_series(alt, cache_dir)
    if not series.empty:
        return series
    try:
        import yfinance as yf

        for sym in (symbol, "QQQ", "^IXIC"):
            raw = yf.download(sym, period="2y", auto_adjust=True, progress=False)
            if raw is None or raw.empty:
                continue
            if isinstance(raw.columns, pd.MultiIndex):
                close = raw["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
            elif "Close" in raw.columns:
                close = raw["Close"]
            else:
                close = raw.iloc[:, 0]
            s = pd.Series(close.astype(float).to_numpy(), index=pd.to_datetime(close.index))
            s = s.dropna()
            s.index = pd.to_datetime(s.index).tz_localize(None)
            s = s.sort_index()
            if s.empty:
                continue
            fname = sym.replace("^", "") + ".parquet"
            out = Path(cache_dir) / fname
            out.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame({"close": s}).to_parquet(out)
            return s
    except Exception as exc:  # noqa: BLE001
        logger.warning("benchmark fetch failed: %s", exc)
    return pd.Series(dtype=float)


def _load_close_series(
    ticker: str,
    cache_dir: str | Path,
    _cache: dict[str, pd.Series] | None = None,
) -> pd.Series:
    key = ticker.upper()
    if _cache is not None and key in _cache:
        return _cache[key]
    from sepa.data import store

    cache = Path(cache_dir)
    candidates = [cache / f"{key}.parquet"]
    if key.startswith("^"):
        candidates.append(cache / f"{key[1:]}.parquet")
    elif key in {"IXIC", "GSPC"}:
        candidates.append(cache / f"^{key}.parquet")

    series = pd.Series(dtype=float)
    df = None
    for path in candidates:
        if path.exists():
            try:
                df = pd.read_parquet(path)
                break
            except Exception:  # noqa: BLE001
                continue
    if df is None:
        try:
            df = store.get_history(key, cache_dir, lookback_years=2, update=False)
        except Exception:  # noqa: BLE001
            df = None
    if df is not None and not df.empty and "close" in df.columns:
        s = df["close"].astype(float).copy()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        series = s.sort_index()
    if _cache is not None:
        _cache[key] = series
    return series


def _period_return(series: pd.Series, as_of: pd.Timestamp, days: int) -> float | None:
    if series.empty:
        return None
    start_idx = series.index.searchsorted(as_of, side="left")
    if start_idx >= len(series):
        start_idx = len(series) - 1
    # prefer on/before as_of
    if start_idx > 0 and series.index[start_idx] > as_of:
        start_idx -= 1
    end_idx = start_idx + days
    if end_idx >= len(series):
        return None
    p0 = float(series.iloc[start_idx])
    p1 = float(series.iloc[end_idx])
    if p0 <= 0:
        return None
    return p1 / p0 - 1.0


def plot_sepatop_attribution(
    constituents: pd.DataFrame,
    out_path: Path,
    *,
    cache_dir: str | Path,
    as_of: str,
    lookback_days: int = 20,
    top_n: int = 15,
) -> Path | None:
    """5. Cap-weight × lookback return contribution by stock and sector."""
    _setup_korean_font()
    d = constituents.copy()
    if d.empty or "market_cap" not in d.columns:
        return None
    d["ticker"] = d["ticker"].astype(str).str.upper()
    d["market_cap"] = pd.to_numeric(d["market_cap"], errors="coerce")
    d = d.dropna(subset=["market_cap"])
    d = d[d["market_cap"] > 0]
    if d.empty:
        return None
    total_cap = float(d["market_cap"].sum())
    d["weight"] = d["market_cap"] / total_cap
    as_of_ts = pd.Timestamp(as_of)
    start_ts = as_of_ts - pd.Timedelta(days=int(lookback_days * 1.6))

    rets = []
    px_cache: dict[str, pd.Series] = {}
    for t in d["ticker"]:
        s = _load_close_series(t, cache_dir, px_cache)
        if s.empty:
            rets.append(np.nan)
            continue
        window = s.loc[(s.index >= start_ts) & (s.index <= as_of_ts)]
        if len(window) < 2:
            rets.append(np.nan)
            continue
        p0, p1 = float(window.iloc[0]), float(window.iloc[-1])
        rets.append(p1 / p0 - 1.0 if p0 > 0 else np.nan)
    d["ret"] = rets
    d["contrib"] = d["weight"] * d["ret"].fillna(0.0)

    sector_col = "primary_tag" if "primary_tag" in d.columns else (
        "sector" if "sector" in d.columns else None
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.5))

    top = d.nlargest(top_n, "contrib")
    bot = d.nsmallest(min(5, len(d)), "contrib")
    show = pd.concat([bot, top]).drop_duplicates("ticker").sort_values("contrib")
    colors = ["#E76F51" if v < 0 else "#2A9D8F" for v in show["contrib"]]
    axes[0].barh(show["ticker"], show["contrib"] * 100, color=colors)
    axes[0].axvline(0, color="#333", lw=0.8)
    axes[0].set_xlabel(f"contribution (pp of index, ~{lookback_days}d)")
    axes[0].set_title("Stock contribution")

    if sector_col:
        sec = (
            d.groupby(d[sector_col].fillna("기타").astype(str))["contrib"]
            .sum()
            .sort_values()
        )
        sc = ["#E76F51" if v < 0 else "#2E86AB" for v in sec]
        axes[1].barh(sec.index.astype(str), sec.values * 100, color=sc)
        axes[1].axvline(0, color="#333", lw=0.8)
        axes[1].set_xlabel("contribution (pp)")
        axes[1].set_title("Sector contribution")
    else:
        axes[1].text(0.5, 0.5, "no sector column", ha="center", va="center")
        axes[1].axis("off")

    fig.suptitle(
        f"5. sepaTop contribution attribution ({as_of}, lookback≈{lookback_days}d)",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def compute_quantile_forward_returns(
    report_dir: str | Path,
    cache_dir: str | Path,
    *,
    current_stamp: str | None = None,
    n_quantiles: int = 4,
    horizons: tuple[int, ...] = HORIZONS,
    benchmark: str = "^IXIC",
) -> pd.DataFrame:
    """Average forward returns by fund_score quantile across historical snapshots."""
    paths = list_fundamental_csvs(report_dir)
    if current_stamp:
        # need forward window after stamp → use snapshots strictly before last price
        paths = [p for p in paths if (_stamp_from_fundamental_name(p.name) or "") <= current_stamp]

    bench = _ensure_benchmark(cache_dir, benchmark)
    if bench.empty:
        bench = _ensure_benchmark(cache_dir, "QQQ")

    px_cache: dict[str, pd.Series] = {}
    if not bench.empty:
        px_cache[benchmark.upper()] = bench
        px_cache["QQQ"] = bench
        px_cache["^IXIC"] = bench
        px_cache["IXIC"] = bench
    rows = []
    for path in paths:
        stamp = _stamp_from_fundamental_name(path.name)
        if not stamp:
            continue
        as_of = pd.Timestamp(f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}")
        try:
            df = pd.read_csv(path)
        except Exception:  # noqa: BLE001
            continue
        if "ticker" not in df.columns or "fund_score" not in df.columns:
            continue
        df = df.copy()
        df["ticker"] = df["ticker"].astype(str).str.upper()
        df["fund_score"] = pd.to_numeric(df["fund_score"], errors="coerce")
        df = df.dropna(subset=["fund_score"])
        if len(df) < n_quantiles * 3:
            continue
        try:
            df["q"] = pd.qcut(df["fund_score"], n_quantiles, labels=False, duplicates="drop")
        except ValueError:
            continue

        for q, g in df.groupby("q"):
            for h in horizons:
                stock_rets = []
                for t in g["ticker"]:
                    r = _period_return(_load_close_series(t, cache_dir, px_cache), as_of, h)
                    if r is not None:
                        stock_rets.append(r)
                if len(stock_rets) < 3:
                    continue
                avg = float(np.mean(stock_rets))
                br = _period_return(bench, as_of, h)
                rows.append(
                    {
                        "stamp": stamp,
                        "quantile": int(q) + 1,
                        "horizon": h,
                        "avg_return": avg,
                        "bench_return": br,
                        "excess": avg - br if br is not None else np.nan,
                        "n": len(stock_rets),
                    }
                )
    return pd.DataFrame(rows)


def plot_quantile_forward_returns(
    report_dir: str | Path,
    cache_dir: str | Path,
    out_path: Path,
    *,
    current_stamp: str | None = None,
    n_quantiles: int = 4,
) -> Path | None:
    """6. Fund quantile forward returns vs NASDAQ."""
    _setup_korean_font()
    detail = compute_quantile_forward_returns(
        report_dir, cache_dir, current_stamp=current_stamp, n_quantiles=n_quantiles
    )
    if detail.empty:
        return None

    agg = (
        detail.groupby(["quantile", "horizon"], as_index=False)
        .agg(avg_return=("avg_return", "mean"), excess=("excess", "mean"), n_snaps=("stamp", "nunique"))
    )
    horizons = sorted(int(h) for h in agg["horizon"].unique())
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
    qs = sorted(agg["quantile"].unique())
    x = np.arange(len(qs))
    width = 0.8 / max(len(horizons), 1)
    for ax, metric, title, ylabel in [
        (axes[0], "avg_return", "Absolute forward return", "avg return"),
        (axes[1], "excess", "Excess vs NASDAQ/QQQ", "excess return"),
    ]:
        for i, h in enumerate(horizons):
            sub = agg[agg["horizon"] == h].set_index("quantile").reindex(qs)
            vals = sub[metric].fillna(0).to_numpy(dtype=float) * 100
            ax.bar(x + (i - (len(horizons) - 1) / 2) * width, vals, width=width, label=f"+{h}d")
        ax.set_xticks(x)
        ax.set_xticklabels([f"Q{q}" for q in qs])
        ax.axhline(0, color="#333", lw=0.8)
        ax.set_xlabel("fund_score quantile (Q4=highest)")
        ax.set_ylabel(ylabel + " (%)")
        ax.set_title(title)
        ax.legend(fontsize=8, frameon=False)
    n_snaps = int(detail["stamp"].nunique())
    fig.suptitle(
        f"6. Fund quantile forward returns ({n_snaps} snapshots)",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_data_coverage(df: pd.DataFrame, out_path: Path) -> Path | None:
    """7. Coverage: surprise, margin source, accel depth + quality (v2.1)."""
    _setup_korean_font()
    if df is None or df.empty:
        return None
    d = df.copy()
    n = len(d)

    surprise_present = 0
    if "eps_surprise_pct" in d.columns:
        surprise_present = int(pd.to_numeric(d["eps_surprise_pct"], errors="coerce").notna().sum())
    s_pos = 0
    if "s_surprise" in d.columns:
        s_pos = int((pd.to_numeric(d["s_surprise"], errors="coerce").fillna(0) > 0).sum())

    margin_counts = {"opm": 0, "npm": 0, "none": 0, "other": 0}
    if "margin_source" in d.columns:
        for v in d["margin_source"].fillna("none").astype(str).str.lower():
            if v in margin_counts:
                margin_counts[v] += 1
            else:
                margin_counts["other"] += 1
    else:
        margin_counts["none"] = n

    def _depth_share(col: str, min_n: int = 2) -> float:
        if col not in d.columns:
            return 0.0
        return float((pd.to_numeric(d[col], errors="coerce").fillna(0) >= min_n).mean())

    has_quality = all(c in d.columns for c in ("b_quality", "d_quality", "e_quality"))
    fig, axes = plt.subplots(2 if has_quality else 1, 3, figsize=(12, 8.2 if has_quality else 4.8))
    if not has_quality:
        axes = np.array([axes])

    row0 = axes[0]
    row0[0].bar(
        ["surprise\npresent", "S score\n> 0", "missing\nsurprise"],
        [
            100 * surprise_present / n,
            100 * s_pos / n,
            100 * (n - surprise_present) / n,
        ],
        color=["#2E86AB", "#2A9D8F", "#E76F51"],
    )
    row0[0].set_ylim(0, 105)
    row0[0].set_ylabel("% of universe")
    row0[0].set_title("EPS surprise coverage")
    for i, v in enumerate(
        [100 * surprise_present / n, 100 * s_pos / n, 100 * (n - surprise_present) / n]
    ):
        row0[0].text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=8)

    labels = list(margin_counts.keys())
    vals = [margin_counts[k] for k in labels]
    colors = ["#C73E1D", "#F18F01", "#999", "#666"]
    row0[1].bar(labels, [100 * v / n for v in vals], color=colors)
    row0[1].set_ylim(0, 105)
    row0[1].set_title("Margin source (E factor)")
    row0[1].set_ylabel("% of universe")
    for i, v in enumerate(vals):
        row0[1].text(i, 100 * v / n + 1.5, f"{v}", ha="center", fontsize=8)

    depth = {
        "EPS accel\nn≥2": 100 * _depth_share("eps_accel_n", 2),
        "Sales accel\nn≥2": 100 * _depth_share("sales_accel_n", 2),
        "Margin\nn≥2": 100 * _depth_share("margin_n", 2),
        "Any factor\n> 0": 100
        * float(
            (
                _ensure_factor_cols(d)[[c for c, _, _ in FACTOR_COLS]].sum(axis=1) > 0
            ).mean()
        ),
    }
    row0[2].bar(list(depth.keys()), list(depth.values()), color="#2E86AB")
    row0[2].set_ylim(0, 105)
    row0[2].set_title("Series depth / scored share")
    row0[2].set_ylabel("% of universe")
    for i, v in enumerate(depth.values()):
        row0[2].text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=8)

    if has_quality:
        row1 = axes[1]
        for ax, col, title, color in [
            (row1[0], "b_quality", "B quality (EPS accel gate)", "#A23B72"),
            (row1[1], "d_quality", "D quality (Sales accel gate)", "#F18F01"),
            (row1[2], "e_quality", "E quality (OPM/NPM)", "#C73E1D"),
        ]:
            s = pd.to_numeric(d[col], errors="coerce").fillna(0)
            buckets = {
                "0": float((s <= 0).mean() * 100),
                "partial": float(((s > 0) & (s < 1)).mean() * 100),
                "1.0": float((s >= 1).mean() * 100),
            }
            ax.bar(list(buckets.keys()), list(buckets.values()), color=color)
            ax.set_ylim(0, 105)
            ax.set_title(title)
            ax.set_ylabel("% of universe")
            for i, v in enumerate(buckets.values()):
                ax.text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=8)

    fig.suptitle(f"7. Data coverage panel (n={n})", fontsize=12, fontweight="bold")
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def run_model_metrics(
    df: pd.DataFrame,
    *,
    chart_dir: Path,
    stamp: str,
    report_dir: str | Path,
    cache_dir: str | Path,
    as_of: str | None = None,
    top_n_decomp: int = 25,
) -> dict:
    """Generate charts 1–7; return {ok, charts: [Path...]}."""
    chart_dir = Path(chart_dir)
    chart_dir.mkdir(parents=True, exist_ok=True)
    as_of = as_of or (f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}" if len(stamp) == 8 else stamp)
    paths: list[Path] = []

    jobs = [
        ("1 decomp", lambda: plot_factor_decomposition(
            df, chart_dir / f"model_factor_decomp_{stamp}.png", top_n=top_n_decomp
        )),
        ("2 dist", lambda: plot_factor_distributions(
            df, chart_dir / f"model_factor_dist_{stamp}.png"
        )),
        ("3 scatter", lambda: plot_rs_factor_scatter_matrix(
            df, chart_dir / f"model_rs_factor_matrix_{stamp}.png"
        )),
        ("4 stability", lambda: plot_rank_stability(
            report_dir, chart_dir / f"model_rank_stability_{stamp}.png", current_stamp=stamp
        )),
        ("5 attrib", lambda: plot_sepatop_attribution(
            df, chart_dir / f"model_sepatop_attrib_{stamp}.png",
            cache_dir=cache_dir, as_of=as_of,
        )),
        ("6 quantile", lambda: plot_quantile_forward_returns(
            report_dir, cache_dir, chart_dir / f"model_quantile_fwd_{stamp}.png",
            current_stamp=stamp,
        )),
        ("7 coverage", lambda: plot_data_coverage(
            df, chart_dir / f"model_data_coverage_{stamp}.png"
        )),
    ]

    for name, fn in jobs:
        try:
            p = fn()
            if p is not None and Path(p).exists():
                paths.append(Path(p))
                print(f"  model-metric [{name}]: {Path(p).name}")
            else:
                print(f"  model-metric [{name}]: skipped (insufficient data)")
        except Exception as exc:  # noqa: BLE001
            logger.exception("model metric %s failed", name)
            print(f"  [경고] model-metric [{name}] 실패: {exc}")

    if paths:
        publish_many(paths)
    return {"ok": bool(paths), "charts": paths, "n": len(paths)}
