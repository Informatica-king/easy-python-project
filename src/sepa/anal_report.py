"""Bundle SEPA analyze charts for download — PDF + Android-friendly ZIP/PNG.

Android Cursor app often cannot download PDF artifacts, so we also publish:
  - analyze_report_YYYYMMDD.zip  (all chart PNGs)
  - analyze_report_YYYYMMDD_boardNN.png  (2 charts per page, inline-viewable)
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from PIL import Image  # noqa: E402

from sepa.artifacts import publish, publish_many

logger = logging.getLogger(__name__)

BOARD_CHARTS_PER_PAGE = 2


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
        "Android: use .zip or board*.png artifacts (PDF may not download)",
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
    ordered: list[Path] = []
    seen: set[str] = set()
    for name in patterns:
        p = chart_dir / name
        if not p.exists():
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


def build_anal_zip(
    image_paths: list[Path],
    out_path: Path,
) -> Path | None:
    """Zip all chart PNGs for Android/desktop download."""
    images = [Path(p) for p in image_paths if Path(p).exists()]
    if not images:
        return None
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i, img in enumerate(images, start=1):
            zf.write(img, arcname=f"{i:02d}_{img.name}")
    publish(out_path)
    logger.info("anal ZIP published: %s (%d files)", out_path, len(images))
    return out_path


def _fit_width(img: Image.Image, width: int) -> Image.Image:
    if img.width == width:
        return img.convert("RGB")
    ratio = width / img.width
    h = max(1, int(img.height * ratio))
    return img.convert("RGB").resize((width, h), Image.Resampling.LANCZOS)


def build_anal_png_boards(
    image_paths: list[Path],
    out_dir: Path,
    *,
    stamp: str,
    charts_per_page: int = BOARD_CHARTS_PER_PAGE,
    page_width: int = 1400,
) -> list[Path]:
    """Stack charts into vertical PNG boards (Android-viewable Artifacts)."""
    images = [Path(p) for p in image_paths if Path(p).exists()]
    if not images:
        return []
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    boards: list[Path] = []
    # cover board
    cover = Image.new("RGB", (page_width, 480), (250, 250, 248))
    # simple cover via matplotlib → temp then paste is heavy; use PIL text-less cover
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(cover)
    try:
        font_lg = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 42)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 24)
    except Exception:  # noqa: BLE001
        font_lg = ImageFont.load_default()
        font_sm = font_lg
    title = f"SEPA Analyze Report  {stamp}"
    draw.text((page_width // 2, 180), title, fill=(30, 30, 30), font=font_lg, anchor="mm")
    draw.text(
        (page_width // 2, 260),
        f"{len(images)} charts  ·  Android PNG board pack",
        fill=(90, 90, 90),
        font=font_sm,
        anchor="mm",
    )
    cover_path = out_dir / f"analyze_report_{stamp}_board00_cover.png"
    cover.save(cover_path, optimize=True)
    boards.append(cover_path)

    chunks = [
        images[i : i + charts_per_page]
        for i in range(0, len(images), charts_per_page)
    ]
    for bi, chunk in enumerate(chunks, start=1):
        fitted = [_fit_width(Image.open(p), page_width - 40) for p in chunk]
        gap = 24
        label_h = 36
        total_h = sum(im.height + label_h + gap for im in fitted) + 40
        canvas = Image.new("RGB", (page_width, total_h), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        y = 20
        for src, im in zip(chunk, fitted):
            draw.text((20, y), src.name, fill=(80, 80, 80), font=font_sm)
            y += label_h
            canvas.paste(im, (20, y))
            y += im.height + gap
        out = out_dir / f"analyze_report_{stamp}_board{bi:02d}.png"
        canvas.save(out, optimize=True)
        boards.append(out)

    publish_many(boards)
    return boards


def build_anal_pack(
    image_paths: list[Path],
    *,
    stamp: str,
    out_dir: Path,
) -> dict:
    """Build PDF + ZIP + PNG boards. Returns paths dict."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    images = [Path(p) for p in image_paths if Path(p).exists()]
    result: dict = {"ok": bool(images), "n_charts": len(images)}
    if not images:
        return result

    pdf = build_anal_pdf(images, out_dir / f"analyze_report_{stamp}.pdf", stamp=stamp)
    zpath = build_anal_zip(images, out_dir / f"analyze_report_{stamp}.zip")
    boards = build_anal_png_boards(images, out_dir, stamp=stamp)
    result.update({"pdf": pdf, "zip": zpath, "boards": boards})
    return result
