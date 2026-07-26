"""Downloadable artifact helpers for Cursor Cloud / local runs.

Charts and reports copied under ``/opt/cursor/artifacts`` (when available)
show up as downloadable files in the Cursor agent UI.
"""

from __future__ import annotations

import os
import shutil
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
    try:
        if dest.resolve() == src.resolve():
            return dest
    except OSError:
        pass
    shutil.copy2(src, dest)
    return dest


def publish_many(paths: list[str | Path]) -> list[Path]:
    published: list[Path] = []
    for p in paths:
        out = publish(p)
        if out is not None:
            published.append(out)
    return published
