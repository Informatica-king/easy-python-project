import numpy as np

from sepa.config import UniverseFilterParams
from sepa.screener import passes_liquidity
from synthetic import frame_from_close

UF = UniverseFilterParams(min_price=10.0, min_avg_dollar_volume=10_000_000.0)


def test_rejects_penny_stock():
    df = frame_from_close(np.full(60, 5.0), np.full(60, 10_000_000.0))
    assert not passes_liquidity(df, UF)


def test_rejects_illiquid_stock():
    # $50 price but only 1,000 shares/day => $50k dollar volume
    df = frame_from_close(np.full(60, 50.0), np.full(60, 1_000.0))
    assert not passes_liquidity(df, UF)


def test_accepts_liquid_stock():
    # $50 x 1M shares = $50M/day
    df = frame_from_close(np.full(60, 50.0), np.full(60, 1_000_000.0))
    assert passes_liquidity(df, UF)
