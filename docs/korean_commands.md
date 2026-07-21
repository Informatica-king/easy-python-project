# 한국어 분석 명령 규약

> 이 페이지(에이전트)에서 사용자가 아래 **함수형 한국어 명령**을 치면
> 설명 없이 해당 파이프라인을 실행한다.

---

## 명령 목록

| 명령 | 의미 | 구현 |
|---|---|---|
| `심층분석(티커,…)` | Chase RR·7섹션 심층 PDF | 딥분석 생성기 + **종료 시 기술적분석 자동** |
| `기술적분석(티커,…)` | TA 4축 + EARN_D5/BAND 훅 | `python -m sepa.tech_analysis` / `!sepa.ta` |
| `수익구조분석(티커)` | 수익구조 딥다이브 PDF | `reports/generate_revenue_structure_*.py` |

티커 생략 시:

- `심층분석()` — 당일 SEPA Fund 중앙값↑ 리스트(사용자가 가져온 목록) 기준
- `기술적분석()` — **최신 Chase RR 스냅샷**에서 매수 고려 종목 자동 선정 후 실행

---

## 심층분석 → 기술적분석 자동 연결 (필수)

`심층분석(...)` 실행이 끝나면 에이전트/스크립트는 **반드시** 다음을 수행한다.

1. Chase RR 스냅샷 저장  
   `reports/chase_rr_YYYYMMDD.json` (`sepa.chase_select.write_chase_snapshot`)
2. 매수 고려 종목 자동 선정 (`select_buy_candidates`)
3. `기술적분석(선정티커)` 즉시 실행 (`sepa.tech_analysis.run_from_chase`)
4. 채팅에 TA 표(`ta_action` / `action` / `override`) 요약 제시

사용자는 심층분석만 호출해도, 같은 턴에 기술적분석 결과까지 받는다.

```
심층분석(티커들)
   → PDF + chase_rr_DATE.json
   → select_buy_candidates(chase)
   → 기술적분석(자동 선정)
   → (선택) 관심 종목만 수익구조분석
```

---

## 매수 고려 종목 선정 규칙 (Chase RR, 그 시각 기준)

입력: `chase_rr_*.json`의 `rows` (rank 오름차순 = Chase 우선).

**제외** — `chase` 라벨에 다음이 포함되면 탈락:

`과열` `매도` `추격금지` `비적합` `최하` `중하`  
또는 라벨이 `하`로 시작(예: `하·과열`)

**포함** — 제외되지 않았고, 다음 중 하나:

1. 라벨이 `최상` / `상` / `중상` 으로 시작 (예: `상·분할보유`, `중상·07-30반만`)
2. 라벨에 `분할` 포함 (보유 분할 타이밍)
3. Chase 순위 **≤ 10** 이면서 라벨이 `중`으로 시작 (단 `중하` 제외)

**상한**: 최대 **12종목** (TA ≤20 효율 규칙). rank 순으로 자름.

선정 0종이면 기술적분석은 “후보 없음”만 보고하고 종료.

---

## 기술적분석(티커) 단독 실행

```text
기술적분석(ECPG,NESR,NEO)
기술적분석()                    # 최신 chase_rr_*.json 자동
```

CLI:

```bash
.venv/bin/python -m sepa.tech_analysis --tickers ECPG,NESR
.venv/bin/python -m sepa.tech_analysis --from-chase          # 최신 스냅샷
.venv/bin/python -m sepa.tech_analysis --from-chase reports/chase_rr_20260721.json
```

매크로: `!sepa.ta(...)` 동일 엔진. `!sepa.ta(from_chase=1)` → 스냅샷 자동.

---

## Chase 스냅샷 스키마

```json
{
  "as_of": "2026-07-21",
  "source": "심층분석",
  "rows": [
    {"rank": 1, "ticker": "NEO", "chase": "최상", "px": 14.24, "earn_date": "2026-07-28"},
    {"rank": 7, "ticker": "NESR", "chase": "상·분할보유", "px": 27.23}
  ]
}
```

`earn_date`가 있으면 워치리스트 메타보다 **스냅샷 값이 EARN_D5에 우선** 병합된다.
