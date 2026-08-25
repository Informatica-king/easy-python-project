"""SEPA performance study on accumulated ``reports/perf/`` panels (D29 Phase 1).

Usage:
    python -m sepa.perf_study
    !검증  /  !sepa.perf_study()

User-facing deliverable: Hangul PDF ``verify_report_YYYYMMDD.pdf`` + GitHub download link
(tag ``sepa-검증-YYYYMMDD``; ASCII asset name — Hangul filenames break ``gh`` uploads).
Modules A–D feed the report; small-N gates stay explicit.
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

from sepa.config import load_params
from sepa.fonts import KoreanFontError, savefig_korean, setup_korean_matplotlib
from sepa.perf_ledger import (
    BASKET_MEDIAN_PLUS,
    BASKET_RS90_OK,
    BASKET_SOFT_DROP,
    LEDGER_VERSION,
    perf_dir,
    update_perf_ledger,
)
from sepa.result_ledger import EVENT_FWD_HORIZONS
from sepa.sepatop import load_membership_history, presence_table
from sepa.verify_report import (
    build_verify_pdf,
    gate_ko,
    one_line_summary,
    overall_trust_gate,
    publish_verify_pdf_github_release,
    verify_pdf_name,
)

logger = logging.getLogger(__name__)

GATE_INSUFFICIENT = "insufficient"
GATE_MONITOR = "monitor"
GATE_INTERPRET = "interpret"

STREAK_BINS = (
    ("1", 1, 1),
    ("2-4", 2, 4),
    ("5+", 5, 10_000),
)


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:  # noqa: BLE001
        logger.warning("unreadable %s", path)
        return pd.DataFrame()


def _pct(x: float | None) -> str:
    if x is None or x != x:
        return "n/a"
    return f"{100 * float(x):+.2f}%"


def _as_bool_series(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().isin({"1", "true", "yes", "t"})


def _spearman(a: pd.Series, b: pd.Series) -> float:
    """Spearman without requiring scipy."""
    x = pd.to_numeric(a, errors="coerce")
    y = pd.to_numeric(b, errors="coerce")
    mask = x.notna() & y.notna()
    if mask.sum() < 2:
        return float("nan")
    return float(x[mask].rank().corr(y[mask], method="pearson"))


def sample_gate(
    *,
    n_ready: int,
    n_stamps: int = 0,
    kind: str = "basket",
) -> str:
    """Return insufficient | monitor | interpret for small-N labeling."""
    n_ready = int(n_ready or 0)
    n_stamps = int(n_stamps or 0)
    if kind == "basket":
        if n_stamps >= 40 and n_ready >= 200:
            return GATE_INTERPRET
        if n_stamps >= 5 and n_ready >= 30:
            return GATE_MONITOR
        return GATE_INSUFFICIENT
    if kind == "event":
        if n_ready >= 20:
            return GATE_INTERPRET if n_ready >= 50 else GATE_MONITOR
        return GATE_INSUFFICIENT
    if kind == "streak":
        if n_ready >= 80:
            return GATE_INTERPRET
        if n_ready >= 30:
            return GATE_MONITOR
        return GATE_INSUFFICIENT
    if kind == "soft_vs":
        # per-basket ready counts passed as n_ready = min(side_a, side_b)
        if n_stamps >= 20 and n_ready >= 50:
            return GATE_INTERPRET
        if n_stamps >= 5 and n_ready >= 15:
            return GATE_MONITOR
        return GATE_INSUFFICIENT
    return GATE_INSUFFICIENT


def gate_badge(gate: str) -> str:
    return {
        GATE_INSUFFICIENT: "`insufficient`",
        GATE_MONITOR: "`monitor`",
        GATE_INTERPRET: "`interpret`",
    }.get(gate, f"`{gate}`")


# ── A. Basket excess ──────────────────────────────────────────────


def aggregate_basket_excess(fwd: pd.DataFrame) -> pd.DataFrame:
    """Pool ready stamp×ticker rows by basket × horizon (+ sample_gate)."""
    if fwd.empty:
        return pd.DataFrame()
    rows = []
    for basket, g in fwd.groupby("basket"):
        for lab, _ in EVENT_FWD_HORIZONS:
            ready_col, exc_col = f"ready_{lab}", f"excess_{lab}"
            if ready_col not in g.columns or exc_col not in g.columns:
                continue
            ready = g.loc[_as_bool_series(g[ready_col])]
            n = len(ready)
            n_stamps = int(ready["stamp"].nunique()) if n and "stamp" in ready.columns else 0
            mean_exc = float(ready[exc_col].mean()) if n else np.nan
            rows.append(
                {
                    "basket": basket,
                    "horizon": lab,
                    "n_ready": n,
                    "n_stamps": n_stamps,
                    "mean_excess": mean_exc,
                    "median_excess": float(ready[exc_col].median()) if n else np.nan,
                    "std_excess": float(ready[exc_col].std(ddof=0)) if n else np.nan,
                    "win_rate": float((ready[exc_col] > 0).mean()) if n else np.nan,
                    "sample_gate": sample_gate(n_ready=n, n_stamps=n_stamps, kind="basket"),
                }
            )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["horizon", "basket"]).reset_index(drop=True)


# ── B. Enter/exit events ──────────────────────────────────────────


def load_event_forward(sepatop_report: Path) -> pd.DataFrame:
    path = Path(sepatop_report) / "membership_event_fwd_panel.csv"
    return _load_csv(path)


def study_event_forward(events: pd.DataFrame) -> pd.DataFrame:
    """Aggregate enter/exit × horizon mean excess (ready only)."""
    if events.empty or "action" not in events.columns:
        return pd.DataFrame()
    rows = []
    for lab, _ in EVENT_FWD_HORIZONS:
        ready_col, exc_col = f"ready_{lab}", f"excess_{lab}"
        if ready_col not in events.columns or exc_col not in events.columns:
            continue
        for action in ("enter", "exit"):
            g = events.loc[
                (events["action"].astype(str) == action) & _as_bool_series(events[ready_col])
            ]
            n = len(g)
            rows.append(
                {
                    "action": action,
                    "horizon": lab,
                    "n_ready": n,
                    "n_stamps": int(g["stamp"].nunique()) if n and "stamp" in g.columns else 0,
                    "mean_excess": float(g[exc_col].mean()) if n else np.nan,
                    "median_excess": float(g[exc_col].median()) if n else np.nan,
                    "win_rate": float((g[exc_col] > 0).mean()) if n else np.nan,
                    "sample_gate": sample_gate(n_ready=n, kind="event"),
                }
            )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["horizon", "action"]).reset_index(drop=True)


# ── C. Streak × excess ────────────────────────────────────────────


def streak_excess_frame(
    presence: pd.DataFrame,
    fwd: pd.DataFrame,
    *,
    basket: str = BASKET_MEDIAN_PLUS,
    horizon: str = "21d",
) -> pd.DataFrame:
    """Join latest presence streak with forward excess for one basket/horizon."""
    if presence.empty or fwd.empty:
        return pd.DataFrame()
    exc = f"excess_{horizon}"
    ready = f"ready_{horizon}"
    sub = fwd.loc[fwd["basket"].astype(str) == basket].copy()
    if sub.empty or ready not in sub.columns or exc not in sub.columns:
        return pd.DataFrame()
    sub = sub.loc[_as_bool_series(sub[ready])]
    if sub.empty:
        return pd.DataFrame()
    sub = sub.sort_values("stamp").groupby("ticker", as_index=False).tail(1)
    keep = ["ticker", "streak_from_end", "n_present", "presence_rate", "always_present"]
    keep = [c for c in keep if c in presence.columns]
    p = presence[keep].copy()
    p["ticker"] = p["ticker"].astype(str).str.upper()
    sub["ticker"] = sub["ticker"].astype(str).str.upper()
    out = sub.merge(p, on="ticker", how="left")
    if "streak_from_end" in out.columns:
        out["streak_bucket"] = _streak_bucket(out["streak_from_end"])
    return out


def _streak_bucket(streak: pd.Series) -> pd.Series:
    s = pd.to_numeric(streak, errors="coerce")
    labels = pd.Series(index=s.index, dtype=object)
    for name, lo, hi in STREAK_BINS:
        labels.loc[(s >= lo) & (s <= hi)] = name
    return labels


def study_streak_buckets(streak: pd.DataFrame, *, horizon: str = "21d") -> pd.DataFrame:
    """Mean excess by streak bucket + overall spearman."""
    exc = f"excess_{horizon}"
    if streak.empty or exc not in streak.columns or "streak_from_end" not in streak.columns:
        return pd.DataFrame()
    valid = streak.dropna(subset=[exc, "streak_from_end"]).copy()
    if valid.empty:
        return pd.DataFrame()
    rho = _spearman(valid["streak_from_end"], valid[exc])
    rows = []
    if "streak_bucket" not in valid.columns:
        valid["streak_bucket"] = _streak_bucket(valid["streak_from_end"])
    for name, _, _ in STREAK_BINS:
        g = valid.loc[valid["streak_bucket"] == name]
        n = len(g)
        rows.append(
            {
                "bucket": name,
                "horizon": horizon,
                "n_ready": n,
                "mean_excess": float(g[exc].mean()) if n else np.nan,
                "win_rate": float((g[exc] > 0).mean()) if n else np.nan,
                "spearman_all": rho,
                "sample_gate": sample_gate(n_ready=len(valid), kind="streak"),
            }
        )
    # always_present row
    if "always_present" in valid.columns:
        ap = valid.loc[_as_bool_series(valid["always_present"])]
        n = len(ap)
        rows.append(
            {
                "bucket": "always_present",
                "horizon": horizon,
                "n_ready": n,
                "mean_excess": float(ap[exc].mean()) if n else np.nan,
                "win_rate": float((ap[exc] > 0).mean()) if n else np.nan,
                "spearman_all": rho,
                "sample_gate": sample_gate(n_ready=len(valid), kind="streak"),
            }
        )
    return pd.DataFrame(rows)


# ── D. soft_drop vs rs90_ok ───────────────────────────────────────


def study_soft_vs_rs90(fwd: pd.DataFrame) -> pd.DataFrame:
    """Compare soft_drop vs rs90_ok forward excess by horizon."""
    if fwd.empty or "basket" not in fwd.columns:
        return pd.DataFrame()
    rows = []
    for lab, _ in EVENT_FWD_HORIZONS:
        ready_col, exc_col = f"ready_{lab}", f"excess_{lab}"
        if ready_col not in fwd.columns or exc_col not in fwd.columns:
            continue
        sides = {}
        for basket in (BASKET_SOFT_DROP, BASKET_RS90_OK):
            g = fwd.loc[
                (fwd["basket"].astype(str) == basket) & _as_bool_series(fwd[ready_col])
            ]
            n = len(g)
            sides[basket] = {
                "n_ready": n,
                "n_stamps": int(g["stamp"].nunique()) if n and "stamp" in g.columns else 0,
                "mean_excess": float(g[exc_col].mean()) if n else np.nan,
                "median_excess": float(g[exc_col].median()) if n else np.nan,
                "win_rate": float((g[exc_col] > 0).mean()) if n else np.nan,
            }
        soft = sides[BASKET_SOFT_DROP]
        ok = sides[BASKET_RS90_OK]
        min_n = min(soft["n_ready"], ok["n_ready"])
        min_stamps = min(soft["n_stamps"], ok["n_stamps"])
        delta = (
            soft["mean_excess"] - ok["mean_excess"]
            if soft["n_ready"] and ok["n_ready"]
            else np.nan
        )
        rows.append(
            {
                "horizon": lab,
                "n_soft_drop": soft["n_ready"],
                "n_rs90_ok": ok["n_ready"],
                "n_stamps_soft": soft["n_stamps"],
                "n_stamps_rs90": ok["n_stamps"],
                "mean_soft_drop": soft["mean_excess"],
                "mean_rs90_ok": ok["mean_excess"],
                "delta_soft_minus_rs90": delta,
                "win_soft_drop": soft["win_rate"],
                "win_rs90_ok": ok["win_rate"],
                "sample_gate": sample_gate(n_ready=min_n, n_stamps=min_stamps, kind="soft_vs"),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("horizon").reset_index(drop=True)


# ── Charts ────────────────────────────────────────────────────────


def plot_basket_bars(agg: pd.DataFrame, out_path: Path, *, horizon: str) -> Path | None:
    setup_korean_matplotlib()
    if agg.empty or "horizon" not in agg.columns:
        return None
    g = agg.loc[agg["horizon"] == horizon].dropna(subset=["mean_excess"])
    if g.empty:
        return None
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(g["basket"].astype(str), g["mean_excess"] * 100, color="#2c5f7c", alpha=0.85)
    ax.axhline(0, color="#333", lw=0.8)
    for i, row in enumerate(g.itertuples()):
        ax.text(i, row.mean_excess * 100, f"n={int(row.n_ready)}", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("mean excess vs SPX (%)")
    ax.set_title(f"A. Basket mean excess — {horizon} (ready only)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return savefig_korean(fig, out_path, dpi=140)


def plot_event_bars(event_agg: pd.DataFrame, out_path: Path, *, horizon: str) -> Path | None:
    setup_korean_matplotlib()
    if event_agg.empty or "horizon" not in event_agg.columns:
        return None
    g = event_agg.loc[event_agg["horizon"] == horizon].dropna(subset=["mean_excess"])
    if g.empty:
        return None
    fig, ax = plt.subplots(figsize=(6, 4))
    colors = {"enter": "#2c5f7c", "exit": "#8b4513"}
    xs = g["action"].astype(str).tolist()
    ys = (g["mean_excess"] * 100).tolist()
    ax.bar(xs, ys, color=[colors.get(a, "#666") for a in xs], alpha=0.85)
    ax.axhline(0, color="#333", lw=0.8)
    for i, row in enumerate(g.itertuples()):
        ax.text(i, row.mean_excess * 100, f"n={int(row.n_ready)}", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("mean excess vs SPX (%)")
    ax.set_title(f"B. Enter/exit excess — {horizon}")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return savefig_korean(fig, out_path, dpi=140)


def plot_streak_scatter(streak: pd.DataFrame, out_path: Path, *, horizon: str = "21d") -> Path | None:
    setup_korean_matplotlib()
    exc = f"excess_{horizon}"
    if streak.empty or exc not in streak.columns or "streak_from_end" not in streak.columns:
        return None
    valid = streak.dropna(subset=[exc, "streak_from_end"])
    if valid.empty:
        return None
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(
        valid["streak_from_end"],
        valid[exc] * 100,
        alpha=0.65,
        c="#2c5f7c",
        edgecolors="none",
        s=36,
    )
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_xlabel("streak_from_end")
    ax.set_ylabel(f"excess {horizon} vs SPX (%)")
    ax.set_title(f"C. Streak × excess (median_plus, {horizon})")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return savefig_korean(fig, out_path, dpi=140)


def plot_soft_vs_rs90(soft_cmp: pd.DataFrame, out_path: Path) -> Path | None:
    setup_korean_matplotlib()
    if soft_cmp.empty:
        return None
    g = soft_cmp.dropna(subset=["mean_soft_drop", "mean_rs90_ok"], how="all")
    if g.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(g))
    w = 0.35
    ax.bar(x - w / 2, g["mean_soft_drop"] * 100, w, label="soft_drop", color="#8b4513", alpha=0.85)
    ax.bar(x + w / 2, g["mean_rs90_ok"] * 100, w, label="rs90_ok", color="#2c5f7c", alpha=0.85)
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(g["horizon"].astype(str))
    ax.set_ylabel("mean excess vs SPX (%)")
    ax.set_title("D. soft_drop vs rs90_ok (ready only)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    for i, row in enumerate(g.itertuples()):
        ax.text(i - w / 2, (row.mean_soft_drop or 0) * 100, f"n={int(row.n_soft_drop)}", ha="center", va="bottom", fontsize=7)
        ax.text(i + w / 2, (row.mean_rs90_ok or 0) * 100, f"n={int(row.n_rs90_ok)}", ha="center", va="bottom", fontsize=7)
    fig.tight_layout()
    return savefig_korean(fig, out_path, dpi=140)


# ── Report MD ─────────────────────────────────────────────────────


def write_study_md(
    path: Path,
    *,
    stamp: str,
    n_pool_days: int,
    agg: pd.DataFrame,
    event_agg: pd.DataFrame,
    streak: pd.DataFrame,
    streak_buckets: pd.DataFrame,
    soft_cmp: pd.DataFrame,
    pool_log: pd.DataFrame,
) -> Path:
    lines = [
        f"# SEPA performance study — {stamp}",
        "",
        f"- ledger: `{LEDGER_VERSION}`",
        f"- phase: **D29 Phase 1** (A–D)",
        f"- generated (UTC): `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}`",
        f"- daily_pool_log days: **{n_pool_days}**",
        "",
        "> **표본 주의**: 수 주 수준이면 통계적 확증이 아니다. "
        "섹션마다 `insufficient` / `monitor` / `interpret` 게이트를 붙인다. "
        "프로덕션 파라미터는 이 리포트만으로 바꾸지 않는다.",
        "",
        "## A. Basket mean excess vs SPX (ready rows only)",
        "",
    ]
    if agg.empty:
        lines.append("_아직 ready forward 표본이 없습니다. go가 반복되면 자동 백필됩니다._")
    else:
        worst = GATE_INSUFFICIENT
        if (agg["sample_gate"] == GATE_INTERPRET).any():
            worst = GATE_INTERPRET
        elif (agg["sample_gate"] == GATE_MONITOR).any():
            worst = GATE_MONITOR
        lines.append(f"- section gate (best row): {gate_badge(worst)}")
        lines += [
            "",
            "| basket | horizon | n_ready | n_stamps | mean | win | gate |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
        for r in agg.itertuples():
            lines.append(
                f"| {r.basket} | {r.horizon} | {int(r.n_ready)} | {int(r.n_stamps)} | "
                f"{_pct(r.mean_excess)} | {_pct(r.win_rate)} | {r.sample_gate} |"
            )

    lines += ["", "## B. sepaTop enter/exit event forward", ""]
    if event_agg.empty:
        lines.append("_membership_event_fwd_panel 없음 또는 ready=0 — sepaTop 히스토리·대기 필요_")
    else:
        best_gate = GATE_INSUFFICIENT
        if (event_agg["sample_gate"] == GATE_INTERPRET).any():
            best_gate = GATE_INTERPRET
        elif (event_agg["sample_gate"] == GATE_MONITOR).any():
            best_gate = GATE_MONITOR
        lines.append(f"- section gate (best row): {gate_badge(best_gate)}")
        lines += [
            "",
            "| action | horizon | n_ready | mean excess | win | gate |",
            "|---|---|---:|---:|---:|---|",
        ]
        for r in event_agg.itertuples():
            lines.append(
                f"| {r.action} | {r.horizon} | {int(r.n_ready)} | "
                f"{_pct(r.mean_excess)} | {_pct(r.win_rate)} | {r.sample_gate} |"
            )

    lines += ["", "## C. Streak × excess (median_plus, 21d)", ""]
    if streak_buckets.empty:
        lines.append("_presence/forward 조인 표본 부족_")
    else:
        gate_c = str(streak_buckets["sample_gate"].iloc[0])
        rho = streak_buckets["spearman_all"].iloc[0]
        lines.append(f"- section gate: {gate_badge(gate_c)}")
        lines.append(f"- Spearman(streak, excess_21d) = **{float(rho):.3f}**")
        lines += [
            "",
            "| bucket | n | mean excess | win |",
            "|---|---:|---:|---:|",
        ]
        for r in streak_buckets.itertuples():
            lines.append(
                f"| {r.bucket} | {int(r.n_ready)} | {_pct(r.mean_excess)} | {_pct(r.win_rate)} |"
            )

    lines += ["", "## D. soft_drop vs rs90_ok (정책 검증)", ""]
    lines.append(
        "> soft_drop = RS≥90이지만 Fund<중앙값으로 탈락 · "
        "rs90_ok = 풀 안 RS≥90 통과. "
        "`delta = mean(soft_drop) − mean(rs90_ok)` — 음수면 뺀 쪽이 더 못함(정책 지지 쪽)."
    )
    lines.append("")
    if soft_cmp.empty:
        lines.append("_soft_drop / rs90_ok ready 표본 없음_")
    else:
        best_gate = GATE_INSUFFICIENT
        if (soft_cmp["sample_gate"] == GATE_INTERPRET).any():
            best_gate = GATE_INTERPRET
        elif (soft_cmp["sample_gate"] == GATE_MONITOR).any():
            best_gate = GATE_MONITOR
        lines.append(f"- section gate (best min-n row): {gate_badge(best_gate)}")
        lines += [
            "",
            "| horizon | n_soft | n_rs90 | mean soft | mean rs90 | Δ soft−rs90 | gate |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
        for r in soft_cmp.itertuples():
            lines.append(
                f"| {r.horizon} | {int(r.n_soft_drop)} | {int(r.n_rs90_ok)} | "
                f"{_pct(r.mean_soft_drop)} | {_pct(r.mean_rs90_ok)} | "
                f"{_pct(r.delta_soft_minus_rs90)} | {r.sample_gate} |"
            )

    lines += ["", "## Pool size trail (recent)", ""]
    if pool_log.empty:
        lines.append("_daily_pool_log 없음_")
    else:
        tail = pool_log.sort_values("stamp").tail(10)
        lines += [
            "| stamp | n_fund | n_median+ | n_q4 | fund_median |",
            "|---|---:|---:|---:|---:|",
        ]
        for r in tail.itertuples():
            lines.append(
                f"| {r.stamp} | {getattr(r, 'n_fund_pool', 'n/a')} | "
                f"{getattr(r, 'n_median_plus', 'n/a')} | {getattr(r, 'n_fund_q4', 'n/a')} | "
                f"{getattr(r, 'fund_median', float('nan'))} |"
            )

    lines += [
        "",
        "## 다음",
        "",
        "- go / fill_gaps 반복 → `ready_*`·게이트가 `monitor`→`interpret`로 올라감",
        "- Phase 2: 풀 안정성 차트(E), `--module` 단일 실행",
        "- Phase 3: 섹터·분위(F) — stamps 충분할 때",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_perf_study(
    *,
    report_dir: str | Path = "reports",
    cache_dir: str | Path = "data/raw",
    stamp: str | None = None,
    refresh_ledger: bool = False,
    skip_github_release: bool = False,
) -> dict:
    report_dir = Path(report_dir)
    out = perf_dir(report_dir)
    stamp = stamp or datetime.now().strftime("%Y%m%d")

    if refresh_ledger:
        fund_path = report_dir / f"fundamental_{stamp}.csv"
        if fund_path.exists():
            fund_df = pd.read_csv(fund_path)
            soft_path = report_dir / f"rs_soft_drops_{stamp}.csv"
            soft = pd.read_csv(soft_path) if soft_path.exists() else None
            stage2 = report_dir / f"stage2_{stamp}.csv"
            n_stage2 = len(pd.read_csv(stage2)) if stage2.exists() else None
            update_perf_ledger(
                report_dir=report_dir,
                cache_dir=cache_dir,
                stamp=stamp,
                fund_df=fund_df,
                soft_drops=soft,
                n_stage2=n_stage2,
                publish=True,
            )

    pool_log = _load_csv(out / "daily_pool_log.csv")
    fwd = _load_csv(out / "security_forward_panel.csv")
    agg = aggregate_basket_excess(fwd)
    events = load_event_forward(report_dir / "sepatop")
    event_agg = study_event_forward(events)

    presence = pd.DataFrame()
    sepatop = report_dir / "sepatop"
    if sepatop.exists():
        hist = load_membership_history(sepatop)
        presence = presence_table(hist)
    streak = streak_excess_frame(presence, fwd)
    streak_buckets = study_streak_buckets(streak, horizon="21d")
    soft_cmp = study_soft_vs_rs90(fwd)

    # Fund-bucket 1y path — interpretation layer for verify PDF (not a verdict)
    fund_trend_combined = pd.DataFrame()
    fund_trend_counts: dict[str, int] = {}
    fund_trend_context: dict = {}
    try:
        from sepa.candidates import apply_candidate_filters
        from sepa.fund_score_trend import (
            build_bucket_trends,
            summarize_fund_trend_context,
        )

        fund_path = report_dir / f"fundamental_{stamp}.csv"
        if not fund_path.exists():
            # latest fundamental_*.csv fallback
            cands = sorted(report_dir.glob("fundamental_????????.csv"))
            fund_path = cands[-1] if cands else fund_path
        if fund_path.exists():
            fund_df = pd.read_csv(fund_path)
            fund_df, _ = apply_candidate_filters(fund_df)
            fund_trend_combined, fund_trend_counts = build_bucket_trends(
                fund_df, cache_dir=cache_dir
            )
            fund_trend_context = summarize_fund_trend_context(
                fund_trend_combined, fund_trend_counts
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("fund trend context for verify failed: %s", exc)
        fund_trend_context = {
            "ok": False,
            "tip": "Fund 구간 추세 맥락을 만들지 못했습니다.",
            "bullets": ["본심판은 A–D입니다."],
            "empty_high": [],
        }

    n_pool_days = int(pool_log["stamp"].nunique()) if not pool_log.empty else 0
    trust = overall_trust_gate(
        agg=agg, event_agg=event_agg, soft_cmp=soft_cmp, streak_buckets=streak_buckets
    )
    n_5d_stamps = 0
    if not agg.empty:
        g5 = agg.loc[agg["horizon"].astype(str) == "5d"]
        if not g5.empty:
            n_5d_stamps = int(g5["n_stamps"].max())
    summary = one_line_summary(
        n_pool_days=n_pool_days,
        n_5d_stamps=n_5d_stamps,
        trust=trust,
        agg=agg,
        soft_cmp=soft_cmp,
    )
    if fund_trend_context.get("tip"):
        summary = f"{summary}  {fund_trend_context['tip']}"

    pdf_path = out / verify_pdf_name(stamp)
    pdf_error: str | None = None
    try:
        build_verify_pdf(
            pdf_path,
            stamp=stamp,
            n_pool_days=n_pool_days,
            agg=agg,
            event_agg=event_agg,
            streak_buckets=streak_buckets,
            soft_cmp=soft_cmp,
            pool_log=pool_log,
            fwd=fwd,
            fund_trend_combined=fund_trend_combined,
            fund_trend_counts=fund_trend_counts,
            fund_trend_context=fund_trend_context,
        )
    except KoreanFontError as exc:
        pdf_path = None  # type: ignore[assignment]
        pdf_error = str(exc)
        logger.error("verify PDF failed: %s", exc)

    release: dict | None = None
    if pdf_path is not None and pdf_path.exists() and not skip_github_release:
        release = publish_verify_pdf_github_release(pdf_path, stamp=stamp)
        if not release.get("ok"):
            logger.warning("verify release upload failed: %s", release.get("error"))

    print(f"\n=== SEPA 검증 보고서 ({stamp}) ===")
    print(f"신뢰: {gate_ko(trust)} (관측 {n_pool_days}일 · 5일 성적 stamp {n_5d_stamps}일)")
    print(f"한줄: {summary}")
    if fund_trend_context.get("ok") and fund_trend_context.get("tip"):
        print(fund_trend_context["tip"])
    if pdf_path is not None and pdf_path.exists():
        print(f"\n  PDF: {pdf_path.resolve()}")
    elif pdf_error:
        print(f"\n  PDF 실패: {pdf_error}")
    if release and release.get("ok"):
        print(f"\n  PDF 직접 다운로드:\n  {release['download_url']}\n")
        print(f"  릴리즈 페이지:\n  {release['release_url']}\n")
    elif release and not release.get("ok"):
        print(f"\n  Release 업로드 실패: {release.get('error')}")

    return {
        "ok": pdf_path is not None and pdf_path.exists(),
        "pdf": pdf_path,
        "pdf_error": pdf_error,
        "release": release,
        "trust": trust,
        "summary": summary,
        "fund_trend_context": fund_trend_context,
        "agg": agg,
        "event_agg": event_agg,
        "streak_buckets": streak_buckets,
        "soft_cmp": soft_cmp,
        "n_pool_days": n_pool_days,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SEPA 검증 보고서 PDF (D29 → verify report)")
    p.add_argument("--config", default="config/params.yaml")
    p.add_argument("--stamp", default=None)
    p.add_argument("--refresh-ledger", action="store_true")
    p.add_argument(
        "--skip-github-release",
        action="store_true",
        help="Skip uploading PDF to GitHub Release (no public download link)",
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    params = load_params(args.config)
    run_perf_study(
        report_dir=params.report_dir,
        cache_dir=params.data.cache_dir,
        stamp=args.stamp,
        refresh_ledger=bool(args.refresh_ledger),
        skip_github_release=bool(args.skip_github_release),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
