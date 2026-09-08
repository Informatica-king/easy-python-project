"""Fill missing go-day analysis CSVs quickly (D30).

Purpose: when daily ``!sepa.go`` is skipped, restore/rebuild only the
minimum artifacts needed for later model analysis — not a full go replay.

See ``docs/gap_fill_plan.md``.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from sepa.anal_report import github_repo_slug, pdf_release_tag
from sepa.analyze import print_fund_median_copy_list
from sepa.config import load_params
from sepa.perf_ledger import ingest_missing_fundamental_stamps, update_perf_ledger
from sepa.result_ledger import _stamp_as_of
from sepa.sepatop import (
    append_membership_panel,
    list_membership_files,
    load_first_seen,
    load_membership_history,
    membership_changes_frame,
    membership_diff,
    presence_table,
    previous_membership,
    save_first_seen,
    save_membership,
    sepatop_dirs,
    update_first_seen,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_DAYS = 10
SOURCE_RESTORED = "release_restore"
SOURCE_REBUILD = "asof_rebuild"

# Day-specific assets needed for analysis (no PDF/charts/ZIP).
_ROOT_PATTERNS = (
    "stage2_{stamp}.csv",
    "fundamental_{stamp}.csv",
    "rs_soft_drops_{stamp}.csv",
    "fund_median_tickers_{stamp}.txt",
    "fund_quantile_{stamp}.csv",
    "diagnostics_summary_{stamp}.csv",
    "params_{stamp}.yaml",
    "params_meta_{stamp}.csv",
)
_SEPATOP_PATTERNS = (
    "membership_{stamp}.csv",
    "membership_changes_{stamp}.csv",
    "presence_{stamp}.csv",
    "always_present_{stamp}.csv",
    "tenure_{stamp}.csv",
    "membership_event_fwd_{stamp}.csv",
)


@dataclass
class GapFillResult:
    restored: list[str] = field(default_factory=list)
    rebuilt: list[str] = field(default_factory=list)
    skipped_local: list[str] = field(default_factory=list)
    skipped_weekend: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    dry_run_gaps: list[str] = field(default_factory=list)
    truncated: bool = False
    max_days: int = DEFAULT_MAX_DAYS


def parse_stamp(stamp: str) -> date:
    s = str(stamp).replace("-", "")
    if len(s) != 8 or not s.isdigit():
        raise ValueError(f"bad stamp: {stamp}")
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def date_to_stamp(d: date) -> str:
    return d.strftime("%Y%m%d")


def stamp_to_as_of(stamp: str) -> str:
    return _stamp_as_of(str(stamp).replace("-", ""))


def trading_days(start: date, end: date) -> list[date]:
    """Weekdays only (v1 — no US holiday calendar)."""
    if end < start:
        return []
    out: list[date] = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            out.append(cur)
        cur += timedelta(days=1)
    return out


def local_fundamental_stamps(report_dir: str | Path) -> set[str]:
    report_dir = Path(report_dir)
    found: set[str] = set()
    for path in report_dir.glob("fundamental_*.csv"):
        m = re.fullmatch(r"fundamental_(\d{8})\.csv", path.name)
        if m:
            found.add(m.group(1))
    return found


def list_anal_release_stamps(*, repo: str | None = None) -> set[str]:
    """Return stamps that have a ``sepa-anal-YYYYMMDD`` GitHub release."""
    repo = repo or github_repo_slug()
    if not repo or shutil.which("gh") is None:
        return set()
    try:
        proc = subprocess.run(
            ["gh", "release", "list", "--repo", repo, "--limit", "200"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("gh release list failed: %s", exc)
        return set()
    if proc.returncode != 0:
        logger.warning("gh release list error: %s", (proc.stderr or proc.stdout or "").strip())
        return set()
    stamps: set[str] = set()
    for line in (proc.stdout or "").splitlines():
        parts = line.split("\t")
        tag = parts[2].strip() if len(parts) >= 3 else ""
        m = re.fullmatch(r"sepa-anal-(\d{8})", tag)
        if m:
            stamps.add(m.group(1))
    return stamps


def _write_source_meta(report_dir: Path, stamp: str, source: str) -> Path:
    meta_dir = report_dir / "gap_fill"
    meta_dir.mkdir(parents=True, exist_ok=True)
    path = meta_dir / f"source_{stamp}.txt"
    path.write_text(
        f"stamp={stamp}\nsource={source}\n"
        f"written_utc={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n",
        encoding="utf-8",
    )
    return path


def restore_stamp_from_release(
    stamp: str,
    *,
    report_dir: str | Path,
    sepatop_report: str | Path,
    repo: str | None = None,
    force: bool = False,
) -> bool:
    """Download analysis CSVs for one stamp from ``sepa-anal-*``."""
    report_dir = Path(report_dir)
    sepatop_report = Path(sepatop_report)
    fund_path = report_dir / f"fundamental_{stamp}.csv"
    if fund_path.exists() and not force:
        return True

    repo = repo or github_repo_slug()
    if not repo or shutil.which("gh") is None:
        logger.warning("cannot restore %s: gh/repo unavailable", stamp)
        return False

    tag = pdf_release_tag(stamp)
    patterns = [p.format(stamp=stamp) for p in _ROOT_PATTERNS + _SEPATOP_PATTERNS]
    with tempfile.TemporaryDirectory(prefix=f"sepa-gap-{stamp}-") as tmp:
        tmp_path = Path(tmp)
        cmd = [
            "gh",
            "release",
            "download",
            tag,
            "--repo",
            repo,
            "--dir",
            str(tmp_path),
            "--clobber",
        ]
        for pat in patterns:
            cmd.extend(["-p", pat])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
        if proc.returncode != 0:
            logger.warning(
                "release download %s: %s",
                tag,
                (proc.stderr or proc.stdout or "failed").strip()[:300],
            )

        sepatop_report.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)
        moved = 0
        sepatop_names = {p.format(stamp=stamp) for p in _SEPATOP_PATTERNS}
        for path in tmp_path.iterdir():
            if not path.is_file():
                continue
            name = path.name
            dest = sepatop_report / name if name in sepatop_names else report_dir / name
            shutil.copy2(path, dest)
            moved += 1

        if not fund_path.exists():
            logger.warning("restore %s incomplete: fundamental missing", stamp)
            return False

        _write_source_meta(report_dir, stamp, SOURCE_RESTORED)
        logger.info("restored stamp %s (%d files)", stamp, moved)
        return True


def save_light_membership(
    *,
    fund_df: pd.DataFrame,
    report_dir: str | Path,
    cache_dir: str | Path,
    stamp: str,
    as_of: str,
) -> Path:
    """Persist membership/changes/panel/presence without charts or index."""
    report_dir = Path(report_dir)
    sepatop_report, sepatop_data = sepatop_dirs(report_dir, cache_dir)
    sepatop_report.mkdir(parents=True, exist_ok=True)

    work = fund_df.copy()
    work["ticker"] = work["ticker"].astype(str).str.upper()
    if "market_cap" in work.columns:
        mcap = pd.to_numeric(work["market_cap"], errors="coerce")
        fund = pd.to_numeric(work.get("fund_score"), errors="coerce")
        keep = (fund > 0) & mcap.notna() & (mcap >= 1_000_000_000)
        work = work.loc[keep].copy()

    prev_set, prev_stamp = previous_membership(sepatop_report, stamp)
    curr_set = set(work["ticker"].astype(str).str.upper())
    entered, exited = membership_diff(prev_set, curr_set)

    mem_path = sepatop_report / f"membership_{stamp}.csv"
    save_membership(mem_path, work, as_of)

    changes = membership_changes_frame(
        stamp=stamp,
        as_of=as_of,
        prev_stamp=prev_stamp,
        entered=entered,
        exited=exited,
    )
    changes.to_csv(sepatop_report / f"membership_changes_{stamp}.csv", index=False)

    append_membership_panel(
        sepatop_report / "membership_panel.csv",
        work,
        stamp=stamp,
        as_of=as_of,
    )

    first_seen = load_first_seen(sepatop_data)
    first_seen = update_first_seen(first_seen, list(curr_set), as_of)
    save_first_seen(sepatop_data, first_seen)

    history = load_membership_history(sepatop_report)
    presence = presence_table(history)
    presence.to_csv(sepatop_report / f"presence_{stamp}.csv", index=False)
    always = presence.loc[presence["always_present"]].copy() if not presence.empty else presence
    always.to_csv(sepatop_report / f"always_present_{stamp}.csv", index=False)
    return mem_path


def rebuild_panels(report_dir: str | Path, cache_dir: str | Path) -> dict:
    """Reassemble membership panel/presence and ingest any missing perf stamps."""
    report_dir = Path(report_dir)
    sepatop_report, _ = sepatop_dirs(report_dir, cache_dir)

    panel_rows: list[pd.DataFrame] = []
    for path in list_membership_files(sepatop_report):
        stamp = path.stem.replace("membership_", "")
        as_of = stamp_to_as_of(stamp)
        try:
            df = pd.read_csv(path)
        except Exception:  # noqa: BLE001
            continue
        cols = [c for c in ["ticker", "name", "fund_score", "rs_rank", "market_cap", "close"] if c in df.columns]
        today = df[cols].copy()
        today["stamp"] = stamp
        today["as_of"] = as_of
        today["ticker"] = today["ticker"].astype(str).str.upper()
        panel_rows.append(today)
    history = load_membership_history(sepatop_report)
    if panel_rows:
        panel = pd.concat(panel_rows, ignore_index=True)
        ordered = ["stamp", "as_of", "ticker"] + [
            c for c in ["name", "fund_score", "rs_rank", "market_cap", "close"] if c in panel.columns
        ]
        panel = panel[[c for c in ordered if c in panel.columns]].sort_values(["stamp", "ticker"])
        sepatop_report.mkdir(parents=True, exist_ok=True)
        panel.to_csv(sepatop_report / "membership_panel.csv", index=False)

    if history:
        presence = presence_table(history)
        latest = history[-1][0]
        presence.to_csv(sepatop_report / f"presence_{latest}.csv", index=False)
        always = presence.loc[presence["always_present"]].copy() if not presence.empty else presence
        always.to_csv(sepatop_report / f"always_present_{latest}.csv", index=False)

    ingested = ingest_missing_fundamental_stamps(report_dir, cache_dir, publish=False)
    stamps = sorted(local_fundamental_stamps(report_dir))
    if stamps:
        latest = stamps[-1]
        fund = pd.read_csv(report_dir / f"fundamental_{latest}.csv")
        soft_path = report_dir / f"rs_soft_drops_{latest}.csv"
        soft = pd.read_csv(soft_path) if soft_path.exists() else None
        stage2 = report_dir / f"stage2_{latest}.csv"
        n_stage2 = len(pd.read_csv(stage2)) if stage2.exists() else None
        update_perf_ledger(
            report_dir=report_dir,
            cache_dir=cache_dir,
            stamp=latest,
            fund_df=fund,
            soft_drops=soft,
            n_stage2=n_stage2,
            publish=False,
            backfill_all_history=True,
        )
    return {"ingested": ingested, "membership_stamps": len(history)}


def rebuild_day_asof(
    as_of: str,
    *,
    config: str = "config/params.yaml",
    report_dir: str | Path | None = None,
    cache_dir: str | Path | None = None,
) -> bool:
    """Lightweight as-of scan+fund+membership+perf (no anal/PDF/charts/release)."""
    from sepa import fundamental, screener

    params = load_params(config)
    report_dir = Path(report_dir or params.report_dir)
    cache_dir = Path(cache_dir or params.data.cache_dir)
    stamp = as_of.replace("-", "")

    screener.main(["--full", "--as-of", as_of, "--no-update", "--config", config])
    stage2 = report_dir / f"stage2_{stamp}.csv"
    if not stage2.exists():
        logger.error("asof rebuild %s: stage2 missing", stamp)
        return False

    fundamental.main(
        ["--from-stage2", str(stage2), "--as-of", as_of, "--no-update", "--config", config]
    )
    fund_path = report_dir / f"fundamental_{stamp}.csv"
    if not fund_path.exists():
        logger.error("asof rebuild %s: fundamental missing", stamp)
        return False

    fund_df = pd.read_csv(fund_path)
    print_fund_median_copy_list(
        fund_df,
        out_path=report_dir / f"fund_median_tickers_{stamp}.txt",
        banner=False,
    )
    soft_path = report_dir / f"rs_soft_drops_{stamp}.csv"
    soft = pd.read_csv(soft_path) if soft_path.exists() else None

    as_of_iso = as_of if "-" in as_of else stamp_to_as_of(stamp)
    save_light_membership(
        fund_df=fund_df,
        report_dir=report_dir,
        cache_dir=cache_dir,
        stamp=stamp,
        as_of=as_of_iso,
    )
    n_stage2 = len(pd.read_csv(stage2))
    update_perf_ledger(
        report_dir=report_dir,
        cache_dir=cache_dir,
        stamp=stamp,
        fund_df=fund_df,
        soft_drops=soft,
        n_stage2=n_stage2,
        publish=False,
        backfill_all_history=True,
    )
    _write_source_meta(report_dir, stamp, SOURCE_REBUILD)
    return True


def fill_gaps(
    *,
    start: str | date | None = None,
    end: str | date | None = None,
    config: str = "config/params.yaml",
    dry_run: bool = False,
    max_days: int = DEFAULT_MAX_DAYS,
    restore: bool = True,
    rebuild: bool = True,
    force: bool = False,
    repo: str | None = None,
) -> GapFillResult:
    """Restore and/or lightly rebuild missing trading-day analysis CSVs."""
    params = load_params(config)
    report_dir = Path(params.report_dir)
    cache_dir = Path(params.data.cache_dir)
    sepatop_report, _ = sepatop_dirs(report_dir, cache_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    local = local_fundamental_stamps(report_dir)
    if end is None:
        end_d = date.today()
    elif isinstance(end, date):
        end_d = end
    else:
        end_d = parse_stamp(str(end).replace("-", ""))

    if start is None:
        if local:
            start_d = parse_stamp(min(local))
        else:
            start_d = end_d - timedelta(days=30)
    elif isinstance(start, date):
        start_d = start
    else:
        start_d = parse_stamp(str(start).replace("-", ""))

    result = GapFillResult(max_days=max_days)
    days = trading_days(start_d, end_d)
    cur = start_d
    while cur <= end_d:
        if cur.weekday() >= 5:
            result.skipped_weekend.append(date_to_stamp(cur))
        cur += timedelta(days=1)

    release_stamps = list_anal_release_stamps(repo=repo) if restore else set()
    gaps: list[date] = []
    for d in days:
        stamp = date_to_stamp(d)
        if stamp in local and not force:
            result.skipped_local.append(stamp)
            continue
        gaps.append(d)

    if len(gaps) > max_days:
        result.truncated = True
        gaps = gaps[:max_days]

    if dry_run:
        result.dry_run_gaps = [date_to_stamp(d) for d in gaps]
        return result

    for d in gaps:
        stamp = date_to_stamp(d)
        as_of = d.isoformat()
        ok = False
        if restore and stamp in release_stamps:
            ok = restore_stamp_from_release(
                stamp,
                report_dir=report_dir,
                sepatop_report=sepatop_report,
                repo=repo,
                force=force,
            )
            if ok:
                result.restored.append(stamp)
                local.add(stamp)
                continue
        if rebuild:
            try:
                ok = rebuild_day_asof(
                    as_of,
                    config=config,
                    report_dir=report_dir,
                    cache_dir=cache_dir,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("rebuild failed %s: %s", stamp, exc)
                ok = False
            if ok:
                result.rebuilt.append(stamp)
                local.add(stamp)
                continue
        result.failed.append(stamp)

    if result.restored or result.rebuilt:
        rebuild_panels(report_dir, cache_dir)

    return result


def print_gap_fill_summary(result: GapFillResult) -> None:
    print("\n" + "=" * 64)
    print("  SEPA gap fill  (analysis CSVs only — no PDF/charts)")
    print("=" * 64)
    if result.dry_run_gaps:
        print(f"  dry-run gaps ({len(result.dry_run_gaps)}): {', '.join(result.dry_run_gaps)}")
    print(f"  restored : {len(result.restored)}  {', '.join(result.restored) or '-'}")
    print(f"  rebuilt  : {len(result.rebuilt)}  {', '.join(result.rebuilt) or '-'}")
    print(f"  skip local: {len(result.skipped_local)}")
    print(f"  skip weekend: {len(result.skipped_weekend)}")
    if result.failed:
        print(f"  failed  : {', '.join(result.failed)}")
    if result.truncated:
        print(f"  [note] truncated to max_days={result.max_days}")
    print("=" * 64 + "\n")


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Fill missing SEPA go analysis days (lightweight)")
    p.add_argument("--config", default="config/params.yaml")
    p.add_argument("--from", dest="date_from", default=None, help="YYYYMMDD or YYYY-MM-DD")
    p.add_argument("--to", dest="date_to", default=None, help="YYYYMMDD or YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-days", type=int, default=DEFAULT_MAX_DAYS)
    p.add_argument("--no-restore", action="store_true")
    p.add_argument("--no-rebuild", action="store_true")
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = fill_gaps(
        start=args.date_from,
        end=args.date_to,
        config=args.config,
        dry_run=bool(args.dry_run),
        max_days=int(args.max_days),
        restore=not args.no_restore,
        rebuild=not args.no_rebuild,
        force=bool(args.force),
    )
    print_gap_fill_summary(result)
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
