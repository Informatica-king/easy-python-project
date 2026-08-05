#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수익구조분석 멀티티커 배치 실행기.

각 티커별 PDF를 개별 생성합니다 (한 PDF에 합치지 않음).

Usage:
  python reports/run_revenue_structure.py ECPG AMRX LASR NESR RELY
  python reports/run_revenue_structure.py --portfolio
  python reports/run_revenue_structure.py --list

Notes:
  - 티커마다 ``reports/generate_revenue_structure_<ticker>.py`` 가 있어야 함.
  - SCHD 등 ETF/생성기 없는 티커는 skip.
  - 생성기 품질은 티커별로 다름(최신 compete 포함 여부는 --list 참고).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ARTIFACTS = Path("/opt/cursor/artifacts")
ASSETS = ROOT / "assets"

# Default portfolio equity names from recent confirmed book
# (SCHD = ETF buffer — no revenue-structure generator)
DEFAULT_PORTFOLIO = ["ECPG", "AMRX", "LASR", "NESR", "RELY"]

SKIP_REASON = {
    "SCHD": "ETF 버퍼 — 개별기업 수익구조분석 대상 아님",
}


@dataclass
class GenInfo:
    ticker: str
    script: Path
    has_compete: bool
    has_price: bool
    asof: str | None


def _discover(ticker: str) -> GenInfo | None:
    t = ticker.upper().strip()
    script = REPORTS / f"generate_revenue_structure_{t.lower()}.py"
    if not script.exists():
        return None
    text = script.read_text(encoding="utf-8", errors="ignore")
    asof_m = re.search(r'ASOF\s*=\s*["\']([^"\']+)["\']', text)
    return GenInfo(
        ticker=t,
        script=script,
        has_compete="build_compete_charts" in text or "rev_compete" in text,
        has_price="build_and_insert_price" in text or "rev_price_chart" in text,
        asof=asof_m.group(1) if asof_m else None,
    )


def list_available() -> list[GenInfo]:
    infos = []
    for p in sorted(REPORTS.glob("generate_revenue_structure_*.py")):
        # skip this runner if ever named similarly
        stem = p.stem.replace("generate_revenue_structure_", "").upper()
        if stem in {"", "BATCH", "RUN"}:
            continue
        info = _discover(stem)
        if info:
            infos.append(info)
    return infos


def load_portfolio_tickers(yaml_path: Path | None = None) -> list[str]:
    """Prefer portfolio_watch.yaml holdings; fall back to DEFAULT_PORTFOLIO."""
    path = yaml_path or (ROOT / "config" / "portfolio_watch.yaml")
    if not path.exists():
        return list(DEFAULT_PORTFOLIO)
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return list(DEFAULT_PORTFOLIO)

    tickers: list[str] = []
    # legacy roles block (optional; grade-era yaml may omit)
    strat = data.get("strategy") or {}
    roles = strat.get("roles") or {}
    for key in ("core", "satellite", "buffer", "candidate_core", "A", "B", "C"):
        for t in roles.get(key) or []:
            if isinstance(t, str) and t.upper() not in tickers:
                tickers.append(t.upper())
    # holdings blocks if present
    for block in ("holdings", "positions", "names"):
        raw = data.get(block)
        if isinstance(raw, dict):
            for t in raw:
                if str(t).upper() not in tickers:
                    tickers.append(str(t).upper())
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, str) and item.upper() not in tickers:
                    tickers.append(item.upper())
                elif isinstance(item, dict) and item.get("ticker"):
                    t = str(item["ticker"]).upper()
                    if t not in tickers:
                        tickers.append(t)
    # merge confirmed book defaults that may be missing from stale yaml
    for t in DEFAULT_PORTFOLIO:
        if t not in tickers:
            tickers.append(t)
    return tickers


def run_one(ticker: str, *, python: str = sys.executable) -> dict:
    """Run one ticker via subprocess (isolates matplotlib/weasy state)."""
    import os

    t = ticker.upper().strip()
    if t in SKIP_REASON:
        return {"ticker": t, "ok": False, "skipped": True, "reason": SKIP_REASON[t]}
    info = _discover(t)
    if info is None:
        return {
            "ticker": t,
            "ok": False,
            "skipped": True,
            "reason": f"생성기 없음: reports/generate_revenue_structure_{t.lower()}.py",
        }
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    try:
        proc = subprocess.run(
            [python, str(info.script)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode != 0:
            return {
                "ticker": t,
                "ok": False,
                "skipped": False,
                "asof": info.asof,
                "error": (proc.stderr or proc.stdout or "nonzero exit")[-1200:],
            }
        pdfs = _find_pdfs(t)
        return {
            "ticker": t,
            "ok": True,
            "skipped": False,
            "asof": info.asof,
            "compete": info.has_compete,
            "price": info.has_price,
            "pdfs": [str(p) for p in pdfs],
            "log_tail": (proc.stdout or "")[-400:],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ticker": t,
            "ok": False,
            "skipped": False,
            "error": f"{exc}\n{traceback.format_exc()[-800:]}",
        }


def _find_pdfs(ticker: str) -> list[Path]:
    name = f"{ticker.upper()}_Revenue_Structure_Analysis.pdf"
    out = []
    for base in (ARTIFACTS, REPORTS, ASSETS):
        p = base / name
        if p.exists():
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="수익구조분석 멀티티커 배치 (티커별 PDF)")
    ap.add_argument("tickers", nargs="*", help="티커 목록 (예: ECPG AMRX LASR)")
    ap.add_argument(
        "--portfolio",
        action="store_true",
        help="config/portfolio_watch.yaml 역할·보유 티커 일괄",
    )
    ap.add_argument(
        "--book",
        action="store_true",
        help=f"확정 북 기본 세트 일괄 ({', '.join(DEFAULT_PORTFOLIO)})",
    )
    ap.add_argument("--list", action="store_true", help="사용 가능한 생성기 목록")
    ap.add_argument("--dry-run", action="store_true", help="실행 없이 대상만 표시")
    args = ap.parse_args(argv)

    if args.list:
        print(f"{'TICKER':6} {'ASOF':12} {'PRICE':5} {'COMPETE':7} SCRIPT")
        for info in list_available():
            print(
                f"{info.ticker:6} {(info.asof or '—'):12} "
                f"{'Y' if info.has_price else '—':5} "
                f"{'Y' if info.has_compete else '—':7} "
                f"{info.script.name}"
            )
        return 0

    tickers: list[str] = []
    if args.book:
        tickers.extend(DEFAULT_PORTFOLIO)
    if args.portfolio:
        tickers.extend(load_portfolio_tickers())
    tickers.extend(t.upper() for t in args.tickers)

    # de-dupe preserve order
    seen = set()
    ordered = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            ordered.append(t)

    if not ordered:
        ap.print_help()
        print("\n예: python reports/run_revenue_structure.py --book")
        print("    python reports/run_revenue_structure.py ECPG AMRX NESR")
        print("    python reports/run_revenue_structure.py --list")
        return 2

    print(f"수익구조분석 배치 n={len(ordered)} → {', '.join(ordered)}")
    if args.dry_run:
        for t in ordered:
            if t in SKIP_REASON:
                print(f"  SKIP {t}: {SKIP_REASON[t]}")
                continue
            info = _discover(t)
            if not info:
                print(f"  MISS {t}: 생성기 없음")
            else:
                print(
                    f"  OK   {t}: asof={info.asof} price={info.has_price} "
                    f"compete={info.has_compete}"
                )
        return 0

    results = []
    for t in ordered:
        print(f"\n===== {t} =====")
        r = run_one(t)
        results.append(r)
        if r.get("skipped"):
            print(f"SKIP {t}: {r.get('reason')}")
        elif r.get("ok"):
            print(f"OK   {t} asof={r.get('asof')} compete={r.get('compete')}")
            for p in r.get("pdfs") or []:
                print(f"     PDF {p}")
        else:
            print(f"FAIL {t}: {str(r.get('error'))[:500]}")

    ok_n = sum(1 for r in results if r.get("ok"))
    skip_n = sum(1 for r in results if r.get("skipped"))
    fail_n = sum(1 for r in results if not r.get("ok") and not r.get("skipped"))
    print(f"\n요약: ok={ok_n} skip={skip_n} fail={fail_n} / total={len(results)}")
    # write machine-readable summary
    import json

    summary_path = REPORTS / "revenue_batch_last.json"
    summary_path.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"summary {summary_path}")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
