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


def _tool_backtest(args: list, kwargs: dict) -> None:
    from sepa import backtest

    argv = []
    if kwargs.get("recompute"):
        argv.append("--recompute-signals")
    if kwargs.get("start"):
        argv += ["--start", str(kwargs["start"])]
    backtest.main(argv)


def _tool_update(args: list, kwargs: dict) -> None:
    from sepa.data import store, universe

    params = load_params(DEFAULT_CONFIG)
    listed = universe.fetch_nasdaq_listed(cache_dir=params.data.cache_dir)
    tickers = universe.common_stock_tickers(listed)
    print(f"나스닥 전 종목 {len(tickers)}개 증분 업데이트 시작...")
    ok, failed = store.bulk_update(tickers, params.data.cache_dir, params.data.lookback_years)
    print(f"완료: 성공 {len(ok)} / 실패 {len(failed)}")


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
        "sepa.screener", '!sepa.screener()  |  !sepa.screener("full")  |  !sepa.screener(full, as_of=2025-02-18)',
        "Stage 2 스크리너 — 인자 없으면 파일럿 유니버스, 'full'이면 나스닥 전 종목. 결과: 회사명-티커 리스트",
        _tool_screener, aliases=("screener", "sepa.stage2"),
    ),
    MacroSpec(
        "sepa.vcp", '!sepa.vcp("NVDA,MSFT")  |  !sepa.vcp(sandisk, as_of=2025-02-18)',
        "shortlist VCP 진입 타이밍 — BREAKOUT/WATCHLIST/FORMING/EXTENDED 시그널. 기업 이름도 인식",
        _tool_vcp, aliases=("vcp", "sepa.vcp_timing"),
    ),
    MacroSpec(
        "sepa.chart", '!sepa.chart("SNDK")  |  !sepa.chart(sandisk, months=12)',
        "SEPA 일봉 분석 차트 — 추세선(SMA 50/150/200, 52주 고저) + Trend Template 스코어카드 + VCP 구조",
        _tool_chart, aliases=("chart",),
    ),
    MacroSpec(
        "sepa.backtest", "!sepa.backtest()  |  !sepa.backtest(recompute=True)",
        "가상투자 백테스트 — 진입 변형 3종 × 청산 그리드 36조합 탐색 후 수익률/샤프/MDD별 최적 모델 리포트",
        _tool_backtest, aliases=("backtest",),
    ),
    MacroSpec(
        "sepa.update", "!sepa.update()",
        "나스닥 전 종목 가격 데이터 증분 업데이트 (스크리너 실행 없이 데이터만)",
        _tool_update, aliases=("update",),
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
