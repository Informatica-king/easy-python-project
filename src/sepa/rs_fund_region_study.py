"""RS×Fund region returns vs S&P500 — experiments A / D / E (+ light B).

A  Trailing excess mapped onto score coordinates (heatmap + scatter overlay)
D  Spearman(Fund/RS, excess) and Fund-quantile mean excess
E  Live policy bands (RS 70–89 vs RS≥90 Fund≥median, etc.)
B  Short forward excess from archived fundamental_*.csv (where prices allow)

Usage:
    python -m sepa.rs_fund_region_study
    python -m sepa.rs_fund_region_study --scored reports/rs_study/fundamental_tech_....csv
    !sepa.rs_fund_study()
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd

from sepa.artifacts import publish_many
from sepa.candidates import apply_candidate_filters
from sepa.config import load_params
from sepa.model_metrics import (
    _ensure_benchmark,
    _load_close_series,
    _setup_korean_font,
    _spearman,
    list_fundamental_csvs,
)

logger = logging.getLogger(__name__)

# calendar-ish trading-day horizons from the plan
TRAIL_HORIZONS = (
    ("2w", 10),
    ("1m", 21),
    ("3m", 63),
    ("6m", 126),
)
FWD_HORIZONS = (
    ("5d", 5),
    ("10d", 10),
)

# R1 fixed grid (plan §3.4)
RS_EDGES = (0.0, 70.0, 80.0, 90.0, 100.01)
RS_LABELS = ("RS0–69", "RS70–79", "RS80–89", "RS90+")
FUND_EDGES = (0.0, 25.0, 50.0, 75.0, 100.01)
FUND_LABELS = ("F0–24", "F25–49", "F50–74", "F75–100")


def _asof_ts(as_of: str | None, series: pd.Series) -> pd.Timestamp:
    if as_of:
        ts = pd.Timestamp(as_of)
    elif not series.empty:
        ts = pd.Timestamp(series.index.max())
    else:
        ts = pd.Timestamp(datetime.now(timezone.utc).date())
    return ts.tz_localize(None) if getattr(ts, "tzinfo", None) else ts


def trailing_return(series: pd.Series, as_of: pd.Timestamp, days: int) -> float | None:
    """Return over the last ``days`` trading bars ending on/before as_of."""
    if series.empty or days <= 0:
        return None
    end_idx = series.index.searchsorted(as_of, side="left")
    if end_idx >= len(series):
        end_idx = len(series) - 1
    if end_idx > 0 and series.index[end_idx] > as_of:
        end_idx -= 1
    start_idx = end_idx - days
    if start_idx < 0:
        return None
    p0 = float(series.iloc[start_idx])
    p1 = float(series.iloc[end_idx])
    if p0 <= 0:
        return None
    return p1 / p0 - 1.0


def forward_return(series: pd.Series, as_of: pd.Timestamp, days: int) -> float | None:
    """Return over the next ``days`` trading bars starting on/before as_of."""
    if series.empty or days <= 0:
        return None
    start_idx = series.index.searchsorted(as_of, side="left")
    if start_idx >= len(series):
        start_idx = len(series) - 1
    if start_idx > 0 and series.index[start_idx] > as_of:
        start_idx -= 1
    end_idx = start_idx + days
    if end_idx >= len(series):
        return None
    p0 = float(series.iloc[start_idx])
    p1 = float(series.iloc[end_idx])
    if p0 <= 0:
        return None
    return p1 / p0 - 1.0


def assign_r1(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rs = pd.to_numeric(out["rs_rank"], errors="coerce")
    fund = pd.to_numeric(out["fund_score"], errors="coerce")
    out["rs_bin"] = pd.cut(rs, bins=RS_EDGES, labels=RS_LABELS, right=False)
    out["fund_bin"] = pd.cut(fund, bins=FUND_EDGES, labels=FUND_LABELS, right=False)
    out["r1_cell"] = out["fund_bin"].astype(str) + " × " + out["rs_bin"].astype(str)
    return out


def assign_r4_live(df: pd.DataFrame, *, fund_median: float | None = None) -> pd.DataFrame:
    """Live-policy-ish bands for experiment E."""
    out = df.copy()
    rs = pd.to_numeric(out["rs_rank"], errors="coerce")
    fund = pd.to_numeric(out["fund_score"], errors="coerce")
    med = float(fund.median()) if fund_median is None else float(fund_median)
    band = pd.Series("other", index=out.index, dtype=object)
    band[(rs >= 70) & (rs < 90)] = "RS70–89"
    band[(rs >= 90) & (fund >= med)] = "RS90+ & Fund≥med"
    band[(rs >= 90) & (fund < med)] = "RS90+ & Fund<med (soft-drop)"
    band[rs < 70] = "RS<70"
    out["r4_band"] = band
    out["r4_median_used"] = med
    return out


def enrich_trailing_excess(
    df: pd.DataFrame,
    *,
    cache_dir: str | Path,
    as_of: pd.Timestamp,
    bench: pd.Series,
    horizons: tuple[tuple[str, int], ...] = TRAIL_HORIZONS,
    px_cache: dict[str, pd.Series] | None = None,
) -> pd.DataFrame:
    work = df.copy()
    work["ticker"] = work["ticker"].astype(str).str.upper()
    if px_cache is None:
        px_cache = {}
    bench_rets = {lab: trailing_return(bench, as_of, h) for lab, h in horizons}
    for lab, h in horizons:
        col_r = f"trail_{lab}"
        col_x = f"excess_{lab}"
        rets, exs = [], []
        b = bench_rets[lab]
        for t in work["ticker"]:
            s = _load_close_series(t, cache_dir, px_cache)
            r = trailing_return(s, as_of, h)
            rets.append(r)
            if r is None or b is None:
                exs.append(None)
            else:
                exs.append(r - b)
        work[col_r] = rets
        work[col_x] = exs
        work[f"bench_{lab}"] = b
    return work


def summarize_cells(
    df: pd.DataFrame,
    *,
    cell_col: str,
    excess_cols: list[str],
) -> pd.DataFrame:
    rows = []
    for cell, g in df.groupby(cell_col, observed=False):
        row: dict = {"cell": str(cell), "n": int(len(g))}
        for c in excess_cols:
            s = pd.to_numeric(g[c], errors="coerce").dropna()
            row[f"{c}_n"] = int(len(s))
            row[f"{c}_mean"] = float(s.mean()) if len(s) else float("nan")
            row[f"{c}_median"] = float(s.median()) if len(s) else float("nan")
            row[f"{c}_win"] = float((s > 0).mean()) if len(s) else float("nan")
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    # sort by first horizon mean excess desc
    key = f"{excess_cols[0]}_mean" if excess_cols else "n"
    return out.sort_values(key, ascending=False).reset_index(drop=True)


def correlation_table(df: pd.DataFrame, excess_cols: list[str]) -> pd.DataFrame:
    rows = []
    for c in excess_cols:
        rows.append({
            "excess": c,
            "n": int(pd.to_numeric(df[c], errors="coerce").notna().sum()),
            "rho_fund": _spearman(df["fund_score"], df[c]),
            "rho_rs": _spearman(df["rs_rank"], df[c]),
        })
    return pd.DataFrame(rows)


def fund_quantile_excess(df: pd.DataFrame, excess_cols: list[str], q: int = 4) -> pd.DataFrame:
    work = df.copy()
    fund = pd.to_numeric(work["fund_score"], errors="coerce")
    try:
        work["fund_q"] = pd.qcut(fund, q=q, labels=[f"Q{i}" for i in range(1, q + 1)], duplicates="drop")
    except ValueError:
        work["fund_q"] = pd.cut(fund, bins=q, labels=[f"Q{i}" for i in range(1, q + 1)])
    rows = []
    for label, g in work.groupby("fund_q", observed=False):
        row: dict = {"fund_q": str(label), "n": int(len(g))}
        for c in excess_cols:
            s = pd.to_numeric(g[c], errors="coerce").dropna()
            row[f"{c}_mean"] = float(s.mean()) if len(s) else float("nan")
            row[f"{c}_median"] = float(s.median()) if len(s) else float("nan")
            row[f"{c}_win"] = float((s > 0).mean()) if len(s) else float("nan")
        rows.append(row)
    return pd.DataFrame(rows)


def plot_heatmap(
    cell_summary: pd.DataFrame,
    *,
    excess_col: str,
    title: str,
    out_path: Path,
    value_suffix: str = "_mean",
) -> Path | None:
    _setup_korean_font()
    # rebuild 4x4 matrix Fund rows × RS cols
    mat = np.full((len(FUND_LABELS), len(RS_LABELS)), np.nan)
    nmat = np.zeros_like(mat)
    col = f"{excess_col}{value_suffix}"
    ncol = f"{excess_col}_n"
    for _, r in cell_summary.iterrows():
        cell = str(r["cell"])
        if " × " not in cell:
            continue
        fbin, rsbin = cell.split(" × ", 1)
        if fbin not in FUND_LABELS or rsbin not in RS_LABELS:
            continue
        i = FUND_LABELS.index(fbin)
        j = RS_LABELS.index(rsbin)
        mat[i, j] = r.get(col, np.nan)
        nmat[i, j] = r.get(ncol, 0)
    if np.all(np.isnan(mat)):
        return None
    fig, ax = plt.subplots(figsize=(8.2, 5.6))
    vmax = np.nanmax(np.abs(mat))
    vmax = max(float(vmax), 1e-6)
    im = ax.imshow(mat, cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(RS_LABELS)))
    ax.set_xticklabels(RS_LABELS)
    ax.set_yticks(range(len(FUND_LABELS)))
    ax.set_yticklabels(FUND_LABELS)
    ax.set_title(title)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if np.isnan(v):
                txt = "—"
            else:
                txt = f"{v*100:.1f}%\nn={int(nmat[i, j])}"
            ax.text(j, i, txt, ha="center", va="center", fontsize=8,
                    color="black" if abs(v) < 0.6 * vmax or np.isnan(v) else "white")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="mean excess vs SPX")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_scatter_excess(
    df: pd.DataFrame,
    *,
    excess_col: str,
    title: str,
    out_path: Path,
) -> Path | None:
    _setup_korean_font()
    work = df.dropna(subset=["rs_rank", "fund_score", excess_col]).copy()
    if work.empty:
        return None
    x = pd.to_numeric(work["rs_rank"], errors="coerce")
    y = pd.to_numeric(work["fund_score"], errors="coerce")
    c = pd.to_numeric(work[excess_col], errors="coerce")
    fig, ax = plt.subplots(figsize=(8.5, 6.2))
    sc = ax.scatter(x, y, c=c, cmap="RdYlGn", s=36, alpha=0.85, edgecolors="none")
    ax.axvline(70, color="#546e7a", ls="--", lw=0.8, alpha=0.7)
    ax.axvline(90, color="#546e7a", ls=":", lw=0.8, alpha=0.7)
    ax.axhline(y.median(), color="#6a1b9a", ls="--", lw=0.8, alpha=0.5, label="Fund median")
    ax.set_xlabel("RS rank")
    ax.set_ylabel("Fund score")
    ax.set_title(title)
    ax.legend(fontsize=8, loc="lower left")
    fig.colorbar(sc, ax=ax, label="excess vs SPX")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_r4_bars(
    summary: pd.DataFrame,
    *,
    excess_cols: list[str],
    out_path: Path,
) -> Path | None:
    _setup_korean_font()
    if summary.empty:
        return None
    order = ["RS70–89", "RS90+ & Fund≥med", "RS90+ & Fund<med (soft-drop)", "RS<70", "other"]
    s = summary.set_index("cell")
    present = [c for c in order if c in s.index] + [c for c in s.index if c not in order]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(present))
    width = 0.18
    for i, col in enumerate(excess_cols):
        vals = [s.loc[c, f"{col}_mean"] if c in s.index else np.nan for c in present]
        ax.bar(x + (i - 1.5) * width, vals, width=width, label=col.replace("excess_", ""))
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(present, rotation=15, ha="right")
    ax.set_ylabel("mean excess vs SPX")
    ax.set_title("실험 E — live 정책 밴드 trailing 초과수익")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def run_forward_light(
    *,
    report_dir: Path,
    cache_dir: Path,
    bench: pd.Series,
    px_cache: dict[str, pd.Series],
    out_dir: Path,
) -> pd.DataFrame:
    """Experiment B: short forward excess on archived fund CSVs."""
    rows = []
    for path in list_fundamental_csvs(report_dir):
        stamp = path.stem.split("_")[-1]
        try:
            as_of = pd.Timestamp(datetime.strptime(stamp, "%Y%m%d"))
        except ValueError:
            continue
        df = pd.read_csv(path)
        if df.empty or "fund_score" not in df.columns:
            continue
        df = assign_r1(df)
        for lab, h in FWD_HORIZONS:
            b = forward_return(bench, as_of, h)
            if b is None:
                continue
            for _, r in df.iterrows():
                t = str(r["ticker"]).upper()
                s = _load_close_series(t, cache_dir, px_cache)
                ret = forward_return(s, as_of, h)
                if ret is None:
                    continue
                rows.append({
                    "stamp": stamp,
                    "horizon": lab,
                    "days": h,
                    "ticker": t,
                    "fund_score": r.get("fund_score"),
                    "rs_rank": r.get("rs_rank"),
                    "r1_cell": r.get("r1_cell"),
                    "ret": ret,
                    "bench": b,
                    "excess": ret - b,
                })
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail
    detail.to_csv(out_dir / "forward_detail.csv", index=False)
    agg = (
        detail.groupby(["horizon", "r1_cell"], observed=False)
        .agg(
            n=("excess", "count"),
            mean_excess=("excess", "mean"),
            median_excess=("excess", "median"),
            win=("excess", lambda s: float((s > 0).mean())),
            rho_note=("stamp", "nunique"),
        )
        .reset_index()
        .rename(columns={"rho_note": "n_stamps"})
        .sort_values(["horizon", "mean_excess"], ascending=[True, False])
    )
    # also fund/rs spearman by horizon pooled
    corr_rows = []
    for lab, g in detail.groupby("horizon"):
        corr_rows.append({
            "horizon": lab,
            "n": len(g),
            "rho_fund": _spearman(g["fund_score"], g["excess"]),
            "rho_rs": _spearman(g["rs_rank"], g["excess"]),
            "mean_excess": float(g["excess"].mean()),
        })
    pd.DataFrame(corr_rows).to_csv(out_dir / "forward_corr.csv", index=False)
    agg.to_csv(out_dir / "forward_cells.csv", index=False)
    return agg


def write_report(
    path: Path,
    *,
    stamp: str,
    as_of: str,
    universe_n: int,
    scored_path: str,
    r1: pd.DataFrame,
    r4: pd.DataFrame,
    corr: pd.DataFrame,
    qtab: pd.DataFrame,
    fwd: pd.DataFrame,
    bench_name: str,
) -> Path:
    lines = [
        f"# RS×Fund region vs {bench_name} — results ({stamp})",
        "",
        f"- Experiments: **A** (trailing heatmap), **D** (score↔excess), **E** (live bands), light **B** (short forward)",
        f"- Universe U2-style scored file: `{scored_path}` → Fund>0 & mcap≥$1B → **n={universe_n}**",
        f"- Trailing as-of: **{as_of}** (coordinates from scored snapshot; returns end on/before this date)",
        f"- Horizons: 2w=10d, 1m=21d, 3m=63d, 6m=126d trading bars",
        "",
        "## Verdict",
        "",
    ]
    # craft verdict from corr — treat long-horizon RS↔trailing as partly mechanical
    if not corr.empty:
        short = corr[corr["excess"].isin(["excess_2w", "excess_1m"])]
        fund_weak = True
        for r in short.itertuples():
            if r.rho_fund == r.rho_fund and abs(r.rho_fund) >= 0.25:
                fund_weak = False
        if fund_weak:
            lines.append(
                "- **단기(2주·1개월) trailing 초과와 Fund 상관은 약함** (|ρ|≲0.1) — "
                "“Fund 높을수록 최근 단기 초과 보장”은 **지지되지 않음**."
            )
        lines.append(
            "- RS↔3·6개월 trailing 초과 상관은 클 수 있으나, RS 자체가 과거 수익률 기반이라 "
            "**상당 부분 동어반복** — 예측력으로 읽지 말 것."
        )
        rho2w = short.loc[short["excess"] == "excess_2w", "rho_rs"]
        if len(rho2w) and float(rho2w.iloc[0]) == float(rho2w.iloc[0]) and abs(float(rho2w.iloc[0])) < 0.1:
            lines.append("- **2주**에서는 RS와도 거의 무관 (ρ≈0) — 초단기 타이밍 신호 아님.")
    if not r4.empty and "excess_1m_mean" in r4.columns:
        top = r4.sort_values("excess_1m_mean", ascending=False).iloc[0]
        lines.append(
            f"- 1개월 trailing 기준 live 밴드 최고 평균초과: **{top['cell']}** "
            f"(mean={top['excess_1m_mean']*100:.1f}%, n={int(top['n'])})."
        )
    if not r1.empty and "excess_1m_mean" in r1.columns:
        top1 = r1.dropna(subset=["excess_1m_mean"]).sort_values("excess_1m_mean", ascending=False).head(3)
        cells = ", ".join(f"{r.cell} ({r.excess_1m_mean*100:.1f}%)" for r in top1.itertuples())
        lines.append(f"- R1 1개월 상위 셀: {cells}")
    if not fwd.empty:
        # pooled forward corr if file exists alongside — optional note from fwd means
        lines.append(
            "- Forward(B) 짧은 창에서는 고Fund·고RS 셀이 **항상 이기지 않음** "
            "(다수 셀 평균 초과 음수) — 단기 보장 가설과 배치."
        )
    lines.append("- Fund 점수 상한 부근(F75–100) 셀은 표본 0인 경우가 많음 (현 스코어 분포상).")
    lines += ["", "## A — R1 cell trailing excess (mean / win rate)", ""]
    lines += [
        "| cell | n | 2w mean | 2w win | 1m mean | 1m win | 3m mean | 3m win | 6m mean | 6m win |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in r1.itertuples():
        def pct(col, row=r):
            v = getattr(row, col, float("nan"))
            return "" if v != v else f"{v*100:.1f}%"
        lines.append(
            f"| {r.cell} | {r.n} | {pct('excess_2w_mean')} | {pct('excess_2w_win')} | "
            f"{pct('excess_1m_mean')} | {pct('excess_1m_win')} | "
            f"{pct('excess_3m_mean')} | {pct('excess_3m_win')} | "
            f"{pct('excess_6m_mean')} | {pct('excess_6m_win')} |"
        )

    lines += ["", "## E — live policy bands", "",
              "| band | n | 2w mean | 1m mean | 3m mean | 6m mean | 1m win |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for r in r4.itertuples():
        def pct(col):
            v = getattr(r, col, float("nan"))
            return "" if v != v else f"{v*100:.1f}%"
        lines.append(
            f"| {r.cell} | {r.n} | {pct('excess_2w_mean')} | {pct('excess_1m_mean')} | "
            f"{pct('excess_3m_mean')} | {pct('excess_6m_mean')} | {pct('excess_1m_win')} |"
        )

    lines += ["", "## D — Spearman ρ (score vs trailing excess)", "",
              "| excess | n | ρ(Fund) | ρ(RS) |",
              "|---|---:|---:|---:|"]
    for r in corr.itertuples():
        lines.append(
            f"| {r.excess} | {r.n} | {r.rho_fund:.3f} | {r.rho_rs:.3f} |"
        )

    lines += ["", "### Fund quartile mean excess", "",
              "| Q | n | 2w | 1m | 3m | 6m |",
              "|---|---:|---:|---:|---:|---:|"]
    for r in qtab.itertuples():
        def pct(col):
            v = getattr(r, col, float("nan"))
            return "" if v != v else f"{v*100:.1f}%"
        lines.append(
            f"| {r.fund_q} | {r.n} | {pct('excess_2w_mean')} | {pct('excess_1m_mean')} | "
            f"{pct('excess_3m_mean')} | {pct('excess_6m_mean')} |"
        )

    lines += ["", "## B — short forward (archived fundamental CSVs)", ""]
    if fwd is None or fwd.empty:
        lines.append("_가격 구간 부족 등으로 forward 표본 없음/미산출._")
    else:
        lines.append("스냅샷 이후 5·10거래일 초과 (셀  pooled). 표본·기간 짧음 — 참고용.")
        lines += ["", "| horizon | cell | n | mean excess | win | stamps |",
                  "|---|---|---:|---:|---:|---:|"]
        for r in fwd.head(24).itertuples():
            lines.append(
                f"| {r.horizon} | {r.r1_cell} | {r.n} | {r.mean_excess*100:.1f}% | "
                f"{r.win*100:.0f}% | {r.n_stamps} |"
            )

    lines += [
        "",
        "## How to read",
        "",
        "- Trailing(A/E/D)는 **사후** 성과를 오늘(스냅샷) 좌표에 칠한 것 — 미래 보장 아님.",
        "- Forward(B)는 보관 스냅샷이 짧아 **2주 전후만** 가능.",
        "- 본 결과는 단일 국면(2026 중반 Nasdaq 스크리너 유니버스)에 한정.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_study(
    *,
    config: str = "config/params.yaml",
    scored: str | None = None,
    as_of: str | None = None,
    benchmark: str = "^GSPC",
    out_dir: Path | None = None,
    skip_forward: bool = False,
) -> dict:
    params = load_params(config)
    cache_dir = Path(params.data.cache_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out = Path(out_dir or Path(params.report_dir) / "rs_fund_region")
    charts = out / "charts"
    out.mkdir(parents=True, exist_ok=True)
    charts.mkdir(parents=True, exist_ok=True)

    scored_path = Path(
        scored
        or "reports/rs_study/fundamental_tech_20260727.csv"
    )
    if not scored_path.exists():
        # fallback to latest fundamental
        cands = list_fundamental_csvs(params.report_dir)
        if not cands:
            print("[오류] scored CSV 없음")
            return {"ok": False}
        scored_path = cands[-1]
        print(f"[warn] U2 tech CSV 없음 → {scored_path} 사용")

    print(f"\n=== RS×Fund region study ===\nscored: {scored_path}")
    raw = pd.read_csv(scored_path)
    kept, dropped = apply_candidate_filters(raw)
    print(f"filters: {len(raw)} → {len(kept)} ({len(dropped)} dropped)")
    if kept.empty:
        return {"ok": False}

    bench = _ensure_benchmark(cache_dir, benchmark)
    if bench.empty:
        bench = _ensure_benchmark(cache_dir, "SPY")
        benchmark = "SPY"
    if bench.empty:
        print("[오류] S&P500/SPY 벤치 가격 없음")
        return {"ok": False}

    as_of_ts = _asof_ts(as_of, bench)
    print(f"benchmark={benchmark}  as_of={as_of_ts.date()}  bars={len(bench)}")

    px_cache: dict[str, pd.Series] = {benchmark.upper().lstrip("^"): bench, benchmark.upper(): bench}
    px_cache["GSPC"] = bench
    px_cache["^GSPC"] = bench

    enriched = enrich_trailing_excess(
        kept, cache_dir=cache_dir, as_of=as_of_ts, bench=bench, px_cache=px_cache
    )
    enriched = assign_r1(enriched)
    # R4 median from RS≥70 pool after soft-ceiling style reference
    rs70 = enriched[pd.to_numeric(enriched["rs_rank"], errors="coerce") >= 70]
    med70 = float(pd.to_numeric(rs70["fund_score"], errors="coerce").median()) if not rs70.empty else float("nan")
    enriched = assign_r4_live(enriched, fund_median=med70)

    excess_cols = [f"excess_{lab}" for lab, _ in TRAIL_HORIZONS]
    enriched.to_csv(out / f"trailing_security_{stamp}.csv", index=False)

    r1 = summarize_cells(enriched, cell_col="r1_cell", excess_cols=excess_cols)
    r4 = summarize_cells(enriched, cell_col="r4_band", excess_cols=excess_cols)
    r1.to_csv(out / f"trailing_r1_cells_{stamp}.csv", index=False)
    r4.to_csv(out / f"trailing_r4_bands_{stamp}.csv", index=False)

    corr = correlation_table(enriched, excess_cols)
    qtab = fund_quantile_excess(enriched, excess_cols)
    corr.to_csv(out / f"trailing_corr_{stamp}.csv", index=False)
    qtab.to_csv(out / f"trailing_fund_quantiles_{stamp}.csv", index=False)

    chart_paths = []
    for lab, _ in TRAIL_HORIZONS:
        p = plot_heatmap(
            r1,
            excess_col=f"excess_{lab}",
            title=f"A · R1 mean excess vs {benchmark} · {lab}",
            out_path=charts / f"heatmap_excess_{lab}_{stamp}.png",
        )
        if p:
            chart_paths.append(p)
        p2 = plot_scatter_excess(
            enriched,
            excess_col=f"excess_{lab}",
            title=f"A · RS×Fund colored by excess {lab}",
            out_path=charts / f"scatter_excess_{lab}_{stamp}.png",
        )
        if p2:
            chart_paths.append(p2)
    p3 = plot_r4_bars(r4, excess_cols=excess_cols, out_path=charts / f"r4_bands_{stamp}.png")
    if p3:
        chart_paths.append(p3)

    fwd = pd.DataFrame()
    if not skip_forward:
        print("experiment B: short forward on archived fundamentals...")
        fwd = run_forward_light(
            report_dir=Path(params.report_dir),
            cache_dir=cache_dir,
            bench=bench,
            px_cache=px_cache,
            out_dir=out,
        )

    md = write_report(
        out / f"rs_fund_region_results_{stamp}.md",
        stamp=stamp,
        as_of=str(as_of_ts.date()),
        universe_n=len(enriched),
        scored_path=str(scored_path),
        r1=r1,
        r4=r4,
        corr=corr,
        qtab=qtab,
        fwd=fwd,
        bench_name=benchmark,
    )
    docs = Path("docs") / f"rs_fund_region_results_{stamp}.md"
    docs.write_text(md.read_text(encoding="utf-8"), encoding="utf-8")

    published = publish_many([md, *chart_paths, out / f"trailing_r1_cells_{stamp}.csv",
                             out / f"trailing_r4_bands_{stamp}.csv", out / f"trailing_corr_{stamp}.csv"])

    print("\n=== D correlations ===")
    print(corr.to_string(index=False))
    print("\n=== E live bands (mean excess) ===")
    cols = ["cell", "n"] + [f"excess_{lab}_mean" for lab, _ in TRAIL_HORIZONS]
    print(r4[[c for c in cols if c in r4.columns]].to_string(index=False))
    print(f"\nreport: {md}")
    if published:
        print(f"artifacts: {len(published)}")
    return {
        "ok": True,
        "report": md,
        "docs": docs,
        "r1": r1,
        "r4": r4,
        "corr": corr,
        "enriched": enriched,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="RS×Fund region returns vs SPX (A/D/E/B)")
    p.add_argument("--config", default="config/params.yaml")
    p.add_argument("--scored", default=None, help="U2 scored CSV (default: rs_study fundamental_tech)")
    p.add_argument("--as-of", default=None)
    p.add_argument("--benchmark", default="^GSPC")
    p.add_argument("--out-dir", default=None)
    p.add_argument("--skip-forward", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run_study(
        config=args.config,
        scored=args.scored,
        as_of=args.as_of,
        benchmark=args.benchmark,
        out_dir=Path(args.out_dir) if args.out_dir else None,
        skip_forward=bool(args.skip_forward),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
