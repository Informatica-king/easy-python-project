# 모델 결과 데이터 축적 가이드

> 기준: 2026-08-03  
> 목적: `!sepa.go` / `!sepa.anal` 결과물이 쌓일 때 **무엇을 남기면 모델 분석에 유용한지** 정리.  
> 상태: **sepaTop 멤버십 분석 팩은 다음 go부터 자동 저장**. 아래 후보는 같이 저장할지 선택용.

---

## 1. 다음 go부터 자동으로 남는 것 (구현됨)

매일 `!sepa.go` → `anal` → sepaTop 경로에서 아래가 생성·퍼블리시된다.

| 파일 | 내용 | 분석 용도 |
|---|---|---|
| `membership_YYYYMMDD.csv` | 당일 sepaTop 구성 (Fund>0·시총≥$1B 후) | 일별 유니버스 스냅샷 |
| `membership_changes_YYYYMMDD.csv` | 전일 대비 enter/exit | 회전율·이벤트 스터디 |
| `presence_YYYYMMDD.csv` | 스냅샷별 출현율·끝쪽 연속 streak·always | **진짜 연속 체류** (tenure와 다름) |
| `always_present_YYYYMMDD.csv` | 디스크상 모든 membership에 한 번도 빠지지 않은 종목 | never-missed 코어셋 |
| `membership_panel.csv` | stamp×ticker 롱 패널 (누적) | 시계열 결합·조인 키 |
| `analysis_snapshot_YYYYMMDD.md` | 당일 요약 (편입/편출·always 목록) | 사람용 로그 |
| `tenure_YYYYMMDD.csv` | `first_seen` 기반 체류일 | 참고만 — **연속 체류 아님** |
| `index_YYYYMMDD.csv` + 차트 | sepaTop vs 벤치 | 지수 추적 |
| `fundamental_YYYYMMDD.csv` | Fund 스코어 풀 | RS×Fund·분포 |
| `rs_soft_drops_YYYYMMDD.csv` | RS≥90 & Fund<중앙값 탈락 | soft ceiling 효과 |
| `fund_median_tickers_YYYYMMDD.txt` | median+ shortlist | VCP/집중 관찰 |
| `stage2_YYYYMMDD.csv` | Stage2 원본 | 퍼널 상단 |

**저장 위치**

1. Cursor artifacts (`/opt/cursor/artifacts`) — 해당 런에서 바로 다운로드  
2. GitHub Release `sepa-anal-YYYYMMDD` — PDF와 **같은 태그**에 CSV/MD도 업로드 (VM wipe 대비 내구 저장)

> `tenure` / `first_seen`은 “최초 등장일”이라 중간에 빠져도 날짜가 안 지워진다.  
> never-missed·연속 streak는 반드시 `presence_*` / `always_present_*`를 쓴다.

---

## 2. 같이 쌓을지 고민할 후보 (미구현 / 선택)

우선순위는 **이미 go가 만드는 원본을 빼먹지 않는 것** → **파생 집계** 순.

### A. 퍼널·필터 (모델 게이트 진단)

| 후보 | 소스 | 왜 유용한가 | 부담 |
|---|---|---|---|
| `diagnostics_YYYYMMDD.csv` | scan | Trend Template 조건별 탈락 비율 추이 | 파일 큼 |
| soft ceiling 탈락 일별 집계 | `rs_soft_drops_*` 누적 | RS90 게이트가 Fund 품질을 얼마나 거르는지 | 낮음 (이미 일별 저장) |
| quality 필터 탈락 리스트 | fund | quality ON일 때 민감도 | 낮음 |

### B. 점수·영역 구조

| 후보 | 소스 | 왜 유용한가 | 부담 |
|---|---|---|---|
| 일별 RS×Fund 셀 소속 (`trailing_r1` 스타일) | fund + 셀 정의 | 영역 이동·과밀 구간 추적 | 중 |
| Fund 분위수 / 중앙값 시계열 | fund | 풀 난이도·인플레이션 | 낮음 |
| 섹터 점유 `sector_share_*` 히스토리 | anal | 테마 쏠림·로테이션 | 중 (이미 일부 생성) |

### C. 성과·검증 (스크리너 ≠ 단기 타이밍 전제)

| 후보 | 소스 | 왜 유용한가 | 부담 |
|---|---|---|---|
| sepaTop / median+ 의 SPX 대비 forward 1w·1m | 가격 캐시 | “점수↑ → 단기초과?” 재검증 | 중 |
| enter/exit 이후 forward return | membership_changes | 편입 알파·편출 타이밍 | 중 |
| always_present 바스켓 vs 회전 바스켓 | presence + 가격 | 코어셋 안정성 | 중 |
| model_metrics 분위 forward 상세 CSV | model_metrics | 차트만이 아닌 수치 재현 | 중 |

### D. 진입 시그널 (shortlist)

| 후보 | 소스 | 왜 유용한가 | 부담 |
|---|---|---|---|
| median+ VCP 결과 일별 | `!sepa.vcp` | 셋업 밀도·품질 점수 분포 | 실행 추가 |
| VCP hit 후 실현 경로 | vcp + 가격 | 타이밍 모듈 별도 검증 | 높음 |

### E. 메타·재현성

| 후보 | 소스 | 왜 유용한가 | 부담 |
|---|---|---|---|
| `params.yaml` 스냅샷 해시 / 덤프 | config | 파라미터 변경 전후 비교 | 낮음 |
| 데이터 as-of·캐시 최신일 | store | look-ahead / stale 점검 | 낮음 |
| 벤치마크 종가 스냅샷 | sepaTop benches | 지수 재계산 재현 | 낮음 |

---

## 3. 추천 축적 세트 (결정용)

**이미 ON (필수에 가깝게 동작 중)**  
멤버십 분석 팩 + fund + soft drops + median+ + stage2 + anal PDF 릴리즈.

**다음에 켜면 가성비 좋음 (제안)**

1. **params 스냅샷** (go 시작 시 해시/YAML 복사) — 결과 해석의 전제  
2. **enter/exit forward return 패널** — 멤버십 변경의 사후 성과  
3. **일별 Fund 분위수 1행 로그** — 풀 난이도 시계열  
4. **diagnostics 요약만** (전량 CSV 대신 조건별 pass rate 1행) — 용량↓

**나중에 / 연구 전용**

- 전 종목 diagnostics 원본, VCP 전수 히스토리, RS×Fund forward 전체 격자

---

## 4. 운영 메모

- `reports/`·`data/`는 gitignore + 클라우드 VM wipe → **릴리즈/아티팩트에 안 올린 파일은 사라질 수 있음**.
- 장기 분석은 Release 태그 `sepa-anal-YYYYMMDD`에서 membership/presence/panel을 모아 `membership_panel`로 재조립하면 된다.
- always-present는 **그 시점까지 디스크(또는 모은 릴리즈)에 있는 스냅샷 교집합**이다. 과거 릴리즈를 로컬에 복원하면 교집합이 달라질 수 있다.
