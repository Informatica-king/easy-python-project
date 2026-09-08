# SEPA 성능 검증 프레임워크 (장기 축적)

> 목적: `!sepa.go`가 돌 때마다 **분석에 필요한 패널을 자동 갱신**하고,  
> 수개월·수년 뒤에도 같은 스키마로 `!sepa.perf_study`를 재실행할 수 있게 한다.  
> 현재(~수 주)는 표본이 작아 **확증이 아니라 틀·모니터링**이다.

---

## 1. 설계 원칙

| 원칙 | 내용 |
|---|---|
| go마다 append | 새 스냅샷을 누적 패널에 upsert (같은 stamp는 덮어씀) |
| 스키마 고정 | 컬럼 이름은 가능한 한 바꾸지 않음 — 장기 조인 키 |
| forward는 백필 | 당일 enter/선정은 `ready_*=False`; 이후 go에서 가격이 되면 채움 |
| 벤치 고정 | 기본 초과수익 벤치 `^GSPC` (SPX); 스터디에서 교체 가능 |
| look-ahead 금지 | as_of 스냅샷 종가 기준 forward만 |
| 작은 N 허용 | study는 표본 부족을 명시하고도 요약·차트 생성 |

---

## 2. 디렉터리 (`reports/perf/`)

| 파일 | 갱신 | 내용 |
|---|---|---|
| `daily_pool_log.csv` | go마다 1행 | n_stage2/n_fund/n_median+/중앙값/RS90+ 등 |
| `basket_members_panel.csv` | go마다 append | `stamp × basket × ticker` 멤버십 |
| `security_forward_panel.csv` | go마다 백필 | 선정일 기준 5/10/21d fwd·excess |
| `basket_forward_summary_log.csv` | go마다 | 바스켓×호라이즌 평균 excess (ready만) |
| `verify_report_*.pdf` | `!검증` / `!sepa.perf_study` | 비전공자용 8쪽 한글 성적 보고서 (+ Release 링크; 파일명은 ASCII) |

go/anal이 이미 쌓는 원본(`fundamental_*`, `membership_*`, `presence_*`, `rs_soft_drops_*`, `params_hash_log` 등)과 **조인**한다. perf 패널은 “성능 검증용 파생”이다.

---

## 3. 바스켓 정의 (버전 v1)

| basket | 정의 |
|---|---|
| `fund_pool` | soft ceiling 통과 후 Fund 풀 |
| `median_plus` | Fund ≥ 당일 풀 중앙값 |
| `fund_q4` | Fund 상위 25% (동점 포함 qcut) |
| `rs90_ok` | 풀 안 RS≥90 |
| `soft_drop` | 당일 RS soft ceiling 탈락 |

나중에 바스켓을 추가해도 패널은 long-format이라 **행만 늘어난다**.

---

## 4. 스터디 메뉴 (데이터가 늘수록 채워짐)

1. **A** 바스켓별 SPX 초과수익 (5/10/21d) — mean / win / n  
2. **B** enter/exit 이벤트 forward (sepaTop membership_changes)  
3. **C** 체류 streak (`presence`) × excess  
4. **D** soft_drop 사후 성과 vs rs90_ok  
5. **E** 풀·필터 안정성 (`daily_pool_log`)  
6. **F** (향후) 섹터 편중·IR·분위 예측력 확장  

구현 범위·쉬운 설명: **`docs/perf_study_dev_plan.md`** (D29).  
**Phase 1 구현됨** — A~D + sample_gate (`!검증` / `!sepa.perf_study`).

---

## 5. 운영

```text
!sepa.go()          → 자동으로 reports/perf/* 갱신 + 아티팩트/릴리즈 첨부
!검증               → 9쪽 한글 PDF + sepa-검증-YYYYMMDD 다운로드 링크
                      (A–D 본심판 + Fund 구간 1년 추세 해석 레이어)
!sepa.perf_study()  → 위와 동일
!sepa.perf_study(refresh=1)  → 당일 패널 갱신 후 보고서
!sepa.perf_study(skip_github_release=1)  → PDF만 (업로드 생략)
```

결정 로그: **D28** — 성능 검증 장기 프레임 (`sepa.perf_ledger` / `sepa.perf_study`).  
결정 로그: **D29** — 검증·분석 함수 (`!검증` = `!sepa.perf_study`).  
결정 로그: **D31** — `!검증` PDF 보고서 + Release (`docs/verify_report_design.md`).  
결정 로그: **D33** — Fund 구간 1년 추세를 검증 PDF 해석 레이어로 편입.
