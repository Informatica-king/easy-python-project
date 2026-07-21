"""매크로 명령 디스패처 — `!명령어(...)` 한 줄로 SEPA 도구 실행.

터미널에서 `sepa`(또는 `python -m sepa.macro`)를 실행하면 대화형 프롬프트가
열리고, 아래처럼 입력하면 해당 도구가 즉시 실행된다.

    sepa> !tools                          # 도구 목록·사용법
    sepa> !sepa.chart("SNDK")             # 티커로 차트
    sepa> !sepa.chart("sandisk")          # 기업 이름으로도 가능
    sepa> !sepa.screener("full")          # 전 종목 Stage 2 스크리닝
    sepa> !sepa.vcp("NVDA,MSFT")          # shortlist VCP 타이밍

일회성 실행도 지원한다:

    $ sepa '!sepa.chart("sandisk")'
"""

from __future__ import annotations

import ast
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sepa.config import load_params

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "config/params.yaml"

_CMD_RE = re.compile(r"^\s*!?\s*([\w\.]+)\s*(?:\((.*)\))?\s*$", re.S)


class MacroError(Exception):
    """User-facing macro failure (bad syntax, unknown tool, ambiguous name)."""


# ──────────────────────────────────────────────────────────────────
# 명령 파서
# ──────────────────────────────────────────────────────────────────

def parse_command(line: str) -> tuple[str, list, dict]:
    """'!name(arg1, key=val)' -> (name, args, kwargs).

    인자는 따옴표 유무와 무관하게 허용한다: !sepa.chart(SNDK) == !sepa.chart("SNDK")
    """
    m = _CMD_RE.match(line)
    if not m:
        raise MacroError(f"명령을 해석할 수 없습니다: {line!r} — !tools 로 사용법을 확인하세요")
    name, args_str = m.group(1).lower(), (m.group(2) or "").strip()
    if not args_str:
        return name, [], {}
    try:
        return (name, *_parse_args_ast(args_str))
    except (SyntaxError, ValueError):
        return (name, *_parse_args_naive(args_str))


def _parse_args_ast(args_str: str) -> tuple[list, dict]:
    call = ast.parse(f"__f({args_str})", mode="eval").body
    assert isinstance(call, ast.Call)

    def value(node: ast.expr):
        if isinstance(node, ast.Name):  # 따옴표 없는 단어는 문자열로 취급
            return node.id
        return ast.literal_eval(node)

    args = [value(a) for a in call.args]
    kwargs = {kw.arg: value(kw.value) for kw in call.keywords if kw.arg}
    return args, kwargs


def _parse_args_naive(args_str: str) -> tuple[list, dict]:
    args: list = []
    kwargs: dict = {}
    for part in args_str.split(","):
        part = part.strip().strip("'\"")
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            kwargs[k.strip()] = v.strip().strip("'\"")
        else:
            args.append(part)
    return args, kwargs


# ──────────────────────────────────────────────────────────────────
# 티커/기업명 해석기
# ──────────────────────────────────────────────────────────────────

def resolve_ticker(query: str, names: dict[str, str]) -> str:
    """티커 또는 기업 이름(부분 일치)을 티커로 해석."""
    q = query.strip()
    if q.upper() in names:
        return q.upper()
    matches = {t: n for t, n in names.items() if q.lower() in n.lower()}
    if len(matches) == 1:
        return next(iter(matches))
    if not matches:
        raise MacroError(f"'{query}'에 해당하는 종목을 찾을 수 없습니다")
    # 여러 증권 유형(보통주/우선주 등)이 같은 회사명을 공유하면 짧은 티커(보통주) 우선
    tickers = sorted(matches, key=len)
    if len({matches[t] for t in tickers}) == 1:
        return tickers[0]
    listing = ", ".join(f"{t}({matches[t]})" for t in tickers[:8])
    raise MacroError(f"'{query}'가 모호합니다. 후보: {listing}")


def _load_names() -> dict[str, str]:
    """보통주만 대상으로 하는 티커→회사명 맵 (ETF·워런트 등 제외)."""
    from sepa.data import universe

    params = load_params(DEFAULT_CONFIG)
    listed = universe.fetch_nasdaq_listed(cache_dir=params.data.cache_dir)
    common = set(universe.common_stock_tickers(listed))
    names = universe.security_names(listed)
    return {t: n for t, n in names.items() if t in common}


# ──────────────────────────────────────────────────────────────────
# 도구 구현
# ──────────────────────────────────────────────────────────────────

def _tool_tools(args: list, kwargs: dict) -> None:
    print("\n=== 사용 가능한 도구 ===\n")
    for spec in REGISTRY:
        print(f"  {spec.usage}")
        print(f"      {spec.desc}\n")
    print("인자는 따옴표 없이도 됩니다: !sepa.chart(sandisk)")
    print("종료: !exit\n")


def _tool_screener(args: list, kwargs: dict) -> None:
    from sepa import screener

    argv = []
    for a in args:
        a = str(a)
        if a.lower() == "full":
            argv.append("--full")
        elif a.endswith((".yaml", ".yml")):
            argv += ["--universe", a]
        else:
            raise MacroError(f"알 수 없는 인자: {a!r} — 'full' 또는 유니버스 yaml 경로")
    if kwargs.get("as_of"):
        argv += ["--as-of", str(kwargs["as_of"])]
    if kwargs.get("no_update"):
        argv.append("--no-update")
    screener.main(argv)


def _tool_vcp(args: list, kwargs: dict) -> None:
    from sepa import vcp_timing

    if not args:
        raise MacroError('shortlist가 필요합니다: !sepa.vcp("NVDA,MSFT")')
    names = _load_names()
    tickers = [resolve_ticker(t, names) for t in str(args[0]).split(",") if t.strip()]
    argv = ["--tickers", ",".join(tickers)]
    if kwargs.get("as_of"):
        argv += ["--as-of", str(kwargs["as_of"])]
    if kwargs.get("no_update"):
        argv.append("--no-update")
    vcp_timing.main(argv)


def _tool_chart(args: list, kwargs: dict) -> None:
    from sepa import chart

    if not args:
        raise MacroError('종목이 필요합니다: !sepa.chart("SNDK") 또는 !sepa.chart(sandisk)')
    ticker = resolve_ticker(str(args[0]), _load_names())
    argv = ["--ticker", ticker]
    if kwargs.get("months"):
        argv += ["--months", str(kwargs["months"])]
    if kwargs.get("as_of"):
        argv += ["--as-of", str(kwargs["as_of"])]
    if kwargs.get("no_update"):
        argv.append("--no-update")
    chart.main(argv)


def _tool_update(args: list, kwargs: dict) -> None:
    from sepa.data import store, universe

    params = load_params(DEFAULT_CONFIG)
    listed = universe.fetch_nasdaq_listed(cache_dir=params.data.cache_dir)
    tickers = universe.common_stock_tickers(listed)
    print(f"나스닥 전 종목 {len(tickers)}개 증분 업데이트 시작...")
    ok, failed = store.bulk_update(tickers, params.data.cache_dir, params.data.lookback_years)
    print(f"완료: 성공 {len(ok)} / 실패 {len(failed)}")


def _tool_fundamental(args: list, kwargs: dict) -> None:
    from sepa import fundamental

    argv = ["--full"]
    for a in args:
        a = str(a)
        if a.lower() == "full":
            continue
        if a.endswith((".csv",)):
            argv = ["--from-stage2", a]
        else:
            raise MacroError(
                f"알 수 없는 인자: {a!r} — !sepa.fund() 또는 "
                f'!sepa.fund("reports/stage2_20260716.csv")'
            )
    if kwargs.get("as_of"):
        argv += ["--as-of", str(kwargs["as_of"])]
    if kwargs.get("no_update"):
        argv.append("--no-update")
    if kwargs.get("refresh"):
        argv.append("--refresh-fundamentals")
    fundamental.main(argv)


def _tool_analyze(args: list, kwargs: dict) -> None:
    from sepa import analyze

    argv: list[str] = []
    for a in args:
        a = str(a)
        if a.endswith(".csv"):
            argv += ["--from-fundamental", a]
        else:
            raise MacroError(
                f"알 수 없는 인자: {a!r} — !sepa.anal() 또는 "
                f'!sepa.anal("reports/fundamental_20260716.csv")'
            )
    if kwargs.get("refresh"):
        argv.append("--refresh-sectors")
    if kwargs.get("skip_sepatop"):
        argv.append("--skip-sepatop")
    if kwargs.get("sepatop_days"):
        argv += ["--sepatop-days", str(kwargs["sepatop_days"])]
    if kwargs.get("skip_sector_share"):
        argv.append("--skip-sector-share")
    if kwargs.get("sector_top_n"):
        argv += ["--sector-top-n", str(kwargs["sector_top_n"])]
    if kwargs.get("force_sector_week") or kwargs.get("week"):
        argv.append("--force-sector-week")
    if kwargs.get("force_sector_month") or kwargs.get("month"):
        argv.append("--force-sector-month")
    if kwargs.get("skip_pdf"):
        argv.append("--skip-pdf")
    if kwargs.get("skip_github_release"):
        argv.append("--skip-github-release")
    analyze.main(argv)


def _tool_sector_share(args: list, kwargs: dict) -> None:
    """On-demand sector share (+ optional forced week/month views)."""
    from sepa import sector_share

    argv: list[str] = []
    force_week = bool(kwargs.get("week") or kwargs.get("force_week"))
    force_month = bool(kwargs.get("month") or kwargs.get("force_month"))
    for a in args:
        a = str(a).lower()
        if a in ("week", "weekly", "주", "주간"):
            force_week = True
        elif a in ("month", "monthly", "월", "월간"):
            force_month = True
        elif a in ("all", "both"):
            force_week = True
            force_month = True
        elif a.endswith(".csv"):
            raise MacroError(
                "sectorShare 는 analyze 스냅샷을 사용합니다 — "
                "!sepa.sectorShare() / !sepa.sectorShare(week) / !sepa.sectorShare(month)"
            )
        else:
            raise MacroError(
                f"알 수 없는 인자: {a!r} — !sepa.sectorShare() | week | month | all"
            )
    if force_week:
        argv.append("--week")
    if force_month:
        argv.append("--month")
    if kwargs.get("top_n"):
        argv += ["--top-n", str(kwargs["top_n"])]
    sector_share.main(argv)


def _tool_sepatop(args: list, kwargs: dict) -> None:
    from sepa import sepatop

    argv: list[str] = []
    for a in args:
        a = str(a)
        if a.endswith(".csv"):
            argv += ["--from-fundamental", a]
        else:
            raise MacroError(
                f"알 수 없는 인자: {a!r} — !sepa.sepaTop() 또는 "
                f'!sepa.sepaTop("reports/fundamental_20260718.csv")'
            )
    if kwargs.get("lookback_days") or kwargs.get("days"):
        argv += ["--lookback-days", str(kwargs.get("lookback_days") or kwargs.get("days"))]
    sepatop.main(argv)


def _latest_report(pattern: str) -> Path | None:
    paths = sorted(Path("reports").glob(pattern))
    return paths[-1] if paths else None


def _tool_go(args: list, kwargs: dict) -> None:
    """Run scan(full) → fund → anal in order with clear section banners."""
    from datetime import datetime

    from sepa import analyze, fundamental, screener

    if args:
        raise MacroError("!sepa.go() 는 인자가 없습니다 — !sepa.go() 또는 !sepa.go")

    stamp = (kwargs.get("as_of") or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
    no_update = bool(kwargs.get("no_update"))

    def banner(step: int, total: int, title: str) -> None:
        print("\n" + "=" * 64)
        print(f"  SEPA GO  [{step}/{total}]  {title}")
        print("=" * 64 + "\n")

    print("\n" + "#" * 64)
    print("  SEPA GO — scan(full) → fund → anal")
    print("#" * 64)

    # 1) Stage 2 scan (full Nasdaq) — includes incremental price update unless no_update
    banner(1, 3, "!sepa.scan(full)")
    scan_argv = ["--full"]
    if kwargs.get("as_of"):
        scan_argv += ["--as-of", str(kwargs["as_of"])]
    if no_update:
        scan_argv.append("--no-update")
    screener.main(scan_argv)

    stage2 = Path(f"reports/stage2_{stamp}.csv")
    if not stage2.exists():
        stage2 = _latest_report("stage2_*.csv")
    if stage2 is None or not stage2.exists():
        raise MacroError("scan 후 stage2 리포트가 없습니다 — reports/stage2_*.csv 확인")

    # 2) Fundamental scores from that Stage 2 list (skip re-download / re-screen)
    banner(2, 3, "!sepa.fund()  ← Stage 2 결과 재사용")
    fund_argv = ["--from-stage2", str(stage2), "--no-update"]
    if kwargs.get("refresh"):
        fund_argv.append("--refresh-fundamentals")
    fundamental.main(fund_argv)

    fund_csv = Path(f"reports/fundamental_{stamp}.csv")
    if not fund_csv.exists():
        fund_csv = _latest_report("fundamental_*.csv")
    if fund_csv is None or not fund_csv.exists():
        raise MacroError("fund 후 fundamental 리포트가 없습니다 — reports/fundamental_*.csv 확인")

    # Copy-friendly median+ ticker export (also printed again inside anal)
    import pandas as pd

    from sepa.analyze import print_fund_median_copy_list

    fund_df = pd.read_csv(fund_csv)
    median_export = Path(f"reports/fund_median_tickers_{stamp}.txt")
    print_fund_median_copy_list(fund_df, out_path=median_export)

    # 3) Sector + RS×Fund analysis
    banner(3, 3, "!sepa.anal()")
    anal_argv = ["--from-fundamental", str(fund_csv)]
    if kwargs.get("refresh"):
        anal_argv.append("--refresh-sectors")
    analyze.main(anal_argv)

    print("\n" + "#" * 64)
    print("  SEPA GO 완료")
    print(f"  stage2 : {stage2}")
    print(f"  fund   : {fund_csv}")
    print(f"  median+: {median_export}")
    scatter = Path(f"reports/charts/analyze_scatter_{stamp}.png")
    sectors = Path(f"reports/charts/analyze_sectors_{stamp}.png")
    if not scatter.exists():
        found = _latest_report("charts/analyze_scatter_*.png")
        if found is not None:
            scatter = found
    if not sectors.exists():
        found = _latest_report("charts/analyze_sectors_*.png")
        if found is not None:
            sectors = found
    print(f"  charts : {sectors}")
    print(f"           {scatter}")
    print("#" * 64 + "\n")


@dataclass(frozen=True)
class MacroSpec:
    name: str
    usage: str
    desc: str
    fn: Callable[[list, dict], None]
    aliases: tuple[str, ...] = ()


REGISTRY: list[MacroSpec] = [
    MacroSpec(
        "tools", "!tools",
        "사용 가능한 도구 목록과 사용법 출력", _tool_tools, aliases=("help",),
    ),
    MacroSpec(
        "sepa.screener",
        '!sepa.scan()  |  !sepa.scan(full)  |  !sepa.screener(full, as_of=2025-02-18)',
        "Stage 2 스크리너 — 인자 없으면 파일럿, 'full'이면 나스닥 전 종목",
        _tool_screener,
        aliases=("screener", "sepa.stage2", "sepa.scan", "scan"),
    ),
    MacroSpec(
        "sepa.vcp", '!sepa.vcp("NVDA,MSFT")  |  !sepa.vcp(sandisk, as_of=2025-02-18)',
        "shortlist VCP 진입 타이밍 — BREAKOUT/WATCHLIST/FORMING/EXTENDED",
        _tool_vcp, aliases=("vcp", "sepa.vcp_timing"),
    ),
    MacroSpec(
        "sepa.chart", '!sepa.chart("SNDK")  |  !sepa.chart(sandisk, months=12)',
        "SEPA 일봉 분석 차트 — SMA·52주·ZigZag·Trend Template 스코어카드",
        _tool_chart, aliases=("chart",),
    ),
    MacroSpec(
        "sepa.update", "!sepa.update()",
        "나스닥 전 종목 가격 데이터 증분 업데이트",
        _tool_update, aliases=("update",),
    ),
    MacroSpec(
        "sepa.fundamental",
        '!sepa.fund()  |  !sepa.fund("reports/stage2_20260716.csv")  |  !sepa.fundamental()',
        "Stage 2·RS≥80 정량 펀더멘털 점수 — fund_score 내림차순, RS 병기",
        _tool_fundamental,
        aliases=("fundamental", "sepa.fund", "fund"),
    ),
    MacroSpec(
        "sepa.analyze",
        '!sepa.anal()  |  !sepa.anal("reports/fundamental_20260716.csv")  |  !sepa.analyze()',
        "섹터/테마·Fund·시가총액 + RS×Fund + 섹터점유율(전체/Fund≥40 꺾은선) + sepaTop + PDF 묶음",
        _tool_analyze,
        aliases=("analyze", "sepa.anal", "anal"),
    ),
    MacroSpec(
        "sepa.sectorshare",
        "!sepa.sectorShare()  |  !sepa.sectorShare(week)  |  !sepa.sectorShare(month)  |  !sepa.sectorShare(all)",
        "Fund 섹터 점유율 시계열 단독 실행. week/month/all 로 주·월 비교 강제 표시",
        _tool_sector_share,
        aliases=("sectorshare", "sepa.sectorShare", "sepa.sector", "sector"),
    ),
    MacroSpec(
        "sepa.sepatop",
        '!sepa.sepaTop()  |  !sepa.sepatop()  |  !sepa.sepaTop("reports/fundamental_20260718.csv")',
        "sepaTop 시총가중 지수 vs NASDAQ/S&P/SOX 등 + 편입·편출·체류기간",
        _tool_sepatop,
        aliases=("sepatop", "sepa.sepaTop", "sepa.top", "top"),
    ),
    MacroSpec(
        "sepa.go",
        "!sepa.go()  |  !sepa.go",
        "일일 파이프라인 — scan(full) → fund → anal(+sectorShare+sepaTop) 을 순서대로 실행·출력. Fund 중앙값 이상 티커를 쉼표 목록으로 출력·export",
        _tool_go,
        aliases=("go",),
    ),
]

_LOOKUP: dict[str, MacroSpec] = {}
for _spec in REGISTRY:
    _LOOKUP[_spec.name] = _spec
    for _a in _spec.aliases:
        _LOOKUP[_a] = _spec


def run_line(line: str) -> int:
    """한 줄 매크로 실행. 성공 0, 실패 1."""
    line = line.strip()
    if not line:
        return 0
    try:
        name, args, kwargs = parse_command(line)
        if name in ("exit", "quit", "q"):
            raise EOFError
        spec = _LOOKUP.get(name)
        if spec is None:
            raise MacroError(f"알 수 없는 도구: !{name} — !tools 로 목록을 확인하세요")
        spec.fn(args, kwargs)
        return 0
    except MacroError as exc:
        print(f"[오류] {exc}")
        return 1


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        return run_line(" ".join(argv))

    print("SEPA 매크로 콘솔 — !tools 입력 시 도구 목록, !exit 입력 시 종료")
    while True:
        try:
            line = input("sepa> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        try:
            run_line(line)
        except EOFError:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
