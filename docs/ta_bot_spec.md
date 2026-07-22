# 기술적 분석(TA) 봇 — 효율 설계 & MVP 스펙

> 기준일: 2026-07-21  
> 목표: **연산·네트워크 비용 최소화**하면서 진입/청산 보조 스코어 제공

---

## 1. 비용이 큰 곳 (우선순위)

| 순위 | 비용 | 대응 |
|---|---|---|
| 1 | 나스닥 전종목(~3,300) 다운로드·스크리닝 | **TA는 절대 full scan 안 함** |
| 2 | 티커별 HTTP(yfinance) | 기존 `data/raw/*.parquet` **증분만**, 당일 캐시면 `--no-update` |
| 3 | 차트 PNG 렌더 | **기본 OFF** — 표만 출력, `--chart`일 때만 |
| 4 | 유니버스 상대 RS 순위 | TA에서 **제외** (전종목 로드 필요). 절대 모멘텀만 사용 |
| 5 | 긴 시계열 rolling | 로드 후 **최근 `tail_bars`(기본 280)** 만 지표 계산 |

지표 자체(EMA/RSI/ATR)는 종목 10개×280봉이면 무시 가능. 병목은 네트워크·전종목이다.

---

## 2. 실행 유니버스 (좁게)

기본 입력만 허용:

1. 사용자가 준 티커 (`!sepa.ta("ECPG,NESR,NEO")`)
2. 없으면 `config/ta_watchlist.yaml` (보유+이벤트 리저브+관심, ≤20)

`!sepa.update()` / `!sepa.scan(full)` 와 **분리**. TA는 shortlist 전용.

---

## 3. 파이프라인 (1-pass)

```
tickers (≤20)
  → store.load (증분 or no-update)
  → df.iloc[-tail_bars:]          # 메모리·rolling 축소
  → vectorized features (1회)
  → 4축 스코어 0–100 + action
  → CSV + 채팅 표
  → (옵션) 차트
```

### 4축 (절대값, cross-section 없음)

| 축 | 입력 | 비고 |
|---|---|---|
| Trend | close vs EMA20/50, EMA20>EMA50 | SMA150/200 불필요 → 웜업 짧음 |
| Momentum | RSI14, 20일 수익률 | MACD는 옵션(기본 ON, 비용 작음) |
| Volatility | ATR14% | 손절 거리·사이징 힌트 |
| Setup | EMA20 이격, vol vs 20일평균 | 눌림/돌파 힌트 |

판정: `신규금지` / `분할OK` / `홀드` / `대기` / `축소검토`

---

## 4. 데이터 의존

- **필수**: `data/raw/{TICKER}.parquet` (SEPA 동일 스키마 OHLCV)
- **불필요(MVP)**: fundamentals, RS 전종목, 분봉, 옵션 IV
- 캐시 없으면 해당 티커만 fetch (배치 가능하나 MVP는 기존 `get_history`)

---

## 5. CLI / 매크로

```bash
sepa '!sepa.ta("ECPG,ASTH,NESR,NEO,AMRX")'
sepa '!sepa.ta(ECPG,NESR, no_update=1)'      # 네트워크 0
python -m sepa.ta_bot --tickers ECPG,NESR --no-update
python -m sepa.ta_bot --watchlist             # ta_watchlist.yaml
```

출력: `reports/ta_YYYYMMDD.csv` + 콘솔 표. 차트는 `--chart`만.

---

## 6. 하지 않을 것 (초기)

- 전종목 TA 스캔
- 피처를 parquet에 상시 저장 (파라미터 바뀌면 폐기 비용 > 재계산)
- ML / 패턴 매칭 / 분봉
- 자동매매

---

## 7. 포트 훅 (EARN_D5 · BAND · NO_ADD · STOP · TP)

TA 점수는 유지하고 **action만** 덮어씀 (`ta_action`에 순수 TA 보존).

| 훅 | 조건 | 효과 |
|---|---|---|
| `EARN_D5` | `earn−5일 ≤ as_of ≤ earn` | `분할OK` → `대기` |
| `NO_ADD` | `no_add: true` | `분할OK` → `대기` |
| `BAND` | `close ∉ [lo,hi]` | `분할OK` → `대기`; 밴드 안이면 entry∩band |
| `STOP` | `close ≤ stop` | → `축소검토` |
| `TP` | `close ≥ tp1` (tp2면 이유 표기) | → `익절검토` |

설정:
- `config/ta_watchlist.yaml` — TA 훅 필드
- `config/portfolio_watch.yaml` — 보유·익절/손절 시나리오 (병합, 충돌 시 portfolio 우선)

출력 컬럼: `ta_action`(순수 TA) / `action`(최종) / `override` / `reason`.  
`--no-hooks` 로 비활성.

## 8. 한국어 명령 · 심층분석 연동

- 명령 계약: `docs/korean_commands.md`
- 엔트리: `python -m sepa.tech_analysis` / `!sepa.ta` / 사용자 말 `기술적분석(...)`
- `심층분석` 종료 시 `after_deep_analysis(chase_rows)` → 스냅샷 + 자동 TA

## 9. 다음 (미승인 · 보류)

- PT 프리미엄 캡, 현금 사이징
- VCP/Stage2 점수 합치기, 자동매매
