"""SEPA ``!검증`` — plain-language 8-page Hangul PDF + GitHub download link.

User-facing deliverable is **PDF only** (no MD/ZIP in V1).
Release tag: ``sepa-검증-YYYYMMDD``.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

from sepa.artifacts import publish
from sepa.fonts import (
    assert_korean_font_ready,
    korean_fontproperties,
    setup_korean_matplotlib,
)
from sepa.perf_ledger import LEDGER_VERSION

logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = 11.0, 8.5
FOOTER_NOTE = "시장 = S&P500(^GSPC) 대비 초과수익 · look-ahead 없음 · 매매 권유 아님"

GATE_INSUFFICIENT = "insufficient"
GATE_MONITOR = "monitor"
GATE_INTERPRET = "interpret"

GATE_KO = {
    GATE_INSUFFICIENT: "자료 부족",
    GATE_MONITOR: "지켜보는 중",
    GATE_INTERPRET: "해석 가능",
}

ANSWER_KO = {
    "yes": "예",
    "no": "아니오",
    "unknown": "모름",
}


def gate_ko(gate: str) -> str:
    return GATE_KO.get(str(gate), str(gate))


def _pct(x: float | None, digits: int = 2) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{100 * float(x):+.{digits}f}%"


def _setup() -> None:
    setup_korean_matplotlib(allow_install=True)


def _fp(*, bold: bool = False, size: float = 11):
    return korean_fontproperties(bold=bold, size=size)


def _wrap(text: str, width: int = 54) -> str:
    lines: list[str] = []
    remaining = (text or "").strip()
    while len(remaining) > width:
        cut = width
        window = remaining[:width]
        for i, ch in enumerate(reversed(window[-14:]), start=1):
            if ch in " .，。、;；/·,":
                cut = width - i + 1
                break
        lines.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        lines.append(remaining)
    return "\n".join(lines)


def _footer(fig, page: int, total: int = 9) -> None:
    fig.text(
        0.5, 0.025,
        f"{FOOTER_NOTE}  ·  {page}/{total}",
        ha="center", va="bottom",
        fontproperties=_fp(size=7.5),
        color="#888",
    )


def _best_gate(series: pd.Series | None) -> str:
    if series is None or len(series) == 0:
        return GATE_INSUFFICIENT
    s = series.astype(str)
    if (s == GATE_INTERPRET).any():
        return GATE_INTERPRET
    if (s == GATE_MONITOR).any():
        return GATE_MONITOR
    return GATE_INSUFFICIENT


def _worst_gate(*gates: str) -> str:
    order = {GATE_INSUFFICIENT: 0, GATE_MONITOR: 1, GATE_INTERPRET: 2}
    if not gates:
        return GATE_INSUFFICIENT
    return min(gates, key=lambda g: order.get(g, 0))


def _row_horizon(df: pd.DataFrame, horizon: str = "5d") -> pd.Series | None:
    if df is None or df.empty or "horizon" not in df.columns:
        return None
    g = df.loc[df["horizon"].astype(str) == horizon]
    if g.empty:
        return None
    return g.iloc[0]


def overall_trust_gate(
    *,
    agg: pd.DataFrame,
    event_agg: pd.DataFrame,
    soft_cmp: pd.DataFrame,
    streak_buckets: pd.DataFrame,
) -> str:
    gates = [
        _best_gate(agg["sample_gate"] if not agg.empty and "sample_gate" in agg.columns else None),
        _best_gate(
            event_agg["sample_gate"] if not event_agg.empty and "sample_gate" in event_agg.columns else None
        ),
        _best_gate(
            soft_cmp["sample_gate"] if not soft_cmp.empty and "sample_gate" in soft_cmp.columns else None
        ),
        _best_gate(
            streak_buckets["sample_gate"]
            if not streak_buckets.empty and "sample_gate" in streak_buckets.columns
            else None
        ),
    ]
    return _worst_gate(*gates)


def _answer_basket(agg: pd.DataFrame) -> str:
    row = None
    if not agg.empty:
        g = agg.loc[
            (agg["basket"].astype(str) == "median_plus") & (agg["horizon"].astype(str) == "5d")
        ]
        if not g.empty:
            row = g.iloc[0]
    if row is None or int(row.get("n_ready", 0) or 0) == 0:
        return "unknown"
    if str(row.get("sample_gate")) == GATE_INSUFFICIENT:
        return "unknown"
    mean = float(row["mean_excess"])
    if mean != mean:
        return "unknown"
    return "yes" if mean > 0 else "no"


def _answer_timing(event_agg: pd.DataFrame) -> str:
    if event_agg.empty:
        return "unknown"
    enter = event_agg.loc[
        (event_agg["action"].astype(str) == "enter") & (event_agg["horizon"].astype(str) == "5d")
    ]
    exit_ = event_agg.loc[
        (event_agg["action"].astype(str) == "exit") & (event_agg["horizon"].astype(str) == "5d")
    ]
    if enter.empty or exit_.empty:
        return "unknown"
    er, xr = enter.iloc[0], exit_.iloc[0]
    if str(er.get("sample_gate")) == GATE_INSUFFICIENT and str(xr.get("sample_gate")) == GATE_INSUFFICIENT:
        return "unknown"
    if int(er.get("n_ready", 0) or 0) == 0 or int(xr.get("n_ready", 0) or 0) == 0:
        return "unknown"
    # weak heuristic: enter excess >= 0 and exit excess <= 0 → timing ok
    e_mean = float(er["mean_excess"])
    x_mean = float(xr["mean_excess"])
    if e_mean != e_mean or x_mean != x_mean:
        return "unknown"
    if e_mean >= 0 and x_mean <= 0:
        return "yes"
    if e_mean < 0 and x_mean > 0:
        return "no"
    return "unknown"


def _answer_streak(streak_buckets: pd.DataFrame) -> str:
    if streak_buckets.empty:
        return "unknown"
    gate = str(streak_buckets["sample_gate"].iloc[0])
    if gate == GATE_INSUFFICIENT:
        return "unknown"
    long_ = streak_buckets.loc[streak_buckets["bucket"].astype(str).isin(["5+", "always_present"])]
    short = streak_buckets.loc[streak_buckets["bucket"].astype(str) == "1"]
    if long_.empty or short.empty:
        return "unknown"
    lm = float(long_["mean_excess"].mean())
    sm = float(short["mean_excess"].mean())
    if lm != lm or sm != sm:
        return "unknown"
    return "yes" if lm > sm else "no"


def _answer_soft(soft_cmp: pd.DataFrame) -> str:
    row = _row_horizon(soft_cmp, "5d")
    if row is None or int(row.get("n_soft_drop", 0) or 0) == 0 or int(row.get("n_rs90_ok", 0) or 0) == 0:
        return "unknown"
    if str(row.get("sample_gate")) == GATE_INSUFFICIENT:
        return "unknown"
    delta = float(row["delta_soft_minus_rs90"])
    if delta != delta:
        return "unknown"
    # negative delta → dropped names did worse → policy helped → yes
    return "yes" if delta < 0 else "no"


def one_line_summary(
    *,
    n_pool_days: int,
    n_5d_stamps: int,
    trust: str,
    agg: pd.DataFrame,
    soft_cmp: pd.DataFrame,
) -> str:
    med = "n/a"
    if not agg.empty:
        g = agg.loc[
            (agg["basket"].astype(str) == "median_plus") & (agg["horizon"].astype(str) == "5d")
        ]
        if not g.empty:
            med = _pct(float(g.iloc[0]["mean_excess"]))
    soft = "n/a"
    row = _row_horizon(soft_cmp, "5d")
    if row is not None:
        soft = _pct(float(row["mean_soft_drop"]))
    if trust == GATE_INSUFFICIENT:
        return (
            f"지금은 관측 {n_pool_days}일·5일 성적 stamp {n_5d_stamps}일 수준이라 "
            f"확정 평가가 아닙니다. (중앙값 이상 5일 {med}, soft 탈락 {soft} — 참고만)"
        )
    if trust == GATE_MONITOR:
        return (
            f"자료가 쌓이는 중입니다(관측 {n_pool_days}일). "
            f"중앙값 이상 바구니 5일 {med}, soft ceiling 탈락 {soft} — 추세만 보세요."
        )
    return (
        f"표본이 해석 가능한 수준입니다(관측 {n_pool_days}일). "
        f"중앙값 이상 바구니 5일 {med}, soft ceiling 탈락 {soft}."
    )


def interpret_soft_delta(delta: float | None, gate: str) -> str:
    if gate == GATE_INSUFFICIENT:
        return "아직 시험 횟수가 적어 판단 보류합니다."
    if delta is None or (isinstance(delta, float) and delta != delta):
        return "차이를 계산할 수 없습니다."
    if delta < 0:
        return "지금 신호는 규칙이 도움이 되는 쪽입니다(뺀 쪽이 더 못함)."
    if delta > 0:
        return "규칙이 좋은 종목을 잘못 잘랐을 수도 있습니다 — 표본을 더 모으세요."
    return "두 그룹 평균이 거의 같습니다."


def interpret_basket(mean: float | None, gate: str, *, basket_label: str = "중앙값 이상") -> str:
    if gate == GATE_INSUFFICIENT or mean is None or (isinstance(mean, float) and mean != mean):
        return f"{basket_label} 바구니 성적은 아직 참고 수준입니다(표본 부족)."
    direction = "높았습니다" if mean > 0 else "낮았습니다"
    return (
        f"{basket_label} 바구니가 5일 평균으로 시장보다 {_pct(mean)} "
        f"{direction}. 게이트={gate_ko(gate)}."
    )


# ── Page builders ─────────────────────────────────────────────────


def _page_cover(
    pdf: PdfPages,
    *,
    stamp: str,
    n_pool_days: int,
    n_fwd_ready_5d: int,
    n_5d_stamps: int,
    stamp_span: str,
    trust: str,
    summary: str,
    answers: dict[str, str],
) -> None:
    _setup()
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    as_of = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}" if len(stamp) == 8 else stamp
    fig.text(0.5, 0.90, "SEPA 모델 성적 보고서", ha="center", va="top", fontproperties=_fp(bold=True, size=24))
    fig.text(
        0.5, 0.82,
        f"기간 {stamp_span}  ·  생성 {as_of}  ·  관측 {n_pool_days}일",
        ha="center", va="top", fontproperties=_fp(size=11), color="#444",
    )
    badge = gate_ko(trust)
    badge_color = {
        GATE_INSUFFICIENT: "#b33a3a",
        GATE_MONITOR: "#b37a00",
        GATE_INTERPRET: "#2a7a4b",
    }.get(trust, "#555")
    fig.text(
        0.5, 0.74,
        f"신뢰 배지: {badge}",
        ha="center", va="top", fontproperties=_fp(bold=True, size=14), color=badge_color,
    )
    fig.text(
        0.08, 0.66,
        _wrap(summary, 62),
        ha="left", va="top", fontproperties=_fp(size=11), color="#222", linespacing=1.4,
    )

    questions = [
        ("우리가 고른 바구니가 시장보다 나았나?", answers.get("basket", "unknown")),
        ("리스트에 넣고 뺀 타이밍이 괜찮았나?", answers.get("timing", "unknown")),
        ("오래 남은 종목이 더 나았나?", answers.get("streak", "unknown")),
        ("soft ceiling으로 뺀 종목이 정말 못했나?", answers.get("soft", "unknown")),
    ]
    y0 = 0.48
    fig.text(0.08, y0 + 0.06, "오늘 질문 네 가지", ha="left", va="top", fontproperties=_fp(bold=True, size=12))
    for i, (q, ans) in enumerate(questions):
        y = y0 - i * 0.07
        fig.text(0.10, y, f"{i + 1}. {q}", ha="left", va="top", fontproperties=_fp(size=10.5))
        fig.text(
            0.88, y, ANSWER_KO.get(ans, ans),
            ha="right", va="top", fontproperties=_fp(bold=True, size=11),
            color="#2c5f7c" if ans == "yes" else ("#8b4513" if ans == "no" else "#888"),
        )

    fig.text(
        0.08, 0.14,
        f"큰 숫자  ·  관측 {n_pool_days}일  ·  5일 성적 준비 {n_fwd_ready_5d}건  ·  5일 stamp {n_5d_stamps}일",
        ha="left", va="bottom", fontproperties=_fp(size=10), color="#555",
    )
    _footer(fig, 1)
    pdf.savefig(fig)
    plt.close(fig)


def _page_scope(pdf: PdfPages) -> None:
    _setup()
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    fig.text(0.08, 0.90, "이 보고서가 보는 것 / 안 보는 것", ha="left", va="top", fontproperties=_fp(bold=True, size=16))
    fig.text(
        0.08, 0.80,
        _wrap(
            "비유: 매일 시험 본 답안지를 모아 중간 성적표를 만드는 일입니다. "
            "내일 점수를 맞히는 시험이 아닙니다.",
            60,
        ),
        ha="left", va="top", fontproperties=_fp(size=11), linespacing=1.35,
    )
    fig.text(0.08, 0.66, "본다", ha="left", va="top", fontproperties=_fp(bold=True, size=12), color="#2a7a4b")
    fig.text(
        0.08, 0.60,
        _wrap(
            "· 스크리너 규칙으로 이미 뽑힌 종목의 사후 성적 (A–D 본심판)\n"
            "· 시장(S&P500) 대비 초과수익 (5·10·21거래일)\n"
            "· soft ceiling 등 우리 규칙이 도움이 됐는지의힌트\n"
            "· (맥락) 오늘 Fund 구간의 최근 1년 종가 경로 — 예측 아님",
            58,
        ),
        ha="left", va="top", fontproperties=_fp(size=10.5), linespacing=1.45,
    )
    fig.text(0.08, 0.40, "안 본다", ha="left", va="top", fontproperties=_fp(bold=True, size=12), color="#b33a3a")
    fig.text(
        0.08, 0.34,
        _wrap(
            "· 내일 주가 예측  ·  자동매매 신호  ·  “이 종목 사라”\n"
            "· 표본이 적을 때 파라미터를 바꾸는 단정 권고\n"
            "· Fund 1년 추세만으로 규칙 변경(확증 아님)",
            58,
        ),
        ha="left", va="top", fontproperties=_fp(size=10.5), linespacing=1.45,
    )
    fig.text(0.08, 0.20, "용어 미니 사전", ha="left", va="top", fontproperties=_fp(bold=True, size=12))
    glossary = [
        ("바구니", "그날 규칙으로 뽑힌 종목 묶음"),
        ("시장보다 잘함", "S&P500보다 수익률이 높음(초과)"),
        ("중앙값 이상", "Fund 점수가 그날 후보 중위 이상(median+)"),
        ("soft ceiling", "RS는 높지만 Fund가 약해서 일부러 뺀 종목"),
        ("들어옴/나감", "sepaTop 편입(enter) / 편출(exit)"),
        ("Fund 구간 추세", "오늘 점수 버킷의 과거 1년 등가 종가 경로(맥락)"),
    ]
    y = 0.155
    for term, meaning in glossary:
        fig.text(0.10, y, term, ha="left", va="top", fontproperties=_fp(bold=True, size=9))
        fig.text(0.32, y, meaning, ha="left", va="top", fontproperties=_fp(size=9), color="#333")
        y -= 0.028
    _footer(fig, 2)
    pdf.savefig(fig)
    plt.close(fig)


def _embed_bar_page(
    pdf: PdfPages,
    *,
    page: int,
    title: str,
    subtitle: str,
    body: str,
    labels: list[str],
    values: list[float],
    ns: list[int] | None = None,
    colors: list[str] | None = None,
    empty_note: str | None = None,
) -> None:
    _setup()
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    fig.text(0.08, 0.92, title, ha="left", va="top", fontproperties=_fp(bold=True, size=15))
    fig.text(0.08, 0.86, subtitle, ha="left", va="top", fontproperties=_fp(size=10), color="#555")
    fig.text(
        0.08, 0.78,
        _wrap(body, 70),
        ha="left", va="top", fontproperties=_fp(size=10.5), linespacing=1.35,
    )
    ax = fig.add_axes([0.12, 0.18, 0.76, 0.48])
    if not labels or all(v != v for v in values):
        ax.axis("off")
        ax.text(
            0.5, 0.5, empty_note or "아직 그릴 표본이 없습니다.",
            ha="center", va="center", fontproperties=_fp(size=12), color="#888",
            transform=ax.transAxes,
        )
    else:
        cols = colors or ["#2c5f7c"] * len(labels)
        xs = np.arange(len(labels))
        ys = [0.0 if (v != v) else float(v) * 100 for v in values]
        ax.bar(xs, ys, color=cols, alpha=0.88)
        ax.axhline(0, color="#333", lw=0.8)
        ax.set_xticks(xs)
        ax.set_xticklabels(labels, fontproperties=_fp(size=9))
        ax.set_ylabel("시장 대비 초과 (%)", fontproperties=_fp(size=9))
        for label in ax.get_yticklabels():
            label.set_fontproperties(_fp(size=8))
        if ns:
            for i, (y, n) in enumerate(zip(ys, ns)):
                ax.text(i, y, f"n={n}", ha="center", va="bottom", fontsize=8)
        ax.grid(axis="y", alpha=0.3)
    _footer(fig, page)
    pdf.savefig(fig)
    plt.close(fig)


def _page_basket(pdf: PdfPages, agg: pd.DataFrame) -> None:
    g = pd.DataFrame()
    if not agg.empty:
        g = agg.loc[agg["horizon"].astype(str) == "5d"].copy()
    labels, values, ns, colors = [], [], [], []
    prefer = ["fund_pool", "median_plus", "fund_q4", "rs90_ok", "soft_drop"]
    if not g.empty:
        order = {b: i for i, b in enumerate(prefer)}
        g["_ord"] = g["basket"].astype(str).map(lambda x: order.get(x, 99))
        g = g.sort_values("_ord")
        labels = g["basket"].astype(str).tolist()
        values = [float(x) for x in g["mean_excess"].tolist()]
        ns = [int(x) for x in g["n_ready"].tolist()]
        colors = ["#8b4513" if b == "soft_drop" else "#2c5f7c" for b in labels]
    med_row = None
    if not g.empty:
        m = g.loc[g["basket"].astype(str) == "median_plus"]
        if not m.empty:
            med_row = m.iloc[0]
    gate = str(med_row["sample_gate"]) if med_row is not None else GATE_INSUFFICIENT
    mean = float(med_row["mean_excess"]) if med_row is not None else None
    body = interpret_basket(mean, gate)
    soft_warn = ""
    if not g.empty:
        soft = g.loc[g["basket"].astype(str) == "soft_drop"]
        if not soft.empty and float(soft.iloc[0]["mean_excess"]) == float(soft.iloc[0]["mean_excess"]):
            if float(soft.iloc[0]["mean_excess"]) < -0.005:
                soft_warn = " 주의: soft_drop 바구니가 유독 약합니다."
    _embed_bar_page(
        pdf,
        page=3,
        title="A. 우리가 고른 팀이 시장보다 잘했나?",
        subtitle=f"5일 바구니 평균 초과수익  ·  게이트 {gate_ko(gate)}",
        body=body + soft_warn,
        labels=labels,
        values=values,
        ns=ns,
        colors=colors,
        empty_note="5일 성적(ready)이 아직 채워지지 않았습니다. go를 반복하면 자동으로 쌓입니다.",
    )


def _page_soft(pdf: PdfPages, soft_cmp: pd.DataFrame) -> None:
    row = _row_horizon(soft_cmp, "5d")
    if row is None:
        labels, values, ns, colors = [], [], [], []
        gate = GATE_INSUFFICIENT
        delta = None
        soft_m = ok_m = None
        n_soft = n_ok = 0
    else:
        soft_m = float(row["mean_soft_drop"])
        ok_m = float(row["mean_rs90_ok"])
        delta = float(row["delta_soft_minus_rs90"])
        gate = str(row["sample_gate"])
        n_soft = int(row["n_soft_drop"])
        n_ok = int(row["n_rs90_ok"])
        labels = ["뺀 그룹\n(soft_drop)", "남긴 RS≥90\n(rs90_ok)"]
        values = [soft_m, ok_m]
        ns = [n_soft, n_ok]
        colors = ["#8b4513", "#2c5f7c"]
    interp = interpret_soft_delta(delta, gate)
    body = (
        f"【자료 {gate_ko(gate)}】 soft ceiling으로 뺀 종목의 5일 평균 성적은 "
        f"시장 대비 {_pct(soft_m)}였고, 통과한 RS≥90 그룹은 {_pct(ok_m)}였습니다. "
        f"차이(뺀−통과)는 {_pct(delta)}입니다. {interp}"
    )
    _setup()
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    fig.text(0.08, 0.92, "D. 일부러 뺀 종목, 빼길 잘했나?", ha="left", va="top", fontproperties=_fp(bold=True, size=15))
    fig.text(
        0.08, 0.86,
        "정책 핵심 검사  ·  soft_drop vs rs90_ok (5일)",
        ha="left", va="top", fontproperties=_fp(size=10), color="#555",
    )
    fig.text(0.08, 0.78, _wrap(body, 70), ha="left", va="top", fontproperties=_fp(size=10.5), linespacing=1.35)
    fig.text(
        0.5, 0.62,
        f"Δ (뺀 − 통과)  =  {_pct(delta)}",
        ha="center", va="center", fontproperties=_fp(bold=True, size=18), color="#2c5f7c",
    )
    ax = fig.add_axes([0.22, 0.16, 0.56, 0.38])
    if not labels:
        ax.axis("off")
        ax.text(
            0.5, 0.5, "soft_drop / rs90_ok ready 표본이 없습니다.",
            ha="center", va="center", fontproperties=_fp(size=12), color="#888",
            transform=ax.transAxes,
        )
    else:
        xs = np.arange(2)
        ys = [0.0 if v != v else v * 100 for v in values]
        ax.bar(xs, ys, color=colors, alpha=0.88)
        ax.axhline(0, color="#333", lw=0.8)
        ax.set_xticks(xs)
        ax.set_xticklabels(labels, fontproperties=_fp(size=9))
        ax.set_ylabel("시장 대비 초과 (%)", fontproperties=_fp(size=9))
        for label in ax.get_yticklabels():
            label.set_fontproperties(_fp(size=8))
        for i, (y, n) in enumerate(zip(ys, ns)):
            ax.text(i, y, f"n={n}", ha="center", va="bottom", fontsize=8)
        ax.grid(axis="y", alpha=0.3)
    _footer(fig, 4)
    pdf.savefig(fig)
    plt.close(fig)


def _page_events(pdf: PdfPages, event_agg: pd.DataFrame) -> None:
    labels, values, ns, colors = [], [], [], []
    gate = GATE_INSUFFICIENT
    body = "sepaTop 편입·편출 직후 5일 성적을 봅니다."
    if not event_agg.empty:
        g = event_agg.loc[event_agg["horizon"].astype(str) == "5d"]
        for action, color in (("enter", "#2c5f7c"), ("exit", "#8b4513")):
            row = g.loc[g["action"].astype(str) == action]
            if row.empty:
                continue
            r = row.iloc[0]
            labels.append("들어옴" if action == "enter" else "나감")
            values.append(float(r["mean_excess"]))
            ns.append(int(r["n_ready"]))
            colors.append(color)
            gate = str(r["sample_gate"]) if gate == GATE_INSUFFICIENT else gate
        if labels:
            body = (
                f"편입(들어옴) 직후 평균 {_pct(values[0] if labels else None)}, "
                f"편출(나감) 직후 평균 {_pct(values[1] if len(values) > 1 else None)}. "
                f"편입 + · 편출 − 이면 타이밍이 대체로 맞다는 약한 신호입니다. "
                f"(게이트 {gate_ko(gate)})"
            )
    _embed_bar_page(
        pdf,
        page=5,
        title="B. 넣고 뺀 직후 성적은?",
        subtitle="sepaTop enter / exit · 5일 초과수익",
        body=body,
        labels=labels,
        values=values,
        ns=ns,
        colors=colors,
        empty_note="편입·편출 이벤트 성적이 아직 없습니다.",
    )


def _page_streak(pdf: PdfPages, streak_buckets: pd.DataFrame) -> None:
    if streak_buckets.empty:
        body = "21일 성적이 아직 안 채워져 이 장은 다음 기회에 채웁니다. go를 반복하면 자동으로 준비됩니다."
        labels, values, ns = [], [], []
        gate = GATE_INSUFFICIENT
    else:
        gate = str(streak_buckets["sample_gate"].iloc[0])
        rho = float(streak_buckets["spearman_all"].iloc[0])
        body = (
            f"리스트에 오래 남은 종목과 단기 성적의 관계를 봅니다. "
            f"Spearman(체류, 21일 초과)={rho:.3f}. 게이트 {gate_ko(gate)}."
        )
        prefer = ["1", "2-4", "5+", "always_present"]
        labels, values, ns = [], [], []
        for b in prefer:
            g = streak_buckets.loc[streak_buckets["bucket"].astype(str) == b]
            if g.empty:
                continue
            r = g.iloc[0]
            labels.append("항상" if b == "always_present" else b)
            values.append(float(r["mean_excess"]))
            ns.append(int(r["n_ready"]))
    _embed_bar_page(
        pdf,
        page=6,
        title="C. 오래 붙어 있는 종목이 더 좋았나?",
        subtitle="median+ 체류 구간 × 21일 초과수익",
        body=body,
        labels=labels,
        values=values,
        ns=ns,
        empty_note="21일 성적이 아직 안 채워져 이 장은 다음 기회에.",
    )


def _page_fund_trend(
    pdf: PdfPages,
    *,
    context: dict | None,
    combined: pd.DataFrame | None = None,
    counts: dict[str, int] | None = None,
) -> None:
    """Interpretation layer: today's Fund buckets' 1y path (not a verdict)."""
    _setup()
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    fig.text(
        0.08, 0.93,
        "Fund 구간 1년 추세 — 해석 레이어 (본심판 아님)",
        ha="left", va="top", fontproperties=_fp(bold=True, size=15),
    )
    fig.text(
        0.08, 0.87,
        "오늘 점수 버킷 × 과거 1년 등가 종가 (기준 1000) · S&P500과 비교",
        ha="left", va="top", fontproperties=_fp(size=10), color="#555",
    )

    ctx = context or {}
    tip = str(ctx.get("tip") or "맥락 자료 없음.")
    fig.text(
        0.08, 0.80,
        _wrap(tip, 70),
        ha="left", va="top", fontproperties=_fp(size=10.5), color="#222", linespacing=1.35,
    )

    ax = fig.add_axes([0.10, 0.28, 0.80, 0.42])
    if combined is None or combined.empty:
        ax.axis("off")
        ax.text(
            0.5, 0.5,
            "Fund 구간 추세 시계열이 없습니다. (fundamental CSV·가격 캐시 필요)",
            ha="center", va="center", fontproperties=_fp(size=11), color="#888",
            transform=ax.transAxes,
        )
    else:
        import matplotlib.dates as mdates

        cmap = plt.get_cmap("tab10")
        from sepa.fund_score_trend import BUCKET_LABELS

        counts = counts or {}
        for i, label in enumerate([c for c in BUCKET_LABELS if c in combined.columns]):
            n = counts.get(label, 0)
            ax.plot(
                combined.index, combined[label],
                color=cmap(i % 10), lw=1.4, alpha=0.9,
                label=f"{label} (n={n})",
            )
        if "S&P500" in combined.columns:
            ax.plot(
                combined.index, combined["S&P500"],
                color="#1a1a1a", lw=2.4, label="S&P500", zorder=5,
            )
        ax.axhline(1000, color="#888", lw=0.7, ls="--", alpha=0.7)
        ax.set_ylabel("지수(기준 1000)", fontproperties=_fp(size=8))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        for lab in ax.get_xticklabels() + ax.get_yticklabels():
            lab.set_fontproperties(_fp(size=7))
        ax.legend(loc="upper left", ncol=3, prop=_fp(size=7), frameon=False)
        ax.grid(alpha=0.3)

    bullets = list(ctx.get("bullets") or [])
    y = 0.22
    for line in bullets[:6]:
        fig.text(
            0.08, y, "· " + _wrap(line, 72).replace("\n", " "),
            ha="left", va="top", fontproperties=_fp(size=8.5), color="#333",
        )
        y -= 0.028
    _footer(fig, 7)
    pdf.savefig(fig)
    plt.close(fig)


def _page_pool(pdf: PdfPages, pool_log: pd.DataFrame) -> None:
    _setup()
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    fig.text(0.08, 0.92, "후보 숫자가 너무 널뛰나?", ha="left", va="top", fontproperties=_fp(bold=True, size=15))
    fig.text(
        0.08, 0.86,
        "풀 크기 · 중앙값 이상 · Fund 중앙값 추이 (가벼운 안정성 점검)",
        ha="left", va="top", fontproperties=_fp(size=10), color="#555",
    )
    ax = fig.add_axes([0.10, 0.22, 0.80, 0.55])
    if pool_log.empty or "stamp" not in pool_log.columns:
        ax.axis("off")
        ax.text(
            0.5, 0.5, "daily_pool_log 가 없습니다.",
            ha="center", va="center", fontproperties=_fp(size=12), color="#888",
            transform=ax.transAxes,
        )
        note = "후보 규모 기록이 아직 없습니다."
    else:
        g = pool_log.sort_values("stamp").copy()
        x = np.arange(len(g))
        stamps = g["stamp"].astype(str).tolist()
        if "n_fund_pool" in g.columns:
            ax.plot(x, g["n_fund_pool"], "o-", label="Fund 풀", color="#2c5f7c")
        if "n_median_plus" in g.columns:
            ax.plot(x, g["n_median_plus"], "s-", label="중앙값 이상", color="#8b4513")
        ax.set_xticks(x)
        ax.set_xticklabels(stamps, rotation=45, ha="right", fontproperties=_fp(size=7))
        ax.set_ylabel("종목 수", fontproperties=_fp(size=9))
        for label in ax.get_yticklabels():
            label.set_fontproperties(_fp(size=8))
        ax.legend(prop=_fp(size=9))
        ax.grid(alpha=0.3)
        note = f"최근 {len(g)}일 기록. 하루 만에 크게 뛰면 데이터·유니버스 변화를 점검하세요."
        if "n_fund_pool" in g.columns and len(g) >= 2:
            deltas = g["n_fund_pool"].astype(float).diff().abs()
            if deltas.max() == deltas.max() and float(deltas.max()) >= 30:
                idx = int(deltas.idxmax())
                jump_stamp = str(g.loc[idx, "stamp"])
                note += f" 급변 후보일: {jump_stamp}."
    fig.text(0.08, 0.12, _wrap(note, 72), ha="left", va="top", fontproperties=_fp(size=10), color="#333")
    _footer(fig, 8)
    pdf.savefig(fig)
    plt.close(fig)


def _page_appendix(
    pdf: PdfPages,
    *,
    stamp: str,
    agg: pd.DataFrame,
    event_agg: pd.DataFrame,
    soft_cmp: pd.DataFrame,
    streak_buckets: pd.DataFrame,
) -> None:
    _setup()
    lines: list[str] = []
    lines.append("[A] 바구니 5일")
    if agg.empty:
        lines.append("  (없음)")
    else:
        g = agg.loc[agg["horizon"].astype(str) == "5d"]
        for r in g.itertuples():
            lines.append(
                f"  {r.basket}: mean {_pct(r.mean_excess)}  win {_pct(r.win_rate)}  "
                f"n={int(r.n_ready)}/{int(r.n_stamps)}d  [{r.sample_gate}]"
            )
    lines.append("[B] enter/exit 5일")
    if event_agg.empty:
        lines.append("  (없음)")
    else:
        g = event_agg.loc[event_agg["horizon"].astype(str) == "5d"]
        for r in g.itertuples():
            lines.append(
                f"  {r.action}: mean {_pct(r.mean_excess)}  win {_pct(r.win_rate)}  "
                f"n={int(r.n_ready)}  [{r.sample_gate}]"
            )
    lines.append("[C] streak 21일")
    if streak_buckets.empty:
        lines.append("  (없음)")
    else:
        for r in streak_buckets.itertuples():
            lines.append(
                f"  {r.bucket}: mean {_pct(r.mean_excess)}  n={int(r.n_ready)}"
            )
    lines.append("[D] soft vs rs90")
    if soft_cmp.empty:
        lines.append("  (없음)")
    else:
        for r in soft_cmp.itertuples():
            lines.append(
                f"  {r.horizon}: soft {_pct(r.mean_soft_drop)}  ok {_pct(r.mean_rs90_ok)}  "
                f"Δ {_pct(r.delta_soft_minus_rs90)}  [{r.sample_gate}]"
            )

    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    fig.text(0.08, 0.93, "부록 · 숫자 원표", ha="left", va="top", fontproperties=_fp(bold=True, size=15))
    fig.text(
        0.08, 0.88,
        f"stamp {stamp}  ·  ledger {LEDGER_VERSION}  ·  UTC {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        ha="left", va="top", fontproperties=_fp(size=9), color="#666",
    )
    y = 0.82
    for line in lines[:30]:
        fig.text(0.08, y, line, ha="left", va="top", fontproperties=_fp(size=8.5), color="#222")
        y -= 0.024
    fig.text(
        0.08, 0.10,
        "사용자 산출물은 이 PDF 하나입니다.",
        ha="left", va="bottom", fontproperties=_fp(size=9), color="#666",
    )
    _footer(fig, 9)
    pdf.savefig(fig)
    plt.close(fig)


def build_verify_pdf(
    out_path: Path,
    *,
    stamp: str,
    n_pool_days: int,
    agg: pd.DataFrame,
    event_agg: pd.DataFrame,
    streak_buckets: pd.DataFrame,
    soft_cmp: pd.DataFrame,
    pool_log: pd.DataFrame,
    fwd: pd.DataFrame | None = None,
    fund_trend_combined: pd.DataFrame | None = None,
    fund_trend_counts: dict[str, int] | None = None,
    fund_trend_context: dict | None = None,
) -> Path:
    """Write the 9-page Hangul verify PDF. Raises KoreanFontError if no Hangul font."""
    assert_korean_font_ready(context="검증 PDF")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_fwd_ready_5d = 0
    n_5d_stamps = 0
    if fwd is not None and not fwd.empty and "ready_5d" in fwd.columns:
        if fwd["ready_5d"].dtype == bool:
            ready = fwd.loc[fwd["ready_5d"]]
        else:
            ready = fwd.loc[fwd["ready_5d"].astype(str).str.lower().isin({"1", "true", "yes", "t"})]
        n_fwd_ready_5d = int(len(ready))
        if "stamp" in ready.columns and n_fwd_ready_5d:
            n_5d_stamps = int(ready["stamp"].nunique())
    if n_5d_stamps == 0 and not agg.empty:
        g = agg.loc[agg["horizon"].astype(str) == "5d"]
        if not g.empty:
            n_5d_stamps = int(g["n_stamps"].max())
            if n_fwd_ready_5d == 0:
                n_fwd_ready_5d = int(g["n_ready"].sum())

    if not pool_log.empty and "stamp" in pool_log.columns:
        stamps = sorted(pool_log["stamp"].astype(str).unique())
        stamp_span = f"{stamps[0]}–{stamps[-1]}" if stamps else stamp
    else:
        stamp_span = stamp

    trust = overall_trust_gate(
        agg=agg, event_agg=event_agg, soft_cmp=soft_cmp, streak_buckets=streak_buckets
    )
    summary = one_line_summary(
        n_pool_days=n_pool_days,
        n_5d_stamps=n_5d_stamps,
        trust=trust,
        agg=agg,
        soft_cmp=soft_cmp,
    )
    if fund_trend_context and fund_trend_context.get("tip"):
        summary = summary + "  " + str(fund_trend_context["tip"])

    answers = {
        "basket": _answer_basket(agg),
        "timing": _answer_timing(event_agg),
        "streak": _answer_streak(streak_buckets),
        "soft": _answer_soft(soft_cmp),
    }

    with PdfPages(out_path) as pdf:
        _page_cover(
            pdf,
            stamp=stamp,
            n_pool_days=n_pool_days,
            n_fwd_ready_5d=n_fwd_ready_5d,
            n_5d_stamps=n_5d_stamps,
            stamp_span=stamp_span,
            trust=trust,
            summary=summary,
            answers=answers,
        )
        _page_scope(pdf)
        _page_basket(pdf, agg)
        _page_soft(pdf, soft_cmp)
        _page_events(pdf, event_agg)
        _page_streak(pdf, streak_buckets)
        _page_fund_trend(
            pdf,
            context=fund_trend_context,
            combined=fund_trend_combined,
            counts=fund_trend_counts,
        )
        _page_pool(pdf, pool_log)
        _page_appendix(
            pdf,
            stamp=stamp,
            agg=agg,
            event_agg=event_agg,
            soft_cmp=soft_cmp,
            streak_buckets=streak_buckets,
        )

    published = publish(out_path)
    if published is not None:
        logger.info("verify PDF published: %s", published)
    return out_path


# ── GitHub Release ────────────────────────────────────────────────


def verify_release_tag(stamp: str) -> str:
    """Release tag (Hangul kept; URLs must percent-encode)."""
    return f"sepa-검증-{stamp}"


def verify_pdf_name(stamp: str) -> str:
    """ASCII-only asset filename — ``gh`` strips Hangul from release asset names."""
    return f"verify_report_{stamp}.pdf"


def verify_direct_download_url(repo: str, stamp: str, pdf_name: str | None = None) -> str:
    from urllib.parse import quote

    name = pdf_name or verify_pdf_name(stamp)
    tag = verify_release_tag(stamp)
    # quote tag (Hangul) but keep ASCII filename as-is
    return (
        f"https://github.com/{repo}/releases/download/"
        f"{quote(tag, safe='')}/{quote(name, safe='')}"
    )


def github_repo_slug() -> str | None:
    from sepa.anal_report import github_repo_slug as _slug

    return _slug()


def publish_verify_pdf_github_release(
    pdf_path: Path,
    *,
    stamp: str,
    repo: str | None = None,
) -> dict:
    """Upload verify PDF to GitHub Release tag ``sepa-검증-YYYYMMDD``.

    Asset label is always ASCII ``verify_report_YYYYMMDD.pdf`` so ``gh`` does not
    mangle Hangul filenames (previously became ``_YYYYMMDD.pdf`` → 404).
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return {"ok": False, "error": f"PDF missing: {pdf_path}"}
    if shutil.which("gh") is None:
        return {"ok": False, "error": "gh CLI not available"}

    repo = repo or github_repo_slug()
    if not repo:
        return {"ok": False, "error": "cannot resolve GitHub repo slug"}

    tag = verify_release_tag(stamp)
    asset_name = verify_pdf_name(stamp)
    title = f"SEPA 검증 보고서 {stamp}"
    as_of = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}" if len(stamp) == 8 else stamp
    download = verify_direct_download_url(repo, stamp, asset_name)
    notes = (
        f"SEPA `!검증` 성적 보고서 ({as_of}).\n\n"
        f"PDF: {download}\n"
        f"표본이 작을 때는 확증이 아닙니다.\n"
    )
    # Force ASCII display name via path#name (Hangul basenames get stripped by gh)
    asset = f"{pdf_path.resolve()}#{asset_name}"

    view = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if view.returncode != 0:
        created = subprocess.run(
            [
                "gh", "release", "create", tag,
                asset,
                "--repo", repo,
                "--title", title,
                "--notes", notes,
                "--latest=false",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if created.returncode != 0:
            return {
                "ok": False,
                "error": (created.stderr or created.stdout or "release create failed").strip(),
                "repo": repo,
                "tag": tag,
            }
    else:
        uploaded = subprocess.run(
            [
                "gh", "release", "upload", tag,
                asset,
                "--repo", repo,
                "--clobber",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if uploaded.returncode != 0:
            return {
                "ok": False,
                "error": (uploaded.stderr or uploaded.stdout or "release upload failed").strip(),
                "repo": repo,
                "tag": tag,
            }
        subprocess.run(
            ["gh", "release", "edit", tag, "--repo", repo, "--notes", notes],
            capture_output=True,
            text=True,
            timeout=60,
        )

    page = f"https://github.com/{repo}/releases/tag/{quote_tag(tag)}"
    return {
        "ok": True,
        "repo": repo,
        "tag": tag,
        "download_url": download,
        "release_url": page,
        "pdf_name": asset_name,
    }


def quote_tag(tag: str) -> str:
    from urllib.parse import quote

    return quote(tag, safe="")

