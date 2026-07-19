#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-07-19 NASDAQ deep analysis PDF (NanumGothic / WeasyPrint)."""

from __future__ import annotations

import html
from pathlib import Path

from weasyprint import HTML

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
ASOF = "2026-07-17 종가"
REPORT = "2026-07-19"

OUT = [
    Path("/opt/cursor/artifacts/NASDAQ_Deep_Analysis_2026-07-19.pdf"),
    Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-19.pdf"),
]

# Rank order for reading
ORDER = [
    "ECPG", "INDV", "AMRX", "KNSA", "JAZZ", "SEPN", "VCYT",
    "LQDA", "LIND", "CDNA", "TVTX", "KRYS", "TXG", "DAVE",
]

TICKERS = {
    "ECPG": {
        "name": "Encore Capital Group",
        "price": "현재 $91.33 | 52주 $35.67–$94.60 | PT $105/$113/$120 | A/B/C $100/$110/$120",
        "thesis": "채권회수 사이클 + EPS/매출 4/4·연속 Beat로 서프라이즈 품질 최고. 시총 ~$2.0B. 촉매: ~08-06 KST 실적 콜.",
        "sector": "금융 · 채권회수(NPL)",
        "sector_feat": "연체율·매입가·회수율이 핵심. 현금흐름형 중소형 금융.",
        "mcap_rank": "시총 ~$2.0B. 동종 소형 금융 상위.",
        "items": "연체채권(NPL) 매입·회수. 한 줄: 싸게 산 빚을 회수해 이익을 내는 회사.",
        "financials": "Q1'26 매출 $475M(YoY +21%), Non-GAAP EPS $3.86. QoQ 고수준 유지.",
        "consensus": "Buy. PT 저$105/평균$113/고$120. 현재 대비 평균 +24%.",
        "surprise": "EPS 4/4·Rev 4/4, 연속 6분기 EPS Beat. Q1 +26%, 평균 ~+56%. 품질 최상.",
        "strategy_view": "서프라이즈·PT 업사이드 모두 정합 → 코어 1순위.",
        "news": [
            "연속 EPS·매출 Beat 기록 (ChartMill).",
            "채권회수·소비자 신용 연체 섹터 관심 지속 (IR/섹터).",
            "차기 실적 ~2026-08-05/06 (회사 일정).",
        ],
        "bull": "또 Beat+가이드 상향 → $110–120",
        "base": "완만한 개선 → $100–110",
        "bear": "회수율 둔화 → $80–88",
        "breaker": "Beat 단절, 매입마진 악화, 규제",
        "conclusion": {
            "섹터": "금융·채권회수", "핵심 아이템": "NPL 회수",
            "EPS": "6연속 Beat", "신규진입": "$88–93",
            "탈락": "회수율·가이드 하향", "Chase": "최상·코어",
        },
    },
    "INDV": {
        "name": "Indivior",
        "price": "현재 $40.54 | 52주 $15.55–$42.81 | PT $46/$50.8/$59 | A/B/C $46/$52/$58",
        "thesis": "EPS/Rev 4/4 대형 서프라이즈 머신. 시총 ~$4.9B. 촉매: 07-30 실적(이벤트 리스크).",
        "sector": "제약 · 중독치료",
        "sector_feat": "소송·약가·장기작용형 주사제 침투율이 주가 핵심.",
        "mcap_rank": "시총 ~$4.9B. 특수 제약 중소형.",
        "items": "SUBLOCADE 등. 한 줄: 오피오이드 중독 치료제를 파는 제약사.",
        "financials": "Q1'26 매출 $317M, EPS $0.96. YoY·QoQ 개선.",
        "consensus": "Buy. PT $46/$50.8/$59. 평균 +25% 업사이드.",
        "surprise": "EPS 4/4·Rev 4/4, 연속 4+. Q1 EPS +44%·Rev +14%. 평균 EPS ~+57%.",
        "strategy_view": "서프라이즈 최상이나 07-30 직전 → 홀드·추가 금지.",
        "news": [
            "연속 대형 Beat (ChartMill).",
            "Q2 실적 2026-07-30 (회사 일정).",
            "장기작용형 중독치료 침투 테마 (업계).",
        ],
        "bull": "Beat+가이드 상향 → $50–58",
        "base": "성장 유지 → $46–52",
        "bear": "소송/볼륨 쇼크 → $32–36",
        "breaker": "소송·약가·가이던스 하향",
        "conclusion": {
            "섹터": "제약(중독치료)", "핵심 아이템": "SUBLOCADE",
            "EPS": "4/4 Beat 머신", "신규진입": "07-30 전 관망",
            "탈락": "소송/가이드 하향", "Chase": "상·이벤트 대기",
        },
    },
    "AMRX": {
        "name": "Amneal Pharmaceuticals",
        "price": "현재 $17.85 | 52주 $7.66–$18.39 | PT $16/$18.2/$23 | A/B/C $18/$20/$23",
        "thesis": "EPS 4연속 Beat이나 Rev는 4연속 Miss → 이익 품질은 좋되 탑라인 경계. 시총 ~$5.2–5.4B. 촉매: 07-30 장전 실적(21:30 KST 콜).",
        "sector": "제약 · 제네릭/바이오시밀러/스페셜티",
        "sector_feat": "가격 압력·출시 파이프라인·Specialty(파킨슨 등) 믹스가 핵심.",
        "mcap_rank": "시총 ~$5.4B. 제네릭 중형.",
        "items": "제네릭·바이오시밀러·Specialty(CREXONT 등). 한 줄: 저렴한 복제약과 일부 브랜드약을 만드는 회사.",
        "financials": "Q1'26 매출 $723M, EPS $0.27(+56% vs est). YoY EPS 성장, 매출은 컨센서스 소폭 하회.",
        "consensus": "Buy 우세. PT $16/$18.2/$23. 현재 ≈ 평균 PT.",
        "surprise": "EPS 4/4 연속 Beat(평균 ~+32%). Rev 0/4 Miss. Q1 EPS +56%, Rev −1%.",
        "strategy_view": "EPS 서프라이즈는 강하나 Rev 약점·고점 근접·07-30 이벤트 → 반만/대기.",
        "news": [
            "EPS 연속 Beat·매출 소폭 Miss 패턴 (ChartMill).",
            "Q2 실적 07-30 장전, 콜 08:30 ET (회사 IR).",
            "제네릭·바이오시밀러 접근성 확대 뉴스 (Amneal IR).",
        ],
        "bull": "매출 Beat 복귀 → $20–23",
        "base": "EPS만 Beat → $17–19",
        "bear": "EPS 단절·가격압력 → $14–16",
        "breaker": "매출 가이던스 컷, Specialty 둔화",
        "conclusion": {
            "섹터": "제네릭/스페셜티 제약", "핵심 아이템": "제네릭+Specialty",
            "EPS": "4연속 Beat / Rev 0/4", "신규진입": "$16–17.5 또는 실적 후",
            "탈락": "매출·가이드 하향", "Chase": "중상·반만",
        },
    },
    "KNSA": {
        "name": "Kiniksa Pharmaceuticals",
        "price": "현재 $63.95 | 52주 $26.27–$67.53 | PT $60/$68.3/$74 | A/B/C $68/$74/$80",
        "thesis": "Arcalyst 매출 Rev 4/4 Beat, EPS는 2/4·연속 1. 시총 ~$4.9B. 촉매: 07-28 ~20:00 KST 실적.",
        "sector": "바이오 · 희귀염증",
        "sector_feat": "단일 제품 의존. 처방·적응증 확장이 핵심.",
        "mcap_rank": "시총 ~$4.9B. 상업화 바이오 중소형.",
        "items": "Arcalyst. 한 줄: 희귀 염증 질환 치료제를 파는 바이오.",
        "financials": "Q1'26 매출 $214M(+56% YoY), EPS $0.27. FY매출 가이던스 $930–945M로 상향.",
        "consensus": "Buy. PT $60/$68.3/$74. 평균 +7%.",
        "surprise": "EPS 2/4(연속 1), Rev 4/4. Q1 EPS +32%. Q3·Q4'25 EPS Miss.",
        "strategy_view": "실적 직전 → 반만. EPS 불안정은 감점.",
        "news": [
            "Q1 Beat 후 FY 가이던스 상향 (Investing.com/IR).",
            "Q2 실적 ~07-27/28 (TipRanks/ChartMill).",
            "Arcalyst 처방·침투율 확대 (실적 콜).",
        ],
        "bull": "Q2 Beat+가이드 → $70–74",
        "base": "매출 유지 → $64–70",
        "bear": "EPS 미스 → $55–60",
        "breaker": "Q2 EPS/가이드 미스",
        "conclusion": {
            "섹터": "바이오(희귀염증)", "핵심 아이템": "Arcalyst",
            "EPS": "2/4 · Rev 4/4", "신규진입": "실적 전 반만 $60–64",
            "탈락": "Q2 미스", "Chase": "중상·반만",
        },
    },
    "JAZZ": {
        "name": "Jazz Pharmaceuticals",
        "price": "현재 $247.53 | 52주 $105–$250.49 | PT $229/$264.5/$307 | A/B/C $265/$285/$307",
        "thesis": "Q1 EPS·매출 대형 Beat, 다만 FY 매출 가이드는 컨센서스 소폭 하회. 시총 대형 바이오파마. 고점 근접으로 눌림 선호.",
        "sector": "바이오파마 · 신경과학/종양",
        "sector_feat": "Xywav·Epidiolex 등 상업화 포트폴리오. 가이던스와 마진이 핵심.",
        "mcap_rank": "대형 바이오파마(시총 수십억$). 섹터 내 상위권.",
        "items": "수면장애·뇌전증·종양 치료제. 한 줄: 신경계·암 관련 전문약을 파는 대형 바이오.",
        "financials": "Q1'26 매출 $1.07B(+19% YoY), Adj EPS $6.34. 영업이익률 개선 보고.",
        "consensus": "Buy/Overweight. PT $229/$264.5/$307. 평균 +7%.",
        "surprise": "Q1 EPS +36%·Rev +9% Beat. FY 매출 가이드는 Street 대비 약함. L4Q는 최근 강세 중심.",
        "strategy_view": "품질 좋으나 52주 고점·업사이드 제한 → 눌림/$230대 대기.",
        "news": [
            "Q1 매출·EPS Beat, FY 가이드 소폭 약함 (Yahoo Finance).",
            "신경과학·Epidiolex/Xywav 포트폴리오 포커스 (회사/섹터).",
            "주가 52주 고점권 (가격 데이터).",
        ],
        "bull": "가이드 상향 → $280–307",
        "base": "완만한 성장 → $250–270",
        "bear": "가이드 재하향 → $210–230",
        "breaker": "매출 가이드 컷, 키제품 둔화",
        "conclusion": {
            "섹터": "바이오파마", "핵심 아이템": "Xywav/Epidiolex 등",
            "EPS": "Q1 대형 Beat", "신규진입": "$230–240 눌림",
            "탈락": "가이드 하향", "Chase": "중·눌림",
        },
    },
    "SEPN": {
        "name": "Septerna",
        "price": "현재 $33.40 | 52주 $10.62–$38.04 | PT $38/$46.3/$60 | A/B/C $40/$48/$58",
        "thesis": "GPCR 신약 플랫폼, Q1 손실 축소·매출 Beat. PT 대비 업사이드. 시총 소형·임상 리스크 큼.",
        "sector": "바이오 · GPCR 신약발견",
        "sector_feat": "초기~중기 임상. 파이프라인·파트너십·현금이 핵심.",
        "mcap_rank": "소형 바이오(시총 수십억$ 미만 구간).",
        "items": "GPCR 타깃 신약. 한 줄: 세포 신호 수용체(GPCR)를 겨냥한 신약을 개발.",
        "financials": "Q1'26 EPS −$0.19 vs est −$0.32 Beat, 매출 $26.5M vs ~$16M Beat.",
        "consensus": "Buy. PT $38/$46.3/$60. 평균 +38% 업사이드.",
        "surprise": "최근 Q1 EPS·Rev Beat. 상장 초기라 L4Q 연속성 제한. Benzinga 평균 서프라이즈 양호.",
        "strategy_view": "PT 업사이드는 매력, 임상·변동성으로 소형 위성만.",
        "news": [
            "Q1 손실 축소·매출 상회 (Benzinga).",
            "차기 실적 ~08-10 (Benzinga).",
            "GPCR 신약 플랫폼 테마 (회사).",
        ],
        "bull": "임상 호재 → $46–60",
        "base": "점진 재평가 → $38–46",
        "bear": "임상 실패 → $20–28",
        "breaker": "임상 실패, 현금 소진",
        "conclusion": {
            "섹터": "바이오(GPCR)", "핵심 아이템": "GPCR 파이프라인",
            "EPS": "Q1 Beat(적자 축소)", "신규진입": "$30–34 소량",
            "탈락": "임상 실패", "Chase": "중·위성",
        },
    },
    "VCYT": {
        "name": "Veracyte",
        "price": "현재 $59.13 | 52주 $22.61–$60.91 | PT $47/$59/$70 | A/B/C $62/$68/$75",
        "thesis": "Rev 4/4·EPS 3/4·최근 2연속 Beat. PT≈현재·고점. 눌림만.",
        "sector": "헬스케어 · 분자진단",
        "sector_feat": "검사 볼륨·보험 급여가 핵심.",
        "mcap_rank": "시총 ~$4.7B. 진단 중소형.",
        "items": "Afirma 등. 한 줄: 유전자·조직 검사로 불필요 수술을 줄이는 진단사.",
        "financials": "Q1'26 매출 $139M, EPS $0.35. YoY 성장.",
        "consensus": "Buy/Hold. PT $47/$59/$70. 평균≈현재.",
        "surprise": "EPS 3/4(연속 2), Rev 4/4. Q1 EPS +133%.",
        "strategy_view": "품질 양호, 업사이드 제한 → 중하위.",
        "news": [
            "연속 매출 Beat (ChartMill).",
            "분자진단 성장 테마 (섹터).",
            "보험·볼륨이 관전 포인트.",
        ],
        "bull": "볼륨 가속 → $68–75",
        "base": "현상 유지 → $58–65",
        "bear": "급여 축소 → $47–52",
        "breaker": "보험·볼륨 둔화",
        "conclusion": {
            "섹터": "분자진단", "핵심 아이템": "Afirma",
            "EPS": "3/4 · 연속 2", "신규진입": "$52–55",
            "탈락": "보험·볼륨 둔화", "Chase": "중하·눌림",
        },
    },
    "LQDA": {
        "name": "Liquidia",
        "price": "현재 $79.94 | 52주 $14.25–$82.96 | PT $60/$75.1/$109 | A/B/C $75/$90/$109",
        "thesis": "YUTREPIA 출시 후 흑자·매출 급증, EPS 3/4·Rev 4/4 Beat. 다만 현재가 > 평균 PT → 추격 주의.",
        "sector": "바이오 · 희귀 심폐/폐고혈압",
        "sector_feat": "흡입 치료제 침투·특허소송·제조 증설이 핵심.",
        "mcap_rank": "시총 ~$7B대. 상업화 바이오 중형.",
        "items": "YUTREPIA(흡입 treprostinil). 한 줄: 폐고혈압 환자가 들이마시는 치료 분말약.",
        "financials": "Q1'26 제품매출 ~$130M, 순이익 ~$53M, Diluted EPS $0.52. YoY 적자→흑자 전환.",
        "consensus": "Buy. PT $60/$75/$109. 현재가 평균 PT 대비 +6% 프리미엄.",
        "surprise": "EPS 3/4, Rev 4/4. Q1 EPS +55%, Rev +22%.",
        "strategy_view": "펀더·서프라이즈 우수하나 고점·PT 프리미엄 → 신규 추격 비권장, 눌림 대기.",
        "news": [
            "YUTREPIA Q1 매출 ~$130M, 3분기 연속 흑자 (GlobeNewswire 2026-05-11).",
            "특허/법적 리스크 완화 보도 (Simply Wall St 등).",
            "L606 Phase 3·제조 증설 계획 (회사 IR).",
        ],
        "bull": "침투 가속 → $90–109",
        "base": "성장·밸류 부담 → $70–85",
        "bear": "소송/수요 둔화 → $55–65",
        "breaker": "특허 패소, 처방 둔화",
        "conclusion": {
            "섹터": "희귀 심폐", "핵심 아이템": "YUTREPIA",
            "EPS": "3/4 · Rev 4/4", "신규진입": "비추격 · $65–72",
            "탈락": "소송·수요 둔화", "Chase": "중·고점주의",
        },
    },
    "LIND": {
        "name": "Lindblad Expeditions",
        "price": "현재 $27.67 | 52주 $11.37–$30.00 | PT $17/$27.5/$34 | A/B/C $28/$31/$34",
        "thesis": "탐험 크루즈/여행. PT≈현재·고점권. 바이오 유니버스와 이질적, 모멘텀은 제한적.",
        "sector": "소비재 · 여행/레저(탐험)",
        "sector_feat": "예약·선박 가동·유가·소비심리 민감.",
        "mcap_rank": "소형 여행주.",
        "items": "탐험 크루즈·랜드 투어. 한 줄: 극지·자연 탐험 여행을 파는 회사.",
        "financials": "여행 수요 회복 스토리. 분기 실적은 시즌성 큼(상세 YoY는 차기 실적에서 확인).",
        "consensus": "혼재. PT $17/$27.5/$34. 평균≈현재.",
        "surprise": "공개 소스상 L4Q 연속 Beat 데이터 제한. 서프라이즈 신뢰도 중하로 보수 평가.",
        "strategy_view": "어닝 서프라이즈 전략 중심 유니버스에서 후순위.",
        "news": [
            "탐험여행·크루즈 수요 회복 테마 (섹터).",
            "주가 52주 고점 근접 (가격).",
            "매크로(소비·유가) 민감 (업계).",
        ],
        "bull": "예약 강세 → $31–34",
        "base": "횡보 → $26–29",
        "bear": "수요 둔화 → $20–24",
        "breaker": "예약 취소·매크로 충격",
        "conclusion": {
            "섹터": "여행/레저", "핵심 아이템": "탐험 크루즈",
            "EPS": "데이터 제한·보수", "신규진입": "비선호",
            "탈락": "수요 둔화", "Chase": "하",
        },
    },
    "CDNA": {
        "name": "CareDx",
        "price": "현재 $39.73 | 52주 $11.26–$40.47 | PT $21/$32.3/$45 | A/B/C $35/$40/$45",
        "thesis": "이식 진단 강자 + Naveris 인수. 현재가 > 평균 PT, 고점, 07-30 실적.",
        "sector": "헬스케어 · 이식/정밀진단",
        "sector_feat": "검사 볼륨·보험·M&A 통합이 핵심.",
        "mcap_rank": "시총 ~$1.5–2B대. 진단 소형.",
        "items": "AlloMap 등 이식 감시 검사. 한 줄: 장기이식 후 거부반응을 피 검사로 보는 회사.",
        "financials": "이식 검사 매출 중심. Naveris 인수로 종양 MRD 확장(거래대금 최대 $260M).",
        "consensus": "혼재. PT $21/$32.3/$45. 현재가 평균 대비 +23% 프리미엄.",
        "surprise": "최근 L4Q 상세는 소스 혼재. 가격·PT 괴리가 커 서프라이즈만으로 추격 불가.",
        "strategy_view": "이벤트+PT 프리미엄 → 관망. 실적·인수 시너지 확인 후.",
        "news": [
            "Naveris 인수 합의(선급 $160M+마일스톤) (CareDx IR).",
            "Q2 실적 07-30 장마감 후, 콜 16:30 ET (StockTitan).",
            "이식 정밀의료 테마 (회사).",
        ],
        "bull": "인수 시너지 → $42–45",
        "base": "횡보·소화 → $32–38",
        "bear": "통합 비용·볼륨 둔화 → $25–30",
        "breaker": "실적 미스, 인수 차질",
        "conclusion": {
            "섹터": "이식진단", "핵심 아이템": "AlloMap+MRD 확장",
            "EPS": "확인 후 가중", "신규진입": "실적 후 / $30–33",
            "탈락": "실적·인수 차질", "Chase": "하·과열",
        },
    },
    "TVTX": {
        "name": "Travere Therapeutics",
        "price": "현재 $56.71 | 52주 $15.03–$60.10 | PT $43/$58.3/$70 | A/B/C $58/$65/$70",
        "thesis": "희귀 신장 상업화 스토리이나 Q1 EPS·매출 Miss → 서프라이즈 감점. 고점 근접.",
        "sector": "바이오 · 희귀 신장/대사",
        "sector_feat": "Filspari 등 상업화·적응증 확장이 핵심.",
        "mcap_rank": "중소형 상업화 바이오.",
        "items": "희귀 신장질환 치료제. 한 줄: 드문 신장병 약을 개발·판매하는 바이오.",
        "financials": "Q1'26 매출 $127M(YoY +56%)나 컨센서스 Miss. Adj EPS −$0.39 vs −$0.30 Miss.",
        "consensus": "Buy 혼재. PT $43/$58.3/$70. 평균≈현재.",
        "surprise": "Q1 EPS −31% Miss, Rev −1.8% Miss. L4Q EPS 2/4 Beat.",
        "strategy_view": "최근 Miss로 서프라이즈 전략 감점 → 후순위.",
        "news": [
            "Q1 손실·매출 Miss (Yahoo/Zacks).",
            "희귀 신장 상업화 성장 스토리는 유지 (섹터).",
            "주가 고점권 (가격).",
        ],
        "bull": "다음 분기 Beat 전환 → $65–70",
        "base": "횡보 → $52–60",
        "bear": "또 Miss → $40–48",
        "breaker": "연속 Miss, 처방 둔화",
        "conclusion": {
            "섹터": "희귀 신장", "핵심 아이템": "Filspari 등",
            "EPS": "Q1 Miss · L4Q 2/4", "신규진입": "비선호",
            "탈락": "연속 Miss", "Chase": "하·감점",
        },
    },
    "KRYS": {
        "name": "Krystal Biotech",
        "price": "현재 $354.86 | 52주 $130.50–$382.54 | PT $284/$355.7/$474 | A/B/C $360/$400/$450",
        "thesis": "EPS 연속 Beat 우수하나 가격≈PT 평균·고점 → 추격 비추천.",
        "sector": "바이오 · 유전자치료",
        "sector_feat": "VYJUVEK 상업화·해외승인·파이프라인.",
        "mcap_rank": "시총 ~$10.5B. 유전자치료 중대형.",
        "items": "VYJUVEK. 한 줄: 희귀 피부질환 유전자치료제.",
        "financials": "Q1'26 매출 $116M, EPS $1.83.",
        "consensus": "Buy. PT $284/$356/$474. 평균≈현재.",
        "surprise": "연속 EPS Beat(Benzinga 3연속+). Q1 +26%대.",
        "strategy_view": "서프라이즈 OK, 가격 부담 → 하단.",
        "news": [
            "Q1 Beat (MarketBeat).",
            "영국 등 해외 승인 관련 보도 (2026-05).",
            "차기 실적 ~08-03.",
        ],
        "bull": "확장 → $400–450",
        "base": "안정 → $340–380",
        "bear": "둔화 → $280–300",
        "breaker": "처방 둔화·디레이팅",
        "conclusion": {
            "섹터": "유전자치료", "핵심 아이템": "VYJUVEK",
            "EPS": "연속 Beat", "신규진입": "$300–320 대기",
            "탈락": "상업화 둔화", "Chase": "하·고점",
        },
    },
    "TXG": {
        "name": "10x Genomics",
        "price": "현재 $43.74 | 52주 $11.16–$46.32 | PT $20/$34.2/$50 | A/B/C $35/$42/$50",
        "thesis": "EPS/Rev 4/4 Beat이나 현재가 >> 평균 PT($34) → 과열 추격 금지.",
        "sector": "헬스케어 · 생명과학도구(단일세포/공간)",
        "sector_feat": "연구비·도구 수요·경쟁이 핵심. 성장 둔화 구간.",
        "mcap_rank": "중형 라이프사이언스 툴.",
        "items": "단일세포·공간전사체 장비/시약. 한 줄: 세포를 하나씩 분석하는 연구 장비를 파는 회사.",
        "financials": "Q1'26 매출 $151M(조정 YoY +9%), 순손실 축소. FY 가이던스 $600–625M 유지.",
        "consensus": "Hold/Buy 혼재. PT $20/$34.2/$50. 현재가 평균 대비 +28% 프리미엄.",
        "surprise": "EPS 4/4·Rev 4/4 연속 Beat. Q1 EPS 서프라이즈 +66%(적자 축소).",
        "strategy_view": "서프라이즈는 최고 수준이나 PT 대비 과열 → 랭킹 최하위권.",
        "news": [
            "Q1 Beat, FY 가이드 유지 (PR Newswire 2026-05-07).",
            "단일세포/공간생물학 수요 테마 (섹터).",
            "차기 실적 ~08-06 (MarketBeat).",
        ],
        "bull": "성장 재가속 → $48–50",
        "base": "밸류 조정 → $32–40",
        "bear": "가이드 하향 → $22–28",
        "breaker": "가이드 컷, 연구비 둔화",
        "conclusion": {
            "섹터": "라이프사이언스 툴", "핵심 아이템": "단일세포/공간",
            "EPS": "4/4 Beat", "신규진입": "회피 / $30–34",
            "탈락": "가이드 하향", "Chase": "최하·과열",
        },
    },
    "DAVE": {
        "name": "Dave Inc.",
        "price": "현재 $440.42 | 52주 $152.21–$455.98 | PT $250/$373/$485 | A/B/C $380/$420/$485",
        "thesis": "최근 3연속 EPS Beat·Rev 4/4이나 $440>>PT $373 → 과열.",
        "sector": "핀테크 · 소비자 금융앱",
        "sector_feat": "ExtraCash·규제·신용비용. 실적 변동성 큼.",
        "mcap_rank": "시총 ~$5.6B. 핀테크 중소형.",
        "items": "ExtraCash. 한 줄: 급여 전 소액 현금을 주는 금융앱.",
        "financials": "Q1'26 매출 $158M(+47% YoY), Adj EPS 강세.",
        "consensus": "Buy 혼재. PT $250/$373/$485. 현재 +18% 프리미엄.",
        "surprise": "EPS 3/4·연속 3, Rev 4/4. Q2'25 Miss 이력. 변동성 큼.",
        "strategy_view": "비추격.",
        "news": [
            "Q1 Beat 후 가이던스 공백 변동성 (ChartMill).",
            "차기 실적 ~08-05.",
            "핀테크·규제 리스크 (섹터).",
        ],
        "bull": "가이드 제시 → $450–485",
        "base": "밸류 부담 → $360–420",
        "bear": "규제·신용 → $280–330",
        "breaker": "규제, 신용손실",
        "conclusion": {
            "섹터": "핀테크", "핵심 아이템": "ExtraCash",
            "EPS": "3/4 · 변동성", "신규진입": "회피",
            "탈락": "규제·신용", "Chase": "최하·과열",
        },
    },
}


def e(s: str) -> str:
    return html.escape(s)


def kv(pairs):
    rows = "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in pairs)
    return f'<table class="kv">{rows}</table>'


def ticker_block(i: int, tkey: str) -> str:
    t = TICKERS[tkey]
    c = t["conclusion"]
    news = "".join(f"<li>{e(n)}</li>" for n in t["news"])
    return f"""
    <section class="ticker">
      <h2>{i}. {e(tkey)} — {e(t['name'])}</h2>
      <p class="price">{e(t['price'])}</p>
      <div class="section"><h3>1. One-line Thesis</h3><p>{e(t['thesis'])}</p></div>
      <div class="section"><h3>2. 섹터 · 섹터주 특징 · 시총 순위</h3>
        {kv([('섹터', t['sector']), ('특징', t['sector_feat']), ('시총/순위', t['mcap_rank'])])}
      </div>
      <div class="section"><h3>3. 핵심 아이템</h3><p>{e(t['items'])}</p></div>
      <div class="section"><h3>4. 실적 (YoY+QoQ · 컨센서스 · 서프라이즈 · 전략 비교)</h3>
        {kv([('실적', t['financials']), ('컨센서스', t['consensus']),
             ('서프라이즈', t['surprise']), ('전략 관점', t['strategy_view'])])}
      </div>
      <div class="section"><h3>5. 섹터·기업 뉴스 (출처)</h3><ul>{news}</ul></div>
      <div class="section"><h3>6. 중단기 시나리오 (BULL / BASE / BEAR)</h3>
        {kv([('BULL', t['bull']), ('BASE', t['base']), ('BEAR', t['bear']),
             ('Thesis breaker', t['breaker'])])}
      </div>
      <div class="section"><h3>7. 결론 표</h3>
        {kv([(k, c[k]) for k in ['섹터','핵심 아이템','EPS','신규진입','탈락','Chase']])}
      </div>
    </section>
    """


def build_html() -> str:
    surprise = [
        ("ECPG", "4/4", "6연속", "4/4", "최상"),
        ("INDV", "4/4", "4연속+", "4/4", "최상"),
        ("AMRX", "4/4", "4연속", "0/4", "상(매출약)"),
        ("TXG", "4/4", "4연속", "4/4", "상(과열)"),
        ("LQDA", "3/4", "최근강", "4/4", "상(고점)"),
        ("KRYS", "3~4연속", "연속", "Beat", "상(고점)"),
        ("DAVE", "3/4", "3연속", "4/4", "중상(과열)"),
        ("VCYT", "3/4", "2연속", "4/4", "중상"),
        ("JAZZ", "Q1강", "최근Beat", "Q1Beat", "중상"),
        ("SEPN", "Q1Beat", "초기", "Q1Beat", "중(임상)"),
        ("KNSA", "2/4", "1연속", "4/4", "중"),
        ("CDNA", "혼재", "-", "-", "중하(과열)"),
        ("LIND", "제한", "-", "-", "하"),
        ("TVTX", "2/4", "Q1Miss", "Miss", "하"),
    ]
    srows = "".join(
        f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td><td>{e(d)}</td><td>{e(f)}</td></tr>"
        for a, b, c, d, f in surprise
    )
    ranks = [
        ("1", "ECPG", "6연속 Beat + PT 업사이드 + 코어"),
        ("2", "INDV", "4/4 Beat 머신 · 07-30 이벤트"),
        ("3", "AMRX", "EPS 4연속 · Rev 약 · 07-30"),
        ("4", "KNSA", "Rev 완벽 · EPS 불안정 · 07-28 반만"),
        ("5", "JAZZ", "Q1 대형 Beat · 고점 눌림"),
        ("6", "SEPN", "PT 업사이드 · 임상 위성"),
        ("7", "VCYT", "3/4 Beat · PT≈현재"),
        ("8", "LQDA", "펀더 강 · PT/고점 주의"),
        ("9", "LIND", "이질 섹터 · 서프라이즈 약"),
        ("10", "CDNA", "PT 프리미엄 · 07-30"),
        ("11", "TVTX", "Q1 Miss 감점"),
        ("12", "KRYS", "Beat나 고점"),
        ("13", "TXG", "4/4 Beat나 PT 대비 과열"),
        ("14", "DAVE", "PT 대비 과열"),
    ]
    rrows = "".join(
        f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td></tr>" for a, b, c in ranks
    )
    bodies = "".join(ticker_block(i, k) for i, k in enumerate(ORDER, 1))

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/>
<title>NASDAQ 심층분석 {REPORT}</title>
<style>
@font-face {{ font-family:'NanumReport'; src:url('file://{FONT_REG}'); font-weight:400; }}
@font-face {{ font-family:'NanumReport'; src:url('file://{FONT_BOLD}'); font-weight:700; }}
@page {{ size:A4; margin:16mm 13mm 16mm 13mm;
  @bottom-center {{ content:counter(page); font-family:'NanumReport'; font-size:9pt; color:#666; }} }}
body {{ font-family:'NanumReport',sans-serif; font-size:10.5pt; line-height:1.45; color:#1e1e1e; }}
h1 {{ font-size:21pt; color:#142846; }}
h2 {{ font-size:14.5pt; color:#19375f; page-break-after:avoid; }}
h3 {{ font-size:11pt; color:#14325a; background:#e6eef8; padding:5pt 8pt; margin:10pt 0 4pt; page-break-after:avoid; }}
.cover {{ text-align:center; padding-top:36mm; page-break-after:always; }}
.meta {{ font-size:11pt; margin:4pt 0; color:#333; }}
.ticker {{ page-break-before:always; }}
.price {{ font-size:9.5pt; color:#333; }}
table.data, table.kv {{ width:100%; border-collapse:collapse; margin:6pt 0 10pt; font-size:9.5pt; }}
table.data th {{ background:#1e3c64; color:#fff; padding:5pt; border:1px solid #1e3c64; }}
table.data td {{ border:1px solid #c5d0de; padding:4pt 5pt; text-align:center; }}
table.data tr:nth-child(even) td {{ background:#f0f5fa; }}
table.kv th {{ width:22%; text-align:left; vertical-align:top; background:#f3f6fa; border:1px solid #d0dae6; padding:4pt 6pt; }}
table.kv td {{ border:1px solid #d0dae6; padding:4pt 6pt; vertical-align:top; }}
ul {{ margin:4pt 0 8pt 16pt; }}
.disclaimer {{ margin-top:24pt; font-size:9pt; color:#777; }}
</style></head><body>
<section class="cover">
  <h1>NASDAQ 심층분석 보고서</h1>
  <p class="meta" style="font-size:14pt;font-weight:700;">보고서일 {REPORT} · 기준가 {ASOF}</p>
  <p class="meta">전략: NASDAQ · 중단기 모멘텀 · 어닝 서프라이즈 중시</p>
  <p class="meta">PT: StockAnalysis · 서프라이즈: ChartMill/Benzinga/Yahoo/IR</p>
  <p class="meta" style="margin-top:14pt;font-weight:700;">분석 대상 (14)</p>
  <p class="meta">KNSA · AMRX · JAZZ · INDV · LQDA · TXG · TVTX</p>
  <p class="meta">CDNA · VCYT · ECPG · KRYS · SEPN · LIND · DAVE</p>
  <p class="meta" style="margin-top:10pt;font-size:9pt;">폰트: NanumGothic (CID / Identity-H)</p>
  <p class="disclaimer">면책: 투자 권유가 아닌 공개자료 기반 분석 노트입니다.</p>
</section>
<section>
  <h2>0. 어닝 서프라이즈 요약</h2>
  <table class="data"><thead><tr><th>티커</th><th>EPS</th><th>연속</th><th>Rev</th><th>품질</th></tr></thead>
  <tbody>{srows}</tbody></table>
</section>
{bodies}
<section class="ticker">
  <h2>투자 우선순위 재편성 (Chase RR · 오늘 14종만)</h2>
  <table class="data"><thead><tr><th>순위</th><th>티커</th><th>핵심 이유</th></tr></thead>
  <tbody>{rrows}</tbody></table>
  <h3>실행 우선순위</h3>
  <ul>
    <li>코어 유지: ECPG (보유 시)</li>
    <li>이벤트 관전: KNSA(07-28 반만), INDV·AMRX·CDNA(07-30)</li>
    <li>신규 관심(가격 조건): AMRX 눌림, SEPN 소량, JAZZ 눌림</li>
    <li>비추격: DAVE, TXG, LQDA 고점, CDNA 프리미엄, KRYS 고점, TVTX(Miss)</li>
  </ul>
</section>
</body></html>
"""


def main():
    for f in (FONT_REG, FONT_BOLD):
        if not Path(f).exists():
            raise SystemExit(f"missing font {f}")
    doc = build_html()
    Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-19.html").write_text(doc, encoding="utf-8")
    pdf = HTML(string=doc, base_url="file:///").write_pdf()
    for p in OUT:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf)
        print(f"Wrote {p} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
