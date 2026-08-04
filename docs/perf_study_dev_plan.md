# 개발 계획서 — SEPA 모델 검증·분석 함수

> **상태**: 설계안 (구현 전 — 사용자가 페이즈/우선순위 확정)  
> **작성일**: 2026-08-04  
> **선행**: D28 축적 프레임 (`docs/perf_study_framework.md`, `sepa.perf_ledger`)  
> **목표**: `!sepa.go`로 쌓인 패널 위에서, **재현 가능한 검증·분석 함수**를 단계적으로 완성한다.  
> **전제**: 현재(~3주)는 확증 불가. 수개월·수년 표본을 전제로 한 **틀 + 점진 강화**.

---

## 0. 한 줄 요약

데이터는 go마다 이미 쌓인다. 이제 필요한 것은 **무엇을 어떤 순서로 검증할지 고정한 분석 API**다.  
`!sepa.perf_study`를 “한 방에 전부 리포트”로 유지하되, 내부는 **모듈(A~F)로 쪼개** 표본이 찰 때마다 켜지게 한다.

---

## 1. 배경 — 이미 있는 것 / 부족한 것

| 자산 | 상태 | 역할 |
|---|---|---|
| `reports/perf/daily_pool_log.csv` | ON (go마다) | 풀 규모·중앙값 시계열 |
| `reports/perf/basket_members_panel.csv` | ON | stamp×basket×ticker |
| `reports/perf/security_forward_panel.csv` | ON + 백필 | 5/10/21d fwd·excess |
| `reports/perf/basket_forward_summary_log.csv` | ON | 바스켓×호라이즌 요약 |
| sepaTop `membership_*` / `presence_*` / `membership_event_fwd_panel` | ON | 체류·enter/exit |
| `params_hash_log` / Fund 분위수 / diag 요약 | ON | 레짐·품질 조인 키 |
| `!sepa.perf_study` | **스켈레톤** | A·B·C 요약 + 차트 일부 |
| soft_drop vs rs90_ok 대비 | **미구현** | 정책 검증 핵심 |
| 섹터 IR·분위 예측력 | **미구현** | 장기 확장 |
| 표본 게이트 / CI / 레짐 분할 | **미구현** | 확증 단계용 |

**원칙**: 패널 스키마는 바꾸지 않는다. 분석 함수만 늘린다.

---

## 2. 분석 파트 정리 (검증 메뉴)

각 파트 = **질문 1개 + 입력 패널 + 산출물 + 최소 표본 가이드**.

### A. 바스켓 SPX 초과수익 (운용 필터 성과)

| 항목 | 내용 |
|---|---|
| 질문 | fund_pool / median_plus / fund_q4 / rs90_ok 가 SPX 대비 단기 초과를 냈는가? |
| 입력 | `security_forward_panel` (ready만) |
| 지표 | n_ready, n_stamps, mean/median excess, win rate (5/10/21d) |
| 산출 | 표 + bar chart · `study_basket_agg_*.csv` |
| 최소 표본 | 모니터링: stamps≥5 & ready≥30 / **해석**: stamps≥40 & ready≥200 |
| 현재 | 스켈레톤 있음 → **집계·차트·CI 강화** |

### B. sepaTop enter / exit 이벤트 forward

| 항목 | 내용 |
|---|---|
| 질문 | 편입(enter) 직후·편출(exit) 직후 초과수익 패턴이 있는가? |
| 입력 | `membership_event_fwd_panel` (+ 필요 시 changes) |
| 지표 | action×horizon mean excess, n, win; (선택) exit 후 잔여 모멘텀 |
| 산출 | MD 섹션 + 이벤트 요약 CSV |
| 최소 표본 | enter ready≥20 / exit ready≥20 부터 해석 시작 |
| 현재 | 요약 줄만 → **표·차트·누적 분포** |

### C. 체류 streak × excess (코어 vs 회전)

| 항목 | 내용 |
|---|---|
| 질문 | 오래 남아 있는 종목이 단기 초과와 상관이 있는가? always_present가 더 나은가? |
| 입력 | `presence_*` ⨝ median_plus(또는 sepaTop) forward |
| 지표 | Spearman(streak, excess), always_present vs 비코어 mean excess |
| 산출 | `study_streak_excess_*.csv` + scatter |
| 최소 표본 | ready ticker≥30 (상관), ≥80 (그룹 비교) |
| 현재 | Spearman·always 평균만 → **구간 버킷·차트** |

### D. soft_drop vs rs90_ok (정책 검증)

| 항목 | 내용 |
|---|---|
| 질문 | soft ceiling으로 뺀 종목(soft_drop)이, 통과한 RS≥90(rs90_ok)보다 사후 성적이 나빴는가? |
| 입력 | basket `soft_drop`, `rs90_ok` forward |
| 지표 | horizon별 Δmean excess, win 차이, n; (선택) paired stamp 비교 |
| 산출 | 대비 표 + bar · `study_soft_vs_rs90_*.csv` |
| 최소 표본 | 각 바스켓 ready≥50 / stamps≥20 |
| 현재 | **미구현 (1순위 신규)** |

### E. 풀·필터 안정성 (모니터링)

| 항목 | 내용 |
|---|---|
| 질문 | 날마다 풀 크기·중앙값·median+ 비중이 어떻게 움직이는가? 급변 일은? |
| 입력 | `daily_pool_log` |
| 지표 | n_fund / n_median+ / fund_median trail, Δday, 이상치 플래그 |
| 산출 | sparkline/line chart + MD 표 (최근 N일 + 전체 요약) |
| 최소 표본 | days≥10 모니터링 / ≥60 레짐 논의 |
| 현재 | 최근 10일 표만 → **시계열 차트·변동성** |

### F. (향후) 섹터·IR·분위 예측력

| 항목 | 내용 |
|---|---|
| 질문 | 섹터 편중이 초과를 설명하는가? Fund/RS 분위가 forward를 가르는가? |
| 입력 | analyze 태그 + forward + (선택) params_hash 레짐 |
| 지표 | 섹터별 mean excess·IR(근사), Fund Q1–Q4 forward 단조? |
| 산출 | 히트맵/표 |
| 최소 표본 | stamps≥60 권장 |
| 현재 | **보류** — A~E 안정 후 |

---

## 3. API · 모듈 설계

### 3.1 공개 엔트리 (유지)

```text
!sepa.perf_study()          # 전체 리포트 (모듈 A~E 묶음)
!sepa.perf_study(module="D") # (선택) 단일 모듈만
python -m sepa.perf_study [--stamp YYYYMMDD] [--module A|B|C|D|E|all]
```

### 3.2 내부 모듈 (신규/확장)

| 함수 | 파트 | 비고 |
|---|---|---|
| `study_basket_excess(fwd)` | A | 기존 `aggregate_basket_excess` 확장 (CI·std) |
| `study_event_forward(events)` | B | enter/exit 표·집계 |
| `study_streak_excess(presence, fwd)` | C | 기존 조인 + 버킷 |
| `study_soft_vs_rs90(fwd)` | D | **신규** |
| `study_pool_stability(pool_log)` | E | **신규** |
| `write_study_md(...)` | 공통 | 섹션별 플러그인 |
| `sample_gate(n, stamps, …)` | 공통 | `monitor` / `interpret` / `insufficient` 라벨 |

### 3.3 산출 디렉터리

```text
reports/perf/
  study_YYYYMMDD.md
  study_basket_agg_YYYYMMDD.csv
  study_event_fwd_YYYYMMDD.csv        # B
  study_streak_excess_YYYYMMDD.csv
  study_soft_vs_rs90_YYYYMMDD.csv     # D
  study_pool_stability_YYYYMMDD.csv   # E
  charts/
    perf_basket_excess_{5d|10d|21d}_*.png
    perf_soft_vs_rs90_*.png
    perf_streak_scatter_*.png
    perf_pool_trail_*.png
```

go/anal 릴리즈(`sepa-anal-YYYYMMDD`)에 study MD·차트·핵심 CSV를 첨부 (기존 publish 경로 재사용).

---

## 4. 공통 규칙 (확정 제안)

| 규칙 | 값 |
|---|---|
| 벤치 | `^GSPC` (실패 시 `SPY`) |
| 초과 | \(r_i - r_{\mathrm{SPX}}\) 단순 차감 |
| 호라이즌 | 5 / 10 / 21 거래일 (기존 `EVENT_FWD_HORIZONS`) |
| look-ahead | as_of 종가 기준 forward만, ready 플래그 강제 |
| 바스켓 v1 | fund_pool, median_plus, fund_q4, rs90_ok, soft_drop |
| 작은 N | 리포트 상단 고정 경고 + 섹션별 `sample_gate` |
| 스키마 | perf 패널 컬럼명 변경 금지 (분석 컬럼만 추가) |

---

## 5. 구현 페이즈

### Phase 0 — 문서·게이트 (본 계획서)

- [x] 분석 파트 A~F 정리
- [ ] 사용자: 페이즈 범위·우선순위 확정 (권장: Phase 1→2)

### Phase 1 — 코어 검증 함수 (A·B·C 강화 + D 신규)  ← **권장 1차**

| ID | 작업 | 산출 |
|---|---|---|
| P1.1 | A: CI(선택 bootstrap)·std·n_stamps 표 강화, 차트 유지 | `study_basket_agg` |
| P1.2 | B: enter/exit×horizon 표 CSV + 간단 bar | `study_event_fwd_*` |
| P1.3 | C: streak 버킷(1 / 2–4 / 5+) + scatter | 차트 + CSV |
| P1.4 | D: soft_drop vs rs90_ok 대비 표·차트 | **신규 핵심** |
| P1.5 | `sample_gate` + MD 섹션에 상태 배지 | study MD |
| P1.6 | 단위 테스트 (합성 fwd로 A/B/D) | `tests/test_perf_study.py` |
| P1.7 | 매크로/레지스트리 확인 (`!perf` 동일) | 회귀 테스트 |

**완료 기준**: `!sepa.perf_study` 한 번으로 A~D 섹션이 항상 나오고, N 부족 시에도 크래시 없이 `insufficient` 표기.

### Phase 2 — 모니터링·운영성 (E + UX)

| ID | 작업 |
|---|---|
| P2.1 | E: pool trail line chart + Δ/이상치 |
| P2.2 | `--module` 단일 실행 |
| P2.3 | study 산출물을 anal 릴리즈 extras에 명시 첨부 |
| P2.4 | `docs/perf_study_framework.md`에 파트 링크 동기화 |

### Phase 3 — 확장 (F, 표본 충분 시)

| ID | 작업 | 조건 |
|---|---|---|
| P3.1 | 섹터별 excess·근사 IR | stamps≥60 권장 |
| P3.2 | Fund/RS 분위 × forward 단조 검사 | ready 분위당 ≥30 |
| P3.3 | params_hash 레짐 분할 요약 | 해시 변경 ≥2회 |
| P3.4 | (선택) 63/126d 호라이즌 — 패널 스키마 확장 합의 후 | 장기 전용 |

---

## 6. 테스트 계획

| 테스트 | 내용 |
|---|---|
| 단위 | 합성 `security_forward_panel` → A/D 집계 수치 |
| 단위 | 빈 패널 / ready=0 → MD 생성, exit 0 |
| 단위 | soft_drop·rs90_ok 분리 평균 |
| 스모크 | 실제 `reports/perf/` 있으면 시 `perf_study` 종료 코드 0 |
| 회귀 | 매크로 alias `perf` / `perf_study` |

프로덕션 파라미터·live 게이트는 이 페이즈에서 **변경하지 않는다**. 검증만.

---

## 7. 리스크 · 비범위

| 포함 | 제외 |
|---|---|
| 누적 패널 기반 사후·forward 요약 | Phase 5 풀 백테스트 엔진 부활 |
| soft ceiling 정책의효과 모니터링 | live RS/Fund 임계값 즉각 변경 |
| small-N 안전 리포트 | “통계적 유의 → 바로 파라미터 확정” |
| SPX 초과 단순 차감 | 거래비용·슬리피지·포트 최적화 |

생존 편향·짧은 히스토리 VM 유실 가능성은 Release `sepa-anal-*` + perf 패널로 완화 (기존 D24/D28).

---

## 8. 결정이 필요한 항목 (실행 전)

1. **1차 범위**: Phase 1만 / Phase 1+2 / 전부  
2. **D 기본 바스켓**: soft_drop vs rs90_ok 만 / fund_pool 대비도 병행?  
3. **CI**: Phase 1에 bootstrap 넣을지, 표의 n·mean·win만으로 충분할지  
4. **호라이즌**: 5/10/21 유지 (권장) vs 63d 조기 추가  

**권장 기본**: Phase 1 전체, D는 soft_drop vs rs90_ok, CI는 생략(n·mean·win), 호라이즌 5/10/21.

---

## 9. 운영 플로우 (완성 후)

```text
매주/매일  !sepa.go()
    → reports/perf/* 자동 갱신·백필

원할 때    !sepa.perf_study()
    → A~E(구현분) MD/차트/CSV
    → 표본 게이트가 interpret 미만이면 “틀 점검”으로만 사용

수개월 후  같은 명령 재실행 → 같은 스키마로 해석력만 상승
```

---

## 10. 결정 로그 연결

- 프레임: **D28** (`perf_ledger` / `perf_study` 스켈레톤)  
- 본 계획: **D29** (검증·분석 함수 개발 계획서)  
- 구현 착수 시: Phase 1 PR에서 D30 등으로 완료 기록
