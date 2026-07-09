"""Fetch all NASDAQ-listed securities and export them to a formatted Excel file.

Data source: the official NASDAQ Trader symbol directory
(https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt), which lists
every security actively listed on the NASDAQ Stock Market. The file is a
pipe-delimited text file that is refreshed every trading day.

Usage:
    python fetch_nasdaq_companies.py [--output nasdaq_companies.xlsx]
"""

from __future__ import annotations

import argparse
import io
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"

# Human-readable code lookups documented by NASDAQ Trader.
MARKET_CATEGORY = {
    "Q": "NASDAQ Global Select Market",
    "G": "NASDAQ Global Market",
    "S": "NASDAQ Capital Market",
}

FINANCIAL_STATUS = {
    "D": "Deficient",
    "E": "Delinquent",
    "Q": "Bankrupt",
    "N": "Normal",
    "G": "Deficient and Bankrupt",
    "H": "Deficient and Delinquent",
    "J": "Delinquent and Bankrupt",
    "K": "Deficient, Delinquent and Bankrupt",
}

YES_NO = {"Y": "Yes", "N": "No"}


def _format_creation_time(raw_time: str) -> str:
    """Convert NASDAQ's ``MMDDYYYYHH:MM`` timestamp to a readable string."""
    try:
        return datetime.strptime(raw_time, "%m%d%Y%H:%M").strftime(
            "%Y-%m-%d %H:%M (US/Eastern)"
        )
    except ValueError:
        return raw_time


def download_nasdaq_listed(url: str = NASDAQ_LISTED_URL) -> str:
    """Download the raw pipe-delimited NASDAQ listing file."""
    headers = {"User-Agent": "Mozilla/5.0 (nasdaq-company-lister)"}
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.text


def parse_listing(raw_text: str) -> tuple[pd.DataFrame, str | None]:
    """Parse the raw file into a tidy DataFrame.

    The last line of the file is a footer such as
    ``File Creation Time: 0709202605:30`` which must be dropped before parsing.
    """
    lines = raw_text.splitlines()
    creation_time = None
    if lines and lines[-1].startswith("File Creation Time"):
        raw_time = lines[-1].split(":", 1)[1].strip().rstrip("|").strip()
        creation_time = _format_creation_time(raw_time)
        lines = lines[:-1]

    df = pd.read_csv(io.StringIO("\n".join(lines)), sep="|", dtype=str)
    df = df.fillna("")

    # Add readable columns derived from the raw single-letter codes.
    df["Market Category (Name)"] = df["Market Category"].map(MARKET_CATEGORY).fillna(
        df["Market Category"]
    )
    df["Financial Status (Name)"] = df["Financial Status"].map(FINANCIAL_STATUS).fillna(
        df["Financial Status"]
    )
    df["Is Test Issue"] = df["Test Issue"].map(YES_NO).fillna(df["Test Issue"])
    df["Is ETF"] = df["ETF"].map(YES_NO).fillna(df["ETF"])

    return df, creation_time


def build_companies_view(df: pd.DataFrame) -> pd.DataFrame:
    """Return a company-focused view.

    Excludes test issues and ETFs so the result reflects operating companies /
    common equity rather than funds or exchange test tickers.
    """
    companies = df[(df["Test Issue"] != "Y") & (df["ETF"] != "Y")].copy()
    return companies.reset_index(drop=True)


def _autosize_and_style(writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame) -> None:
    from openpyxl.styles import Alignment, Font, PatternFill

    worksheet = writer.sheets[sheet_name]
    header_fill = PatternFill("solid", fgColor="1F3864")
    header_font = Font(color="FFFFFF", bold=True)

    for col_idx, column in enumerate(df.columns, start=1):
        cell = worksheet.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

        max_len = max(
            [len(str(column))]
            + [len(str(v)) for v in df[column].head(2000).tolist()]
        )
        worksheet.column_dimensions[
            worksheet.cell(row=1, column=col_idx).column_letter
        ].width = min(max_len + 2, 60)

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions


def export_to_excel(
    df: pd.DataFrame,
    companies: pd.DataFrame,
    output_path: str,
    creation_time: str | None,
) -> None:
    """Write the listing to a multi-sheet, styled Excel workbook."""
    summary = pd.DataFrame(
        {
            "Metric": [
                "Data source",
                "Source file creation time",
                "Downloaded at (UTC)",
                "Total securities listed on NASDAQ",
                "Companies / common equity (excl. ETFs & test issues)",
                "ETFs",
                "Test issues",
                "NASDAQ Global Select Market",
                "NASDAQ Global Market",
                "NASDAQ Capital Market",
            ],
            "Value": [
                NASDAQ_LISTED_URL,
                creation_time or "N/A",
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                len(df),
                len(companies),
                int((df["ETF"] == "Y").sum()),
                int((df["Test Issue"] == "Y").sum()),
                int((df["Market Category"] == "Q").sum()),
                int((df["Market Category"] == "G").sum()),
                int((df["Market Category"] == "S").sum()),
            ],
        }
    )

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        companies.to_excel(writer, sheet_name="Companies", index=False)
        df.to_excel(writer, sheet_name="All NASDAQ Securities", index=False)

        _autosize_and_style(writer, "Summary", summary)
        _autosize_and_style(writer, "Companies", companies)
        _autosize_and_style(writer, "All NASDAQ Securities", df)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="nasdaq_companies.xlsx",
        help="Path to the Excel file to create (default: nasdaq_companies.xlsx)",
    )
    args = parser.parse_args(argv)

    print(f"Downloading NASDAQ listing from {NASDAQ_LISTED_URL} ...")
    raw = download_nasdaq_listed()

    df, creation_time = parse_listing(raw)
    companies = build_companies_view(df)

    print(
        f"Parsed {len(df)} listed securities "
        f"({len(companies)} companies after excluding ETFs and test issues)."
    )

    export_to_excel(df, companies, args.output, creation_time)
    print(f"Saved Excel workbook to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
