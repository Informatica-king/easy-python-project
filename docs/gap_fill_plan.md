# 개발 계획서 — 빠진 go 날짜 빠른 채우기 (gap fill)

> **상태**: 설계안 (구현 전)  
> **작성일**: 2026-08-12 (목적·경량화 반영)  
> **결정 로그**: **D30**

---

## 목적 (이게 전부)

바빠서 **매일 `!sepa.go`를 못 돌릴 수 있다.**  
나중에 SEPA 모델을 분석하려면 **빠진 거래일의 분석용 숫자만** 이어져 있으면 된다.

그래서 이 기능은:

- ❌ 그날의 풀 go를 다시 재현하는 것이 **아님**
- ❌ PDF·섹터 차트·model_metrics·릴리즈 업로드를 하는 것이 **아님**
- ✅ **분석 패널에 필요한 최소 CSV만** 빨리 채우는 것

**원칙: 목적에 필요 없는 연산량은 최대한 줄인다.**

---

## 한 문장

빈 거래일만 찾아서, **점수·멤버십·perf에 필요한 최소 계산**만 하고 저장한다.

---

## 꼭 채울 것 (분석 최소 세트)

나중에 `!sepa.perf_study` / membership·soft ceiling 검증에 쓰이는 것:

| 산출물 | 왜 필요 |
|---|---|
| `stage2_YYYYMMDD.csv` | 그날 Stage2 후보 |
| `fundamental_YYYYMMDD.csv` | RS·Fund·시총 (바스켓 재료) |
| `rs_soft_drops_YYYYMMDD.csv` | soft ceiling 탈락 |
| `fund_median_tickers_YYYYMMDD.txt` | median+ 목록 |
| `sepatop/membership_YYYYMMDD.csv` | 편입 집합·presence 연속 |
| `reports/perf/` upsert | daily_pool / basket_members / forward 백필 |
| (선택) params hash 1줄 | 레짐 구분 |

**복원(①)일 때:** 릴리즈에 위 CSV가 있으면 **다운로드만** (계산 0).

**재계산(②)일 때:** 위 목록만 만들고 **끝**.

---

## 절대 하지 않을 것 (연산 절감)

빠진 날 fill에서 **기본 OFF / 호출 금지**:

| 스킵 | 이유 |
|---|---|
| analyze PDF / PNG board / ZIP | 무겁고 분석 패널에 불필요 |
| 섹터 점유율 차트·히트맵 | 시각화 전용 |
| sepaTop vs 벤치 성과 차트 | 인덱스 차트 불필요 |
| model_metrics 1–7 | 당일 진단용 |
| GitHub Release 업로드 | fill은 로컬 창고만 |
| Cursor artifact 대량 publish | 선택적·기본 OFF |
| 가격 전량 재다운로드 | 캐시 있으면 `--no-update` |
| Fund SEC 전량 refresh | 기본 캐시 재사용 (`--no-update` 계열) |

재계산 경로의 실질 비용 ≈ **as-of Stage2 스크린 + Fund 채점** 정도만 남긴다.

---

## 동작 조합 (유지)

### ① 릴리즈 복원 (있으면 최우선 · 가장 빠름)

로컬에 없고 `sepa-anal-YYYYMMDD`에 **최소 세트 CSV**만 있으면 받아서 꽂기.  
PDF/ZIP은 받지 않음.

### ② 빈 거래일 경량 재계산

아무데도 없을 때만:

```text
가격 캐시 유지 (--no-update)
→ scan(full, as_of=D, no_update)
→ fund(from stage2, as_of=D, no_update)  # soft ceiling·median+ 포함
→ membership CSV만 저장 (차트 없음)
→ perf_ledger upsert + forward 백필
→ source=asof_rebuild 표시
```

### ③ go 앞단은 옵션

```text
!sepa.fill_gaps()                 # 수동·기본 진입점
!sepa.fill_gaps(from=..., to=...)
!sepa.go(fill_gaps=1)             # 원할 때만 (기본 go는 오늘만)
```

---

## 속도 가드

| 가드 | 기본 |
|---|---|
| 주말 스킵 | ON |
| 이미 로컬에 `fundamental_*` 있으면 스킵 | ON |
| 한 번 실행 max 일수 | 10 (초과 시 경고 후 자름) |
| `--dry-run` | 구멍만 보여주고 계산 안 함 |
| PDF/차트 | 항상 OFF |
| 가격/재무 강제 refresh | 기본 OFF |

---

## 구현 페이즈 (짧고 가볍게)

### Phase 1 — 복원 + 탐지 (계산 거의 0)

- 거래일 캘린더 · 로컬/릴리즈 stamp diff  
- 최소 CSV만 다운로드·배치  
- membership_panel / perf ingest 재조립  
- `!sepa.fill_gaps` + 테스트  

### Phase 2 — 경량 rebuild

- 빈 날: scan+fund(+membership)+perf만  
- `asof_rebuild` 메타  
- max days / dry-run  

### Phase 3 — UX

- `go(fill_gaps=1)` 옵션  
- 요약: restore N / rebuild M / skip K · **소요 초**

---

## 비범위

- 빠진 날 “완전한 go 체험” 재현  
- 시각 리포트·릴리즈 재발행  
- live 파라미터 변경  
- 정밀 휴장 캘린더 (v1은 주말 제외만)

---

## 성공 기준

1. 바쁜 주간에 go를 못 해도, 나중에 `fill_gaps` 한 번으로 **분석용 stamp가 이어진다.**  
2. 빈 날 1일 채우기 비용이 **풀 go(anal+PDF+릴리즈)보다 훨씬 짧다.**  
3. 리포트에 `asof_rebuild`와 live go가 구분된다.

---

## 한 장 요약

```text
목적: 분석용 구멍만 메우기 (풀 go 대체 아님)
① 릴리즈 CSV 복원 = 제일 빠름
② 없으면 as-of scan+fund+membership+perf 만
③ PDF/차트/metrics/릴리즈/불필요 publish = 전부 스킵
④ 기본 !go 는 그대로, fill은 별도·옵션
```
