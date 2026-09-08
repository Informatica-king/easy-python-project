"""후보 종목 공통 필터.

제외 조건 (2026-07-17 확정):
  - Fund 점수 == 0
  - 시가총액 < $1B (또는 시총 미확인)

RS soft ceiling (2026-07-27):
  - RS ≥ rs_soft_max 이면 Fund ≥ (풀 중앙값) 일 때만 유지 (하드 상한 컷 아님)
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


def apply_rs_soft_ceiling(
    df: pd.DataFrame,
    *,
    rs_soft_max: float,
    enabled: bool = True,
    rs_col: str = "rs_rank",
    fund_col: str = "fund_score",
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """Keep RS < soft_max always; keep RS ≥ soft_max only if Fund ≥ pool median.

    ``df`` should already be Fund>0 / mcap-filtered. Returns
    ``(kept, dropped_by_soft_ceiling, median_fund_used)``.
    """
    if df is None or df.empty or not enabled or rs_soft_max is None or float(rs_soft_max) <= 0:
        empty = df.iloc[0:0].copy() if df is not None else pd.DataFrame()
        return (df.copy() if df is not None else pd.DataFrame()), empty, float("nan")

    work = df.copy()
    if rs_col not in work.columns or fund_col not in work.columns:
        return work, work.iloc[0:0].copy(), float("nan")

    rs = pd.to_numeric(work[rs_col], errors="coerce")
    fund = pd.to_numeric(work[fund_col], errors="coerce")
    median_fund = float(fund.median()) if fund.notna().any() else float("nan")
    if median_fund != median_fund:  # NaN
        return work, work.iloc[0:0].copy(), median_fund

    high_rs = rs >= float(rs_soft_max)
    weak_fund = fund.fillna(-1.0) < median_fund
    drop_mask = high_rs & weak_fund
    kept = work.loc[~drop_mask].reset_index(drop=True)
    dropped = work.loc[drop_mask].reset_index(drop=True)
    return kept, dropped, median_fund


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
