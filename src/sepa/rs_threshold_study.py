"""RS-rank threshold sweep through Stage2 → Fund (go-like ticker sets).

Runs **one** broad Stage-2 screen with Trend Template RS gate disabled
(conditions 1–7 only), scores fundamentals once, then slices by RS≥T for
T in 50/60/70/80/90 (configurable). Compares ticker groups between adjacent
thresholds — without re-running full scan/anal PDF per threshold.

Usage:
    python -m sepa.rs_threshold_study --full --no-update
    python -m sepa.rs_threshold_study --from-stage2-tech reports/stage2_tech_....csv
    python -m sepa.rs_threshold_study --from-scored reports/rs_study/fundamental_tech_....csv
    !sepa.rs_study()
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd

from sepa import fundamental, screener
from sepa.analyze import fund_median_tickers
from sepa.artifacts import publish_many
from sepa.candidates import apply_candidate_filters, summarize_drops
from sepa.config import Params, load_params, load_universe
from sepa.data import universe

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS = (50, 60, 70, 80, 90)


def _setup_korean_font() -> None:
    from sepa.fonts import setup_korean_matplotlib

    setup_korean_matplotlib(allow_install=True)
    plt.rcParams["axes.unicode_minus"] = False


def broad_stage2_tech(
    params: Params,
    *,
    full: bool = True,
    universe_path: str = "config/universe.yaml",
    as_of: str | None = None,
    update: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 2 on conditions 1–7 only; ``rs_rank`` still attached for slicing."""
    tp = dataclasses.replace(params.trend_template, rs_enabled=False)
    p = dataclasses.replace(params, trend_template=tp)

    try:
        names = universe.security_names(cache_dir=params.data.cache_dir)
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not load company names: %s", exc)
        names = {}

    if full:
        listed = universe.fetch_nasdaq_listed(cache_dir=params.data.cache_dir)
        tickers = universe.common_stock_tickers(listed)
        logger.info("full Nasdaq universe: %d tickers", len(tickers))
        if update:
            tickers, failed = store_bulk_update(params, tickers)
            logger.info("bulk update done: ok=%d failed=%d", len(tickers), len(failed))
            update = False
    else:
        tickers = load_universe(universe_path)

    stage2, diagnostics = screener.screen_stage2(
        p, tickers, as_of=as_of, update=update, names=names
    )
    return stage2, diagnostics


def store_bulk_update(params: Params, tickers: list[str]) -> tuple[list[str], list[str]]:
    from sepa.data import store

    return store.bulk_update(tickers, params.data.cache_dir, params.data.lookback_years)


def score_once(stage2: pd.DataFrame, params: Params, *, refresh: bool = False) -> pd.DataFrame:
    """Score every tech-Stage2 name once (no RS pre-filter), attach mcap/sector."""
    if stage2.empty:
        return stage2.copy()
    scored = fundamental.score_universe(stage2, params, refresh=refresh)
    if scored.empty:
        return scored
    from sepa.analyze import enrich_with_sectors

    return enrich_with_sectors(scored, params.data.cache_dir, refresh=False)


def slice_at_threshold(scored: pd.DataFrame, rs_min: float) -> dict:
    """Apply RS≥T then the same Fund/mcap candidate filters as go/fund."""
    work = scored.copy()
    work["rs_rank"] = pd.to_numeric(work["rs_rank"], errors="coerce")
    stage = work[work["rs_rank"] >= rs_min].reset_index(drop=True)
    kept, dropped = apply_candidate_filters(stage)
    median_tickers, med = fund_median_tickers(kept) if not kept.empty else ([], float("nan"))
    fund_tickers = (
        kept.sort_values(["fund_score", "rs_rank"], ascending=[False, False])["ticker"]
        .astype(str).str.upper().tolist()
        if not kept.empty else []
    )
    return {
        "rs_min": rs_min,
        "n_stage2": len(stage),
        "n_fund": len(kept),
        "n_dropped": len(dropped),
        "drop_summary": summarize_drops(dropped),
        "median_fund": med,
        "n_median_plus": len(median_tickers),
        "stage2_tickers": set(stage["ticker"].astype(str).str.upper()),
        "fund_tickers": set(fund_tickers),
        "median_tickers": set(median_tickers),
        "stage2_df": stage,
        "fund_df": kept,
    }


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    u = a | b
    return len(a & b) / len(u) if u else 1.0


def compare_adjacent(slices: list[dict], key: str = "fund_tickers") -> pd.DataFrame:
    rows = []
    for lo, hi in zip(slices, slices[1:]):
        a, b = lo[key], hi[key]
        added = sorted(b - a)      # appear when raising threshold? wait
        # slices sorted ascending by rs_min: lo=50, hi=60
        # when raising RS min 50→60, set shrinks: removed = in 50 not in 60, added = empty usually
        removed = sorted(a - b)  # lost when raising floor
        gained = sorted(b - a)   # should be empty when raising; keep for safety
        rows.append({
            "band": f"{int(lo['rs_min'])}→{int(hi['rs_min'])}",
            "rs_lo": lo["rs_min"],
            "rs_hi": hi["rs_min"],
            "n_lo": len(a),
            "n_hi": len(b),
            "delta_n": len(b) - len(a),
            "removed_n": len(removed),
            "added_n": len(gained),
            "symdiff_n": len(a ^ b),
            "jaccard": round(jaccard(a, b), 3),
            "removed": ",".join(removed),
            "added": ",".join(gained),
        })
    return pd.DataFrame(rows)


def plot_counts(summary: pd.DataFrame, out_path: Path) -> Path:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = summary["rs_min"].astype(int).astype(str)
    ax.plot(x, summary["n_stage2"], "o-", label="Stage2 (RS≥T)", color="#546e7a")
    ax.plot(x, summary["n_fund"], "s-", label="Fund 통과 (필터 후)", color="#1565c0")
    ax.plot(x, summary["n_median_plus"], "^-", label="Fund≥중앙값", color="#2e7d32")
    ax.set_xlabel("RS 하한 T")
    ax.set_ylabel("종목 수")
    ax.set_title("RS 임계값별 티커 수 (tech Stage2 → Fund)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_band_churn(adj: pd.DataFrame, out_path: Path, *, title: str) -> Path:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(adj["band"], adj["symdiff_n"], color="#ef6c00", label="대칭차집합 |A△B|")
    ax.plot(adj["band"], adj["removed_n"], "o--", color="#b71c1c", label="상향 시 탈락")
    ax.set_ylabel("종목 수")
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def fund_score_stats(series: pd.Series) -> dict:
    """Distribution summary for fund_score (empty-safe)."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {
            "n": 0,
            "mean": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "p10": float("nan"),
            "p25": float("nan"),
            "median": float("nan"),
            "p75": float("nan"),
            "p90": float("nan"),
            "max": float("nan"),
            "iqr": float("nan"),
            "share_ge_40": float("nan"),
            "share_ge_50": float("nan"),
            "share_ge_60": float("nan"),
        }
    q = s.quantile([0.10, 0.25, 0.50, 0.75, 0.90])
    return {
        "n": int(len(s)),
        "mean": round(float(s.mean()), 2),
        "std": round(float(s.std(ddof=1)), 2) if len(s) > 1 else 0.0,
        "min": round(float(s.min()), 2),
        "p10": round(float(q.loc[0.10]), 2),
        "p25": round(float(q.loc[0.25]), 2),
        "median": round(float(q.loc[0.50]), 2),
        "p75": round(float(q.loc[0.75]), 2),
        "p90": round(float(q.loc[0.90]), 2),
        "max": round(float(s.max()), 2),
        "iqr": round(float(q.loc[0.75] - q.loc[0.25]), 2),
        "share_ge_40": round(float((s >= 40).mean()), 3),
        "share_ge_50": round(float((s >= 50).mean()), 3),
        "share_ge_60": round(float((s >= 60).mean()), 3),
    }


def exclusive_rs_edges(thresholds: list[int] | tuple[int, ...]) -> list[tuple[float, float, str]]:
    """Build half-open RS bands from sorted floors, last band open to 100+."""
    ts = sorted(int(t) for t in thresholds)
    edges: list[tuple[float, float, str]] = []
    for i, lo in enumerate(ts):
        if i + 1 < len(ts):
            hi = ts[i + 1]
            edges.append((float(lo), float(hi), f"{lo}–{hi - 1}"))
        else:
            edges.append((float(lo), 101.0, f"{lo}+"))
    return edges


def fund_dist_cumulative(slices: list[dict]) -> pd.DataFrame:
    rows = []
    for sl in slices:
        stats = fund_score_stats(sl["fund_df"]["fund_score"] if not sl["fund_df"].empty else pd.Series(dtype=float))
        rows.append({"scope": "cumulative", "label": f"RS≥{int(sl['rs_min'])}", "rs_min": sl["rs_min"], **stats})
    return pd.DataFrame(rows)


def fund_dist_exclusive(scored: pd.DataFrame, thresholds: list[int] | tuple[int, ...]) -> pd.DataFrame:
    """Fund-passers only, binned into exclusive RS bands (not cumulative)."""
    kept, _ = apply_candidate_filters(scored)
    if kept.empty:
        return pd.DataFrame()
    work = kept.copy()
    work["rs_rank"] = pd.to_numeric(work["rs_rank"], errors="coerce")
    work = work.dropna(subset=["rs_rank", "fund_score"])
    rows = []
    for lo, hi, label in exclusive_rs_edges(thresholds):
        band = work[(work["rs_rank"] >= lo) & (work["rs_rank"] < hi)]
        stats = fund_score_stats(band["fund_score"])
        rows.append({"scope": "exclusive", "label": label, "rs_lo": lo, "rs_hi": hi, **stats})
    return pd.DataFrame(rows)


def fund_dist_removed_on_raise(slices: list[dict]) -> pd.DataFrame:
    """Fund-score stats for names dropped when RS floor is raised (lo → hi)."""
    rows = []
    for lo, hi in zip(slices, slices[1:]):
        removed = lo["fund_tickers"] - hi["fund_tickers"]
        kept = hi["fund_tickers"]
        lo_df = lo["fund_df"]
        if lo_df.empty:
            rem_scores = pd.Series(dtype=float)
            keep_scores = pd.Series(dtype=float)
        else:
            tick = lo_df["ticker"].astype(str).str.upper()
            rem_scores = lo_df.loc[tick.isin(removed), "fund_score"]
            keep_scores = lo_df.loc[tick.isin(kept), "fund_score"]
        rem = fund_score_stats(rem_scores)
        kep = fund_score_stats(keep_scores)
        rows.append({
            "band": f"{int(lo['rs_min'])}→{int(hi['rs_min'])}",
            "removed_n": rem["n"],
            "removed_mean": rem["mean"],
            "removed_median": rem["median"],
            "removed_p25": rem["p25"],
            "removed_p75": rem["p75"],
            "kept_n": kep["n"],
            "kept_mean": kep["mean"],
            "kept_median": kep["median"],
            "kept_p25": kep["p25"],
            "kept_p75": kep["p75"],
            "delta_median": (
                round(float(kep["median"] - rem["median"]), 2)
                if rem["n"] and kep["n"] and rem["median"] == rem["median"] and kep["median"] == kep["median"]
                else float("nan")
            ),
        })
    return pd.DataFrame(rows)


def plot_fund_box(
    slices: list[dict],
    scored: pd.DataFrame,
    thresholds: list[int] | tuple[int, ...],
    out_path: Path,
) -> Path:
    """Side-by-side boxplots: cumulative RS≥T and exclusive RS bands."""
    _setup_korean_font()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), sharey=True)

    cum_data, cum_labels = [], []
    for sl in slices:
        s = pd.to_numeric(sl["fund_df"]["fund_score"], errors="coerce").dropna()
        if len(s):
            cum_data.append(s.values)
            cum_labels.append(f"≥{int(sl['rs_min'])}\n(n={len(s)})")
    if cum_data:
        bp = axes[0].boxplot(cum_data, tick_labels=cum_labels, patch_artist=True, showfliers=True)
        for patch in bp["boxes"]:
            patch.set_facecolor("#90caf9")
            patch.set_alpha(0.85)
    axes[0].set_title("누적 RS≥T — Fund 점수 분포")
    axes[0].set_ylabel("Fund 점수")
    axes[0].grid(alpha=0.3, axis="y")

    kept, _ = apply_candidate_filters(scored)
    work = kept.copy() if not kept.empty else kept
    if not work.empty:
        work["rs_rank"] = pd.to_numeric(work["rs_rank"], errors="coerce")
        work["fund_score"] = pd.to_numeric(work["fund_score"], errors="coerce")
    excl_data, excl_labels = [], []
    for lo, hi, label in exclusive_rs_edges(thresholds):
        if work.empty:
            continue
        band = work[(work["rs_rank"] >= lo) & (work["rs_rank"] < hi)]["fund_score"].dropna()
        if len(band):
            excl_data.append(band.values)
            excl_labels.append(f"{label}\n(n={len(band)})")
    if excl_data:
        bp2 = axes[1].boxplot(excl_data, tick_labels=excl_labels, patch_artist=True, showfliers=True)
        for patch in bp2["boxes"]:
            patch.set_facecolor("#a5d6a7")
            patch.set_alpha(0.85)
    axes[1].set_title("독점 RS 구간 — Fund 점수 분포")
    axes[1].grid(alpha=0.3, axis="y")

    fig.suptitle("RS 구간별 Fund 점수 분포", fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_fund_hist_overlay(slices: list[dict], out_path: Path) -> Path:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    colors = ["#90a4ae", "#42a5f5", "#66bb6a", "#ffa726", "#ef5350"]
    bins = list(range(0, 85, 5))
    for i, sl in enumerate(slices):
        s = pd.to_numeric(sl["fund_df"]["fund_score"], errors="coerce").dropna()
        if s.empty:
            continue
        color = colors[i % len(colors)]
        ax.hist(
            s,
            bins=bins,
            density=True,
            histtype="step",
            linewidth=2.0,
            label=f"RS≥{int(sl['rs_min'])} (n={len(s)}, med={s.median():.1f})",
            color=color,
        )
    ax.set_xlabel("Fund 점수")
    ax.set_ylabel("밀도")
    ax.set_title("누적 RS≥T — Fund 점수 히스토그램(밀도)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_fund_centiles(dist_cum: pd.DataFrame, out_path: Path) -> Path:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(9, 5.0))
    x = dist_cum["label"]
    ax.fill_between(range(len(dist_cum)), dist_cum["p25"], dist_cum["p75"], color="#bbdefb", alpha=0.7, label="IQR (p25–p75)")
    ax.plot(range(len(dist_cum)), dist_cum["median"], "o-", color="#1565c0", label="중앙값")
    ax.plot(range(len(dist_cum)), dist_cum["mean"], "s--", color="#6a1b9a", label="평균")
    ax.plot(range(len(dist_cum)), dist_cum["p10"], ":", color="#546e7a", label="p10 / p90")
    ax.plot(range(len(dist_cum)), dist_cum["p90"], ":", color="#546e7a")
    ax.set_xticks(range(len(dist_cum)))
    ax.set_xticklabels(x)
    ax.set_ylabel("Fund 점수")
    ax.set_title("누적 RS≥T — Fund 점수 중심·분위수")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_removed_vs_kept(removed_df: pd.DataFrame, out_path: Path) -> Path:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = range(len(removed_df))
    w = 0.35
    ax.bar([i - w / 2 for i in x], removed_df["removed_median"], width=w, color="#ef9a9a", label="탈락 중앙값")
    ax.bar([i + w / 2 for i in x], removed_df["kept_median"], width=w, color="#81c784", label="잔류 중앙값")
    ax.set_xticks(list(x))
    ax.set_xticklabels(removed_df["band"])
    ax.set_ylabel("Fund 점수 중앙값")
    ax.set_title("RS 상향 시 탈락 vs 잔류 — Fund 중앙값")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def write_markdown(
    path: Path,
    *,
    stamp: str,
    thresholds: list[int],
    summary: pd.DataFrame,
    adj_fund: pd.DataFrame,
    adj_stage: pd.DataFrame,
    adj_median: pd.DataFrame,
    focus_70_80: dict,
    dist_cum: pd.DataFrame | None = None,
    dist_excl: pd.DataFrame | None = None,
    dist_removed: pd.DataFrame | None = None,
) -> Path:
    biggest = adj_fund.sort_values("symdiff_n", ascending=False).iloc[0]
    dist_note = ""
    if dist_cum is not None and not dist_cum.empty:
        peak = dist_cum.loc[dist_cum["median"].idxmax()]
        dist_note = (
            f"- Fund 중앙값 최고 구간(누적): **{peak['label']}** "
            f"(median={peak['median']}, mean={peak['mean']}, n={int(peak['n'])})"
        )
    rem_note = ""
    if dist_removed is not None and not dist_removed.empty and 70 in thresholds and 80 in thresholds:
        row7080 = dist_removed[dist_removed["band"] == "70→80"]
        if not row7080.empty:
            r = row7080.iloc[0]
            rem_note = (
                f"- 70→80 탈락 vs 잔류 Fund 중앙값: "
                f"탈락 {r['removed_median']} / 잔류 {r['kept_median']} "
                f"(Δ={r['delta_median']})"
            )

    lines = [
        f"# RS threshold study ({stamp})",
        "",
        "Broad scan: Trend Template **without RS gate** (conditions 1–7), then slice RS≥T "
        f"for T={list(thresholds)}. Fund scored once; go-equivalent filters "
        "(Fund>0, mcap≥$1B) applied per slice. Anal/PDF skipped (ticker-set focus).",
        "",
        "## Verdict",
        "",
        f"- Largest **Fund-set** change band: **{biggest['band']}** "
        f"(symdiff={int(biggest['symdiff_n'])}, removed={int(biggest['removed_n'])}, "
        f"jaccard={biggest['jaccard']})",
        f"- Focus 70 vs 80: stage2 {focus_70_80['n_stage_70']}→{focus_70_80['n_stage_80']}, "
        f"fund {focus_70_80['n_fund_70']}→{focus_70_80['n_fund_80']}, "
        f"fund removed when raising 70→80: {focus_70_80['fund_removed_n']}종",
    ]
    if dist_note:
        lines.append(dist_note)
    if rem_note:
        lines.append(rem_note)
    lines += [
        "",
        "## 1. Counts by RS floor",
        "",
        "| rs_min | n_stage2 | n_fund | n_dropped | n_median+ | median_fund |",
        "|---|---|---|---|---|---|",
    ]
    for r in summary.itertuples():
        med = "" if r.median_fund != r.median_fund else f"{r.median_fund:.1f}"
        lines.append(
            f"| {int(r.rs_min)} | {r.n_stage2} | {r.n_fund} | {r.n_dropped} | "
            f"{r.n_median_plus} | {med} |"
        )

    lines += [
        "",
        "## 2. Adjacent Fund-set churn (raising RS floor)",
        "",
        "| band | n_lo | n_hi | Δn | removed | symdiff | jaccard |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in adj_fund.itertuples():
        lines.append(
            f"| {r.band} | {r.n_lo} | {r.n_hi} | {r.delta_n} | {r.removed_n} | "
            f"{r.symdiff_n} | {r.jaccard} |"
        )

    lines += [
        "",
        "### Tickers removed 70→80 (Fund 통과 집합)",
        "",
        focus_70_80["fund_removed"] or "_(none)_",
        "",
        "### Tickers only in RS≥70 Fund (not in RS≥80)",
        "",
        focus_70_80["fund_only_70"] or "_(none)_",
        "",
        "## 3. Adjacent Stage2 churn",
        "",
        "| band | n_lo | n_hi | removed | symdiff | jaccard |",
        "|---|---|---|---|---|---|",
    ]
    for r in adj_stage.itertuples():
        lines.append(
            f"| {r.band} | {r.n_lo} | {r.n_hi} | {r.removed_n} | {r.symdiff_n} | {r.jaccard} |"
        )

    if dist_cum is not None and not dist_cum.empty:
        lines += [
            "",
            "## 4. Fund score distribution (cumulative RS≥T)",
            "",
            "| label | n | mean | std | p10 | p25 | median | p75 | p90 | max | ≥50% | ≥60% |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for r in dist_cum.itertuples():
            lines.append(
                f"| {r.label} | {r.n} | {r.mean} | {r.std} | {r.p10} | {r.p25} | "
                f"{r.median} | {r.p75} | {r.p90} | {r.max} | {r.share_ge_50} | {r.share_ge_60} |"
            )

    if dist_excl is not None and not dist_excl.empty:
        lines += [
            "",
            "## 5. Fund score distribution (exclusive RS bands)",
            "",
            "Fund 통과 종목만 RS 독점 구간에 배치 (겹치지 않음).",
            "",
            "| band | n | mean | std | p25 | median | p75 | ≥50% | ≥60% |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for r in dist_excl.itertuples():
            lines.append(
                f"| {r.label} | {r.n} | {r.mean} | {r.std} | {r.p25} | {r.median} | "
                f"{r.p75} | {r.share_ge_50} | {r.share_ge_60} |"
            )

    if dist_removed is not None and not dist_removed.empty:
        lines += [
            "",
            "## 6. Removed vs kept Fund scores (when raising RS floor)",
            "",
            "| band | removed_n | rem_med | rem_mean | kept_n | kept_med | kept_mean | Δmedian |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in dist_removed.itertuples():
            lines.append(
                f"| {r.band} | {r.removed_n} | {r.removed_median} | {r.removed_mean} | "
                f"{r.kept_n} | {r.kept_median} | {r.kept_mean} | {r.delta_median} |"
            )

    lines += [
        "",
        "## 7. How to read",
        "",
        "- Raising RS floor **shrinks** sets; `removed` = names that fall out of the go-like Fund list.",
        "- Largest `symdiff_n` band = where the RS knife cuts the most names — tune around there.",
        "- Cumulative distributions nest (RS≥90 ⊂ RS≥80 ⊂ …); exclusive bands show marginal RS quality.",
        "- If raising RS drops median Fund, high-RS names are not automatically higher-Fund.",
        "- Live production today uses **RS≥80** (Trend Template + fund.rs_min).",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_study(
    *,
    config: str = "config/params.yaml",
    full: bool = True,
    universe_path: str = "config/universe.yaml",
    from_stage2_tech: str | None = None,
    from_scored: str | None = None,
    thresholds: tuple[int, ...] = DEFAULT_THRESHOLDS,
    as_of: str | None = None,
    update: bool = False,
    refresh_fundamentals: bool = False,
    out_dir: Path | None = None,
) -> dict:
    params = load_params(config)
    stamp = (as_of or datetime.now(timezone.utc).strftime("%Y-%m-%d")).replace("-", "")
    out = Path(out_dir or Path(params.report_dir) / "rs_study")
    chart_dir = out / "charts"
    out.mkdir(parents=True, exist_ok=True)
    chart_dir.mkdir(parents=True, exist_ok=True)

    print("\n=== RS threshold study ===")
    if from_scored:
        scored = pd.read_csv(from_scored)
        print(f"loaded scored universe: {from_scored} (n={len(scored)})")
        if scored.empty:
            print("[오류] scored CSV가 비었습니다")
            return {"ok": False}
    else:
        if from_stage2_tech:
            stage2 = pd.read_csv(from_stage2_tech)
            print(f"loaded tech Stage2: {from_stage2_tech} (n={len(stage2)})")
        else:
            print("broad scan: Trend Template without RS gate (1–7)...")
            stage2, diagnostics = broad_stage2_tech(
                params, full=full, universe_path=universe_path, as_of=as_of, update=update
            )
            tech_path = out / f"stage2_tech_{stamp}.csv"
            diag_path = out / f"diagnostics_tech_{stamp}.csv"
            stage2.to_csv(tech_path, index=False)
            diagnostics.to_csv(diag_path, index=False)
            print(f"tech Stage2: {len(stage2)}  → {tech_path}")

        if stage2.empty:
            print("[오류] tech Stage2가 비었습니다")
            return {"ok": False}

        print(f"scoring fundamentals once for {len(stage2)} names...")
        scored = score_once(stage2, params, refresh=refresh_fundamentals)
        scored_path = out / f"fundamental_tech_{stamp}.csv"
        scored.to_csv(scored_path, index=False)
        print(f"scored: {scored_path}")

    slices = []
    for t in thresholds:
        sl = slice_at_threshold(scored, float(t))
        slices.append(sl)
        sl["fund_df"].to_csv(out / f"fundamental_rs{int(t)}_{stamp}.csv", index=False)
        (out / f"fund_tickers_rs{int(t)}_{stamp}.txt").write_text(
            ",".join(sorted(sl["fund_tickers"])) + ("\n" if sl["fund_tickers"] else "")
        )
        (out / f"fund_median_tickers_rs{int(t)}_{stamp}.txt").write_text(
            ",".join(sorted(sl["median_tickers"])) + ("\n" if sl["median_tickers"] else "")
        )
        print(
            f"  RS≥{int(t)}: stage2={sl['n_stage2']}  fund={sl['n_fund']}  "
            f"median+={sl['n_median_plus']}  ({sl['drop_summary']})"
        )

    summary = pd.DataFrame([{
        "rs_min": s["rs_min"],
        "n_stage2": s["n_stage2"],
        "n_fund": s["n_fund"],
        "n_dropped": s["n_dropped"],
        "n_median_plus": s["n_median_plus"],
        "median_fund": s["median_fund"],
    } for s in slices])
    summary.to_csv(out / f"rs_summary_{stamp}.csv", index=False)

    adj_fund = compare_adjacent(slices, "fund_tickers")
    adj_stage = compare_adjacent(slices, "stage2_tickers")
    adj_median = compare_adjacent(slices, "median_tickers")
    adj_fund.to_csv(out / f"rs_adjacent_fund_{stamp}.csv", index=False)
    adj_stage.to_csv(out / f"rs_adjacent_stage2_{stamp}.csv", index=False)
    adj_median.to_csv(out / f"rs_adjacent_median_{stamp}.csv", index=False)

    by_t = {int(s["rs_min"]): s for s in slices}
    focus = {
        "n_stage_70": by_t.get(70, {}).get("n_stage2", 0),
        "n_stage_80": by_t.get(80, {}).get("n_stage2", 0),
        "n_fund_70": by_t.get(70, {}).get("n_fund", 0),
        "n_fund_80": by_t.get(80, {}).get("n_fund", 0),
        "fund_removed_n": len(by_t[70]["fund_tickers"] - by_t[80]["fund_tickers"]) if 70 in by_t and 80 in by_t else 0,
        "fund_removed": ",".join(sorted(by_t[70]["fund_tickers"] - by_t[80]["fund_tickers"])) if 70 in by_t and 80 in by_t else "",
        "fund_only_70": ",".join(sorted(by_t[70]["fund_tickers"] - by_t[80]["fund_tickers"])) if 70 in by_t and 80 in by_t else "",
    }

    dist_cum = fund_dist_cumulative(slices)
    dist_excl = fund_dist_exclusive(scored, thresholds)
    dist_removed = fund_dist_removed_on_raise(slices)
    dist_cum.to_csv(out / f"rs_fund_dist_cumulative_{stamp}.csv", index=False)
    dist_excl.to_csv(out / f"rs_fund_dist_exclusive_{stamp}.csv", index=False)
    dist_removed.to_csv(out / f"rs_fund_dist_removed_{stamp}.csv", index=False)

    charts = [
        plot_counts(summary, chart_dir / f"rs_counts_{stamp}.png"),
        plot_band_churn(adj_fund, chart_dir / f"rs_churn_fund_{stamp}.png",
                        title="Fund 통과 집합 — RS 상향 시 변화"),
        plot_band_churn(adj_stage, chart_dir / f"rs_churn_stage2_{stamp}.png",
                        title="Stage2 집합 — RS 상향 시 변화"),
        plot_fund_box(slices, scored, thresholds,
                      chart_dir / f"rs_fund_box_{stamp}.png"),
        plot_fund_hist_overlay(slices, chart_dir / f"rs_fund_hist_{stamp}.png"),
        plot_fund_centiles(dist_cum, chart_dir / f"rs_fund_centiles_{stamp}.png"),
        plot_removed_vs_kept(dist_removed, chart_dir / f"rs_fund_removed_vs_kept_{stamp}.png"),
    ]

    md = write_markdown(
        out / f"rs_threshold_study_{stamp}.md",
        stamp=stamp,
        thresholds=list(thresholds),
        summary=summary,
        adj_fund=adj_fund,
        adj_stage=adj_stage,
        adj_median=adj_median,
        focus_70_80=focus,
        dist_cum=dist_cum,
        dist_excl=dist_excl,
        dist_removed=dist_removed,
    )
    docs = Path("docs") / f"rs_threshold_study_{stamp}.md"
    docs.write_text(md.read_text(encoding="utf-8"), encoding="utf-8")

    published = publish_many([
        md, *charts,
        out / f"rs_summary_{stamp}.csv",
        out / f"rs_adjacent_fund_{stamp}.csv",
        out / f"rs_fund_dist_cumulative_{stamp}.csv",
        out / f"rs_fund_dist_exclusive_{stamp}.csv",
        out / f"rs_fund_dist_removed_{stamp}.csv",
    ])

    print("\n=== Adjacent Fund churn ===")
    print(adj_fund[["band", "n_lo", "n_hi", "removed_n", "symdiff_n", "jaccard"]].to_string(index=False))
    print("\n=== Fund score distribution (cumulative) ===")
    print(dist_cum[["label", "n", "mean", "median", "p25", "p75", "share_ge_50"]].to_string(index=False))
    print("\n=== Fund score distribution (exclusive) ===")
    if not dist_excl.empty:
        print(dist_excl[["label", "n", "mean", "median", "p25", "p75", "share_ge_50"]].to_string(index=False))
    print("\n=== Removed vs kept Fund (raise RS) ===")
    print(dist_removed[["band", "removed_n", "removed_median", "kept_n", "kept_median", "delta_median"]].to_string(index=False))
    if focus["fund_removed"]:
        print(f"\n70→80 Fund 탈락: {focus['fund_removed']}")
    print(f"\nreport: {md}")
    print(f"docs:   {docs}")
    if published:
        print(f"artifacts: {len(published)} files")
    return {
        "ok": True,
        "summary": summary,
        "adj_fund": adj_fund,
        "dist_cum": dist_cum,
        "dist_excl": dist_excl,
        "dist_removed": dist_removed,
        "focus_70_80": focus,
        "report": md,
        "docs": docs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RS threshold sweep (Stage2→Fund)")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--full", action="store_true", help="full Nasdaq scan (default if no --universe)")
    parser.add_argument("--universe", default="config/universe.yaml")
    parser.add_argument("--from-stage2-tech", default=None, help="reuse prior tech Stage2 CSV")
    parser.add_argument("--from-scored", default=None, help="reuse scored fundamental_tech CSV (skip rescore)")
    parser.add_argument("--thresholds", default="50,60,70,80,90", help="comma-separated RS floors")
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--no-update", action="store_true", default=True)
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--refresh-fundamentals", action="store_true")
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    thresholds = tuple(int(x) for x in args.thresholds.split(",") if x.strip())
    full = args.full or (args.from_stage2_tech is None and args.from_scored is None)
    run_study(
        config=args.config,
        full=full,
        universe_path=args.universe,
        from_stage2_tech=args.from_stage2_tech,
        from_scored=args.from_scored,
        thresholds=thresholds,
        as_of=args.as_of,
        update=bool(args.update),
        refresh_fundamentals=args.refresh_fundamentals,
        out_dir=Path(args.out_dir) if args.out_dir else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
