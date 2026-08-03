"""Bundle SEPA analyze charts for download — PDF + Android-friendly ZIP/PNG.

Android Cursor app often cannot download PDF artifacts, so we also publish:
  - analyze_report_YYYYMMDD.zip  (all chart PNGs)
  - analyze_report_YYYYMMDD_boardNN.png  (2 charts per page, inline-viewable)
"""

from __future__ import annotations

import glob
import logging
import re
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from PIL import Image  # noqa: E402

from sepa.artifacts import publish, publish_many

logger = logging.getLogger(__name__)

BOARD_CHARTS_PER_PAGE = 2

# Newly added model-metric pages: (한글 제목, 보는 법 한 줄)
MODEL_PAGE_COMMENTS: dict[str, tuple[str, str]] = {
    "model_factor_decomp": (
        "1. 팩터 분해 (S/B/D/E)",
        "상위 종목 Fund 점수가 어떤 팩터에서 쌓였는지 봅니다. 파란(S)=서프라이즈, 보라(B)=EPS가속도, "
        "주황(D)=매출가속도, 빨강(E)=마진변화. 한 색이 과하면 그 요인 의존도가 큽니다.",
    ),
    "model_factor_dist": (
        "2. 팩터 점수 분포",
        "네 팩터 점수가 후보군에서 어떻게 퍼져 있는지 봅니다. 한쪽(0 또는 만점)에 몰리면 "
        "변별력이 약하고, 평균선 주변에 고르게 퍼지면 점수 체계가 살아 있는 상태입니다.",
    ),
    "model_rs_factor_matrix": (
        "3. RS × 팩터 산점도",
        "가로=상대강도(RS), 세로=각 팩터/종합점수. ρ(스피어만)가 +면 RS 강종목이 해당 팩터도 "
        "높은 편. ρ≈0이면 모멘텀과 펀더멘털이 따로 움직입니다.",
    ),
    "model_rank_stability": (
        "4. 순위 안정성 / 교체율",
        "위: 전일 대비 점수 순위 상관(Spearman)과 유니버스 겹침(Jaccard). "
        "아래: Top-N 잔류 vs 교체. 상관이 급락·교체가 뛰면 그 날 스크리닝/데이터 변화가 큽니다.",
    ),
    "model_sepatop_attrib": (
        "5. sepaTop 기여도 분해",
        "최근 구간의 지수 수익을 시총가중×수익률로 나눕니다. 왼쪽=종목, 오른쪽=섹터. "
        "초록(+)/빨강(−)이 지수를 끌어올린·깎은 축입니다.",
    ),
    "model_quantile_fwd": (
        "6. Fund 분위별 선행수익률",
        "Q4=Fund 상위. 왼쪽=절대수익, 오른쪽=나스닥/QQQ 대비 초과수익. "
        "Q4가 Q1보다 꾸준히 높으면 점수에 단기 예측력이 있다는 신호입니다.",
    ),
    "model_data_coverage": (
        "7. 데이터 커버리지",
        "위: 서프라이즈·마진소스(OPM/NPM)·가속도 깊이. 아래(v2.1): B/D/E quality 분포 "
        "(0=미채점·게이트, partial=페널티, 1.0=신뢰). OPM·quality 1.0 비중이 늘수록 E/B/D가 믿을 만합니다.",
    ),
}


def _setup_korean_font() -> None:
    for path in glob.glob("/usr/share/fonts/truetype/nanum/NanumGothic*.ttf"):
        fm.fontManager.addfont(path)
    if any(f.name == "NanumGothic" for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = "NanumGothic"
        plt.rcParams["axes.unicode_minus"] = False


def chart_page_comment(image_path: Path | str) -> tuple[str, str] | None:
    """Return (title, how-to-read) for newly added model pages, else None."""
    name = Path(image_path).name
    stem = re.sub(r"_\d{8}$", "", Path(name).stem)
    return MODEL_PAGE_COMMENTS.get(stem)


def _cover_page(pdf: PdfPages, *, title: str, subtitle: str, n_pages: int) -> None:
    _setup_korean_font()
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


def _wrap_comment(text: str, width: int = 52) -> str:
    """Wrap by character count (Korean has few spaces)."""
    lines: list[str] = []
    remaining = text.strip()
    while len(remaining) > width:
        cut = width
        # prefer break near punctuation / space in the last 12 chars
        window = remaining[:width]
        for i, ch in enumerate(reversed(window[-12:]), start=1):
            if ch in " .，。、;；/·":
                cut = width - i + 1
                break
        lines.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        lines.append(remaining)
    return "\n".join(lines)


def _image_page(pdf: PdfPages, image_path: Path) -> bool:
    _setup_korean_font()
    try:
        img = mpimg.imread(str(image_path))
    except Exception as exc:  # noqa: BLE001
        logger.warning("skip image %s: %s", image_path, exc)
        return False

    comment = chart_page_comment(image_path)
    page_w, page_h = 11.0, 8.5
    fig = plt.figure(figsize=(page_w, page_h))

    if comment:
        title, body = comment
        # Leave bottom band for Korean guide
        ax = fig.add_axes([0.04, 0.22, 0.92, 0.72])
        ax.imshow(img)
        ax.axis("off")
        fig.text(
            0.5, 0.965, title,
            ha="center", va="top", fontsize=13, fontweight="bold", color="#1a1a1a",
        )
        fig.text(
            0.05, 0.16, "어떻게 보면 되나",
            ha="left", va="top", fontsize=9, color="#2E86AB", fontweight="bold",
        )
        fig.text(
            0.05, 0.13, _wrap_comment(body, width=58),
            ha="left", va="top", fontsize=9.5, color="#333",
            linespacing=1.35,
        )
        fig.text(
            0.98, 0.02, image_path.name,
            ha="right", va="bottom", fontsize=7, color="#999",
        )
    else:
        h, w = img.shape[:2]
        aspect = w / max(h, 1)
        if aspect >= page_w / page_h:
            # wide: fit width, center vertically
            img_h = (page_w / aspect) / page_h
            y0 = (1.0 - img_h) / 2
            ax = fig.add_axes([0.03, y0, 0.94, img_h * 0.92])
        else:
            ax = fig.add_axes([0.03, 0.04, 0.94, 0.88])
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
    """Ordered lean PNG list for the anal PDF.

    Keeps core decision charts + model metrics 1–7; drops duplicate sector-share
    fundhi/delta/heatmap/week/month variants and mcap/sector bar clutter.
    """
    chart_dir = Path(chart_dir)
    patterns = [
        # Core
        f"analyze_scatter_{stamp}.png",
        f"analyze_fund_hist_{stamp}.png",
        # Sector share (lean)
        f"sector_share_lines_n_all_{stamp}.png",
        f"sector_share_all_vs_fundhi_{stamp}.png",
        # sepaTop
        f"sepatop_{stamp}.png",
        f"sepatop_relative_{stamp}.png",
        # Model metrics 1–7
        f"model_factor_decomp_{stamp}.png",
        f"model_factor_dist_{stamp}.png",
        f"model_rs_factor_matrix_{stamp}.png",
        f"model_rank_stability_{stamp}.png",
        f"model_sepatop_attrib_{stamp}.png",
        f"model_quantile_fwd_{stamp}.png",
        f"model_data_coverage_{stamp}.png",
    ]
    lean_names = set(patterns)
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
        if not pp.exists() or pp.suffix.lower() != ".png":
            continue
        # Do not re-introduce trimmed clutter via ``extra``.
        if pp.name not in lean_names and not pp.name.startswith(f"model_"):
            continue
        key = str(pp.resolve())
        if key not in seen:
            ordered.append(pp)
            seen.add(key)
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


def github_repo_slug() -> str | None:
    """Return owner/repo from gh, or None."""
    import json
    import shutil
    import subprocess

    if shutil.which("gh") is None:
        return None
    try:
        out = subprocess.check_output(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=30,
        ).strip()
        return out or None
    except Exception:  # noqa: BLE001
        try:
            raw = subprocess.check_output(
                ["gh", "repo", "view", "--json", "nameWithOwner"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            return json.loads(raw).get("nameWithOwner")
        except Exception:  # noqa: BLE001
            return None


def pdf_release_tag(stamp: str) -> str:
    return f"sepa-anal-{stamp}"


def pdf_direct_download_url(repo: str, stamp: str, pdf_name: str | None = None) -> str:
    name = pdf_name or f"analyze_report_{stamp}.pdf"
    return f"https://github.com/{repo}/releases/download/{pdf_release_tag(stamp)}/{name}"


def _release_asset_args(paths: list[Path]) -> list[str]:
    """Build ``path#name`` args for gh release create/upload."""
    args: list[str] = []
    for p in paths:
        p = Path(p)
        if p.exists() and p.is_file():
            args.append(f"{p}#{p.name}")
    return args


def publish_pdf_github_release(
    pdf_path: Path,
    *,
    stamp: str,
    repo: str | None = None,
    extra_assets: list[Path] | None = None,
) -> dict:
    """Upload PDF (+ optional analysis CSVs) to GitHub Release.

    Creates tag ``sepa-anal-YYYYMMDD`` (or re-uploads assets with --clobber).
    Extra assets keep longitudinal sepaTop membership history across VM wipes.
    """
    import shutil
    import subprocess

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return {"ok": False, "error": f"PDF missing: {pdf_path}"}
    if shutil.which("gh") is None:
        return {"ok": False, "error": "gh CLI not available"}

    repo = repo or github_repo_slug()
    if not repo:
        return {"ok": False, "error": "cannot resolve GitHub repo slug"}

    extras = [Path(p) for p in (extra_assets or []) if Path(p).exists()]
    all_assets = _release_asset_args([pdf_path, *extras])
    if not all_assets:
        return {"ok": False, "error": "no release assets to upload"}

    tag = pdf_release_tag(stamp)
    title = f"SEPA Analyze Report {stamp}"
    as_of = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}" if len(stamp) == 8 else stamp
    extra_names = ", ".join(p.name for p in extras) if extras else "(none)"
    notes = (
        f"SEPA `!sepa.anal` / `!sepa.go` pack ({as_of}).\n\n"
        f"PDF: {pdf_direct_download_url(repo, stamp, pdf_path.name)}\n"
        f"Analysis extras: {extra_names}\n"
    )

    # Create release if missing; otherwise clobber-upload assets
    view = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if view.returncode != 0:
        created = subprocess.run(
            [
                "gh", "release", "create", tag,
                *all_assets,
                "--repo", repo,
                "--title", title,
                "--notes", notes,
                "--latest=false",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if created.returncode != 0:
            return {
                "ok": False,
                "error": (created.stderr or created.stdout or "release create failed").strip(),
                "repo": repo,
                "tag": tag,
            }
    else:
        uploaded = subprocess.run(
            [
                "gh", "release", "upload", tag,
                *all_assets,
                "--repo", repo,
                "--clobber",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if uploaded.returncode != 0:
            return {
                "ok": False,
                "error": (uploaded.stderr or uploaded.stdout or "release upload failed").strip(),
                "repo": repo,
                "tag": tag,
            }
        subprocess.run(
            ["gh", "release", "edit", tag, "--repo", repo, "--notes", notes],
            capture_output=True,
            text=True,
            timeout=60,
        )

    download = pdf_direct_download_url(repo, stamp, pdf_path.name)
    page = f"https://github.com/{repo}/releases/tag/{tag}"
    return {
        "ok": True,
        "repo": repo,
        "tag": tag,
        "download_url": download,
        "release_url": page,
        "pdf_name": pdf_path.name,
        "extra_assets": [p.name for p in extras],
    }
