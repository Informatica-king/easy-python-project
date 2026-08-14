#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기술적분석 유니버스 배치 (ta_bot 청크≤20 병합).

Usage:
  PYTHONPATH=src python3 reports/run_ta_universe.py BLZE,APPS,...
  PYTHONPATH=src python3 reports/run_ta_universe.py --from-file tickers.txt
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sepa.config import load_params  # noqa: E402
from sepa.ta_bot import ACTION_ORDER, run  # noqa: E402
from sepa.ta_hooks import load_hook_meta  # noqa: E402

CHUNK = 20


def _parse(raw: str) -> list[str]:
    parts = [p.strip().upper() for p in raw.replace(";", ",").replace("\n", ",").split(",")]
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="기술적분석 유니버스 배치")
    ap.add_argument("tickers", nargs="?", default="", help="Comma-separated tickers")
    ap.add_argument("--from-file", type=str, default="")
    ap.add_argument("--no-update", action="store_true")
    ap.add_argument("--no-hooks", action="store_true")
    ap.add_argument("--tag", type=str, default="", help="CSV suffix e.g. univ52")
    args = ap.parse_args(argv)

    raw = args.tickers
    if args.from_file:
        raw = Path(args.from_file).read_text(encoding="utf-8")
    tickers = _parse(raw)
    if not tickers:
        ap.error("pass tickers or --from-file")

    params = load_params("config/params.yaml")
    meta = {}
    if not args.no_hooks:
        meta = load_hook_meta("config/ta_watchlist.yaml", "config/portfolio_watch.yaml")
    use_meta = {t: meta[t] for t in tickers if t in meta}

    chunks = [tickers[i : i + CHUNK] for i in range(0, len(tickers), CHUNK)]
    frames: list[pd.DataFrame] = []
    for i, ch in enumerate(chunks, 1):
        print(f"===== chunk {i}/{len(chunks)} n={len(ch)} =====", flush=True)
        frames.append(
            run(
                ch,
                cache_dir=params.data.cache_dir,
                lookback_years=params.data.lookback_years,
                update=not args.no_update,
                tail_bars=60,
                as_of=None,
                report_dir=params.report_dir,
                meta_by_ticker={t: use_meta[t] for t in ch if t in use_meta},
            )
        )

    out = pd.concat(frames, ignore_index=True)
    if not out.empty:
        out["_ord"] = out["action"].map(lambda a: ACTION_ORDER.get(a, 9))
        out = out.sort_values(["_ord", "total"], ascending=[True, False]).drop(columns=["_ord"])
        out = out.reset_index(drop=True)

    stamp = datetime.now().strftime("%Y%m%d")
    tag = f"_{args.tag}" if args.tag else f"_univ{len(tickers)}"
    path = Path(params.report_dir) / f"ta_{stamp}{tag}.csv"
    daily = Path(params.report_dir) / f"ta_{stamp}.csv"
    out.to_csv(path, index=False)
    out.to_csv(daily, index=False)
    art = Path("/opt/cursor/artifacts") / path.name
    art.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(art, index=False)
    print(f"[ta-batch] {path} rows={len(out)}")
    if not out.empty:
        print(out["action"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
