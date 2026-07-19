import pytest

from sepa.macro import MacroError, parse_command, resolve_ticker

NAMES = {
    "SNDK": "Sandisk Corporation",
    "NVDA": "NVIDIA Corporation",
    "AAPL": "Apple Inc.",
    "GOOG": "Alphabet Inc.",
    "GOOGL": "Alphabet Inc.",
}


def test_parse_quoted_and_bare_args_equivalent():
    assert parse_command('!sepa.chart("SNDK")') == ("sepa.chart", ["SNDK"], {})
    assert parse_command("!sepa.chart(SNDK)") == ("sepa.chart", ["SNDK"], {})


def test_parse_kwargs():
    name, args, kwargs = parse_command('!sepa.chart(sandisk, months=12, as_of="2025-02-18")')
    assert name == "sepa.chart"
    assert args == ["sandisk"]
    assert kwargs == {"months": 12, "as_of": "2025-02-18"}


def test_parse_no_args_and_without_bang():
    assert parse_command("!tools") == ("tools", [], {})
    assert parse_command("tools") == ("tools", [], {})
    assert parse_command("!sepa.screener()") == ("sepa.screener", [], {})


def test_parse_rejects_garbage():
    with pytest.raises(MacroError):
        parse_command("!!! ???")


def test_resolve_exact_ticker():
    assert resolve_ticker("sndk", NAMES) == "SNDK"


def test_resolve_by_company_name():
    assert resolve_ticker("sandisk", NAMES) == "SNDK"
    assert resolve_ticker("nvidia", NAMES) == "NVDA"


def test_resolve_same_company_prefers_short_ticker():
    assert resolve_ticker("alphabet", NAMES) == "GOOG"


def test_resolve_unknown_raises():
    with pytest.raises(MacroError):
        resolve_ticker("does-not-exist", NAMES)


def test_short_aliases_resolve():
    from sepa.macro import _LOOKUP

    assert _LOOKUP["sepa.scan"] is _LOOKUP["sepa.screener"]
    assert _LOOKUP["scan"] is _LOOKUP["sepa.screener"]
    assert _LOOKUP["sepa.fund"] is _LOOKUP["sepa.fundamental"]
    assert _LOOKUP["fund"] is _LOOKUP["sepa.fundamental"]
    assert _LOOKUP["sepa.anal"] is _LOOKUP["sepa.analyze"]
    assert _LOOKUP["anal"] is _LOOKUP["sepa.analyze"]
    assert _LOOKUP["go"] is _LOOKUP["sepa.go"]
    assert _LOOKUP["sepa.sepatop"] is _LOOKUP["top"]
    assert _LOOKUP["sepatop"] is _LOOKUP["sepa.sepatop"]
    assert _LOOKUP["sepa.top"] is _LOOKUP["sepa.sepatop"]
    assert _LOOKUP["sepa.sectorshare"] is _LOOKUP["sector"]
    assert _LOOKUP["sepa.sectorshare"] is _LOOKUP["sectorshare"]


def test_parse_sepatop():
    assert parse_command("!sepa.sepaTop()") == ("sepa.sepatop", [], {})
    assert parse_command("!sepa.sepatop") == ("sepa.sepatop", [], {})
    assert parse_command("!top") == ("top", [], {})


def test_parse_sector_share():
    assert parse_command("!sepa.sectorShare()") == ("sepa.sectorshare", [], {})
    assert parse_command("!sepa.sectorShare(week)") == ("sepa.sectorshare", ["week"], {})
    assert parse_command("!sector(month)") == ("sector", ["month"], {})


def test_parse_go():
    assert parse_command("!sepa.go()") == ("sepa.go", [], {})
    assert parse_command("!sepa.go") == ("sepa.go", [], {})
    assert parse_command("!go") == ("go", [], {})
