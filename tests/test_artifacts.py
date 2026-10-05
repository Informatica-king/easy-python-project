"""Tests for artifact publishing helper."""

from pathlib import Path

from sepa.artifacts import publish, publish_many


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


def test_publish_same_path_is_noop(tmp_path, monkeypatch):
    art = tmp_path / "artifacts"
    art.mkdir()
    monkeypatch.setenv("SEPA_ARTIFACT_DIR", str(art))
    src = art / "already.png"
    src.write_bytes(b"x")
    dest = publish(src)
    assert dest == src
    assert dest.read_bytes() == b"x"
