"""sepaTop — Fund 후보 시총가중 지수 vs 벤치마크.

나스닥·S&P500과 같이 **시가총액 가중(가격×주식수 프록시)** 로 지수를 구성한다.
주식수 프록시 = 최신 market_cap / 최신 종가 (고정 수량 가정, 리밸런싱은 멤버십 변경일만).

Usage:
    python -m sepa.sepatop [--from-fundamental reports/fundamental_YYYYMMDD.csv]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
import glob
import numpy as np
import pandas as pd

from sepa.artifacts import publish_many
from sepa.config import load_params
from sepa.data import store

logger = logging.getLogger(__name__)

BASE_LEVEL = 1000.0
DEFAULT_LOOKBACK_DAYS = 252  # ~1 trading year

# Display name -> yfinance symbol (broad + sector detail indices)
BENCHMARKS: list[tuple[str, str]] = [
    ("NASDAQ", "^IXIC"),
    ("S&P500", "^GSPC"),
    ("QQQ(나스닥100)", "QQQ"),
    ("SOX(필라델피아반도체)", "^SOX"),
    ("SMH(반도체ETF)", "SMH"),
    ("XBI(바이오테크)", "XBI"),
    ("XLK(기술섹터)", "XLK"),
    ("IWM(러셀2000)", "IWM"),
]


def _setup_korean_font() -> None:
    for path in glob.glob("/usr/share/fonts/truetype/nanum/NanumGothic*.ttf"):
        fm.fontManager.addfont(path)
    if any(f.name == "NanumGothic" for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = "NanumGothic"
        plt.rcParams["axes.unicode_minus"] = False


def sepatop_dirs(report_dir: str | Path, cache_dir: str | Path) -> tuple[Path, Path]:
    """Return (reports/sepatop, data/sepatop)."""
    reports = Path(report_dir) / "sepatop"
    root = Path(cache_dir)
    data = root.parent / "sepatop" if root.name == "raw" else root / "sepatop"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "charts").mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    return reports, data


def latest_fundamental_csv(report_dir: str | Path) -> Path | None:
    paths = sorted(Path(report_dir).glob("fundamental_*.csv"))
    return paths[-1] if paths else None


def load_constituents(path: Path, cache_dir: str | Path | None = None) -> pd.DataFrame:
    """Load fund CSV and ensure market_cap (enrich via yfinance cache if missing)."""
    from sepa.analyze import enrich_with_sectors
    from sepa.candidates import apply_candidate_filters, summarize_drops

    df = pd.read_csv(path)
    if "ticker" not in df.columns:
        raise ValueError(f"{path} missing columns: ['ticker']")
    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.upper()
    if "fund_score" not in df.columns:
        raise ValueError(f"{path} missing columns: ['fund_score']")

    need_mcap = "market_cap" not in df.columns or pd.to_numeric(
        df["market_cap"], errors="coerce"
    ).isna().all()
    if need_mcap or "market_cap" not in df.columns:
        if cache_dir is None:
            raise ValueError(f"{path} missing market_cap and no cache_dir to enrich")
        df = enrich_with_sectors(df, cache_dir, refresh=False)

    df["market_cap"] = pd.to_numeric(df["market_cap"], errors="coerce")
    if "close" in df.columns:
        df["close"] = pd.to_numeric(df["close"], errors="coerce")

    before = len(df)
    df, dropped = apply_candidate_filters(df)
    print(
        f"sepaTop 후보 필터: {before} → {len(df)}  "
        f"({summarize_drops(dropped)}; Fund=0 또는 시총 <$1B 제외)"
    )
    return df.reset_index(drop=True)


def estimate_shares(constituents: pd.DataFrame, price_map: dict[str, float]) -> dict[str, float]:
    """shares ≈ market_cap / latest_price."""
    shares: dict[str, float] = {}
    for _, row in constituents.iterrows():
        t = row["ticker"]
        px = price_map.get(t)
        if px is None or px <= 0:
            # fallback to CSV close
            px = float(row["close"]) if "close" in row and pd.notna(row.get("close")) else None
        if px is None or px <= 0:
            continue
        shares[t] = float(row["market_cap"]) / float(px)
    return shares


def load_price_panel(
    tickers: list[str],
    cache_dir: str | Path,
    lookback_years: int,
) -> pd.DataFrame:
    """Wide close panel (columns=tickers), tz-naive DatetimeIndex."""
    frames = {}
    for t in tickers:
        try:
            df = store.get_history(t, cache_dir, lookback_years, update=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("price load failed %s: %s", t, exc)
            continue
        if df is None or df.empty:
            continue
        s = df["close"].astype(float).copy()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        frames[t] = s
    if not frames:
        return pd.DataFrame()
    panel = pd.DataFrame(frames).sort_index()
    return panel.dropna(how="all")


def build_cap_weighted_index(
    panel: pd.DataFrame,
    shares: dict[str, float],
    *,
    base_level: float = BASE_LEVEL,
    min_coverage: float = 0.8,
) -> pd.Series:
    """Cap-weighted price index with fixed share counts (S&P-style level).

    Index_t = base * Σ(P_t * Q) / Σ(P_base * Q)
    Days where fewer than min_coverage of constituents have prices are dropped.
    """
    cols = [c for c in panel.columns if c in shares]
    if not cols:
        return pd.Series(dtype=float)
    q = pd.Series({c: shares[c] for c in cols}, dtype=float)
    sub = panel[cols]
    n = len(cols)
    coverage = sub.notna().sum(axis=1) / n
    sub = sub.loc[coverage >= min_coverage].ffill(limit=2)
    # drop rows still missing too many after ffill
    coverage = sub.notna().sum(axis=1) / n
    sub = sub.loc[coverage >= min_coverage]
    if sub.empty:
        return pd.Series(dtype=float)

    # Use first date with full-ish coverage as base
    base_row = sub.iloc[0]
    # fill remaining NA in a row with base prices so weights don't explode
    filled = sub.fillna(base_row)
    numer = filled.mul(q, axis=1).sum(axis=1)
    denom = float((base_row.fillna(0) * q).sum())
    if denom <= 0:
        return pd.Series(dtype=float)
    idx = base_level * numer / denom
    idx.name = "sepaTop"
    return idx


def fetch_benchmark_series(
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    """Download benchmark closes and return columns by display name."""
    import yfinance as yf

    symbols = [sym for _, sym in BENCHMARKS]
    raw = yf.download(
        symbols,
        start=start.date().isoformat(),
        end=(end + pd.Timedelta(days=1)).date().isoformat(),
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )
    out = {}
    name_by_sym = {sym: name for name, sym in BENCHMARKS}
    if isinstance(raw.columns, pd.MultiIndex):
        for sym in symbols:
            try:
                if sym in raw.columns.get_level_values(0):
                    s = raw[sym]["Close"]
                else:
                    continue
            except Exception:  # noqa: BLE001
                continue
            s = s.dropna().astype(float)
            s.index = pd.to_datetime(s.index).tz_localize(None)
            out[name_by_sym[sym]] = s
    else:
        # single symbol edge case
        if "Close" in raw.columns and len(symbols) == 1:
            s = raw["Close"].dropna().astype(float)
            s.index = pd.to_datetime(s.index).tz_localize(None)
            out[name_by_sym[symbols[0]]] = s
    return pd.DataFrame(out).sort_index()


def rebase_to(series: pd.Series, base_level: float, base_date: pd.Timestamp) -> pd.Series:
    if series.empty:
        return series
    # nearest date on or after base_date
    use = series.loc[series.index >= base_date]
    if use.empty:
        use = series
    base_val = float(use.iloc[0])
    if base_val == 0:
        return series * np.nan
    return base_level * series / base_val


def save_membership(path: Path, constituents: pd.DataFrame, as_of: str) -> None:
    cols = [c for c in ["ticker", "name", "fund_score", "rs_rank", "market_cap", "close"] if c in constituents.columns]
    out = constituents[cols].copy()
    out["as_of"] = as_of
    out.to_csv(path, index=False)


def list_membership_files(sepatop_report: Path) -> list[Path]:
    return sorted(sepatop_report.glob("membership_*.csv"))


def load_first_seen(data_dir: Path) -> dict[str, str]:
    path = data_dir / "first_seen.json"
    if path.exists():
        return {k.upper(): v for k, v in json.loads(path.read_text()).items()}
    return {}


def save_first_seen(data_dir: Path, data: dict[str, str]) -> None:
    (data_dir / "first_seen.json").write_text(json.dumps(dict(sorted(data.items())), indent=0))


def update_first_seen(first_seen: dict[str, str], tickers: list[str], as_of: str) -> dict[str, str]:
    out = dict(first_seen)
    for t in tickers:
        t = t.upper()
        if t not in out:
            out[t] = as_of
    return out


def membership_diff(prev: set[str], curr: set[str]) -> tuple[list[str], list[str]]:
    entered = sorted(curr - prev)
    exited = sorted(prev - curr)
    return entered, exited


def previous_membership(sepatop_report: Path, current_stamp: str) -> tuple[set[str], str | None]:
    files = [p for p in list_membership_files(sepatop_report) if p.stem.replace("membership_", "") < current_stamp]
    # also seed from older fundamental reports if no sepatop history
    if not files:
        return set(), None
    prev_path = files[-1]
    prev = set(pd.read_csv(prev_path)["ticker"].astype(str).str.upper())
    stamp = prev_path.stem.replace("membership_", "")
    return prev, stamp


def load_membership_history(sepatop_report: Path) -> list[tuple[str, set[str]]]:
    """Load (stamp, ticker_set) pairs sorted by stamp from membership_*.csv."""
    out: list[tuple[str, set[str]]] = []
    for path in list_membership_files(sepatop_report):
        stamp = path.stem.replace("membership_", "")
        try:
            tickers = set(pd.read_csv(path)["ticker"].astype(str).str.upper())
        except Exception:  # noqa: BLE001
            logger.warning("skip unreadable membership file: %s", path)
            continue
        out.append((stamp, tickers))
    return out


def membership_changes_frame(
    *,
    stamp: str,
    as_of: str,
    prev_stamp: str | None,
    entered: list[str],
    exited: list[str],
) -> pd.DataFrame:
    rows: list[dict] = []
    for t in entered:
        rows.append(
            {
                "stamp": stamp,
                "as_of": as_of,
                "prev_stamp": prev_stamp or "",
                "action": "enter",
                "ticker": t,
            }
        )
    for t in exited:
        rows.append(
            {
                "stamp": stamp,
                "as_of": as_of,
                "prev_stamp": prev_stamp or "",
                "action": "exit",
                "ticker": t,
            }
        )
    return pd.DataFrame(rows, columns=["stamp", "as_of", "prev_stamp", "action", "ticker"])


def append_membership_panel(
    panel_path: Path,
    constituents: pd.DataFrame,
    *,
    stamp: str,
    as_of: str,
) -> pd.DataFrame:
    """Append today's membership rows to a long panel (dedupe by stamp+ticker)."""
    cols = [c for c in ["ticker", "name", "fund_score", "rs_rank", "market_cap", "close"] if c in constituents.columns]
    today = constituents[cols].copy()
    today["stamp"] = stamp
    today["as_of"] = as_of
    today["ticker"] = today["ticker"].astype(str).str.upper()

    if panel_path.exists():
        try:
            hist = pd.read_csv(panel_path)
            hist["ticker"] = hist["ticker"].astype(str).str.upper()
            hist["stamp"] = hist["stamp"].astype(str)
            hist = hist.loc[hist["stamp"] != stamp]
            panel = pd.concat([hist, today], ignore_index=True)
        except Exception:  # noqa: BLE001
            logger.warning("rebuild membership panel from today only (%s)", panel_path)
            panel = today
    else:
        panel = today

    ordered = ["stamp", "as_of", "ticker"] + [c for c in cols if c != "ticker"]
    panel = panel[[c for c in ordered if c in panel.columns]].sort_values(
        ["stamp", "ticker"]
    ).reset_index(drop=True)
    panel.to_csv(panel_path, index=False)
    return panel


def presence_table(history: list[tuple[str, set[str]]]) -> pd.DataFrame:
    """True snapshot presence stats (unlike first_seen tenure, exits reset streak).

    Columns:
      n_snapshots, n_present, presence_rate,
      always_present (in every snapshot on disk),
      streak_from_end (contiguous presence ending at latest stamp),
      first_stamp, last_stamp
    """
    if not history:
        return pd.DataFrame(
            columns=[
                "ticker",
                "n_snapshots",
                "n_present",
                "presence_rate",
                "always_present",
                "streak_from_end",
                "first_stamp",
                "last_stamp",
            ]
        )

    n_snap = len(history)
    stamps = [s for s, _ in history]
    all_tickers = sorted(set().union(*(s for _, s in history)))
    rows = []
    for t in all_tickers:
        flags = [t in s for _, s in history]
        n_present = int(sum(flags))
        streak = 0
        for f in reversed(flags):
            if f:
                streak += 1
            else:
                break
        present_stamps = [stamps[i] for i, f in enumerate(flags) if f]
        rows.append(
            {
                "ticker": t,
                "n_snapshots": n_snap,
                "n_present": n_present,
                "presence_rate": round(n_present / n_snap, 4) if n_snap else 0.0,
                "always_present": bool(n_present == n_snap and n_snap > 0),
                "streak_from_end": streak,
                "first_stamp": present_stamps[0] if present_stamps else "",
                "last_stamp": present_stamps[-1] if present_stamps else "",
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values(
            ["always_present", "streak_from_end", "presence_rate", "ticker"],
            ascending=[False, False, False, True],
        )
        .reset_index(drop=True)
    )


def write_analysis_snapshot_md(
    path: Path,
    *,
    stamp: str,
    as_of: str,
    n_constituents: int,
    prev_stamp: str | None,
    entered: list[str],
    exited: list[str],
    presence: pd.DataFrame,
    n_snapshots: int,
) -> Path:
    always = (
        presence.loc[presence["always_present"], "ticker"].astype(str).tolist()
        if not presence.empty and "always_present" in presence.columns
        else []
    )
    current = (
        presence.loc[presence["last_stamp"].astype(str) == stamp]
        if not presence.empty and "last_stamp" in presence.columns
        else presence.iloc[0:0]
    )
    top_streak = current.head(15) if not current.empty else presence.head(15)

    lines = [
        f"# sepaTop analysis snapshot — {as_of}",
        "",
        f"- stamp: `{stamp}`",
        f"- constituents: **{n_constituents}**",
        f"- membership snapshots on disk: **{n_snapshots}**",
        f"- prev snapshot: `{prev_stamp or '(none)'}`",
        f"- entered ({len(entered)}): {', '.join(entered) if entered else '(none)'}",
        f"- exited ({len(exited)}): {', '.join(exited) if exited else '(none)'}",
        "",
        "## Always present (every membership_*.csv on disk)",
        "",
        f"- count: **{len(always)}**",
        f"- tickers: {', '.join(always) if always else '(none yet — need ≥1 snapshot)'}",
        "",
        "> Note: `tenure_*.csv` / `first_seen` is **first appearance**, not continuous presence.",
        "> Use `presence_*.csv` / `always_present_*.csv` for never-missed / streak analysis.",
        "",
        "## Longest current streaks (ending today)",
        "",
        "| ticker | streak_from_end | n_present | presence_rate | always |",
        "|---|---:|---:|---:|:---:|",
    ]
    if top_streak.empty:
        lines.append("| (none) | | | | |")
    else:
        for _, row in top_streak.iterrows():
            lines.append(
                f"| {row['ticker']} | {int(row['streak_from_end'])} | "
                f"{int(row['n_present'])} | {float(row['presence_rate']):.2%} | "
                f"{'Y' if row['always_present'] else ''} |"
            )
    lines.extend(
        [
            "",
            "## Artifact files this run",
            "",
            f"- `membership_{stamp}.csv` — today's sepaTop constituents",
            f"- `membership_changes_{stamp}.csv` — enter/exit vs previous stamp",
            f"- `presence_{stamp}.csv` — presence rate / streak / always_present",
            f"- `always_present_{stamp}.csv` — never-missed subset",
            "- `membership_panel.csv` — cumulative long panel (all stamps on disk)",
            f"- `tenure_{stamp}.csv` — first_seen based (not continuous)",
            f"- `index_{stamp}.csv` — sepaTop vs benchmarks",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def seed_first_seen_from_fundamentals(report_dir: Path, first_seen: dict[str, str]) -> dict[str, str]:
    """Backfill first_seen from historical fundamental_*.csv dates."""
    out = dict(first_seen)
    for path in sorted(Path(report_dir).glob("fundamental_*.csv")):
        m = re.search(r"fundamental_(\d{8})", path.name)
        if not m:
            continue
        day = f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:8]}"
        try:
            tickers = pd.read_csv(path)["ticker"].astype(str).str.upper().tolist()
        except Exception:  # noqa: BLE001
            continue
        for t in tickers:
            if t not in out:
                out[t] = day
    return out


def tenure_table(
    constituents: pd.DataFrame,
    first_seen: dict[str, str],
    as_of: str,
) -> pd.DataFrame:
    as_of_ts = pd.Timestamp(as_of)
    rows = []
    for _, row in constituents.iterrows():
        t = row["ticker"]
        fs = first_seen.get(t, as_of)
        days = (as_of_ts - pd.Timestamp(fs)).days
        rows.append(
            {
                "ticker": t,
                "name": row.get("name", ""),
                "fund_score": row.get("fund_score"),
                "rs_rank": row.get("rs_rank"),
                "first_seen": fs,
                "days_in_sepaTop": max(int(days), 0) + 1,  # inclusive of first day
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["days_in_sepaTop", "fund_score"], ascending=[False, False]
    ).reset_index(drop=True)


def plot_index_chart(combined: pd.DataFrame, out_path: Path, title: str) -> Path:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(12, 6.5))
    colors = {
        "sepaTop": "#c0392b",
        "NASDAQ": "#2980b9",
        "S&P500": "#27ae60",
        "QQQ(나스닥100)": "#1abc9c",
        "SOX(필라델피아반도체)": "#8e44ad",
        "SMH(반도체ETF)": "#d68910",
        "XBI(바이오테크)": "#e74c3c",
        "XLK(기술섹터)": "#34495e",
        "IWM(러셀2000)": "#7f8c8d",
    }
    for col in combined.columns:
        ax.plot(
            combined.index,
            combined[col],
            label=col,
            lw=2.4 if col == "sepaTop" else 1.3,
            color=colors.get(col),
            alpha=0.95 if col == "sepaTop" else 0.8,
            zorder=5 if col == "sepaTop" else 2,
        )
    ax.axhline(BASE_LEVEL, color="#999", ls="--", lw=0.8, alpha=0.7)
    ax.set_title(title)
    ax.set_ylabel(f"지수 (기준일={BASE_LEVEL:.0f})")
    ax.grid(alpha=0.3)
    ax.legend(loc="best", fontsize=7, ncol=2)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_relative_chart(combined: pd.DataFrame, out_path: Path, title: str) -> Path:
    """sepaTop / each benchmark (relative strength), base=1.0."""
    _setup_korean_font()
    if "sepaTop" not in combined.columns or combined.empty:
        return out_path
    fig, ax = plt.subplots(figsize=(12, 5.5))
    sepa = combined["sepaTop"]
    colors = {
        "NASDAQ": "#2980b9",
        "S&P500": "#27ae60",
        "QQQ(나스닥100)": "#1abc9c",
        "SOX(필라델피아반도체)": "#8e44ad",
        "SMH(반도체ETF)": "#d68910",
        "XBI(바이오테크)": "#e74c3c",
        "XLK(기술섹터)": "#34495e",
        "IWM(러셀2000)": "#7f8c8d",
    }
    for col in combined.columns:
        if col == "sepaTop":
            continue
        rel = sepa / combined[col]
        base = float(rel.iloc[0])
        if base == 0 or pd.isna(base):
            continue
        ax.plot(
            combined.index,
            rel / base,
            label=f"sepaTop / {col}",
            lw=1.4,
            color=colors.get(col),
            alpha=0.9,
        )
    ax.axhline(1.0, color="#999", ls="--", lw=0.9)
    ax.set_title(title)
    ax.set_ylabel("상대강도 (기준일=1.0)")
    ax.grid(alpha=0.3)
    ax.legend(loc="best", fontsize=7, ncol=2)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def print_performance(combined: pd.DataFrame) -> None:
    if combined.empty:
        print("(지수 시계열 없음)")
        return
    first = combined.iloc[0]
    last = combined.iloc[-1]
    print("\n=== sepaTop vs 벤치마크 성과 ===\n")
    print(f"  기간: {combined.index[0].date()} → {combined.index[-1].date()}  "
          f"({len(combined)} 거래일)\n")
    print(f"  {'지수':<22} {'시작':>8} {'종료':>8} {'수익률':>10}")
    for col in combined.columns:
        ret = last[col] / first[col] - 1.0
        print(f"  {col:<22} {first[col]:8.1f} {last[col]:8.1f} {ret*100:9.2f}%")


def print_membership_changes(entered: list[str], exited: list[str], prev_stamp: str | None) -> None:
    print("\n=== sepaTop 편입 / 편출 ===\n")
    if prev_stamp is None:
        print("  (이전 스냅샷 없음 — 이번이 첫 기록)")
        return
    print(f"  비교 기준: membership_{prev_stamp}")
    print(f"  편입 ({len(entered)}): {', '.join(entered) if entered else '(없음)'}")
    print(f"  편출 ({len(exited)}): {', '.join(exited) if exited else '(없음)'}")


def print_tenure(tenure: pd.DataFrame, top_n: int = 20) -> None:
    print(f"\n=== sepaTop 체류 기간 (상위 {min(top_n, len(tenure))} / 전체 {len(tenure)}) ===\n")
    if tenure.empty:
        print("  (없음)")
        return
    for _, row in tenure.head(top_n).iterrows():
        name = row.get("name") or row["ticker"]
        fs = row["fund_score"]
        rs = row["rs_rank"]
        fs_s = f"{fs:.1f}" if pd.notna(fs) else "n/a"
        rs_s = f"{rs:.1f}" if pd.notna(rs) else "n/a"
        print(
            f"  {name}-{row['ticker']}  "
            f"{int(row['days_in_sepaTop']):4d}일  "
            f"(최초 {row['first_seen']} | RS {rs_s} | Fund {fs_s})"
        )


def run_sepatop(
    *,
    constituents: pd.DataFrame,
    params,
    stamp: str,
    as_of: str,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict:
    """Build index, membership diffs, charts. Returns paths/metrics dict."""
    sepatop_report, sepatop_data = sepatop_dirs(params.report_dir, params.data.cache_dir)

    # --- membership persistence (diff vs previous stamp, then save) ---
    prev_set, prev_stamp = previous_membership(sepatop_report, stamp)
    curr_set = set(constituents["ticker"].astype(str).str.upper())
    entered, exited = membership_diff(prev_set, curr_set)
    mem_path = sepatop_report / f"membership_{stamp}.csv"
    save_membership(mem_path, constituents, as_of)

    first_seen = load_first_seen(sepatop_data)
    first_seen = seed_first_seen_from_fundamentals(Path(params.report_dir), first_seen)
    first_seen = update_first_seen(first_seen, list(curr_set), as_of)
    # Don't erase first_seen for exited names — tenure history preserved
    save_first_seen(sepatop_data, first_seen)
    tenure = tenure_table(constituents, first_seen, as_of)
    tenure_path = sepatop_report / f"tenure_{stamp}.csv"
    tenure.to_csv(tenure_path, index=False)

    # --- price panel & shares ---
    tickers = constituents["ticker"].tolist()
    panel = load_price_panel(tickers, params.data.cache_dir, params.data.lookback_years)
    if panel.empty:
        print("[오류] sepaTop: 가격 패널을 만들 수 없습니다.")
        return {"ok": False}

    # trim to lookback window
    if len(panel) > lookback_days:
        panel = panel.iloc[-lookback_days:]

    last_prices = {}
    for t in tickers:
        if t in panel.columns and panel[t].notna().any():
            last_prices[t] = float(panel[t].dropna().iloc[-1])
    shares = estimate_shares(constituents, last_prices)
    sepa_idx = build_cap_weighted_index(panel, shares)
    if sepa_idx.empty:
        print("[오류] sepaTop: 지수 시계열 생성 실패.")
        return {"ok": False}

    base_date = sepa_idx.index[0]
    end_date = sepa_idx.index[-1]
    benches = fetch_benchmark_series(base_date, end_date)
    combined = pd.DataFrame({"sepaTop": sepa_idx})
    for col in benches.columns:
        combined[col] = rebase_to(benches[col], BASE_LEVEL, base_date)
    # Keep rows where sepaTop exists; benchmarks may have gaps (e.g. ^SOX)
    combined = combined.dropna(subset=["sepaTop"])
    # Forward-fill short benchmark gaps, then drop leading NA
    bench_cols = [c for c in combined.columns if c != "sepaTop"]
    if bench_cols:
        combined[bench_cols] = combined[bench_cols].ffill(limit=3)
    combined = combined.dropna(how="any")

    index_csv = sepatop_report / f"index_{stamp}.csv"
    combined.to_csv(index_csv)

    chart_path = sepatop_report / "charts" / f"sepatop_{stamp}.png"
    plot_index_chart(
        combined,
        chart_path,
        title=f"sepaTop vs Benchmarks  (cap-weighted, base {BASE_LEVEL:.0f} @ {base_date.date()})",
    )
    rel_path = sepatop_report / "charts" / f"sepatop_relative_{stamp}.png"
    plot_relative_chart(
        combined,
        rel_path,
        title=f"sepaTop 상대강도 vs Benchmarks  (@ {base_date.date()}=1.0)",
    )

    # --- longitudinal analysis pack (survives as Cursor artifacts + release assets) ---
    changes = membership_changes_frame(
        stamp=stamp,
        as_of=as_of,
        prev_stamp=prev_stamp,
        entered=entered,
        exited=exited,
    )
    changes_path = sepatop_report / f"membership_changes_{stamp}.csv"
    changes.to_csv(changes_path, index=False)

    panel_path = sepatop_report / "membership_panel.csv"
    append_membership_panel(panel_path, constituents, stamp=stamp, as_of=as_of)

    history = load_membership_history(sepatop_report)
    presence = presence_table(history)
    presence_path = sepatop_report / f"presence_{stamp}.csv"
    presence.to_csv(presence_path, index=False)
    always = (
        presence.loc[presence["always_present"]].copy()
        if not presence.empty
        else presence
    )
    always_path = sepatop_report / f"always_present_{stamp}.csv"
    always.to_csv(always_path, index=False)

    snapshot_md = write_analysis_snapshot_md(
        sepatop_report / f"analysis_snapshot_{stamp}.md",
        stamp=stamp,
        as_of=as_of,
        n_constituents=len(constituents),
        prev_stamp=prev_stamp,
        entered=entered,
        exited=exited,
        presence=presence,
        n_snapshots=len(history),
    )

    print_membership_changes(entered, exited, prev_stamp)
    print_tenure(tenure)
    n_always = int(always["always_present"].sum()) if not always.empty else 0
    print(
        f"\n=== sepaTop presence (snapshots={len(history)}, "
        f"always_present={n_always}) ===\n"
    )
    if n_always:
        print(f"  never-missed: {', '.join(always['ticker'].astype(str).tolist())}")
    else:
        print("  never-missed: (none — need overlapping history on disk)")
    print_performance(combined)
    print(f"\nsepaTop charts: {chart_path.resolve()}")
    print(f"               {rel_path.resolve()}")
    print(f"sepaTop index : {index_csv.resolve()}")
    print(f"membership    : {mem_path.resolve()}")
    print(f"changes       : {changes_path.resolve()}")
    print(f"presence      : {presence_path.resolve()}")
    print(f"always_present: {always_path.resolve()}")
    print(f"panel         : {panel_path.resolve()}")
    print(f"snapshot md   : {snapshot_md.resolve()}")
    print(f"tenure        : {tenure_path.resolve()}")

    analysis_paths = [
        chart_path,
        rel_path,
        index_csv,
        mem_path,
        tenure_path,
        changes_path,
        presence_path,
        always_path,
        panel_path,
        snapshot_md,
    ]
    published = publish_many(analysis_paths)
    if published:
        print(f"sepaTop artifacts: {len(published)} files published")
    return {
        "ok": True,
        "chart": chart_path,
        "relative_chart": rel_path,
        "index_csv": index_csv,
        "membership": mem_path,
        "tenure": tenure_path,
        "changes": changes_path,
        "presence": presence_path,
        "always_present": always_path,
        "panel": panel_path,
        "snapshot_md": snapshot_md,
        "analysis_paths": analysis_paths,
        "entered": entered,
        "exited": exited,
        "combined": combined,
        "n_always_present": n_always,
        "n_snapshots": len(history),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="sepaTop cap-weighted index vs benchmarks")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--from-fundamental", default=None)
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    params = load_params(args.config)

    src = Path(args.from_fundamental) if args.from_fundamental else latest_fundamental_csv(params.report_dir)
    if src is None or not src.exists():
        print("[오류] fundamental 결과가 필요합니다. 먼저 !sepa.fund() 또는 !sepa.go() 를 실행하세요.")
        return 1

    m = re.search(r"fundamental_(\d{8})", src.name)
    stamp = m.group(1) if m else datetime.now().strftime("%Y%m%d")
    as_of = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"

    try:
        constituents = load_constituents(src, cache_dir=params.data.cache_dir)
    except ValueError as exc:
        print(f"[오류] {exc}")
        return 1
    if constituents.empty:
        print("[오류] sepaTop 구성 종목이 비어 있습니다.")
        return 1

    print(f"\n=== sepaTop 구성 ({len(constituents)}종, 시총가중) — {as_of} ===")
    result = run_sepatop(
        constituents=constituents,
        params=params,
        stamp=stamp,
        as_of=as_of,
        lookback_days=args.lookback_days,
    )
    return 0 if result.get("ok") else 1


def run_from_fundamental_df(
    df: pd.DataFrame,
    *,
    params,
    stamp: str,
    as_of: str,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict:
    """Entry used by analyze / macros — applies same candidate filters."""
    from sepa.candidates import apply_candidate_filters, summarize_drops

    work = df.copy()
    work["ticker"] = work["ticker"].astype(str).str.upper()
    if "market_cap" not in work.columns:
        from sepa.analyze import enrich_with_sectors

        work = enrich_with_sectors(work, params.data.cache_dir, refresh=False)
    before = len(work)
    work, dropped = apply_candidate_filters(work)
    print(
        f"sepaTop 후보 필터: {before} → {len(work)}  "
        f"({summarize_drops(dropped)}; Fund=0 또는 시총 <$1B 제외)"
    )
    if work.empty:
        print("[오류] sepaTop 구성 종목이 비어 있습니다.")
        return {"ok": False}
    print(f"\n=== sepaTop 구성 ({len(work)}종, 시총가중) — {as_of} ===")
    return run_sepatop(
        constituents=work,
        params=params,
        stamp=stamp,
        as_of=as_of,
        lookback_days=lookback_days,
    )


if __name__ == "__main__":
    raise SystemExit(main())
