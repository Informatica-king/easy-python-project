"""VCP entry-timing tool for a hand-picked shortlist.

Intended workflow: run `python -m sepa.screener` to get the Stage 2 list,
review fundamentals and rank manually, then feed the top names here to get
VCP setup status and pivot breakout timing per ticker.

Unlike the screener this tool does NOT gate on the Trend Template (the
shortlist is assumed to be already curated); it reports trend status for
reference only.

Usage:
    python -m sepa.vcp_timing --tickers NVDA,MSFT,AVGO
    python -m sepa.vcp_timing --tickers-file shortlist.txt [--as-of YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import dataclasses
import glob
import html
import logging
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
import pandas as pd

from sepa import indicators, trend_template, vcp
from sepa.artifacts import publish_many
from sepa.config import Params, load_params
from sepa.data import store

logger = logging.getLogger(__name__)

REPORT_COLUMNS = [
    "ticker", "signal", "close", "pivot", "stop", "risk_pct", "quality_score",
    "dist_to_pivot_pct", "trend_ok", "base_weeks", "footprint",
    "final_depth_pct", "dryup_ratio", "volume_vs_avg", "note",
]

# Operator-facing Korean headers for the visual table (CSV keeps English keys).
DISPLAY_HEADERS = {
    "ticker": "티커",
    "signal": "신호",
    "close": "종가",
    "pivot": "피벗",
    "stop": "손절",
    "risk_pct": "리스크%",
    "quality_score": "품질",
    "dist_to_pivot_pct": "피벗이격%",
    "trend_ok": "추세",
    "base_weeks": "베이스주",
    "footprint": "풋프린트",
    "final_depth_pct": "최종수축%",
    "dryup_ratio": "거래량고갈",
    "volume_vs_avg": "거래량배수",
    "note": "비고 / 탈락사유",
}

SIGNAL_ORDER = {s.value: i for i, s in enumerate(
    [vcp.Signal.BREAKOUT, vcp.Signal.WATCHLIST, vcp.Signal.FORMING, vcp.Signal.EXTENDED, vcp.Signal.NONE]
)}

SIGNAL_COLORS = {
    "BREAKOUT": ("#1b5e20", "#e8f5e9"),
    "WATCHLIST": ("#0d47a1", "#e3f2fd"),
    "FORMING": ("#e65100", "#fff3e0"),
    "EXTENDED": ("#bf360c", "#fbe9e7"),
    "NONE": ("#424242", "#f5f5f5"),
    "NO_DATA": ("#b71c1c", "#ffebee"),
}

ROWS_PER_PNG = 28


def analyze(
    params: Params,
    tickers: list[str],
    as_of: str | None = None,
    update: bool = True,
) -> pd.DataFrame:
    """Compute VCP timing signals for each ticker in the shortlist."""
    data, failed = store.load_universe_history(
        tickers, params.data.cache_dir, params.data.lookback_years, update
    )
    if failed:
        logger.warning("failed to load: %s", ", ".join(failed))

    if as_of:
        cutoff = pd.Timestamp(as_of)
        data = {t: df.loc[:cutoff] for t, df in data.items()}

    # RS rank needs a universe; on a small shortlist it is meaningless, so the
    # trend check here skips condition 8.
    tp_no_rs = dataclasses.replace(params.trend_template, rs_enabled=False)

    rows = []
    for ticker in tickers:
        df = data.get(ticker)
        if df is None or len(df) < params.data.min_history_days:
            rows.append({"ticker": ticker, "signal": "NO_DATA", "note": "가격 이력 부족"})
            continue
        enriched = indicators.add_indicators(df, params.trend_template)
        trend_ok = trend_template.evaluate(enriched, tp_no_rs).passed
        res = vcp.detect_vcp(enriched, params.vcp)
        rows.append({
            "ticker": ticker,
            "signal": res.signal.value if res.valid else "NONE",
            "close": round(float(df["close"].iloc[-1]), 2),
            "pivot": res.pivot,
            "stop": res.stop,
            "risk_pct": res.risk_pct,
            "quality_score": res.quality_score,
            "dist_to_pivot_pct": res.dist_to_pivot_pct,
            "trend_ok": trend_ok,
            "base_weeks": res.base_weeks,
            "footprint": res.footprint,
            "final_depth_pct": round(res.final_depth * 100, 1) if res.final_depth is not None else None,
            "dryup_ratio": res.dryup_ratio_actual,
            "volume_vs_avg": res.volume_vs_avg,
            "note": res.reason,
        })

    report = pd.DataFrame(rows, columns=REPORT_COLUMNS)
    if not report.empty:
        report = report.sort_values(
            by="signal", key=lambda s: s.map(lambda v: SIGNAL_ORDER.get(v, len(SIGNAL_ORDER)))
        ).reset_index(drop=True)
    return report


def _setup_korean_font() -> None:
    from sepa.fonts import setup_korean_matplotlib

    setup_korean_matplotlib(allow_install=True)


def signal_summary(report: pd.DataFrame) -> dict[str, int]:
    """Count rows per signal label (including NO_DATA)."""
    if report.empty or "signal" not in report.columns:
        return {}
    order = ["BREAKOUT", "WATCHLIST", "FORMING", "EXTENDED", "NONE", "NO_DATA"]
    counts = report["signal"].fillna("NO_DATA").astype(str).value_counts()
    return {k: int(counts.get(k, 0)) for k in order if int(counts.get(k, 0)) > 0}


def _fmt_cell(col: str, value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if col == "trend_ok":
        return "Y" if bool(value) else "N"
    if col in {"close", "pivot", "stop"}:
        return f"{float(value):.2f}"
    if col in {
        "dist_to_pivot_pct", "base_weeks", "final_depth_pct",
        "dryup_ratio", "volume_vs_avg", "risk_pct", "quality_score",
    }:
        try:
            if col == "final_depth_pct":
                return f"{float(value):.1f}"
            if col == "quality_score":
                return f"{float(value):.0f}"
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _display_frame(report: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in REPORT_COLUMNS if c in report.columns]
    out = report[cols].copy()
    for c in cols:
        out[c] = out[c].map(lambda v, col=c: _fmt_cell(col, v))
    out = out.rename(columns={c: DISPLAY_HEADERS.get(c, c) for c in cols})
    return out


def build_vcp_table_html(report: pd.DataFrame, out_path: Path, *, stamp: str) -> Path:
    """Write a self-contained HTML table for browser viewing."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary = signal_summary(report)
    summary_bits = " · ".join(f"{k} {v}" for k, v in summary.items()) or "empty"

    rows_html: list[str] = []
    for _, raw in report.iterrows():
        sig = str(raw.get("signal", "NONE"))
        fg, bg = SIGNAL_COLORS.get(sig, SIGNAL_COLORS["NONE"])
        cells = []
        for col in REPORT_COLUMNS:
            if col not in report.columns:
                continue
            text = html.escape(_fmt_cell(col, raw.get(col)))
            if col == "signal":
                cells.append(
                    f'<td style="color:{fg};font-weight:700;background:{bg}">{text}</td>'
                )
            elif col == "note":
                cells.append(f'<td class="note">{text}</td>')
            else:
                cells.append(f"<td>{text}</td>")
        rows_html.append(f'<tr style="background:{bg}">{"".join(cells)}</tr>')

    headers = "".join(
        f"<th>{html.escape(DISPLAY_HEADERS.get(c, c))}</th>"
        for c in REPORT_COLUMNS
        if c in report.columns
    )
    doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>VCP timing {html.escape(stamp)}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: "Nanum Gothic", "Apple SD Gothic Neo", sans-serif;
         margin: 16px; background: #fafafa; color: #222; }}
  h1 {{ font-size: 1.25rem; margin: 0 0 4px; }}
  .meta {{ color: #666; margin-bottom: 14px; font-size: 0.92rem; }}
  .badge {{ display: inline-block; padding: 2px 8px; margin: 0 4px 6px 0;
            border-radius: 4px; font-size: 0.85rem; font-weight: 700; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); font-size: 0.88rem; }}
  th, td {{ border: 1px solid #e0e0e0; padding: 6px 8px; text-align: left;
            white-space: nowrap; }}
  th {{ position: sticky; top: 0; background: #263238; color: #fff;
       font-weight: 600; z-index: 1; }}
  td.note {{ white-space: normal; min-width: 220px; max-width: 420px; }}
  tr:hover td {{ filter: brightness(0.97); }}
  .wrap {{ overflow-x: auto; }}
</style>
</head>
<body>
  <h1>VCP 타이밍 리포트</h1>
  <div class="meta">{html.escape(stamp)} · {len(report)}종 · {html.escape(summary_bits)}</div>
  <div>
    {"".join(
        f'<span class="badge" style="color:{SIGNAL_COLORS.get(k, SIGNAL_COLORS["NONE"])[0]};'
        f'background:{SIGNAL_COLORS.get(k, SIGNAL_COLORS["NONE"])[1]}">{html.escape(k)} {v}</span>'
        for k, v in summary.items()
    )}
  </div>
  <div class="wrap">
  <table>
    <thead><tr>{headers}</tr></thead>
    <tbody>
      {"".join(rows_html) if rows_html else "<tr><td colspan='12'>(결과 없음)</td></tr>"}
    </tbody>
  </table>
  </div>
</body>
</html>
"""
    out_path.write_text(doc, encoding="utf-8")
    return out_path


def build_vcp_table_pngs(
    report: pd.DataFrame,
    out_dir: Path,
    *,
    stamp: str,
    rows_per_page: int = ROWS_PER_PNG,
) -> list[Path]:
    """Render paginated PNG table boards (Cursor / Android artifact friendly)."""
    _setup_korean_font()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = signal_summary(report)
    summary_bits = "  ·  ".join(f"{k} {v}" for k, v in summary.items()) or "empty"
    disp = _display_frame(report)
    n = len(disp)
    if n == 0:
        # still emit a one-page empty board
        pages = [disp]
    else:
        pages = [disp.iloc[i:i + rows_per_page] for i in range(0, n, rows_per_page)]

    paths: list[Path] = []
    col_labels = list(disp.columns)
    n_pages = len(pages)

    for page_i, chunk in enumerate(pages, start=1):
        n_rows = max(len(chunk), 1)
        fig_h = max(2.8, 0.42 * n_rows + 1.6)
        fig_w = 16.5
        fig, ax = plt.subplots(figsize=(fig_w, fig_h))
        ax.axis("off")
        title = f"VCP 타이밍 리포트  {stamp}   ({len(report)}종)"
        if n_pages > 1:
            title += f"   ·  {page_i}/{n_pages}"
        ax.set_title(title, fontsize=13, fontweight="bold", pad=12, loc="left")
        ax.text(
            0.0, 1.02, summary_bits,
            transform=ax.transAxes, fontsize=9, color="#555", va="bottom",
        )

        if len(chunk):
            cell_text = chunk.values.tolist()
        else:
            cell_text = [["(결과 없음)"] + [""] * max(0, len(col_labels) - 1)]

        table = ax.table(
            cellText=cell_text,
            colLabels=col_labels,
            cellLoc="left",
            loc="upper center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1.0, 1.35)

        # Column width hints — note gets more room
        note_header = DISPLAY_HEADERS["note"]
        signal_header = DISPLAY_HEADERS["signal"]
        note_idx = col_labels.index(note_header) if note_header in col_labels else -1
        signal_idx = col_labels.index(signal_header) if signal_header in col_labels else -1
        for (r, c), cell in table.get_celld().items():
            cell.set_edgecolor("#cfd8dc")
            if r == 0:
                cell.set_facecolor("#263238")
                cell.set_text_props(color="white", fontweight="bold")
                cell.set_height(0.08)
            else:
                # map back to signal color from original report rows
                if len(chunk):
                    sig = str(report.loc[chunk.index[r - 1], "signal"])
                else:
                    sig = "NONE"
                fg, bg = SIGNAL_COLORS.get(sig, SIGNAL_COLORS["NONE"])
                cell.set_facecolor(bg)
                if c == signal_idx:
                    cell.set_text_props(color=fg, fontweight="bold")
            if c == note_idx:
                cell.set_width(0.28)
            elif c == 0:
                cell.set_width(0.05)

        out = out_dir / (f"vcp_{stamp}_table.png" if n_pages == 1 else f"vcp_{stamp}_table_{page_i:02d}.png")
        fig.tight_layout()
        fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        paths.append(out)
    return paths


def write_vcp_report_pack(
    report: pd.DataFrame,
    out_dir: Path,
    *,
    stamp: str,
) -> dict[str, Path | list[Path]]:
    """Write CSV + HTML + PNG table boards and publish as artifacts."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"vcp_{stamp}.csv"
    report.to_csv(csv_path, index=False)

    html_path = build_vcp_table_html(report, out_dir / f"vcp_{stamp}.html", stamp=stamp)
    png_paths = build_vcp_table_pngs(report, out_dir, stamp=stamp)

    published = publish_many([csv_path, html_path, *png_paths])
    return {
        "csv": csv_path,
        "html": html_path,
        "pngs": png_paths,
        "published": published,
    }


def _parse_tickers(args: argparse.Namespace) -> list[str]:
    if args.tickers:
        return [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    lines = Path(args.tickers_file).read_text().splitlines()
    return [ln.strip().upper() for ln in lines if ln.strip() and not ln.startswith("#")]


def _print_console_table(report: pd.DataFrame, as_of: str | None, n_tickers: int) -> None:
    print(f"\n=== VCP timing ({as_of or 'latest'}) — shortlist: {n_tickers} tickers ===\n")
    summary = signal_summary(report)
    if summary:
        print("신호 요약: " + "  ".join(f"{k}={v}" for k, v in summary.items()))
        print()
    with pd.option_context(
        "display.width", 200,
        "display.max_columns", None,
        "display.max_colwidth", 60,
        "display.unicode.east_asian_width", True,
    ):
        print(report.to_string(index=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VCP entry timing for a shortlist")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tickers", help="comma-separated tickers, e.g. NVDA,MSFT")
    group.add_argument("--tickers-file", help="text file with one ticker per line")
    parser.add_argument("--config", default="config/params.yaml")
    parser.add_argument("--as-of", default=None, help="analyze as of date YYYY-MM-DD")
    parser.add_argument("--no-update", action="store_true", help="use cache only, skip downloads")
    parser.add_argument(
        "--swing-mode",
        choices=["pct", "atr"],
        default=None,
        help="ZigZag mode override (default: config; atr = research ATR ZigZag)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    params = load_params(args.config)
    if args.swing_mode:
        params = dataclasses.replace(
            params,
            vcp=dataclasses.replace(params.vcp, swing_mode=args.swing_mode),
        )
    tickers = _parse_tickers(args)
    report = analyze(params, tickers, as_of=args.as_of, update=not args.no_update)

    stamp = (args.as_of or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
    mode_tag = f"_{params.vcp.swing_mode}" if args.swing_mode else ""
    out_dir = Path(params.report_dir)
    pack = write_vcp_report_pack(report, out_dir, stamp=f"{stamp}{mode_tag}")

    _print_console_table(report, args.as_of, len(tickers))
    print(f"\nswing_mode : {params.vcp.swing_mode}")
    print(f"report csv : {pack['csv']}")
    print(f"report html: {pack['html']}")
    pngs = pack["pngs"]
    if len(pngs) == 1:
        print(f"report png : {pngs[0]}")
    else:
        print(f"report png : {len(pngs)} pages")
        for p in pngs:
            print(f"             {p}")
    if pack["published"]:
        print(f"artifacts  : {len(pack['published'])} files published")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
