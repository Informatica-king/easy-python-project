"""Charts and file outputs for fund weight study."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd

from sepa.artifacts import publish_many

logger = logging.getLogger(__name__)


def plot_factor_bars(corr: pd.DataFrame, out_path: Path, *, title: str, value_col: str = "spearman") -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    if corr.empty or value_col not in corr.columns:
        ax.text(0.5, 0.5, "no data", ha="center")
        ax.set_axis_off()
    else:
        sub = corr.dropna(subset=[value_col]).sort_values(value_col)
        colors = ["#c0392b" if v < 0 else "#27ae60" for v in sub[value_col]]
        ax.barh(sub["factor"], sub[value_col], color=colors)
        ax.axvline(0, color="#444", lw=0.8)
        ax.set_xlabel(value_col)
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


def plot_weight_compare(weights: pd.DataFrame, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    if weights.empty:
        ax.text(0.5, 0.5, "no data", ha="center")
        ax.set_axis_off()
    else:
        sub = weights.copy()
        x = range(len(sub))
        ax.bar([i - 0.2 for i in x], sub["current_hint"], width=0.4, label="current hint", color="#7f8c8d")
        ax.bar([i + 0.2 for i in x], sub["weight"], width=0.4, label="proposed", color="#2980b9")
        ax.set_xticks(list(x))
        ax.set_xticklabels(sub["factor"], rotation=30, ha="right")
        ax.set_ylabel("weight")
        ax.set_title("Current hint vs proposed weights")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


def write_exception_draft(path: Path) -> Path:
    text = """# Fund weight study — exception rules draft

Status: draft from locked spec (2026-07-19). Pending empirical review.

## Hard excludes (applied in panel build)
- Event-window dollar volume in bottom 30%
- Missing prices / incomplete return window
- |YoY| or |QoQ| > 500% (explosion)
- ADR / ETF / non-common

## Flag for scoring exceptions (include in sample, review later)
- One-time items distorting margins (manual / heuristic flags TBD)
- Seasonal industries when using QoQ speed factors
- Sign flips (loss ↔ profit) near zero EPS base

## Bonus / non-main X
- Consecutive acceleration quarter count `n` — candidate bonus only, not main correlator
- ROE — excluded from phase-1 weight estimation; revisit as filter later

## Reverse-scoring candidates
- Any factor with stable negative Spearman (ortho) after yearly stability check
- Do not auto-invert; require explicit approval
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def save_study_outputs(
    *,
    out_dir: Path,
    panel: pd.DataFrame,
    corr: pd.DataFrame,
    chosen: pd.DataFrame,
    ortho: pd.DataFrame,
    weights: pd.DataFrame,
    yearly: pd.DataFrame,
    stamp: str,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    paths["panel"] = out_dir / f"event_panel_{stamp}.csv"
    panel.to_csv(paths["panel"], index=False)
    paths["corr"] = out_dir / f"factor_corr_{stamp}.csv"
    corr.to_csv(paths["corr"], index=False)
    paths["chosen"] = out_dir / f"factor_chosen_{stamp}.csv"
    chosen.to_csv(paths["chosen"], index=False)
    paths["ortho"] = out_dir / f"factor_ortho_corr_{stamp}.csv"
    ortho.to_csv(paths["ortho"], index=False)
    paths["weights"] = out_dir / f"weight_proposal_{stamp}.csv"
    weights.to_csv(paths["weights"], index=False)
    paths["yearly"] = out_dir / f"yearly_stability_{stamp}.csv"
    yearly.to_csv(paths["yearly"], index=False)
    paths["exceptions"] = write_exception_draft(out_dir / f"exceptions_draft_{stamp}.md")

    chart_dir = out_dir / "charts"
    paths["chart_corr"] = plot_factor_bars(
        corr, chart_dir / f"corr_spearman_{stamp}.png",
        title=f"Factor vs mkt-adj return (Spearman) — {stamp}",
        value_col="spearman",
    )
    if "spearman_ortho" in ortho.columns:
        paths["chart_ortho"] = plot_factor_bars(
            ortho.rename(columns={"spearman_ortho": "spearman"}),
            chart_dir / f"corr_ortho_{stamp}.png",
            title=f"Orthogonalized Spearman — {stamp}",
            value_col="spearman",
        )
    paths["chart_weights"] = plot_weight_compare(weights, chart_dir / f"weights_{stamp}.png")

    publish_many([p for p in paths.values() if Path(p).suffix in {".png", ".csv", ".md"}])
    return paths
