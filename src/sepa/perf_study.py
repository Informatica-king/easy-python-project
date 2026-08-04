"""SEPA performance study on accumulated ``reports/perf/`` panels.

Usage:
    python -m sepa.perf_study
    !sepa.perf_study()

Small-N safe: always emits a report that states sample size limitations.
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
from sepa.config import load_params
from sepa.fonts import savefig_korean, setup_korean_matplotlib
from sepa.perf_ledger import (
    BASKET_MEDIAN_PLUS,
    LEDGER_VERSION,
    perf_dir,
    update_perf_ledger,
)
from sepa.result_ledger import EVENT_FWD_HORIZONS
from sepa.sepatop import load_membership_history, presence_table

logger = logging.getLogger(__name__)


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


def aggregate_basket_excess(fwd: pd.DataFrame) -> pd.DataFrame:
    """Pool all ready stamp×ticker rows by basket × horizon."""
    if fwd.empty:
        return pd.DataFrame()
    rows = []
    for basket, g in fwd.groupby("basket"):
        for lab, _ in EVENT_FWD_HORIZONS:
            ready_col, exc_col = f"ready_{lab}", f"excess_{lab}"
            if ready_col not in g.columns:
                continue
            ready = g.loc[g[ready_col].astype(bool)]
            n = len(ready)
            rows.append(
                {
                    "basket": basket,
                    "horizon": lab,
                    "n_ready": n,
                    "n_stamps": int(ready["stamp"].nunique()) if n and "stamp" in ready.columns else 0,
                    "mean_excess": float(ready[exc_col].mean()) if n else np.nan,
                    "median_excess": float(ready[exc_col].median()) if n else np.nan,
                    "win_rate": float((ready[exc_col] > 0).mean()) if n else np.nan,
                }
            )
    return pd.DataFrame(rows).sort_values(["horizon", "basket"]).reset_index(drop=True)


def load_event_forward(sepatop_report: Path) -> pd.DataFrame:
    path = Path(sepatop_report) / "membership_event_fwd_panel.csv"
    return _load_csv(path)


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
    if sub.empty or ready not in sub.columns:
        return pd.DataFrame()
    # use most recent stamp per ticker that is ready
    sub = sub.loc[sub[ready].astype(bool)]
    if sub.empty:
        return pd.DataFrame()
    sub = sub.sort_values("stamp").groupby("ticker", as_index=False).tail(1)
    p = presence[["ticker", "streak_from_end", "n_present", "presence_rate", "always_present"]].copy()
    p["ticker"] = p["ticker"].astype(str).str.upper()
    sub["ticker"] = sub["ticker"].astype(str).str.upper()
    return sub.merge(p, on="ticker", how="left")


def plot_basket_bars(agg: pd.DataFrame, out_path: Path, *, horizon: str) -> Path | None:
    setup_korean_matplotlib()
    g = agg.loc[agg["horizon"] == horizon].dropna(subset=["mean_excess"])
    if g.empty:
        return None
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(g["basket"].astype(str), g["mean_excess"] * 100, color="#2c5f7c", alpha=0.85)
    ax.axhline(0, color="#333", lw=0.8)
    for i, row in enumerate(g.itertuples()):
        ax.text(i, row.mean_excess * 100, f"n={int(row.n_ready)}", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("mean excess vs SPX (%)")
    ax.set_title(f"Basket mean excess — {horizon} (ready only)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return savefig_korean(fig, out_path, dpi=140)


def write_study_md(
    path: Path,
    *,
    stamp: str,
    n_pool_days: int,
    agg: pd.DataFrame,
    events: pd.DataFrame,
    streak: pd.DataFrame,
    pool_log: pd.DataFrame,
) -> Path:
    lines = [
        f"# SEPA performance study — {stamp}",
        "",
        f"- ledger: `{LEDGER_VERSION}`",
        f"- generated (UTC): `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}`",
        f"- daily_pool_log days: **{n_pool_days}**",
        "",
        "> **표본 주의**: 수 주 수준이면 통계적 확증이 아니다. "
        "이 리포트는 장기 축적 프레임의 스냅샷이며, 수개월·수년 데이터가 쌓일수록 해석력이 커진다.",
        "",
        "## 1. Basket mean excess vs SPX (ready rows only)",
        "",
    ]
    if agg.empty:
        lines.append("_아직 ready forward 표본이 없습니다. go가 반복되면 자동 백필됩니다._")
    else:
        lines += [
            "| basket | horizon | n_ready | n_stamps | mean excess | win |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for r in agg.itertuples():
            lines.append(
                f"| {r.basket} | {r.horizon} | {int(r.n_ready)} | {int(r.n_stamps)} | "
                f"{_pct(r.mean_excess)} | {_pct(r.win_rate)} |"
            )

    lines += ["", "## 2. sepaTop enter/exit event forward", ""]
    if events.empty:
        lines.append("_membership_event_fwd_panel 없음 — sepaTop 히스토리가 더 필요_")
    else:
        for lab, _ in EVENT_FWD_HORIZONS:
            ready = f"ready_{lab}"
            exc = f"excess_{lab}"
            if ready not in events.columns:
                continue
            for action in ("enter", "exit"):
                g = events.loc[(events["action"] == action) & events[ready].astype(bool)]
                n = len(g)
                mean = float(g[exc].mean()) if n else float("nan")
                lines.append(f"- **{action}** {lab}: n={n}, mean excess={_pct(mean)}")

    lines += ["", "## 3. Streak × excess (median_plus, 21d, latest ready)", ""]
    if streak.empty or streak.get("streak_from_end") is None:
        lines.append("_presence/forward 조인 표본 부족_")
    else:
        valid = streak.dropna(subset=["excess_21d", "streak_from_end"]) if "excess_21d" in streak.columns else streak
        if valid.empty:
            lines.append("_ready 21d 표본 없음_")
        else:
            rho = float(valid["streak_from_end"].corr(valid["excess_21d"], method="spearman"))
            lines.append(f"- Spearman(streak, excess_21d) = **{rho:.3f}** (n={len(valid)})")
            if "always_present" in valid.columns:
                ap = valid.loc[valid["always_present"].astype(bool), "excess_21d"]
                lines.append(
                    f"- always_present mean excess_21d = {_pct(float(ap.mean()) if len(ap) else float('nan'))}"
                )

    lines += ["", "## 4. Pool size trail (recent)", ""]
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
        "- go를 반복할수록 `security_forward_panel`의 `ready_*`가 채워짐",
        "- soft_drop vs rs90_ok, 섹터 IR 등은 표본 증가 후 확장",
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

    presence = pd.DataFrame()
    sepatop = report_dir / "sepatop"
    if sepatop.exists():
        hist = load_membership_history(sepatop)
        presence = presence_table(hist)
    streak = streak_excess_frame(presence, fwd)

    charts_dir = out / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    chart_paths = []
    for lab, _ in EVENT_FWD_HORIZONS:
        p = plot_basket_bars(agg, charts_dir / f"perf_basket_excess_{lab}_{stamp}.png", horizon=lab)
        if p:
            chart_paths.append(p)

    if not agg.empty:
        agg.to_csv(out / f"study_basket_agg_{stamp}.csv", index=False)
    if not streak.empty:
        streak.to_csv(out / f"study_streak_excess_{stamp}.csv", index=False)

    md = write_study_md(
        out / f"study_{stamp}.md",
        stamp=stamp,
        n_pool_days=int(pool_log["stamp"].nunique()) if not pool_log.empty else 0,
        agg=agg,
        events=events,
        streak=streak,
        pool_log=pool_log,
    )

    published = publish_many([md, *chart_paths, out / "daily_pool_log.csv", out / "security_forward_panel.csv", out / "basket_members_panel.csv"])
    print(f"\n=== SEPA perf_study ({stamp}) ===")
    print(f"pool days: {0 if pool_log.empty else pool_log['stamp'].nunique()}")
    print(f"forward rows: {len(fwd)}")
    if not agg.empty:
        print(agg.to_string(index=False))
    print(f"report: {md.resolve()}")
    if published:
        print(f"artifacts: {len(published)} files")
    return {"ok": True, "md": md, "agg": agg, "charts": chart_paths, "published": published}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SEPA longitudinal performance study")
    p.add_argument("--config", default="config/params.yaml")
    p.add_argument("--stamp", default=None)
    p.add_argument("--refresh-ledger", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    params = load_params(args.config)
    run_perf_study(
        report_dir=params.report_dir,
        cache_dir=params.data.cache_dir,
        stamp=args.stamp,
        refresh_ledger=bool(args.refresh_ledger),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
