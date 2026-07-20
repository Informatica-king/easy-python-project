#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-07-20 deep analysis for 40 NASDAQ tickers — NanumGothic WeasyPrint PDF."""

from __future__ import annotations
import html
from pathlib import Path
from weasyprint import HTML

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
REPORT, ASOF = "2026-07-20", "2026-07-17 종가"
OUT = [
    Path("/opt/cursor/artifacts/NASDAQ_Deep_Analysis_2026-07-20.pdf"),
    Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-20.pdf"),
]

# Compact records: px, h, l, ptL, ptA, ptH, name, sector, feat, mcap, item, fin, cons, sur, strat, news, bull, base, bear, brk, eps, entry, drop, chase, abc
# Rank order (Chase RR)
ORDER = [
    "ECPG","INDV","NESR","AMRX","KNSA","NEO","XMTR","FROG","ACHC","CHEF",
    "NWPX","FA","BAND","CMPR","JAZZ","SEPN","AVTX","SLS","DNTH","RAPP",
    "ASTH","BTSG","JBHT","VCYT","KYMR","ALKS","FTRE","GPRE","LQDA","PTGX",
    "LFST","CLMT","LIND","CDNA","KRYS","TVTX","FTNT","SEZL","TXG","DAVE",
]

T = {
"ECPG": dict(px=91.33,h=94.60,l=35.67,ptL=105,ptA=113.33,ptH=120,name="Encore Capital",sector="금융·채권회수",
 feat="연체율·매입가·회수율 핵심",mcap="~$2.0B 소형금융",item="NPL 회수. 한줄: 싸게 산 빚을 회수",
 fin="Q1 매출$475M(+21%YoY) EPS$3.86",cons="Buy PT평균$113(+24%)",
 sur="EPS4/4 Rev4/4 6연속Beat 평균+56%",strat="서프라이즈·PT 정합 → 코어1",
 news="연속Beat(ChartMill); ~08-06실적",bull="$110–120",base="$100–110",bear="$80–88",
 brk="Beat단절·규제",eps="6연속Beat",entry="$88–93",drop="회수율하향",chase="최상·코어",abc="$100/$110/$120"),
"INDV": dict(px=40.54,h=42.81,l=15.55,ptL=46,ptA=50.75,ptH=59,name="Indivior",sector="제약·중독치료",
 feat="소송·약가·장기주사 침투",mcap="~$4.9B",item="SUBLOCADE. 한줄: 중독치료 제약",
 fin="Q1 매출$317M EPS$0.96",cons="Buy PT$50.8(+25%)",
 sur="EPS4/4 Rev4/4 연속4+ Q1+44%",strat="Beat머신·07-30관전·추가금지",
 news="07-30실적; 연속대형Beat",bull="$50–58",base="$46–52",bear="$32–36",
 brk="소송·가이드하향",eps="4/4 Beat머신",entry="07-30전 관망",drop="소송/가이드",chase="상·이벤트",abc="$46/$52/$58"),
"NESR": dict(px=27.99,h=30.31,l=6.00,ptL=30,ptA=33,ptH=36,name="National Energy Services",sector="에너지·OFS(MENA)",
 feat="중동CAPEX·지정학",mcap="~$2.8B",item="통합오일필드서비스. 한줄: 중동 유전 장비·인력",
 fin="Q1 매출$405M(+34%) EPS~$0.26Beat",cons="Buy PT$33(+18%)",
 sur="EPS4/4 Rev4/4 연속Beat Q1+24%",strat="서프라이즈·PT여유 → 분할1순위",
 news="Jafurah프랙; ~08-19실적",bull="$33–36",base="$30–33",bear="$22–25",
 brk="지정학·마진압축",eps="연속Beat",entry="$25–28분할",drop="가동률하락",chase="상·분할",abc="$31/$34/$36"),
"AMRX": dict(px=17.85,h=18.39,l=7.66,ptL=16,ptA=18.2,ptH=23,name="Amneal",sector="제네릭/스페셜티제약",
 feat="가격압력·파이프라인",mcap="~$5.4B",item="제네릭+Specialty. 한줄: 복제약·브랜드약",
 fin="Q1 EPS$0.27(+56%vs) 매출소폭Miss",cons="Buy PT$18.2≈현재",
 sur="EPS4/4연속 Rev0/4Miss",strat="EPS강·매출약·07-30반만",
 news="07-30장전실적 08:30ET콜",bull="$20–23",base="$17–19",bear="$14–16",
 brk="매출가이드컷",eps="4연속/Rev0/4",entry="$16–17.5반만",drop="가이드하향",chase="중상·반만",abc="$18/$20/$23"),
"KNSA": dict(px=63.95,h=67.53,l=26.27,ptL=60,ptA=68.29,ptH=74,name="Kiniksa",sector="바이오·희귀염증",
 feat="Arcalyst의존",mcap="~$4.9B",item="Arcalyst. 한줄: 희귀염증 치료제",
 fin="Q1 매출$214M(+56%) EPS$0.27 FY가이드상향",cons="Buy PT$68(+7%)",
 sur="EPS2/4연속1 Rev4/4 Q1+32%",strat="07-28전 반만",
 news="07-28~20:00KST실적; 가이드상향",bull="$70–74",base="$64–70",bear="$55–60",
 brk="Q2 EPS미스",eps="2/4·Rev4/4",entry="반만$60–64",drop="Q2미스",chase="중상·반만",abc="$68/$74/$80"),
"NEO": dict(px=14.61,h=15.57,l=4.72,ptL=11,ptA=16.36,ptH=25,name="NeoGenomics",sector="헬스케어·암진단랩",
 feat="검사볼륨·급여",mcap="중소형진단",item="암진단검사. 한줄: 암 유전자·병리 검사 랩",
 fin="연속수익성개선 스토리",cons="PT$16.4(+12%)",
 sur="EPS4/4 8연속Beat Rev3/4 Q1+150%",strat="서프라이즈강·PT소폭여유·07-28이벤트",
 news="07-28실적예정",bull="$18–25",base="$15–18",bear="$11–13",
 brk="볼륨·급여둔화",eps="8연속Beat",entry="$13–14.5",drop="볼륨둔화",chase="상",abc="$16/$19/$23"),
"XMTR": dict(px=98.54,h=102.00,l=30.63,ptL=62,ptA=90.88,ptH=126,name="Xometry",sector="산업·AI제조마켓플레이스",
 feat="제조수요·수수료",mcap="중형",item="주문형제조플랫폼. 한줄: 부품을 공장에 연결하는 마켓",
 fin="Q1 EPS·Rev Beat",cons="PT$90.9 현재+8%프리미엄",
 sur="EPS4/4 8연속 Rev4/4 Q1EPS+140%",strat="Beat최상이나PT프리미엄→눌림선호",
 news="~08-04실적",bull="$110–126",base="$90–105",bear="$70–85",
 brk="수요둔화",eps="8연속Beat",entry="$85–92",drop="가이던스하향",chase="중상·눌림",abc="$95/$110/$126"),
"FROG": dict(px=88.54,h=99.22,l=34.05,ptL=65,ptA=88.05,ptH=110,name="JFrog",sector="IT·SW공급망/DevOps",
 feat="기업SW지출·경쟁",mcap="중형SaaS",item="아티팩트·보안플랫폼. 한줄: 소프트웨어 배포 파이프라인 도구",
 fin="Q1 EPS+69% Rev+4%Beat",cons="PT$88≈현재",
 sur="EPS4/4 8연속 Rev4/4",strat="Beat우수·가격반영→눌림",
 news="~08-06실적",bull="$100–110",base="$85–95",bear="$70–80",
 brk="성장둔화",eps="8연속Beat",entry="$78–85",drop="가이드컷",chase="중·눌림",abc="$90/$100/$110"),
"ACHC": dict(px=34.50,h=34.74,l=11.43,ptL=13,ptA=31.55,ptH=40,name="Acadia Healthcare",sector="헬스케어·행동건강",
 feat="입원·외래수요·규제",mcap="중형",item="행동건강시설. 한줄: 정신건강·중독 치료 병원",
 fin="Q1 EPS+37% RevBeat",cons="PT$31.6 현재+9%프리미엄",
 sur="EPS4/4 5연속 Rev4/4",strat="Beat강·고점·07-28→대기",
 news="07-28실적",bull="$38–40",base="$32–36",bear="$25–30",
 brk="규제·점유둔화",eps="5연속Beat",entry="$28–32",drop="실적미스",chase="중·대기",abc="$35/$38/$40"),
"CHEF": dict(px=97.08,h=102.87,l=53.20,ptL=66,ptA=92,ptH=110,name="The Chefs' Warehouse",sector="소비재·식품유통",
 feat="외식수요·마진",mcap="중형",item="특수식자재유통. 한줄: 고급 식당에 식재료 납품",
 fin="Q1 EPS+60% Rev+5%Beat",cons="PT$92 현재+5%",
 sur="EPS4/4 8연속 Rev4/4",strat="Beat최상·소폭프리미엄·07-29",
 news="07-29실적",bull="$105–110",base="$95–102",bear="$80–90",
 brk="외식둔화",eps="8연속Beat",entry="$88–94",drop="마진압축",chase="중상",abc="$98/$105/$110"),
"NWPX": dict(px=138.20,h=152.03,l=40.01,ptL=90,ptA=103.33,ptH=130,name="Northwest Pipe",sector="소재·수자원인프라",
 feat="공공인프라·수주",mcap="소형",item="강관·수자원제품. 한줄: 수도관·인프라용 강관",
 fin="Q1 EPS+93% Rev+10%Beat",cons="PT$103 현재+34%과열",
 sur="EPS4/4 4연속 Rev4/4",strat="Beat우수나PT대비과열→비추격",
 news="07-29실적",bull="$140–152",base="$110–130",bear="$90–105",
 brk="수주둔화",eps="4연속Beat",entry="$100–110",drop="가이던스하향",chase="중하·과열",abc="$120/$135/$150"),
"FA": dict(px=22.35,h=22.78,l=8.82,ptL=15,ptA=17.29,ptH=20,name="First Advantage",sector="산업·신원조회",
 feat="채용사이클",mcap="중형",item="배경조사. 한줄: 채용 때 신원·경력 조회",
 fin="Q1 EPS+30% Rev+3%Beat",cons="PT$17.3 현재+29%과열",
 sur="EPS4/4 4연속 Rev4/4",strat="Beat강·가격과열→대기",
 news="~08-06실적",bull="$23–25",base="$17–21",bear="$14–16",
 brk="채용한파",eps="4연속Beat",entry="$16–18",drop="볼륨둔화",chase="중하·과열",abc="$19/$22/$25"),
"BAND": dict(px=71.81,h=79.08,l=12.50,ptL=15,ptA=57.5,ptH=85,name="Bandwidth",sector="IT·CPaaS통신",
 feat="API통화·메시징수요",mcap="소중형",item="클라우드통신API. 한줄: 앱에 전화·문자 기능을 넣는 회사",
 fin="Q1 EPS+65% Rev+4%Beat",cons="PT$57.5 현재+25%과열",
 sur="EPS4/4 5연속 Rev3/4",strat="Beat강·과열·07-29",
 news="07-29실적",bull="$80–85",base="$55–70",bear="$40–50",
 brk="성장둔화",eps="5연속Beat",entry="$55–62",drop="가이드컷",chase="중하·과열",abc="$65/$75/$85"),
"CMPR": dict(px=102.85,h=106.57,l=43.52,ptL=110,ptA=111.5,ptH=113,name="Cimpress",sector="산업·맞춤인쇄",
 feat="온라인맞춤제작수요",mcap="중형",item="대량맞춤인쇄. 한줄: 명함·홍보물 등 맞춤 인쇄",
 fin="최근분기 EPS대형Beat RevBeat",cons="PT$111.5(+8%)",
 sur="EPS3/4 3연속 Rev4/4",strat="PT소폭업사이드·07-29",
 news="07-29실적",bull="$110–113",base="$100–108",bear="$85–95",
 brk="수요둔화",eps="3연속Beat",entry="$95–100",drop="마진악화",chase="중",abc="$105/$110/$113"),
"JAZZ": dict(px=247.53,h=250.49,l=105.00,ptL=229,ptA=264.5,ptH=307,name="Jazz Pharmaceuticals",sector="바이오파마",
 feat="Xywav/Epidiolex·가이던스",mcap="대형",item="신경·종양약. 한줄: 신경계·암 전문약",
 fin="Q1 매출$1.07B(+19%) EPS$6.34(+36%) FY가이드약",cons="PT$264(+7%)",
 sur="Q1대형Beat·FY가이드약",strat="품질양호·고점눌림",
 news="Q1Beat(Yahoo)",bull="$280–307",base="$250–270",bear="$210–230",
 brk="가이드컷",eps="Q1대형Beat",entry="$230–240",drop="키제품둔화",chase="중·눌림",abc="$265/$285/$307"),
"SEPN": dict(px=33.40,h=38.04,l=10.62,ptL=38,ptA=46.25,ptH=60,name="Septerna",sector="바이오·GPCR",
 feat="임상·현금",mcap="소형",item="GPCR신약. 한줄: 세포수용체 신약개발",
 fin="Q1 적자축소Beat 매출Beat",cons="PT$46(+38%)",
 sur="Q1 EPS/RevBeat 초기",strat="업사이드·임상위성",
 news="~08-10실적",bull="$46–60",base="$38–46",bear="$20–28",
 brk="임상실패",eps="Q1Beat",entry="소량$30–34",drop="임상실패",chase="중·위성",abc="$40/$48/$58"),
"AVTX": dict(px=19.37,h=24.27,l=5.50,ptL=34,ptA=45.18,ptH=60,name="Avalo Therapeutics",sector="바이오·염증",
 feat="임상단계·희석",mcap="소형",item="염증질환신약. 한줄: 염증 치료 후보물질 개발",
 fin="임상바이오·매출미미",cons="PT$45(+133%이론)",
 sur="최근EPS Beat혼재 Rev희소",strat="PT업사이드크나임상리스크→극소량",
 news="~08-06실적",bull="$34–50",base="$18–28",bear="$8–14",
 brk="임상실패·희석",eps="혼재",entry="극소량/관망",drop="임상실패",chase="하·고위험",abc="$25/$35/$50"),
"SLS": dict(px=13.19,h=15.88,l=1.39,ptL=25,ptA=27.5,ptH=30,name="SELLAS Life Sciences",sector="바이오·항암",
 feat="파이프라인의존",mcap="초소형",item="항암신약. 한줄: 암 치료제 임상 바이오",
 fin="임상단계",cons="PT$27.5(+108%)",
 sur="EPS4/4연속 Rev데이터희소",strat="이론업사이드·바이너리리스크",
 news="~08-11실적",bull="$25–30",base="$12–18",bear="$5–9",
 brk="임상실패",eps="연속Beat(적자)",entry="관망/극소",drop="임상실패",chase="하·고위험",abc="$18/$25/$30"),
"DNTH": dict(px=105.60,h=105.72,l=18.08,ptL=98,ptA=129.73,ptH=200,name="Dianthus Therapeutics",sector="바이오·자가면역",
 feat="임상·경쟁",mcap="중형바이오",item="자가면역신약. 한줄: 면역질환 치료제 개발",
 fin="Q1 EPS/Rev Beat",cons="PT$130(+23%)",
 sur="EPS1/4 Rev1/4 최근Beat",strat="업사이드·고점·서프라이즈약",
 news="~08-07실적",bull="$130–180",base="$100–120",bear="$70–90",
 brk="임상실패",eps="1/4",entry="$90–100",drop="임상실패",chase="중하",abc="$110/$130/$160"),
"RAPP": dict(px=42.62,h=43.76,l=13.62,ptL=40,ptA=53.56,ptH=66,name="Rapport Therapeutics",sector="바이오·신경과학",
 feat="임상",mcap="소중형",item="신경과학신약. 한줄: 뇌·신경 질환 신약",
 fin="Q1 EPS+38% RevBeat",cons="PT$53.6(+26%)",
 sur="EPS3/4 Rev희소",strat="업사이드·임상위성",
 news="~08-06실적",bull="$53–66",base="$40–50",bear="$25–35",
 brk="임상실패",eps="3/4",entry="$36–40소량",drop="임상실패",chase="중·위성",abc="$48/$55/$66"),
"ASTH": dict(px=44.94,h=51.60,l=18.08,ptL=36,ptA=48.57,ptH=65,name="Astrana Health",sector="헬스케어서비스·VBC",
 feat="CarePartners·레버리지",mcap="~$2.2B",item="가치기반케어. 한줄: 의사네트워크로 환자관리",
 fin="Q1 매출$965M(+56%) AdjEPS$0.74",cons="PT$48.6(+8%)",
 sur="Adj최근2연속대형Beat(GAAP혼선) Rev대체로Beat",strat="보유적합·08-07콜",
 news="08-06/07실적콜",bull="$55–65",base="$48–55",bear="$36–40",
 brk="Adj미스·레버리지",eps="Adj턴",entry="$42–46",drop="가이드미스",chase="상·보유",abc="$48/$55/$62"),
"BTSG": dict(px=70.69,h=72.22,l=19.01,ptL=49,ptA=74.88,ptH=90,name="BrightSpring",sector="헬스케어서비스",
 feat="스페셜티약국·홈케어",mcap="~$14.7B",item="전문약+재택돌봄",
 fin="Q1 EPS$0.39(+23%) RevBeat",cons="PT$74.9(+6%)",
 sur="EPS3/4연속1 Rev4/4",strat="고점·07-31·추가금지",
 news="07-31 21:30KST콜",bull="$80–90",base="$70–78",bear="$55–62",
 brk="마진·통합쇼크",eps="3/4",entry="$58–62대기",drop="마진압축",chase="중·보유만",abc="$75/$82/$90"),
"JBHT": dict(px=291.41,h=299.76,l=130.12,ptL=200,ptA=298.05,ptH=370,name="J.B. Hunt",sector="운송·물류",
 feat="화물사이클·운임",mcap="~$27B대장",item="Intermodal/DCS",
 fin="Q2 EPS$1.91(+45%) 매출+19%",cons="PT$298≈현재",
 sur="EPS4/4 4연속",strat="고점반영→$260–275대기",
 news="Q2실적발표완료",bull="$320–350",base="$290–310",bear="$240–260",
 brk="화물피크아웃",eps="4연속",entry="$260–275",drop="운임하락",chase="중·눌림",abc="$300/$320/$350"),
"VCYT": dict(px=59.13,h=60.91,l=22.61,ptL=47,ptA=59,ptH=70,name="Veracyte",sector="분자진단",
 feat="볼륨·보험",mcap="~$4.7B",item="Afirma 등",
 fin="Q1 매출$139M EPS$0.35",cons="PT$59≈현재",
 sur="EPS3/4연속2 Rev4/4",strat="눌림만",
 news="분자진단테마",bull="$68–75",base="$58–65",bear="$47–52",
 brk="급여축소",eps="3/4",entry="$52–55",drop="볼륨둔화",chase="중하",abc="$62/$68/$75"),
"KYMR": dict(px=115.77,h=130.05,l=36.65,ptL=100,ptA=126.61,ptH=155,name="Kymera Therapeutics",sector="바이오·단백질분해",
 feat="TPD플랫폼·임상",mcap="중형바이오",item="표적단백질분해. 한줄: 질병단백질을 분해하는 신약",
 fin="Q1 EPSBeat Rev대형Beat(일회성가능)",cons="PT$127(+9%)",
 sur="EPS1/4 Rev1/4",strat="서프라이즈약·임상모멘텀",
 news="~08-10실적",bull="$126–155",base="$100–120",bear="$70–90",
 brk="임상실패",eps="1/4",entry="$100–110",drop="임상실패",chase="중하",abc="$120/$135/$155"),
"ALKS": dict(px=52.72,h=55.67,l=25.17,ptL=38,ptA=52.2,ptH=65,name="Alkermes",sector="바이오파마·신경과학",
 feat="상업화포트폴리오",mcap="중형",item="신경과학약",
 fin="Rev4/4Beat이나EPS최근미스",cons="PT$52≈현재",
 sur="EPS2/4 연속2미스 Rev4/4 Q1EPS-167%",strat="Rev강·EPS약·07-28감점",
 news="07-28실적",bull="$58–65",base="$50–55",bear="$38–45",
 brk="연속EPS미스",eps="2미스연속",entry="실적후",drop="가이드하향",chase="하·감점",abc="$55/$60/$65"),
"FTRE": dict(px=17.76,h=18.67,l=4.45,ptL=9.5,ptA=15.64,ptH=20,name="Fortrea",sector="헬스케어·CRO",
 feat="임상수탁·바이오고객",mcap="소중형",item="임상시험수탁. 한줄: 제약사 대신 임상시험 대행",
 fin="Q1 EPS대형Beat Rev+1%",cons="PT$15.6 현재+14%",
 sur="EPS2/4연속1 Rev3/4",strat="소폭과열·07-29",
 news="07-29실적",bull="$19–20",base="$15–18",bear="$10–13",
 brk="수주둔화",eps="2/4",entry="$14–16",drop="가이던스하향",chase="중하",abc="$17/$19/$20"),
"GPRE": dict(px=19.23,h=19.65,l=7.07,ptL=10,ptA=17.2,ptH=20,name="Green Plains",sector="소재·저탄소연료/에탄올",
 feat="에탄올마진·옥수수",mcap="소형",item="에탄올·저탄소연료",
 fin="EPSBeat연속·Rev4연속Miss",cons="PT$17.2 현재+12%",
 sur="EPS3/4 3연속 Rev0/4",strat="AMRX유사·매출약·과열주의",
 news="~08-10실적",bull="$20–22",base="$16–19",bear="$12–15",
 brk="마진붕괴",eps="3연속/Rev0",entry="$15–17",drop="스프레드악화",chase="중하",abc="$18/$20/$22"),
"LQDA": dict(px=79.94,h=82.96,l=14.25,ptL=60,ptA=75.14,ptH=109,name="Liquidia",sector="희귀심폐",
 feat="YUTREPIA침투·특허",mcap="~$7B",item="YUTREPIA 흡입치료",
 fin="Q1 제품~$130M 흑자EPS$0.52",cons="PT$75 현재+6%",
 sur="EPS3/4 Rev4/4",strat="펀더강·고점비추격",
 news="3분기연속흑자(IR)",bull="$90–109",base="$70–85",bear="$55–65",
 brk="소송·수요둔화",eps="3/4",entry="$65–72",drop="특허패소",chase="중·고점",abc="$75/$90/$109"),
"PTGX": dict(px=140.91,h=141.10,l=50.49,ptL=100,ptA=124.1,ptH=165,name="Protagonist",sector="바이오·신약",
 feat="파이프라인·파트너",mcap="중형",item="경구펩타이드신약",
 fin="Q1 EPS/Rev대형Beat(일회성가능)",cons="PT$124 현재+14%",
 sur="EPS1/4 Rev1/4",strat="고점과열·서프라이즈약",
 news="~08-05실적",bull="$150–165",base="$120–140",bear="$90–110",
 brk="파이프라인실패",eps="1/4",entry="$115–125",drop="임상실패",chase="하·고점",abc="$130/$145/$165"),
"LFST": dict(px=11.58,h=11.68,l=3.74,ptL=9,ptA=11.5,ptH=14,name="LifeStance Health",sector="헬스케어·외래정신건강",
 feat="외래정신건강수요",mcap="중형",item="외래정신건강클리닉",
 fin="Rev4/4Beat·EPS0/4 5연속Miss",cons="PT$11.5≈현재",
 sur="EPS0/4 5연속Miss Rev4/4",strat="서프라이즈실패→하위",
 news="~08-06실적",bull="$13–14",base="$10–12",bear="$7–9",
 brk="연속미스",eps="5연속Miss",entry="비선호",drop="또미스",chase="하",abc="$11/$12/$14"),
"CLMT": dict(px=42.83,h=42.95,l=12.94,ptL=26,ptA=37.8,ptH=60,name="Calumet",sector="소재·특수제품/재생연료",
 feat="리파이닝·재생연료마진",mcap="소중형",item="특수석유·재생연료",
 fin="Q1 EPS대형Miss RevBeat",cons="PT$37.8 현재+13%",
 sur="EPS2/4 최근Miss Rev3/4",strat="고점·미스→비추격",
 news="~08-07실적",bull="$45–55",base="$35–42",bear="$25–32",
 brk="마진붕괴",eps="최근Miss",entry="$32–36",drop="스프레드악화",chase="하",abc="$40/$48/$55"),
"LIND": dict(px=27.67,h=30.00,l=11.37,ptL=17,ptA=27.5,ptH=34,name="Lindblad Expeditions",sector="여행·탐험",
 feat="예약·유가·소비",mcap="소형",item="탐험크루즈",
 fin="시즌성여행실적",cons="PT$27.5≈현재",
 sur="데이터제한·보수",strat="이질섹터·후순위",
 news="여행수요테마",bull="$31–34",base="$26–29",bear="$20–24",
 brk="예약둔화",eps="제한",entry="비선호",drop="수요둔화",chase="하",abc="$28/$31/$34"),
"CDNA": dict(px=39.73,h=40.47,l=11.26,ptL=21,ptA=32.25,ptH=45,name="CareDx",sector="이식진단",
 feat="검사볼륨·M&A",mcap="~$1.5–2B",item="AlloMap+Naveris인수",
 fin="이식검사·인수확장",cons="PT$32 현재+23%과열",
 sur="혼재",strat="07-30·과열관망",
 news="Naveris인수; 07-30실적",bull="$42–45",base="$32–38",bear="$25–30",
 brk="실적·인수차질",eps="혼재",entry="실적후$30–33",drop="통합실패",chase="하·과열",abc="$35/$40/$45"),
"KRYS": dict(px=354.86,h=382.54,l=130.50,ptL=284,ptA=355.7,ptH=474,name="Krystal Biotech",sector="유전자치료",
 feat="VYJUVEK상업화",mcap="~$10.5B",item="VYJUVEK",
 fin="Q1 매출$116M EPS$1.83",cons="PT$356≈현재",
 sur="연속EPSBeat",strat="고점비추격",
 news="~08-03실적",bull="$400–450",base="$340–380",bear="$280–300",
 brk="처방둔화",eps="연속Beat",entry="$300–320",drop="상업화둔화",chase="하·고점",abc="$360/$400/$450"),
"TVTX": dict(px=56.71,h=60.10,l=15.03,ptL=43,ptA=58.33,ptH=70,name="Travere",sector="희귀신장",
 feat="Filspari상업화",mcap="중소형",item="희귀신장약",
 fin="Q1 매출$127M(+56%)나Miss EPSMiss",cons="PT$58≈현재",
 sur="Q1 EPS-31%Miss L4Q 2/4",strat="Miss감점",
 news="Q1Miss(Yahoo)",bull="$65–70",base="$52–60",bear="$40–48",
 brk="연속Miss",eps="Q1Miss",entry="비선호",drop="또Miss",chase="하",abc="$58/$65/$70"),
"FTNT": dict(px=161.61,h=170.35,l=70.12,ptL=75,ptA=118.42,ptH=215,name="Fortinet",sector="IT·사이버보안",
 feat="방화벽·보안지출",mcap="대형",item="네트워크보안",
 fin="Q1 EPS+37% Rev+7%Beat",cons="PT$118 현재+36%과열",
 sur="EPS4/4 8연속 Rev4/4",strat="Beat최고·가격과열→비추격",
 news="07-29실적",bull="$170–200",base="$120–150",bear="$95–115",
 brk="성장둔화",eps="8연속Beat",entry="$115–125",drop="가이드컷",chase="하·과열",abc="$140/$160/$190"),
"SEZL": dict(px=174.67,h=195.71,l=49.50,ptL=108,ptA=154.17,ptH=190,name="Sezzle",sector="핀테크·BNPL",
 feat="신용손실·규제",mcap="~$5.9B",item="후불결제",
 fin="Q1 EPS+17% RevBeat",cons="PT$154 현재+13%",
 sur="EPS4/4 7연속 Rev4/4",strat="Beat강·과열회피",
 news="~08-06실적",bull="$180–190",base="$150–170",bear="$110–130",
 brk="신용손실",eps="7연속Beat",entry="회피",drop="규제",chase="최하·과열",abc="$160/$180/$190"),
"TXG": dict(px=43.74,h=46.32,l=11.16,ptL=20,ptA=34.17,ptH=50,name="10x Genomics",sector="라이프사이언스툴",
 feat="연구비·도구수요",mcap="중형",item="단일세포/공간분석",
 fin="Q1 매출$151M 손실축소",cons="PT$34 현재+28%과열",
 sur="EPS4/4 Rev4/4",strat="Beat강·과열회피",
 news="~08-06실적",bull="$48–50",base="$32–40",bear="$22–28",
 brk="가이드컷",eps="4/4",entry="회피/$30–34",drop="연구비둔화",chase="최하·과열",abc="$35/$42/$50"),
"DAVE": dict(px=440.42,h=455.98,l=152.21,ptL=250,ptA=373,ptH=485,name="Dave",sector="핀테크",
 feat="ExtraCash·규제",mcap="~$5.6B",item="ExtraCash",
 fin="Q1 매출$158M(+47%)",cons="PT$373 현재+18%",
 sur="EPS3/4 3연속 Rev4/4 변동성큼",strat="과열회피",
 news="~08-05실적",bull="$450–485",base="$360–420",bear="$280–330",
 brk="규제·신용",eps="3/4",entry="회피",drop="규제",chase="최하·과열",abc="$380/$420/$485"),
}

def e(s): return html.escape(str(s))

def block(i, k):
    t=T[k]
    price=f"현재 ${t['px']} | 52주 ${t['l']}–${t['h']} | PT ${t['ptL']}/${t['ptA']}/${t['ptH']} | A/B/C {t['abc']}"
    return f"""
<section class="ticker">
<h2>{i}. {e(k)} — {e(t['name'])}</h2>
<p class="price">{e(price)}</p>
<div class="sec"><h3>1. One-line Thesis</h3><p>{e(t['strat'])} · {e(t['fin'])}</p></div>
<div class="sec"><h3>2. 섹터 · 특징 · 시총</h3>
<table class="kv"><tr><th>섹터</th><td>{e(t['sector'])}</td></tr>
<tr><th>특징</th><td>{e(t['feat'])}</td></tr>
<tr><th>시총</th><td>{e(t['mcap'])}</td></tr></table></div>
<div class="sec"><h3>3. 핵심 아이템</h3><p>{e(t['item'])}</p></div>
<div class="sec"><h3>4. 실적 · 컨센서스 · 서프라이즈 · 전략</h3>
<table class="kv"><tr><th>실적</th><td>{e(t['fin'])}</td></tr>
<tr><th>컨센서스</th><td>{e(t['cons'])}</td></tr>
<tr><th>서프라이즈</th><td>{e(t['sur'])}</td></tr>
<tr><th>전략</th><td>{e(t['strat'])}</td></tr></table></div>
<div class="sec"><h3>5. 뉴스</h3><p>{e(t['news'])}</p></div>
<div class="sec"><h3>6. BULL / BASE / BEAR</h3>
<table class="kv"><tr><th>BULL</th><td>{e(t['bull'])}</td></tr>
<tr><th>BASE</th><td>{e(t['base'])}</td></tr>
<tr><th>BEAR</th><td>{e(t['bear'])}</td></tr>
<tr><th>Breaker</th><td>{e(t['brk'])}</td></tr></table></div>
<div class="sec"><h3>7. 결론</h3>
<table class="kv"><tr><th>섹터</th><td>{e(t['sector'])}</td></tr>
<tr><th>핵심</th><td>{e(t['item'].split('.')[0])}</td></tr>
<tr><th>EPS</th><td>{e(t['eps'])}</td></tr>
<tr><th>신규진입</th><td>{e(t['entry'])}</td></tr>
<tr><th>탈락</th><td>{e(t['drop'])}</td></tr>
<tr><th>Chase</th><td>{e(t['chase'])}</td></tr></table></div>
</section>"""

def main():
    assert Path(FONT_REG).exists()
    sur_rows = []
    for k in ORDER:
        t=T[k]
        sur_rows.append(f"<tr><td>{k}</td><td>{e(t['eps'])}</td><td>{e(t['sur'][:28])}</td><td>{e(t['chase'])}</td></tr>")
    rank_rows = [f"<tr><td>{i}</td><td>{k}</td><td>{e(T[k]['chase'])} · {e(T[k]['entry'])}</td></tr>" for i,k in enumerate(ORDER,1)]
    bodies="".join(block(i,k) for i,k in enumerate(ORDER,1))
    doc=f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"/>
<title>심층분석 {REPORT}</title>
<style>
@font-face{{font-family:N;src:url('file://{FONT_REG}');font-weight:400}}
@font-face{{font-family:N;src:url('file://{FONT_BOLD}');font-weight:700}}
@page{{size:A4;margin:14mm 12mm;@bottom-center{{content:counter(page);font-family:N;font-size:8pt;color:#666}}}}
body{{font-family:N,sans-serif;font-size:9.5pt;line-height:1.4;color:#1a1a1a}}
h1{{font-size:18pt;color:#142846;text-align:center}}
h2{{font-size:13pt;color:#19375f;page-break-after:avoid;margin:0 0 4pt}}
h3{{font-size:10pt;background:#e6eef8;color:#14325a;padding:3pt 6pt;margin:6pt 0 3pt;page-break-after:avoid}}
.cover{{text-align:center;padding-top:28mm;page-break-after:always}}
.ticker{{page-break-before:always}}
.price{{font-size:8.5pt;color:#333;margin:0 0 4pt}}
table.kv,table.data{{width:100%;border-collapse:collapse;margin:3pt 0 6pt;font-size:8.5pt}}
table.data th{{background:#1e3c64;color:#fff;padding:3pt;border:1px solid #1e3c64}}
table.data td{{border:1px solid #c5d0de;padding:3pt;text-align:center}}
table.data tr:nth-child(even) td{{background:#f0f5fa}}
table.kv th{{width:20%;text-align:left;background:#f3f6fa;border:1px solid #d0dae6;padding:3pt 5pt;vertical-align:top}}
table.kv td{{border:1px solid #d0dae6;padding:3pt 5pt;vertical-align:top}}
.meta{{margin:3pt 0;color:#333}}
</style></head><body>
<section class="cover">
<h1>NASDAQ 심층분석 보고서</h1>
<p class="meta" style="font-weight:700;font-size:12pt">{REPORT} · 기준 {ASOF}</p>
<p class="meta">전략: 중단기 모멘텀 · 어닝 서프라이즈 중시 · PT 과열 회피</p>
<p class="meta">폰트: NanumGothic Identity-H · 대상 40종</p>
<p class="meta" style="margin-top:12pt;font-size:8.5pt">KNSA AMRX JAZZ INDV LQDA TXG TVTX CDNA VCYT ECPG KRYS SEPN LIND DAVE<br/>
KYMR XMTR FROG FTRE GPRE FA CMPR BAND AVTX BTSG JBHT NWPX NEO RAPP NESR<br/>
ACHC DNTH CLMT FTNT SEZL ALKS CHEF SLS PTGX LFST ASTH</p>
<p class="meta" style="margin-top:16pt;font-size:8pt;color:#777">면책: 투자 권유가 아닌 공개자료 기반 분석 노트</p>
</section>
<section>
<h2>0. 서프라이즈·Chase 요약</h2>
<table class="data"><thead><tr><th>티커</th><th>EPS</th><th>서프라이즈</th><th>Chase</th></tr></thead>
<tbody>{''.join(sur_rows)}</tbody></table>
</section>
{bodies}
<section class="ticker">
<h2>투자 우선순위 (Chase RR · 오늘 40종)</h2>
<table class="data"><thead><tr><th>순위</th><th>티커</th><th>메모</th></tr></thead>
<tbody>{''.join(rank_rows)}</tbody></table>
<h3>실행 요약</h3>
<p>• 코어/상위: ECPG, NESR 분할, INDV·AMRX·KNSA는 실적 이벤트 관리<br/>
• 서프라이즈 강하나 과열: FTNT, FA, BAND, NWPX, TXG, SEZL, DAVE → 눌림/회피<br/>
• 금주 이벤트(KST): NEO/ACHC/ALKS 07-28 · CHEF/FTNT/BAND/NWPX/CMPR/FTRE 07-29 · INDV/AMRX/CDNA 07-30 · BTSG 07-31 · KNSA 07-28</p>
</section>
</body></html>"""
    Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-20.html").write_text(doc, encoding="utf-8")
    pdf=HTML(string=doc, base_url="file:///").write_pdf()
    for p in OUT:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf)
        print("Wrote", p, p.stat().st_size)

if __name__=="__main__":
    main()
