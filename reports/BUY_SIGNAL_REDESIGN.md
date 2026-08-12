# 매수 신호 개편 — 본선(좋은 종목) ∩ 타이밍 GO + 군인 프리마켓 실행

**상태:** 패키지 1~3 반영 (2026-08-12) — pick∩GO · shared `buy_scenarios` · earn confirmed/estimate  
**관련:** `sepa.pick_pool` · `sepa.timing_gate` · `sepa.earn_calendar` · `sepa.buy_scenarios` · `portfolio_ops.filter_buy_ideas`

---

## 한줄

매수 신호 = **좋은 종목(Chase 본선)** × **좋은 타이밍(GO)**  
실행 = **KR 17:30~20:55 지정가** (미국 장전만)

---

## 이전 문제

1. A′/B가 입구 → 눌린 종목만 후보 → Chase 상(ANAB) 탈락  
2. 타이밍 도구가 종목 선발을 가로챔  
3. EARN_D5가 Yahoo **추정일**로 하드블록 (ANAB 8/12)  
4. 군인 창=프리마켓인데 B 돌파 추격은 정규장용

---

## 새 파이프라인

```
Chase RR → pick_pool (본선)
buy_scenarios A/B/SOFT → timing_gate (GO_A / WAIT / BLOCK)
포폴 filter_buy_ideas:
  실행후보 = 본선 ∩ timing.is_go
  워치     = 본선 ∩ WAIT   (삭제하지 않음)
  금지     = NO_ADD · 확정 EARN_D5 · Chase 제외 · 업사이드−
buy_score L1/L2/L3 → 실행후보 순위만
액션 카드 → 지정가≤종가+1.5% · 1주 · 갭+2% VOID
```

---

## 모듈

| 모듈 | 역할 |
|------|------|
| `sepa.pick_pool` | 좋은 종목 본선 |
| `sepa.timing_gate` | GO_A/GO_B/WAIT/BLOCK (`ALLOW_GO_B_EXEC=False`) |
| `sepa.earn_calendar` | confirmed vs estimate · 확정만 하드블록 · `load_confirmed_earn_map` |
| `sepa.buy_scenarios` | 공유 타이밍 스캐너 → `buy_scenarios_*.json` (날짜별 스크립트는 thin wrapper) |
| `sepa.chase_select` | 본선 포함/제외 규칙 |
| `sepa.portfolio_ops` | 필터·저녁창 액션 |
| `sepa.buy_score` | 실행후보 순위 (입력만 본선∩GO로 바뀜) |

CLI: `PYTHONPATH=src python -m sepa.buy_scenarios --asof YYYY-MM-DD --rank reports/rank_YYYYMMDD.json`

---

## `PORTFOLIO_OPS_PLAN` / `BUY_SCORE_LAYERS_PLAN` 갱신 요지

- **폐기:** “심층 → A′ → 포폴 입구”  
- **채택:** “심층 Chase → 본선 → 타이밍 GO → 포폴 실행”  
- buy_score §2.1 “A′ 파이프라인 유지” → **본선∩GO 유지**로 수정  
- EARN: 확정만 D5 하드게이트

---

## 군인 실행 카드 (고정)

- 창: **17:30~20:55 KST**  
- 주문: **지정가** · 상한 = 기준가 +1.5% · 시장가 금지  
- 갭 +2% 이상 → **VOID** (그날 패스)  
- 미체결 → 억지 추격 금지 · 다음날 재평가  
- GO_B(돌파) 기본 **비실행(WAIT)**
