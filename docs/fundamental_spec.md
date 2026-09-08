# 펀더멘털 점수 명세서 — `sepa.fundamental`

> **문서 버전**: v2.1  
> **상태**: **프로덕션 확정** (2026-07-26)  
> **가중치**: v2.0과 동일 — S47 / E25 / D14 / B14 (재스터디 ±2pt → 변경 없음)  
> **추가**: quality 레이어 (OPM 백필 · NPM 페널티 · B/D accel 게이트)  
> **근거**: `docs/fund_weight_study_spec.md`, `docs/fund_model_comparison_20260726.md`  
> **용도**: Stage 2 · RS≥70 기업에 대한 정량 펀더멘털 순위 (RS≥90은 Fund≥중앙값 조건부)

---

## 1. 역할

`!sepa.fundamental()` 실행 시:

1. 나스닥 Stage 2(Trend Template 8조건) 기업을 산출
2. **RS ≥ 70** 인 종목만 대상으로 함
3. 후보 필터(Fund>0, 시총≥$1B) 후, **RS ≥ 90** 은 **Fund ≥ 풀 중앙값**일 때만 유지 (소프트 상한)
4. 기업별 **펀더멘털 점수(0~100)** 를 계산해 **내림차순** 출력 (동점이면 RS)

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
컬럼: `s_surprise`, `b_eps_dyoy`, `d_sales_dyoy`, `e_opm_delta`,
`fund_raw`, `b/d/e_quality`, `b/d/e_raw`, `b/d/e_status`, `margin_source`, …

---

## 6. 변경 이력

| 일자 | 내용 |
|---|---|
| 2026-07-16 | v1.0 A25/B20/C15/D10/E15/G5 (합 90) |
| 2026-07-19 | v2.0 S47/E25/D14/B14 (합 100); Surprise·OPMΔ·연속 ΔYoY |
| 2026-07-26 | v2.1 quality 레이어 코드 반영 (가중치 동일) |
| 2026-07-26 | **v2.1 프로덕션 확정** — 재스터디 S47/E27/B14/D12 (±2) → 가중치 유지, quality on 기본 |

### v2.1 quality (요약) — **live 기본 ON** (`quality_enabled: true`)

```
fund_raw = S + B·qB + D·qD + E·qE
fund_score = fund_raw   # 가중 합 100 기준, quality로 헤드룸 남김 허용
```

| 계수 | 규칙 |
|---|---|
| qE | opm=1.0 · npm=0.6 · none=0 |
| qB / qD | accel_n&lt;2 → 0 · =2 → 0.7 · ≥3 → 1.0 |
| S | \|surprise\| winsor 1.0 (100%) 후 기존 곡선 |

폴백 순서: **SEC OPM → yfinance OPM → NPM(페널티) → none**.  
캐시에 OPM이 없으면 `load_quarterly`가 SEC로 자동 백필한다.  
끄려면 `config/params.yaml`에서 `quality_enabled: false`.
