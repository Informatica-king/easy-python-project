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

logger = logging.getLogger(__name__)


def _setup_korean_font() -> None:
    for path in glob.glob("/usr/share/fonts/truetype/nanum/NanumGothic*.ttf"):
        fm.fontManager.addfont(path)
    if any(f.name == "NanumGothic" for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = "NanumGothic"
        plt.rcParams["axes.unicode_minus"] = False


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
    fig.savefig(out_path, dpi=140)
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
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
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
    fig.savefig(out_path, dpi=140)
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
    fig.savefig(out_path, dpi=140)
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
        "--skip-pdf",
        action="store_true",
        help="Skip bundling all anal charts into one PDF",
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
    if enriched.empty:
        print("[오류] 필터 후 후보가 없습니다.")
        return 1

    stamp = datetime.now().strftime("%Y%m%d")
    m = re.search(r"fundamental_(\d{8})", src.name)
    if m:
        stamp = m.group(1)

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
    print(f"중심값(산점도 원점): RS mean={cx:.1f}, Fund mean={cy:.1f}")
    print(f"charts: {bar_path.resolve()}")
    print(f"        {scatter_path.resolve()}")
    print(f"        {fund_hist_path.resolve()}")
    print(f"        {mcap_hist_path.resolve()}")
    print(f"report: {csv_path.resolve()}")

    core_charts = [bar_path, scatter_path, fund_hist_path, mcap_hist_path]
    publish_many(core_charts + [csv_path])

    all_chart_paths: list[Path] = list(core_charts)

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
            if top.get("ok"):
                for key in ("chart", "relative_chart"):
                    p = top.get(key)
                    if p:
                        all_chart_paths.append(Path(p))
        except Exception as exc:  # noqa: BLE001
            logger.exception("sepaTop failed")
            print(f"[경고] sepaTop 실행 실패: {exc}")

    # One PDF with every anal visualization (mobile-friendly Artifacts download)
    if not args.skip_pdf:
        from sepa.anal_report import build_anal_pdf, collect_anal_chart_paths

        print("\n" + "=" * 64)
        print("  Analyze PDF pack — all charts")
        print("=" * 64)
        try:
            ordered = collect_anal_chart_paths(
                chart_dir=chart_dir, stamp=stamp, extra=all_chart_paths
            )
            pdf_path = Path(params.report_dir) / "charts" / f"analyze_report_{stamp}.pdf"
            out = build_anal_pdf(ordered, pdf_path, stamp=stamp)
            if out is not None:
                print(f"PDF: {out.resolve()}  ({len(ordered)} charts)")
                print("  → Artifacts에서 analyze_report_*.pdf 다운로드 (Android 지원)")
            else:
                print("[경고] PDF에 넣을 차트가 없습니다.")
        except Exception as exc:  # noqa: BLE001
            logger.exception("anal PDF failed")
            print(f"[경고] Analyze PDF 생성 실패: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
