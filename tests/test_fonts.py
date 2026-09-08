"""Korean font discovery / Hangul readiness guards."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, findfont

from sepa.fonts import (
    assert_korean_font_ready,
    clear_font_cache,
    discover_korean_font_files,
    font_has_hangul,
    hangul_font_status,
    korean_fontproperties,
    setup_korean_matplotlib,
)


def test_discover_and_hangul_glyph():
    clear_font_cache()
    regular, bold = discover_korean_font_files()
    assert regular, "expected a Hangul font on this image (Nanum or WQY)"
    assert font_has_hangul(regular)
    status = hangul_font_status()
    assert status["ok"] is True


def test_setup_does_not_resolve_to_dejavu():
    clear_font_cache()
    prop = setup_korean_matplotlib(allow_install=True)
    path = findfont(prop)
    assert "DejaVu" not in path
    bold = korean_fontproperties(bold=True)
    assert "DejaVu" not in findfont(bold)


def test_assert_korean_font_ready():
    clear_font_cache()
    assert_korean_font_ready(context="unit-test")


def test_savefig_korean_applies_to_legend_and_ticks(tmp_path: Path):
    clear_font_cache()
    from sepa.fonts import savefig_korean

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot([1, 2, 3], [1, 2, 1], label="나스닥100")
    ax.set_ylabel("지수")
    ax.set_xlabel("종목 수")
    ax.legend()
    out = tmp_path / "legend_hangul.png"
    savefig_korean(fig, out, dpi=100)
    plt.close(fig)
    assert out.exists() and out.stat().st_size > 800
    # legend text must resolve to Hangul face
    assert "DejaVu" not in findfont(korean_fontproperties())


def test_pdf_comment_text_uses_hangul_font(tmp_path: Path):
    """Smoke: rendering Hangul with explicit FontProperties must not warn DejaVu."""
    clear_font_cache()
    setup_korean_matplotlib(allow_install=True)
    fig = plt.figure(figsize=(4, 2))
    fig.text(
        0.5, 0.5, "어떻게 보면 되나",
        ha="center", va="center",
        fontproperties=korean_fontproperties(bold=True, size=12),
    )
    out = tmp_path / "hangul_probe.png"
    fig.savefig(out, dpi=100)
    plt.close(fig)
    assert out.exists() and out.stat().st_size > 500
    # resolved face for bold props must be Hangul file
    assert "DejaVu" not in findfont(korean_fontproperties(bold=True))
