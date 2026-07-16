# SEPA Screener — Minervini Stage 2 + VCP

마크 미너비니의 SEPA 전략을 정량화한 나스닥 종목 분석 도구입니다.
자동 매매가 아닌 **추천 전용**이며, 최종 판단은 사용자가 직접 합니다.
(개인 투자 참고용 · 비상업)

두 개의 독립 도구로 구성됩니다.

1. **Stage 2 스크리너**: Trend Template 8조건을 통과한 상승 추세 기업을
   "회사명-티커" 리스트로 출력 → 사용자가 펀더멘털을 직접 검토·순위화
2. **VCP 타이밍**: 검토를 마친 상위권 shortlist에 대해서만 VCP(변동성 수축
   패턴) 셋업과 피벗 돌파 타이밍을 계산

## 설치

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
```

## 사용법

### 1단계 — Stage 2 스크리닝

```bash
python -m sepa.screener                                   # 파일럿 유니버스(10종목)
python -m sepa.screener --universe config/universe.yaml   # 유니버스 파일 지정
python -m sepa.screener --as-of 2025-02-18                # 과거 시점 기준 (검증용)
python -m sepa.screener --no-update                       # 캐시만 사용
```

출력: "회사명-티커" 리스트(RS 순위 내림차순) + `reports/stage2_YYYYMMDD.csv`,
`reports/diagnostics_YYYYMMDD.csv`(전 종목 조건별 진단).

### 2단계 — shortlist VCP 타이밍

```bash
python -m sepa.vcp_timing --tickers NVDA,MSFT,AVGO
python -m sepa.vcp_timing --tickers-file shortlist.txt --as-of 2025-02-18
```

출력: 종목별 시그널 테이블 + `reports/vcp_YYYYMMDD.csv`.

| 시그널 | 의미 |
|---|---|
| `BREAKOUT` | 피벗을 평균 1.5배 이상 거래량으로 돌파 — 진입 후보 |
| `WATCHLIST` | 셋업 완성, 피벗 근접 — 돌파 감시 |
| `FORMING` | 수축 구조는 유효하나 아직 피벗에서 먼 상태 |
| `EXTENDED` | 피벗 돌파 후 5% 초과 이격 — 추격 금지 |
| `NONE` | 유효한 VCP 셋업 없음 (`note`에 사유) |

## 구조

```
config/          # 파라미터(params.yaml)·유니버스(universe.yaml)
src/sepa/
  data/          # 데이터 수집 (yfinance→Stooq 폴백, Parquet 캐시, 나스닥 유니버스·회사명)
  indicators.py  # SMA, 52주 고저, RS 순위
  trend_template.py  # Stage 2 판별 (8조건)
  screener.py    # [도구 1] Stage 2 스크리너 — "회사명-티커" 리스트
  vcp.py         # VCP 탐지기 (ZigZag 수축 분석 + 거래량 고갈)
  vcp_timing.py  # [도구 2] shortlist VCP 진입 타이밍
docs/            # 개발 노트, 전략 명세서
tests/           # 단위 테스트 (합성 데이터 기반)
```

전략 정의와 파라미터 의미는 `docs/strategy_spec.md`, 개발 로드맵은
`docs/DEVELOPMENT_NOTE.md`를 참고하세요.

## 테스트

```bash
.venv/bin/python -m pytest tests/
```
