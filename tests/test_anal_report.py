"""Tests for analyze PDF packer."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from sepa.anal_report import build_anal_pdf, collect_anal_chart_paths


def _fake_png(path: Path, color: str = "C0") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot([0, 1], [0, 1], color=color)
    ax.set_title(path.stem)
    fig.savefig(path, dpi=80)
    plt.close(fig)


def test_build_anal_pdf(tmp_path: Path):
    charts = tmp_path / "charts"
    imgs = []
    for name in [
        "analyze_sectors_20260718.png",
        "sector_share_lines_n_all_20260718.png",
        "sector_share_lines_n_fundhi_20260718.png",
    ]:
        p = charts / name
        _fake_png(p)
        imgs.append(p)

    ordered = collect_anal_chart_paths(chart_dir=charts, stamp="20260718", extra=imgs)
    assert len(ordered) >= 3
    out = tmp_path / "analyze_report_20260718.pdf"
    result = build_anal_pdf(ordered, out, stamp="20260718")
    assert result is not None
    assert out.exists()
    assert out.stat().st_size > 1000
