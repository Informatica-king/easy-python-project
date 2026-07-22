# 경제뉴스() — 직전 미국 정규장 하룻밤 브리핑

> 승인: 2026-07-22 — 뉴스 자동수집 · 보유+워치 · 상세 PDF

## 목적
군인 루틴(21시 폰 통제)용. 미 본장 실시간 불가 → **직전 정규장 1일**을
한국어 상세 PDF로 요약.

## 입력
- `경제뉴스()` / `python -m sepa.econ_news`
- 선택: `--as-of YYYY-MM-DD` (그 날짜의 정규장)

## 데이터
| 블록 | 소스 |
|---|---|
| 지수·섹터·거래량 | yfinance (SPY QQQ IWM DIA VIX SMH + XLF… 섹터 ETF) |
| 헤드라인 | Yahoo RSS · CNBC RSS · MarketWatch RSS + 보유/워치 `Ticker.news` |
| 포트 | `config/portfolio_watch.yaml` |

## 출력
`reports/Econ_News_YYYY-MM-DD.pdf` (+ artifacts 복사)

## 섹션
1. 표지 3불릿 2. 자금이동 3. 핫/콜드 섹터+뉴스 4. 대표지수
5. 포트 영향(보유+워치) 6. 다음 장 체크리스트 7. 헤드라인 부록
