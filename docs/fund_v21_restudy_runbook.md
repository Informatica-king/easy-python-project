# Fund v2.1 재스터디 실행 노트 (Phase D)

가중치 변경은 **이 단계 승인 전 금지**. A1–B1 반영 후 데이터가 바뀐 상태에서만 재실행.

## 사전 조건

- [x] OPM 백필 후 후보군 `margin_source=opm` 비중 확인 (`reports/opm_coverage_*.csv`)
- [x] `reports/fundamental_v21_compare_*.csv` 로 v2 vs v2.1 점수 차이 검토
- [x] quality 게이트 파라미터가 `config/params.yaml`에 확정됨

## 실행

```bash
# 1) (선택) 가격·실적 이벤트 캐시 갱신
PYTHONPATH=src python3 -m sepa.fund_study --backfill-prices

# 2) 본 스터디 (Spearman / 직교화 / 제안 가중치)
PYTHONPATH=src python3 -m sepa.fund_study

# 3) 산출물 확인
ls reports/fund_study/
```

## 판정

1. 제안 가중치가 현행 S47/E25/D14/B14와 **유의미히 다른지** 리포트
2. quality 적용 전후 상관 부호·크기 비교
3. **사용자 승인 후에만** `params.yaml` / `fundamental_score.py` 가중치 갱신 (v2.2)

## 참고 KPI (메인 아님)

- 일상 스냅샷 Q4−Q1 (+5/+20d) — 모니터링만
- 섹터 중립화 Q4−Q1 — 바이오 편중 통제용


## 실행 결과 (2026-07-26 full)

- Events: 10,948 · proposed weights **S47 / E27 / B14 / D12**
- vs live: E +2, D −2 (within ±5 → **keep live weights**)
- Comparison report: `docs/fund_model_comparison_20260726.md`
- Score Spearman live↔v2.1 **0.958**, v2.1↔proposed **0.998**
