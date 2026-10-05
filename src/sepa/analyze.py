"""섹터 태깅 + RS×펀더멘털 분석 시각화.

Usage:
    python -m sepa.analyze [--from-fundamental reports/fundamental_YYYYMMDD.csv]
                           [--out reports/charts]
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
import pandas as pd

from sepa.config import load_params
from sepa.artifacts import publish_many
from sepa.candidates import apply_candidate_filters, summarize_drops
from sepa.fonts import savefig_korean, setup_korean_matplotlib

logger = logging.getLogger(__name__)


def _setup_korean_font() -> None:
    setup_korean_matplotlib(allow_install=True)


# (표시 태그, 매칭 키워드) — sector/industry 문자열에 대해 복수 매칭 가능
TAG_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("바이오", ("biotechnology", "biotech")),
    ("제약", ("pharmaceutical", "drug manufacturer", "drug manufacturers")),
    ("반도체", ("semiconductor",)),
    ("소프트웨어", ("software", "information technology services")),
    ("인터넷/플랫폼", ("internet content", "internet retail", "interactive media")),
    ("통신장비", ("communication equipment", "telecom")),
    ("금융", ("financial", "bank", "capital markets", "credit services", "insurance")),
    ("에너지", ("energy", "oil", "gas", "uranium")),
    ("산업재", ("industrial", "aerospace", "defense", "machinery", "construction", "trucking")),
    ("소비재", ("consumer", "restaurant", "apparel", "leisure", "travel", "retail")),
    ("헬스케어장비", ("medical device", "medical instruments", "medical care", "diagnostics", "health information")),
    ("하드웨어", ("computer hardware", "consumer electronics", "electronic components", "scientific instruments")),
]

SECTOR_KO = {
    "Technology": "기술",
    "Healthcare": "헬스케어",
    "Financial Services": "금융",
    "Consumer Cyclical": "경기소비재",
    "Consumer Defensive": "필수소비재",
    "Industrials": "산업재",
    "Energy": "에너지",
    "Basic Materials": "소재",
    "Communication Services": "커뮤니케이션",
    "Real Estate": "부동산",
    "Utilities": "유틸리티",
}


def classify_tags(sector: str | None, industry: str | None) -> list[str]:
    """Return multi-label sector tags (한국어). Primary GICS sector first when known."""
    tags: list[str] = []
    sec = (sector or "").strip()
    ind = (industry or "").strip()
    blob = f"{sec} {ind}".lower()

    if sec:
        tags.append(SECTOR_KO.get(sec, sec))

    for label, keys in TAG_RULES:
        if any(k in blob for k in keys):
            if label not in tags:
                tags.append(label)

    if not tags:
        tags.append("기타")
    return tags


def _sectors_cache_path(cache_dir: str | Path) -> Path:
    root = Path(cache_dir)
    fund = root.parent / "fundamentals" if root.name == "raw" else root / "fundamentals"
    fund.mkdir(parents=True, exist_ok=True)
    return fund / "_sectors.json"


def load_sector_cache(cache_dir: str | Path) -> dict[str, dict]:
    path = _sectors_cache_path(cache_dir)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_sector_cache(cache_dir: str | Path, data: dict[str, dict]) -> None:
    path = _sectors_cache_path(cache_dir)
    path.write_text(json.dumps(data, indent=0, ensure_ascii=False))


def fetch_sector_meta(ticker: str) -> dict:
    """Fetch sector/industry/marketCap from yfinance."""
    import yfinance as yf

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:  # noqa: BLE001
        logger.debug("sector fetch failed %s: %s", ticker, exc)
        return {"sector": None, "industry": None, "market_cap": None}
    mcap = info.get("marketCap")
    try:
        mcap_f = float(mcap) if mcap is not None else None
    except (TypeError, ValueError):
        mcap_f = None
    return {
        "sector": info.get("sector") or info.get("sectorDisp"),
        "industry": info.get("industry") or info.get("industryDisp"),
        "market_cap": mcap_f,
    }


def enrich_with_sectors(
    df: pd.DataFrame,
    cache_dir: str | Path,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Attach sector, industry, tags, market_cap columns."""
    cache = {} if refresh else load_sector_cache(cache_dir)
    rows = []
    for ticker in df["ticker"].astype(str):
        t = ticker.upper()
        need = (
            refresh
            or t not in cache
            or "market_cap" not in cache.get(t, {})
        )
        if need:
            cache[t] = fetch_sector_meta(t)
        meta = cache[t]
        tags = classify_tags(meta.get("sector"), meta.get("industry"))
        rows.append(
            {
                "ticker": t,
                "sector": meta.get("sector"),
                "industry": meta.get("industry"),
                "market_cap": meta.get("market_cap"),
                "tags": "|".join(tags),
                "primary_tag": tags[0],
            }
        )
    save_sector_cache(cache_dir, cache)
    meta_df = pd.DataFrame(rows)
    out = df.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper()
    # Avoid market_cap_x/y (and similar) when CSV already has meta columns
    overlap = [c for c in meta_df.columns if c != "ticker" and c in out.columns]
    if overlap:
        out = out.drop(columns=overlap)
    return out.merge(meta_df, on="ticker", how="left")


FUND_HIST_BINS = list(range(0, 80, 10)) + [100]
FUND_HIST_LABELS = ["0–9", "10–19", "20–29", "30–39", "40–49", "50–59", "60–69", "70+"]

# Mutually exclusive market-cap buckets (USD)
MCAP_EDGES = [0, 1e9, 5e9, 10e9, 50e9, float("inf")]
MCAP_LABELS = ["$1B 미만", "$1B–5B", "$5B–10B", "$10B–50B", "$50B+"]

FUND_COPY_MIN_DEFAULT = 40.0


def fund_score_bin_counts(scores: pd.Series) -> pd.Series:
    cat = pd.cut(
        scores.astype(float),
        bins=FUND_HIST_BINS,
        right=False,
        labels=FUND_HIST_LABELS,
        include_lowest=True,
    )
    return cat.value_counts().reindex(FUND_HIST_LABELS, fill_value=0)


def market_cap_bin_counts(market_caps: pd.Series) -> pd.Series:
    caps = pd.to_numeric(market_caps, errors="coerce")
    cat = pd.cut(
        caps,
        bins=MCAP_EDGES,
        right=False,
        labels=MCAP_LABELS,
        include_lowest=True,
    )
    return cat.value_counts().reindex(MCAP_LABELS, fill_value=0)


def fund_highlight_tickers(df: pd.DataFrame, min_score: float = FUND_COPY_MIN_DEFAULT) -> list[str]:
    """Tickers with fund_score >= min_score, fund_score desc then RS desc."""
    sub = df[df["fund_score"].astype(float) >= min_score].copy()
    if sub.empty:
        return []
    sort_cols = ["fund_score"] + (["rs_rank"] if "rs_rank" in sub.columns else [])
    sub = sub.sort_values(sort_cols, ascending=[False] * len(sort_cols))
    return [str(t) for t in sub["ticker"].tolist()]


def print_fund_distribution(scores: pd.Series) -> None:
    counts = fund_score_bin_counts(scores)
    n = max(len(scores), 1)
    print("\n=== Fund 점수 분포 ===\n")
    print(f"  n={len(scores)}  mean={scores.mean():.1f}  median={scores.median():.1f}  "
          f"std={scores.std():.1f}  min={scores.min():.1f}  max={scores.max():.1f}")
    print(f"  Fund=0: {(scores == 0).sum()} ({100 * (scores == 0).mean():.1f}%)\n")
    for lab, c in counts.items():
        pct = 100 * int(c) / n
        bar = "█" * int(round(pct / 2))
        print(f"  {lab:>6}  {int(c):3d}  ({pct:5.1f}%)  {bar}")


def print_mcap_distribution(market_caps: pd.Series) -> None:
    known = pd.to_numeric(market_caps, errors="coerce")
    n_known = int(known.notna().sum())
    n_miss = int(known.isna().sum())
    counts = market_cap_bin_counts(known)
    n = max(n_known, 1)
    print("\n=== 시가총액 분포 ===\n")
    print(f"  집계 가능 {n_known}종 / 결측 {n_miss}종\n")
    for lab, c in counts.items():
        pct = 100 * int(c) / n if n_known else 0.0
        bar = "█" * int(round(pct / 2))
        print(f"  {lab:>10}  {int(c):3d}  ({pct:5.1f}%)  {bar}")


def print_fund_copy_list(df: pd.DataFrame, min_score: float = FUND_COPY_MIN_DEFAULT) -> None:
    tickers = fund_highlight_tickers(df, min_score)
    print(f"\n=== Fund ≥ {min_score:.0f} 티커 (복사용, 쉼표 구분) — {len(tickers)}종 ===\n")
    if not tickers:
        print("  (해당 없음)")
    else:
        print(",".join(tickers))
    print()


def fund_median_threshold(df: pd.DataFrame) -> float:
    """Median fund_score of the candidate frame (NaN-safe)."""
    scores = pd.to_numeric(df["fund_score"], errors="coerce").dropna()
    if scores.empty:
        return float("nan")
    return float(scores.median())


def fund_median_tickers(df: pd.DataFrame) -> tuple[list[str], float]:
    """Tickers with fund_score >= median, ordered like fund_highlight_tickers."""
    med = fund_median_threshold(df)
    if not (med == med):  # NaN
        return [], med
    return fund_highlight_tickers(df, min_score=med), med


def print_fund_median_copy_list(
    df: pd.DataFrame,
    *,
    out_path: Path | None = None,
    banner: bool = True,
) -> tuple[list[str], float, str]:
    """Print (and optionally export) ALL median+ tickers as one copyable CSV line.

    Hard requirement for ``!sepa.go`` / ``!sepa.anal``: never truncate or omit
    tickers. Returns ``(tickers, median, comma_joined_line)``.
    """
    tickers, med = fund_median_tickers(df)
    med_s = "n/a" if med != med else f"{med:.1f}"
    line = ",".join(tickers)
    if banner:
        print("\n" + "=" * 64)
        print(f"  Fund ≥ 중앙값({med_s}) 티커 — 복사용 전체 문자열 ({len(tickers)}종)")
        print("  (생략 없음 · 한 줄 전부 복사)")
        print("=" * 64)
    else:
        print(f"\n=== Fund ≥ 중앙값({med_s}) 티커 (복사용, 쉼표 구분) — {len(tickers)}종 ===\n")
    if not tickers:
        print("(해당 없음)")
    else:
        # Single uninterrupted line — do not wrap, ellipsize, or sample.
        print(line)
    print()
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text((line + "\n") if line else "")
        print(f"export: {out_path}")
    return tickers, med, line


def format_fund_median_copy_line(df: pd.DataFrame) -> tuple[list[str], float, str]:
    """Return median+ tickers and comma-joined copy string (no printing)."""
    tickers, med = fund_median_tickers(df)
    return tickers, med, ",".join(tickers)


def latest_fundamental_csv(report_dir: str | Path) -> Path | None:
    paths = sorted(Path(report_dir).glob("fundamental_*.csv"))
    return paths[-1] if paths else None


def tag_counts(df: pd.DataFrame) -> pd.Series:
    counter: dict[str, int] = defaultdict(int)
    for raw in df["tags"].fillna("기타"):
        for tag in str(raw).split("|"):
            if tag:
                counter[tag] += 1
    return pd.Series(counter).sort_values(ascending=True)


def print_sector_sections(df: pd.DataFrame) -> None:
    """Group by primary_tag and list tickers with RS/Fund."""
    print("\n=== 섹터별 분류 (primary tag, 복수 태그는 CSV tags 컬럼) ===\n")
    for tag, g in df.groupby("primary_tag", sort=True):
        g = g.sort_values("fund_score", ascending=False)
        print(f"◆ {tag} ({len(g)})")
        for _, row in g.iterrows():
            name = row.get("name") or row["ticker"]
            print(
                f"  {name}-{row['ticker']}  "
                f"(RS {row['rs_rank']:.1f} | Fund {row['fund_score']:.1f})  "
                f"[{row['tags']}]"
            )
        print()


def plot_sector_bars(counts: pd.Series, out_path: Path) -> Path:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(9, max(4.0, 0.35 * len(counts) + 1)))
    counts.plot(kind="barh", ax=ax, color="#2c5f7c")
    ax.set_xlabel("종목 수 (복수 태그 중복 집계)")
    ax.set_title("SEPA Analyze — Sector / Theme tags")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    savefig_korean(fig, out_path, dpi=140)
    plt.close(fig)
    return out_path


def plot_rs_fund_scatter(df: pd.DataFrame, out_path: Path) -> tuple[Path, float, float]:
    """Scatter RS (x) vs Fund (y) with origin at mean of each axis."""
    _setup_korean_font()
    x = df["rs_rank"].astype(float)
    y = df["fund_score"].astype(float)
    cx, cy = float(x.mean()), float(y.mean())

    # Larger canvas so dense ticker labels remain readable even when overlapping
    fig, ax = plt.subplots(figsize=(14, 11))
    tags = df["primary_tag"].fillna("기타")
    uniq = sorted(tags.unique())
    cmap = plt.get_cmap("tab20", max(len(uniq), 1))
    color_map = {t: cmap(i) for i, t in enumerate(uniq)}

    for tag in uniq:
        m = tags == tag
        ax.scatter(
            x[m], y[m],
            s=42, alpha=0.85, label=tag,
            c=[color_map[tag]], edgecolors="white", linewidths=0.4,
        )

    ax.axvline(cx, color="#444", ls="--", lw=1.0, alpha=0.8)
    ax.axhline(cy, color="#444", ls="--", lw=1.0, alpha=0.8)
    ax.scatter([cx], [cy], c="black", s=60, zorder=5, marker="x")

    # Label every ticker (overlap allowed — user preference)
    for _, row in df.iterrows():
        ax.annotate(
            str(row["ticker"]),
            (float(row["rs_rank"]), float(row["fund_score"])),
            textcoords="offset points",
            xytext=(3, 3),
            fontsize=6,
            alpha=0.95,
            clip_on=False,
        )

    ax.set_xlabel("RS rank")
    ax.set_ylabel("Fundamental score")
    ax.set_title(
        f"SEPA Analyze — RS × Fund  (origin @ mean RS={cx:.1f}, Fund={cy:.1f})"
    )
    ax.grid(alpha=0.25)
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    ax.text(xmax, ymax, "강모멘텀·강펀더", ha="right", va="top", fontsize=8, color="#1a5", alpha=0.7)
    ax.text(xmin, ymax, "약모멘텀·강펀더", ha="left", va="top", fontsize=8, color="#555", alpha=0.7)
    ax.text(xmax, ymin, "강모멘텀·약펀더", ha="right", va="bottom", fontsize=8, color="#555", alpha=0.7)
    ax.text(xmin, ymin, "약모멘텀·약펀더", ha="left", va="bottom", fontsize=8, color="#888", alpha=0.7)

    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7, frameon=False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    savefig_korean(fig, out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return out_path, cx, cy


def plot_fund_histogram(scores: pd.Series, out_path: Path) -> Path:
    _setup_korean_font()
    counts = fund_score_bin_counts(scores)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(range(len(counts)), counts.values, color="#2c5f7c", edgecolor="white")
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(list(counts.index), rotation=0)
    ax.set_xlabel("Fund score")
    ax.set_ylabel("종목 수")
    ax.set_title(
        f"SEPA Analyze — Fund score distribution  "
        f"(n={len(scores)}, mean={scores.mean():.1f}, median={scores.median():.1f})"
    )
    ax.grid(axis="y", alpha=0.3)
    for i, v in enumerate(counts.values):
        if v:
            ax.text(i, v + 0.3, str(int(v)), ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    savefig_korean(fig, out_path, dpi=140)
    plt.close(fig)
    return out_path


def plot_mcap_histogram(market_caps: pd.Series, out_path: Path) -> Path:
    _setup_korean_font()
    known = pd.to_numeric(market_caps, errors="coerce")
    counts = market_cap_bin_counts(known)
    n_known = int(known.notna().sum())
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(range(len(counts)), counts.values, color="#5a7d4e", edgecolor="white")
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(list(counts.index), rotation=15, ha="right")
    ax.set_xlabel("시가총액")
    ax.set_ylabel("종목 수")
    ax.set_title(f"SEPA Analyze — Market cap distribution  (n={n_known})")
    ax.grid(axis="y", alpha=0.3)
    for i, v in enumerate(counts.values):
        if v:
            ax.text(i, v + 0.3, str(int(v)), ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    savefig_korean(fig, out_path, dpi=140)
    plt.close(fig)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SEPA sector + RS×Fund analysis")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument(
        "--from-fundamental", default=None,
        help="fundamental_*.csv path (default: latest in reports/)",
    )
    parser.add_argument("--out", default=None, help="chart output directory")
    parser.add_argument("--refresh-sectors", action="store_true")
    parser.add_argument(
        "--fund-min", type=float, default=FUND_COPY_MIN_DEFAULT,
        help="Fund score threshold for comma-separated ticker copy list (default 40)",
    )
    parser.add_argument(
        "--skip-sepatop",
        action="store_true",
        help="Skip sepaTop index build (default: run with anal)",
    )
    parser.add_argument(
        "--sepatop-days",
        type=int,
        default=252,
        help="Lookback trading days for sepaTop vs benchmarks (default 252)",
    )
    parser.add_argument(
        "--skip-sector-share",
        action="store_true",
        help="Skip sector share time-series charts (default: run with anal)",
    )
    parser.add_argument(
        "--sector-top-n",
        type=int,
        default=8,
        help="Top-N sectors in stacked/heatmap charts; rest → 기타 (default 8)",
    )
    parser.add_argument(
        "--force-sector-week",
        action="store_true",
        help="Force week-vs-last-Friday sector delta even if history < 7 days",
    )
    parser.add_argument(
        "--force-sector-month",
        action="store_true",
        help="Force month-vs-prior-month-end sector delta even if history < 28 days",
    )
    parser.add_argument(
        "--skip-model-metrics",
        action="store_true",
        help="Skip model-metric charts 1–7 (factor decomp, stability, coverage, …)",
    )
    parser.add_argument(
        "--skip-fund-trend",
        action="store_true",
        help="Skip Fund 10-pt bucket 1y equal-weight trend vs S&P500 chart",
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Skip bundling all anal charts into one PDF/ZIP/PNG pack",
    )
    parser.add_argument(
        "--skip-github-release",
        action="store_true",
        help="Skip uploading PDF to GitHub Release (no public download link)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    params = load_params(args.config)

    src = Path(args.from_fundamental) if args.from_fundamental else latest_fundamental_csv(params.report_dir)
    if src is None or not src.exists():
        print(
            "[오류] fundamental 결과가 없습니다. "
            "먼저 !sepa.fund() 를 실행하거나 --from-fundamental 경로를 지정하세요."
        )
        return 1

    df = pd.read_csv(src)
    required = {"ticker", "rs_rank", "fund_score"}
    missing = required - set(df.columns)
    if missing:
        print(f"[오류] {src} 에 필수 컬럼이 없습니다: {sorted(missing)}")
        return 1

    logger.info("loading %s (%d rows)", src, len(df))
    enriched = enrich_with_sectors(
        df, params.data.cache_dir, refresh=args.refresh_sectors
    )
    before_n = len(enriched)
    enriched, dropped = apply_candidate_filters(enriched)
    print(
        f"\n후보 필터: {before_n} → {len(enriched)}  "
        f"({summarize_drops(dropped)}; Fund=0 또는 시총 <$1B 제외)"
    )
    qmin = float(getattr(params.fundamental, "fund_quality_min", 0.0) or 0.0)
    if qmin > 0 and not enriched.empty:
        from sepa.fundamental import apply_fund_quality_filter

        enriched, qdrop = apply_fund_quality_filter(enriched, min_quality=qmin)
        print(f"quality 필터 (mean b/d/e ≥ {qmin}): 추가 제외 {qdrop} → n={len(enriched)}")
    if enriched.empty:
        print("[오류] 필터 후 후보가 없습니다.")
        return 1

    stamp = datetime.now().strftime("%Y%m%d")
    m = re.search(r"fundamental_(\d{8})", src.name)
    if m:
        stamp = m.group(1)

    from sepa.result_ledger import save_fund_quantile_log, save_params_snapshot

    params_pack = save_params_snapshot(args.config, params.report_dir, stamp, publish=True)
    print(
        f"params snapshot: sha256={str(params_pack.get('sha256', ''))[:12]}… "
        f"→ {params_pack.get('yaml')}"
    )
    qlog = save_fund_quantile_log(enriched, params.report_dir, stamp, publish=True)
    print(
        f"fund quantile log: n={(qlog.get('row') or {}).get('n')} "
        f"median={(qlog.get('row') or {}).get('fund_median')} → {qlog.get('log')}"
    )

    out_dir = Path(args.out or params.report_dir)
    chart_dir = out_dir / "charts" if out_dir.name != "charts" else out_dir
    chart_dir.mkdir(parents=True, exist_ok=True)

    scores = enriched["fund_score"].astype(float)
    counts = tag_counts(enriched)
    bar_path = plot_sector_bars(counts, chart_dir / f"analyze_sectors_{stamp}.png")
    scatter_path, cx, cy = plot_rs_fund_scatter(
        enriched, chart_dir / f"analyze_scatter_{stamp}.png"
    )
    fund_hist_path = plot_fund_histogram(
        scores, chart_dir / f"analyze_fund_hist_{stamp}.png"
    )
    mcap_hist_path = plot_mcap_histogram(
        enriched["market_cap"], chart_dir / f"analyze_mcap_hist_{stamp}.png"
    )

    csv_path = Path(params.report_dir) / f"analyze_{stamp}.csv"
    Path(params.report_dir).mkdir(parents=True, exist_ok=True)
    enriched.to_csv(csv_path, index=False)

    print_sector_sections(enriched)
    print_fund_distribution(scores)
    print_mcap_distribution(enriched["market_cap"])
    print_fund_copy_list(enriched, min_score=args.fund_min)
    median_export = Path(params.report_dir) / f"fund_median_tickers_{stamp}.txt"
    print_fund_median_copy_list(enriched, out_path=median_export)
    print(f"중심값(산점도 원점): RS mean={cx:.1f}, Fund mean={cy:.1f}")
    print(f"charts: {bar_path.resolve()}")
    print(f"        {scatter_path.resolve()}")
    print(f"        {fund_hist_path.resolve()}")
    print(f"        {mcap_hist_path.resolve()}")
    print(f"report: {csv_path.resolve()}")

    core_charts = [bar_path, scatter_path, fund_hist_path, mcap_hist_path]
    publish_many(core_charts + [csv_path, median_export])

    all_chart_paths: list[Path] = list(core_charts)
    sepatop_result: dict = {}
    release_extras: list[Path] = [csv_path, median_export]

    # Fund score 10-pt bucket 1y equal-weight trend vs S&P500 (PDF 본편)
    if not args.skip_fund_trend:
        from sepa.fund_score_trend import run_fund_score_trend

        print("\n" + "=" * 64)
        print("  Fund 점수 구간별 1년 추세 — auto from anal")
        print("=" * 64)
        try:
            ft = run_fund_score_trend(
                enriched,
                chart_dir=chart_dir,
                stamp=stamp,
                cache_dir=params.data.cache_dir,
                report_dir=params.report_dir,
            )
            if ft.get("chart"):
                all_chart_paths.append(Path(ft["chart"]))
            if ft.get("csv"):
                release_extras.append(Path(ft["csv"]))
        except Exception as exc:  # noqa: BLE001
            logger.exception("fund score trend failed")
            print(f"[경고] Fund 점수 구간 추세 실행 실패: {exc}")

    if not args.skip_sector_share:
        from sepa.sector_share import run_sector_share

        print("\n" + "=" * 64)
        print("  Sector share time-series — auto from anal")
        print("=" * 64)
        try:
            ss = run_sector_share(
                report_dir=params.report_dir,
                stamp=stamp,
                current_df=enriched,
                cache_dir=params.data.cache_dir,
                chart_dir=chart_dir,
                top_n=args.sector_top_n,
                fund_high=args.fund_min,
                force_week=args.force_sector_week,
                force_month=args.force_sector_month,
            )
            if ss.get("ok") and ss.get("charts"):
                all_chart_paths.extend(ss["charts"])
        except Exception as exc:  # noqa: BLE001
            logger.exception("sector share failed")
            print(f"[경고] 섹터 점유율 시계열 실행 실패: {exc}")

    if not args.skip_sepatop:
        from sepa.sepatop import run_from_fundamental_df

        as_of = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"
        print("\n" + "=" * 64)
        print("  sepaTop (cap-weighted) — auto from anal")
        print("=" * 64)
        try:
            top = run_from_fundamental_df(
                enriched,
                params=params,
                stamp=stamp,
                as_of=as_of,
                lookback_days=args.sepatop_days,
            )
            sepatop_result = top if isinstance(top, dict) else {}
            if sepatop_result.get("ok"):
                for key in ("chart", "relative_chart"):
                    p = sepatop_result.get(key)
                    if p:
                        all_chart_paths.append(Path(p))
                for key in (
                    "membership",
                    "tenure",
                    "changes",
                    "presence",
                    "always_present",
                    "panel",
                    "snapshot_md",
                    "index_csv",
                    "event_fwd",
                    "event_fwd_panel",
                    "event_fwd_summary",
                ):
                    p = sepatop_result.get(key)
                    if p:
                        release_extras.append(Path(p))
        except Exception as exc:  # noqa: BLE001
            logger.exception("sepaTop failed")
            print(f"[경고] sepaTop 실행 실패: {exc}")

    if not args.skip_model_metrics:
        from sepa.model_metrics import run_model_metrics

        as_of = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"
        print("\n" + "=" * 64)
        print("  Model metrics (1–7) — auto from anal")
        print("=" * 64)
        try:
            mm = run_model_metrics(
                enriched,
                chart_dir=chart_dir,
                stamp=stamp,
                report_dir=params.report_dir,
                cache_dir=params.data.cache_dir,
                as_of=as_of,
            )
            if mm.get("ok") and mm.get("charts"):
                all_chart_paths.extend(mm["charts"])
        except Exception as exc:  # noqa: BLE001
            logger.exception("model metrics failed")
            print(f"[경고] model metrics 실행 실패: {exc}")

    # Longitudinal performance ledger (grows with every go/anal)
    print("\n" + "=" * 64)
    print("  Performance ledger — auto update")
    print("=" * 64)
    try:
        from sepa.perf_ledger import ingest_missing_fundamental_stamps, update_perf_ledger
        from sepa.result_ledger import file_sha256

        soft_path = Path(params.report_dir) / f"rs_soft_drops_{stamp}.csv"
        soft_df = pd.read_csv(soft_path) if soft_path.exists() else None
        stage2_path = Path(params.report_dir) / f"stage2_{stamp}.csv"
        n_stage2 = len(pd.read_csv(stage2_path)) if stage2_path.exists() else None
        params_sha = ""
        cfg = Path(args.config)
        if cfg.exists():
            params_sha = file_sha256(cfg)
        missing = ingest_missing_fundamental_stamps(
            params.report_dir, params.data.cache_dir, publish=False
        )
        if missing:
            print(f"perf ledger backfill stamps: {', '.join(missing)}")
        perf = update_perf_ledger(
            report_dir=params.report_dir,
            cache_dir=params.data.cache_dir,
            stamp=stamp,
            fund_df=enriched,
            soft_drops=soft_df,
            n_stage2=n_stage2,
            params_sha=params_sha,
            publish=True,
            backfill_all_history=True,
        )
        if perf.get("ok"):
            print(
                f"perf baskets: {perf.get('n_baskets')}  "
                f"forward_rows={perf.get('n_forward_rows')}  "
                f"ready={perf.get('ready_counts')}"
            )
            for key in ("pool_log", "members", "forward", "summary_log"):
                p = perf.get(key)
                if p:
                    release_extras.append(Path(p))
    except Exception as exc:  # noqa: BLE001
        logger.exception("perf ledger failed")
        print(f"[경고] performance ledger 갱신 실패: {exc}")

    # Mobile-first pack: ZIP + PNG boards + PDF, then GitHub Release direct link
    if not args.skip_pdf:
        from sepa.anal_report import (
            build_anal_pack,
            collect_anal_chart_paths,
            publish_pdf_github_release,
        )

        print("\n" + "=" * 64)
        print("  Analyze report pack — ZIP / PNG boards / PDF")
        print("=" * 64)
        try:
            ordered = collect_anal_chart_paths(
                chart_dir=chart_dir, stamp=stamp, extra=all_chart_paths
            )
            pack = build_anal_pack(ordered, stamp=stamp, out_dir=chart_dir)
            if pack.get("ok"):
                print(f"charts bundled: {pack['n_charts']}")
                if pack.get("zip"):
                    print(f"ZIP: {Path(pack['zip']).resolve()}")
                if pack.get("boards"):
                    print(f"PNG boards: {len(pack['boards'])} pages")
                if pack.get("pdf"):
                    print(f"PDF: {Path(pack['pdf']).resolve()}")

                if pack.get("pdf") and not args.skip_github_release:
                    print("\n" + "=" * 64)
                    print("  PDF + analysis pack (GitHub Release)")
                    print("=" * 64)
                    fund_csv = Path(params.report_dir) / f"fundamental_{stamp}.csv"
                    soft_csv = Path(params.report_dir) / f"rs_soft_drops_{stamp}.csv"
                    stage2_csv = Path(params.report_dir) / f"stage2_{stamp}.csv"
                    ledger_extras = [
                        fund_csv,
                        soft_csv,
                        stage2_csv,
                        Path(params.report_dir) / f"fund_quantile_{stamp}.csv",
                        Path(params.report_dir) / "fund_quantile_log.csv",
                        Path(params.report_dir) / f"diagnostics_summary_{stamp}.csv",
                        Path(params.report_dir) / "diagnostics_summary_log.csv",
                        Path(params.report_dir) / "params_hash_log.csv",
                        Path(params.report_dir) / "params_snapshots" / f"params_{stamp}.yaml",
                        Path(params.report_dir) / "params_snapshots" / f"params_meta_{stamp}.csv",
                        Path(params.report_dir) / "sepatop" / "membership_event_fwd_panel.csv",
                        Path(params.report_dir) / "sepatop" / f"membership_event_fwd_{stamp}.csv",
                        Path(params.report_dir) / "sepatop" / f"membership_event_fwd_summary_{stamp}.csv",
                        Path(params.report_dir) / "perf" / "daily_pool_log.csv",
                        Path(params.report_dir) / "perf" / "basket_members_panel.csv",
                        Path(params.report_dir) / "perf" / "security_forward_panel.csv",
                        Path(params.report_dir) / "perf" / "basket_forward_summary_log.csv",
                    ]
                    for extra in ledger_extras:
                        if extra.exists():
                            release_extras.append(extra)
                    seen: set[str] = set()
                    unique_extras: list[Path] = []
                    for p in release_extras:
                        path = Path(p)
                        if not path.exists():
                            continue
                        key = str(path.resolve())
                        if key in seen:
                            continue
                        seen.add(key)
                        unique_extras.append(path)
                    rel = publish_pdf_github_release(
                        Path(pack["pdf"]),
                        stamp=stamp,
                        extra_assets=unique_extras,
                    )
                    if rel.get("ok"):
                        print(f"\n  PDF 직접 다운로드:\n  {rel['download_url']}\n")
                        print(f"  릴리즈 페이지: {rel['release_url']}")
                        extras = rel.get("extra_assets") or []
                        if extras:
                            print(f"  분석 부가파일 ({len(extras)}): {', '.join(extras)}")
                        pack["download_url"] = rel["download_url"]
                        pack["release_url"] = rel["release_url"]
                    else:
                        print(f"[경고] GitHub Release 업로드 실패: {rel.get('error')}")
                        print("  (로컬 PDF/ZIP은 생성됨 — --skip-github-release 로 생략 가능)")
            else:
                print("[경고] 리포트에 넣을 차트가 없습니다.")
        except Exception as exc:  # noqa: BLE001
            logger.exception("anal report pack failed")
            print(f"[경고] Analyze 리포트 생성 실패: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
