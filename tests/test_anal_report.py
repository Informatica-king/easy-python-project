"""Tests for analyze report packer (PDF / ZIP / PNG boards)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from sepa.anal_report import (
    build_anal_pack,
    collect_anal_chart_paths,
    pdf_direct_download_url,
    pdf_release_tag,
)


def _fake_png(path: Path, color: str = "C0") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot([0, 1], [0, 1], color=color)
    ax.set_title(path.stem)
    fig.savefig(path, dpi=80)
    plt.close(fig)


def test_build_anal_pack(tmp_path: Path):
    charts = tmp_path / "charts"
    imgs = []
    for name in [
        "analyze_sectors_20260718.png",
        "sector_share_lines_n_all_20260718.png",
        "sector_share_lines_n_fundhi_20260718.png",
        "analyze_scatter_20260718.png",
    ]:
        p = charts / name
        _fake_png(p)
        imgs.append(p)

    ordered = collect_anal_chart_paths(chart_dir=charts, stamp="20260718", extra=imgs)
    assert len(ordered) >= 3
    pack = build_anal_pack(ordered, stamp="20260718", out_dir=charts)
    assert pack["ok"]
    assert Path(pack["pdf"]).exists() and Path(pack["pdf"]).stat().st_size > 1000
    assert Path(pack["zip"]).exists() and Path(pack["zip"]).stat().st_size > 500
    assert len(pack["boards"]) >= 2
    for b in pack["boards"]:
        assert Path(b).exists() and Path(b).suffix == ".png"


def test_pdf_direct_download_url():
    assert pdf_release_tag("20260718") == "sepa-anal-20260718"
    url = pdf_direct_download_url("Informatica-king/easy-python-project", "20260718")
    assert url.endswith("/releases/download/sepa-anal-20260718/analyze_report_20260718.pdf")
