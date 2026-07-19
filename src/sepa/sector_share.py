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
WEEK_SPAN_DAYS = 7
MONTH_SPAN_DAYS = 28


def _setup_korean_font() -> None:
    for path in glob.glob("/usr/share/fonts/truetype/nanum/NanumGothic*.ttf"):
        fm.fontManager.addfont(path)
    if any(f.name == "NanumGothic" for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = "NanumGothic"
        plt.rcParams["axes.unicode_minus"] = False


def stamp_to_date(stamp: str) -> str:
    return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"


def previous_week_friday(as_of: str | pd.Timestamp) -> pd.Timestamp:
    """지난주 금요일 (이번 주 월요 − 3일). as_of가 금요일이어도 지난주를 가리킨다."""
    ts = pd.Timestamp(as_of).normalize()
    this_monday = ts - pd.Timedelta(days=int(ts.weekday()))
    return this_monday - pd.Timedelta(days=3)


def previous_month_end(as_of: str | pd.Timestamp) -> pd.Timestamp:
    """직전 달의 마지막 캘린더일."""
    ts = pd.Timestamp(as_of).normalize()
    return (ts.replace(day=1) - pd.Timedelta(days=1)).normalize()


def nearest_snapshot_on_or_before(dates: list[str], target: pd.Timestamp) -> str | None:
    """dates are ISO YYYY-MM-DD strings; return best snapshot ≤ target."""
    target_s = target.strftime("%Y-%m-%d")
    candidates = [d for d in dates if d <= target_s]
    return candidates[-1] if candidates else None


def span_days(dates: list[str]) -> int:
    if not dates:
        return 0
    return int((pd.Timestamp(dates[-1]) - pd.Timestamp(dates[0])).days)


def resolve_period_baselines(
    dates: list[str],
    *,
    force_week: bool = False,
    force_month: bool = False,
) -> dict:
    """Decide whether week/month comparisons are available.

    Auto rules:
      week  — calendar span ≥ 7d AND a snapshot on/before 지난주 금요일 exists
      month — calendar span ≥ 28d AND a snapshot on/before 전월 말 exists
    force_* still requires a resolvable baseline snapshot.
    """
    if not dates:
        return {
            "as_of": None,
            "week": None,
            "month": None,
        }
    as_of = dates[-1]
    as_of_ts = pd.Timestamp(as_of)
    span = span_days(dates)

    week_target = previous_week_friday(as_of_ts)
    week_snap = nearest_snapshot_on_or_before(dates, week_target)
    week_auto = span >= WEEK_SPAN_DAYS and week_snap is not None and week_snap < as_of
    week_ok = (week_auto or force_week) and week_snap is not None and week_snap < as_of

    month_target = previous_month_end(as_of_ts)
    month_snap = nearest_snapshot_on_or_before(dates, month_target)
    month_auto = span >= MONTH_SPAN_DAYS and month_snap is not None and month_snap < as_of
    month_ok = (month_auto or force_month) and month_snap is not None and month_snap < as_of

    return {
        "as_of": as_of,
        "span_days": span,
        "week": {
            "eligible_auto": week_auto,
            "show": week_ok,
            "forced": force_week and week_ok,
            "target": week_target.strftime("%Y-%m-%d"),
            "snapshot": week_snap,
            "reason": _period_reason(
                kind="week",
                span=span,
                need=WEEK_SPAN_DAYS,
                target=week_target.strftime("%Y-%m-%d"),
                snap=week_snap,
                as_of=as_of,
                force=force_week,
            ),
        },
        "month": {
            "eligible_auto": month_auto,
            "show": month_ok,
            "forced": force_month and month_ok,
            "target": month_target.strftime("%Y-%m-%d"),
            "snapshot": month_snap,
            "reason": _period_reason(
                kind="month",
                span=span,
                need=MONTH_SPAN_DAYS,
                target=month_target.strftime("%Y-%m-%d"),
                snap=month_snap,
                as_of=as_of,
                force=force_month,
            ),
        },
    }


def _period_reason(
    *,
    kind: str,
    span: int,
    need: int,
    target: str,
    snap: str | None,
    as_of: str,
    force: bool,
) -> str:
    label = "주간(지난주 금요일)" if kind == "week" else "월간(전월 말)"
    if snap is None:
        return f"{label}: 기준일 {target} 이전 스냅샷 없음"
    if snap >= as_of:
        return f"{label}: 기준 스냅샷이 최신일과 같음"
    if force:
        return f"{label}: 강제 표시 (기준 스냅샷 {snap}, 목표 {target})"
    if span < need:
        return f"{label}: 데이터 기간 {span}일 < {need}일 — 쌓이면 자동 표시 (강제: !sepa.sectorShare({kind}))"
    return f"{label}: 자동 표시 (기준 스냅샷 {snap}, 목표 {target})"


def compute_delta_vs_baseline(
    panel: pd.DataFrame,
    *,
    baseline_date: str,
    as_of: str,
    value_col: str = "share_n",
    baseline_label: str = "baseline",
) -> pd.DataFrame:
    """Share delta (percentage points) between two snapshot dates."""
    if panel.empty:
        return pd.DataFrame()

    def _map(day: str) -> dict[str, float]:
        sub = panel.loc[panel["date"] == day, ["primary_tag", value_col]]
        out: dict[str, float] = {}
        for k, v in zip(sub["primary_tag"], sub[value_col]):
            if pd.notna(v):
                out[str(k)] = float(v)
        return out

    m0 = _map(baseline_date)
    m1 = _map(as_of)
    tags = sorted(set(m0) | set(m1))
    rows = []
    for t in tags:
        a = m0.get(t, 0.0)
        b = m1.get(t, 0.0)
        rows.append(
            {
                "primary_tag": t,
                f"share_{baseline_label}": a,
                "share_last": b,
                "delta_pp": (b - a) * 100.0,
                "baseline_date": baseline_date,
                "last_date": as_of,
                "baseline_label": baseline_label,
            }
        )
    return pd.DataFrame(rows).sort_values("delta_pp", ascending=False).reset_index(drop=True)


def plot_period_compare(
    panel: pd.DataFrame,
    *,
    baseline_date: str,
    as_of: str,
    out_path: Path,
    title: str,
    value_col: str = "share_n",
    top_k: int = 10,
) -> Path:
    """Side-by-side share bars for baseline vs as_of (top movers by |Δ|)."""
    _setup_korean_font()
    deltas = compute_delta_vs_baseline(
        panel, baseline_date=baseline_date, as_of=as_of, value_col=value_col, baseline_label="base"
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), gridspec_kw={"width_ratios": [1.1, 1]})
    if deltas.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
            ax.set_axis_off()
    else:
        sub = deltas.copy()
        sub["abs"] = sub["delta_pp"].abs()
        sub = sub.sort_values("abs", ascending=False).head(top_k).sort_values("delta_pp")

        ax0 = axes[0]
        colors = ["#c0392b" if v < 0 else "#27ae60" for v in sub["delta_pp"]]
        ax0.barh(sub["primary_tag"], sub["delta_pp"], color=colors, edgecolor="white")
        ax0.axvline(0, color="#444", lw=0.8)
        ax0.set_xlabel("점유율 변화 (%p)")
        ax0.set_title("Δ 점유율")
        ax0.grid(axis="x", alpha=0.3)

        ax1 = axes[1]
        y = np.arange(len(sub))
        h = 0.35
        ax1.barh(y - h / 2, sub["share_base"] * 100, height=h, label=baseline_date, color="#7f8c8d")
        ax1.barh(y + h / 2, sub["share_last"] * 100, height=h, label=as_of, color="#2980b9")
        ax1.set_yticks(y)
        ax1.set_yticklabels(sub["primary_tag"])
        ax1.set_xlabel("점유율 (%)")
        ax1.set_title("비중 비교")
        ax1.legend(fontsize=8, loc="best")
        ax1.grid(axis="x", alpha=0.3)

    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def print_period_section(
    label: str,
    info: dict,
    deltas: pd.DataFrame | None,
) -> None:
    print(f"\n  ◆ {label}")
    print(f"    {info['reason']}")
    if not info.get("show") or deltas is None or deltas.empty:
        return
    print(f"    기준 스냅샷 {info['snapshot']} → 최신 {info.get('as_of', deltas['last_date'].iloc[0])}")
    print(f"    {'섹터':<14} {'기준':>8} {'최신':>8} {'Δ%p':>8}")
    for _, r in deltas.head(12).iterrows():
        base_col = [c for c in r.index if c.startswith("share_") and c != "share_last"]
        base_v = float(r[base_col[0]]) if base_col else 0.0
        print(
            f"    {r['primary_tag']:<14} "
            f"{base_v * 100:7.1f}% {r['share_last'] * 100:7.1f}% {r['delta_pp']:+7.1f}"
        )


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


def plot_share_lines(
    wide: pd.DataFrame,
    out_path: Path,
    *,
    title: str,
    ylabel: str = "점유율 (%)",
) -> Path:
    """Multi-line sector share time series (one line per sector)."""
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
    x_labels = [str(d) for d in wide.index]
    x = np.arange(len(x_labels))
    for col in wide.columns:
        vals = wide[col].to_numpy(dtype=float) * 100.0
        ax.plot(
            x,
            vals,
            label=col,
            color=colors.get(col),
            marker="o",
            markersize=4.5,
            lw=1.8,
            alpha=0.92,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=30, ha="right")
    ymax = float(np.nanmax(wide.to_numpy(dtype=float))) * 100.0 if len(wide) else 0.0
    ax.set_ylim(0, max(ymax * 1.15, 10.0))
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7, frameon=False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


# Backward-compatible alias (old stacked bar/area → line chart)
def plot_stacked_share(
    wide: pd.DataFrame,
    out_path: Path,
    *,
    title: str,
    ylabel: str = "점유율",
) -> Path:
    y = ylabel if "%" in ylabel else f"{ylabel} (%)"
    return plot_share_lines(wide, out_path, title=title, ylabel=y)


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


def _render_universe_charts(
    panel: pd.DataFrame,
    *,
    chart_dir: Path,
    out_dir: Path,
    stamp: str,
    tag: str,
    label: str,
    period: str,
    top_n: int,
    baselines: dict,
) -> tuple[list[Path], list[Path], pd.DataFrame, pd.DataFrame]:
    """Render identical chart suite for one universe (all or fundhi).

    Returns (charts, csvs, week_deltas, month_deltas).
    """
    charts: list[Path] = []
    csvs: list[Path] = []
    week_deltas = pd.DataFrame()
    month_deltas = pd.DataFrame()
    if panel.empty:
        return charts, csvs, week_deltas, month_deltas

    dates = sorted(panel["date"].unique())
    as_of = dates[-1]
    deltas = compute_deltas(panel, value_col="share_n")
    wide_n = pivot_share(panel, "share_n", top_n=top_n)
    wide_m = pivot_share(panel.dropna(subset=["share_mcap"]), "share_mcap", top_n=top_n)

    p_lines_n = chart_dir / f"sector_share_lines_n_{tag}_{stamp}.png"
    p_lines_m = chart_dir / f"sector_share_lines_mcap_{tag}_{stamp}.png"
    p_delta_first = chart_dir / f"sector_share_delta_first_{tag}_{stamp}.png"
    p_delta_prev = chart_dir / f"sector_share_delta_prev_{tag}_{stamp}.png"
    p_heat = chart_dir / f"sector_share_heatmap_{tag}_{stamp}.png"

    plot_share_lines(
        wide_n, p_lines_n,
        title=f"{label} 섹터 점유율 (종목 수)  {period}",
        ylabel="종목 수 점유율 (%)",
    )
    plot_share_lines(
        wide_m, p_lines_m,
        title=f"{label} 섹터 점유율 (시총가중)  {period}",
        ylabel="시총 점유율 (%)",
    )
    plot_delta_bars(
        deltas, p_delta_first,
        title=f"{label} Δ vs 최초 ({dates[0]} → {as_of})",
        value_col="delta_vs_first_pp",
    )
    plot_delta_bars(
        deltas, p_delta_prev,
        title=f"{label} Δ vs 전일 ({dates[-2] if len(dates) > 1 else 'n/a'} → {as_of})",
        value_col="delta_vs_prev_pp",
    )
    plot_share_heatmap(
        wide_n, p_heat,
        title=f"{label} 섹터 점유율 히트맵 (종목 수 %)  {period}",
    )
    charts.extend([p_lines_n, p_lines_m, p_delta_first, p_delta_prev, p_heat])

    week_info = baselines.get("week")
    month_info = baselines.get("month")

    if week_info and week_info.get("show") and week_info.get("snapshot") in dates:
        week_deltas = compute_delta_vs_baseline(
            panel,
            baseline_date=week_info["snapshot"],
            as_of=as_of,
            value_col="share_n",
            baseline_label="week",
        )
        p_week = chart_dir / f"sector_share_vs_week_{tag}_{stamp}.png"
        plot_period_compare(
            panel,
            baseline_date=week_info["snapshot"],
            as_of=as_of,
            out_path=p_week,
            title=(
                f"{label} 주간 섹터 변화 vs 지난주 금요일 "
                f"({week_info['snapshot']} → {as_of})"
            ),
        )
        week_csv = out_dir / f"sector_share_vs_week_{tag}_{stamp}.csv"
        week_deltas.to_csv(week_csv, index=False)
        charts.append(p_week)
        csvs.append(week_csv)
        p_week_m = chart_dir / f"sector_share_vs_week_mcap_{tag}_{stamp}.png"
        plot_period_compare(
            panel,
            baseline_date=week_info["snapshot"],
            as_of=as_of,
            out_path=p_week_m,
            title=f"{label} 주간 섹터 변화 (시총가중)  {week_info['snapshot']} → {as_of}",
            value_col="share_mcap",
        )
        charts.append(p_week_m)

    if month_info and month_info.get("show") and month_info.get("snapshot") in dates:
        month_deltas = compute_delta_vs_baseline(
            panel,
            baseline_date=month_info["snapshot"],
            as_of=as_of,
            value_col="share_n",
            baseline_label="month",
        )
        p_month = chart_dir / f"sector_share_vs_month_{tag}_{stamp}.png"
        plot_period_compare(
            panel,
            baseline_date=month_info["snapshot"],
            as_of=as_of,
            out_path=p_month,
            title=(
                f"{label} 월간 섹터 변화 vs 전월 말 "
                f"({month_info['snapshot']} → {as_of})"
            ),
        )
        month_csv = out_dir / f"sector_share_vs_month_{tag}_{stamp}.csv"
        month_deltas.to_csv(month_csv, index=False)
        charts.append(p_month)
        csvs.append(month_csv)
        p_month_m = chart_dir / f"sector_share_vs_month_mcap_{tag}_{stamp}.png"
        plot_period_compare(
            panel,
            baseline_date=month_info["snapshot"],
            as_of=as_of,
            out_path=p_month_m,
            title=f"{label} 월간 섹터 변화 (시총가중)  {month_info['snapshot']} → {as_of}",
            value_col="share_mcap",
        )
        charts.append(p_month_m)

    return charts, csvs, week_deltas, month_deltas


def run_sector_share(
    *,
    report_dir: str | Path,
    stamp: str,
    current_df: pd.DataFrame | None = None,
    cache_dir: str | Path | None = None,
    chart_dir: Path | None = None,
    top_n: int = DEFAULT_TOP_N,
    fund_high: float = FUND_HIGH_DEFAULT,
    force_week: bool = False,
    force_month: bool = False,
) -> dict:
    """Build panel, charts, CSVs. Returns paths dict."""
    report_dir = Path(report_dir)
    chart_dir = chart_dir or (report_dir / "charts")
    chart_dir.mkdir(parents=True, exist_ok=True)
    out_dir = report_dir / "sector_share"
    out_dir.mkdir(parents=True, exist_ok=True)

    disk = list_analyze_snapshots(report_dir)
    dated: list[tuple[str, pd.DataFrame]] = []
    for s, path in disk:
        try:
            dated.append((s, load_snapshot(path, cache_dir=cache_dir)))
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
    dated_hi = [
        (s, d[d["fund_score"].astype(float) >= fund_high].copy())
        for s, d in dated
        if "fund_score" in d.columns
    ]
    dated_hi = [(s, d) for s, d in dated_hi if not d.empty]
    flows_hi = membership_flow_by_sector(dated_hi) if dated_hi else pd.DataFrame()

    dates = sorted(panel["date"].unique()) if not panel.empty else []
    period = f"{dates[0]} → {dates[-1]} ({len(dates)}일)" if dates else ""
    baselines = resolve_period_baselines(
        dates, force_week=force_week, force_month=force_month
    )

    charts_all, csvs_all, week_deltas, month_deltas = _render_universe_charts(
        panel,
        chart_dir=chart_dir,
        out_dir=out_dir,
        stamp=stamp,
        tag="all",
        label="Fund 전체 군집",
        period=period,
        top_n=top_n,
        baselines=baselines,
    )
    charts_hi, csvs_hi, week_hi, month_hi = _render_universe_charts(
        panel_hi,
        chart_dir=chart_dir,
        out_dir=out_dir,
        stamp=stamp,
        tag="fundhi",
        label=f"Fund≥{fund_high:.0f} 핵심 군집",
        period=period,
        top_n=top_n,
        baselines=baselines,
    )
    charts = charts_all + charts_hi
    extra_csvs = csvs_all + csvs_hi

    # Latest-day composition gap: all vs fundhi
    if dates and not panel.empty and not panel_hi.empty:
        last = dates[-1]
        a = panel[panel["date"] == last][["primary_tag", "share_n", "share_mcap"]].rename(
            columns={"share_n": "share_n_all", "share_mcap": "share_mcap_all"}
        )
        h = panel_hi[panel_hi["date"] == last][["primary_tag", "share_n", "share_mcap"]].rename(
            columns={"share_n": "share_n_hi", "share_mcap": "share_mcap_hi"}
        )
        gap = a.merge(h, on="primary_tag", how="outer").fillna(0.0)
        gap["delta_n_pp"] = (gap["share_n_hi"] - gap["share_n_all"]) * 100.0
        gap["delta_mcap_pp"] = (gap["share_mcap_hi"] - gap["share_mcap_all"]) * 100.0
        gap = gap.sort_values("delta_n_pp", ascending=False)
        gap_path = out_dir / f"sector_share_all_vs_fundhi_{stamp}.csv"
        gap.to_csv(gap_path, index=False)
        extra_csvs.append(gap_path)
        gap_chart = chart_dir / f"sector_share_all_vs_fundhi_{stamp}.png"
        plot_delta_bars(
            gap.rename(columns={"delta_n_pp": "delta_vs_first_pp"}),
            gap_chart,
            title=f"핵심 vs 전체 섹터 비중 차이 (Fund≥{fund_high:.0f} − 전체, %p)  {last}",
            value_col="delta_vs_first_pp",
        )
        charts.append(gap_chart)

    panel_path = out_dir / f"sector_share_panel_{stamp}.csv"
    hi_path = out_dir / f"sector_share_fundhi_{stamp}.csv"
    delta_path = out_dir / f"sector_share_delta_{stamp}.csv"
    flow_path = out_dir / f"sector_share_flow_{stamp}.csv"
    history_path = out_dir / "sector_share_history.csv"

    panel.to_csv(panel_path, index=False)
    panel_hi.to_csv(hi_path, index=False)
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
    if not flows_hi.empty:
        flows_hi.to_csv(out_dir / f"sector_share_flow_fundhi_{stamp}.csv", index=False)

    if history_path.exists():
        old = pd.read_csv(history_path)
        old = old[~old["date"].isin(panel["date"].unique())]
        hist = pd.concat([old, panel], ignore_index=True)
    else:
        hist = panel
    hist = hist.sort_values(["date", "primary_tag"]).reset_index(drop=True)
    hist.to_csv(history_path, index=False)

    print_share_tables(panel, deltas, flows, panel_hi, fund_high=fund_high)

    week_info = baselines.get("week")
    month_info = baselines.get("month")
    as_of = baselines.get("as_of")
    print("\n  ◆ 주/월 기준 섹터 변화 (전체 군집)")
    if week_info:
        week_info = {**week_info, "as_of": as_of}
        print_period_section("주간 vs 지난주 금요일", week_info, week_deltas if week_info["show"] else None)
    if month_info:
        month_info = {**month_info, "as_of": as_of}
        print_period_section("월간 vs 전월 말", month_info, month_deltas if month_info["show"] else None)

    if dates:
        last_counts = panel[panel["date"] == dates[-1]].sort_values("n", ascending=False)
        print("\n  ◆ 섹터별 절대 종목 수 (전체, 최근일)")
        print("   " + ", ".join(f"{r.primary_tag}={int(r.n)}" for _, r in last_counts.iterrows()))
        if not panel_hi.empty:
            hi_counts = panel_hi[panel_hi["date"] == dates[-1]].sort_values("n", ascending=False)
            print(f"\n  ◆ 섹터별 절대 종목 수 (Fund≥{fund_high:.0f}, 최근일)")
            print("   " + ", ".join(f"{r.primary_tag}={int(r.n)}" for _, r in hi_counts.iterrows()))

    print("\n섹터 점유율 charts:")
    for p in charts:
        print(f"  {p.resolve()}")
    print(f"panel : {panel_path.resolve()}")
    print(f"delta : {delta_path.resolve()}")
    print(f"flow  : {flow_path.resolve()}")
    print(f"hist  : {history_path.resolve()}")
    for p in extra_csvs:
        print(f"period: {p.resolve()}")

    publish_many(charts + [panel_path, hi_path, delta_path, flow_path, history_path] + extra_csvs)
    return {
        "ok": True,
        "panel": panel_path,
        "panel_hi": hi_path,
        "deltas": delta_path,
        "flows": flow_path,
        "history": history_path,
        "charts": charts,
        "n_snapshots": len(dates),
        "span_days": baselines.get("span_days", 0),
        "week": week_info,
        "month": month_info,
        "week_deltas": week_deltas,
        "month_deltas": month_deltas,
    }


def main(argv: list[str] | None = None) -> int:
    """Standalone: python -m sepa.sector_share [--week] [--month] [--force-week] [--force-month]"""
    import argparse

    from sepa.config import load_params

    parser = argparse.ArgumentParser(description="Fund sector-share time series (+ week/month)")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--stamp", default=None, help="YYYYMMDD (default: latest analyze_)")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--fund-high", type=float, default=FUND_HIGH_DEFAULT)
    parser.add_argument(
        "--week",
        action="store_true",
        help="Force weekly vs last-Friday comparison even if span < 7d",
    )
    parser.add_argument(
        "--month",
        action="store_true",
        help="Force monthly vs prior-month-end comparison even if span < 28d",
    )
    parser.add_argument("--force-week", action="store_true", help="Alias of --week")
    parser.add_argument("--force-month", action="store_true", help="Alias of --month")
    args = parser.parse_args(argv)

    params = load_params(args.config)
    snaps = list_analyze_snapshots(params.report_dir)
    if not snaps:
        print("[오류] analyze_*.csv 가 없습니다. 먼저 !sepa.anal() 을 실행하세요.")
        return 1
    stamp = args.stamp or snaps[-1][0]
    result = run_sector_share(
        report_dir=params.report_dir,
        stamp=stamp,
        cache_dir=params.data.cache_dir,
        top_n=args.top_n,
        fund_high=args.fund_high,
        force_week=bool(args.week or args.force_week),
        force_month=bool(args.month or args.force_month),
    )
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
