"""Tests for sector tagging and analyze helpers (no network)."""

import pandas as pd

from sepa.analyze import (
    classify_tags,
    fund_highlight_tickers,
    fund_score_bin_counts,
    market_cap_bin_counts,
    tag_counts,
)


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


def test_fund_score_bin_counts():
    s = pd.Series([0, 0, 12, 25, 41, 55, 67.5])
    c = fund_score_bin_counts(s)
    assert int(c["0–9"]) == 2
    assert int(c["10–19"]) == 1
    assert int(c["40–49"]) == 1
    assert int(c["60–69"]) == 1


def test_market_cap_bin_counts():
    caps = pd.Series([5e8, 2e9, 7e9, 20e9, 80e9, None])
    c = market_cap_bin_counts(caps)
    assert int(c["$1B 미만"]) == 1
    assert int(c["$1B–5B"]) == 1
    assert int(c["$5B–10B"]) == 1
    assert int(c["$10B–50B"]) == 1
    assert int(c["$50B+"]) == 1


def test_fund_highlight_tickers_comma_order():
    df = pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D"],
            "fund_score": [50, 39.9, 67, 40],
            "rs_rank": [90, 95, 80, 88],
        }
    )
    assert fund_highlight_tickers(df, 40) == ["C", "A", "D"]
