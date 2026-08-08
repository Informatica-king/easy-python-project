"""Downloadable artifact helpers for Cursor Cloud / local runs.

Charts and reports copied under ``/opt/cursor/artifacts`` (when available)
show up as downloadable files in the Cursor agent UI.

PDFs also get a public GitHub Release direct-download URL (same pattern as
``!sepa.anal``), so mobile clients can tap a link even when artifact PDF
download is flaky.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_ARTIFACT_DIRS = (
    Path("/opt/cursor/artifacts"),
    Path("artifacts"),  # local fallback next to cwd
)


def artifact_dir() -> Path | None:
    """Return a writable artifacts directory, or None."""
    override = os.environ.get("SEPA_ARTIFACT_DIR")
    candidates = [Path(override)] if override else list(DEFAULT_ARTIFACT_DIRS)
    for d in candidates:
        try:
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".sepa_write_probe"
            probe.write_text("ok")
            probe.unlink(missing_ok=True)
            return d
        except OSError:
            continue
    return None


def publish(path: str | Path, *, name: str | None = None) -> Path | None:
    """Copy ``path`` into the artifacts dir for one-click download.

    Returns the published path, or None if publishing is unavailable.
    """
    src = Path(path)
    if not src.exists():
        return None
    dest_dir = artifact_dir()
    if dest_dir is None:
        return None
    dest = dest_dir / (name or src.name)
    shutil.copy2(src, dest)
    return dest


def publish_many(paths: list[str | Path]) -> list[Path]:
    published: list[Path] = []
    for p in paths:
        out = publish(p)
        if out is not None:
            published.append(out)
    return published


def github_repo_slug() -> str | None:
    """Return owner/repo from gh, or None."""
    if shutil.which("gh") is None:
        return None
    try:
        out = subprocess.check_output(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=30,
        ).strip()
        return out or None
    except Exception:  # noqa: BLE001
        try:
            raw = subprocess.check_output(
                ["gh", "repo", "view", "--json", "nameWithOwner"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            return json.loads(raw).get("nameWithOwner")
        except Exception:  # noqa: BLE001
            return None


def release_download_url(repo: str, tag: str, asset_name: str) -> str:
    return f"https://github.com/{repo}/releases/download/{tag}/{asset_name}"


def publish_github_release_asset(
    path: str | Path,
    *,
    tag: str,
    title: str,
    notes: str,
    repo: str | None = None,
) -> dict:
    """Upload a file to a GitHub Release (create or --clobber) and return URLs."""
    path = Path(path)
    if not path.exists():
        return {"ok": False, "error": f"asset missing: {path}"}
    if shutil.which("gh") is None:
        return {"ok": False, "error": "gh CLI not available"}

    repo = repo or github_repo_slug()
    if not repo:
        return {"ok": False, "error": "cannot resolve GitHub repo slug"}

    asset_arg = f"{path}#{path.name}"
    download = release_download_url(repo, tag, path.name)
    page = f"https://github.com/{repo}/releases/tag/{tag}"
    notes_final = notes if "http" in notes else f"{notes}\n\nDirect download: {download}\n"

    view = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if view.returncode != 0:
        created = subprocess.run(
            [
                "gh", "release", "create", tag,
                asset_arg,
                "--repo", repo,
                "--title", title,
                "--notes", notes_final,
                "--latest=false",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if created.returncode != 0:
            return {
                "ok": False,
                "error": (created.stderr or created.stdout or "release create failed").strip(),
                "repo": repo,
                "tag": tag,
            }
    else:
        uploaded = subprocess.run(
            [
                "gh", "release", "upload", tag,
                asset_arg,
                "--repo", repo,
                "--clobber",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if uploaded.returncode != 0:
            return {
                "ok": False,
                "error": (uploaded.stderr or uploaded.stdout or "release upload failed").strip(),
                "repo": repo,
                "tag": tag,
            }
        subprocess.run(
            ["gh", "release", "edit", tag, "--repo", repo, "--notes", notes_final],
            capture_output=True,
            text=True,
            timeout=60,
        )

    return {
        "ok": True,
        "repo": repo,
        "tag": tag,
        "download_url": download,
        "release_url": page,
        "asset_name": path.name,
    }


def compact_stamp(as_of: str) -> str:
    """``2026-08-07`` or ``20260807`` → ``20260807``."""
    return str(as_of).replace("-", "")[:8]


def publish_deep_pdf_release(
    pdf_path: str | Path,
    *,
    as_of: str,
    notes: str = "",
    title: str | None = None,
) -> dict:
    """Upload NASDAQ deep-analysis PDF → ``sepa-deep-YYYYMMDD`` (mobile download)."""
    pdf_path = Path(pdf_path)
    stamp = compact_stamp(as_of)
    tag = f"sepa-deep-{stamp}"
    repo = github_repo_slug() or "Informatica-king/easy-python-project"
    download = release_download_url(repo, tag, pdf_path.name)
    body = notes.strip() or f"NASDAQ 심층분석 ({as_of})."
    notes_final = f"{body}\n\nDirect download: {download}\n"
    rel = publish_github_release_asset(
        pdf_path,
        tag=tag,
        title=title or f"SEPA Deep Analysis — {as_of}",
        notes=notes_final,
        repo=repo,
    )
    if rel.get("ok"):
        rel["pdf_name"] = pdf_path.name
    return rel


def publish_portfolio_pdf_release(
    pdf_path: str | Path,
    *,
    as_of: str,
    notes: str = "",
    title: str | None = None,
) -> dict:
    """Upload 포폴() PDF → ``sepa-portfolio-ops-YYYYMMDD`` (mobile download)."""
    pdf_path = Path(pdf_path)
    stamp = compact_stamp(as_of)
    tag = f"sepa-portfolio-ops-{stamp}"
    repo = github_repo_slug() or "Informatica-king/easy-python-project"
    download = release_download_url(repo, tag, pdf_path.name)
    body = notes.strip() or f"포폴() 운영브리프 ({as_of})."
    notes_final = f"{body}\n\nDirect download: {download}\n"
    rel = publish_github_release_asset(
        pdf_path,
        tag=tag,
        title=title or f"SEPA Portfolio Ops — {as_of}",
        notes=notes_final,
        repo=repo,
    )
    if rel.get("ok"):
        rel["pdf_name"] = pdf_path.name
    return rel


def print_release_result(rel: dict, *, label: str = "PDF") -> None:
    """Stdout block matching ``!sepa.anal`` mobile UX."""
    print("\n" + "=" * 64)
    print(f"  {label} 직접 다운로드 링크 (GitHub Release)")
    print("=" * 64)
    if rel.get("ok"):
        print(f"\n  PDF 직접 다운로드:\n  {rel['download_url']}\n")
        print(f"  릴리즈 페이지: {rel['release_url']}")
    else:
        print(f"[경고] GitHub Release 업로드 실패: {rel.get('error')}")
        print("  (로컬 PDF/artifacts는 생성됨 — --skip-github-release 로 생략 가능)")
