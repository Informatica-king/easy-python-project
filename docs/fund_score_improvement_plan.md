# Fund 점수 개선 개발안 (v2 → v2.1)

> **작성일**: 2026-07-26  
> **근거**: `!sepa.anal` 모델 지표 1–7 + 라이브 `fundamental_20260725` 진단  
> **현행 스펙**: `docs/fundamental_spec.md` (v2.0 · S47/E25/D14/B14)  
> **연구 스펙**: `docs/fund_weight_study_spec.md`  
> **원칙**: 가중치를 먼저 건드리지 않는다. **데이터 신뢰도 → 채점 규칙 → 역할 분리 → 재스터디** 순.

---

## 0. 한 줄 목표

Fund를 “매일 높은 점수가 곧 알파”가 아니라  
**(1) 신뢰 가능한 실적 품질 신호** + **(2) 실적 이벤트 국면에서만 검증된 가점**으로 재정의한다.

---

## 1. 현황 진단 요약 (개선 입력)

| 관찰 | 의미 | 개발 함의 |
|---|---|---|
| Top25 점수 중 S ≈ 58% | 서프라이즈 과의존 | S 만점 캡·곡선 재검토는 **데이터 개선 후** |
| E: OPM 1 / NPM 64 / none 13 | E25점이 사실상 NPM 대리 | OPM 커버·폴백 페널티 필수 |
| B/D n≥2 ≈ 3–5% | 가속도가 거의 안 쌓임 | 깊이 부족 시 미채점/캡 |
| RS×Fund ρ ≈ −0.14 | 모멘텀과 펀더 거의 비정렬 | 결합 신호 과신 금지 |
| Q4≤Q1 (+1d/+5d, 7스냅샷) | 일상 단기 예측력 미검증 | 검증 국면을 실적일로 분리 |
| sepaTop 1Y ≫ 벤치 | 추세 유니버스는 강함 | Fund는 **가점/필터**, 엔진 교체 아님 |

---

## 2. 범위 / 비범위

### 한다 (In scope)
- E·B·D **데이터 품질·커버리지·결측 규칙**
- 채점 **신뢰도 가중**(소스·시계열 깊이)
- Fund **사용 국면** 분리 (일상 vs 실적 이벤트)
- 재검증 파이프라인 (이벤트 스터디 + 일상 분위 수익)
- anal PDF 지표로 **개선 전후 A/B**

### 안 한다 (Out of scope · 1차)
- Stage2 / RS 임계 재설계
- sepaTop 가중 방식 변경
- 새 팩터 대량 추가(ROE 부활, QoQ 등) — 2차 후보만
- 프로덕션 가중치 즉각 변경 (스터디·승인 전)

---

## 3. 성공 기준 (Done이면)

1. **커버리지**
   - 후보군 E: `margin_source=opm` ≥ **40%** (현재 ~1%)
   - `none` ≤ **10%** (현재 ~17%)
   - B·D: `*_accel_n ≥ 2` 비중 ≥ **25%** 또는, 미달 시 **명시적 미채점**으로 가짜 0점과 구분
2. **규칙 투명성**
   - CSV에 `e_quality`, `b_quality`, `d_quality`, `fund_raw`, `fund_score` 구분 기록
3. **검증**
   - **이벤트 창**(day0−1→+3, 시장조정): Fund 분위 Q4−Q1 excess **양수** 재현 또는 “미재현” 문서화
   - **일상 창**(스냅샷 +5/+20d): Q4−Q1를 메인 KPI로 쓰지 않되, 악화(역전 확대) 없는지 모니터링
4. **운영**
   - anal 차트 6·7이 개선 전후 동일 포맷으로 비교 가능

---

## 4. 단계별 개발안

### Phase A — 데이터 신뢰도 (최우선)

**A1. OPM 파이프라인 강화**
- SEC `OperatingIncomeLoss` / `Revenues` 매핑 누락 티커 감사 리포트
- 단위·스케일·sign 이상치 가드
- yfinance operating income 폴백 순서 명확화: `SEC OPM → yf OPM → NPM(페널티) → none`

**A2. NPM 폴백 페널티**
- `margin_source=npm` 이면 E 기여에 **×0.5~0.7** (기본안 **×0.6**)
- `none` 이면 E=0 + `e_quality=0`
- CSV: `opm_delta_pp`, `margin_source`, `e_quality`

**A3. 가속도 깊이 게이트 (B/D)**
- `eps_accel_n < 2` → B 미채점 (`b_quality=0`, 점수 0) — “데이터 없음”과 “Δ≤0”을 로그/플래그로 구분
- Sales 동일
- 선택: n=2만 있으면 만점의 **70% 캡**

**A4. Surprise 품질**
- 컨센서스 표본·발표 경과 일수 메타 저장
- 이상치(|surprise|≫) winsorize 후 채점 (곡선 자체는 유지)

**산출물**: `docs/fundamental_spec.md` 개정 초안(v2.1-draft), 커버리지 리포트 CSV, 단위 테스트

---

### Phase B — 채점 규칙 v2.1 (가중치 고정, 품질 반영)

현행 가중치 **S47/E25/D14/B14 유지**한 채:

```
fund_raw = S + B*qB + D*qD + E*qE
fund_score = fund_raw          # 0~100 스케일 유지
```

- `qE ∈ {0, 0.6, 1.0}` (none / npm / opm)
- `qB, qD ∈ {0, 0.7, 1.0}` (n&lt;2 / n=2 / n≥3) — 숫자는 A/B로 확정
- **합이 100 미만이 되는 것 허용** (결측 페널티 = 의도된 하향)

**산출물**: `fundamental_score.py` + `params.yaml` 품질 계수, 전후 비교 CSV (`fund_score_v2` vs `v21`)

---

### Phase C — 역할 분리 (프로덕션 사용법)

| 국면 | Fund 사용 | 비고 |
|---|---|---|
| 일상 스크리닝 | **약한 필터** (예: Fund≥P20 또는 결측 과다 제외) | 순위 강제 정렬 금지 |
| 실적 시즌/이벤트 | **강한 랭커** (기존 스터디 창) | day0 전후 watchlist |
| sepaTop 편입 | 현행 유지 + 선택적 `e_quality·b_quality` 최소치 | 시총가중 엔진 불변 |

매크로/카피리스트에 `fund_min`과 별도로 `fund_quality_min` 옵션 추가.

**산출물**: `macro`/`analyze` 플래그, DEVELOPMENT_NOTE 사용 가이드 1절

---

### Phase D — 재검증 · 가중치 재스터디 (조건부)

Phase A–B 반영 후 **데이터가 바뀐 상태**에서만:

1. 기존 `fund_study` 재실행 (ADV≥$5M, day0−1→+3)
2. 품질 게이트 전/후 Spearman·직교화 비교
3. 양수 상관만으로 가중 재추정 → **리포트만** 제출
4. 사용자 승인 시에만 v2.2 가중치 반영

추가로 측정:
- 보유 5/20/60거래일 분위 수익 (참고 KPI)
- 섹터 중립화 후 Q4−Q1 (바이오 편중 통제)

**산출물**: `reports/fund_study/` 신규 런, 가중치 제안표

---

### Phase E — 관측·가드레일 (상시)

- anal 차트 7에 quality 분포 패널 추가
- 차트 6에 “이벤트 창 / 일상 창” 토글 또는 분리 파일
- 알림: `opm` 비중 &lt; 30% 또는 Top25 S점유 &gt; 70% 이면 경고 로그

---

## 5. 2차 후보 (이번에는 넣지 않음)

- Sales surprise 병행
- QoQ / ΔQoQ 스피드 팩터
- 연속 비트 보너스(n분기)
- ROE 소가중 재도입
- S 가중 하향(47→35대) — **D 재스터디 결과 보고만**

---

## 6. 작업 분해 (구현 단위)

| ID | 작업 | 주요 파일 | 의존 |
|---|---|---|---|
| A1 | SEC OPM 커버 감사 + 폴백 순서 | `data/fundamentals.py`, fund_study factors | — |
| A2 | NPM 페널티·quality 컬럼 | `fundamental_score.py`, CSV 스키마 | A1 |
| A3 | B/D depth gate | `fundamental_score.py` | — |
| A4 | Surprise winsorize/메타 | surprise 캐시 로더 | — |
| B1 | v2.1 채점 + 전후 비교 리포트 | `fundamental.py`, reports | A2–A3 |
| C1 | quality 필터 옵션 | `macro.py`, `analyze.py`, params | B1 |
| D1 | fund_study 재런 + 제안 가중 | `sepa.fund_study` | B1 |
| E1 | anal 차트 7/6 확장 | `model_metrics.py` | B1 |

테스트: `tests/test_fundamental_score.py`에 quality/페널티 케이스 추가.

---

## 7. 리스크 · 의사결정 포인트

1. **점수 하향 편향**: quality 게이트로 평균 Fund↓ → 카피리스트/`fund_min=40` 재보정 필요  
2. **OPM 확보 실패**: 40% 미달 시 E 가중을 스터디 전에도 임시 축소할지 사용자 결정  
3. **이벤트 vs 일상**: 일상 Q4≤Q1가 계속이면 Fund를 랭커가 아닌 **리스크/품질 필터**로 고정하는 안을 채택

---

## 8. 권장 착수 순서 (승인용)

```
A1 → A3 → A2 → B1 → E1(관측) → C1 → (데이터 안정 후) D1
```

가중치 변경은 **D1 승인 전 금지**.

---

## 9. 변경 이력

| 일자 | 내용 |
|---|---|
| 2026-07-26 | 초안: 진단 기반 v2.1 개발안 (데이터→규칙→역할→재스터디) |
| 2026-07-26 | **A1–C1 코드 반영 시작**: OPM 백필, quality 채점, anal coverage 확장, `fund_quality_min` / `--compare-legacy` |
