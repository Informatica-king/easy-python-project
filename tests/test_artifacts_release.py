"""Tests for GitHub Release PDF publish helpers (offline; no network)."""

from sepa.artifacts import compact_stamp, release_download_url


def test_compact_stamp():
    assert compact_stamp("2026-08-07") == "20260807"
    assert compact_stamp("20260807") == "20260807"


def test_release_download_url_deep_and_portfolio():
    repo = "Informatica-king/easy-python-project"
    deep = release_download_url(repo, "sepa-deep-20260807", "NASDAQ_Deep_Analysis_2026-08-07.pdf")
    assert deep.endswith("/releases/download/sepa-deep-20260807/NASDAQ_Deep_Analysis_2026-08-07.pdf")
    port = release_download_url(repo, "sepa-portfolio-ops-20260806", "Portfolio_Ops_2026-08-06.pdf")
    assert "sepa-portfolio-ops-20260806" in port
    assert port.startswith("https://github.com/")
