# AGENTS.md

## 프로젝트 개요

마크 미너비니 SEPA 전략 기반 나스닥 스크리너 (개인 투자 참고용 · 비상업).
전략 정의는 `docs/strategy_spec.md`, 로드맵·결정 로그는 `docs/DEVELOPMENT_NOTE.md`,
데이터 구조는 `docs/data_structure.md` 참조.

## 환경

- Python 3.11+ / 가상환경 `.venv` (`pip install -r requirements.txt && pip install -e .`)
- 테스트: `python -m pytest tests/` (네트워크 불필요, 합성 데이터 기반)
- 가격 데이터 캐시는 `data/raw/`(git 제외) — 없으면 도구 실행 시 자동 수집

## `!` 매크로 컨벤션 (중요)

사용자가 채팅에 `!`로 시작하는 명령을 입력하면 (예: `!tools`,
`!sepa.chart("SNDK")`, `!sepa.screener(full)`), 별도 설명 없이 즉시 아래처럼
실행하고 결과를 보여줄 것:

```bash
.venv/bin/sepa '!입력받은 명령 그대로'
```

- 도구 목록·사용법: `.venv/bin/sepa '!tools'`
- 매크로 정의·파서·티커/기업명 해석기: `src/sepa/macro.py` (`REGISTRY`)
- 새 도구를 추가하면 `REGISTRY`에 등록해 `!tools`에 노출시킬 것
- 차트 등 이미지 산출물이 생기면 사용자에게 보여줄 것 (`reports/charts/`)

## Cursor Cloud specific instructions

- CLI 도구 중심 프로젝트라 GUI 테스트는 불필요. 셸 실행 결과와 생성된
  차트 이미지(`reports/charts/`)로 검증할 것
- Stooq는 데이터센터 IP에서 JS 챌린지로 차단됨 — yfinance 폴백 체인이
  자동 처리하므로 무시해도 됨
- 전 종목 수집(`!sepa.update()` 또는 `--full`)은 약 3분 소요
