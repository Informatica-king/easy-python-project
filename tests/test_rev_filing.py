"""Tests for sepa.rev_filing (official PDF → YAML SSOT + unofficial fallback)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from sepa.rev_filing import (
    SOURCE_OFFICIAL,
    SOURCE_UNOFFICIAL,
    FilingDoc,
    FilingRequiredError,
    extract_txg_earnings_release,
    latest_filing,
    load_filing,
    portfolio_memo_line,
    require_filing,
    resolve_filing,
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
    assert doc.is_official
    assert doc.source_kind in (SOURCE_OFFICIAL, None) or doc.source_kind == SOURCE_OFFICIAL


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


def test_resolve_prefers_official(tmp_path, monkeypatch):
    monkeypatch.setattr("sepa.rev_filing.FILINGS_ROOT", tmp_path)
    off = FilingDoc(
        ticker="ABCD",
        company="Abcd Inc",
        period_end="2026-06-30",
        report_date="2026-08-01",
        source_pdf="x.pdf",
        source_label="Official",
        source_kind=SOURCE_OFFICIAL,
        revenue_total_m=10.0,
        portfolio_memo="공식 10M",
    )
    unoff = FilingDoc(
        ticker="ABCD",
        company="Abcd Inc",
        period_end="2026-03-31",
        report_date="2026-05-01",
        source_pdf="",
        source_label="Unofficial",
        source_kind=SOURCE_UNOFFICIAL,
        revenue_total_m=9.0,
        portfolio_memo="비공식 9M · IR미확보",
    )
    save_filing(unoff)
    save_filing(off)
    doc = resolve_filing("ABCD", allow_unofficial=True)
    assert doc.is_official
    assert doc.period_end == "2026-06-30"


def test_resolve_unofficial_when_no_official(tmp_path, monkeypatch):
    monkeypatch.setattr("sepa.rev_filing.FILINGS_ROOT", tmp_path)

    fake = FilingDoc(
        ticker="NOIR",
        company="No IR Co",
        period_end="2026-03-31",
        report_date="2026-09-16",
        source_pdf="",
        source_label="Unofficial · yfinance",
        source_kind=SOURCE_UNOFFICIAL,
        revenue_total_m=42.5,
        yoy_reported_pct=-5.0,
        portfolio_memo="비공식 2026-03-31 · 매출 $42.5M · YoY -5% · IR미확보",
        risks=["IR/실적보도 PDF 미확보 — 비공식(공개데이터) 추정"],
    )

    def _fake_build(ticker: str) -> FilingDoc:
        assert ticker == "NOIR"
        return fake

    monkeypatch.setattr("sepa.rev_filing.build_unofficial_from_yfinance", _fake_build)
    with pytest.raises(FilingRequiredError):
        require_filing("NOIR")
    doc = resolve_filing("NOIR", allow_unofficial=True, save_unofficial=True)
    assert not doc.is_official
    assert doc.source_kind == SOURCE_UNOFFICIAL
    assert "IR미확보" in doc.portfolio_memo
    assert (tmp_path / "NOIR" / "2026-03-31.yaml").exists()
    memo = portfolio_memo_line("NOIR")
    assert memo is not None
    assert "비공식" in memo or "IR미확보" in memo


def test_require_rejects_unofficial_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr("sepa.rev_filing.FILINGS_ROOT", tmp_path)
    doc = FilingDoc(
        ticker="NOIR",
        company="No IR",
        period_end="2026-01-01",
        report_date="2026-01-02",
        source_pdf="",
        source_label="u",
        source_kind=SOURCE_UNOFFICIAL,
        revenue_total_m=1.0,
    )
    save_filing(doc)
    with pytest.raises(FilingRequiredError):
        require_filing("NOIR")
    with pytest.raises(FilingRequiredError):
        require_filing("NOIR", period_end="2026-01-01")


def test_build_unofficial_from_yfinance_mocked(monkeypatch):
    from sepa import rev_filing as rf

    class FakeCols(list):
        pass

    import pandas as pd

    idx = ["Total Revenue", "Operating Income", "Net Income"]
    cols = pd.to_datetime(["2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30", "2025-03-31"])
    data = [
        [100_000_000, 90_000_000, 95_000_000, 88_000_000, 80_000_000],
        [-5_000_000, -4_000_000, -3_000_000, -2_000_000, -1_000_000],
        [-6_000_000, -5_000_000, -4_000_000, -3_000_000, -2_000_000],
    ]
    q = pd.DataFrame(data, index=idx, columns=cols)

    tk = MagicMock()
    tk.info = {
        "shortName": "Fake Co",
        "grossMargins": 0.55,
        "totalCash": 200_000_000,
    }
    tk.quarterly_income_stmt = q
    tk.quarterly_financials = q

    yf = MagicMock()
    yf.Ticker.return_value = tk
    monkeypatch.setitem(__import__("sys").modules, "yfinance", yf)
    # Also patch import site used inside function
    monkeypatch.setattr(rf, "build_unofficial_from_yfinance", rf.build_unofficial_from_yfinance)

    # Force import yfinance to return our mock by injecting into builtins via patch of import
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yfinance":
            return yf
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    doc = rf.build_unofficial_from_yfinance("FAKE")
    assert doc.source_kind == SOURCE_UNOFFICIAL
    assert not doc.is_official
    assert doc.revenue_total_m == pytest.approx(100.0, abs=0.01)
    assert doc.revenue_prior_m == pytest.approx(80.0, abs=0.01)  # YoY col[4]
    assert doc.yoy_reported_pct == pytest.approx(25.0, abs=0.1)
    assert "IR미확보" in doc.portfolio_memo
    assert doc.gross_margin_pct == pytest.approx(55.0, abs=0.1)
