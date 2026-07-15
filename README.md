# SEPA Screener — Minervini Stage 2 + VCP

마크 미너비니의 SEPA 전략을 정량화한 나스닥 종목 스크리너입니다.
Trend Template 8조건으로 Stage 2 상승 추세 종목을 거르고, VCP(변동성 수축 패턴)
셋업을 탐지하여 매수 후보를 추천합니다. 자동 매매가 아닌 **추천 전용**이며,
최종 판단은 사용자가 직접 합니다. (개인 투자 참고용 · 비상업)

## 설치

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
```

## 사용법

```bash
# 파일럿 유니버스(나스닥 상위 10개) 스크리닝
python -m sepa.screener

# 옵션
python -m sepa.screener --universe config/universe.yaml   # 유니버스 파일 지정
python -m sepa.screener --as-of 2025-02-18                # 과거 시점 기준 스크리닝 (검증용)
python -m sepa.screener --no-update                       # 캐시만 사용 (다운로드 생략)
```

결과는 콘솔 요약과 함께 `reports/screen_YYYYMMDD.csv`(셋업 목록),
`reports/diagnostics_YYYYMMDD.csv`(전 종목 진단)로 저장됩니다.

### 시그널 종류

| 시그널 | 의미 |
|---|---|
| `BREAKOUT` | 피벗을 평균 1.5배 이상 거래량으로 돌파 — 진입 후보 |
| `WATCHLIST` | 셋업 완성, 피벗 근접 — 돌파 감시 |
| `FORMING` | 수축 구조는 유효하나 아직 피벗에서 먼 상태 |
| `EXTENDED` | 피벗 돌파 후 5% 초과 이격 — 추격 금지 |

## 구조

```
config/          # 파라미터(params.yaml)·유니버스(universe.yaml)
src/sepa/
  data/          # 데이터 수집 (yfinance→Stooq 폴백, Parquet 캐시, 나스닥 유니버스)
  indicators.py  # SMA, 52주 고저, RS 순위
  trend_template.py  # Stage 2 판별 (8조건)
  vcp.py         # VCP 탐지기 (ZigZag 수축 분석 + 거래량 고갈)
  screener.py    # CLI 파이프라인
docs/            # 개발 노트, 전략 명세서
tests/           # 단위 테스트 (합성 데이터 기반)
```

전략 정의와 파라미터 의미는 `docs/strategy_spec.md`, 개발 로드맵은
`docs/DEVELOPMENT_NOTE.md`를 참고하세요.

## 테스트

```bash
.venv/bin/python -m pytest tests/
```
