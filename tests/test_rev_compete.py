"""Tests for sepa.rev_compete profiles (no network required for share math)."""

from sepa.rev_compete import ShareRow, get_profile, load_compete_bundle


def test_roku_profile_exists():
    p = get_profile("ROKU")
    assert p is not None
    assert "share_rows" in p
    assert "mix_rows" in p
    assert any(r.get("subject") for r in p["mix_rows"])


def test_share_delta_pp():
    r = ShareRow("Roku", 36.0, 38.0)
    assert r.delta_pp == -2.0


def test_rely_profile_exists():
    p = get_profile("RELY")
    assert p is not None
    assert any(r.get("subject") for r in p["mix_rows"])
    assert p["share_rows"][2][0] == "Remitly"


def test_pebo_profile_exists():
    p = get_profile("PEBO")
    assert p is not None
    assert any(r.get("subject") for r in p["mix_rows"])
    assert abs(p["mix_rows"][0]["mix"]["Net Interest Income"] - 76.2) < 0.1


def test_sblk_profile_exists():
    p = get_profile("SBLK")
    assert p is not None
    assert any(r.get("subject") for r in p["mix_rows"])
    assert p["share_rows"][0][0] == "Star Bulk"
    assert "Cape/Newcastlemax" in p["mix_buckets"]
    assert abs(p["mix_rows"][0]["mix"]["Cape/Newcastlemax"] - 33.0) < 0.1


def test_clmt_profile_exists():
    p = get_profile("CLMT")
    assert p is not None
    assert any(r.get("subject") for r in p["mix_rows"])
    assert p["share_rows"][2][0] == "Calumet"
    assert "Specialty Products" in p["mix_buckets"]
    assert abs(p["mix_rows"][0]["mix"]["Specialty Products"] - 68.5) < 0.1


def test_txg_profile_exists():
    p = get_profile("TXG")
    assert p is not None
    assert any(r.get("subject") for r in p["mix_rows"])
    assert p["share_rows"][0][0] == "10x Genomics"
    assert "Consumables" in p["mix_buckets"]
    assert abs(p["mix_rows"][0]["mix"]["Consumables"] - 86.0) < 0.1


def test_load_bundle_offline_share(monkeypatch):
    monkeypatch.setattr("sepa.rev_compete._ttm_revenue", lambda _t: None)
    b = load_compete_bundle("RELY")
    assert b is not None
    assert b.share_rows[2].name == "Remitly"
    assert abs(b.share_rows[2].delta_pp - 0.4) < 1e-9

    b2 = load_compete_bundle("SBLK")
    assert b2 is not None
    assert b2.share_rows[0].name == "Star Bulk"
    assert abs(b2.share_rows[0].delta_pp - 2.0) < 1e-9

    b3 = load_compete_bundle("CLMT")
    assert b3 is not None
    assert b3.share_rows[2].name == "Calumet"
    assert abs(b3.share_rows[2].delta_pp - 2.0) < 1e-9

    b4 = load_compete_bundle("TXG")
    assert b4 is not None
    assert b4.share_rows[0].name == "10x Genomics"
    assert abs(b4.share_rows[0].delta_pp - 3.0) < 1e-9
