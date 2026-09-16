"""Official earnings-filing SSOT for 수익구조분석().

Policy (v1):
  * Official PDF → structured YAML under ``data/rev_filings/<TICKER>/``.
  * Revenue-structure generators that opt in **must** load a filing YAML;
    if missing, raise ``FilingRequiredError`` (do not fall back to estimates).
  * Portfolio ops can cite a one-line memo from the latest filing.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
FILINGS_ROOT = ROOT / "data" / "rev_filings"


class FilingRequiredError(FileNotFoundError):
    """Raised when an official filing YAML is required but missing."""


@dataclass
class MixLine:
    name: str
    amount_m: float
    prior_m: float | None = None
    note: str = ""

    @property
    def yoy_pct(self) -> float | None:
        if self.prior_m is None or abs(self.prior_m) < 1e-9:
            return None
        return (self.amount_m / self.prior_m - 1.0) * 100.0


@dataclass
class FilingDoc:
    ticker: str
    company: str
    period_end: str  # YYYY-MM-DD
    report_date: str  # YYYY-MM-DD
    source_pdf: str
    source_label: str
    currency: str = "USD"
    units: str = "millions"  # amounts stored as millions of USD
    revenue_total_m: float | None = None
    revenue_ex_onetime_m: float | None = None
    revenue_prior_m: float | None = None
    revenue_prior_ex_onetime_m: float | None = None
    yoy_reported_pct: float | None = None
    yoy_ex_onetime_pct: float | None = None
    gross_margin_pct: float | None = None
    gross_margin_prior_pct: float | None = None
    operating_income_m: float | None = None
    net_income_m: float | None = None
    eps_basic: float | None = None
    cash_and_securities_m: float | None = None
    guidance_fy_low_m: float | None = None
    guidance_fy_high_m: float | None = None
    guidance_note: str = ""
    onetime_items: list[dict[str, Any]] = field(default_factory=list)
    mix_product: list[dict[str, Any]] = field(default_factory=list)
    mix_geo: list[dict[str, Any]] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    catalysts: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    quotes: list[str] = field(default_factory=list)
    portfolio_memo: str = ""
    extracted_by: str = "sepa.rev_filing"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def filings_dir(ticker: str) -> Path:
    return FILINGS_ROOT / str(ticker).upper()


def filing_path(ticker: str, period_end: str) -> Path:
    return filings_dir(ticker) / f"{period_end}.yaml"


def list_filings(ticker: str) -> list[Path]:
    d = filings_dir(ticker)
    if not d.exists():
        return []
    return sorted(d.glob("????-??-??.yaml"), reverse=True)


def load_filing(path: str | Path) -> FilingDoc:
    p = Path(path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return FilingDoc(**{k: v for k, v in raw.items() if k in FilingDoc.__dataclass_fields__})


def save_filing(doc: FilingDoc, path: str | Path | None = None) -> Path:
    out = Path(path) if path else filing_path(doc.ticker, doc.period_end)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(doc.to_dict(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return out


def latest_filing(ticker: str) -> FilingDoc | None:
    paths = list_filings(ticker)
    if not paths:
        return None
    return load_filing(paths[0])


def require_filing(ticker: str, *, period_end: str | None = None) -> FilingDoc:
    """Load official filing YAML or raise FilingRequiredError (policy 1-A)."""
    t = str(ticker).upper()
    if period_end:
        p = filing_path(t, period_end)
        if not p.exists():
            raise FilingRequiredError(
                f"공식 실적 YAML 없음: {p}\n"
                f"수익구조분석({t})은 공식 PDF→YAML이 필요합니다. "
                f"PDF를 첨부한 뒤 `python -m sepa.rev_filing ingest --ticker {t} --pdf <path>` 를 실행하세요."
            )
        return load_filing(p)
    doc = latest_filing(t)
    if doc is None:
        raise FilingRequiredError(
            f"공식 실적 YAML 없음: {filings_dir(t)}\n"
            f"수익구조분석({t})은 공식 PDF→YAML이 필요합니다. "
            f"PDF를 첨부한 뒤 `python -m sepa.rev_filing ingest --ticker {t} --pdf <path>` 를 실행하세요."
        )
    return doc


def portfolio_memo_line(ticker: str) -> str | None:
    """One-line cite for 포폴 메모 (policy 3-B)."""
    doc = latest_filing(ticker)
    if doc is None:
        return None
    if doc.portfolio_memo:
        return doc.portfolio_memo
    bits = [f"공식실적 {doc.period_end}"]
    if doc.revenue_total_m is not None:
        bits.append(f"매출 ${doc.revenue_total_m:.1f}M")
    if doc.yoy_ex_onetime_pct is not None:
        bits.append(f"ex-일회성 {doc.yoy_ex_onetime_pct:+.0f}%")
    elif doc.yoy_reported_pct is not None:
        bits.append(f"YoY {doc.yoy_reported_pct:+.0f}%")
    if doc.guidance_fy_low_m is not None and doc.guidance_fy_high_m is not None:
        bits.append(f"FY가이드 ${doc.guidance_fy_low_m:.0f}–{doc.guidance_fy_high_m:.0f}M")
    return " · ".join(bits)


def pdf_to_text(pdf_path: str | Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def _money_m(val: str) -> float:
    """Parse '$151.0 million' / '151,036' (thousands) helpers are caller-specific."""
    s = val.replace(",", "").replace("$", "").strip()
    return float(s)


def extract_txg_earnings_release(pdf_path: str | Path, *, copy_source: bool = True) -> FilingDoc:
    """Parse 10x Genomics quarterly earnings press-release PDF into FilingDoc."""
    pdf_path = Path(pdf_path)
    text = pdf_to_text(pdf_path)

    # Header dates
    m_date = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(20\d{2})",
        text,
    )
    months = {
        "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
        "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
    }
    report_date = date.today().isoformat()
    if m_date:
        report_date = date(int(m_date.group(3)), months[m_date.group(1)], int(m_date.group(2))).isoformat()

    m_period = re.search(
        r"second quarter ended\s+(June|March|September|December)\s+(\d{1,2}),\s+(20\d{2})",
        text,
        re.I,
    )
    # fallback quarter labels
    period_end = "2026-06-30"
    if m_period:
        mo = months[m_period.group(1).title()]
        period_end = date(int(m_period.group(3)), mo, int(m_period.group(2))).isoformat()
    elif re.search(r"first quarter ended\s+March", text, re.I):
        period_end = "2026-03-31"

    def find_rev(pat: str) -> float | None:
        m = re.search(pat, text, re.I | re.S)
        return float(m.group(1)) if m else None

    rev_total = find_rev(r"Revenue was \$([0-9]+(?:\.[0-9]+)?)\s*million for the second quarter of 2026")
    onetime_cur = None
    onetime_pri = None
    m_both = re.search(
        r"Excluding\s*\$([0-9.]+)\s*million\s+and\s+\$([0-9.]+)\s*million\s+of\s+non-recurring",
        text,
        re.I,
    )
    if m_both:
        onetime_cur = float(m_both.group(1))
        onetime_pri = float(m_both.group(2))
    if onetime_cur is None:
        onetime_cur = find_rev(
            r"Excluding\s*\$([0-9]+(?:\.[0-9]+)?)\s*million related to a patent litigation settlement"
        )

    rev_prior = find_rev(
        r"as compared to \$([0-9]+(?:\.[0-9]+)?)\s*million for the corresponding period of 2025"
    )
    yoy_ex = find_rev(
        r"revenue increased ([0-9]+(?:\.[0-9]+)?)%\s*over the corresponding period of 2025 when excluding"
    )
    if yoy_ex is None:
        yoy_ex = find_rev(
            r"revenue increased ([0-9]+(?:\.[0-9]+)?)%\s*over the corresponding period of 2025"
        )

    gm = find_rev(r"Gross margin was ([0-9]+(?:\.[0-9]+)?)%\s*for the second quarter of 2026")
    gm_pri = find_rev(r"as compared to ([0-9]+(?:\.[0-9]+)?)%\s*for the corresponding prior year period")
    op_loss = find_rev(r"Operating loss was \$([0-9]+(?:\.[0-9]+)?)\s*million for the second quarter of 2026")
    net_loss = find_rev(r"Net loss was \$([0-9]+(?:\.[0-9]+)?)\s*million for the second quarter of 2026")
    cash = find_rev(
        r"Cash and cash equivalents and marketable securities were \$([0-9]+(?:\.[0-9]+)?)\s*million as of"
    )

    g_low = g_high = None
    m_g = re.search(
        r"expects revenue in the range of \$([0-9]+)\s*million to \$([0-9]+)\s*million",
        text,
        re.I,
    )
    if m_g:
        g_low, g_high = float(m_g.group(1)), float(m_g.group(2))
    g_growth = re.search(
        r"this represents ([0-9]+)%\s*to\s*([0-9]+)%\s*growth over full year 2025",
        text,
        re.I,
    )
    guidance_note = ""
    if g_growth:
        guidance_note = f"ex-settlement FY 성장 {g_growth.group(1)}–{g_growth.group(2)}%"

    # Table amounts are in thousands in the condensed statements
    def grab_row(label: str) -> tuple[float | None, float | None]:
        # e.g. "Single Cell $ 3,087   $ 5,727"
        pat = rf"{re.escape(label)}\s*\$?\s*([0-9,]+)\s+\$?\s*([0-9,]+)"
        m = re.search(pat, text)
        if not m:
            return None, None
        return float(m.group(1).replace(",", "")) / 1000.0, float(m.group(2).replace(",", "")) / 1000.0

    sc_inst, sc_inst_p = grab_row("Single Cell")
    # Spatial instruments row appears after first Single Cell under Instruments
    # More robust: parse products block
    mix_product: list[dict[str, Any]] = []
    # Prefer explicit block parse
    block = re.search(
        r"Instruments\s+Single Cell\s*\$?\s*([0-9,]+)\s+\$?\s*([0-9,]+).*?"
        r"Spatial\s*\$?\s*([0-9,]+)\s+\$?\s*([0-9,]+).*?"
        r"Total instruments revenue\s*([0-9,]+)\s+([0-9,]+).*?"
        r"Consumables\s+Single Cell\s*([0-9,]+)\s+([0-9,]+).*?"
        r"Spatial\s*([0-9,]+)\s+([0-9,]+).*?"
        r"Total consumables revenue\s*([0-9,]+)\s+([0-9,]+).*?"
        r"Services\s*([0-9,]+)\s+([0-9,]+).*?"
        r"Products and services revenue\s*([0-9,]+)\s+\$?\s*([0-9,]+).*?"
        r"License and royalty revenue\s*([0-9,]+)\s+\$?\s*([0-9,]+).*?"
        r"Total revenue\s*\$?\s*([0-9,]+)\s+\$?\s*([0-9,]+)",
        text,
        re.S | re.I,
    )
    if block:
        def th(i: int) -> float:
            return float(block.group(i).replace(",", "")) / 1000.0

        rows = [
            ("Instruments — Single Cell", 1, 2),
            ("Instruments — Spatial", 3, 4),
            ("Instruments total", 5, 6),
            ("Consumables — Single Cell", 7, 8),
            ("Consumables — Spatial", 9, 10),
            ("Consumables total", 11, 12),
            ("Services", 13, 14),
            ("Products & services", 15, 16),
            ("License & royalty", 17, 18),
            ("Total revenue", 19, 20),
        ]
        for name, a, b in rows:
            cur, pri = th(a), th(b)
            mix_product.append(
                {
                    "name": name,
                    "amount_m": round(cur, 3),
                    "prior_m": round(pri, 3),
                    "yoy_pct": round((cur / pri - 1.0) * 100.0, 1) if pri else None,
                }
            )

    mix_geo: list[dict[str, Any]] = []
    geo = re.search(
        r"United States\*?\s*\$?\s*([0-9,]+)\s+\$?\s*([0-9,]+).*?"
        r"Americas \(excluding United States\)\s*([0-9,]+)\s+([0-9,]+).*?"
        r"Total Americas\s*([0-9,]+)\s+([0-9,]+).*?"
        r"Europe, Middle East and Africa\s*([0-9,]+)\s+([0-9,]+).*?"
        r"China\s*([0-9,]+)\s+([0-9,]+).*?"
        r"Asia-Pacific \(excluding China\)\s*([0-9,]+)\s+([0-9,]+).*?"
        r"Total Asia-Pacific\s*([0-9,]+)\s+([0-9,]+)",
        text,
        re.S | re.I,
    )
    if geo:
        def thg(i: int) -> float:
            return float(geo.group(i).replace(",", "")) / 1000.0

        for name, a, b in [
            ("United States", 1, 2),
            ("Americas ex-US", 3, 4),
            ("Americas total", 5, 6),
            ("EMEA", 7, 8),
            ("China", 9, 10),
            ("APAC ex-China", 11, 12),
            ("APAC total", 13, 14),
        ]:
            cur, pri = thg(a), thg(b)
            mix_geo.append(
                {
                    "name": name,
                    "amount_m": round(cur, 3),
                    "prior_m": round(pri, 3),
                    "yoy_pct": round((cur / pri - 1.0) * 100.0, 1) if pri else None,
                }
            )

    rev_ex = None
    if rev_total is not None and onetime_cur is not None:
        rev_ex = round(rev_total - onetime_cur, 3)
    prior_ex = None
    if rev_prior is not None and onetime_pri is not None:
        prior_ex = round(rev_prior - onetime_pri, 3)

    yoy_reported = None
    if rev_total and rev_prior:
        yoy_reported = round((rev_total / rev_prior - 1.0) * 100.0, 1)

    onetime_items = []
    if onetime_cur is not None:
        onetime_items.append(
            {
                "label": "Patent litigation settlement (license/royalty)",
                "amount_m": onetime_cur,
                "period": "current",
            }
        )
    if onetime_pri is not None:
        onetime_items.append(
            {
                "label": "Patent litigation settlement (license/royalty)",
                "amount_m": onetime_pri,
                "period": "prior_year",
            }
        )

    highlights = []
    if rev_total is not None:
        highlights.append(f"Q 매출 ${rev_total:.1f}M" + (f" · ex-settlement ${rev_ex:.1f}M" if rev_ex else ""))
    if yoy_ex is not None:
        highlights.append(f"일회성 제외 YoY +{yoy_ex:.0f}%")
    if gm is not None:
        highlights.append(f"총이익률 {gm:.0f}%")
    if cash is not None:
        highlights.append(f"현금+단기투자 ${cash:.0f}M")

    catalysts = []
    if re.search(r"\bAtera\b", text):
        catalysts.append("Atera — 고객 반응·초기 주문 강세 (CEO)")
    if re.search(r"Proteintech Genomics", text):
        catalysts.append("Proteintech Genomics 인수 — 단백질(multiomics) 역량")
    if re.search(r"Cleveland Clinic", text):
        catalysts.append("Cleveland Clinic·Lausanne — 진단/암 연구 협력")
    if re.search(r"raising its full year 2026 revenue guidance", text, re.I):
        catalysts.append("FY26 매출 가이던스 상향")

    risks = []
    if re.search(r"Instruments", text) and mix_product:
        inst = next((r for r in mix_product if r["name"] == "Instruments total"), None)
        if inst and inst.get("yoy_pct") is not None and inst["yoy_pct"] < 0:
            risks.append(f"장비 매출 YoY {inst['yoy_pct']:+.0f}%")
    us = next((r for r in mix_geo if r["name"] == "United States"), None)
    if us and us.get("yoy_pct") is not None and us["yoy_pct"] < 0:
        risks.append(f"미국 매출 YoY {us['yoy_pct']:+.0f}%")
    cn = next((r for r in mix_geo if r["name"] == "China"), None)
    if cn and cn.get("yoy_pct") is not None and cn["yoy_pct"] < 0:
        risks.append(f"중국 매출 YoY {cn['yoy_pct']:+.0f}%")

    quote = None
    m_q = re.search(r"“([^”]{40,280})”\s*,\s*said Serge Saxonov", text)
    if m_q:
        quote = m_q.group(1).strip()

    # Destination for copied source
    src_rel = f"data/rev_filings/TXG/source/{pdf_path.name}"
    if copy_source:
        dest = ROOT / src_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if pdf_path.resolve() != dest.resolve():
            dest.write_bytes(pdf_path.read_bytes())

    cons = next((r for r in mix_product if r["name"] == "Consumables total"), None)
    cons_pct = None
    if cons and rev_total:
        # share of total reported revenue
        cons_pct = round(100.0 * cons["amount_m"] / rev_total, 1)

    memo_bits = [
        f"공식Q2'26 매출 ${rev_total:.1f}M" if rev_total else "공식Q2'26",
    ]
    if yoy_ex is not None:
        memo_bits.append(f"ex-합의 +{yoy_ex:.0f}%")
    if cons_pct is not None:
        memo_bits.append(f"소모품~{cons_pct:.0f}%")
    if g_low and g_high:
        memo_bits.append(f"FY가이드 ${g_low:.0f}–{g_high:.0f}M↑")
    memo_bits.append("NO_ADD")

    return FilingDoc(
        ticker="TXG",
        company="10x Genomics, Inc.",
        period_end=period_end,
        report_date=report_date,
        source_pdf=src_rel,
        source_label="Q2 2026 Earnings Press Release (Exhibit-style)",
        revenue_total_m=rev_total,
        revenue_ex_onetime_m=rev_ex,
        revenue_prior_m=rev_prior,
        revenue_prior_ex_onetime_m=prior_ex,
        yoy_reported_pct=yoy_reported,
        yoy_ex_onetime_pct=float(yoy_ex) if yoy_ex is not None else None,
        gross_margin_pct=gm,
        gross_margin_prior_pct=gm_pri,
        operating_income_m=(-op_loss) if op_loss is not None else None,
        net_income_m=(-net_loss) if net_loss is not None else None,
        cash_and_securities_m=cash,
        guidance_fy_low_m=g_low,
        guidance_fy_high_m=g_high,
        guidance_note=guidance_note,
        onetime_items=onetime_items,
        mix_product=mix_product,
        mix_geo=mix_geo,
        highlights=highlights,
        catalysts=catalysts,
        risks=risks,
        quotes=[quote] if quote else [],
        portfolio_memo=" · ".join(memo_bits),
        notes="Amounts in millions USD. Statement tables originally in thousands.",
    )


def ingest(ticker: str, pdf_path: str | Path) -> Path:
    t = str(ticker).upper()
    pdf_path = Path(pdf_path)
    if t == "TXG":
        doc = extract_txg_earnings_release(pdf_path)
    else:
        raise NotImplementedError(
            f"v1 파일럿은 TXG만 지원합니다. ({t}) — 추출기 추가 후 재시도."
        )
    return save_filing(doc)


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="sepa.rev_filing")
    sub = p.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest", help="Parse official PDF → YAML")
    ing.add_argument("--ticker", required=True)
    ing.add_argument("--pdf", required=True)

    sh = sub.add_parser("show", help="Print latest filing / memo")
    sh.add_argument("--ticker", required=True)

    req = sub.add_parser("require", help="Exit 2 if filing YAML missing")
    req.add_argument("--ticker", required=True)

    args = p.parse_args(argv)
    if args.cmd == "ingest":
        out = ingest(args.ticker, args.pdf)
        print(f"wrote {out}")
        doc = load_filing(out)
        print("memo:", doc.portfolio_memo)
        return 0
    if args.cmd == "show":
        doc = latest_filing(args.ticker)
        if not doc:
            print("NO_FILING")
            return 1
        print(yaml.safe_dump(doc.to_dict(), allow_unicode=True, sort_keys=False))
        print("MEMO:", portfolio_memo_line(args.ticker))
        return 0
    if args.cmd == "require":
        try:
            doc = require_filing(args.ticker)
        except FilingRequiredError as e:
            print(e)
            return 2
        print(f"OK {doc.ticker} {doc.period_end} ← {doc.source_pdf}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
