"""Tests for artifact publishing helper."""

from pathlib import Path

from sepa.artifacts import publish, publish_many, release_download_url


def test_release_download_url():
    url = release_download_url("o/r", "sepa-econ-20260721", "Econ_News_2026-07-21.pdf")
    assert url.endswith("/releases/download/sepa-econ-20260721/Econ_News_2026-07-21.pdf")


def test_publish_copies_to_artifact_dir(tmp_path, monkeypatch):
    src = tmp_path / "chart.png"
    src.write_bytes(b"fake-png")
    art = tmp_path / "artifacts"
    monkeypatch.setenv("SEPA_ARTIFACT_DIR", str(art))

    dest = publish(src)
    assert dest is not None
    assert dest.exists()
    assert dest.read_bytes() == b"fake-png"
    assert dest.parent == art


def test_publish_many(tmp_path, monkeypatch):
    monkeypatch.setenv("SEPA_ARTIFACT_DIR", str(tmp_path / "out"))
    files = []
    for name in ("a.png", "b.png"):
        p = tmp_path / name
        p.write_text(name)
        files.append(p)
    published = publish_many(files)
    assert len(published) == 2
    assert all(p.exists() for p in published)
