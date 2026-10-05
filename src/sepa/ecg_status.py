"""ECG / CSS status one-liners for live UX (D34 Phase B2).

Reads existing artifacts only — does not recompute as-of CSS grids.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _latest(report_dir: Path, pattern: str) -> Path | None:
    paths = sorted(report_dir.glob(pattern))
    return paths[-1] if paths else None


def load_ecg_recommend_line(report_dir: str | Path, stamp: str | None = None) -> tuple[int, str, Path | None]:
    """Return (n, copy_line, path) for ECG recommend tickers."""
    report_dir = Path(report_dir)
    path: Path | None = None
    if stamp:
        cand = report_dir / f"ecg_recommend_tickers_{stamp}.txt"
        if cand.exists():
            path = cand
    if path is None:
        path = _latest(report_dir, "ecg_recommend_tickers_*.txt")
    if path is None or not path.exists():
        return 0, "", None
    line = path.read_text(encoding="utf-8").strip()
    tickers = [t for t in line.split(",") if t.strip()]
    return len(tickers), line, path


def load_css_ecg_vs_sepatop(report_dir: str | Path) -> dict[str, float | str]:
    """Best-effort CSS snapshot from last ``css_rollup.csv`` / ``css_delta.csv``."""
    report_dir = Path(report_dir)
    out: dict[str, float | str] = {"ok": False}
    roll_path = report_dir / "asof_forward_bt" / "css_rollup.csv"
    delta_path = report_dir / "asof_forward_bt" / "css_delta.csv"
    if not roll_path.exists():
        return out
    try:
        roll = pd.read_csv(roll_path)
        if roll.empty or "rule" not in roll.columns:
            return out
        st = roll.loc[roll["rule"] == "sepaTop"]
        ec = roll.loc[roll["rule"] == "ecg_top"]
        if st.empty or ec.empty:
            return out
        st_css = float(st.iloc[0]["CSS"])
        ec_css = float(ec.iloc[0]["CSS"])
        n_asof = int(st.iloc[0].get("n_asof", ec.iloc[0].get("n_asof", 0)) or 0)
        delta = ec_css - st_css
        s2_d = float("nan")
        s4_d = float("nan")
        if delta_path.exists():
            d = pd.read_csv(delta_path)
            er = d.loc[d["rule"] == "ecg_top"]
            if not er.empty:
                if "d_S2_median_excess" in er.columns:
                    s2_d = float(er.iloc[0]["d_S2_median_excess"])
                if "d_S4_tail_penalty" in er.columns:
                    s4_d = float(er.iloc[0]["d_S4_tail_penalty"])
                if "delta_css_vs_sepaTop" in er.columns:
                    delta = float(er.iloc[0]["delta_css_vs_sepaTop"])
        out.update(
            {
                "ok": True,
                "n_asof": n_asof,
                "css_sepaTop": st_css,
                "css_ecg_top": ec_css,
                "delta_css": delta,
                "d_S2": s2_d,
                "d_S4": s4_d,
                "sample_note": "자료 부족" if n_asof < 20 else "모니터",
            }
        )
    except Exception:  # noqa: BLE001
        return {"ok": False}
    return out


def format_ecg_b2_summary_line(report_dir: str | Path, *, stamp: str | None = None) -> str:
    """Single Korean status line for go / !검증 footers."""
    n, _line, _path = load_ecg_recommend_line(report_dir, stamp=stamp)
    css = load_css_ecg_vs_sepatop(report_dir)
    parts = [
        "ECG추천 레이어(B1) · 본선(sepaTop/soft/median+) 유지",
    ]
    if n > 0:
        parts.append(f"오늘 추천 {n}종")
    else:
        parts.append("오늘 추천 파일 없음(!anal/!go 후 생성)")
    if css.get("ok"):
        d = float(css["delta_css"])
        parts.append(
            f"CSS ecg_top {float(css['css_ecg_top']):.1f} vs sepaTop {float(css['css_sepaTop']):.1f} "
            f"(Δ{d:+.1f}, n_asof={int(css['n_asof'])}, {css['sample_note']})"
        )
        s2 = css.get("d_S2")
        s4 = css.get("d_S4")
        if s2 == s2 and s4 == s4:
            parts.append(f"S2{float(s2):+.1f}/S4{float(s4):+.1f}")
    else:
        parts.append("CSS 롤업 없음(!sepa.css()로 갱신)")
    return " · ".join(parts)


def print_ecg_b2_summary(report_dir: str | Path, *, stamp: str | None = None) -> str:
    line = format_ecg_b2_summary_line(report_dir, stamp=stamp)
    print("=" * 64)
    print("  [B2] ECG/CSS 한 줄 요약")
    print("=" * 64)
    print(f"  {line}")
    print("=" * 64 + "\n")
    return line
