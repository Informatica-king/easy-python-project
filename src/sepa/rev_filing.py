"""Earnings filing SSOT for 수익구조분석().

Policy:
  * **Official** — company IR/earnings PDF → YAML under ``data/rev_filings/<TICKER>/``.
  * **Unofficial fallback** — IR 자료가 없으면 yfinance 등 공개 데이터로 YAML 초안 생성.
    표지·메모에 ``비공식``을 명시하고, 공식 PDF가 생기면 자동으로 공식본을 우선한다.
  * Portfolio ops can cite a one-line memo from the latest filing (official or unofficial).
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

SOURCE_OFFICIAL = "official"
SOURCE_UNOFFICIAL = "unofficial"


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
    source_kind: str = SOURCE_OFFICIAL  # official | unofficial
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

    @property
    def is_official(self) -> bool:
        return (self.source_kind or SOURCE_OFFICIAL) == SOURCE_OFFICIAL


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


def require_filing(ticker: str, *, period_end: str | None = None) -> FilingDoc:
    """Load **official** filing YAML or raise FilingRequiredError."""
    t = str(ticker).upper()
    if period_end:
        p = filing_path(t, period_end)
        if not p.exists():
            raise FilingRequiredError(_missing_msg(t, p))
        doc = load_filing(p)
        if not doc.is_official:
            raise FilingRequiredError(
                f"{p} 는 비공식(source_kind={doc.source_kind})입니다. 공식 PDF ingest가 필요합니다."
            )
        return doc
    for p in list_filings(t):
        doc = load_filing(p)
        if doc.is_official:
            return doc
    raise FilingRequiredError(_missing_msg(t, filings_dir(t)))


def _missing_msg(ticker: str, where: Path) -> str:
    return (
        f"공식 실적 YAML 없음: {where}\n"
        f"옵션1) PDF 첨부 후 `python -m sepa.rev_filing ingest --ticker {ticker} --pdf <path>`\n"
        f"옵션2) IR 없으면 `python -m sepa.rev_filing fallback --ticker {ticker}` (비공식)"
    )


def latest_filing(ticker: str, *, prefer_official: bool = True) -> FilingDoc | None:
    paths = list_filings(ticker)
    if not paths:
        return None
    docs = [load_filing(p) for p in paths]
    if prefer_official:
        for d in docs:
            if d.is_official:
                return d
    return docs[0]


def portfolio_memo_line(ticker: str) -> str | None:
    """One-line cite for 포폴 메모 (policy 3-B)."""
    doc = latest_filing(ticker)
    if doc is None:
        return None
    if doc.portfolio_memo:
        return doc.portfolio_memo
    prefix = "공식실적" if doc.is_official else "비공식실적"
    bits = [f"{prefix} {doc.period_end}"]
    if doc.revenue_total_m is not None:
        bits.append(f"매출 ${doc.revenue_total_m:.1f}M")
    if doc.yoy_ex_onetime_pct is not None:
        bits.append(f"ex-일회성 {doc.yoy_ex_onetime_pct:+.0f}%")
    elif doc.yoy_reported_pct is not None:
        bits.append(f"YoY {doc.yoy_reported_pct:+.0f}%")
    if doc.guidance_fy_low_m is not None and doc.guidance_fy_high_m is not None:
        bits.append(f"FY가이드 ${doc.guidance_fy_low_m:.0f}–{doc.guidance_fy_high_m:.0f}M")
    if not doc.is_official:
        bits.append("IR미확보")
    return " · ".join(bits)


def _to_millions(x: float | None) -> float | None:
    """Convert yfinance absolute-USD amounts to millions.

    Quarterly statements return full dollars (e.g. 28_529_000 → 28.529).
    Small amounts like operating income of $74,000 must become 0.074, not 74000.
    """
    if x is None:
        return None
    v = float(x)
    return round(v / 1_000_000.0, 3)


def build_unofficial_from_yfinance(ticker: str) -> FilingDoc:
    """IR/실적보도가 없을 때 공개 데이터로 비공식 FilingDoc 초안."""
    import yfinance as yf

    t = str(ticker).upper()
    tk = yf.Ticker(t)
    info = tk.info or {}
    company = info.get("shortName") or info.get("longName") or t
    report_date = date.today().isoformat()

    # Prefer quarterly income statement
    rev_cur = rev_pri = None
    op_cur = net_cur = None
    period_end = report_date
    prior_is_yoy = False
    try:
        q = getattr(tk, "quarterly_income_stmt", None)
        if q is None or getattr(q, "empty", True):
            q = tk.quarterly_financials
        if q is not None and not q.empty:
            cols = list(q.columns)
            c0 = cols[0]
            period_end = c0.date().isoformat() if hasattr(c0, "date") else str(c0)[:10]
            def cell(row_names: tuple[str, ...], col) -> float | None:
                for name in row_names:
                    if name in q.index:
                        val = q.loc[name, col]
                        try:
                            return float(val)
                        except Exception:
                            return None
                return None

            rev_cur = cell(("Total Revenue", "Operating Revenue", "Revenue"), cols[0])
            if len(cols) > 1:
                rev_pri = cell(("Total Revenue", "Operating Revenue", "Revenue"), cols[1])
            # YoY: same quarter prior year ≈ 4th prior col if available and non-zero
            if len(cols) > 4:
                rev_pri_yoy = cell(("Total Revenue", "Operating Revenue", "Revenue"), cols[4])
                if rev_pri_yoy is not None and abs(float(rev_pri_yoy)) > 1e-9:
                    rev_pri = rev_pri_yoy
                    prior_is_yoy = True
            op_cur = cell(("Operating Income", "Operating Income Loss", "EBIT"), cols[0])
            net_cur = cell(("Net Income", "Net Income Common Stockholders"), cols[0])
    except Exception:
        pass

    if rev_cur is None:
        rev_cur = info.get("totalRevenue")
    if op_cur is None:
        op_cur = info.get("ebit") or None
    if net_cur is None:
        net_cur = info.get("netIncomeToCommon")

    rev_m = _to_millions(rev_cur)
    rev_pri_m = _to_millions(rev_pri)
    # If totalRevenue is annual TTM, mark in notes
    annualish = bool(info.get("totalRevenue") and rev_cur == info.get("totalRevenue") and rev_pri is None)

    yoy = None
    if rev_m is not None and rev_pri_m is not None and abs(rev_pri_m) > 1e-9:
        yoy = round((rev_m / rev_pri_m - 1.0) * 100.0, 1)
    growth_label = "YoY" if prior_is_yoy else "QoQ"

    gm = info.get("grossMargins")
    gm_pct = round(float(gm) * 100.0, 1) if gm is not None else None
    cash = info.get("totalCash")
    cash_m = _to_millions(cash)

    mix_product: list[dict[str, Any]] = []
    if rev_m is not None:
        mix_product.append(
            {
                "name": "Total revenue",
                "amount_m": rev_m,
                "prior_m": rev_pri_m,
                "yoy_pct": yoy if prior_is_yoy else None,
                "qoq_pct": yoy if not prior_is_yoy else None,
            }
        )

    risks = [
        "IR/실적보도 PDF 미확보 — 비공식(공개데이터) 추정",
        "세그먼트·지역 믹스 없음 — 구성 분석 제한",
    ]
    if annualish:
        risks.append("매출이 분기 확정이 아닐 수 있음(TTM/연간 혼재 가능)")
    if yoy is not None and not prior_is_yoy:
        risks.append("전년동분기 매출 부재/0 — 성장률은 QoQ 참고")

    highlights = []
    if rev_m is not None:
        highlights.append(f"비공식 매출 ${rev_m:.1f}M")
    if yoy is not None:
        highlights.append(f"{growth_label} {yoy:+.0f}%")
    if cash_m is not None:
        highlights.append(f"현금~${cash_m:.0f}M")

    memo_bits = [f"비공식 {period_end}"]
    if rev_m is not None:
        memo_bits.append(f"매출 ${rev_m:.1f}M")
    if yoy is not None:
        memo_bits.append(f"{growth_label} {yoy:+.0f}%")
    memo_bits.append("IR미확보")

    return FilingDoc(
        ticker=t,
        company=str(company),
        period_end=period_end,
        report_date=report_date,
        source_pdf="",
        source_label="Unofficial · yfinance / public market data (IR PDF unavailable)",
        source_kind=SOURCE_UNOFFICIAL,
        revenue_total_m=rev_m,
        revenue_ex_onetime_m=rev_m,
        revenue_prior_m=rev_pri_m,
        yoy_reported_pct=yoy if prior_is_yoy else None,
        yoy_ex_onetime_pct=yoy if prior_is_yoy else None,
        gross_margin_pct=gm_pct,
        operating_income_m=_to_millions(op_cur) if op_cur is not None else None,
        net_income_m=_to_millions(net_cur) if net_cur is not None else None,
        cash_and_securities_m=cash_m,
        mix_product=mix_product,
        highlights=highlights,
        risks=risks,
        catalysts=["공식 IR/실적 PDF 확보 시 재ingest로 교체"],
        portfolio_memo=" · ".join(memo_bits),
        extracted_by="sepa.rev_filing.unofficial_yfinance",
        notes=(
            "비공식. 세그먼트/가이던스/일회성 분해 없음. 공식 PDF가 최우선."
            + ("" if prior_is_yoy else " 성장률은 QoQ(직전분기).")
        ),
    )


def resolve_filing(
    ticker: str,
    *,
    allow_unofficial: bool = True,
    save_unofficial: bool = True,
    period_end: str | None = None,
) -> FilingDoc:
    """공식 YAML 우선 · 없으면 비공식 폴백(기본 허용)."""
    t = str(ticker).upper()
    if period_end:
        p = filing_path(t, period_end)
        if p.exists():
            return load_filing(p)
    official = None
    try:
        official = require_filing(t, period_end=period_end)
    except FilingRequiredError:
        official = None
    if official is not None:
        return official
    # existing unofficial yaml?
    doc = latest_filing(t, prefer_official=False)
    if doc is not None:
        return doc
    if not allow_unofficial:
        raise FilingRequiredError(_missing_msg(t, filings_dir(t)))
    doc = build_unofficial_from_yfinance(t)
    if save_unofficial:
        save_filing(doc)
        print(f"[rev_filing] unofficial fallback wrote {filing_path(t, doc.period_end)}")
    return doc


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
        source_kind=SOURCE_OFFICIAL,
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
            f"공식 PDF 추출기는 TXG 파일럿만 지원합니다. ({t})\n"
            f"IR PDF가 없으면: `python -m sepa.rev_filing fallback --ticker {t}`"
        )
    doc.source_kind = SOURCE_OFFICIAL
    return save_filing(doc)


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="sepa.rev_filing")
    sub = p.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest", help="Parse official PDF → YAML")
    ing.add_argument("--ticker", required=True)
    ing.add_argument("--pdf", required=True)

    fb = sub.add_parser("fallback", help="IR 없을 때 비공식 yfinance YAML 생성")
    fb.add_argument("--ticker", required=True)
    fb.add_argument("--no-save", action="store_true")

    sh = sub.add_parser("show", help="Print latest filing / memo")
    sh.add_argument("--ticker", required=True)
    sh.add_argument("--allow-unofficial", action="store_true", default=True)

    req = sub.add_parser("require", help="Exit 2 if official filing YAML missing")
    req.add_argument("--ticker", required=True)

    res = sub.add_parser("resolve", help="공식 우선 · 없으면 비공식 폴백")
    res.add_argument("--ticker", required=True)
    res.add_argument("--official-only", action="store_true")

    args = p.parse_args(argv)
    if args.cmd == "ingest":
        out = ingest(args.ticker, args.pdf)
        print(f"wrote {out}")
        doc = load_filing(out)
        print("kind:", doc.source_kind, "memo:", doc.portfolio_memo)
        return 0
    if args.cmd == "fallback":
        doc = build_unofficial_from_yfinance(args.ticker)
        if not args.no_save:
            out = save_filing(doc)
            print(f"wrote {out}")
        print("kind:", doc.source_kind, "memo:", doc.portfolio_memo)
        print(yaml.safe_dump(doc.to_dict(), allow_unicode=True, sort_keys=False))
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
        print(f"OK official {doc.ticker} {doc.period_end} ← {doc.source_pdf}")
        return 0
    if args.cmd == "resolve":
        doc = resolve_filing(args.ticker, allow_unofficial=not args.official_only)
        print(f"OK {doc.source_kind} {doc.ticker} {doc.period_end}")
        print("MEMO:", doc.portfolio_memo)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
