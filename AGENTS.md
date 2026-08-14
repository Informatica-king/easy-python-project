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
`!sepa.go()`, `!sepa.scan(full)`, `!sepa.fund()`, `!sepa.anal()`,
`!sepa.chart("SNDK")`), 별도 설명 없이 즉시 아래처럼
실행하고 결과를 보여줄 것:

```bash
.venv/bin/sepa '!입력받은 명령 그대로'
```

- 도구 목록·사용법: `.venv/bin/sepa '!tools'`
- 매크로 정의·파서·티커/기업명 해석기: `src/sepa/macro.py` (`REGISTRY`)
- 짧은 별칭: `sepa.scan`(=screener), `sepa.fund`(=fundamental), `sepa.anal`(=analyze), `sepa.go`(scan→fund→anal)
- `!sepa.go()` = 나스닥 full scan → fund → anal 일괄 실행. 구간별 배너로 구분된 출력을 그대로 보여 줄 것.
  끝나면 Artifacts 차트 링크도 안내할 것.
- 새 도구를 추가하면 `REGISTRY`에 등록해 `!tools`에 노출시킬 것
- 차트 이미지: 데스크톱에서는 `Read`로 PNG를 열어 채팅에 표시 시도.
  **Android/모바일 앱에서는 인라인 이미지가 안 보이는 경우가 많음** →
  반드시 `/opt/cursor/artifacts/`에 복사하고, 사용자에게
  **이 에이전트 실행 화면의 Artifacts(첨부/산출물)** 에서
  `analyze_sectors_*.png` / `analyze_scatter_*.png` /
  `analyze_fund_hist_*.png` / `analyze_mcap_hist_*.png` 를 열어보라고 안내할 것.
  가능하면 PR 본문에 `<img src="/opt/cursor/artifacts/...">` 로도 올려
  공개 미리보기 URL을 확보할 것.
- `!sepa.anal()` / `!sepa.fund()` 후보 필터: **Fund=0** 또는 **시총 <$1B**(미확인 포함) 제외
- 펀더멘털 점수 스펙: `docs/fundamental_spec.md` (`!sepa.fund`)

## 결과 제시 규칙 (사용자 지정)

- 스크리너 결과를 채팅에 제시할 때 "상위 N개" 같은 임의 절단 금지.
  **RS 90 이상은 전부 나열**하고, 전체 리스트는 RS 점수를 함께 표기해
  내림차순으로 제시할 것 (긴 나머지 구간은 아티팩트 참조 가능)
- **`!sepa.go()` Fund 중앙값 이상(median+) 티커 복사용 문자열 — 필수**:
  go가 끝날 때마다 Fund ≥ 중앙값 티커를 **쉼표 구분 한 줄로 전부** 출력할 것.
  생략·말줄임(`…`)·샘플링·상위 N개 절단 금지. 파일
  `reports/fund_median_tickers_YYYYMMDD.txt`와 채팅/콘솔 모두 동일 전체 문자열.
  에이전트 요약에서도 이 한 줄은 **반드시 전문을 그대로** 제시할 것.
- **analyze PDF 한글 폰트 — 필수**: `fonts-nanum`(또는 WQY/Noto CJK) 없으면
  PDF 한글이 □로 깨진다. `sepa.fonts.assert_korean_font_ready`가 go 시작·PDF
  생성 시 검사하고, 없으면 apt 설치를 시도한다. 깨진 PDF를 릴리즈하지 말 것.
- **성능 검증 장기 프레임**: `!sepa.go`마다 `reports/perf/` 패널 자동 갱신
  (`sepa.perf_ledger`). 요약·검증은 `!검증` (= `!sepa.perf_study()`) →
  **한글 8쪽 PDF** `verify_report_YYYYMMDD.pdf` + Release `sepa-검증-YYYYMMDD`
  다운로드 링크 (에셋 파일명은 ASCII — `gh`가 한글 파일명을 깨뜨림). 스키마:
  `docs/perf_study_framework.md` · 양식: `docs/verify_report_design.md`.
  표본이 작을 때는 확증이 아님을 명시할 것.
- **빠진 go 날짜 채우기**: `!sepa.fill_gaps()` — 분석용 CSV만 빠르게 채움
  (릴리즈 복원 우선, 없으면 as-of scan+fund+membership+perf). PDF/차트/metrics
  없음. 선택적으로 `!sepa.go(fill_gaps=1)`. 문서: `docs/gap_fill_plan.md`.

## Cursor Cloud specific instructions

- CLI 도구 중심 프로젝트라 GUI 테스트는 불필요. 셸 실행 결과와 생성된
  차트 이미지(`reports/charts/`)로 검증할 것
- Stooq는 데이터센터 IP에서 JS 챌린지로 차단됨 — yfinance 폴백 체인이
  자동 처리하므로 무시해도 됨
- 전 종목 수집(`!sepa.update()` 또는 `--full`)은 약 3분 소요
