"""Korean font discovery and matplotlib setup for SEPA charts/PDF.

Cloud VMs often lack Nanum fonts; without a CJK face matplotlib falls back to
DejaVu Sans and Hangul becomes tofu (□). This module:

1. Finds a usable Hangul TTF/TTC (Nanum preferred, then WenQuanYi / Noto)
2. Registers it with matplotlib and sets ``font.family``
3. Exposes regular/bold ``FontProperties`` for explicit ``fig.text(..., fontproperties=)``
4. Can attempt ``apt-get install fonts-nanum`` when missing
5. Guards PDF generation so missing Hangul fonts fail loudly instead of shipping broken PDFs
"""

from __future__ import annotations

import glob
import logging
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.font_manager import FontProperties

logger = logging.getLogger(__name__)

# Ordered preference: Korean-first, then broad CJK fallbacks already common on Ubuntu.
_FONT_CANDIDATES: tuple[tuple[str, str], ...] = (
    # (regular glob/path, bold glob/path-or-empty)
    (
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf",
    ),
    (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ),
    (
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    ),
    (
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "",  # no separate bold file
    ),
)

_HANGUL_PROBE = "한글테스트"


class KoreanFontError(RuntimeError):
    """Raised when no Hangul-capable font is available for charts/PDF."""


def _exists(path: str) -> bool:
    return bool(path) and Path(path).is_file()


def discover_korean_font_files() -> tuple[str, str | None]:
    """Return ``(regular_path, bold_path_or_None)`` for the best available Hangul font."""
    for regular, bold in _FONT_CANDIDATES:
        if _exists(regular):
            bold_path = bold if _exists(bold) else None
            return regular, bold_path
    # last-resort glob for nanum variants
    matches = sorted(glob.glob("/usr/share/fonts/truetype/nanum/NanumGothic*.ttf"))
    if matches:
        regular = next((p for p in matches if "Bold" not in Path(p).name), matches[0])
        bold = next((p for p in matches if "Bold" in Path(p).name), None)
        return regular, bold
    return "", None


def try_install_nanum_fonts() -> bool:
    """Best-effort apt install of fonts-nanum (needs sudo). Returns True if fonts appear."""
    regular, _ = discover_korean_font_files()
    if regular and "nanum" in regular.lower():
        return True
    if os.environ.get("SEPA_SKIP_FONT_INSTALL", "").strip() in {"1", "true", "yes"}:
        return False
    apt = shutil.which("apt-get")
    if apt is None:
        return False
    sudo = shutil.which("sudo")
    cmd_prefix = [sudo, "-n"] if sudo else []
    try:
        subprocess.run(
            [*cmd_prefix, apt, "install", "-y", "fonts-nanum", "fonts-nanum-coding"],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("fonts-nanum install attempt failed: %s", exc)
        return False
    # refresh fontconfig cache if available
    fc = shutil.which("fc-cache")
    if fc:
        subprocess.run([fc, "-f"], check=False, capture_output=True, timeout=60)
    regular, _ = discover_korean_font_files()
    return bool(regular)


def font_has_hangul(path: str, sample: str = _HANGUL_PROBE) -> bool:
    """True if the font file can load Hangul codepoints (not tofu fallback)."""
    if not _exists(path):
        return False
    try:
        from matplotlib.ft2font import FT2Font

        face = FT2Font(str(path))
        for ch in sample:
            face.load_char(ord(ch))
        return True
    except Exception:  # noqa: BLE001
        return False


def _invalidate_matplotlib_font_cache() -> None:
    """Drop on-disk fontlist cache so newly installed Nanum is visible."""
    try:
        import matplotlib as mpl

        cache_dir = Path(mpl.get_cachedir())
        for p in cache_dir.glob("fontlist-*.json"):
            try:
                p.unlink()
            except OSError:
                pass
        # Rebuild in-process manager (API differs slightly across mpl versions).
        if hasattr(fm, "_load_fontmanager"):
            fm.fontManager = fm._load_fontmanager(try_read_cache=False)
        else:
            fm.fontManager = fm.FontManager()
    except Exception as exc:  # noqa: BLE001
        logger.debug("font cache invalidate skipped: %s", exc)


@lru_cache(maxsize=1)
def _resolved() -> tuple[str, str | None, str]:
    """Cached ``(regular, bold, family_name)`` after registration."""
    regular, bold = discover_korean_font_files()
    if not regular:
        return "", None, ""
    _invalidate_matplotlib_font_cache()
    fm.fontManager.addfont(regular)
    if bold:
        fm.fontManager.addfont(bold)
    family = FontProperties(fname=regular).get_name()
    return regular, bold, family


def clear_font_cache() -> None:
    _resolved.cache_clear()


def ensure_korean_font(*, allow_install: bool = True) -> tuple[str, str | None, str]:
    """Ensure a Hangul font is available; optionally apt-install Nanum.

    Returns ``(regular_path, bold_path, family_name)``.
    Raises ``KoreanFontError`` if still unavailable / Hangul missing.
    """
    clear_font_cache()
    regular, bold, family = _resolved()
    if (not regular or not font_has_hangul(regular)) and allow_install:
        if try_install_nanum_fonts():
            clear_font_cache()
            _invalidate_matplotlib_font_cache()
            regular, bold, family = _resolved()
    if not regular:
        raise KoreanFontError(
            "한글 폰트가 없습니다. 예: `sudo apt-get install -y fonts-nanum` "
            "(또는 WenQuanYi / Noto CJK). PDF/차트 한글이 □로 깨집니다."
        )
    if not font_has_hangul(regular):
        raise KoreanFontError(
            f"폰트는 있으나 한글 글리프 없음: {regular}"
        )
    return regular, bold, family


def setup_korean_matplotlib(*, allow_install: bool = True) -> FontProperties:
    """Register Hangul font and set matplotlib rcParams for axes/legends/ticks.

    Uses the ``sans-serif`` family chain (Nanum first) so legend labels and
    tick labels pick up Hangul — setting ``font.family='NanumGothic'`` alone
    still lets some artists fall back to DejaVu when weight/style differs.
    """
    regular, bold, family = ensure_korean_font(allow_install=allow_install)
    # Primary: sans-serif chain (legends, ticklabels, pandas plots).
    plt.rcParams["font.family"] = "sans-serif"
    sans = [family]
    for name in list(plt.rcParams.get("font.sans-serif", [])):
        if name and name not in sans:
            sans.append(name)
    # Keep DejaVu as last-resort for missing glyphs (symbols), never first.
    if "DejaVu Sans" not in sans:
        sans.append("DejaVu Sans")
    plt.rcParams["font.sans-serif"] = sans
    plt.rcParams["axes.unicode_minus"] = False
    # Also expose the concrete family for code that sets family=NanumGothic.
    if family:
        plt.rcParams["font.serif"] = list(plt.rcParams.get("font.serif", []))
    return FontProperties(fname=regular)


def korean_fontproperties(*, bold: bool = False, size: float | None = None) -> FontProperties:
    """FontProperties pointed at the Hangul TTF (use for fig.text to avoid DejaVu bold fallback)."""
    regular, bold_path, _family = ensure_korean_font(allow_install=True)
    path = bold_path if bold and bold_path else regular
    props = FontProperties(fname=path)
    if size is not None:
        props.set_size(size)
    return props


def finalize_korean_figure(fig) -> None:
    """Force Hangul FontProperties onto titles, axis labels, ticks, and legends.

    Call immediately before ``savefig`` so baked chart PNGs cannot ship tofu
    even if an artist ignored rcParams.
    """
    setup_korean_matplotlib(allow_install=True)
    fp = korean_fontproperties()
    for ax in fig.get_axes():
        for label in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            label.set_fontproperties(fp)
        if ax.xaxis.label.get_text():
            ax.xaxis.label.set_fontproperties(fp)
        if ax.yaxis.label.get_text():
            ax.yaxis.label.set_fontproperties(fp)
        if ax.title.get_text():
            ax.title.set_fontproperties(fp)
        for text in getattr(ax, "texts", []):
            text.set_fontproperties(fp)
        leg = ax.get_legend()
        if leg is not None:
            for text in leg.get_texts():
                text.set_fontproperties(fp)
            title = leg.get_title()
            if title is not None and title.get_text():
                title.set_fontproperties(fp)
    for text in list(fig.texts):
        # Keep PDF page guides that already set fontproperties; still safe to reset.
        text.set_fontproperties(fp)


def savefig_korean(fig, path: str | Path, **kwargs):
    """``fig.savefig`` after applying Hangul fonts to all text artists."""
    finalize_korean_figure(fig)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, **kwargs)
    return path


def assert_korean_font_ready(*, context: str = "chart/PDF") -> None:
    """Guard used by anal PDF / go — fail fast instead of shipping tofu Hangul."""
    regular, bold, family = ensure_korean_font(allow_install=True)
    # Bold path often triggers DejaVu fallback when family name is used with weight=bold
    # without a registered bold face — verify findfont does not resolve to DejaVu.
    found = fm.findfont(FontProperties(fname=regular))
    if "DejaVu" in found:
        raise KoreanFontError(
            f"{context}: Hangul font resolved to DejaVu ({found}). "
            f"expected {regular} ({family})"
        )
    if bold:
        found_b = fm.findfont(FontProperties(fname=bold))
        if "DejaVu" in found_b:
            raise KoreanFontError(
                f"{context}: Hangul bold resolved to DejaVu ({found_b}). expected {bold}"
            )
    logger.info("Korean font ready for %s: %s (%s)", context, family, regular)


def hangul_font_status() -> dict:
    """Diagnostic snapshot for logs / tests."""
    regular, bold = discover_korean_font_files()
    ok = bool(regular) and font_has_hangul(regular)
    return {
        "ok": ok,
        "regular": regular or None,
        "bold": bold,
        "family": FontProperties(fname=regular).get_name() if regular else None,
        "has_hangul": font_has_hangul(regular) if regular else False,
    }
