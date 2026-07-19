"""Fund 군집 섹터 점유율 시계열 분석.

analyze_*.csv 스냅샷을 모아 date × primary_tag 패널을 만들고,
종목수/시총 비중·Δ·편입편출·Fund≥40 서브군집 비중을 산출·시각화한다.

Usage (normally via analyze):
    from sepa.sector_share import run_sector_share
"""

from __future__ import annotations

import glob
import logging
import re
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
import numpy as np
import pandas as pd

from sepa.artifacts import publish_many

logger = logging.getLogger(__name__)

OTHER_LABEL = "기타(소규모)"
DEFAULT_TOP_N = 8
FUND_HIGH_DEFAULT = 40.0
STAMP_RE = re.compile(r"analyze_(\d{8})\.csv$")


def _setup_korean_font() -> None:
    for path in glob.glob("/usr/share/fonts/truetype/nanum/NanumGothic*.ttf"):
        fm.fontManager.addfont(path)
    if any(f.name == "NanumGothic" for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = "NanumGothic"
        plt.rcParams["axes.unicode_minus"] = False


def stamp_to_date(stamp: str) -> str:
    return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"


def list_analyze_snapshots(report_dir: str | Path) -> list[tuple[str, Path]]:
    """Return [(YYYYMMDD, path), ...] sorted ascending."""
    out: list[tuple[str, Path]] = []
    for path in Path(report_dir).glob("analyze_*.csv"):
        m = STAMP_RE.search(path.name)
        if m:
            out.append((m.group(1), path))
    return sorted(out, key=lambda x: x[0])


def load_snapshot(
    path: Path,
    *,
    cache_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Load one analyze CSV; ensure ticker / primary_tag / fund_score / market_cap."""
    df = pd.read_csv(path)
    if "ticker" not in df.columns:
        raise ValueError(f"{path} missing ticker")
    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.upper()
    if "fund_score" in df.columns:
        df["fund_score"] = pd.to_numeric(df["fund_score"], errors="coerce")
    else:
        df["fund_score"] = np.nan

    if "primary_tag" not in df.columns or df["primary_tag"].isna().all():
        if "sector" in df.columns:
            from sepa.analyze import classify_tags

            tags = [
                classify_tags(s, i if "industry" in df.columns else None)
                for s, i in zip(
                    df.get("sector", pd.Series([None] * len(df))),
                    df["industry"] if "industry" in df.columns else [None] * len(df),
                )
            ]
            df["primary_tag"] = [t[0] if t else "기타" for t in tags]
        else:
            df["primary_tag"] = "기타"
    df["primary_tag"] = df["primary_tag"].fillna("기타").astype(str)

    need_mcap = "market_cap" not in df.columns or pd.to_numeric(
        df["market_cap"], errors="coerce"
    ).isna().all()
    if need_mcap and cache_dir is not None:
        from sepa.analyze import enrich_with_sectors

        df = enrich_with_sectors(df, cache_dir, refresh=False)
    if "market_cap" in df.columns:
        df["market_cap"] = pd.to_numeric(df["market_cap"], errors="coerce")
    else:
        df["market_cap"] = np.nan
    return df


def _share_frame(df: pd.DataFrame, tag_col: str = "primary_tag") -> pd.DataFrame:
    """Per-tag counts and shares for one snapshot."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "primary_tag", "n", "share_n", "mcap_sum", "share_mcap",
            ]
        )
    work = df.copy()
    work[tag_col] = work[tag_col].fillna("기타").astype(str)
    g = work.groupby(tag_col, dropna=False)
    n = g.size().rename("n")
    mcap = g["market_cap"].sum(min_count=1).rename("mcap_sum")
    out = pd.concat([n, mcap], axis=1).reset_index().rename(columns={tag_col: "primary_tag"})
    total_n = float(out["n"].sum())
    out["share_n"] = out["n"] / total_n if total_n else 0.0
    mcap_ok = out["mcap_sum"].fillna(0)
    total_m = float(mcap_ok.sum())
    out["share_mcap"] = (mcap_ok / total_m) if total_m > 0 else np.nan
    return out


def build_share_panel(
    dated_frames: list[tuple[str, pd.DataFrame]],
    *,
    fund_high: float = FUND_HIGH_DEFAULT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (full_panel, fund_high_panel) long-form share tables.

    Columns: date, stamp, primary_tag, n, share_n, mcap_sum, share_mcap,
             universe (all|fund_high)
    """
    rows_all: list[pd.DataFrame] = []
    rows_hi: list[pd.DataFrame] = []
    for stamp, df in dated_frames:
        date = stamp_to_date(stamp)
        base = _share_frame(df)
        base["stamp"] = stamp
        base["date"] = date
        base["universe"] = "all"
        rows_all.append(base)

        hi = df[df["fund_score"].astype(float) >= fund_high] if "fund_score" in df.columns else df.iloc[0:0]
        hi_share = _share_frame(hi)
        hi_share["stamp"] = stamp
        hi_share["date"] = date
        hi_share["universe"] = "fund_high"
        rows_hi.append(hi_share)

    panel = pd.concat(rows_all, ignore_index=True) if rows_all else pd.DataFrame()
    panel_hi = pd.concat(rows_hi, ignore_index=True) if rows_hi else pd.DataFrame()
    return panel, panel_hi


def pivot_share(
    panel: pd.DataFrame,
    value_col: str = "share_n",
    *,
    top_n: int = DEFAULT_TOP_N,
    other_label: str = OTHER_LABEL,
) -> pd.DataFrame:
    """Wide matrix date × sector (Top-N by mean share + Other). Missing → 0."""
    if panel.empty:
        return pd.DataFrame()
    # rank sectors by mean share across history (prefer latest weight)
    means = panel.groupby("primary_tag")[value_col].mean().sort_values(ascending=False)
    means = means.dropna()
    keep = list(means.head(top_n).index)
    work = panel.copy()
    work["sector_plot"] = work["primary_tag"].where(work["primary_tag"].isin(keep), other_label)
    wide = (
        work.groupby(["date", "sector_plot"], as_index=False)[value_col]
        .sum()
        .pivot(index="date", columns="sector_plot", values=value_col)
        .fillna(0.0)
        .sort_index()
    )
    # column order: top_n then other
    cols = [c for c in keep if c in wide.columns]
    if other_label in wide.columns:
        cols.append(other_label)
    for c in wide.columns:
        if c not in cols:
            cols.append(c)
    return wide[cols]


def absolute_counts_wide(panel: pd.DataFrame, *, top_n: int = DEFAULT_TOP_N) -> pd.DataFrame:
    return pivot_share(panel, "n", top_n=top_n)


def compute_deltas(
    panel: pd.DataFrame,
    *,
    value_col: str = "share_n",
) -> pd.DataFrame:
    """Per-sector share on first / prev / last + deltas (percentage points)."""
    if panel.empty:
        return pd.DataFrame()
    dates = sorted(panel["date"].unique())
    first, last = dates[0], dates[-1]
    prev = dates[-2] if len(dates) >= 2 else None

    def _map(day: str) -> dict[str, float]:
        sub = panel.loc[panel["date"] == day, ["primary_tag", value_col]]
        return dict(zip(sub["primary_tag"], sub[value_col].astype(float)))

    m_first = _map(first)
    m_last = _map(last)
    m_prev = _map(prev) if prev else {}
    tags = sorted(set(m_first) | set(m_last) | set(m_prev))
    rows = []
    for t in tags:
        a = float(m_first.get(t, 0.0) or 0.0)
        b = float(m_last.get(t, 0.0) or 0.0)
        p = float(m_prev.get(t, 0.0) or 0.0) if prev else np.nan
        rows.append(
            {
                "primary_tag": t,
                "share_first": a,
                "share_prev": p,
                "share_last": b,
                "delta_vs_first_pp": (b - a) * 100.0,
                "delta_vs_prev_pp": ((b - p) * 100.0) if prev is not None else np.nan,
                "first_date": first,
                "prev_date": prev,
                "last_date": last,
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values("delta_vs_first_pp", ascending=False).reset_index(drop=True)


def membership_flow_by_sector(
    dated_frames: list[tuple[str, pd.DataFrame]],
) -> pd.DataFrame:
    """Compare consecutive snapshots: entered/exited counts by primary_tag."""
    if len(dated_frames) < 2:
        return pd.DataFrame(
            columns=[
                "from_date", "to_date", "primary_tag",
                "entered", "exited", "net",
            ]
        )
    rows = []
    for (s0, d0), (s1, d1) in zip(dated_frames[:-1], dated_frames[1:]):
        t0 = set(d0["ticker"].astype(str).str.upper())
        t1 = set(d1["ticker"].astype(str).str.upper())
        entered = t1 - t0
        exited = t0 - t1
        tag0 = dict(zip(d0["ticker"].astype(str).str.upper(), d0["primary_tag"].astype(str)))
        tag1 = dict(zip(d1["ticker"].astype(str).str.upper(), d1["primary_tag"].astype(str)))
        tags = sorted(set(tag0.values()) | set(tag1.values()))
        for tag in tags:
            e = sum(1 for t in entered if tag1.get(t) == tag)
            x = sum(1 for t in exited if tag0.get(t) == tag)
            if e or x:
                rows.append(
                    {
                        "from_date": stamp_to_date(s0),
                        "to_date": stamp_to_date(s1),
                        "from_stamp": s0,
                        "to_stamp": s1,
                        "primary_tag": tag,
                        "entered": e,
                        "exited": x,
                        "net": e - x,
                    }
                )
    return pd.DataFrame(rows)


def _sector_colors(labels: list[str]) -> dict[str, tuple]:
    cmap = plt.get_cmap("tab20", max(len(labels), 1))
    colors = {lab: cmap(i) for i, lab in enumerate(labels)}
    if OTHER_LABEL in colors:
        colors[OTHER_LABEL] = (0.75, 0.75, 0.75, 1.0)
    return colors


def plot_stacked_share(
    wide: pd.DataFrame,
    out_path: Path,
    *,
    title: str,
    ylabel: str = "점유율",
) -> Path:
    _setup_korean_font()
    if wide.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
        ax.set_axis_off()
        fig.savefig(out_path, dpi=140)
        plt.close(fig)
        return out_path

    fig_w = max(9.0, 0.55 * len(wide) + 6.0)
    fig, ax = plt.subplots(figsize=(fig_w, 5.8))
    colors = _sector_colors(list(wide.columns))
    x = np.arange(len(wide.index))
    # Prefer area when many dates; stacked bar when few (≤7)
    use_bar = len(wide) <= 7
    if use_bar:
        bottom = np.zeros(len(wide))
        for col in wide.columns:
            vals = wide[col].to_numpy(dtype=float)
            ax.bar(x, vals, bottom=bottom, label=col, color=colors.get(col), width=0.72, edgecolor="white", lw=0.4)
            bottom = bottom + vals
        ax.set_xticks(x)
        ax.set_xticklabels(list(wide.index), rotation=30, ha="right")
    else:
        ax.stackplot(
            wide.index.astype(str),
            *[wide[c].to_numpy(dtype=float) for c in wide.columns],
            labels=list(wide.columns),
            colors=[colors.get(c) for c in wide.columns],
            alpha=0.92,
        )
        ax.tick_params(axis="x", rotation=30)
    ax.set_ylim(0, 1.02)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7, frameon=False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_delta_bars(
    deltas: pd.DataFrame,
    out_path: Path,
    *,
    title: str,
    value_col: str = "delta_vs_first_pp",
    top_k: int = 12,
) -> Path:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    if deltas.empty or value_col not in deltas.columns:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
        ax.set_axis_off()
    else:
        sub = deltas.dropna(subset=[value_col]).copy()
        sub["abs"] = sub[value_col].abs()
        sub = sub.sort_values("abs", ascending=False).head(top_k)
        sub = sub.sort_values(value_col)
        colors = ["#c0392b" if v < 0 else "#27ae60" for v in sub[value_col]]
        ax.barh(sub["primary_tag"], sub[value_col], color=colors, edgecolor="white")
        ax.axvline(0, color="#444", lw=0.8)
        ax.set_xlabel("점유율 변화 (%p)")
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_share_heatmap(
    wide: pd.DataFrame,
    out_path: Path,
    *,
    title: str,
) -> Path:
    _setup_korean_font()
    fig_h = max(4.0, 0.38 * max(len(wide.columns), 1) + 2.0)
    fig_w = max(8.0, 0.5 * max(len(wide.index), 1) + 4.0)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    if wide.empty:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
        ax.set_axis_off()
    else:
        mat = wide.T.to_numpy(dtype=float) * 100.0  # sectors × dates, percent
        im = ax.imshow(mat, aspect="auto", cmap="YlOrRd", vmin=0)
        ax.set_xticks(range(len(wide.index)))
        ax.set_xticklabels(list(wide.index), rotation=35, ha="right", fontsize=8)
        ax.set_yticks(range(len(wide.columns)))
        ax.set_yticklabels(list(wide.columns), fontsize=8)
        ax.set_title(title)
        cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        cbar.set_label("점유율 (%)")
        # annotate when grid is small enough
        if mat.size <= 120:
            for i in range(mat.shape[0]):
                for j in range(mat.shape[1]):
                    val = mat[i, j]
                    if val >= 0.5:
                        ax.text(j, i, f"{val:.0f}", ha="center", va="center", fontsize=7, color="#222")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def print_share_tables(
    panel: pd.DataFrame,
    deltas: pd.DataFrame,
    flows: pd.DataFrame,
    panel_hi: pd.DataFrame,
    *,
    fund_high: float,
) -> None:
    if panel.empty:
        print("\n=== 섹터 점유율 시계열 ===\n  (스냅샷 없음)")
        return
    dates = sorted(panel["date"].unique())
    last = dates[-1]
    print("\n=== Fund 군집 섹터 점유율 시계열 ===\n")
    print(f"  기간: {dates[0]} → {last}  ({len(dates)}개 스냅샷)")
    today = panel[panel["date"] == last].sort_values("share_n", ascending=False)
    print(f"\n  ◆ 오늘({last}) 종목수 비중 / 시총 비중\n")
    print(f"  {'섹터':<14} {'n':>4} {'share_n':>9} {'share_mcap':>10}")
    for _, r in today.iterrows():
        sm = r["share_mcap"]
        sm_s = f"{sm * 100:8.1f}%" if pd.notna(sm) else "      n/a"
        print(f"  {r['primary_tag']:<14} {int(r['n']):4d} {r['share_n'] * 100:8.1f}% {sm_s}")

    if not deltas.empty:
        print("\n  ◆ Δ점유율 (종목수 기준, %p)\n")
        print(f"  {'섹터':<14} {'vs최초':>8} {'vs전일':>8}")
        for _, r in deltas.head(15).iterrows():
            d0 = r["delta_vs_first_pp"]
            dp = r["delta_vs_prev_pp"]
            dp_s = f"{dp:+7.1f}" if pd.notna(dp) else "    n/a"
            print(f"  {r['primary_tag']:<14} {d0:+7.1f} {dp_s}")

    if not flows.empty:
        latest_pair = flows[flows["to_date"] == last]
        if not latest_pair.empty:
            print(f"\n  ◆ 섹터별 편입/편출 (→ {last})\n")
            for _, r in latest_pair.sort_values("net", ascending=False).iterrows():
                print(
                    f"  {r['primary_tag']:<14}  "
                    f"+{int(r['entered'])} / -{int(r['exited'])}  "
                    f"(net {int(r['net']):+d})"
                )

    if not panel_hi.empty:
        hi_today = panel_hi[panel_hi["date"] == last].sort_values("share_n", ascending=False)
        n_hi = int(hi_today["n"].sum()) if not hi_today.empty else 0
        print(f"\n  ◆ Fund≥{fund_high:.0f} 서브군집 섹터 비중 (n={n_hi})\n")
        for _, r in hi_today.head(10).iterrows():
            print(f"  {r['primary_tag']:<14} {int(r['n']):4d}  {r['share_n'] * 100:5.1f}%")


def run_sector_share(
    *,
    report_dir: str | Path,
    stamp: str,
    current_df: pd.DataFrame | None = None,
    cache_dir: str | Path | None = None,
    chart_dir: Path | None = None,
    top_n: int = DEFAULT_TOP_N,
    fund_high: float = FUND_HIGH_DEFAULT,
) -> dict:
    """Build panel, charts, CSVs. Returns paths dict."""
    report_dir = Path(report_dir)
    chart_dir = chart_dir or (report_dir / "charts")
    chart_dir.mkdir(parents=True, exist_ok=True)
    out_dir = report_dir / "sector_share"
    out_dir.mkdir(parents=True, exist_ok=True)

    disk = list_analyze_snapshots(report_dir)
    # Reload with cache enrichment for missing mcap
    dated: list[tuple[str, pd.DataFrame]] = []
    seen: set[str] = set()
    for s, path in disk:
        try:
            dated.append((s, load_snapshot(path, cache_dir=cache_dir)))
            seen.add(s)
        except Exception as exc:  # noqa: BLE001
            logger.warning("skip %s: %s", path, exc)
    if current_df is not None and not current_df.empty:
        work = current_df.copy()
        work["ticker"] = work["ticker"].astype(str).str.upper()
        if "primary_tag" not in work.columns:
            work["primary_tag"] = "기타"
        if "market_cap" in work.columns:
            work["market_cap"] = pd.to_numeric(work["market_cap"], errors="coerce")
        else:
            work["market_cap"] = np.nan
        if "fund_score" in work.columns:
            work["fund_score"] = pd.to_numeric(work["fund_score"], errors="coerce")
        dated = [(s, d) for s, d in dated if s != stamp] + [(stamp, work)]
        dated = sorted(dated, key=lambda x: x[0])

    if not dated:
        print("[경고] 섹터 점유율: analyze 스냅샷이 없습니다.")
        return {"ok": False}

    panel, panel_hi = build_share_panel(dated, fund_high=fund_high)
    deltas = compute_deltas(panel, value_col="share_n")
    deltas_mcap = compute_deltas(panel.dropna(subset=["share_mcap"]), value_col="share_mcap")
    flows = membership_flow_by_sector(dated)

    wide_n = pivot_share(panel, "share_n", top_n=top_n)
    wide_m = pivot_share(panel.dropna(subset=["share_mcap"]), "share_mcap", top_n=top_n)
    wide_n_counts = absolute_counts_wide(panel, top_n=top_n)
    wide_hi = pivot_share(panel_hi, "share_n", top_n=top_n)

    dates = sorted(panel["date"].unique())
    period = f"{dates[0]} → {dates[-1]} ({len(dates)}일)"

    chart_stack_n = chart_dir / f"sector_share_stack_n_{stamp}.png"
    chart_stack_m = chart_dir / f"sector_share_stack_mcap_{stamp}.png"
    chart_delta_first = chart_dir / f"sector_share_delta_first_{stamp}.png"
    chart_delta_prev = chart_dir / f"sector_share_delta_prev_{stamp}.png"
    chart_heat = chart_dir / f"sector_share_heatmap_{stamp}.png"
    chart_stack_hi = chart_dir / f"sector_share_stack_fundhi_{stamp}.png"

    plot_stacked_share(
        wide_n, chart_stack_n,
        title=f"Fund 군집 섹터 점유율 (종목 수)  {period}",
        ylabel="종목 수 점유율",
    )
    plot_stacked_share(
        wide_m, chart_stack_m,
        title=f"Fund 군집 섹터 점유율 (시총가중)  {period}",
        ylabel="시총 점유율",
    )
    plot_delta_bars(
        deltas, chart_delta_first,
        title=f"섹터 점유율 Δ vs 최초 ({dates[0]} → {dates[-1]})",
        value_col="delta_vs_first_pp",
    )
    plot_delta_bars(
        deltas, chart_delta_prev,
        title=f"섹터 점유율 Δ vs 전일 ({dates[-2] if len(dates) > 1 else 'n/a'} → {dates[-1]})",
        value_col="delta_vs_prev_pp",
    )
    plot_share_heatmap(
        wide_n, chart_heat,
        title=f"섹터 점유율 히트맵 (종목 수 %)  {period}",
    )
    plot_stacked_share(
        wide_hi, chart_stack_hi,
        title=f"Fund≥{fund_high:.0f} 서브군집 섹터 점유율 (종목 수)  {period}",
        ylabel="종목 수 점유율",
    )

    panel_path = out_dir / f"sector_share_panel_{stamp}.csv"
    hi_path = out_dir / f"sector_share_fundhi_{stamp}.csv"
    delta_path = out_dir / f"sector_share_delta_{stamp}.csv"
    flow_path = out_dir / f"sector_share_flow_{stamp}.csv"
    # also keep a rolling history file that appends uniquely by date
    history_path = out_dir / "sector_share_history.csv"

    panel.to_csv(panel_path, index=False)
    panel_hi.to_csv(hi_path, index=False)
    # merge count + mcap deltas
    delta_out = deltas.copy()
    if not deltas_mcap.empty:
        merge_cols = ["primary_tag", "delta_vs_first_pp", "delta_vs_prev_pp", "share_last"]
        dm = deltas_mcap[merge_cols].rename(
            columns={
                "delta_vs_first_pp": "delta_mcap_vs_first_pp",
                "delta_vs_prev_pp": "delta_mcap_vs_prev_pp",
                "share_last": "share_mcap_last",
            }
        )
        delta_out = delta_out.merge(dm, on="primary_tag", how="outer")
    delta_out.to_csv(delta_path, index=False)
    flows.to_csv(flow_path, index=False)

    # rolling history: replace dates present in this panel
    if history_path.exists():
        old = pd.read_csv(history_path)
        old = old[~old["date"].isin(panel["date"].unique())]
        hist = pd.concat([old, panel], ignore_index=True)
    else:
        hist = panel
    hist = hist.sort_values(["date", "primary_tag"]).reset_index(drop=True)
    hist.to_csv(history_path, index=False)

    print_share_tables(panel, deltas, flows, panel_hi, fund_high=fund_high)

    # absolute counts summary line
    if not wide_n_counts.empty:
        print("\n  ◆ 섹터별 절대 종목 수 (최근일)")
        last_counts = panel[panel["date"] == dates[-1]].sort_values("n", ascending=False)
        print("   " + ", ".join(f"{r.primary_tag}={int(r.n)}" for _, r in last_counts.iterrows()))

    charts = [
        chart_stack_n, chart_stack_m, chart_delta_first, chart_delta_prev,
        chart_heat, chart_stack_hi,
    ]
    print("\n섹터 점유율 charts:")
    for p in charts:
        print(f"  {p.resolve()}")
    print(f"panel : {panel_path.resolve()}")
    print(f"delta : {delta_path.resolve()}")
    print(f"flow  : {flow_path.resolve()}")
    print(f"hist  : {history_path.resolve()}")

    publish_many(charts + [panel_path, hi_path, delta_path, flow_path, history_path])
    return {
        "ok": True,
        "panel": panel_path,
        "panel_hi": hi_path,
        "deltas": delta_path,
        "flows": flow_path,
        "history": history_path,
        "charts": charts,
        "n_snapshots": len(dates),
    }
