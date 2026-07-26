"""Tests for model-metric charts and lean anal PDF collect order."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd

from sepa.anal_report import collect_anal_chart_paths
from sepa.model_metrics import (
    compute_rank_stability,
    plot_data_coverage,
    plot_factor_decomposition,
    plot_factor_distributions,
    plot_rank_stability,
    plot_rs_factor_scatter_matrix,
    run_model_metrics,
)


def _sample_df(n: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "ticker": [f"T{i:02d}" for i in range(n)],
            "fund_score": rng.uniform(5, 95, n),
            "rs_rank": rng.uniform(80, 99, n),
            "s_surprise": rng.uniform(0, 47, n),
            "b_eps_dyoy": rng.uniform(0, 14, n),
            "d_sales_dyoy": rng.uniform(0, 14, n),
            "e_opm_delta": rng.uniform(0, 25, n),
            "eps_surprise_pct": rng.uniform(-5, 40, n),
            "margin_source": rng.choice(["opm", "npm", "none"], n),
            "eps_accel_n": rng.integers(0, 5, n),
            "sales_accel_n": rng.integers(0, 5, n),
            "margin_n": rng.integers(0, 5, n),
            "market_cap": rng.uniform(1e9, 5e10, n),
            "primary_tag": rng.choice(["반도체", "바이오", "소프트웨어"], n),
            "close": rng.uniform(10, 200, n),
        }
    )


def test_plot_factor_charts(tmp_path: Path):
    df = _sample_df()
    p1 = plot_factor_decomposition(df, tmp_path / "decomp.png", top_n=15)
    p2 = plot_factor_distributions(df, tmp_path / "dist.png")
    p3 = plot_rs_factor_scatter_matrix(df, tmp_path / "matrix.png")
    p7 = plot_data_coverage(df, tmp_path / "cov.png")
    assert p1 and p1.exists() and p1.stat().st_size > 500
    assert p2 and p2.exists()
    assert p3 and p3.exists()
    assert p7 and p7.exists()


def test_rank_stability(tmp_path: Path):
    for i, stamp in enumerate(["20260720", "20260721", "20260722"]):
        df = _sample_df(30)
        # shuffle scores a bit each day
        df["fund_score"] = df["fund_score"] * (0.9 + 0.05 * i)
        df.to_csv(tmp_path / f"fundamental_{stamp}.csv", index=False)
    stats = compute_rank_stability(tmp_path, current_stamp="20260722", top_n=10)
    assert len(stats) == 2
    assert "spearman" in stats.columns
    p = plot_rank_stability(tmp_path, tmp_path / "stab.png", current_stamp="20260722", top_n=10)
    assert p and p.exists()


def test_run_model_metrics_partial(tmp_path: Path):
    df = _sample_df()
    # two fund snapshots for stability; quantile may skip without prices
    for stamp in ["20260724", "20260725"]:
        df.to_csv(tmp_path / f"fundamental_{stamp}.csv", index=False)
    charts = tmp_path / "charts"
    out = run_model_metrics(
        df,
        chart_dir=charts,
        stamp="20260725",
        report_dir=tmp_path,
        cache_dir=tmp_path / "raw",
        as_of="2026-07-25",
    )
    assert out["ok"]
    # at least decomp/dist/matrix/stability/coverage (attrib/quantile need prices)
    names = {p.name for p in out["charts"]}
    assert "model_factor_decomp_20260725.png" in names
    assert "model_factor_dist_20260725.png" in names
    assert "model_data_coverage_20260725.png" in names
    assert "model_rank_stability_20260725.png" in names


def test_collect_anal_chart_paths_lean(tmp_path: Path):
    charts = tmp_path / "charts"
    charts.mkdir()
    keep = [
        "analyze_scatter_20260725.png",
        "analyze_fund_hist_20260725.png",
        "sector_share_lines_n_all_20260725.png",
        "sector_share_all_vs_fundhi_20260725.png",
        "sepatop_20260725.png",
        "sepatop_relative_20260725.png",
        "model_factor_decomp_20260725.png",
        "model_data_coverage_20260725.png",
    ]
    drop = [
        "analyze_sectors_20260725.png",
        "analyze_mcap_hist_20260725.png",
        "sector_share_lines_n_fundhi_20260725.png",
        "sector_share_heatmap_all_20260725.png",
        "sector_share_vs_week_all_20260725.png",
    ]
    for name in keep + drop:
        fig, ax = plt.subplots(figsize=(2, 1))
        ax.plot([0, 1], [0, 1])
        fig.savefig(charts / name, dpi=40)
        plt.close(fig)

    ordered = collect_anal_chart_paths(chart_dir=charts, stamp="20260725")
    names = [p.name for p in ordered]
    assert names[0] == "analyze_scatter_20260725.png"
    assert "model_factor_decomp_20260725.png" in names
    assert "analyze_sectors_20260725.png" not in names
    assert "analyze_mcap_hist_20260725.png" not in names
    assert "sector_share_heatmap_all_20260725.png" not in names
    assert "sector_share_lines_n_fundhi_20260725.png" not in names
