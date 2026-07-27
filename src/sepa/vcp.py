"""VCP (Volatility Contraction Pattern) detector.

Algorithm (docs/strategy_spec.md §4):
  1. Base identification  — highest high inside the scan window is the left
     peak; the base runs from that peak to today.
  2. Contraction analysis — ZigZag swings inside the base; each (swing high →
     swing low) leg is a contraction whose depths must shrink sequentially.
  3. Volume dry-up        — recent volume must be well below the 50-day average.
  4. Signal               — pivot is the high of the final contraction;
     classify WATCHLIST / BREAKOUT / EXTENDED / FORMING.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from sepa.config import VCPParams

TRADING_DAYS_PER_WEEK = 5
# Ignore the most recent bars when locating the base's left peak, so that a
# fresh breakout day does not become its own "base high".
BASE_PEAK_EXCLUDE_DAYS = 5


class Signal(str, Enum):
    BREAKOUT = "BREAKOUT"    # pivot cleared on above-average volume
    WATCHLIST = "WATCHLIST"  # setup complete, price near/at pivot
    EXTENDED = "EXTENDED"    # pivot cleared too far — do not chase
    FORMING = "FORMING"      # valid contraction structure, price below watch zone
    NONE = "NONE"


@dataclass
class Swing:
    kind: str  # 'H' or 'L'
    pos: int   # positional index within the base frame
    price: float


@dataclass
class Contraction:
    high_pos: int
    high: float
    low_pos: int
    low: float

    @property
    def depth(self) -> float:
        return (self.high - self.low) / self.high

    @property
    def duration_days(self) -> int:
        """Trading bars from swing high to swing low (inclusive span length)."""
        return max(0, self.low_pos - self.high_pos)


@dataclass
class VCPResult:
    valid: bool
    signal: Signal = Signal.NONE
    reason: str = ""
    pivot: float | None = None
    dist_to_pivot_pct: float | None = None
    base_weeks: float | None = None
    contractions: list[Contraction] = field(default_factory=list)
    footprint: str = ""
    final_depth: float | None = None
    dryup_ratio_actual: float | None = None
    volume_vs_avg: float | None = None
    # Phase-1 operator UX (detection rules unchanged): stop = last contraction low.
    stop: float | None = None
    risk_pct: float | None = None  # (pivot - stop) / pivot * 100 — risk if buying at pivot
    quality_score: float | None = None  # 0–100 pattern quality (not a buy signal)


def zigzag_from_high(high: pd.Series, low: pd.Series, threshold: float) -> list[Swing]:
    """ZigZag swings assuming position 0 is a confirmed swing high.

    A reversal is confirmed once price moves `threshold` (fraction) against
    the running extreme. The final, unconfirmed extreme is not emitted.
    """
    h, l = high.to_numpy(), low.to_numpy()
    swings = [Swing("H", 0, float(h[0]))]
    direction = -1  # searching for a swing low
    ext_pos, ext_price = 0, float(l[0])
    for i in range(1, len(h)):
        if direction == -1:
            if l[i] <= ext_price:
                ext_pos, ext_price = i, float(l[i])
            elif h[i] >= ext_price * (1 + threshold):
                swings.append(Swing("L", ext_pos, ext_price))
                direction = 1
                ext_pos, ext_price = i, float(h[i])
        else:
            if h[i] >= ext_price:
                ext_pos, ext_price = i, float(h[i])
            elif l[i] <= ext_price * (1 - threshold):
                swings.append(Swing("H", ext_pos, ext_price))
                direction = -1
                ext_pos, ext_price = i, float(l[i])
    return swings


def _build_contractions(swings: list[Swing], base: pd.DataFrame) -> list[Contraction]:
    """Pair each swing high with the following swing low.

    If the last confirmed swing is a high, the leg still in progress (running
    low from that high through today) counts as the final contraction.
    """
    contractions = []
    i = 0
    while i + 1 < len(swings):
        if swings[i].kind == "H" and swings[i + 1].kind == "L":
            contractions.append(
                Contraction(swings[i].pos, swings[i].price, swings[i + 1].pos, swings[i + 1].price)
            )
            i += 2
        else:  # pragma: no cover - zigzag guarantees alternation
            i += 1

    last = swings[-1]
    if last.kind == "H" and last.pos < len(base) - 1:
        tail_low = base["low"].iloc[last.pos + 1 :]
        contractions.append(
            Contraction(last.pos, last.price, last.pos + 1 + int(tail_low.argmin()), float(tail_low.min()))
        )
    return contractions


def _merge_minor_contractions(contractions: list[Contraction], min_retrace: float) -> list[Contraction]:
    """Merge noise wiggles into their parent contraction.

    A new "major" contraction only starts when the rally into its swing high
    retraces at least `min_retrace` of the previous contraction's range.
    Otherwise the leg is a continuation of the same decline and the two are
    merged (keep the earlier high, take the deeper low).
    """
    if not contractions:
        return contractions
    merged = [contractions[0]]
    for cur in contractions[1:]:
        prev = merged[-1]
        prev_range = prev.high - prev.low
        retrace = (cur.high - prev.low) / prev_range if prev_range > 0 else 1.0
        if retrace < min_retrace:
            if cur.low < prev.low:
                prev.low, prev.low_pos = cur.low, cur.low_pos
        else:
            merged.append(cur)
    return merged


def compute_quality_score(
    depths: list[float],
    *,
    dryup_ratio: float,
    dist_to_pivot_pct: float,
    p: VCPParams,
) -> float:
    """Pattern-quality score 0–100 (execution/timing is separate via ``signal``).

    Weights (phase-1, intentionally simple):
      - tightening 40: how much each contraction shrinks vs the prior
      - final depth 25: shallower last contraction is better
      - volume dry-up 25: lower recent/50d volume ratio is better
      - pivot proximity 10: closer to pivot (from below) scores higher;
        already extended above ``max_extension`` scores near zero
    """
    if len(depths) < 2:
        return 0.0

    # 1) Tightening: reward ratio well below decay ceiling
    step_scores = []
    for prev, cur in zip(depths, depths[1:]):
        if prev <= 0:
            continue
        ratio = cur / prev
        # full marks at ratio <= 0.5 (classic "half rule"), zero at ratio >= decay
        ceiling = max(p.contraction_decay, 0.51)
        if ratio <= 0.5:
            step_scores.append(1.0)
        elif ratio >= ceiling:
            step_scores.append(0.0)
        else:
            step_scores.append(1.0 - (ratio - 0.5) / (ceiling - 0.5))
    tighten = 40.0 * (sum(step_scores) / len(step_scores) if step_scores else 0.0)

    # 2) Final contraction depth: full at <=5%, zero at >= final_contraction_max
    final = depths[-1]
    fmax = max(p.final_contraction_max, 0.051)
    if final <= 0.05:
        final_pts = 25.0
    elif final >= fmax:
        final_pts = 0.0
    else:
        final_pts = 25.0 * (1.0 - (final - 0.05) / (fmax - 0.05))

    # 3) Dry-up: full at ≤0.40, zero at ≥0.80 (linear in between)
    if dryup_ratio <= 0.40:
        dry_pts = 25.0
    elif dryup_ratio >= 0.80:
        dry_pts = 0.0
    else:
        dry_pts = 25.0 * (1.0 - (dryup_ratio - 0.40) / 0.40)

    # 4) Pivot proximity (pattern readiness, not a buy gate)
    dist = dist_to_pivot_pct / 100.0  # fraction
    if dist > p.max_extension:
        prox_pts = 0.0
    elif dist >= 0:
        # at/above pivot but within extension band
        prox_pts = 10.0 * (1.0 - dist / max(p.max_extension, 1e-6))
    else:
        # below pivot: full marks inside watch zone, fades further away
        depth_below = -dist
        if depth_below <= p.watch_zone_pct:
            prox_pts = 10.0
        else:
            prox_pts = max(0.0, 10.0 * (1.0 - (depth_below - p.watch_zone_pct) / 0.15))

    return round(max(0.0, min(100.0, tighten + final_pts + dry_pts + prox_pts)), 1)


def detect_vcp(df: pd.DataFrame, p: VCPParams) -> VCPResult:
    """Detect a VCP setup on the last row of an indicator-enriched frame.

    Requires columns: open, high, low, close, volume, vol_sma50.
    ``reason`` strings are Korean for operator-facing reports/charts.
    """
    scan_days = p.base_max_weeks * TRADING_DAYS_PER_WEEK
    window = df.tail(scan_days)
    if len(window) < p.base_min_weeks * TRADING_DAYS_PER_WEEK:
        return VCPResult(valid=False, reason="베이스 스캔용 가격 이력 부족")

    # 1. Base identification
    peak_search = window.iloc[: -BASE_PEAK_EXCLUDE_DAYS] if len(window) > BASE_PEAK_EXCLUDE_DAYS else window
    peak_pos = int(peak_search["high"].argmax())
    base = window.iloc[peak_pos:]
    base_days = len(base)
    if base_days < p.base_min_weeks * TRADING_DAYS_PER_WEEK:
        return VCPResult(valid=False, reason=f"베이스 기간 부족 ({base_days}일, 최소 {p.base_min_weeks}주)")

    base_high = float(base["high"].iloc[0])
    base_depth = (base_high - float(base["low"].min())) / base_high
    if base_depth > p.max_base_depth:
        return VCPResult(valid=False, reason=f"베이스 낙폭 과다 ({base_depth:.1%}, 상한 {p.max_base_depth:.0%})")

    # 2. Contraction structure
    swings = zigzag_from_high(base["high"], base["low"], p.swing_threshold)
    contractions = _build_contractions(swings, base)
    contractions = _merge_minor_contractions(contractions, p.contraction_min_retrace)
    n = len(contractions)
    if not (p.min_contractions <= n <= p.max_contractions):
        return VCPResult(
            valid=False,
            reason=f"수축 횟수 {n}회 (허용 {p.min_contractions}~{p.max_contractions}회)",
        )

    # Phase-2: first contraction must be a real base leg (not a shallow wiggle)
    t1 = contractions[0].depth
    if t1 < p.t1_depth_min:
        return VCPResult(
            valid=False,
            reason=f"첫 수축 깊이 부족 ({t1:.1%}, 최소 {p.t1_depth_min:.0%})",
        )

    # Phase-2: each major contraction must last long enough (drop 1-day noise)
    short = [c for c in contractions if c.duration_days < p.min_contraction_days]
    if short:
        days_list = "/".join(str(c.duration_days) for c in contractions)
        return VCPResult(
            valid=False,
            reason=(
                f"수축 기간 부족 ({days_list}일, 최소 {p.min_contraction_days}일)"
            ),
        )

    depths = [c.depth for c in contractions]
    for prev, cur in zip(depths, depths[1:]):
        if cur > prev * p.contraction_decay:
            return VCPResult(
                valid=False,
                reason=f"수축이 점점 얕아지지 않음 ({_fmt_depths(depths)})",
            )
    if depths[-1] > p.final_contraction_max:
        return VCPResult(
            valid=False,
            reason=f"마지막 수축이 너무 깊음 ({depths[-1]:.1%}, 상한 {p.final_contraction_max:.0%})",
        )

    # 3. Volume dry-up
    vol_sma50 = float(df["vol_sma50"].iloc[-1])
    if pd.isna(vol_sma50) or vol_sma50 <= 0:
        return VCPResult(valid=False, reason="거래량 기준선(50일 평균) 없음")
    recent_vol = float(df["volume"].tail(p.dryup_days).mean())
    dryup_actual = recent_vol / vol_sma50
    last_vol_ratio = float(df["volume"].iloc[-1]) / vol_sma50

    pivot = contractions[-1].high
    stop = contractions[-1].low
    close = float(df["close"].iloc[-1])
    dist_to_pivot = close / pivot - 1.0
    risk_pct = (pivot - stop) / pivot * 100.0 if pivot > 0 else None
    qscore = compute_quality_score(
        depths,
        dryup_ratio=dryup_actual,
        dist_to_pivot_pct=dist_to_pivot * 100.0,
        p=p,
    )

    base_weeks = round(base_days / TRADING_DAYS_PER_WEEK, 1)
    footprint = f"{int(round(base_weeks))}W {_fmt_depths(depths)} {n}T"
    result = VCPResult(
        valid=True,
        pivot=round(pivot, 2),
        dist_to_pivot_pct=round(dist_to_pivot * 100, 2),
        base_weeks=base_weeks,
        contractions=contractions,
        footprint=footprint,
        final_depth=round(depths[-1], 4),
        dryup_ratio_actual=round(dryup_actual, 2),
        volume_vs_avg=round(last_vol_ratio, 2),
        stop=round(stop, 2),
        risk_pct=round(risk_pct, 2) if risk_pct is not None else None,
        quality_score=qscore,
    )

    # 4. Signal classification
    if close > pivot * (1 + p.pivot_buffer):
        if dist_to_pivot > p.max_extension:
            result.signal = Signal.EXTENDED
            result.reason = "피벗 돌파 후 이격 과다 — 추격 금지"
        elif last_vol_ratio >= p.breakout_vol_mult:
            result.signal = Signal.BREAKOUT
            result.reason = "피벗 돌파 + 거래량 확인"
        else:
            result.signal = Signal.WATCHLIST
            result.reason = "피벗은 돌파했으나 거래량 미확인"
    else:
        if dryup_actual > p.dryup_ratio:
            result.valid = False
            result.signal = Signal.NONE
            result.reason = (
                f"거래량 고갈 부족 ({dryup_actual:.2f} > {p.dryup_ratio})"
            )
            # keep stop / quality_score — structure was good enough to score
        elif close >= pivot * (1 - p.watch_zone_pct):
            result.signal = Signal.WATCHLIST
            result.reason = "셋업 완료, 피벗 근접 (돌파 임박)"
        else:
            result.signal = Signal.FORMING
            result.reason = "구조는 유효, 아직 감시구간 아래"
    return result


def _fmt_depths(depths: list[float]) -> str:
    return "/".join(f"{d * 100:.0f}" for d in depths)
