# 기계적 포지션 등급 (A/B/C/금지) — 코어·위성 대체

코어/위성 슬리브는 **사이즈 캡이 아니라 품질 라벨처럼 쓰이던 문제**가 있어 폐기한다.
대신 BuyScore L1·L2·L3 + 하드게이트로 **추가(ADD) 허용 비중**만 기계적으로 정한다.

## 캡 (주식 평가금 대비)

| 등급 | max % of equity | 품질 조건(요약) |
|------|-----------------|-----------------|
| **A** | 18% | L1=2 · L2≥1 · L3≠C |
| **B** | 10% | L1≥1 · (L2≥1 또는 Σ≥2) |
| **C** | 6% | 그 외 거래 가능 품질 |
| **금지** | 0% ADD | 하드게이트 (아래) |

추가 한도:
- **절대천장 20%** (A여도)
- **Top-3 합 ≤ 50%**
- **현금바닥 $150**

## 하드게이트 → 유효등급 `금지` (ADD 0%)

품질등급(`quality_grade`)은 유지하되, 아래가 하나라도 있으면 **effective = 금지**:

- EARN_D5
- NO_ADD (보유 OS 기본)
- L1=0 / 강제패스
- 마진↓ / 가이드 C / 축소후보
- 업사이드 &lt; 0
- 손절(stop)·invalidation 없음
- 과열

## SSOT

- `config/portfolio_watch.yaml` — 보유 `grade` / `max_pct` = **품질** 힌트 (18/10/6)
- `src/sepa/position_grade.py` — 등급·캡·weight_status·top3
- `src/sepa/portfolio_ops.py` — `HoldingRow.grade_label`, `apply_holding_grade`, 스텐스/리스크
- `포폴()` PDF — 종목 열에 `A→금지·구조18%` 형태 표시

## 운영 메모

- 현재 스냅(2026-08-04)은 **전원 NO_ADD** → 유효등급은 전부 금지. 표의 품질등급은 “게이트 풀리면 쓸 한도”.
- 신규 매수 사이즈는 실행후보 BuyScore → `assign_from_buy_score` 후 해당 `max_pct`·현금여유·Top3로 제한.
