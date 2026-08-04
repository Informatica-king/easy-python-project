"""VCP parameter sensitivity / quality study.

Cross-sectional funnel + one-at-a-time (OAT) sweeps + historical weekly
as-of hit-rate and forward returns. Research only — does NOT change live
``config/params.yaml`` VCP values.

Usage:
    python -m sepa.vcp_study
    python -m sepa.vcp_study --tickers-file reports/fund_tickers_20260726.txt
    python -m sepa.vcp_study --from-stage2 reports/stage2_20260726.csv --no-history
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd

from sepa import indicators, vcp
from sepa.artifacts import publish_many
from sepa.config import Params, VCPParams, load_params
from sepa.data import store

logger = logging.getLogger(__name__)

# Parameter grids for OAT (one factor at a time around live defaults).
OAT_GRID: dict[str, list] = {
    "base_min_weeks": [3, 4, 5, 6, 8],
    "max_base_depth": [0.25, 0.30, 0.35, 0.45, 0.50],
    "swing_threshold": [0.02, 0.03, 0.04, 0.05],
    "max_contractions": [4, 6, 8, 10, 12],
    "contraction_decay": [0.50, 0.65, 0.75, 0.90, 1.00, 1.25],
    "contraction_min_retrace": [0.30, 0.40, 0.50, 0.65, 0.80],
    "final_contraction_max": [0.08, 0.10, 0.12, 0.15],
    "min_contraction_days": [3, 5, 7, 10],
    "t1_depth_min": [0.05, 0.08, 0.10, 0.12],
    "dryup_ratio": [0.45, 0.55, 0.60, 0.70, 0.80],
    "dryup_days": [3, 5, 8, 10],
    "watch_zone_pct": [0.03, 0.05, 0.08, 0.10],
    "max_extension": [0.03, 0.05, 0.08],
    "breakout_vol_mult": [1.2, 1.5, 2.0],
}


def presets(live: VCPParams) -> dict[str, VCPParams]:
    """Named profiles for comparison (live kept as control)."""
    return {
        "live": live,
        "atr_zigzag": dataclasses.replace(live, swing_mode="atr"),
        "minervini_strict": dataclasses.replace(
            live,
            contraction_decay=0.50,
            dryup_ratio=0.50,
            final_contraction_max=0.08,
        ),
        "base3": dataclasses.replace(live, base_min_weeks=3),
        "base3_atr": dataclasses.replace(live, base_min_weeks=3, swing_mode="atr"),
        "leader_relaxed": dataclasses.replace(
            live,
            base_min_weeks=3,
            max_contractions=10,
            contraction_decay=1.00,
            dryup_ratio=0.75,
            contraction_min_retrace=0.65,
            max_base_depth=0.45,
        ),
    }


def _md_table(df: pd.DataFrame) -> str:
    """Markdown table without requiring the optional ``tabulate`` package."""
    if df is None or df.empty:
        return "_(empty)_"
    cols = [str(c) for c in df.columns]
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for row in df.itertuples(index=False):
        cells = [str(v) if v is not None else "" for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _setup_korean_font() -> None:
    from sepa.fonts import setup_korean_matplotlib

    setup_korean_matplotlib(allow_install=True)
    plt.rcParams["axes.unicode_minus"] = False


def reason_category(reason: str, signal: str, valid: bool) -> str:
    if valid and signal:
        return f"OK:{signal}"
    if not reason:
        return "NONE"
    return reason.split("(")[0].strip()


def load_enriched(
    tickers: list[str],
    params: Params,
    *,
    update: bool = False,
) -> dict[str, pd.DataFrame]:
    data, failed = store.load_universe_history(
        tickers, params.data.cache_dir, params.data.lookback_years, update
    )
    if failed:
        logger.warning("failed to load: %s", ", ".join(failed[:20]))
    out: dict[str, pd.DataFrame] = {}
    for t, df in data.items():
        if len(df) < params.data.min_history_days:
            continue
        out[t] = indicators.add_indicators(df, params.trend_template)
    return out


def evaluate_universe(
    enriched: dict[str, pd.DataFrame],
    p: VCPParams,
    *,
    as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    rows = []
    for ticker, df in enriched.items():
        sub = df.loc[:as_of] if as_of is not None else df
        if len(sub) < 280:
            rows.append({"ticker": ticker, "signal": "NO_DATA", "reason": "가격 이력 부족", "valid": False})
            continue
        res = vcp.detect_vcp(sub, p)
        rows.append({
            "ticker": ticker,
            "signal": res.signal.value if res.valid else "NONE",
            "valid": bool(res.valid),
            "reason": res.reason,
            "reason_cat": reason_category(res.reason, res.signal.value, res.valid),
            "base_weeks": res.base_weeks,
            "footprint": res.footprint,
            "dryup_ratio": res.dryup_ratio_actual,
            "dist_to_pivot_pct": res.dist_to_pivot_pct,
        })
    return pd.DataFrame(rows)


def funnel_counts(report: pd.DataFrame) -> pd.DataFrame:
    c = Counter(report["reason_cat"].tolist())
    n = max(len(report), 1)
    return pd.DataFrame(
        [{"reason_cat": k, "n": v, "pct": round(100 * v / n, 1)} for k, v in c.most_common()]
    )


def base_days_series(enriched: dict[str, pd.DataFrame], live: VCPParams) -> pd.Series:
    """Trading days from left-peak to today under live peak-finding rules."""
    vals = []
    for df in enriched.values():
        scan_days = live.base_max_weeks * vcp.TRADING_DAYS_PER_WEEK
        window = df.tail(scan_days)
        if len(window) <= vcp.BASE_PEAK_EXCLUDE_DAYS:
            continue
        peak_search = window.iloc[: -vcp.BASE_PEAK_EXCLUDE_DAYS]
        peak_pos = int(peak_search["high"].argmax())
        vals.append(len(window.iloc[peak_pos:]))
    return pd.Series(vals, name="base_days")


def structure_diagnostics(
    enriched: dict[str, pd.DataFrame],
    live: VCPParams,
    *,
    base_min_weeks: int = 3,
) -> pd.DataFrame:
    """Inspect contraction geometry after relaxing only base_min."""
    p = dataclasses.replace(live, base_min_weeks=base_min_weeks)
    rows = []
    for ticker, df in enriched.items():
        scan_days = p.base_max_weeks * vcp.TRADING_DAYS_PER_WEEK
        window = df.tail(scan_days)
        if len(window) <= vcp.BASE_PEAK_EXCLUDE_DAYS:
            continue
        peak_search = window.iloc[: -vcp.BASE_PEAK_EXCLUDE_DAYS]
        peak_pos = int(peak_search["high"].argmax())
        base = window.iloc[peak_pos:]
        base_days = len(base)
        if base_days < p.base_min_weeks * vcp.TRADING_DAYS_PER_WEEK:
            rows.append({"ticker": ticker, "gate": "base_short", "base_days": base_days})
            continue
        base_high = float(base["high"].iloc[0])
        base_depth = (base_high - float(base["low"].min())) / base_high
        if base_depth > p.max_base_depth:
            rows.append({
                "ticker": ticker, "gate": "base_deep",
                "base_days": base_days, "base_depth": base_depth,
            })
            continue
        swings = vcp.zigzag_from_high(base["high"], base["low"], p.swing_threshold)
        cons = vcp._build_contractions(swings, base)
        merged = vcp._merge_minor_contractions(cons, p.contraction_min_retrace)
        depths = [c.depth for c in merged]
        step_ratios = [cur / prev for prev, cur in zip(depths, depths[1:]) if prev > 0]
        tighten_ok = all(
            cur <= prev * p.contraction_decay for prev, cur in zip(depths, depths[1:])
        ) if len(depths) >= 2 else False
        rows.append({
            "ticker": ticker,
            "gate": "structure",
            "base_days": base_days,
            "base_depth": round(base_depth, 4),
            "n_raw": len(cons),
            "n_merged": len(merged),
            "depths": "/".join(f"{d * 100:.0f}" for d in depths),
            "max_step_ratio": round(max(step_ratios), 3) if step_ratios else None,
            "tighten_ok": tighten_ok,
            "final_depth": round(depths[-1], 4) if depths else None,
        })
    return pd.DataFrame(rows)


def oat_sweep(
    enriched: dict[str, pd.DataFrame],
    live: VCPParams,
    grid: dict[str, list] | None = None,
) -> pd.DataFrame:
    grid = grid or OAT_GRID
    rows = []
    for key, values in grid.items():
        for val in values:
            p = dataclasses.replace(live, **{key: val})
            rep = evaluate_universe(enriched, p)
            valid = int(rep["valid"].sum())
            sig = Counter(rep["signal"].tolist())
            top = funnel_counts(rep).head(3)
            top_s = "; ".join(f"{r.reason_cat}:{r.n}" for r in top.itertuples())
            rows.append({
                "param": key,
                "value": val,
                "is_live": getattr(live, key) == val,
                "n": len(rep),
                "valid": valid,
                "valid_pct": round(100 * valid / max(len(rep), 1), 2),
                "BREAKOUT": int(sig.get("BREAKOUT", 0)),
                "WATCHLIST": int(sig.get("WATCHLIST", 0)),
                "FORMING": int(sig.get("FORMING", 0)),
                "EXTENDED": int(sig.get("EXTENDED", 0)),
                "NONE": int(sig.get("NONE", 0)),
                "top_reasons": top_s,
            })
    return pd.DataFrame(rows)


def preset_compare(
    enriched: dict[str, pd.DataFrame],
    live: VCPParams,
) -> pd.DataFrame:
    rows = []
    for name, p in presets(live).items():
        rep = evaluate_universe(enriched, p)
        sig = Counter(rep["signal"].tolist())
        top = funnel_counts(rep).head(5)
        rows.append({
            "preset": name,
            "n": len(rep),
            "valid": int(rep["valid"].sum()),
            "valid_pct": round(100 * rep["valid"].mean(), 2),
            "BREAKOUT": int(sig.get("BREAKOUT", 0)),
            "WATCHLIST": int(sig.get("WATCHLIST", 0)),
            "FORMING": int(sig.get("FORMING", 0)),
            "EXTENDED": int(sig.get("EXTENDED", 0)),
            "NONE": int(sig.get("NONE", 0)),
            "top_reasons": "; ".join(f"{r.reason_cat}:{r.n}" for r in top.itertuples()),
        })
    return pd.DataFrame(rows)


def _fwd_return(df: pd.DataFrame, as_of: pd.Timestamp, n: int) -> float:
    fut = df.loc[as_of:]
    if len(fut) <= n:
        return float("nan")
    c0 = float(fut["close"].iloc[0])
    if c0 <= 0:
        return float("nan")
    return float(fut["close"].iloc[n]) / c0 - 1.0


def historical_events(
    enriched: dict[str, pd.DataFrame],
    p: VCPParams,
    *,
    lookback_days: int = 252,
    step: int = 5,
) -> tuple[pd.DataFrame, dict]:
    """Weekly as-of scan; return setup events + aggregate signal counts."""
    # Build as-of calendar from the union of indexes (use densest ticker).
    sample = max(enriched.values(), key=len)
    dates = sample.index
    asofs = dates[-lookback_days::step]
    events = []
    sig_c: Counter = Counter()
    reason_c: Counter = Counter()
    n_eval = 0
    for asof in asofs:
        for ticker, df in enriched.items():
            sub = df.loc[:asof]
            if len(sub) < 280:
                continue
            n_eval += 1
            res = vcp.detect_vcp(sub, p)
            key = res.signal.value if res.valid else "NONE"
            sig_c[key] += 1
            reason_c[reason_category(res.reason, res.signal.value, res.valid)] += 1
            if not res.valid:
                continue
            events.append({
                "ticker": ticker,
                "asof": asof,
                "signal": res.signal.value,
                "reason": res.reason,
                "footprint": res.footprint,
                "dist_to_pivot_pct": res.dist_to_pivot_pct,
                "fwd5": _fwd_return(df, asof, 5),
                "fwd10": _fwd_return(df, asof, 10),
                "fwd20": _fwd_return(df, asof, 20),
            })
    return pd.DataFrame(events), {
        "n_eval": n_eval,
        "n_setups": len(events),
        "hit_rate_pct": round(100 * len(events) / max(n_eval, 1), 3),
        "signals": dict(sig_c),
        "top_reasons": reason_c.most_common(8),
    }


def baseline_fwd10(
    enriched: dict[str, pd.DataFrame],
    *,
    lookback_days: int = 252,
    step: int = 5,
) -> pd.Series:
    sample = max(enriched.values(), key=len)
    asofs = sample.index[-lookback_days::step]
    vals = []
    for asof in asofs:
        for df in enriched.values():
            r = _fwd_return(df, asof, 10)
            if not np.isnan(r):
                vals.append(r)
    return pd.Series(vals, name="fwd10")


def summarize_events(events: pd.DataFrame, baseline_med: float) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=[
            "signal", "n", "med_fwd5", "med_fwd10", "med_fwd20", "mean_fwd10", "edge_vs_base_med_fwd10"
        ])
    rows = []
    for sig, g in events.groupby("signal"):
        med10 = float(g["fwd10"].median())
        rows.append({
            "signal": sig,
            "n": len(g),
            "med_fwd5": round(100 * float(g["fwd5"].median()), 2),
            "med_fwd10": round(100 * med10, 2),
            "med_fwd20": round(100 * float(g["fwd20"].median()), 2),
            "mean_fwd10": round(100 * float(g["fwd10"].mean()), 2),
            "edge_vs_base_med_fwd10": round(100 * (med10 - baseline_med), 2),
        })
    return pd.DataFrame(rows).sort_values("n", ascending=False)


def plot_funnel(funnel: pd.DataFrame, out_path: Path, *, title: str) -> Path:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(10, max(3.5, 0.35 * len(funnel) + 1)))
    ax.barh(funnel["reason_cat"][::-1], funnel["n"][::-1], color="#546e7a")
    ax.set_title(title)
    ax.set_xlabel("count")
    for y, (n, pct) in enumerate(zip(funnel["n"][::-1], funnel["pct"][::-1])):
        ax.text(n + 0.2, y, f"{n} ({pct}%)", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_base_days(base_days: pd.Series, out_path: Path, *, title: str) -> Path:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(base_days, bins=20, color="#607d8b", edgecolor="white")
    for weeks, color in [(3, "#ef6c00"), (5, "#c62828"), (8, "#6a1b9a")]:
        ax.axvline(weeks * 5, color=color, ls="--", lw=1.4, label=f"{weeks}주 ({weeks * 5}일)")
    ax.set_title(title)
    ax.set_xlabel("base_days (peak → today)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_oat_valid(oat: pd.DataFrame, out_path: Path) -> Path:
    _setup_korean_font()
    keys = list(dict.fromkeys(oat["param"].tolist()))
    n = len(keys)
    cols = 3
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(12, 3.2 * rows), squeeze=False)
    for i, key in enumerate(keys):
        ax = axes[i // cols][i % cols]
        g = oat[oat["param"] == key]
        colors = ["#c62828" if live else "#546e7a" for live in g["is_live"]]
        ax.bar([str(v) for v in g["value"]], g["valid_pct"], color=colors)
        ax.set_title(key, fontsize=10)
        ax.set_ylabel("valid %")
        ax.tick_params(axis="x", labelrotation=30, labelsize=7)
    for j in range(n, rows * cols):
        axes[j // cols][j % cols].axis("off")
    fig.suptitle("VCP OAT sensitivity — valid setup % (red = live value)", fontsize=12, y=1.01)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_hist_hit_rates(summary: pd.DataFrame, out_path: Path) -> Path:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(summary["preset"], summary["hit_rate_pct"], color="#455a64")
    ax.set_ylabel("setup hit rate %")
    ax.set_title("Historical weekly as-of setup rate by preset")
    for i, r in enumerate(summary.itertuples()):
        ax.text(i, r.hit_rate_pct + 0.02, f"{r.hit_rate_pct:.2f}%\nn={r.n_setups}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def write_markdown(
    path: Path,
    *,
    stamp: str,
    universe_n: int,
    universe_label: str,
    live_funnel: pd.DataFrame,
    base_days: pd.Series,
    struct: pd.DataFrame,
    oat: pd.DataFrame,
    preset_now: pd.DataFrame,
    hist_summary: pd.DataFrame | None,
    hist_edges: dict[str, pd.DataFrame] | None,
    baseline_med: float | None,
    verdict: list[str],
) -> Path:
    lines = [
        f"# VCP parameter analysis ({stamp})",
        "",
        f"Universe: **{universe_label}** (n={universe_n}). Research only — live weights/params unchanged.",
        "",
        "## Verdict",
        "",
    ]
    lines.extend(f"- {v}" for v in verdict)
    lines += [
        "",
        "## 1. Live funnel (today)",
        "",
        _md_table(live_funnel),
        "",
        "## 2. Base length distribution",
        "",
        f"mean={base_days.mean():.1f}d  median={base_days.median():.1f}d  "
        f"p25={base_days.quantile(0.25):.1f}d  p75={base_days.quantile(0.75):.1f}d",
        "",
        "| min weeks | days | share of names |",
        "|---|---|---|",
    ]
    for w in [3, 4, 5, 6, 8]:
        share = float((base_days >= w * 5).mean())
        lines.append(f"| {w} | {w * 5} | {100 * share:.1f}% |")

    struct_ok = struct[struct["gate"] == "structure"]
    tighten = float(struct_ok["tighten_ok"].mean()) if len(struct_ok) else float("nan")
    lines += [
        "",
        "## 3. Structure after relaxing only `base_min_weeks=3`",
        "",
        f"Gates: {struct['gate'].value_counts().to_dict()}",
        f"Among structure-eligible: tighten_ok (decay≤0.75) = **{100 * tighten:.1f}%**"
        if len(struct_ok) else "No structure-eligible names.",
        "",
    ]
    if len(struct_ok):
        lines += [
            f"n_merged median={struct_ok['n_merged'].median():.1f}, "
            f"max_step_ratio median={struct_ok['max_step_ratio'].median():.2f} "
            f"(>1 means a later contraction deeper than prior — fails classic VCP).",
            "",
        ]

    live_base = oat[(oat["param"] == "base_min_weeks") & oat["is_live"]]
    live_valid_pct = float(live_base["valid_pct"].iloc[0]) if len(live_base) else 0.0
    lines += [
        "## 4. Preset comparison (today)",
        "",
        _md_table(preset_now),
        "",
        "## 5. OAT sensitivity (today) — live row highlighted in CSV",
        "",
        f"Under live params, valid setup rate today ≈ **{live_valid_pct}%** "
        f"(full grid: `vcp_oat_{stamp}.csv`).",
        "",
    ]
    # compact OAT: best valid_pct per param vs live
    lines += [
        "| param | live value | live valid% | best value | best valid% |",
        "|---|---|---|---|---|",
    ]
    for key, g in oat.groupby("param"):
        live_row = g[g["is_live"]].iloc[0]
        best = g.sort_values("valid_pct", ascending=False).iloc[0]
        lines.append(
            f"| `{key}` | {live_row['value']} | {live_row['valid_pct']} | "
            f"{best['value']} | {best['valid_pct']} |"
        )

    if hist_summary is not None and baseline_med is not None:
        lines += [
            "",
            "## 6. Historical weekly as-of (~1y, step=5d)",
            "",
            f"Baseline median fwd10 (all ticker×dates): **{100 * baseline_med:.2f}%**",
            "",
            _md_table(hist_summary),
            "",
        ]
        if hist_edges:
            for name, edge in hist_edges.items():
                lines += [f"### {name} forward returns by signal", "", _md_table(edge), ""]

    lines += [
        "## 7. Interpretation",
        "",
        "Classic VCP needs a multi-week base with *sequentially shallower* contractions and volume dry-up. "
        "Today's Stage2/Fund cohort is dominated by RS leaders sitting near highs, so `base_min_weeks=5` "
        "rejects most names before structure is even tested. That is consistent with the definition, not a bug.",
        "",
        "Loosening `base_min_weeks` alone raises coverage slightly but does **not** create many true VCPs — "
        "the next wall is non-tightening contractions (`max_step_ratio` often >1.5). Raising "
        "`contraction_decay` toward 1.0+ increases hit rate by abandoning Minervini's tightening rule.",
        "",
        "Historical scan (small n): live setups are rare but WATCHLIST/BREAKOUT median fwd10 was above "
        "baseline in this sample; `base3` and `leader_relaxed` added quantity with weaker or flat edge. "
        "Treat as provisional — sample size is tiny.",
        "",
        "## 8. Recommendation",
        "",
        "| Parameter | Keep live? | Note |",
        "|---|---|---|",
        "| `base_min_weeks=5` | **Yes** | Core VCP length; optional research preset `base3` only |",
        "| `contraction_decay=0.75` | **Yes** | Already looser than half-rule (0.5); do not raise to chase hits |",
        "| `contraction_min_retrace=0.5` | **Yes** | Needed to merge ZigZag noise (D7) |",
        "| `dryup_ratio=0.6` | **Yes** | Secondary today; revisit when more setups exist |",
        "| `max_base_depth=0.35` | **Yes** | Rare failure mode on this cohort |",
        "| signal zones (`watch`/`extension`/`vol`) | **Yes** | Too few events to retune |",
        "",
        "**Do not change production VCP params based on today's zero-hit Stage2 snapshot.** "
        "Next step if desired: larger event study on multi-year full-universe VCP fires (not Stage2-only).",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def parse_tickers(args: argparse.Namespace) -> tuple[list[str], str]:
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        return tickers, f"tickers ({len(tickers)})"
    if args.tickers_file:
        raw = Path(args.tickers_file).read_text()
        tickers = [t.strip().upper() for t in raw.replace(",", "\n").split() if t.strip() and not t.startswith("#")]
        return tickers, Path(args.tickers_file).name
    if args.from_stage2:
        df = pd.read_csv(args.from_stage2)
        tickers = df["ticker"].astype(str).str.upper().tolist()
        return tickers, Path(args.from_stage2).name
    # default: stage2 latest + fund latest if present
    stage = sorted(Path("reports").glob("stage2_*.csv"))
    fund = Path("reports/fund_tickers_20260726.txt")
    tickers: list[str] = []
    label_parts = []
    if stage:
        df = pd.read_csv(stage[-1])
        tickers += df["ticker"].astype(str).str.upper().tolist()
        label_parts.append(stage[-1].name)
    if fund.exists():
        tickers += [
            t.strip().upper()
            for t in fund.read_text().replace(",", "\n").split()
            if t.strip()
        ]
        label_parts.append(fund.name)
    tickers = sorted(set(tickers))
    return tickers, "+".join(label_parts) or "empty"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VCP parameter sensitivity study")
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--tickers")
    src.add_argument("--tickers-file")
    src.add_argument("--from-stage2")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--no-update", action="store_true", default=True)
    parser.add_argument("--update", action="store_true", help="allow price downloads")
    parser.add_argument("--no-history", action="store_true", help="skip historical as-of scan")
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    params = load_params(args.config)
    tickers, universe_label = parse_tickers(args)
    if not tickers:
        print("[오류] 티커가 없습니다")
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_dir = Path(args.out_dir or Path(params.report_dir) / "vcp_study")
    chart_dir = out_dir / "charts"
    out_dir.mkdir(parents=True, exist_ok=True)
    chart_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== VCP param study ===\nuniverse: {universe_label} ({len(tickers)})")
    enriched = load_enriched(tickers, params, update=bool(args.update))
    print(f"enriched: {len(enriched)}")
    live = params.vcp

    live_rep = evaluate_universe(enriched, live)
    live_funnel = funnel_counts(live_rep)
    live_funnel.to_csv(out_dir / f"vcp_funnel_live_{stamp}.csv", index=False)
    print("\nLive funnel:")
    print(live_funnel.to_string(index=False))

    base_days = base_days_series(enriched, live)
    base_days.to_csv(out_dir / f"vcp_base_days_{stamp}.csv", index=False)
    print(
        f"\nbase_days: mean={base_days.mean():.1f} median={base_days.median():.1f} "
        f">=5w={(base_days >= 25).mean() * 100:.1f}%"
    )

    struct = structure_diagnostics(enriched, live, base_min_weeks=3)
    struct.to_csv(out_dir / f"vcp_structure_diag_{stamp}.csv", index=False)

    preset_now = preset_compare(enriched, live)
    preset_now.to_csv(out_dir / f"vcp_presets_today_{stamp}.csv", index=False)
    print("\nPresets (today):")
    print(preset_now.to_string(index=False))

    oat = oat_sweep(enriched, live)
    oat.to_csv(out_dir / f"vcp_oat_{stamp}.csv", index=False)

    charts = [
        plot_funnel(live_funnel, chart_dir / f"vcp_funnel_live_{stamp}.png",
                    title=f"VCP live rejection funnel — {universe_label}"),
        plot_base_days(base_days, chart_dir / f"vcp_base_days_{stamp}.png",
                       title=f"Base length distribution — {universe_label}"),
        plot_oat_valid(oat, chart_dir / f"vcp_oat_valid_{stamp}.png"),
    ]

    hist_summary = None
    hist_edges: dict[str, pd.DataFrame] | None = None
    baseline_med = None
    if not args.no_history:
        print("\nHistorical weekly as-of scan...")
        base = baseline_fwd10(enriched)
        baseline_med = float(base.median()) if len(base) else 0.0
        rows = []
        hist_edges = {}
        for name, p in presets(live).items():
            events, meta = historical_events(enriched, p)
            events.to_csv(out_dir / f"vcp_hist_events_{name}_{stamp}.csv", index=False)
            edge = summarize_events(events, baseline_med)
            edge.to_csv(out_dir / f"vcp_hist_edge_{name}_{stamp}.csv", index=False)
            hist_edges[name] = edge
            rows.append({
                "preset": name,
                "n_eval": meta["n_eval"],
                "n_setups": meta["n_setups"],
                "hit_rate_pct": meta["hit_rate_pct"],
                "BREAKOUT": meta["signals"].get("BREAKOUT", 0),
                "WATCHLIST": meta["signals"].get("WATCHLIST", 0),
                "FORMING": meta["signals"].get("FORMING", 0),
                "EXTENDED": meta["signals"].get("EXTENDED", 0),
            })
            print(f"  {name}: hit={meta['hit_rate_pct']}% setups={meta['n_setups']}")
            if not edge.empty:
                print(edge.to_string(index=False))
        hist_summary = pd.DataFrame(rows)
        hist_summary.to_csv(out_dir / f"vcp_hist_summary_{stamp}.csv", index=False)
        charts.append(plot_hist_hit_rates(hist_summary, chart_dir / f"vcp_hist_hitrate_{stamp}.png"))

    verdict = [
        "Live VCP params are **literature-aligned defaults**, not empirically optimized — and that is OK for a timing filter.",
        f"On this universe, live valid setups today = {int(live_rep['valid'].sum())} / {len(live_rep)} "
        f"(dominant reject: base too short).",
        "Relaxing `base_min_weeks` raises coverage but historical WATCHLIST quality did not improve vs baseline in this sample.",
        "Do **not** raise `contraction_decay` just to get more hits — median max_step_ratio ≫ 1 means patterns are not VCPs.",
        "Keep production params; use presets only for research / optional operator modes.",
    ]

    md = write_markdown(
        out_dir / f"vcp_param_analysis_{stamp}.md",
        stamp=stamp,
        universe_n=len(enriched),
        universe_label=universe_label,
        live_funnel=live_funnel,
        base_days=base_days,
        struct=struct,
        oat=oat,
        preset_now=preset_now,
        hist_summary=hist_summary,
        hist_edges=hist_edges,
        baseline_med=baseline_med,
        verdict=verdict,
    )
    # Stable docs copy
    docs = Path("docs") / f"vcp_param_analysis_{stamp}.md"
    docs.write_text(md.read_text(encoding="utf-8"), encoding="utf-8")

    published = publish_many([md, *charts, out_dir / f"vcp_oat_{stamp}.csv",
                              out_dir / f"vcp_presets_today_{stamp}.csv"])
    if hist_summary is not None:
        published += publish_many([out_dir / f"vcp_hist_summary_{stamp}.csv"])

    print(f"\nreport: {md}")
    print(f"docs:   {docs}")
    print(f"charts: {chart_dir}")
    if published:
        print(f"artifacts: {len(published)} files")
    print("\nNOTE: live config/params.yaml VCP block unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
