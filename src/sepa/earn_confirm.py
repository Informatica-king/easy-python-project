"""On-demand confirmed-earn SSOT tools (local I/O only by default).

No network in sync/diff/set/show. Hot path readers just open YAML.
Yahoo/IR scraping is intentionally out of scope (compute + false confirms).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
import yaml

from sepa.earn_calendar import (
    DEFAULT_CONFIRMED_PATH,
    DEFAULT_PORTFOLIO_PATH,
    load_confirmed_earn_file,
    load_confirmed_earn_map,
    parse_earn_date,
    save_confirmed_earn_file,
)


def cmd_show(args: argparse.Namespace) -> int:
    path = Path(args.confirmed)
    entries = load_confirmed_earn_file(path)
    if not entries:
        print(f"(empty) {path}")
        return 0
    for t in sorted(entries):
        e = entries[t]
        print(f"{t:6} {e['earn_date']}  {e.get('note') or ''}")
    print(f"# {len(entries)} confirmed · {path}")
    return 0


def cmd_sync_portfolio(args: argparse.Namespace) -> int:
    """Copy holdings earn_date → earn_confirmed (local). Does not delete extras."""
    port = Path(args.portfolio)
    confirmed_path = Path(args.confirmed)
    raw = yaml.safe_load(port.read_text(encoding="utf-8")) or {}
    existing = load_confirmed_earn_file(confirmed_path)
    today = date.today().isoformat()
    added = updated = 0
    for h in raw.get("holdings") or []:
        if not h or h.get("role") == "exited":
            continue
        t = str(h.get("ticker") or "").strip().upper()
        ed = parse_earn_date(h.get("earn_date"))
        if not t or ed is None:
            continue
        iso = ed.isoformat()
        prev = existing.get(t)
        if prev and prev.get("earn_date") == iso:
            continue
        if prev:
            updated += 1
        else:
            added += 1
        existing[t] = {
            "earn_date": iso,
            "note": str(h.get("note") or "portfolio SSOT")[:80],
            "confirmed_on": today,
        }
    as_of = str(raw.get("as_of") or today)
    save_confirmed_earn_file(
        confirmed_path,
        existing,
        as_of=as_of,
        note="portfolio sync · estimate 자동승격 금지",
    )
    print(f"sync-portfolio → {confirmed_path} added={added} updated={updated} total={len(existing)}")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Compare confirmed SSOT vs rank JSON estimates (local files only)."""
    rank_path = Path(args.rank)
    confirmed = load_confirmed_earn_map(
        portfolio_path=Path(args.portfolio),
        confirmed_path=Path(args.confirmed),
    )
    rank = json.loads(rank_path.read_text(encoding="utf-8"))
    rows = rank.get("rows") or []
    mismatch = 0
    estimate_only = 0
    for r in rows:
        t = str(r.get("t") or r.get("ticker") or "").upper()
        if not t:
            continue
        est = parse_earn_date(r.get("earnDate") or r.get("earn_date"))
        conf = confirmed.get(t)
        if conf and est and conf != est:
            print(f"MISMATCH {t:6} confirmed={conf} estimate={est}")
            mismatch += 1
        elif est and not conf:
            # only print if near-term-ish or --all
            if args.all or (est and abs((est - date.today()).days) <= 45):
                print(f"EST_ONLY {t:6} estimate={est}  (not in confirmed SSOT)")
                estimate_only += 1
        elif conf and not est:
            print(f"CONF_ONLY {t:6} confirmed={conf}")
    print(f"# diff rank={rank_path.name} mismatch={mismatch} est_only_shown={estimate_only}")
    print("# Tip: IR 확인 후 `earn_confirm set TICKER DATE` — Yahoo만으로 confirmed 쓰지 말 것")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    t = str(args.ticker).strip().upper()
    ed = parse_earn_date(args.date)
    if not t or ed is None:
        print("usage: set TICKER YYYY-MM-DD", file=sys.stderr)
        return 2
    path = Path(args.confirmed)
    entries = load_confirmed_earn_file(path)
    entries[t] = {
        "earn_date": ed.isoformat(),
        "note": args.note or "IR confirmed",
        "confirmed_on": date.today().isoformat(),
    }
    save_confirmed_earn_file(path, entries)
    print(f"set {t} {ed.isoformat()} → {path}")
    return 0


def cmd_unset(args: argparse.Namespace) -> int:
    t = str(args.ticker).strip().upper()
    path = Path(args.confirmed)
    entries = load_confirmed_earn_file(path)
    if t not in entries:
        print(f"missing {t}")
        return 1
    del entries[t]
    save_confirmed_earn_file(path, entries)
    print(f"unset {t} → {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Confirmed earn SSOT (local only · no Yahoo auto-promote)"
    )
    ap.add_argument(
        "--confirmed",
        default=str(DEFAULT_CONFIRMED_PATH),
        help="path to earn_confirmed.yaml",
    )
    ap.add_argument(
        "--portfolio",
        default=str(DEFAULT_PORTFOLIO_PATH),
        help="path to portfolio_watch.yaml",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_show = sub.add_parser("show", help="list confirmed entries")
    p_show.set_defaults(func=cmd_show)

    p_sync = sub.add_parser("sync-portfolio", help="copy holdings earn_date → confirmed")
    p_sync.set_defaults(func=cmd_sync_portfolio)

    p_diff = sub.add_parser("diff", help="diff confirmed vs rank estimates (local JSON)")
    p_diff.add_argument("--rank", required=True, help="reports/rank_YYYYMMDD.json")
    p_diff.add_argument("--all", action="store_true", help="show all estimate-only rows")
    p_diff.set_defaults(func=cmd_diff)

    p_set = sub.add_parser("set", help="manually confirm a date (after IR check)")
    p_set.add_argument("ticker")
    p_set.add_argument("date")
    p_set.add_argument("--note", default="IR confirmed")
    p_set.set_defaults(func=cmd_set)

    p_unset = sub.add_parser("unset", help="remove confirmed entry")
    p_unset.add_argument("ticker")
    p_unset.set_defaults(func=cmd_unset)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
