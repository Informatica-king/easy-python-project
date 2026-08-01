"""후보 종목 공통 필터.

제외 조건 (2026-07-17 확정):
  - Fund 점수 == 0
  - 시가총액 < $1B (또는 시총 미확인)
"""

from __future__ import annotations

import pandas as pd

MIN_MARKET_CAP_USD = 1_000_000_000.0  # $1B


def apply_candidate_filters(
    df: pd.DataFrame,
    *,
    fund_col: str = "fund_score",
    mcap_col: str = "market_cap",
    min_market_cap: float = MIN_MARKET_CAP_USD,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (kept, dropped).

    Dropped when fund_score <= 0 (or NaN) OR market_cap < min OR market_cap missing.
    """
    if df.empty:
        return df.copy(), df.copy()

    work = df.copy()
    fund = pd.to_numeric(work[fund_col], errors="coerce")
    if mcap_col not in work.columns:
        work[mcap_col] = pd.NA
    mcap = pd.to_numeric(work[mcap_col], errors="coerce")

    fund_ok = fund.fillna(0) > 0
    mcap_ok = mcap.notna() & (mcap >= min_market_cap)
    keep_mask = fund_ok & mcap_ok

    kept = work.loc[keep_mask].reset_index(drop=True)
    dropped = work.loc[~keep_mask].reset_index(drop=True)
    return kept, dropped


def summarize_drops(dropped: pd.DataFrame) -> str:
    if dropped.empty:
        return "제외 0종"
    fund = pd.to_numeric(dropped.get("fund_score"), errors="coerce").fillna(0)
    mcap = pd.to_numeric(dropped.get("market_cap"), errors="coerce")
    zero_fund = int((fund <= 0).sum())
    small_or_na = int((mcap.isna() | (mcap < MIN_MARKET_CAP_USD)).sum())
    return (
        f"제외 {len(dropped)}종 "
        f"(Fund≤0: {zero_fund}, 시총<$1B/미확인: {small_or_na})"
    )
