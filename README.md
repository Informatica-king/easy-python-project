# easy-python-project

미국 나스닥(NASDAQ)에 상장된 모든 기업/증권 목록을 내려받아 엑셀 파일로 정리하는 스크립트입니다.

## 데이터 출처

- NASDAQ Trader 공식 심볼 디렉터리: `https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt`
- 이 파일은 나스닥에 상장된 모든 증권을 담고 있으며, 거래일마다 갱신됩니다.

## 설치

```bash
pip install -r requirements.txt
```

## 실행

```bash
python fetch_nasdaq_companies.py --output nasdaq_companies.xlsx
```

실행하면 `nasdaq_companies.xlsx` 파일이 생성됩니다.

## 엑셀 파일 구성

생성되는 엑셀 파일은 3개의 시트로 이루어져 있습니다.

| 시트 | 설명 |
| --- | --- |
| `Summary` | 데이터 출처, 다운로드 시각, 총 종목 수, 시장별 통계 요약 |
| `Companies` | ETF와 테스트 종목을 제외한 실제 기업/보통주 목록 |
| `All NASDAQ Securities` | 나스닥에 상장된 전체 증권 목록 (원본 데이터 전부) |

주요 컬럼:

- `Symbol` — 티커 심볼
- `Security Name` — 종목명
- `Market Category (Name)` — 시장 구분 (Global Select / Global / Capital Market)
- `Financial Status (Name)` — 재무 상태 (Normal / Deficient 등)
- `Is ETF`, `Is Test Issue` — ETF 여부, 테스트 종목 여부

## 참고

- 나스닥 상장 종목은 매일 변동됩니다. 최신 목록이 필요하면 스크립트를 다시 실행하세요.
- `nasdaqlisted.txt`에는 보통주 외에 ETF, 워런트(Warrant), 유닛(Unit), 우선주 등도 포함됩니다. 순수 "기업" 목록만 필요하면 `Companies` 시트를 사용하세요.
