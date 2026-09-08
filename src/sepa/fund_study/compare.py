"""Compare fund-study weight proposals vs live model (v2 / v2.1)."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd

from sepa.artifacts import publish_many
from sepa.fundamental_score import (
    DEFAULT_QUALITY,
    DEFAULT_WEIGHTS,
    FundamentalWeights,
    QualityParams,
    score_ticker,
)

logger = logging.getLogger(__name__)

# Live production mapping (factor study name → weight attribute)
LIVE_FACTOR_MAP = {
    "eps_surprise": ("eps_surprise", "S"),
    "eps_dyoy": ("eps_dyoy", "B"),
    "sales_dyoy": ("sales_dyoy", "D"),
    "opm_d": ("opm_delta", "E"),
    "npm_d": ("opm_delta", "E(npm)"),  # only if study chose npm over opm
}

LIVE_WEIGHTS_V2 = {
    "eps_surprise": 47.0,
    "eps_dyoy": 14.0,
    "sales_dyoy": 14.0,
    "opm_d": 25.0,
}


def _round_weights(weights: dict[str, float], total: float = 100.0) -> dict[str, float]:
    if not weights:
        return {}
    raw = {k: max(0.0, float(v)) for k, v in weights.items()}
    s = sum(raw.values())
    if s <= 0:
        return {k: 0.0 for k in raw}
    scaled = {k: v / s * total for k, v in raw.items()}
    # integer-ish display rounding that still sums ~100
    ints = {k: int(round(v)) for k, v in scaled.items()}
    drift = int(total) - sum(ints.values())
    if drift != 0:
        # adjust largest bucket
        k_max = max(ints, key=lambda k: ints[k])
        ints[k_max] += drift
    return {k: float(ints[k]) for k in scaled}


def weights_from_proposal(proposal: pd.DataFrame) -> dict[str, float]:
    """Map study proposal rows to live factor keys (prefer opm_d over npm_d)."""
    if proposal is None or proposal.empty:
        return {}
    work = proposal.copy()
    out: dict[str, float] = {}
    for _, row in work.iterrows():
        f = str(row["factor"])
        w = float(row.get("weight", 0.0) or 0.0)
        if w <= 0:
            continue
        if f == "npm_d" and "opm_d" in set(work["factor"].astype(str)):
            # if both somehow present, keep higher weight later
            pass
        out[f] = w
    # If study picked npm_d instead of opm_d, alias to opm_d for live scorer
    if "opm_d" not in out and "npm_d" in out:
        out["opm_d"] = out.pop("npm_d")
    elif "opm_d" in out and "npm_d" in out:
        out["opm_d"] = out["opm_d"] + out.pop("npm_d")
    # Keep only live-scored factors
    keep = {k: out[k] for k in ("eps_surprise", "eps_dyoy", "sales_dyoy", "opm_d") if k in out}
    return _round_weights(keep)


def build_weight_compare_table(
    proposal: pd.DataFrame,
    *,
    baseline: dict[str, float] | None = None,
    prior_proposal: pd.DataFrame | None = None,
) -> pd.DataFrame:
    baseline = baseline or LIVE_WEIGHTS_V2
    proposed = weights_from_proposal(proposal)
    prior = weights_from_proposal(prior_proposal) if prior_proposal is not None else {}

    factors = sorted(set(baseline) | set(proposed) | set(prior))
    rows = []
    for f in factors:
        label = LIVE_FACTOR_MAP.get(f, (f, f))[1]
        rows.append(
            {
                "factor": f,
                "label": label,
                "weight_live_v2": baseline.get(f, 0.0),
                "weight_study_prior": prior.get(f, np.nan),
                "weight_study_new": proposed.get(f, 0.0),
                "delta_vs_live": proposed.get(f, 0.0) - baseline.get(f, 0.0),
                "delta_vs_prior_study": (
                    proposed.get(f, 0.0) - prior[f] if f in prior else np.nan
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("weight_study_new", ascending=False).reset_index(drop=True)


def plot_weight_model_compare(table: pd.DataFrame, out_path: Path, *, stamp: str) -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    if table.empty:
        ax.text(0.5, 0.5, "no data", ha="center")
        ax.axis("off")
    else:
        x = np.arange(len(table))
        w = 0.28
        ax.bar(x - w, table["weight_live_v2"], width=w, label="Live v2", color="#7f8c8d")
        if table["weight_study_prior"].notna().any():
            ax.bar(x, table["weight_study_prior"].fillna(0), width=w, label="Study 2026-07-19", color="#95a5a6")
            ax.bar(x + w, table["weight_study_new"], width=w, label=f"Study {stamp}", color="#2980b9")
        else:
            ax.bar(x + w / 2, table["weight_study_new"], width=w, label=f"Study {stamp}", color="#2980b9")
        ax.set_xticks(x)
        ax.set_xticklabels(table["label"].tolist())
        ax.set_ylabel("weight (sum≈100)")
        ax.set_title(f"Fund weights: live v2 vs study — {stamp}")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


def rescore_universe_models(
    tickers_meta: pd.DataFrame,
    *,
    cache_dir: str | Path,
    proposed_weights: dict[str, float],
) -> pd.DataFrame:
    """Score each ticker under live-v2 (q off), v2.1 (q on), and proposed weights (q on)."""
    from sepa.data import fundamentals as fund_data

    fund_dir = fund_data.cache_dir(cache_dir)
    cik = fund_data.load_cik_map(fund_dir)
    w_live = DEFAULT_WEIGHTS
    w_prop = FundamentalWeights(
        eps_surprise=proposed_weights.get("eps_surprise", 0.0),
        eps_dyoy=proposed_weights.get("eps_dyoy", 0.0),
        sales_dyoy=proposed_weights.get("sales_dyoy", 0.0),
        opm_delta=proposed_weights.get("opm_d", 0.0),
    )
    q_on = DEFAULT_QUALITY
    q_off = QualityParams(enabled=False)

    rows = []
    tickers = tickers_meta["ticker"].astype(str).str.upper().tolist()
    for i, t in enumerate(tickers, 1):
        if i == 1 or i % 25 == 0 or i == len(tickers):
            print(f"  rescore models {i}/{len(tickers)} {t}")
        qdf, roe, src = fund_data.load_quarterly(t, fund_dir, cik, refresh=False, backfill_opm=True)
        # surprise from latest fund CSV if present
        sur = None
        if "eps_surprise_pct" in tickers_meta.columns:
            hit = tickers_meta[tickers_meta["ticker"].astype(str).str.upper() == t]
            if not hit.empty and pd.notna(hit.iloc[0].get("eps_surprise_pct")):
                sur = float(hit.iloc[0]["eps_surprise_pct"]) / 100.0
        if sur is None:
            from sepa.fundamental import fetch_latest_eps_surprise

            sur = fetch_latest_eps_surprise(t)

        live = score_ticker(t, qdf, roe, source=src, weights=w_live, eps_surprise=sur, quality=q_off)
        v21 = score_ticker(t, qdf, roe, source=src, weights=w_live, eps_surprise=sur, quality=q_on)
        prop = score_ticker(t, qdf, roe, source=src, weights=w_prop, eps_surprise=sur, quality=q_on)
        meta = tickers_meta[tickers_meta["ticker"].astype(str).str.upper() == t]
        name = meta.iloc[0].get("name", "") if not meta.empty else ""
        rs = meta.iloc[0].get("rs_rank") if not meta.empty else None
        rows.append(
            {
                "ticker": t,
                "name": name,
                "rs_rank": rs,
                "fund_live_v2": round(live.fund_score, 1),
                "fund_v21_quality": round(v21.fund_score, 1),
                "fund_proposed": round(prop.fund_score, 1),
                "delta_v21_vs_live": round(v21.fund_score - live.fund_score, 1),
                "delta_proposed_vs_live": round(prop.fund_score - live.fund_score, 1),
                "delta_proposed_vs_v21": round(prop.fund_score - v21.fund_score, 1),
                "margin_source": v21.margin_source,
                "e_quality": v21.e_quality,
                "b_quality": v21.b_quality,
                "d_quality": v21.d_quality,
            }
        )
    return pd.DataFrame(rows)


def rank_overlap(a: pd.Series, b: pd.Series, top_n: int = 20) -> dict:
    ta = set(a.nlargest(top_n).index if a.index.dtype != object else a.sort_values(ascending=False).head(top_n).index)
    # expect ticker as values when passed as series of scores indexed by ticker
    if "ticker" not in str(type(a)):
        pass
    return {}


def topn_retention(df: pd.DataFrame, col_a: str, col_b: str, top_n: int = 20) -> float:
    a = set(df.nlargest(top_n, col_a)["ticker"])
    b = set(df.nlargest(top_n, col_b)["ticker"])
    return len(a & b) / top_n if top_n else float("nan")


def spearman_scores(df: pd.DataFrame, col_a: str, col_b: str) -> float:
    a = pd.to_numeric(df[col_a], errors="coerce")
    b = pd.to_numeric(df[col_b], errors="coerce")
    mask = a.notna() & b.notna()
    if mask.sum() < 5:
        return float("nan")
    return float(a[mask].rank().corr(b[mask].rank()))


def write_comparison_markdown(
    path: Path,
    *,
    stamp: str,
    n_events: int,
    n_tickers: int,
    weight_table: pd.DataFrame,
    score_summary: dict,
    corr_new: pd.DataFrame | None = None,
    corr_prior: pd.DataFrame | None = None,
) -> Path:
    lines = [
        f"# Fund model comparison — study {stamp}",
        "",
        f"- Events: **{n_events}** · Tickers in live rescore: **{n_tickers}**",
        "- Live model: **v2 weights** S47 / E25 / D14 / B14 (quality off)",
        "- v2.1: same weights + quality gates (NPM×0.6, accel depth)",
        "- Proposed: new study weights + v2.1 quality",
        "",
        "## 1. Weight table",
        "",
        "| Factor | Live v2 | Prior study | New study | Δ vs live |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, r in weight_table.iterrows():
        prior = "—" if pd.isna(r["weight_study_prior"]) else f"{r['weight_study_prior']:.0f}"
        lines.append(
            f"| {r['label']} (`{r['factor']}`) | {r['weight_live_v2']:.0f} | {prior} | "
            f"{r['weight_study_new']:.0f} | {r['delta_vs_live']:+.0f} |"
        )

    lines += ["", "## 2. Live universe score summary", ""]
    for k, v in score_summary.items():
        lines.append(f"- **{k}**: {v}")

    if corr_new is not None and not corr_new.empty:
        lines += ["", "## 3. New study raw Spearman (factor vs mkt-adj ret)", "", "```"]
        lines.append(corr_new.sort_values("spearman", ascending=False).to_string(index=False))
        lines.append("```")
    if corr_prior is not None and not corr_prior.empty:
        lines += ["", "### Prior study (2026-07-19) Spearman", "", "```"]
        lines.append(corr_prior.sort_values("spearman", ascending=False).to_string(index=False))
        lines.append("```")

    lines += [
        "",
        "## 4. Recommendation",
        "",
        "- If new weights ≈ live (±5pt per factor): **keep v2 weights**, ship v2.1 quality only.",
        "- If one factor flips sign or moves ≥10pt: review yearly stability before adopting.",
        "- Do **not** apply proposed weights to production without explicit approval.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


def run_model_comparison(
    *,
    stamp: str,
    proposal_path: Path,
    report_dir: Path,
    cache_dir: str | Path,
    live_fund_csv: Path,
    prior_proposal_path: Path | None = None,
    prior_corr_path: Path | None = None,
    new_corr_path: Path | None = None,
    n_events: int = 0,
) -> dict:
    proposal = pd.read_csv(proposal_path)
    prior = pd.read_csv(prior_proposal_path) if prior_proposal_path and prior_proposal_path.exists() else None
    weight_table = build_weight_compare_table(proposal, prior_proposal=prior)
    proposed = weights_from_proposal(proposal)

    live = pd.read_csv(live_fund_csv)
    scored = rescore_universe_models(live, cache_dir=cache_dir, proposed_weights=proposed)

    summary = {
        "mean live_v2": f"{scored['fund_live_v2'].mean():.1f}",
        "mean v2.1_quality": f"{scored['fund_v21_quality'].mean():.1f}",
        "mean proposed": f"{scored['fund_proposed'].mean():.1f}",
        "Spearman(live, v2.1)": f"{spearman_scores(scored, 'fund_live_v2', 'fund_v21_quality'):.3f}",
        "Spearman(live, proposed)": f"{spearman_scores(scored, 'fund_live_v2', 'fund_proposed'):.3f}",
        "Spearman(v2.1, proposed)": f"{spearman_scores(scored, 'fund_v21_quality', 'fund_proposed'):.3f}",
        "Top20 retention live↔v2.1": f"{topn_retention(scored, 'fund_live_v2', 'fund_v21_quality', 20):.0%}",
        "Top20 retention live↔proposed": f"{topn_retention(scored, 'fund_live_v2', 'fund_proposed', 20):.0%}",
        "margin_source=opm %": f"{(scored['margin_source']=='opm').mean():.0%}",
    }

    out_dir = Path(report_dir) / "fund_study"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    paths["weights_compare"] = out_dir / f"model_weight_compare_{stamp}.csv"
    weight_table.to_csv(paths["weights_compare"], index=False)
    paths["scores_compare"] = out_dir / f"model_score_compare_{stamp}.csv"
    scored.to_csv(paths["scores_compare"], index=False)
    paths["chart_weights"] = plot_weight_model_compare(
        weight_table, out_dir / "charts" / f"model_weight_compare_{stamp}.png", stamp=stamp
    )

    corr_new = pd.read_csv(new_corr_path) if new_corr_path and Path(new_corr_path).exists() else None
    corr_prior = pd.read_csv(prior_corr_path) if prior_corr_path and Path(prior_corr_path).exists() else None
    paths["report"] = write_comparison_markdown(
        out_dir / f"model_comparison_{stamp}.md",
        stamp=stamp,
        n_events=n_events,
        n_tickers=len(scored),
        weight_table=weight_table,
        score_summary=summary,
        corr_new=corr_new,
        corr_prior=corr_prior,
    )
    # also copy a stable docs-facing summary
    docs_path = Path("docs") / f"fund_model_comparison_{stamp}.md"
    docs_path.write_text(Path(paths["report"]).read_text())
    paths["docs_report"] = docs_path

    publish_many([p for p in paths.values() if Path(p).suffix in {".png", ".csv", ".md"}])
    return {
        "ok": True,
        "stamp": stamp,
        "proposed_weights": proposed,
        "summary": summary,
        "paths": paths,
        "weight_table": weight_table,
        "scored": scored,
    }
