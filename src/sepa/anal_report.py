"""Bundle SEPA analyze charts into a single downloadable PDF.

Designed for mobile (Android) one-tap download via Cursor Artifacts.
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

from sepa.artifacts import publish

logger = logging.getLogger(__name__)


def _cover_page(pdf: PdfPages, *, title: str, subtitle: str, n_pages: int) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    fig.text(0.5, 0.62, title, ha="center", va="center", fontsize=22, fontweight="bold")
    fig.text(0.5, 0.52, subtitle, ha="center", va="center", fontsize=12, color="#444")
    fig.text(
        0.5, 0.40,
        f"Charts in this PDF: {n_pages}",
        ha="center", va="center", fontsize=11, color="#666",
    )
    fig.text(
        0.5, 0.28,
        "SEPA Analyze report — downloadable on mobile",
        ha="center", va="center", fontsize=10, color="#888",
    )
    pdf.savefig(fig)
    plt.close(fig)


def _image_page(pdf: PdfPages, image_path: Path) -> bool:
    try:
        img = mpimg.imread(str(image_path))
    except Exception as exc:  # noqa: BLE001
        logger.warning("skip image %s: %s", image_path, exc)
        return False
    h, w = img.shape[:2]
    # Fit on landscape letter-ish page
    page_w, page_h = 11.0, 8.5
    aspect = w / max(h, 1)
    if aspect >= page_w / page_h:
        fig_w, fig_h = page_w, page_w / aspect
    else:
        fig_h, fig_w = page_h, page_h * aspect
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.90])
    ax.imshow(img)
    ax.axis("off")
    fig.text(0.5, 0.97, image_path.name, ha="center", va="top", fontsize=8, color="#555")
    pdf.savefig(fig, dpi=140)
    plt.close(fig)
    return True


def collect_anal_chart_paths(
    *,
    chart_dir: Path,
    stamp: str,
    extra: list[Path] | None = None,
) -> list[Path]:
    """Ordered list of PNGs produced by a typical anal run for ``stamp``."""
    chart_dir = Path(chart_dir)
    patterns = [
        f"analyze_sectors_{stamp}.png",
        f"analyze_scatter_{stamp}.png",
        f"analyze_fund_hist_{stamp}.png",
        f"analyze_mcap_hist_{stamp}.png",
        f"sector_share_lines_n_all_{stamp}.png",
        f"sector_share_lines_mcap_all_{stamp}.png",
        f"sector_share_delta_first_all_{stamp}.png",
        f"sector_share_delta_prev_all_{stamp}.png",
        f"sector_share_heatmap_all_{stamp}.png",
        f"sector_share_lines_n_fundhi_{stamp}.png",
        f"sector_share_lines_mcap_fundhi_{stamp}.png",
        f"sector_share_delta_first_fundhi_{stamp}.png",
        f"sector_share_delta_prev_fundhi_{stamp}.png",
        f"sector_share_heatmap_fundhi_{stamp}.png",
        f"sector_share_all_vs_fundhi_{stamp}.png",
        f"sector_share_vs_week_all_{stamp}.png",
        f"sector_share_vs_week_mcap_all_{stamp}.png",
        f"sector_share_vs_week_fundhi_{stamp}.png",
        f"sector_share_vs_week_mcap_fundhi_{stamp}.png",
        f"sector_share_vs_month_all_{stamp}.png",
        f"sector_share_vs_month_mcap_all_{stamp}.png",
        f"sector_share_vs_month_fundhi_{stamp}.png",
        f"sector_share_vs_month_mcap_fundhi_{stamp}.png",
        f"sepatop_{stamp}.png",
        f"sepatop_relative_{stamp}.png",
    ]
    # sepatop charts live under reports/sepatop/charts
    ordered: list[Path] = []
    seen: set[str] = set()
    for name in patterns:
        p = chart_dir / name
        if not p.exists():
            # try sepatop subdir relative to chart_dir parent
            alt = chart_dir.parent / "sepatop" / "charts" / name
            p = alt if alt.exists() else p
        if p.exists() and str(p.resolve()) not in seen:
            ordered.append(p)
            seen.add(str(p.resolve()))

    for p in extra or []:
        pp = Path(p)
        if pp.exists() and pp.suffix.lower() == ".png" and str(pp.resolve()) not in seen:
            ordered.append(pp)
            seen.add(str(pp.resolve()))
    return ordered


def build_anal_pdf(
    image_paths: list[Path],
    out_path: Path,
    *,
    stamp: str,
    title: str | None = None,
) -> Path | None:
    """Write a multi-page PDF; return path or None if no images."""
    images = [Path(p) for p in image_paths if Path(p).exists()]
    if not images:
        logger.warning("build_anal_pdf: no images")
        return None

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    title = title or f"SEPA Analyze Report — {stamp}"
    subtitle = f"as of {stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}" if len(stamp) == 8 else stamp

    with PdfPages(out_path) as pdf:
        _cover_page(pdf, title=title, subtitle=subtitle, n_pages=len(images))
        for img in images:
            _image_page(pdf, img)

    published = publish(out_path)
    if published is not None:
        logger.info("anal PDF published: %s", published)
    return out_path
