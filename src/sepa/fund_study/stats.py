"""Correlation, orthogonalization, and weight proposals."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from numpy.linalg import lstsq

from sepa.fund_study.config import DELTA_FACTORS, LEVEL_FACTORS, MAIN_FACTORS, SPEED_FACTORS

logger = logging.getLogger(__name__)

# Current fund weights (for comparison table) — maps loosely to study factors
CURRENT_WEIGHT_HINTS = {
    "eps_yoy": 25.0,
    "eps_dyoy": 20.0,  # was accel
    "sales_yoy": 15.0,
    "sales_dyoy": 10.0,
    "npm_d": 15.0,
    "opm_d": 15.0,
    "eps_surprise": 0.0,
    "sales_surprise": 0.0,
}


def _safe_spearman(x: pd.Series, y: pd.Series) -> float:
    a = pd.concat([x, y], axis=1).dropna()
    if len(a) < 30:
        return float("nan")
    # Rank-Pearson avoids hard dependency on scipy (pandas spearman imports it)
    return float(a.iloc[:, 0].rank().corr(a.iloc[:, 1].rank(), method="pearson"))


def _safe_pearson(x: pd.Series, y: pd.Series) -> float:
    a = pd.concat([x, y], axis=1).dropna()
    if len(a) < 30:
        return float("nan")
    return float(a.iloc[:, 0].corr(a.iloc[:, 1], method="pearson"))


def factor_correlations(
    panel: pd.DataFrame,
    *,
    y_col: str = "ret_mkt",
    factors: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    factors = factors or (MAIN_FACTORS + SPEED_FACTORS)
    rows = []
    for f in factors:
        if f not in panel.columns:
            continue
        x = pd.to_numeric(panel[f], errors="coerce")
        y = pd.to_numeric(panel[y_col], errors="coerce")
        n = int(pd.concat([x, y], axis=1).dropna().shape[0])
        rows.append(
            {
                "factor": f,
                "n": n,
                "spearman": _safe_spearman(x, y),
                "pearson": _safe_pearson(x, y),
            }
        )
    return pd.DataFrame(rows)


def choose_level_or_delta(corr: pd.DataFrame) -> pd.DataFrame:
    """For paired level/delta families, keep the stronger |spearman|.

    Also picks one of npm_d / opm_d (margin pair) per locked spec.
    """
    pairs = [
        ("eps_yoy", "eps_dyoy"),
        ("sales_yoy", "sales_dyoy"),
        ("eps_qoq", "eps_dqoq"),
        ("sales_qoq", "sales_dqoq"),
        ("npm_d", "opm_d"),  # Margin_Δ: measure both, adopt one
    ]
    keep = set(corr["factor"])
    drop: set[str] = set()
    notes = []
    for a, b in pairs:
        if a not in keep or b not in keep:
            continue
        sa = abs(float(corr.loc[corr["factor"] == a, "spearman"].iloc[0]))
        sb = abs(float(corr.loc[corr["factor"] == b, "spearman"].iloc[0]))
        if not np.isfinite(sa) and not np.isfinite(sb):
            continue
        if not np.isfinite(sa) or (np.isfinite(sb) and sb >= sa):
            drop.add(a)
            notes.append(f"{b} over {a}")
        else:
            drop.add(b)
            notes.append(f"{a} over {b}")
    out = corr[~corr["factor"].isin(drop)].copy()
    out.attrs["choice_notes"] = notes
    return out


def main_factors_only(corr_or_factors: pd.DataFrame | list[str]) -> list[str]:
    """Drop QoQ/speed factors from weight estimation (validation-only)."""
    if isinstance(corr_or_factors, pd.DataFrame):
        names = corr_or_factors["factor"].tolist()
    else:
        names = list(corr_or_factors)
    speed = set(SPEED_FACTORS)
    return [f for f in names if f not in speed]


def orthogonalize_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Sequential residualization in given column order (Gram-Schmidt-like)."""
    work = df[cols].apply(pd.to_numeric, errors="coerce")
    out = pd.DataFrame(index=work.index)
    for i, c in enumerate(cols):
        y = work[c]
        if i == 0:
            out[c] = y
            continue
        X = out[cols[:i]].copy()
        mask = y.notna()
        for cc in X.columns:
            mask &= X[cc].notna()
        resid = y.copy()
        if mask.sum() >= max(30, i + 5):
            Xn = np.column_stack([np.ones(mask.sum()), X.loc[mask].to_numpy()])
            yn = y.loc[mask].to_numpy()
            coef, *_ = lstsq(Xn, yn, rcond=None)
            pred = Xn @ coef
            resid.loc[mask] = yn - pred
        out[c] = resid
    return out


def partial_spearman_vs_y(
    panel: pd.DataFrame,
    factors: list[str],
    *,
    y_col: str = "ret_mkt",
) -> pd.DataFrame:
    """Spearman of sequentially orthogonalized factors vs y."""
    use = [f for f in factors if f in panel.columns]
    if not use:
        return pd.DataFrame()
    # order: levels first then deltas for stability
    ordered = [f for f in use if f in LEVEL_FACTORS] + [f for f in use if f not in LEVEL_FACTORS]
    ortho = orthogonalize_columns(panel, ordered)
    y = pd.to_numeric(panel[y_col], errors="coerce")
    rows = []
    for f in ordered:
        n = int(pd.concat([ortho[f], y], axis=1).dropna().shape[0])
        rows.append(
            {
                "factor": f,
                "n": n,
                "spearman_ortho": _safe_spearman(ortho[f], y),
                "pearson_ortho": _safe_pearson(ortho[f], y),
            }
        )
    return pd.DataFrame(rows)


def quantile_response(
    panel: pd.DataFrame,
    factor: str,
    *,
    y_col: str = "ret_mkt",
    q: float = 0.2,
) -> float:
    """Top-q mean y minus bottom-q mean y."""
    a = panel[[factor, y_col]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(a) < 50:
        return float("nan")
    lo = a[factor].quantile(q)
    hi = a[factor].quantile(1 - q)
    return float(a.loc[a[factor] >= hi, y_col].mean() - a.loc[a[factor] <= lo, y_col].mean())


def propose_weights(
    ortho_corr: pd.DataFrame,
    *,
    total: float = 100.0,
) -> pd.DataFrame:
    """w ∝ max(0, spearman_ortho); flag negatives as reverse candidates."""
    if ortho_corr.empty:
        return ortho_corr
    work = ortho_corr.copy()
    work = work.dropna(subset=["spearman_ortho"]).reset_index(drop=True)
    if work.empty:
        return work
    work["corr_used"] = work["spearman_ortho"]
    work["reverse_candidate"] = work["corr_used"] < 0
    work["w_raw"] = work["corr_used"].clip(lower=0.0)
    s = float(work["w_raw"].sum())
    work["weight"] = (work["w_raw"] / s * total) if s > 0 else 0.0
    work["current_hint"] = work["factor"].map(CURRENT_WEIGHT_HINTS).fillna(0.0)
    return work.sort_values("weight", ascending=False).reset_index(drop=True)


def yearly_stability(
    panel: pd.DataFrame,
    factors: list[str],
    *,
    y_col: str = "ret_mkt",
) -> pd.DataFrame:
    if panel.empty or "day0" not in panel.columns:
        return pd.DataFrame()
    work = panel.copy()
    work["year"] = pd.to_datetime(work["day0"]).dt.year
    rows = []
    for year, g in work.groupby("year"):
        for f in factors:
            if f not in g.columns:
                continue
            rows.append(
                {
                    "year": int(year),
                    "factor": f,
                    "n": int(g[[f, y_col]].dropna().shape[0]),
                    "spearman": _safe_spearman(
                        pd.to_numeric(g[f], errors="coerce"),
                        pd.to_numeric(g[y_col], errors="coerce"),
                    ),
                }
            )
    return pd.DataFrame(rows)
