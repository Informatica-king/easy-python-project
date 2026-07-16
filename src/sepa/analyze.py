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


def fetch_sector_meta(ticker: str) -> dict[str, str | None]:
    import yfinance as yf

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:  # noqa: BLE001
        logger.debug("sector fetch failed %s: %s", ticker, exc)
        return {"sector": None, "industry": None}
    return {
        "sector": info.get("sector") or info.get("sectorDisp"),
        "industry": info.get("industry") or info.get("industryDisp"),
    }


def enrich_with_sectors(
    df: pd.DataFrame,
    cache_dir: str | Path,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Attach sector, industry, tags columns (tags = '|' joined)."""
    cache = {} if refresh else load_sector_cache(cache_dir)
    rows = []
    for ticker in df["ticker"].astype(str):
        t = ticker.upper()
        if t not in cache or refresh:
            cache[t] = fetch_sector_meta(t)
        meta = cache[t]
        tags = classify_tags(meta.get("sector"), meta.get("industry"))
        rows.append(
            {
                "ticker": t,
                "sector": meta.get("sector"),
                "industry": meta.get("industry"),
                "tags": "|".join(tags),
                "primary_tag": tags[0],
            }
        )
    save_sector_cache(cache_dir, cache)
    meta_df = pd.DataFrame(rows)
    out = df.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper()
    return out.merge(meta_df, on="ticker", how="left")


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

    fig, ax = plt.subplots(figsize=(10, 8))
    # color by primary tag
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

    # annotate a few extremes (top fund / top rs)
    label_idx = set()
    for col, ascending in (("fund_score", False), ("rs_rank", False)):
        for i in df.sort_values(col, ascending=ascending).head(8).index:
            label_idx.add(i)
    for i in label_idx:
        row = df.loc[i]
        ax.annotate(
            row["ticker"],
            (row["rs_rank"], row["fund_score"]),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=7,
            alpha=0.9,
        )

    ax.set_xlabel("RS rank")
    ax.set_ylabel("Fundamental score")
    ax.set_title(
        f"SEPA Analyze — RS × Fund  (origin @ mean RS={cx:.1f}, Fund={cy:.1f})"
    )
    ax.grid(alpha=0.25)
    # quadrant hints
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    ax.text(xmax, ymax, "강모멘텀·강펀더", ha="right", va="top", fontsize=8, color="#1a5", alpha=0.7)
    ax.text(xmin, ymax, "약모멘텀·강펀더", ha="left", va="top", fontsize=8, color="#555", alpha=0.7)
    ax.text(xmax, ymin, "강모멘텀·약펀더", ha="right", va="bottom", fontsize=8, color="#555", alpha=0.7)
    ax.text(xmin, ymin, "약모멘텀·약펀더", ha="left", va="bottom", fontsize=8, color="#888", alpha=0.7)

    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7, frameon=False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path, cx, cy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SEPA sector + RS×Fund analysis")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument(
        "--from-fundamental", default=None,
        help="fundamental_*.csv path (default: latest in reports/)",
    )
    parser.add_argument("--out", default=None, help="chart output directory")
    parser.add_argument("--refresh-sectors", action="store_true")
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

    stamp = datetime.now().strftime("%Y%m%d")
    # Prefer date from filename fundamental_YYYYMMDD.csv
    m = re.search(r"fundamental_(\d{8})", src.name)
    if m:
        stamp = m.group(1)

    out_dir = Path(args.out or params.report_dir)
    chart_dir = out_dir / "charts" if out_dir.name != "charts" else out_dir
    chart_dir.mkdir(parents=True, exist_ok=True)

    counts = tag_counts(enriched)
    bar_path = plot_sector_bars(counts, chart_dir / f"analyze_sectors_{stamp}.png")
    scatter_path, cx, cy = plot_rs_fund_scatter(
        enriched, chart_dir / f"analyze_scatter_{stamp}.png"
    )

    csv_path = Path(params.report_dir) / f"analyze_{stamp}.csv"
    Path(params.report_dir).mkdir(parents=True, exist_ok=True)
    enriched.to_csv(csv_path, index=False)

    print_sector_sections(enriched)
    print(f"중심값(산점도 원점): RS mean={cx:.1f}, Fund mean={cy:.1f}")
    print(f"charts: {bar_path}")
    print(f"        {scatter_path}")
    print(f"report: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
