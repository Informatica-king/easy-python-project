"""Technical analysis bot — small-universe scores (docs/ta_bot_spec.md).

Usage:
    python -m sepa.ta_bot --tickers ECPG,NESR,NEO
    python -m sepa.ta_bot --watchlist --no-update
    python -m sepa.ta_bot --tickers NESR --chart
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from sepa.config import load_params
from sepa.data import store
from sepa.ta_hooks import TickerMeta, apply_hooks, parse_watchlist, watchlist_symbols
from sepa.ta_score import TAIL_BARS_DEFAULT, results_to_frame, score_frame

logger = logging.getLogger(__name__)

ACTION_ORDER = {"분할OK": 0, "홀드": 1, "대기": 2, "축소검토": 3, "신규금지": 4}


def _parse_tickers(raw: str) -> list[str]:
    parts = [p.strip().upper() for p in raw.replace(";", ",").split(",")]
    return [p for p in parts if p]


def load_watchlist(path: str | Path = "config/ta_watchlist.yaml") -> list[str]:
    return watchlist_symbols(parse_watchlist(path))


def run(
    tickers: list[str],
    *,
    cache_dir: str,
    lookback_years: int,
    update: bool,
    tail_bars: int,
    as_of: str | None,
    report_dir: str,
    meta_by_ticker: dict[str, TickerMeta] | None = None,
    hooks_as_of: date | None = None,
) -> pd.DataFrame:
    if not tickers:
        raise SystemExit("no tickers — pass --tickers or --watchlist")
    if len(tickers) > 20:
        raise SystemExit(f"refusing {len(tickers)} tickers; TA bot max is 20 (use screener for full scan)")

    data, failed = store.load_universe_history(tickers, cache_dir, lookback_years, update)
    if failed:
        logger.warning("failed to load: %s", ", ".join(failed))

    if as_of:
        cutoff = pd.Timestamp(as_of)
        data = {t: df.loc[:cutoff] for t, df in data.items()}

    meta_by_ticker = meta_by_ticker or {}
    # Hook calendar date: explicit --as-of, else bar date, else today
    hook_day = hooks_as_of
    if hook_day is None and as_of:
        hook_day = date.fromisoformat(as_of[:10])

    rows = []
    for t in tickers:
        df = data.get(t)
        if df is None:
            raw = score_frame(pd.DataFrame(), t, tail_bars)
        else:
            raw = score_frame(df, t, tail_bars)
        rows.append(apply_hooks(raw, meta_by_ticker.get(t), as_of=hook_day))

    out = results_to_frame(rows)
    if not out.empty:
        out["_ord"] = out["action"].map(lambda a: ACTION_ORDER.get(a, 9))
        out = out.sort_values(["_ord", "total"], ascending=[True, False]).drop(columns=["_ord"])
        out = out.reset_index(drop=True)

    Path(report_dir).mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    path = Path(report_dir) / f"ta_{stamp}.csv"
    out.to_csv(path, index=False)
    print(f"[ta] wrote {path} ({len(out)} rows, update={'on' if update else 'off'}, tail={tail_bars})")
    _print_table(out)
    return out


def _print_table(df: pd.DataFrame) -> None:
    if df.empty:
        print("(no rows)")
        return
    cols = [
        "ticker", "close", "trend", "momentum", "setup", "total",
        "rsi", "atr_pct", "status", "ta_action", "action", "override",
        "entry_lo", "entry_hi", "stop", "reason",
    ]
    show = df[[c for c in cols if c in df.columns]].copy()
    with pd.option_context("display.max_rows", 50, "display.width", 160, "display.max_colwidth", 48):
        print(show.to_string(index=False))


def _maybe_charts(tickers: list[str], report_dir: str) -> None:
    """Optional heavy path — only when user asks for charts."""
    from sepa import chart

    out_dir = Path(report_dir) / "charts"
    out_dir.mkdir(parents=True, exist_ok=True)
    for t in tickers:
        try:
            chart.main(["--ticker", t, "--out", str(out_dir), "--no-update"])
        except SystemExit:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("chart failed for %s: %s", t, exc)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="Lean TA scores for a shortlist (≤20 tickers)")
    p.add_argument("--tickers", type=str, default="", help="Comma-separated tickers")
    p.add_argument("--watchlist", action="store_true", help="Use config/ta_watchlist.yaml")
    p.add_argument("--watchlist-file", type=str, default="config/ta_watchlist.yaml")
    p.add_argument("--params", type=str, default="config/params.yaml")
    p.add_argument("--as-of", type=str, default=None)
    p.add_argument("--no-update", action="store_true", help="Cache only — zero network")
    p.add_argument("--tail-bars", type=int, default=TAIL_BARS_DEFAULT)
    p.add_argument("--chart", action="store_true", help="Also render SEPA charts (expensive)")
    p.add_argument(
        "--no-hooks",
        action="store_true",
        help="Skip EARN_D5/BAND portfolio hooks (raw TA only)",
    )
    args = p.parse_args(argv)

    params = load_params(args.params)
    wl_path = Path(args.watchlist_file)
    meta: dict[str, TickerMeta] = {}
    if wl_path.exists() and not args.no_hooks:
        try:
            meta = parse_watchlist(wl_path)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    if args.tickers.strip():
        tickers = _parse_tickers(args.tickers)
    elif args.watchlist:
        if not meta:
            meta = parse_watchlist(wl_path)
        tickers = watchlist_symbols(meta)
    else:
        p.error("pass --tickers or --watchlist")

    # When tickers passed explicitly, still apply meta for those symbols if present
    use_meta = {} if args.no_hooks else {t: meta[t] for t in tickers if t in meta}

    run(
        tickers,
        cache_dir=params.data.cache_dir,
        lookback_years=params.data.lookback_years,
        update=not args.no_update,
        tail_bars=args.tail_bars,
        as_of=args.as_of,
        report_dir=params.report_dir,
        meta_by_ticker=use_meta,
    )
    if args.chart:
        _maybe_charts(tickers, params.report_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
