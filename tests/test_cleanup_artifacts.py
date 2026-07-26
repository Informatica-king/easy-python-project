"""Tests for artifact cleanup planning (no live gh deletes)."""

from __future__ import annotations

from pathlib import Path

from sepa.cleanup_artifacts import (
    ReleaseInfo,
    find_dupes,
    plan_git_untrack,
    plan_release_deletions,
)


CFG = {
    "releases": {
        "sepa-anal": {"keep_last": 2},
        "sepa-deep": {"keep_last": 2},
        "sepa-econ": {"keep_last": 2},
        "sepa-rev": {"keep_latest_per_ticker": True},
    }
}


def _rel(tag: str, published: str, nbytes: int = 100) -> ReleaseInfo:
    return ReleaseInfo(tag=tag, published_at=published, is_latest=False, asset_bytes=nbytes)


def test_keep_last_drops_older_anal():
    releases = [
        _rel("sepa-anal-20260726", "2026-07-26T13:00:00Z"),
        _rel("sepa-anal-20260725", "2026-07-25T13:00:00Z"),
        _rel("sepa-anal-20260724", "2026-07-24T13:00:00Z"),
        _rel("sepa-anal-20260722", "2026-07-22T13:00:00Z"),
    ]
    plan = plan_release_deletions(releases, CFG)
    tags = {p.target for p in plan}
    assert "sepa-anal-20260726" not in tags
    assert "sepa-anal-20260725" not in tags
    assert "sepa-anal-20260724" in tags
    assert "sepa-anal-20260722" in tags


def test_rev_keeps_latest_per_ticker():
    releases = [
        _rel("sepa-rev-lasr", "2026-07-25T02:00:00Z"),
        _rel("sepa-rev-lasr-old", "2026-07-20T02:00:00Z"),  # same ticker slug lasr
        _rel("sepa-rev-rapp", "2026-07-26T14:00:00Z"),
    ]
    # Note: sepa-rev-lasr-old groups as ticker "lasr" via first segment
    plan = plan_release_deletions(releases, CFG)
    tags = {p.target for p in plan}
    assert "sepa-rev-lasr" not in tags
    assert "sepa-rev-lasr-old" in tags
    assert "sepa-rev-rapp" not in tags


def test_git_untrack_plan():
    paths = [Path("assets/X.pdf"), Path("reports/X.pdf")]
    plan = plan_git_untrack(paths)
    assert len(plan) == 2
    assert all(p.action == "git_rm_cached" for p in plan)


def test_find_dupes(tmp_path: Path, monkeypatch):
    assets = tmp_path / "assets"
    reports = tmp_path / "reports"
    assets.mkdir()
    reports.mkdir()
    data = b"%PDF-1.4 fake"
    a = assets / "FOO.pdf"
    r = reports / "FOO.pdf"
    a.write_bytes(data)
    r.write_bytes(data)
    # run from tmp_path context — find_dupes uses path parts
    monkeypatch.chdir(tmp_path)
    plan = find_dupes([Path("assets/FOO.pdf"), Path("reports/FOO.pdf")])
    assert len(plan) == 1
    assert plan[0].target == "reports/FOO.pdf"
    assert plan[0].action == "dupe_reports_pdf"
