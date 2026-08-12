# 개발 계획서 — 빠진 go 날짜 자동 채우기 (gap fill)

> **상태**: 설계안 (구현 전 — 이 브리핑 확정 후 코딩)  
> **작성일**: 2026-08-12  
> **결정**: 권장 조합 = **① 릴리즈 복원 + ② 빈 거래일 as-of 재계산(fund까지) + ③ go 앞단은 옵션**  
> **결정 로그**: **D30**

---

## 한 문장

오랜만에 `!sepa.go`를 해도, **예전에 돌린 날은 복사본을 되찾고**,  
**안 돌린 거래일은 그날 기준으로 다시 계산해** 성적 창고가 끊기지 않게 한다.

---

## 왜 필요한가

| 문제 | 예 |
|---|---|
| VM이 리셋되면 로컬 `reports/`가 사라짐 | 08-11 go 때 sepaTop이 “첫 스냅샷”으로 보임 |
| 며칠 건너뛰면 거래일 구멍이 생김 | 08-07 다음 거래일 08-10 없음 |
| perf forward·presence는 **연속 stamp**가 있어야 의미가 커짐 | 구멍 있으면 ready·체류가 늦게/잘못 쌓임 |

이미 있는 재료:

- GitHub 릴리즈 `sepa-anal-YYYYMMDD` (그날 실제 go 산출물)
- `scan` / `fund`의 `--as-of`
- `perf_ledger`의 forward 백필·fundamental ingest

없는 것: **빈 날을 찾아 → 복원/재계산 → 패널 재조립**하는 한 줄 도구.

---

## 확정 범위 (권장 조합)

### ① 릴리즈 복원 (우선 · 정확)

- 로컬에 없는 stamp인데 `sepa-anal-YYYYMMDD` 릴리즈가 있으면 자산 다운로드
- 넣는 것(기본):  
  `stage2_*`, `fundamental_*`, `rs_soft_drops_*`, `fund_median_tickers_*`,  
  sepaTop `membership_*` / `changes_*` / `presence_*` / `always_present_*` / event fwd,  
  perf CSV 조각(있으면), params/diag/quantile 요약(있으면)
- 안 넣거나 선택: 큰 PDF/차트 ZIP (기본 OFF — 용량·시간)

### ② 빈 거래일 as-of 재계산 (구멍만)

- 캘린더: **거래일만** (주말 제외; 미국 휴장은 v1에서 단순화 가능 — 주말만 제외해도 OK)
- 아무데도 없는 날만: `scan(full, as_of=D)` → `fund(as_of=D)` → soft ceiling·median+ 저장
- **anal PDF/차트 전체는 기본 OFF** (느림). sepaTop membership은 fund CSV로 **가볍게 재생성**
- 결과 메타: `source=asof_rebuild` (당시 live go와 다를 수 있음 표시)

### ③ go 앞단 옵션

```text
!sepa.go()                    # 기본: 오늘만 (기존과 동일)
!sepa.go(fill_gaps=1)         # 오늘 전에 fill_gaps 실행
!sepa.fill_gaps()             # 수동 전용
!sepa.fill_gaps(from=..., to=...)
```

기본 go는 **지금처럼 빠르게**. 채우기는 원할 때만.

---

## 비범위 (이번에 안 함)

- 빠진 날 PDF·섹터 차트 전부 재생성
- 완벽한 재무 PIT(과거 SEC 시점) 재현
- 미국 전체 휴장 캘린더 정밀화 (v2)
- live RS/Fund 파라미터 변경

---

## 사용자 명령 (완성 후)

```text
!sepa.fill_gaps()
!sepa.fill_gaps(from=2026-08-01, to=2026-08-11)
!sepa.go(fill_gaps=1)          # 옵션
```

출력 예:

```text
gap fill: restore 4일 | rebuild 1일 | skip weekend 2일
  restored: 20260804,20260805,20260806,20260807
  rebuilt:  20260810 (asof_rebuild)
  panels:   membership_panel / presence / perf 재조립 완료
```

---

## 구현 페이즈

### Phase 1 — 뼈대 + 릴리즈 복원  ← **1차**

| ID | 작업 |
|---|---|
| G1.1 | `trading_days(from, to)` — 주말 제외 날짜 리스트 |
| G1.2 | 로컬 stamp 목록 (`fundamental_*.csv`, membership 등) |
| G1.3 | `gh release` / GitHub API로 `sepa-anal-*` 목록·자산 다운로드 |
| G1.4 | 자산을 `reports/`·`reports/sepatop/`에 배치 (덮어쓰기 정책: 같은 stamp면 스킵 또는 강제) |
| G1.5 | 복원 후 `membership_panel` / presence / `perf_ledger` 재조립·ingest |
| G1.6 | `!sepa.fill_gaps` 매크로 + 단위 테스트(가짜 릴리즈 목록) |
| G1.7 | 문서·D30 결정 로그 |

**완료 기준**: VM wipe 직후에도 fill_gaps 한 번으로 08-04~07 로컬 복원 + presence 연속성 회복.

### Phase 2 — 빈 날 as-of 재계산

| ID | 작업 |
|---|---|
| G2.1 | 복원 후에도 비어 있는 거래일 탐지 |
| G2.2 | 해당일 `scan --as-of` + `fund --as-of` (+ soft drops / median+ txt) |
| G2.3 | fund CSV로 sepaTop membership 저장 (차트/PDF 생략) |
| G2.4 | `source=asof_rebuild` 메타 파일 또는 CSV 컬럼 |
| G2.5 | 일수 상한(예: 기본 max 10일) · `--dry-run` |
| G2.6 | perf upsert + forward 백필 |

**완료 기준**: 08-10 같은 구멍이 fundamental+membership+perf에 생기고, 이후 go에서 forward ready가 채워질 준비됨.

### Phase 3 — go 옵션 + UX

| ID | 작업 |
|---|---|
| G3.1 | `!sepa.go(fill_gaps=1)` 앞단 호출 |
| G3.2 | 요약 배너(복원/재계산/스킵 개수) |
| G3.3 | AGENTS.md / result_data_accumulation 안내 |

---

## 모듈·파일 예상

| 파일 | 역할 |
|---|---|
| `src/sepa/gap_fill.py` | 캘린더·탐지·복원·rebuild 오케스트레이션 |
| `src/sepa/release_restore.py` | `sepa-anal-*` 목록/다운로드/배치 |
| `src/sepa/macro.py` | `fill_gaps`, go의 `fill_gaps=` |
| `tests/test_gap_fill.py` | 날짜 구멍·스킵·복원 경로 |
| `docs/gap_fill_plan.md` | 본 문서 |

---

## 리스크

| 리스크 | 대응 |
|---|---|
| 재계산 ≠ 당시 live go | `asof_rebuild` 표시, 해석 시 구분 |
| 전종목 as-of가 느림 | max days, dry-run, PDF OFF |
| gh 인증/네트워크 | 실패 시 해당 일만 스킵·로그 |
| 릴리즈 자산 이름 변경 | 필수 파일 화이트리스트 + 없으면 warn |

---

## 지금 바로 할 일 (코딩 순서)

1. Phase 1 구현·테스트·푸시  
2. 실제 `!sepa.fill_gaps(from=2026-08-04, to=2026-08-11)` 스모크  
3. Phase 2 → 08-10 rebuild  
4. Phase 3 go 옵션  

---

## 한 장 요약

```text
[①] 릴리즈에 있는 날 → 받아서 reports에 꽂기     (정확)
[②] 아무데도 없는 거래일 → as-of scan+fund     (근사, 표시)
[③] !sepa.go(fill_gaps=1) 은 선택              (기본 go는 그대로)
[안 함] 매일 PDF 재생성 / 파라미터 변경
```
