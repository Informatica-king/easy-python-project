# 전략 명세서 — SEPA 스크리너 (Stage 2 + VCP)

> **문서 버전**: v0.2
> **상태**: 파라미터 권장값으로 확정 (2026-07-15 사용자 승인). 구현 완료 — `src/sepa/` 참조
> **용도**: 개인 투자 참고용 (비상업). 상업적 사용 없음
> **최종 수정일**: 2026-07-15

---

## 1. 확정된 범위 (Decision Record)

| # | 결정 사항 | 내용 |
|---|---|---|
| D1 | 펀더멘털 제외 | 펀더멘털 분석은 별도 봇으로 분리. 본 봇은 **기술적 지표만** 사용 |
| D2 | 봇의 역할 | 자동 매매가 아닌 **스크리너(추천기)**. 나스닥 전 종목 중 Stage 2 진입 + VCP 셋업 종목을 탐지하여 사용자가 직접 확인할 수 있게 리포트 |
| D3 | VCP 알고리즘 | 본 문서 §4의 알고리즘 채택. 파라미터 수치는 사용자가 확정 |
| D4 | 데이터 소스 | 무료 소스 사용: yfinance(1순위) + Stooq(백업), 유니버스는 Nasdaq Trader 공식 심볼 파일 |

**운용 워크플로우 (D8, 2026-07-15 확정)**: Stage 2 탐지와 VCP 타이밍은 별도 도구로 분리 운용한다.

1. **Stage 2 스크리너** (`python -m sepa.screener`): Trend Template 8조건을 통과한 기업을 **"회사명-티커"** 리스트로 출력 (RS 순위 내림차순)
2. **사용자 수동 검토**: Stage 2 리스트의 펀더멘털을 직접 확인하고 순위화 → 상위권 shortlist 확정
3. **VCP 타이밍 도구** (`python -m sepa.vcp_timing --tickers ...`): shortlist에 대해서만 VCP 셋업/피벗 돌파 시그널(`BREAKOUT`/`WATCHLIST`/`FORMING`/`EXTENDED`) 계산

---

## 2. 파이프라인 개요

```
[도구 1] Stage 2 스크리너 (sepa.screener)
  나스닥 심볼 목록 (ETF 제외)
        │
        ▼
  일봉 OHLCV 수집·정제 → 지표 계산 (SMA, 52주 고저, RS 순위)
        │
        ▼
  Trend Template 필터 (8조건 전부 통과)
        │
        ▼
  "회사명-티커" 리스트 출력  ──►  [사용자] 펀더멘털 검토·순위화
                                        │
                                        ▼
[도구 2] VCP 타이밍 (sepa.vcp_timing)   상위권 shortlist
  VCP 탐지기 (수축 구조 + 거래량 고갈)
        │
        ▼
  피벗 돌파 감시 → BREAKOUT / WATCHLIST / FORMING / EXTENDED
```

주: VCP 타이밍 도구는 Trend Template을 게이트로 쓰지 않는다(입력이 이미 검토된 shortlist이므로). 참고용 `trend_ok` 컬럼만 제공하며, RS 순위는 유니버스 상대값이라 소수 shortlist에서는 무의미하므로 이 도구의 추세 확인에서는 조건 8을 생략한다.

---

## 3. Stage 2 필터 — Trend Template

### 3.1 조건 정의 (T일 종가 기준)

| # | 조건 | 수식 |
|---|---|---|
| 1 | 주가가 장기 이평선 위 | `close > SMA150 AND close > SMA200` |
| 2 | 중기 > 장기 | `SMA150 > SMA200` |
| 3 | 200일선 상승 중 | `SMA200(T) > SMA200(T - trend_days)` |
| 4 | 완전 정배열 | `SMA50 > SMA150 > SMA200` |
| 5 | 주가가 50일선 위 | `close > SMA50` |
| 6 | 52주 저점 대비 상승 | `close >= low_52w * (1 + low_52w_min_pct)` |
| 7 | 52주 고점 근접 | `close >= high_52w * (1 - high_52w_max_pct)` |
| 8 | RS 순위 | `rs_rank >= rs_rank_min` |

### 3.2 Trend Template 파라미터

| 파라미터 | 권장 기본값 | 설명 |
|---|---|---|
| `trend_days` | 21 (1개월) | 200일선 상승 판정 기간. 미너비니 권장은 4~5개월(84~105일) |
| `low_52w_min_pct` | 0.30 | 52주 저점 대비 최소 상승률 |
| `high_52w_max_pct` | 0.25 | 52주 고점 대비 허용 이격 |
| `rs_rank_min` | 80 | RS 백분위 순위 하한 (미너비니 선호 80~90) |

### 3.3 RS(상대강도) 순위 계산

IBD 방식을 근사한 **가중 수익률 백분위 순위**를 사용한다.

```
rs_raw = 0.4 × ret_63d + 0.2 × ret_126d + 0.2 × ret_189d + 0.2 × ret_252d
rs_rank = 유니버스 내 rs_raw의 백분위 순위 (0~100)
```

- `ret_Nd` = N거래일 수익률. 최근 3개월(63일)에 2배 가중 — 최근 모멘텀 중시
- 유니버스 전체를 함께 계산해야 하므로, 소수 종목 테스트 시에는 나스닥100 등 확장 유니버스로 순위를 산출하거나 임시로 조건 8을 비활성화한다

---

## 4. VCP 탐지 알고리즘 (제안)

### 4.1 설계 개요

스윙 포인트(고점/저점) 기반 수축 분석 방식을 제안한다. 직관적이고 파라미터의 의미가 미너비니의 서술("각 수축이 직전의 절반 수준으로 얕아지고, 거래량이 마른다")과 1:1로 대응되어 튜닝이 쉽다.

3단계로 구성된다: **① 베이스 식별 → ② 수축 구조 검증 → ③ 거래량 고갈 검증**

### 4.2 알고리즘 상세

**① 베이스 식별**

1. 최근 `base_max_weeks` 주 내의 최고가를 **베이스 고점**(base high, 좌측 피크)으로 정의
2. 베이스 고점 이후 현재까지를 베이스 구간으로 삼되, 구간 길이가 `base_min_weeks` 이상이어야 함
3. 베이스 전체 최대 낙폭(고점 대비 최저가)이 `max_base_depth` 이하 — 너무 깊은 베이스는 실패 확률이 높음

**② 수축 구조 검증**

1. 베이스 구간에서 스윙 고점/저점 추출:
   ZigZag 방식 — 직전 극점 대비 `swing_threshold` % 이상 반대 방향으로 움직였을 때만 새 스윙 포인트로 인정 (노이즈 필터링)
2. 연속된 (스윙고점 → 스윙저점) 쌍을 **수축(contraction)** 으로 정의, 깊이 = `(고점 − 저점) / 고점`
3. **소수축 병합** *(실데이터 검증 중 추가)*: 수축 사이의 반등이 직전 하락폭의 `contraction_min_retrace` 미만이면 별개 수축이 아니라 같은 하락의 연장으로 보고 직전 수축에 병합 (고점 유지, 더 깊은 저점 채택). ZigZag만으로는 실제 차트의 잔파동이 수축 7~20개로 과다 집계되어 유효 셋업이 전부 기각되는 문제를 해결
4. 판정 조건:
   - 수축 횟수가 `min_contractions` ~ `max_contractions` 범위
   - 각 수축 깊이 ≤ 직전 수축 깊이 × `contraction_decay` (순차적 수축 — 미너비니의 "절반 룰"은 decay=0.5, 관대하게는 0.75)
   - 마지막 수축 깊이 ≤ `final_contraction_max` (타이트할수록 좋음)

**③ 거래량 고갈 검증**

1. 마지막 수축 구간의 최근 `dryup_days` 일 평균 거래량 ≤ 50일 평균 거래량 × `dryup_ratio`
2. (선택) 베이스 내 수축별 평균 거래량이 감소 추세인지 확인 (`volume_trend_check`)

**④ 피벗과 시그널 판정**

1. **피벗** = 마지막 수축의 스윙 고점
2. **Watchlist 시그널**: ①~③ 모두 통과 AND 현재가가 피벗 대비 `-watch_zone_pct` 이내 (돌파 임박)
3. **Breakout 시그널**: 당일 종가(또는 고가)가 `피벗 × (1 + pivot_buffer)` 상회 AND 당일 거래량 ≥ 50일 평균 × `breakout_vol_mult`
4. **추격 금지 필터**: 종가가 피벗 대비 `max_extension` 초과 상승 시 "이미 이탈(extended)"로 표기하고 추천에서 제외

### 4.3 의사코드

```python
def detect_vcp(df: pd.DataFrame, p: VCPParams) -> VCPResult:
    base = find_base(df, p.base_max_weeks, p.base_min_weeks, p.max_base_depth)
    if base is None:
        return no_setup()

    swings = zigzag(base, threshold=p.swing_threshold)
    contractions = pair_contractions(swings)       # [(depth, start, end), ...]

    ok = (
        p.min_contractions <= len(contractions) <= p.max_contractions
        and all(c2.depth <= c1.depth * p.contraction_decay
                for c1, c2 in pairwise(contractions))
        and contractions[-1].depth <= p.final_contraction_max
        and volume_dryup(df, contractions[-1], p.dryup_days, p.dryup_ratio)
    )
    if not ok:
        return no_setup()

    pivot = contractions[-1].swing_high
    return classify_signal(df, pivot, p)           # WATCHLIST / BREAKOUT / EXTENDED
```

### 4.4 VCP 파라미터 표 — **수치 확정 필요**

> "권장 기본값"은 미너비니의 서술과 일반적인 VCP 구현 관례에서 도출한 제안값이다. **"확정값" 열을 채워 주면 그 값으로 구현한다.** 비워두면 권장값으로 시작한 후 Phase 5에서 백테스트로 조정한다.

| 파라미터 | 의미 | 권장 기본값 | 합리적 범위 | 확정값 |
|---|---|---|---|---|
| `base_min_weeks` | 베이스 최소 기간 | 5주 | 3~8주 | |
| `base_max_weeks` | 베이스 최대 기간 | 26주 | 10~65주 | |
| `max_base_depth` | 베이스 전체 최대 낙폭 | 35% | 25~50% | |
| `swing_threshold` | 스윙 포인트 인정 최소 반전폭 | 3% | 2~5% | |
| `min_contractions` | 최소 수축 횟수 | 2회 | 2~3회 | |
| `max_contractions` | 최대 수축 횟수 | 6회 | 4~6회 | |
| `contraction_decay` | 수축 깊이 감소 비율 상한 | 0.75 | 0.5(엄격)~1.0(감소만 요구) | 0.75 |
| `contraction_min_retrace` | 별개 수축 인정 최소 반등 비율 (소수축 병합) | 0.5 | 0.3~0.7 | 0.5 |
| `final_contraction_max` | 마지막 수축 최대 깊이 | 10% | 3~15% | |
| `dryup_days` | 거래량 고갈 측정 기간 | 5일 | 3~10일 | |
| `dryup_ratio` | 고갈 판정: 50일 평균 대비 비율 | 0.6 | 0.4~0.8 | |
| `pivot_buffer` | 돌파 인정 여유폭 | 0.1% | 0~0.5% | |
| `breakout_vol_mult` | 돌파일 거래량 배수 (50일 평균 대비) | 1.5배 | 1.2~2.0배 | |
| `watch_zone_pct` | Watchlist 인정: 피벗 아래 근접 범위 | 5% | 3~10% | |
| `max_extension` | 추격 금지: 피벗 위 최대 이격 | 5% | 3~8% | |

### 4.5 알려진 한계와 대응

- ZigZag 방식은 `swing_threshold`에 민감 → Phase 3에서 실제 차트와 육안 대조하며 1차 튜닝, Phase 5에서 백테스트로 최종 조정
- 손잡이 달린 컵(Cup-with-Handle) 등 유사 패턴도 수축 구조로 잡힐 수 있음 → 스크리너 목적상 오히려 장점 (사용자가 최종 판단)
- 갭이 큰 종목·저유동성 종목에서 오탐 발생 가능 → 유니버스 필터(§6)로 사전 차단

---

## 5. 출력 명세

### 5.1 Stage 2 스크리너 (`sepa.screener`)

- **콘솔**: "회사명-티커" 리스트 (RS 순위 내림차순), 예: `NVIDIA Corporation-NVDA`
- **`reports/stage2_YYYYMMDD.csv`**: `ticker, name, close, rs_rank`
- **`reports/diagnostics_YYYYMMDD.csv`**: 전 종목의 조건별 통과/실패 내역
- 회사명은 Nasdaq Trader 심볼 파일의 Security Name에서 증권 유형 접미사(" - Common Stock" 등)를 제거해 사용. 오프라인 실행을 위해 로컬 캐시 유지

### 5.2 VCP 타이밍 (`sepa.vcp_timing`) — `reports/vcp_YYYYMMDD.csv`

| 필드 | 설명 |
|---|---|
| `ticker` | 종목 식별 |
| `signal` | `BREAKOUT` / `WATCHLIST` / `FORMING` / `EXTENDED` / `NONE` |
| `close`, `pivot`, `dist_to_pivot_pct` | 현재가, 피벗 가격, 피벗까지 거리 |
| `trend_ok` | Trend Template(조건 8 제외) 통과 여부 — 참고용 |
| `base_weeks`, `footprint` | 베이스 기간, 미너비니식 표기 (예: `12W 18/9/4 3T`) |
| `final_depth_pct`, `dryup_ratio` | 마지막 수축 깊이, 실제 거래량 고갈 비율 |
| `volume_vs_avg` | 당일 거래량 / 50일 평균 (돌파 확인용) |
| `note` | 시그널 근거 또는 셋업 불성립 사유 |

형식: CSV + 콘솔 요약 테이블 (추후 차트 이미지 자동 생성 확장 가능)

---

## 6. 데이터 소스 계획 (무료)

### 6.1 유니버스 목록 — Nasdaq Trader 공식 심볼 파일

- URL: `https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt` (공식, 무료, 매일 갱신)
- 파이프(`|`) 구분 텍스트. **`ETF` 플래그 컬럼으로 ETF 제외**, `Test Issue` 플래그로 테스트 종목 제외
- 5자리 티커의 마지막 글자로 우선주·워런트 등 파생 증권 필터링 가능 (예: W=워런트, R=라이트)

### 6.2 일봉 OHLCV — 2중 소스 전략

| 순위 | 소스 | 방식 | 장점 | 단점 |
|---|---|---|---|---|
| 1순위 | **yfinance** (Yahoo Finance) | Python 라이브러리, 키 불필요 | 수정주가(`auto_adjust`) 지원, 배치 다운로드, 긴 히스토리 | 비공식 API — 야후 사이트 개편 시 일시 장애 이력(2025.2), 과도 호출 시 레이트리밋 |
| 백업 | **Stooq** | CSV 엔드포인트 (`https://stooq.com/q/d/l/?s={ticker}.us&i=d`), 키 불필요 | 매우 단순·안정, 수십 년 히스토리 | 일일 다운로드 한도 존재, 배당 미반영 가능성 → 검증 필요 |

**운영 방식**:

- 수집 계층을 `DataSource` 인터페이스로 추상화 — yfinance 실패 시 Stooq로 자동 폴백, 추후 유료 API 교체도 용이
- **로컬 캐시 필수**: 종목별 Parquet에 저장 후 증분 업데이트(마지막 저장일 이후만 요청) — 전 종목 재다운로드 방지 및 레이트리밋 회피
- 배치 간 지연(sleep)·지수 백오프 재시도·실패 종목 로그
- 나스닥 전 종목(~3,000개) 최초 수집: yfinance 배치 다운로드로 실행. 이후 일일 증분 업데이트는 부담이 크지 않음

**무료 소스 공통 유의사항**:

- 수정주가 정합성을 신뢰하기 전에 검증 — 액면분할 이력이 있는 종목(예: NVDA, TSLA) 몇 개를 두 소스에서 교차 대조
- 본 프로젝트는 개인 연구·비상업 용도로 확정(2026-07-15)되어 무료 소스 사용에 문제 없음
- Alpha Vantage 무료 티어(일 25회 호출)는 전 종목 수집에 부적합하여 제외
- **Stooq 접근 제한 확인(2026-07-15)**: 데이터센터 IP에서는 Stooq가 JS 챌린지로 차단됨(로컬 PC에서는 정상 동작 예상). 폴백 체인은 이 경우를 자동 처리하며 yfinance만으로 수집 완료

---

## 7. 유니버스 필터 (D9, 2026-07-16 확정)

전 종목 스크리닝(`--full`) 시 Trend Template 평가 전에 적용하는 사전 필터:

| 파라미터 | 값 | 근거 |
|---|---|---|
| `min_price` | $10 | 미너비니의 저가주 회피 원칙 |
| `min_avg_dollar_volume` | $10M (50일 평균) | 기관 수급이 가능한 유동성 하한 |

2026-07-16 전 종목 실행 기준 퍼널: 3,277 수집 → 2,879(히스토리 ≥280d) → 951(유동성) → 101 Stage 2.

## 8. 미결정 사항

1. Trend Template의 `trend_days`(현재 1개월 vs 미너비니 권장 4~5개월), `rs_rank_min`(현재 80) — Phase 5 백테스트에서 함께 검토
