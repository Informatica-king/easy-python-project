"""Cleanup old GitHub Releases and duplicate/force-tracked PDFs.

Phone local copies are the owner's archive; GitHub Releases are convenience
download links only. Prefer regeneration over git-tracked binaries.

Usage:
    python -m sepa.cleanup_artifacts                  # dry-run all
    python -m sepa.cleanup_artifacts releases
    python -m sepa.cleanup_artifacts releases --apply --yes
    python -m sepa.cleanup_artifacts git-index
    python -m sepa.cleanup_artifacts git-index --apply --yes
    python -m sepa.cleanup_artifacts dupes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

DEFAULT_CONFIG = Path("config/artifact_retention.yaml")
REV_PREFIX = "sepa-rev-"


@dataclass
class ReleaseInfo:
    tag: str
    published_at: str
    is_latest: bool
    asset_bytes: int


@dataclass
class PlanItem:
    action: str
    target: str
    reason: str
    bytes: int = 0


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    if yaml is None:
        raise SystemExit("PyYAML required: pip install pyyaml")
    if not path.exists():
        raise SystemExit(f"config missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data


def _run_gh(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ["gh", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if check and proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "gh failed").strip()
        raise RuntimeError(f"gh {' '.join(args)}: {err}")
    return proc


def list_releases() -> list[ReleaseInfo]:
    proc = _run_gh(
        [
            "release",
            "list",
            "--limit",
            "100",
            "--json",
            "tagName,publishedAt,isLatest",
        ]
    )
    rows = json.loads(proc.stdout or "[]")
    out: list[ReleaseInfo] = []
    for r in rows:
        tag = r["tagName"]
        size = 0
        try:
            detail = _run_gh(
                ["api", f"repos/{{owner}}/{{repo}}/releases/tags/{tag}"],
                check=False,
            )
            if detail.returncode == 0:
                payload = json.loads(detail.stdout or "{}")
                size = sum(int(a.get("size") or 0) for a in payload.get("assets") or [])
        except Exception:  # noqa: BLE001
            size = 0
        out.append(
            ReleaseInfo(
                tag=tag,
                published_at=str(r.get("publishedAt") or ""),
                is_latest=bool(r.get("isLatest")),
                asset_bytes=size,
            )
        )
    out.sort(key=lambda x: x.published_at, reverse=True)
    return out


def _family_key(tag: str, families: dict[str, Any]) -> str | None:
    # longest prefix match among configured family keys
    keys = sorted(families.keys(), key=len, reverse=True)
    for k in keys:
        if tag == k or tag.startswith(k + "-") or tag.startswith(k):
            # sepa-anal matches sepa-anal-20260726
            if tag.startswith(k + "-") or tag == k:
                return k
    return None


def plan_release_deletions(
    releases: list[ReleaseInfo],
    cfg: dict[str, Any],
) -> list[PlanItem]:
    families = (cfg.get("releases") or {})
    plan: list[PlanItem] = []

    # Date-style families: keep_last
    by_fam: dict[str, list[ReleaseInfo]] = {}
    rev_tags: list[ReleaseInfo] = []
    unmatched: list[ReleaseInfo] = []

    for rel in releases:
        fam = _family_key(rel.tag, families)
        if fam is None:
            unmatched.append(rel)
            continue
        rules = families[fam] or {}
        if rules.get("keep_latest_per_ticker"):
            rev_tags.append(rel)
        elif "keep_last" in rules:
            by_fam.setdefault(fam, []).append(rel)
        else:
            unmatched.append(rel)

    for fam, items in by_fam.items():
        keep_n = int((families[fam] or {}).get("keep_last") or 0)
        # already newest-first from list_releases
        items_sorted = sorted(items, key=lambda x: x.published_at, reverse=True)
        keep = items_sorted[:keep_n]
        drop = items_sorted[keep_n:]
        keep_tags = {x.tag for x in keep}
        for rel in drop:
            if rel.tag in keep_tags:
                continue
            plan.append(
                PlanItem(
                    action="delete_release",
                    target=rel.tag,
                    reason=f"{fam}: keep_last={keep_n}, older than retained window",
                    bytes=rel.asset_bytes,
                )
            )

    # sepa-rev-*: one latest tag per ticker slug
    if rev_tags:
        by_ticker: dict[str, list[ReleaseInfo]] = {}
        for rel in rev_tags:
            slug = rel.tag[len(REV_PREFIX) :] if rel.tag.startswith(REV_PREFIX) else rel.tag
            # if someone used sepa-rev-lasr-v2, group by first segment
            ticker = slug.split("-")[0].lower()
            by_ticker.setdefault(ticker, []).append(rel)
        for ticker, items in by_ticker.items():
            items_sorted = sorted(items, key=lambda x: x.published_at, reverse=True)
            for rel in items_sorted[1:]:
                plan.append(
                    PlanItem(
                        action="delete_release",
                        target=rel.tag,
                        reason=f"sepa-rev: keep latest for ticker={ticker}",
                        bytes=rel.asset_bytes,
                    )
                )

    return plan


def tracked_pdfs(repo_root: Path | None = None) -> list[Path]:
    root = repo_root or Path.cwd()
    proc = subprocess.run(
        ["git", "ls-files", "*.pdf"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        return []
    return [Path(line) for line in proc.stdout.splitlines() if line.strip()]


def plan_git_untrack(pdfs: list[Path]) -> list[PlanItem]:
    return [
        PlanItem(
            action="git_rm_cached",
            target=str(p),
            reason="disallow_pdf_commit: untrack generated PDF (file kept on disk)",
            bytes=p.stat().st_size if p.exists() else 0,
        )
        for p in pdfs
    ]


def find_dupes(pdfs: list[Path]) -> list[PlanItem]:
    """Detect same basename under assets/ and reports/ with identical sha256."""
    by_name: dict[str, list[Path]] = {}
    for p in pdfs:
        by_name.setdefault(p.name, []).append(p)

    plan: list[PlanItem] = []
    for name, paths in sorted(by_name.items()):
        if len(paths) < 2:
            continue
        hashes: dict[str, list[Path]] = {}
        for p in paths:
            if not p.exists():
                continue
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            hashes.setdefault(h, []).append(p)
        for h, group in hashes.items():
            if len(group) < 2:
                continue
            # Prefer keeping assets/ copy as release source; flag reports/ as dupe
            assets = [p for p in group if p.parts and p.parts[0] == "assets"]
            reports = [p for p in group if p.parts and p.parts[0] == "reports"]
            if assets and reports:
                for p in reports:
                    plan.append(
                        PlanItem(
                            action="dupe_reports_pdf",
                            target=str(p),
                            reason=f"duplicate of assets/{name} sha256={h[:12]}…",
                            bytes=p.stat().st_size if p.exists() else 0,
                        )
                    )
            else:
                for p in group[1:]:
                    plan.append(
                        PlanItem(
                            action="dupe_pdf",
                            target=str(p),
                            reason=f"duplicate basename {name} sha256={h[:12]}…",
                            bytes=p.stat().st_size if p.exists() else 0,
                        )
                    )
    return plan


def apply_delete_releases(plan: list[PlanItem], *, yes: bool) -> list[dict[str, Any]]:
    if not yes:
        raise SystemExit("--apply for releases requires --yes")
    results = []
    for item in plan:
        if item.action != "delete_release":
            continue
        proc = _run_gh(
            ["release", "delete", item.target, "--yes", "--cleanup-tag"],
            check=False,
        )
        results.append(
            {
                "tag": item.target,
                "ok": proc.returncode == 0,
                "stderr": (proc.stderr or "").strip(),
            }
        )
    return results


def apply_git_rm_cached(plan: list[PlanItem], *, yes: bool, repo_root: Path | None = None) -> list[dict[str, Any]]:
    if not yes:
        raise SystemExit("--apply for git-index requires --yes")
    root = repo_root or Path.cwd()
    results = []
    paths = [item.target for item in plan if item.action == "git_rm_cached"]
    if not paths:
        return results
    proc = subprocess.run(
        ["git", "rm", "--cached", "-f", "--", *paths],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    results.append(
        {
            "ok": proc.returncode == 0,
            "n": len(paths),
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
    )
    return results


def write_audit(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fmt_bytes(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


def print_plan(title: str, plan: list[PlanItem]) -> None:
    print(f"\n== {title} ({len(plan)} items) ==")
    if not plan:
        print("  (nothing)")
        return
    total = 0
    for item in plan:
        total += item.bytes
        print(f"  [{item.action}] {item.target}")
        print(f"      {item.reason}  ({fmt_bytes(item.bytes)})")
    print(f"  -- sum size ≈ {fmt_bytes(total)}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Cleanup old releases / tracked PDFs")
    p.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=["all", "releases", "git-index", "dupes"],
        help="what to plan/apply (default: all)",
    )
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--apply", action="store_true", help="execute deletes/untrack")
    p.add_argument("--yes", action="store_true", help="required with --apply")
    p.add_argument("--audit", action="store_true", help="always write audit JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    audit_dir = Path((cfg.get("audit") or {}).get("dir") or "reports")
    audit_path = audit_dir / f"cleanup_audit_{stamp}.json"

    payload: dict[str, Any] = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "command": args.command,
        "apply": bool(args.apply),
        "plans": {},
        "results": {},
    }

    do_rel = args.command in ("all", "releases")
    do_git = args.command in ("all", "git-index")
    do_dup = args.command in ("all", "dupes")

    rel_plan: list[PlanItem] = []
    git_plan: list[PlanItem] = []
    dupe_plan: list[PlanItem] = []

    if do_rel:
        print("[cleanup] listing GitHub releases…")
        releases = list_releases()
        print(f"[cleanup] {len(releases)} releases")
        rel_plan = plan_release_deletions(releases, cfg)
        print_plan("Releases to delete", rel_plan)
        payload["plans"]["releases"] = [asdict(x) for x in rel_plan]

    pdfs: list[Path] = []
    if do_git or do_dup:
        pdfs = tracked_pdfs()
        print(f"[cleanup] tracked PDFs: {len(pdfs)}")

    if do_git:
        git_plan = plan_git_untrack(pdfs)
        print_plan("Git index: untrack PDFs", git_plan)
        payload["plans"]["git_index"] = [asdict(x) for x in git_plan]

    if do_dup:
        dupe_plan = find_dupes(pdfs)
        print_plan("Duplicate PDFs (assets vs reports)", dupe_plan)
        payload["plans"]["dupes"] = [asdict(x) for x in dupe_plan]

    if args.apply:
        if do_rel and rel_plan:
            print("[cleanup] applying release deletes…")
            payload["results"]["releases"] = apply_delete_releases(rel_plan, yes=args.yes)
        if do_git and git_plan:
            print("[cleanup] applying git rm --cached…")
            payload["results"]["git_index"] = apply_git_rm_cached(git_plan, yes=args.yes)
        if do_dup:
            print("[cleanup] dupes: informational only — use git-index to untrack")
        write_audit(audit_path, payload)
        print(f"[cleanup] audit → {audit_path}")
    else:
        print("\n[cleanup] dry-run only. Re-run with --apply --yes to execute.")
        if args.audit:
            write_audit(audit_path, payload)
            print(f"[cleanup] audit → {audit_path}")
        # note phone archive
        print(
            "[cleanup] note: owner keeps phone-local PDF copies — "
            "GitHub retention can stay aggressive."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
