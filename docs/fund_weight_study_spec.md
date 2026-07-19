# Fund 가중치 재설계 연구 스펙 (확정)

> **상태**: 확정 (2026-07-19)  
> **ADV**: ≥ **$5M/일** (초기 $10M 제안에서 변경)  
> **적용**: 연구 리포트 → 사용자 승인 후 `sepa.fund` 반영 (**2026-07-19 반영 완료**: S47/E25/D14/B14)

---

## 한 줄

**earnings date(없으면 filing date) = day0**,  
**P(day0−1 종가) → P(day0+3 종가)** 의 **시장조정 수익률**과  
**요인 수준+Δ 중 설명력 높은 쪽**의 상관으로  
**가중치 · 채점곡선 · 예외규칙**을 재산출한다.  
(단순 수익률은 참고용)

---

## 1. 목적

- 목표: 가중치 + 채점 곡선 + 예외규칙 확정
- 적용: 리포트 먼저, **승인 후** 코드 반영

## 2. 팩터

### 메인
| ID | 정의 |
|----|------|
| EPS_YoY | 분기 diluted EPS YoY |
| EPS_ΔYoY | 이번 YoY − 직전 공시 YoY |
| Sales_YoY | 분기 매출 YoY |
| Sales_ΔYoY | 이번 매출 YoY − 직전 YoY |
| Margin_Δ | NPM_Δ · OpMargin_Δ 둘 다 측정 후 하나 채택 |
| Surprise | EPS/Sales 컨센서스 surprise (있으면) |

### 검증
- QoQ / ΔQoQ 스피드 팩터 → 결과 보고 채택 여부 결정

### 제외·보조
- ROE: 1차 제외
- 연속 분기 수 n: 메인 X 아님, 보너스/예외용

## 3. 유니버스

- 나스닥 **보통주** (ETF/ETN 제외)
- 시총 **≥ $1B**
- ADV **≥ $5M/일** (최근 60거래일 평균 달러거래대금)
- **ADR 제외**
- 기간: **최근 10년** (이후 확장)
- Stage2·RS≥80: 메인 아님, **비교군**만

## 4. 이벤트·수익률

- day0 = 실적 발표일 (없으면 SEC filing)
- 장후 발표도 **그 날짜 = day0**
- 수익률: **close(day0−1) → close(day0+3)**
- 메인: `r_i − r_NASDAQ` (동구간)
- 단순 수익률: 참고
- 보조 창: 없음

## 5. 상관·비중

- X: 수준 + Δ 둘 다 → 요인별 우세쪽 채택
- 상관: Pearson + Spearman, **메인 Spearman**
- 중복: 부분상관/직교화
- 비중: 직교화 후 `w ∝ max(0, corr)` 정규화 + 분위수 반응 로버스트
- (−)상관: 역채점 후보 표시 → 별도 합의
- 과적합: **연도별 안정성 필수**

## 6. 필터·예외

| 항목 | 처리 |
|------|------|
| 이벤트 ±3일 거래대금 하위 30% | 제외 |
| 거래정지/결측 | 이벤트 제외 |
| YoY/QoQ 폭발치 (EPS≈0 등) | 제외 |
| 일회성 마진 왜곡 | 샘플 포함 + 예외 draft 플래그 |
| ADR | 제외 |
| 계절 업종 QoQ | 검토 |

## 7. 산출물

- `reports/fund_study/` 이벤트 패널 CSV
- 요인별 상관표 / 반응 차트
- 현행 vs 신규 가중치 비교
- YoY vs QoQ 비교
- 예외규칙 draft

## 8. CLI

```bash
# 1) 가격 10년 백필 먼저 (ADV>=$5M 후보, forward-only 캐시로는 불가)
python -m sepa.fund_study --backfill-prices

# 2) 연구 실행
python -m sepa.fund_study --pilot 50          # 빠른 파일럿
python -m sepa.fund_study --pilot 200
python -m sepa.fund_study --full             # 유니버스 전체 (장시간)
```
