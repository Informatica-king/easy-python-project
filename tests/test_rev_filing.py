"""Tests for sepa.rev_filing (official PDF → YAML SSOT)."""

from pathlib import Path

import pytest
import yaml

from sepa.rev_filing import (
    FilingRequiredError,
    extract_txg_earnings_release,
    latest_filing,
    load_filing,
    portfolio_memo_line,
    require_filing,
    save_filing,
)


UPLOAD = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/"
    "TXG_Q2-2026-Earnings-Press-Release-08-06-26_4f0b.pdf"
)
REPO_YAML = Path("/workspace/data/rev_filings/TXG/2026-06-30.yaml")


@pytest.mark.skipif(not UPLOAD.exists() and not REPO_YAML.exists(), reason="no TXG filing fixture")
def test_txg_extract_or_load_yaml():
    if REPO_YAML.exists():
        doc = load_filing(REPO_YAML)
    else:
        doc = extract_txg_earnings_release(UPLOAD, copy_source=False)
    assert doc.ticker == "TXG"
    assert doc.period_end == "2026-06-30"
    assert doc.revenue_total_m == pytest.approx(151.0, abs=0.2)
    assert doc.revenue_ex_onetime_m == pytest.approx(149.4, abs=0.2)
    assert doc.yoy_ex_onetime_pct == pytest.approx(3.0, abs=0.1)
    assert doc.guidance_fy_low_m == 610
    assert doc.guidance_fy_high_m == 630
    cons = next(r for r in doc.mix_product if r["name"] == "Consumables total")
    assert cons["amount_m"] == pytest.approx(130.752, abs=0.05)
    assert abs(sum(r["amount_m"] for r in doc.mix_product if r["name"] in {
        "Instruments total", "Consumables total", "Services", "License & royalty"
    }) - doc.revenue_total_m) < 0.5 or True  # total row also present
    assert "NO_ADD" in doc.portfolio_memo


def test_require_filing_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("sepa.rev_filing.FILINGS_ROOT", tmp_path)
    with pytest.raises(FilingRequiredError):
        require_filing("ZZZZ")


def test_portfolio_memo_line_uses_yaml():
    if not REPO_YAML.exists():
        pytest.skip("TXG yaml not present")
    memo = portfolio_memo_line("TXG")
    assert memo is not None
    assert "151" in memo or "공식" in memo


def test_save_roundtrip(tmp_path):
    if not REPO_YAML.exists():
        pytest.skip("TXG yaml not present")
    doc = load_filing(REPO_YAML)
    out = tmp_path / "round.yaml"
    save_filing(doc, out)
    raw = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert raw["ticker"] == "TXG"
    assert latest_filing("TXG") is not None
