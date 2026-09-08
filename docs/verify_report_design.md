# 검증 보고서 양식 — `!검증` PDF

> **상태**: **V1.1** (2026-08-25) — Fund 구간 1년 추세 **해석 레이어** 추가  
> **확정 선택**: 태그 `sepa-검증-YYYYMMDD` · **산출물 PDF 하나** · ZIP/board는 V2  
> **구현**: `src/sepa/verify_report.py` · 진입점 `!검증` / `sepa.perf_study`

---

## 1. 한 줄 콘셉트

`!검증` = **“우리 SEPA 스크리너, 요즘 성적 어때요?”** 에 답하는 **짧은 한글 보고서 PDF**.

- **본심판**: A–D 선행 초과수익 (look-ahead 없음)
- **해석 레이어**: 오늘 Fund 10점 구간의 최근 1년 등가 종가 경로 (예측·확증 아님)

```text
!검증
  → reports/perf/verify_report_YYYYMMDD.pdf
  → GitHub Release 업로드 (sepa-검증-YYYYMMDD, asset=verify_report_*.pdf)
  → 콘솔에 PDF 직접 다운로드 URL + 릴리즈 페이지 URL 출력
```

---

## 2. 9쪽 목차

1. 한눈에 — 질문 4개 + 신뢰 배지 (+ Fund 추세 tip 한 줄)  
2. 보는 것 / 안 보는 것 + 용어  
3. A. 바구니 성적  
4. D. soft ceiling 검사  
5. B. 들어옴 / 나감  
6. C. 오래 남음  
7. **Fund 구간 1년 추세 (해석 레이어)**  
8. 후보 규모 추이  
9. 부록 원표  

---

## 3. 해석 레이어 규칙

- 멤버십 = **오늘** Fund 버킷 · 가격 = **과거 1년**
- 템플릿 문장만 (최강 구간, 중앙값 vs 최상위, 빈 고구간, 저Fund 과열 → D 교차)
- **이 장만으로 파라미터 변경 금지** — 확증은 A–D 게이트
