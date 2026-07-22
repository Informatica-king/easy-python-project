"""기술적분석() — Korean command entry + post-심층분석 auto-run.

Usage:
    python -m sepa.tech_analysis --tickers ECPG,NESR
    python -m sepa.tech_analysis --from-chase
    python -m sepa.tech_analysis --from-chase reports/chase_rr_20260721.json

After 심층분석, call::

    python -m sepa.tech_analysis --from-chase reports/chase_rr_YYYYMMDD.json
"""

from __future__ import annotations

import argparse
import logging
from datetime import date
from pathlib import Path

from sepa.chase_select import (
    ChaseRow,
    latest_chase_snapshot,
    load_chase_snapshot,
    select_buy_candidates,
    write_chase_snapshot,
)
from sepa.config import load_params
from sepa.ta_bot import run as ta_run
from sepa.ta_hooks import TickerMeta, load_hook_meta, parse_watchlist

logger = logging.getLogger(__name__)


def _merge_meta(
    tickers: list[str],
    chase_rows: list[ChaseRow],
    watchlist_path: str | Path,
    portfolio_path: str | Path = "config/portfolio_watch.yaml",
) -> dict[str, TickerMeta]:
    """Watchlist+portfolio meta + chase earn_date overlay (snapshot wins for earn_date)."""
    try:
        meta = load_hook_meta(watchlist_path, portfolio_path)
    except ValueError as exc:
        logger.warning("hook meta parse failed: %s", exc)
        meta = {}
        wl = Path(watchlist_path)
        if wl.exists():
            try:
                meta = dict(parse_watchlist(wl))
            except ValueError as exc2:
                logger.warning("watchlist parse failed: %s", exc2)

    by_t = {r.ticker: r for r in chase_rows}
    out: dict[str, TickerMeta] = {}
    for t in tickers:
        base = meta.get(t) or TickerMeta(symbol=t)
        crow = by_t.get(t)
        earn = base.earn_date
        if crow and crow.earn_date:
            earn = date.fromisoformat(crow.earn_date[:10])
        out[t] = TickerMeta(
            symbol=t,
            earn_date=earn,
            band_lo=base.band_lo,
            band_hi=base.band_hi,
            stop=base.stop,
            tp1=base.tp1,
            tp2=base.tp2,
            no_add=base.no_add,
        )
    return out


def run_from_chase(
    chase_path: str | Path | None = None,
    *,
    report_dir: str = "reports",
    watchlist_path: str = "config/ta_watchlist.yaml",
    update: bool = True,
    no_hooks: bool = False,
) -> list[str]:
    """Select buy candidates from Chase snapshot and run TA. Returns tickers used."""
    path = Path(chase_path) if chase_path else latest_chase_snapshot(report_dir)
    if path is None or not path.exists():
        print("[기술적분석] Chase 스냅샷 없음 — reports/chase_rr_YYYYMMDD.json 필요")
        print("  심층분석 종료 시 write_chase_snapshot 으로 저장하세요.")
        return []

    as_of, rows = load_chase_snapshot(path)
    picked = select_buy_candidates(rows)
    print(f"[기술적분석] Chase 스냅샷 {path.name} (as_of={as_of})")
    if not picked:
        print("[기술적분석] 매수 고려 종목 0 — 제외 규칙만 해당 (과열/매도/중하 등)")
        return []

    tickers = [r.ticker for r in picked]
    print("[기술적분석] 자동 선정 (Chase 순):")
    for r in picked:
        px = f"${r.px:.2f}" if r.px is not None else "—"
        print(f"  #{r.rank:<3} {r.ticker:<6} {px:<10} {r.chase}")

    params = load_params("config/params.yaml")
    meta = {} if no_hooks else _merge_meta(tickers, rows, watchlist_path)
    hooks_as_of = date.fromisoformat(as_of) if as_of else None

    ta_run(
        tickers,
        cache_dir=params.data.cache_dir,
        lookback_years=params.data.lookback_years,
        update=update,
        tail_bars=280,
        as_of=None,
        report_dir=params.report_dir,
        meta_by_ticker=meta,
        hooks_as_of=hooks_as_of,
    )
    return tickers


def run_tickers(
    tickers: list[str],
    *,
    update: bool = True,
    no_hooks: bool = False,
    watchlist_path: str = "config/ta_watchlist.yaml",
    portfolio_path: str = "config/portfolio_watch.yaml",
) -> None:
    params = load_params("config/params.yaml")
    meta = {}
    if not no_hooks:
        try:
            full = load_hook_meta(watchlist_path, portfolio_path)
            meta = {t: full[t] for t in tickers if t in full}
        except ValueError as exc:
            logger.warning("hook meta parse failed: %s", exc)
    ta_run(
        tickers,
        cache_dir=params.data.cache_dir,
        lookback_years=params.data.lookback_years,
        update=update,
        tail_bars=280,
        as_of=None,
        report_dir=params.report_dir,
        meta_by_ticker=meta,
        hooks_as_of=None,
    )


def after_deep_analysis(
    chase_rows: list[dict],
    *,
    as_of: str | date | None = None,
    report_dir: str = "reports",
    update: bool = True,
) -> list[str]:
    """Helper for 심층분석 generators: write snapshot then auto-run 기술적분석."""
    as_of_s = str(as_of or date.today())[:10]
    stamp = as_of_s.replace("-", "")
    path = Path(report_dir) / f"chase_rr_{stamp}.json"
    write_chase_snapshot(chase_rows, path, as_of=as_of_s, source="심층분석")
    print(f"[심층분석→기술적분석] wrote {path}")
    return run_from_chase(path, report_dir=report_dir, update=update)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="기술적분석() — TA shortlist / Chase auto")
    p.add_argument("--tickers", type=str, default="", help="Comma-separated tickers")
    p.add_argument(
        "--from-chase",
        nargs="?",
        const="",
        default=None,
        help="Use Chase snapshot (path optional = latest reports/chase_rr_*.json)",
    )
    p.add_argument("--no-update", action="store_true")
    p.add_argument("--no-hooks", action="store_true")
    p.add_argument("--watchlist-file", type=str, default="config/ta_watchlist.yaml")
    args = p.parse_args(argv)

    if args.from_chase is not None:
        path = args.from_chase or None
        run_from_chase(
            path,
            watchlist_path=args.watchlist_file,
            update=not args.no_update,
            no_hooks=args.no_hooks,
        )
        return 0

    if not args.tickers.strip():
        p.error("pass --tickers or --from-chase (기술적분석 자동 선정)")

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    print(f"[기술적분석] 수동 티커: {', '.join(tickers)}")
    run_tickers(
        tickers,
        update=not args.no_update,
        no_hooks=args.no_hooks,
        watchlist_path=args.watchlist_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
