"""Tests for sector tagging and analyze helpers (no network)."""

from sepa.analyze import classify_tags, tag_counts
import pandas as pd


def test_classify_multi_tags_semiconductor():
    tags = classify_tags("Technology", "Semiconductor Equipment & Materials")
    assert "기술" in tags
    assert "반도체" in tags


def test_classify_biotech():
    tags = classify_tags("Healthcare", "Biotechnology")
    assert "헬스케어" in tags
    assert "바이오" in tags


def test_classify_software():
    tags = classify_tags("Technology", "Software - Infrastructure")
    assert "소프트웨어" in tags


def test_classify_unknown_falls_back():
    assert classify_tags(None, None) == ["기타"]


def test_tag_counts_multi_label():
    df = pd.DataFrame({"tags": ["기술|반도체", "기술|소프트웨어", "헬스케어|바이오"]})
    counts = tag_counts(df)
    assert counts["기술"] == 2
    assert counts["반도체"] == 1
    assert counts["바이오"] == 1
