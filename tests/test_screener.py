import pandas as pd

from sepa.data.universe import clean_security_name
from sepa.screener import format_stage2_list


def test_clean_security_name_strips_type_suffix():
    assert clean_security_name("Apple Inc. - Common Stock") == "Apple Inc."
    assert clean_security_name("NVIDIA Corporation - Common Stock") == "NVIDIA Corporation"
    assert clean_security_name("PlainName") == "PlainName"


def test_format_stage2_list_name_dash_ticker():
    stage2 = pd.DataFrame([
        {"ticker": "NVDA", "name": "NVIDIA Corporation", "close": 200.0, "rs_rank": 99.0},
        {"ticker": "XXXX", "name": "", "close": 10.0, "rs_rank": 90.0},
    ])
    assert format_stage2_list(stage2) == ["NVIDIA Corporation-NVDA", "XXXX-XXXX"]


def test_format_stage2_list_empty():
    assert format_stage2_list(pd.DataFrame(columns=["ticker", "name", "close", "rs_rank"])) == []
