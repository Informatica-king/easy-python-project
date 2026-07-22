"""경제뉴스() — overnight US market brief PDF.

Usage:
    python -m sepa.econ_news
    python -m sepa.econ_news --as-of 2026-07-21
"""

from __future__ import annotations

import argparse
import logging
import shutil
from datetime import date
from pathlib import Path

from sepa.econ_news_data import build_bundle
from sepa.econ_news_report import write_pdf

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="경제뉴스() — prior US session brief PDF")
    p.add_argument("--as-of", type=str, default=None, help="Session date YYYY-MM-DD")
    p.add_argument("--portfolio", type=str, default="config/portfolio_watch.yaml")
    p.add_argument("--out-dir", type=str, default="reports")
    args = p.parse_args(argv)

    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    print("[경제뉴스] collecting market bars + RSS + portfolio news…")
    bundle = build_bundle(session=as_of, portfolio_path=args.portfolio)
    stamp = bundle.session_date.isoformat()
    out = Path(args.out_dir) / f"Econ_News_{stamp}.pdf"
    art = Path("/opt/cursor/artifacts") / f"Econ_News_{stamp}.pdf"
    write_pdf(bundle, [out, art])
    print(f"[경제뉴스] session={stamp} mood={bundle.mood}")
    print(f"[경제뉴스] PDF {out} ({out.stat().st_size} bytes)")
    print(f"[경제뉴스] artifact {art}")
    for b in bundle.bullets:
        print(f"  • {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
