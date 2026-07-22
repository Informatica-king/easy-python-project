"""Unit tests for econ news helpers (no network for tag/mood)."""

from sepa.econ_news_data import BarSnap, _tag_sectors, infer_mood


def test_tag_semiconductor_keywords():
    tags = _tag_sectors("Micron and Nvidia chip rally on HBM demand")
    assert "반도체" in tags


def test_tag_fed_financial():
    tags = _tag_sectors("Fed signals possible rate cut as Treasury yields fall")
    assert "금융" in tags


def _bar(t, name, chg, vol_ratio=1.0):
    return BarSnap(t, name, 100, 99, chg, 1e6, 1e6, vol_ratio, 101, 98)


def test_mood_risk_on():
    indices = [_bar("SPY", "S&P", 0.01), _bar("QQQ", "NDX", 0.012), _bar("^VIX", "VIX", -0.08)]
    sectors = [_bar("XLK", "기술", 0.02), _bar("XLU", "유틸", -0.005)]
    mood, bullets = infer_mood(indices, sectors)
    assert "위험선호" in mood
    assert bullets
