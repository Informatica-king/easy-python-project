"""미너비니 스타일 정량 펀더멘털 점수 (docs/fundamental_spec.md)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FundamentalWeights:
    eps_yoy: float = 25.0          # A
    eps_accel: float = 20.0        # B
    sales_yoy: float = 15.0        # C
    sales_accel: float = 10.0      # D
    margin_improve: float = 15.0   # E
    roe: float = 5.0               # G
    # F (annual EPS) intentionally omitted

    @property
    def total(self) -> float:
        return (
            self.eps_yoy
            + self.eps_accel
            + self.sales_yoy
            + self.sales_accel
            + self.margin_improve
            + self.roe
        )


DEFAULT_WEIGHTS = FundamentalWeights()


def prior_year_frame(frame: str) -> str:
    """CY2025Q1 -> CY2024Q1"""
    year = int(frame[2:6])
    return f"CY{year - 1}Q{frame[7]}"


def yoy_growth_map(series: pd.Series) -> dict[str, float]:
    """Frame -> YoY growth using CY(n)Q vs CY(n-1)Q."""
    if series is None or series.empty:
        return {}
    data = series.dropna().to_dict()
    out: dict[str, float] = {}
    for frame, val in data.items():
        prev = data.get(prior_year_frame(frame))
        if prev is None or prev == 0:
            continue
        # EPS can be negative; still define YoY when prior != 0
        out[frame] = float(val) / float(prev) - 1.0
    return out


def sorted_frames(frames: list[str]) -> list[str]:
    return sorted(frames, key=lambda f: (int(f[2:6]), int(f[7])))


def _quarter_tuple(frame: str) -> tuple[int, int]:
    return int(frame[2:6]), int(frame[7])


def is_next_quarter(older: str, newer: str) -> bool:
    """True if `newer` is exactly one calendar quarter after `older`."""
    y1, q1 = _quarter_tuple(older)
    y2, q2 = _quarter_tuple(newer)
    if q1 == 4:
        return (y2, q2) == (y1 + 1, 1)
    return (y2, q2) == (y1, q1 + 1)


def latest_yoy(yoy: dict[str, float]) -> float | None:
    if not yoy:
        return None
    last = sorted_frames(list(yoy.keys()))[-1]
    return yoy[last]


def count_accel_quarters(yoy: dict[str, float]) -> int:
    """Count consecutive YoY-rate increases from the latest quarter. 2+ = full credit."""
    if len(yoy) < 2:
        return 0
    frames = sorted_frames(list(yoy.keys()))
    count = 0
    for i in range(len(frames) - 1, 0, -1):
        newer, older = frames[i], frames[i - 1]
        if not is_next_quarter(older, newer):
            break
        if yoy[newer] > yoy[older]:
            count += 1
        else:
            break
    return count


def count_margin_improve_quarters(npm: pd.Series) -> int:
    """Count consecutive quarters (from latest) where NPM > year-ago NPM."""
    if npm is None or npm.empty:
        return 0
    data = npm.dropna().to_dict()
    frames = sorted_frames(list(data.keys()))
    count = 0
    for i in range(len(frames) - 1, -1, -1):
        frame = frames[i]
        prev_year = data.get(prior_year_frame(frame))
        if prev_year is None:
            break
        if data[frame] <= prev_year:
            break
        count += 1
        if i == 0:
            break
        # streak requires the previous calendar quarter also exists in series
        older = frames[i - 1]
        if not is_next_quarter(older, frame):
            break
    return count


def growth_points(yoy: float | None, weight: float) -> float:
    """Map YoY growth to [0, weight] per fundamental_spec §3.1."""
    if yoy is None or yoy < 0:
        return 0.0
    if yoy < 0.25:
        return weight * (12.0 / 25.0) * (yoy / 0.25)
    if yoy < 0.50:
        return weight * (12.0 / 25.0) + weight * (8.0 / 25.0) * ((yoy - 0.25) / 0.25)
    extra = min(1.0, (yoy - 0.50) / 0.50)
    return weight * (20.0 / 25.0) + weight * (5.0 / 25.0) * extra


def accel_points(n_consec: int, weight: float) -> float:
    """0→0%, 1→50%, 2+→100%."""
    if n_consec <= 0:
        return 0.0
    if n_consec == 1:
        return 0.5 * weight
    return weight


def roe_points(roe: float | None, weight: float, target: float = 0.17) -> float:
    if roe is None or roe <= 0:
        return 0.0
    return weight * min(1.0, roe / target)


@dataclass
class ScoreBreakdown:
    ticker: str
    a_eps_yoy: float
    b_eps_accel: float
    c_sales_yoy: float
    d_sales_accel: float
    e_margin: float
    g_roe: float
    raw: float
    fund_score: float
    eps_yoy: float | None
    sales_yoy: float | None
    eps_accel_n: int
    sales_accel_n: int
    margin_n: int
    roe: float | None
    source: str

    def as_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "fund_score": round(self.fund_score, 1),
            "a_eps_yoy": round(self.a_eps_yoy, 2),
            "b_eps_accel": round(self.b_eps_accel, 2),
            "c_sales_yoy": round(self.c_sales_yoy, 2),
            "d_sales_accel": round(self.d_sales_accel, 2),
            "e_margin": round(self.e_margin, 2),
            "g_roe": round(self.g_roe, 2),
            "eps_yoy_pct": None if self.eps_yoy is None else round(self.eps_yoy * 100, 1),
            "sales_yoy_pct": None if self.sales_yoy is None else round(self.sales_yoy * 100, 1),
            "eps_accel_n": self.eps_accel_n,
            "sales_accel_n": self.sales_accel_n,
            "margin_n": self.margin_n,
            "roe_pct": None if self.roe is None else round(self.roe * 100, 1),
            "source": self.source,
        }


def score_ticker(
    ticker: str,
    quarterly: pd.DataFrame,
    roe: float | None,
    source: str = "",
    weights: FundamentalWeights = DEFAULT_WEIGHTS,
    roe_target: float = 0.17,
) -> ScoreBreakdown:
    eps = quarterly["eps"] if "eps" in quarterly.columns else pd.Series(dtype=float)
    rev = quarterly["revenue"] if "revenue" in quarterly.columns else pd.Series(dtype=float)
    npm = quarterly["npm"] if "npm" in quarterly.columns else pd.Series(dtype=float)

    eps_yoy_map = yoy_growth_map(eps)
    sales_yoy_map = yoy_growth_map(rev)

    eps_yoy = latest_yoy(eps_yoy_map)
    sales_yoy = latest_yoy(sales_yoy_map)
    eps_n = count_accel_quarters(eps_yoy_map)
    sales_n = count_accel_quarters(sales_yoy_map)
    margin_n = count_margin_improve_quarters(npm)

    # Negative base-year EPS makes YoY meaningless for ranking — treat as missing for A
    a = growth_points(eps_yoy if eps_yoy is not None else None, weights.eps_yoy)
    if eps_yoy is not None:
        # If latest EPS itself is negative, cap A at 0
        last_eps_frame = sorted_frames(list(eps.dropna().index))[-1] if not eps.dropna().empty else None
        if last_eps_frame is not None and float(eps.loc[last_eps_frame]) < 0:
            a = 0.0

    b = accel_points(eps_n, weights.eps_accel)
    c = growth_points(sales_yoy, weights.sales_yoy)
    d = accel_points(sales_n, weights.sales_accel)
    e = accel_points(margin_n, weights.margin_improve)
    g = roe_points(roe, weights.roe, target=roe_target)

    raw = a + b + c + d + e + g
    fund = (raw / weights.total) * 100.0 if weights.total else 0.0

    return ScoreBreakdown(
        ticker=ticker.upper(),
        a_eps_yoy=a,
        b_eps_accel=b,
        c_sales_yoy=c,
        d_sales_accel=d,
        e_margin=e,
        g_roe=g,
        raw=raw,
        fund_score=fund,
        eps_yoy=eps_yoy,
        sales_yoy=sales_yoy,
        eps_accel_n=eps_n,
        sales_accel_n=sales_n,
        margin_n=margin_n,
        roe=roe,
        source=source,
    )
