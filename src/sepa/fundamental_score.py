"""미너비니 스타일 정량 펀더멘털 점수 (docs/fundamental_spec.md).

Weights (2026-07-19 empirical study, user-approved; reconfirmed 2026-07-26):
  S eps_surprise 47 · E opm_delta 25 · D sales_dyoy 14 · B eps_dyoy 14

v2.1 quality layer — PRODUCTION DEFAULT ON (2026-07-26):
  fund_raw = S + B*qB + D*qD + E*qE
  qE: opm=1.0 / npm=npm_quality / none=0
  qB/qD: accel_n < min → 0; ==min → partial; >=full → 1.0
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FundamentalWeights:
    """Active factors sum to 100 → fund_score == raw when all full & q=1."""

    eps_surprise: float = 47.0  # S
    eps_dyoy: float = 14.0      # B — latest Δ of EPS YoY
    sales_dyoy: float = 14.0    # D — latest Δ of sales YoY
    opm_delta: float = 25.0     # E — OPM YoY change (pp); NPM fallback

    @property
    def total(self) -> float:
        return self.eps_surprise + self.eps_dyoy + self.sales_dyoy + self.opm_delta


@dataclass(frozen=True)
class QualityParams:
    """v2.1 reliability multipliers (weights stay fixed)."""

    enabled: bool = True
    npm_quality: float = 0.6
    accel_min_n: int = 2       # below → quality 0 (미채점)
    accel_full_n: int = 3      # >= → quality 1
    accel_partial: float = 0.7  # exactly accel_min_n
    surprise_winsor: float = 1.0  # clip |surprise| before curve (fraction)


DEFAULT_WEIGHTS = FundamentalWeights()
DEFAULT_QUALITY = QualityParams()

# Curve full-credit anchors (fraction / percentage-points)
SURPRISE_FULL_AT = 0.20   # +20% beat → full S
DYOY_FULL_AT = 0.25       # +25pp YoY acceleration → full B/D
OPM_DELTA_FULL_AT = 0.05  # +5pp operating margin YoY → full E


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


def latest_delta(yoy: dict[str, float]) -> float | None:
    """Latest adjacent-quarter ΔYoY (newer YoY − older YoY)."""
    if len(yoy) < 2:
        return None
    frames = sorted_frames(list(yoy.keys()))
    for i in range(len(frames) - 1, 0, -1):
        newer, older = frames[i], frames[i - 1]
        if is_next_quarter(older, newer):
            return float(yoy[newer]) - float(yoy[older])
    return None


def latest_margin_yoy_delta(margin: pd.Series) -> float | None:
    """Latest margin_t − margin_{t-4} (YoY change in fraction points)."""
    if margin is None or margin.empty:
        return None
    data = margin.dropna().to_dict()
    frames = sorted_frames(list(data.keys()))
    for frame in reversed(frames):
        prev = data.get(prior_year_frame(frame))
        if prev is None:
            continue
        return float(data[frame]) - float(prev)
    return None


def count_accel_quarters(yoy: dict[str, float]) -> int:
    """Count consecutive YoY-rate increases from the latest quarter (diagnostic)."""
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
    """Diagnostic: consecutive quarters where margin > year-ago margin."""
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
        older = frames[i - 1]
        if not is_next_quarter(older, frame):
            break
    return count


def growth_points(yoy: float | None, weight: float) -> float:
    """Legacy YoY level curve (kept for tests / optional reuse)."""
    if yoy is None or yoy < 0:
        return 0.0
    if yoy < 0.25:
        return weight * (12.0 / 25.0) * (yoy / 0.25)
    if yoy < 0.50:
        return weight * (12.0 / 25.0) + weight * (8.0 / 25.0) * ((yoy - 0.25) / 0.25)
    extra = min(1.0, (yoy - 0.50) / 0.50)
    return weight * (20.0 / 25.0) + weight * (5.0 / 25.0) * extra


def accel_points(n_consec: int, weight: float) -> float:
    """Legacy streak curve (diagnostic / optional reuse)."""
    if n_consec <= 0:
        return 0.0
    if n_consec == 1:
        return 0.5 * weight
    return weight


def roe_points(roe: float | None, weight: float, target: float = 0.17) -> float:
    if roe is None or roe <= 0 or weight <= 0:
        return 0.0
    return weight * min(1.0, roe / target)


def winsorize_surprise(surprise: float | None, limit: float) -> float | None:
    if surprise is None:
        return None
    if limit <= 0:
        return float(surprise)
    return max(-limit, min(limit, float(surprise)))


def surprise_points(
    surprise: float | None,
    weight: float,
    *,
    full_at: float = SURPRISE_FULL_AT,
) -> float:
    """Map EPS surprise (fraction beat) to [0, weight]. Misses → 0."""
    if surprise is None or weight <= 0 or full_at <= 0:
        return 0.0
    if surprise < 0:
        return 0.0
    return weight * min(1.0, float(surprise) / full_at)


def delta_points(
    delta: float | None,
    weight: float,
    *,
    full_at: float = DYOY_FULL_AT,
) -> float:
    """Map ΔYoY (pp as fraction, e.g. 0.10 = +10pp) to [0, weight]."""
    if delta is None or weight <= 0 or full_at <= 0:
        return 0.0
    if delta <= 0:
        return 0.0
    return weight * min(1.0, float(delta) / full_at)


def margin_delta_points(
    delta: float | None,
    weight: float,
    *,
    full_at: float = OPM_DELTA_FULL_AT,
) -> float:
    """Map operating-margin YoY change (fraction points) to [0, weight]."""
    if delta is None or weight <= 0 or full_at <= 0:
        return 0.0
    if delta <= 0:
        return 0.0
    return weight * min(1.0, float(delta) / full_at)


def accel_quality(n: int, qp: QualityParams) -> float:
    """Map consecutive accel depth to quality multiplier."""
    if not qp.enabled:
        return 1.0
    if n < qp.accel_min_n:
        return 0.0
    if n >= qp.accel_full_n:
        return 1.0
    return float(qp.accel_partial)


def margin_quality(source: str, qp: QualityParams) -> float:
    if not qp.enabled:
        return 1.0 if source != "none" else 0.0
    if source == "opm":
        return 1.0
    if source == "npm":
        return float(qp.npm_quality)
    return 0.0


def pick_margin_series(
    opm: pd.Series,
    npm: pd.Series,
) -> tuple[pd.Series, str]:
    """Prefer OPM when YoY-delta is computable; else NPM; else empty."""
    if opm is not None and not opm.dropna().empty:
        if latest_margin_yoy_delta(opm) is not None or opm.dropna().shape[0] >= 2:
            # Prefer OPM if we have ≥2 points (delta may still be None)
            if latest_margin_yoy_delta(opm) is not None:
                return opm, "opm"
            if opm.dropna().shape[0] >= 2:
                return opm, "opm"
    if npm is not None and not npm.dropna().empty and latest_margin_yoy_delta(npm) is not None:
        return npm, "npm"
    if npm is not None and npm.dropna().shape[0] >= 2:
        return npm, "npm"
    return pd.Series(dtype=float), "none"


@dataclass
class ScoreBreakdown:
    ticker: str
    s_surprise: float
    b_eps_dyoy: float
    d_sales_dyoy: float
    e_opm_delta: float
    raw: float
    fund_score: float
    eps_surprise: float | None
    eps_yoy: float | None
    sales_yoy: float | None
    eps_dyoy: float | None
    sales_dyoy: float | None
    opm_delta: float | None
    margin_source: str  # "opm" | "npm" | "none"
    eps_accel_n: int
    sales_accel_n: int
    margin_n: int
    roe: float | None
    source: str
    # v2.1 quality layer
    b_quality: float = 1.0
    d_quality: float = 1.0
    e_quality: float = 1.0
    b_raw: float = 0.0
    d_raw: float = 0.0
    e_raw: float = 0.0
    b_status: str = "scored"
    d_status: str = "scored"
    e_status: str = "scored"

    def as_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "fund_score": round(self.fund_score, 1),
            "fund_raw": round(self.raw, 2),
            "s_surprise": round(self.s_surprise, 2),
            "b_eps_dyoy": round(self.b_eps_dyoy, 2),
            "d_sales_dyoy": round(self.d_sales_dyoy, 2),
            "e_opm_delta": round(self.e_opm_delta, 2),
            "b_raw": round(self.b_raw, 2),
            "d_raw": round(self.d_raw, 2),
            "e_raw": round(self.e_raw, 2),
            "b_quality": round(self.b_quality, 2),
            "d_quality": round(self.d_quality, 2),
            "e_quality": round(self.e_quality, 2),
            "b_status": self.b_status,
            "d_status": self.d_status,
            "e_status": self.e_status,
            "eps_surprise_pct": None
            if self.eps_surprise is None
            else round(self.eps_surprise * 100, 1),
            "eps_yoy_pct": None if self.eps_yoy is None else round(self.eps_yoy * 100, 1),
            "sales_yoy_pct": None if self.sales_yoy is None else round(self.sales_yoy * 100, 1),
            "eps_dyoy_pp": None if self.eps_dyoy is None else round(self.eps_dyoy * 100, 1),
            "sales_dyoy_pp": None if self.sales_dyoy is None else round(self.sales_dyoy * 100, 1),
            "opm_delta_pp": None if self.opm_delta is None else round(self.opm_delta * 100, 1),
            "margin_source": self.margin_source,
            "eps_accel_n": self.eps_accel_n,
            "sales_accel_n": self.sales_accel_n,
            "margin_n": self.margin_n,
            "roe_pct": None if self.roe is None else round(self.roe * 100, 1),
            "source": self.source,
        }


def _factor_status(delta: float | None, n: int, q: float, qp: QualityParams) -> str:
    if delta is None:
        return "no_data"
    if delta <= 0:
        return "nonpositive_delta"
    if qp.enabled and n < qp.accel_min_n:
        return "shallow_accel"
    if q < 1.0 and qp.enabled:
        return "partial_quality"
    return "scored"


def score_ticker(
    ticker: str,
    quarterly: pd.DataFrame,
    roe: float | None,
    source: str = "",
    weights: FundamentalWeights = DEFAULT_WEIGHTS,
    roe_target: float = 0.17,  # retained for API compat; unused (G=0)
    eps_surprise: float | None = None,
    quality: QualityParams = DEFAULT_QUALITY,
) -> ScoreBreakdown:
    del roe_target  # phase-1: ROE out of scorer
    eps = quarterly["eps"] if "eps" in quarterly.columns else pd.Series(dtype=float)
    rev = quarterly["revenue"] if "revenue" in quarterly.columns else pd.Series(dtype=float)
    npm = quarterly["npm"] if "npm" in quarterly.columns else pd.Series(dtype=float)
    opm = quarterly["opm"] if "opm" in quarterly.columns else pd.Series(dtype=float)

    eps_yoy_map = yoy_growth_map(eps)
    sales_yoy_map = yoy_growth_map(rev)

    eps_yoy = latest_yoy(eps_yoy_map)
    sales_yoy = latest_yoy(sales_yoy_map)
    eps_dyoy = latest_delta(eps_yoy_map)
    sales_dyoy = latest_delta(sales_yoy_map)
    eps_n = count_accel_quarters(eps_yoy_map)
    sales_n = count_accel_quarters(sales_yoy_map)

    margin_s, margin_source = pick_margin_series(opm, npm)
    opm_d = latest_margin_yoy_delta(margin_s) if margin_source != "none" else None
    margin_n = count_margin_improve_quarters(margin_s) if margin_source != "none" else 0

    surprise_w = winsorize_surprise(eps_surprise, quality.surprise_winsor)
    s = surprise_points(surprise_w, weights.eps_surprise)
    b_raw = delta_points(eps_dyoy, weights.eps_dyoy)
    d_raw = delta_points(sales_dyoy, weights.sales_dyoy)
    e_raw = margin_delta_points(opm_d, weights.opm_delta)

    q_b = accel_quality(eps_n, quality)
    q_d = accel_quality(sales_n, quality)
    q_e = margin_quality(margin_source, quality)

    b = b_raw * q_b
    d = d_raw * q_d
    e = e_raw * q_e

    raw = s + b + d + e
    # Keep 0–100 scale with fixed weight total (quality may leave headroom unused)
    fund = (raw / weights.total) * 100.0 if weights.total else 0.0

    return ScoreBreakdown(
        ticker=ticker.upper(),
        s_surprise=s,
        b_eps_dyoy=b,
        d_sales_dyoy=d,
        e_opm_delta=e,
        raw=raw,
        fund_score=fund,
        eps_surprise=eps_surprise,
        eps_yoy=eps_yoy,
        sales_yoy=sales_yoy,
        eps_dyoy=eps_dyoy,
        sales_dyoy=sales_dyoy,
        opm_delta=opm_d,
        margin_source=margin_source,
        eps_accel_n=eps_n,
        sales_accel_n=sales_n,
        margin_n=margin_n,
        roe=roe,
        source=source,
        b_quality=q_b,
        d_quality=q_d,
        e_quality=q_e,
        b_raw=b_raw,
        d_raw=d_raw,
        e_raw=e_raw,
        b_status=_factor_status(eps_dyoy, eps_n, q_b, quality),
        d_status=_factor_status(sales_dyoy, sales_n, q_d, quality),
        e_status=(
            "no_data"
            if margin_source == "none" or opm_d is None
            else (
                "nonpositive_delta"
                if opm_d is not None and opm_d <= 0
                else ("npm_penalty" if margin_source == "npm" and quality.enabled else "scored")
            )
        ),
    )
