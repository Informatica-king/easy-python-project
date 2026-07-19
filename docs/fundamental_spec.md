# 펀더멘털 점수 명세서 — `sepa.fundamental`

> **문서 버전**: v2.0  
> **상태**: 가중치 확정 (2026-07-19 이벤트 스터디 → 사용자 승인)  
> **근거**: `docs/fund_weight_study_spec.md`, `reports/fund_study/`  
> **용도**: Stage 2 · RS≥80 기업에 대한 정량 펀더멘털 순위

---

## 1. 역할

`!sepa.fundamental()` 실행 시:

1. 나스닥 Stage 2(Trend Template 8조건) 기업을 산출
2. **RS ≥ 80** 인 종목만 대상으로 함
3. 기업별 **펀더멘털 점수(0~100)** 를 계산해 **내림차순** 출력 (RS 병기)

---

## 2. 확정 가중치 (2026-07-19)

이벤트 스터디(실적 day0−1→+3 시장조정 수익률, Spearman·직교화)에서  
**양수 상관 요인만** `w ∝ max(0, corr)` 로 정규화한 값(정수 반올림, 합 100).

| ID | 요소 | 가중치 | 연구 팩터 |
|---|---|---:|---|
| **S** | EPS Surprise | **47** | `eps_surprise` |
| **E** | 영업이익률 YoY 변화 | **25** | `opm_d` (없으면 NPM Δ) |
| **D** | 매출 YoY 가속도 | **14** | `sales_dyoy` |
| **B** | EPS YoY 가속도 | **14** | `eps_dyoy` |
| ~~A~~ | ~~EPS YoY 수준~~ | ~~0~~ | 연구에서 Δ에 패배 |
| ~~C~~ | ~~매출 YoY 수준~~ | ~~0~~ | 연구에서 Δ에 패배 |
| ~~G~~ | ~~ROE~~ | ~~0~~ | phase-1 제외 |

합계 원점수 **100** → `fund_score = raw` (0~100).

---

## 3. 채점 규칙

### 3.1 Surprise (S)

| Surprise (컨센서스 대비) | 배점 |
|---|---|
| &lt; 0% (미스) | 0 |
| 0 ~ +20% | 0 ~ 100% 선형 |
| ≥ +20% | 만점 |

데이터: yfinance earnings dates (캐시 `data/fund_study/earnings_dates/` 우선). 결측 → 0.

### 3.2 ΔYoY 가속도 (B, D)

최신 인접 분기 `YoY_t − YoY_{t−1}`.

| ΔYoY | 배점 |
|---|---|
| ≤ 0 | 0 |
| 0 ~ +25pp | 0 ~ 100% 선형 |
| ≥ +25pp | 만점 |

### 3.3 마진 YoY 변화 (E)

`OPM_t − OPM_{t−4}` (없으면 NPM). 단위: 비율 포인트.

| Δ마진 | 배점 |
|---|---|
| ≤ 0 | 0 |
| 0 ~ +5pp | 0 ~ 100% 선형 |
| ≥ +5pp | 만점 |

### 3.4 최종 점수

```
raw = S + B + D + E          # 최대 100
fund_score = raw / 100 × 100 # = raw
```

결측 항목은 0점.

---

## 4. 데이터 소스

| 항목 | 1순위 | 폴백 |
|---|---|---|
| 분기 EPS / 매출 / 영업이익 / 순이익 | SEC EDGAR companyfacts | yfinance quarterly income |
| EPS Surprise | yfinance earnings dates (+로컬 캐시) | 0점 |

- YoY는 캘린더 분기 프레임(`CY2025Q1` vs `CY2024Q1`)
- OPM = OperatingIncome / Revenue

---

## 5. 출력

```
회사명-TICKER  (RS xx.x | Fund yy.y)
```

CSV: `reports/fundamental_YYYYMMDD.csv`  
컬럼: `s_surprise`, `b_eps_dyoy`, `d_sales_dyoy`, `e_opm_delta`, …

---

## 6. 변경 이력

| 일자 | 내용 |
|---|---|
| 2026-07-16 | v1.0 A25/B20/C15/D10/E15/G5 (합 90) |
| 2026-07-19 | v2.0 S47/E25/D14/B14 (합 100); Surprise·OPMΔ·연속 ΔYoY |
