#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate NASDAQ deep-analysis PDF for 2026-07-18 tickers."""

from fpdf import FPDF
from pathlib import Path

FONT_REG = "/tmp/noto-cjk/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD = "/tmp/noto-cjk/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
OUT_PATHS = [
    Path("/opt/cursor/artifacts/심층분석_2026-07-18_NASDAQ.pdf"),
    Path("/workspace/reports/심층분석_2026-07-18_NASDAQ.pdf"),
]


class Report(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.add_font("noto", "", FONT_REG)
        self.add_font("noto", "B", FONT_BOLD)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("noto", "", 8)
        self.set_text_color(100, 100, 100)
        self.set_x(self.l_margin)
        self.cell(0, 6, "심층분석 보고서 | 2026-07-18 | NASDAQ Chase Strategy", align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        y = self.get_y()
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(4)
        self.set_x(self.l_margin)

    def footer(self):
        self.set_y(-14)
        self.set_font("noto", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"{self.page_no()}", align="C")

    def h1(self, text):
        self.set_x(self.l_margin)
        self.set_font("noto", "B", 16)
        self.set_text_color(20, 40, 70)
        self.multi_cell(0, 9, text)
        self.ln(2)

    def h2(self, text):
        self.set_x(self.l_margin)
        self.set_font("noto", "B", 13)
        self.set_text_color(25, 55, 95)
        self.multi_cell(0, 8, text)
        self.ln(1)

    def h3(self, text):
        self.set_x(self.l_margin)
        self.set_font("noto", "B", 11)
        self.set_text_color(40, 70, 110)
        self.multi_cell(0, 7, text)
        self.ln(1)

    def body(self, text):
        self.set_x(self.l_margin)
        self.set_font("noto", "", 9.5)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def bullet(self, text):
        self.set_x(self.l_margin)
        self.set_font("noto", "", 9.5)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, f"• {text}")
        self.set_x(self.l_margin)

    def kv(self, key, val):
        self.set_x(self.l_margin)
        self.set_font("noto", "B", 9.5)
        self.set_text_color(40, 40, 40)
        label = f"[{key}] "
        self.set_font("noto", "", 9.5)
        self.multi_cell(0, 5.5, label + val)
        self.set_x(self.l_margin)

    def table(self, headers, rows, col_widths=None):
        if col_widths is None:
            w = 190 / len(headers)
            col_widths = [w] * len(headers)
        self.set_x(self.l_margin)
        self.set_font("noto", "B", 8)
        self.set_fill_color(30, 60, 100)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()
        self.set_font("noto", "", 7.5)
        self.set_text_color(30, 30, 30)
        fill = False
        for row in rows:
            self.set_x(self.l_margin)
            if fill:
                self.set_fill_color(240, 245, 250)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                align = "L" if i == len(row) - 1 and len(row) == 3 else "C"
                if i == 0:
                    align = "C"
                self.cell(col_widths[i], 6.5, str(cell)[:40], border=1, fill=True, align=align)
            self.ln()
            fill = not fill
        self.ln(2)
        self.set_x(self.l_margin)

    def section_box(self, title):
        self.ln(1)
        self.set_x(self.l_margin)
        self.set_fill_color(230, 238, 248)
        self.set_font("noto", "B", 10)
        self.set_text_color(20, 50, 90)
        self.cell(0, 7, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)


TICKERS = [
    {
        "ticker": "ECPG",
        "name": "Encore Capital Group",
        "thesis": "채권회수 사이클 확장 + EPS/매출 서프라이즈 연속성이 가장 깨끗한 중단기 모멘텀. 현재가 $91.33 · 시총 ~$2.0B · 촉매: 2026-08-06 06:00 KST 실적 콜.",
        "sector": "금융 · 채권회수(NPL)",
        "sector_feat": "금리·연체율에 민감. 포트폴리오 매입 가격과 회수율이 핵심. 성장주보다 현금흐름·운영 레버리지 장세.",
        "mcap_rank": "시총 ~$2.0B. 동종 소형 금융 내 상위권. 절대 시총은 중소형.",
        "items": "연체채권(NPL) 매입 후 회수·법적 추심. 한 줄: 싸게 산 빚을 회수해 이익을 내는 회사.",
        "financials": "Q1'26 매출 $475M(YoY +21%), Non-GAAP EPS $3.86. QoQ도 고수준 유지. 회수 효율과 포트폴리오 회전이 개선 중.",
        "consensus": "대형 IB/전문 증권: Buy 우세. PT 저 $105 / 평균 $113 / 고 $120 (StockAnalysis). 현재가 대비 평균 +24% 업사이드.",
        "surprise": "최근 4Q EPS 4/4 Beat, Rev 4/4 Beat, 연속 6분기 EPS Beat. Q1'26 EPS +26%, 평균 서프라이즈 ~+56%. 서프라이즈 품질 최상.",
        "strategy_view": "우리 전략(어닝 서프라이즈·중단기 추격)과 정합. PT 프리미엄 없고 Beat 신뢰 최고 → 코어 1순위.",
        "news": [
            "채권회수·소비자 신용 연체 관련 섹터 관심 지속 (회사 IR / 실적자료).",
            "Q1 실적 발표에서 EPS·매출 모두 컨센서스 상회 (ChartMill / Benzinga earnings history).",
            "차기 실적: 2026-08-05/06 전후 (회사 일정).",
        ],
        "bull": "연속 Beat + 가이던스 상향 → $110–120 (PT 고점권).",
        "base": "완만한 회수 개선 → $100–110.",
        "bear": "회수율 둔화·규제/금리 쇼크 → $80–88.",
        "breaker": "연속 Beat 끊김, 포트폴리오 매입 마진 악화, 규제 강화.",
        "conclusion": {
            "섹터": "금융·채권회수",
            "핵심 아이템": "NPL 회수",
            "EPS": "Non-GAAP 강세, 6연속 Beat",
            "신규진입": "$88–93 (보유·분할 가능)",
            "탈락": "회수율 둔화·가이던스 하향",
            "Chase": "최상 · 코어",
        },
        "price": "현재 $91.33 | 52주 $35.67–$94.60 | PT $105/$113/$120 | A/B/C $100/$110/$120",
    },
    {
        "ticker": "ASTH",
        "name": "Astrana Health",
        "thesis": "Care Partners 성장 + 최근 2연속 Adj EPS 대형 Beat로 턴어라운드 확인. $44.94 · ~$2.2B · 촉매: 2026-08-07 06:30 KST 콜.",
        "sector": "헬스케어 서비스 · Value-based Care",
        "sector_feat": "보험·메디케어 정책과 MSO/의사네트워크 확장이 핵심. 매출 성장은 빠르나 마진·레버리지 관리가 관건.",
        "mcap_rank": "시총 ~$2.2B. 소형 헬스케어 서비스. 대형 보험사 대비 니치.",
        "items": "의사 중심 기술·Care Partners로 가치기반 진료. 한 줄: 병원/클리닉 네트워크를 묶어 효율적으로 환자를 관리.",
        "financials": "Q1'26 매출 $965M(YoY +56%), Adj EBITDA $66.3M(+82%), Adj EPS $0.74. QoQ 규모 확대 지속.",
        "consensus": "컨센서스 Hold~Buy 혼재. PT 저 $36 / 평균 $48.6 / 고 $65. 현재가 대비 평균 +8% 내외.",
        "surprise": "최근 4Q EPS 2/4 Beat이나 Q4'25·Q1'26 연속 대형 Beat(Adj). Rev는 대체로 4/4 Beat. GAAP/Adj 혼선 주의.",
        "strategy_view": "최근 서프라이즈 턴은 긍정적. 보유 적합. 다만 과거 미스 이력으로 ECPG보다 한 단계 아래.",
        "news": [
            "Q1'26 실적: Adj EPS·매출 컨센서스 상회 (Yahoo Finance / IR 2026-05-07).",
            "FY2026 매출·Adj EBITDA 가이던스 재확인 (회사 IR).",
            "Q2 실적 일정: 2026-08-06 장마감 후 발표·콜 (IR).",
        ],
        "bull": "가이던스 상향 + 레버리지 개선 → $55–65.",
        "base": "성장 유지·마진 안정 → $48–55.",
        "bear": "Adj/GAAP 괴리·비용 재확대 → $36–40.",
        "breaker": "Q2 Adj 미스, 레버리지 재상승, Care Partners 성장 둔화.",
        "conclusion": {
            "섹터": "헬스케어 서비스",
            "핵심 아이템": "Care Partners / VBC",
            "EPS": "Adj 최근 2연속 대형 Beat",
            "신규진입": "$42–46",
            "탈락": "Q2 가이던스 미스·레버리지 악화",
            "Chase": "상 · 코어 보유",
        },
        "price": "현재 $44.94 | 52주 $18.08–$51.60 | PT $36/$48.6/$65 | A/B/C $48/$55/$62",
    },
    {
        "ticker": "NESR",
        "name": "National Energy Services Reunited",
        "thesis": "MENA 오일필드 서비스 실행력 + Q1 EPS +20%대 Beat로 실적 신뢰 회복. $27.99 · ~$2.8B · 차기 실적 ~08-05 전후.",
        "sector": "에너지 · 오일필드 서비스(MENA)",
        "sector_feat": "중동 자본지출·비전통(프랙) 활동에 연동. 지정학 리스크와 동시에 구조적 프로젝트 파이프라인.",
        "mcap_rank": "시총 ~$2.8B. 지역 특화 중형. SLB/HAL 대비 중소형 니치.",
        "items": "시추·완성·프랙 등 통합 에너지 서비스. 한 줄: 중동 유전에 장비·인력을 제공하는 회사.",
        "financials": "Q1'26 매출 $405M(YoY +34%), Diluted EPS $0.23, Adj 기준 Street ~$0.26 Beat. Adj EBITDA $76.7M(+23% YoY).",
        "consensus": "Buy 톤. PT 저 $30 / 평균 $33 / 고 $36. 현재가 대비 평균 +18%.",
        "surprise": "Q1'26 EPS +20~27% Beat, Q4'25 +23% Beat. L4Q 3~4/4(소스별). 최소 최근 2연속 확정 Beat.",
        "strategy_view": "서프라이즈·PT 업사이드·가격대 모두 진입 가능. 신규 1순위 후보(분할).",
        "news": [
            "Q1'26 사상 최고 매출, 사우디 Jafurah 프랙 기여 (SEC 8-K / IR).",
            "자본환원(캐피탈 리턴) 논의·실적 개선 보도 (Yahoo/Barchart).",
            "지정학에도 운영 레질리언스 강조 (실적 코멘트).",
        ],
        "bull": "활동량 가속 + 마진 확장 → $33–36.",
        "base": "완만한 성장 → $30–33.",
        "bear": "지정학·가동률 하락 → $22–25.",
        "breaker": "중동 프로젝트 지연, 마진 압축, EPS Beat 단절.",
        "conclusion": {
            "섹터": "에너지 서비스(MENA)",
            "핵심 아이템": "통합 OFS / 프랙",
            "EPS": "최근 연속 Beat",
            "신규진입": "$25–28 분할",
            "탈락": "지정학·유틸리티 둔화",
            "Chase": "상 · 신규 분할",
        },
        "price": "현재 $27.99 | 52주 $6.00–$30.31 | PT $30/$33/$36 | A/B/C $31/$34/$36",
    },
    {
        "ticker": "KNSA",
        "name": "Kiniksa Pharmaceuticals",
        "thesis": "Arcalyst 매출은 Rev 4/4 Beat이나 EPS는 들쭉날쭉 → 07-28 실적 전 반만. $63.95 · ~$4.9B · 촉매: 07-28 ~20:00 KST.",
        "sector": "바이오 · 희귀/염증",
        "sector_feat": "상업화 바이오. 단일 제품 의존도가 높아 볼륨·가격·적응증 확장이 주가 핵심.",
        "mcap_rank": "시총 ~$4.9B. 중소형 상업화 바이오.",
        "items": "Arcalyst(릴로나셉트) 등. 한 줄: 희귀 염증 질환 치료제를 파는 바이오.",
        "financials": "Q1'26 매출 $214M(YoY 강세), EPS $0.27. 매출 성장은 견조, EPS는 분기 변동.",
        "consensus": "Buy 우세. PT 저 $60 / 평균 $68.3 / 고 $74. 현재가 대비 평균 +7%.",
        "surprise": "EPS 2/4 Beat(연속 1), Rev 4/4 Beat. Q1'26 EPS +32%. Q3·Q4'25 EPS Miss.",
        "strategy_view": "매출 서프라이즈는 좋으나 EPS 불안정 → 풀베팅 금지, 실적 전 반만.",
        "news": [
            "Arcalyst 처방·매출 성장 지속 (회사 실적).",
            "Q2 실적 예정 2026-07-27/28 (ChartMill/IR).",
            "희귀질환 상업화 바이오 섹터 변동성 확대 (일반 섹터 동향).",
        ],
        "bull": "Q2 Beat + 가이던스 상향 → $70–74.",
        "base": "매출 유지·EPS 혼조 → $64–70.",
        "bear": "EPS 재미스 → $55–60.",
        "breaker": "Q2 EPS·가이던스 미스, Arcalyst 성장 둔화.",
        "conclusion": {
            "섹터": "바이오(희귀염증)",
            "핵심 아이템": "Arcalyst",
            "EPS": "2/4 · 연속 1 · Rev는 완벽",
            "신규진입": "실적 전 반만 $60–64",
            "탈락": "Q2 EPS/가이드 미스",
            "Chase": "중상 · 반만",
        },
        "price": "현재 $63.95 | 52주 $26.27–$67.53 | PT $60/$68.3/$74 | A/B/C $68/$74/$80",
    },
    {
        "ticker": "INDV",
        "name": "Indivior",
        "thesis": "EPS/Rev 4/4·대형 서프라이즈 머신이나 07-30 실적 이벤트 리스크. $40.54 · ~$4.9B · 보유·추가 금지.",
        "sector": "제약 · 중독치료(오피오이드 의존)",
        "sector_feat": "정책·소송·약가·장기작용형 주사제 침투율이 핵심. 규제 헤드라인에 민감.",
        "mcap_rank": "시총 ~$4.9B. 특수 제약 중소형.",
        "items": "SUBLOCADE 등 의존증 치료. 한 줄: 오피오이드 중독 치료 약을 파는 제약사.",
        "financials": "Q1'26 매출 $317M, EPS $0.96. YoY·QoQ 모두 개선 추세. 장기작용형 제품 믹스 개선.",
        "consensus": "Buy. PT 저 $46 / 평균 $50.8 / 고 $59. 현재가 대비 평균 +25%.",
        "surprise": "EPS 4/4·Rev 4/4, 연속 4+. Q1'26 EPS +44%, Rev +14%. 평균 EPS 서프라이즈 ~+57%.",
        "strategy_view": "서프라이즈 품질은 최상이나 이벤트 직전 → 홀드, 추격·추가 금지.",
        "news": [
            "연속 대형 Beat 기록 (ChartMill).",
            "Q2 실적 2026-07-30 (회사 일정).",
            "중독치료·장기작용형 주사제 침투 관련 섹터 관심 지속 (업계 보도).",
        ],
        "bull": "또 Beat + 가이드 상향 → $50–58.",
        "base": "성장 유지 → $46–52.",
        "bear": "소송/가격·볼륨 쇼크 → $32–36.",
        "breaker": "소송·약가 압력, 볼륨 가이던스 하향.",
        "conclusion": {
            "섹터": "제약(중독치료)",
            "핵심 아이템": "SUBLOCADE 등",
            "EPS": "4/4 Beat 머신",
            "신규진입": "07-30 전 관망·소량만",
            "탈락": "소송/가이드 하향",
            "Chase": "상 · 이벤트 대기",
        },
        "price": "현재 $40.54 | 52주 $15.55–$42.81 | PT $46/$50.8/$59 | A/B/C $46/$52/$58",
    },
    {
        "ticker": "JBHT",
        "name": "J.B. Hunt Transport Services",
        "thesis": "EPS 4연속 Beat 확인됐으나 $291은 고점권·이미 상당 반영. 눌림 대기. $291.41 · ~$27B.",
        "sector": "산업재 · 운송/물류",
        "sector_feat": "화물 사이클·운임·인터모달 점유율이 핵심. 경기민감 대형주.",
        "mcap_rank": "시총 ~$27B. 운송 대장급.",
        "items": "Intermodal, Dedicated, ICS, Truckload. 한 줄: 트럭·철도 연계로 화물을 옮기는 물류 회사.",
        "financials": "Q2'26 매출 $3.50B(+19% YoY), EPS $1.91(+45% YoY). 운영이익 +32%.",
        "consensus": "Buy/Overweight 혼재. PT 저 $200 / 평균 $298 / 고 $370. 현재가 ≈ 평균 PT.",
        "surprise": "Q2'26 Beat, Q1/Q4/Q3도 Beat → EPS 4연속. Rev는 분기별 혼조.",
        "strategy_view": "서프라이즈는 우수하나 가격이 이미 반영 → 추격 금지, $260–275 대기.",
        "news": [
            "Q2'26 실적: EPS $1.91, 매출 +19% (회사 IR 2026-07-15).",
            "화물 수요·생산성·비용 절감 강조 (실적 발표).",
            "운송 섹터 전반 매크로(금리·소비) 민감 (매크로 보도).",
        ],
        "bull": "사이클 연장 → $320–350.",
        "base": "완만한 개선 → $290–310.",
        "bear": "운임·볼륨 피크아웃 → $240–260.",
        "breaker": "화물 둔화, 가이던스 하향, 마진 피크아웃.",
        "conclusion": {
            "섹터": "운송·물류",
            "핵심 아이템": "Intermodal/DCS",
            "EPS": "4연속 Beat",
            "신규진입": "대기 $260–275",
            "탈락": "운임·볼륨 피크아웃",
            "Chase": "중 · 눌림만",
        },
        "price": "현재 $291.41 | 52주 $130.12–$299.76 | PT $200/$298/$370 | A/B/C $300/$320/$350",
    },
    {
        "ticker": "EXTR",
        "name": "Extreme Networks",
        "thesis": "EPS 4연속 Beat이나 매출은 아슬아슬, PT 평균이 현재가 아래. 눌림 선호. $30.34 · ~$4.0B · ~08-05 실적.",
        "sector": "IT · 엔터프라이즈 네트워킹",
        "sector_feat": "캠퍼스/클라우드 네트 교체 사이클. AI 트래픽·보안 수요와 연동되나 경쟁(Cisco 등) 치열.",
        "mcap_rank": "시총 ~$4.0B. 네트워킹 중소형.",
        "items": "스위치·무선·클라우드 관리. 한 줄: 기업·캠퍼스 네트워크 장비·소프트웨어.",
        "financials": "최근 분기 EPS $0.26 전후, 매출 ~$317M. YoY 성장은 있으나 QoQ 정체 구간.",
        "consensus": "Hold/Buy 혼재. PT 저 $22.5 / 평균 $29.6 / 고 $39. 평균 PT < 현재가.",
        "surprise": "EPS 4/4 연속 Beat(평균 +5~6%). Rev 2/4(최근 2Q 소폭 Miss).",
        "strategy_view": "EPS Beat는 좋지만 Rev·PT가 약함 → 현재 추격보다 $27–29 선호.",
        "news": [
            "연속 EPS Beat, 최근 매출은 컨센서스 근처/소폭 하회 (ChartMill).",
            "엔터프라이즈 네트·AI 인프라 수요 테마 (섹터 보도).",
            "차기 실적 ~2026-08-04/05 (일정).",
        ],
        "bull": "매출 Beat 복귀 + 가이드 상향 → $36–39.",
        "base": "EPS만 Beat → $30–33.",
        "bear": "매출 가이던스 하향 → $24–27.",
        "breaker": "매출 가이던스 컷, 경쟁 심화.",
        "conclusion": {
            "섹터": "IT 네트워킹",
            "핵심 아이템": "캠퍼스/클라우드 네트",
            "EPS": "4연속 Beat / Rev 혼조",
            "신규진입": "$27–29",
            "탈락": "매출 가이드 하향",
            "Chase": "중 · 눌림",
        },
        "price": "현재 $30.34 | 52주 $13.48–$33.73 | PT $22.5/$29.6/$39 | A/B/C $33/$36/$39",
    },
    {
        "ticker": "BTSG",
        "name": "BrightSpring Health Services",
        "thesis": "Rev 4/4 Beat, EPS는 Q4 미스 후 Q1 회복. 고점권이라 추가 금지·07-31 대기. $70.69 · ~$14.7B · 07-31 21:30 KST.",
        "sector": "헬스케어 서비스 · Specialty Pharmacy / Home Care",
        "sector_feat": "약제비·홈케어 수요는 구조적. 통합·마진·레버리지가 리스크.",
        "mcap_rank": "시총 ~$14.7B. 헬스케어 서비스 중대형.",
        "items": "전문약국 + 재택·커뮤니티 케어. 한 줄: 약 배송·재택 돌봄을 키우는 헬스케어 서비스.",
        "financials": "Q1'26 매출 $3.61B, EPS $0.39. YoY 매출·이익 성장. 스페셜티 약국 중심.",
        "consensus": "Buy 우세. PT 저 $49 / 평균 $74.9 / 고 $90. 현재가 ≈ 평균 근처.",
        "surprise": "EPS 3/4(연속 1), Rev 4/4. Q1'26 EPS +23%. Q4'25 EPS Miss.",
        "strategy_view": "보유분은 유지 가능하나 고점 추격·추가 매수 비권장. 실적 확인 후.",
        "news": [
            "Q1 Beat 후 주가 강세 (FXEmpire/실적 반응).",
            "Q2 실적 2026-07-31 (Benzinga).",
            "스페셜티 약국·홈케어 통합 스토리 지속 (섹터 보도).",
        ],
        "bull": "또 Beat + 마진 개선 → $80–90.",
        "base": "성장 유지 → $70–78.",
        "bear": "마진·통합 비용 쇼크 → $55–62.",
        "breaker": "마진 압축, 통합 실패, EPS 재미스.",
        "conclusion": {
            "섹터": "헬스케어 서비스",
            "핵심 아이템": "Specialty pharmacy + home care",
            "EPS": "3/4 · Rev 4/4",
            "신규진입": "대기 $58–62 / 추가 금지",
            "탈락": "마진·통합 쇼크",
            "Chase": "중 · 보유만",
        },
        "price": "현재 $70.69 | 52주 $19.01–$72.22 | PT $49/$74.9/$90 | A/B/C $75/$82/$90",
    },
    {
        "ticker": "VCYT",
        "name": "Veracyte",
        "thesis": "Rev 4/4·EPS 3/4·최근 2연속 Beat. 품질은 괜찮으나 PT≈현재라 눌림만. $59.13 · ~$4.7B.",
        "sector": "헬스케어 · 분자진단/게놈",
        "sector_feat": "검사 볼륨·보험 급여·신제품 침투가 핵심. 성장 진단주.",
        "mcap_rank": "시총 ~$4.7B. 진단 중소형.",
        "items": "Afirma 등 분자진단. 한 줄: 조직·유전자 검사로 불필요한 수술을 줄이는 진단 회사.",
        "financials": "Q1'26 매출 $139M, EPS $0.35. YoY 성장, 최근 분기 수익성 개선.",
        "consensus": "Buy/Hold 혼재. PT 저 $47 / 평균 $59 / 고 $70. 평균 ≈ 현재가.",
        "surprise": "EPS 3/4(연속 2), Rev 4/4. Q1'26 EPS +133%. Q2'25 EPS Miss.",
        "strategy_view": "서프라이즈는 양호하나 업사이드 제한 → 랭킹 중하위, $52–55 대기.",
        "news": [
            "연속 매출 Beat, 최근 EPS 대형 Beat (ChartMill).",
            "분자진단·암 진단 섹터 성장 테마 (업계).",
            "보험 급여·검사 볼륨이 관전 포인트 (섹터).",
        ],
        "bull": "볼륨 가속 → $68–75.",
        "base": "완만한 성장 → $58–65.",
        "bear": "급여·볼륨 둔화 → $47–52.",
        "breaker": "보험 급여 축소, 검사 볼륨 둔화.",
        "conclusion": {
            "섹터": "분자진단",
            "핵심 아이템": "Afirma 등",
            "EPS": "3/4 · 연속 2",
            "신규진입": "$52–55",
            "탈락": "보험·볼륨 둔화",
            "Chase": "중하 · 눌림",
        },
        "price": "현재 $59.13 | 52주 $22.61–$60.91 | PT $47/$59/$70 | A/B/C $62/$68/$75",
    },
    {
        "ticker": "TGTX",
        "name": "TG Therapeutics",
        "thesis": "BRIUMVI 스토리는 있으나 EPS 4연속 미스 → 서프라이즈 전략에서 감점. $54.87 · ~$7.8B.",
        "sector": "바이오 · 혈액암/면역",
        "sector_feat": "상업화 바이오. 매출 성장과 수익성 전환 속도가 핵심. EPS 추정치 괴리 주의.",
        "mcap_rank": "시총 ~$7.8B. 상업화 바이오 중형.",
        "items": "BRIUMVI(ublituximab). 한 줄: 다발성 경화증 등 혈액·면역 질환 치료제.",
        "financials": "Q1'26 매출 $205M(YoY 강세), EPS $0.18. 매출은 성장, 이익은 컨센서스 하회 반복.",
        "consensus": "Buy 혼재, PT 분산 큼. 저 $20 / 평균 $55.9 / 고 $83.",
        "surprise": "EPS 0/4 · 4연속 Miss(평균 −38%). Rev 2/4. Q1'26 EPS −40%.",
        "strategy_view": "테마성 모멘텀은 있으나 어닝 서프라이즈 전략과 불일치 → 후순위.",
        "news": [
            "매출 성장에도 EPS 반복 미스 (ChartMill).",
            "MS/혈액암 치료제 경쟁 구도 (섹터 보도).",
            "주가 52주 고점권 근접 후 조정 (가격 데이터).",
        ],
        "bull": "EPS Beat 전환 + 점유율 확대 → $65–75.",
        "base": "매출만 성장 → $50–58.",
        "bear": "또 EPS 미스 → $40–45.",
        "breaker": "연속 EPS 미스 지속, 경쟁 심화.",
        "conclusion": {
            "섹터": "바이오(혈액암/MS)",
            "핵심 아이템": "BRIUMVI",
            "EPS": "4연속 Miss",
            "신규진입": "비선호 / 깊게 $45–48",
            "탈락": "또 EPS 미스",
            "Chase": "하 · 감점",
        },
        "price": "현재 $54.87 | 52주 $25.28–$59.30 | PT $20/$55.9/$83 | A/B/C $55/$65/$75",
    },
    {
        "ticker": "KRYS",
        "name": "Krystal Biotech",
        "thesis": "EPS 4연속 Beat 우수하나 $355≈PT 평균·고점권 → 추격 비추천. $354.86 · ~$10.5B.",
        "sector": "바이오 · 유전자치료",
        "sector_feat": "상업화 유전자치료. 적응증 확장·해외 승인·파이프라인이 밸류에이션 핵심.",
        "mcap_rank": "시총 ~$10.5B. 유전자치료 중대형.",
        "items": "VYJUVEK(B-VEC). 한 줄: 희귀 피부질환(DEB) 유전자치료제를 판매.",
        "financials": "Q1'26 매출 $116M, EPS $1.83. YoY·QoQ 성장. 현금 여력 양호(과거 공시).",
        "consensus": "Buy. PT 저 $284 / 평균 $355.7 / 고 $474. 현재가 ≈ 평균.",
        "surprise": "EPS 4/4 연속 Beat(Q2'25–Q1'26). Q1'26 +26%. Rev도 Beat.",
        "strategy_view": "서프라이즈는 최상급이나 가격·PT가 이미 반영 → 랭킹 하단, 눌림 대기.",
        "news": [
            "Q1'26 EPS·매출 Beat (MarketBeat / Meyka).",
            "영국 MHRA VYJUVEK 승인 관련 보도 (2026-05).",
            "DEB 상업화·파이프라인 확장 스토리 (회사/섹터).",
        ],
        "bull": "적응증·지역 확장 → $400–450.",
        "base": "안정 성장 → $340–380.",
        "bear": "상업화 둔화 → $280–300.",
        "breaker": "처방 둔화, 파이프라인 실패, 고밸류 디레이팅.",
        "conclusion": {
            "섹터": "유전자치료",
            "핵심 아이템": "VYJUVEK",
            "EPS": "4연속 Beat",
            "신규진입": "비추격 · $300–320 대기",
            "탈락": "상업화 둔화",
            "Chase": "하 · 고점",
        },
        "price": "현재 $354.86 | 52주 $130.50–$382.54 | PT $284/$356/$474 | A/B/C $360/$400/$450",
    },
    {
        "ticker": "DAVE",
        "name": "Dave Inc.",
        "thesis": "최근 3연속 EPS Beat·Rev 4/4이나 $440>PT $373 → 과열 추격 금지. $440.42 · ~$5.6B · ~08-05.",
        "sector": "핀테크 · 소비자 금융앱",
        "sector_feat": "회원 성장·ExtraCash 수익화·신용비용·규제. 실적 변동성 큼.",
        "mcap_rank": "시총 ~$5.6B. 핀테크 중소형.",
        "items": "예산·현금 선지급(ExtraCash) 앱. 한 줄: 급여 전 소액 현금과 뱅킹을 제공하는 앱.",
        "financials": "Q1'26 매출 $158M(+47% YoY), Adj EPS 강세. 성장은 빠르나 가이던스 가시성 이슈.",
        "consensus": "Buy 혼재. PT 저 $250 / 평균 $373 / 고 $485. 현재가가 평균 PT 대비 +18% 프리미엄.",
        "surprise": "EPS 3/4·연속 3, Rev 4/4. Q1'26 +37%. Q2'25는 대형 Miss. 서프라이즈 변동성 극대.",
        "strategy_view": "Beat여도 PT 대비 과열 → 전략상 비추격.",
        "news": [
            "Q1 Beat 후에도 가이던스 공백으로 변동성 (ChartMill).",
            "AI·수익화 내러티브와 실적 테스트 (Barchart 분석).",
            "차기 실적 ~2026-08-05.",
        ],
        "bull": "가이드 제시 + Beat → $450–485.",
        "base": "성장 유지·밸류 부담 → $380–420.",
        "bear": "규제·신용비용 → $300–350.",
        "breaker": "규제, 신용손실, 가이던스 실망.",
        "conclusion": {
            "섹터": "핀테크",
            "핵심 아이템": "ExtraCash",
            "EPS": "3/4 · 연속 3 · 변동성 큼",
            "신규진입": "회피 / $320–350만",
            "탈락": "규제·신용비용",
            "Chase": "최하권 · 과열",
        },
        "price": "현재 $440.42 | 52주 $152.21–$455.98 | PT $250/$373/$485 | A/B/C $400/$450/$485",
    },
    {
        "ticker": "SEZL",
        "name": "Sezzle",
        "thesis": "EPS 4연속 Beat 우수하나 $175>PT $154 → 과열. $174.67 · ~$5.9B.",
        "sector": "핀테크 · BNPL",
        "sector_feat": "거래액·신용손실·규제·소비자 건전성. 성장과 리스크가 동시.",
        "mcap_rank": "시총 ~$5.9B. BNPL 중소형.",
        "items": "후불결제(BNPL). 한 줄: 나눠 갚는 결제 서비스를 제공하는 핀테크.",
        "financials": "Q1'26 매출 $136M, EPS $1.47. YoY 고성장. 수익성 개선 스토리.",
        "consensus": "Buy 혼재. PT 저 $108 / 평균 $154 / 고 $190. 현재가 평균 대비 +13% 프리미엄.",
        "surprise": "EPS 4/4 연속 Beat(평균 ~+16%). Rev 3/4. Q1'26 EPS +17%.",
        "strategy_view": "서프라이즈는 좋지만 가격이 Street 앞섬 → 비추격.",
        "news": [
            "연속 EPS Beat (ChartMill).",
            "BNPL 규제·신용 리스크 섹터 이슈 (업계).",
            "차기 실적 ~2026-08-05.",
        ],
        "bull": "성장+마진 → $180–190.",
        "base": "밸류 조정 → $150–170.",
        "bear": "신용손실·규제 → $110–130.",
        "breaker": "신용손실 급증, 규제 강화.",
        "conclusion": {
            "섹터": "BNPL/핀테크",
            "핵심 아이템": "Sezzle 할부",
            "EPS": "4연속 Beat",
            "신규진입": "회피",
            "탈락": "신용손실·규제",
            "Chase": "최하 · 과열",
        },
        "price": "현재 $174.67 | 52주 $49.50–$195.71 | PT $108/$154/$190 | A/B/C $160/$180/$190",
    },
]


def write_cover(pdf: Report):
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font("noto", "B", 22)
    pdf.set_text_color(20, 40, 70)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 12, "NASDAQ 심층분석 보고서", align="C")
    pdf.ln(4)
    pdf.set_font("noto", "B", 14)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 8, "2026년 7월 18일 티커 유니버스", align="C")
    pdf.ln(8)
    pdf.set_font("noto", "", 11)
    pdf.set_text_color(50, 50, 50)
    for line in [
        "전략: NASDAQ 전용 · 중단기 모멘텀 추격 · 어닝 서프라이즈 중시",
        "기준가: 2026-07-17 종가",
        "PT 출처: StockAnalysis (S&P Global 컨센서스)",
        "서프라이즈: ChartMill / Benzinga / MarketBeat / 회사 IR",
    ]:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 7, line, align="C")
    pdf.ln(10)
    pdf.set_font("noto", "B", 11)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 7, "분석 대상 (13)", align="C")
    pdf.set_font("noto", "", 10)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, "ECPG · ASTH · NESR · KNSA · INDV · JBHT · EXTR", align="C")
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, "BTSG · VCYT · TGTX · KRYS · DAVE · SEZL", align="C")
    pdf.ln(12)
    pdf.set_font("noto", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, "면책: 본 보고서는 투자 권유가 아니며, 공개 자료 기반의 분석 노트입니다.", align="C")
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, "실제 매매 전 최신 시세·공시·리스크를 재확인하십시오.", align="C")


def write_surprise_summary(pdf: Report):
    pdf.add_page()
    pdf.h1("0. 어닝 서프라이즈 요약 (최근 4분기)")
    pdf.body("어닝 서프라이즈 여부는 본 전략의 핵심 필터입니다. EPS Beat 횟수·연속성·매출 Beat를 함께 봅니다.")
    headers = ["티커", "EPS", "연속", "Rev", "품질"]
    rows = [
        ["ECPG", "4/4", "6연속", "4/4", "최상"],
        ["INDV", "4/4", "4연속+", "4/4", "최상"],
        ["EXTR", "4/4", "4연속", "2/4", "상(매출혼조)"],
        ["SEZL", "4/4", "4연속", "3/4", "상(과열)"],
        ["KRYS", "4/4", "4연속", "4/4", "상(고점)"],
        ["JBHT", "4/4", "4연속", "혼조", "상(반영됨)"],
        ["NESR", "3~4/4", "2~4연속", "3~4/4", "상"],
        ["DAVE", "3/4", "3연속", "4/4", "중상(변동)"],
        ["VCYT", "3/4", "2연속", "4/4", "중상"],
        ["BTSG", "3/4", "1연속", "4/4", "중"],
        ["ASTH", "2/4", "2연속", "4/4", "중(턴)"],
        ["KNSA", "2/4", "1연속", "4/4", "중"],
        ["TGTX", "0/4", "0(4미스)", "2/4", "하"],
    ]
    pdf.table(headers, rows, [28, 28, 38, 28, 68])
    pdf.body("가격 참고: 현재가 / 52주 / PT(저·평균·고)는 각 티커 본문에 포함.")


def write_ticker(pdf: Report, i: int, t: dict):
    pdf.add_page()
    pdf.h1(f"{i}. {t['ticker']} — {t['name']}")
    pdf.body(t["price"])

    pdf.section_box("1. One-line Thesis")
    pdf.body(t["thesis"])

    pdf.section_box("2. 섹터 · 섹터주 특징 · 시총 순위")
    pdf.kv("섹터", t["sector"])
    pdf.kv("특징", t["sector_feat"])
    pdf.kv("시총/순위", t["mcap_rank"])

    pdf.section_box("3. 핵심 아이템")
    pdf.body(t["items"])

    pdf.section_box("4. 실적 (YoY+QoQ · 컨센서스 · 서프라이즈 · 전략 비교)")
    pdf.kv("실적", t["financials"])
    pdf.kv("컨센서스", t["consensus"])
    pdf.kv("서프라이즈", t["surprise"])
    pdf.kv("전략 관점", t["strategy_view"])

    pdf.section_box("5. 섹터·기업 뉴스 (출처)")
    for n in t["news"]:
        pdf.bullet(n)

    pdf.section_box("6. 중단기 시나리오 (BULL / BASE / BEAR)")
    pdf.kv("BULL", t["bull"])
    pdf.kv("BASE", t["base"])
    pdf.kv("BEAR", t["bear"])
    pdf.kv("Thesis breaker", t["breaker"])

    pdf.section_box("7. 결론 표")
    c = t["conclusion"]
    for k in ["섹터", "핵심 아이템", "EPS", "신규진입", "탈락", "Chase"]:
        pdf.kv(k, c[k])


def write_ranking(pdf: Report):
    pdf.add_page()
    pdf.h1("투자 우선순위 재편성 (Chase RR)")
    pdf.body("당일 유니버스(13종)만 대상으로 재랭킹. 어닝 서프라이즈 · PT 대비 위치 · 이벤트 · 보유 포지션을 반영.")
    headers = ["순위", "티커", "핵심 이유"]
    rows = [
        ["1", "ECPG", "6연속 Beat + PT 업사이드 + 코어"],
        ["2", "ASTH", "최근 2연속 대형 Beat + 합리적 진입"],
        ["3", "NESR", "연속 Beat + PT 여유 + 분할 가능"],
        ["4", "KNSA", "Rev 완벽·EPS 불안정 → 반만"],
        ["5", "INDV", "Beat 머신 · 07-30 이벤트"],
        ["6", "JBHT", "4연속 Beat · 고점 눌림 대기"],
        ["7", "EXTR", "EPS 4연속 · Rev/PT 약함"],
        ["8", "BTSG", "Rev 강 · 고점 · 추가 금지"],
        ["9", "VCYT", "3/4 Beat · PT≈현재"],
        ["10", "TGTX", "EPS 4연속 미스 감점"],
        ["11", "KRYS", "Beat 우수하나 고점"],
        ["12", "DAVE", "Beat나 PT 대비 과열"],
        ["13", "SEZL", "Beat나 PT 대비 과열"],
    ]
    pdf.table(headers, rows, [22, 28, 140])

    pdf.h2("실행 우선순위")
    pdf.bullet("유지(코어 홀드): ECPG, ASTH")
    pdf.bullet("관전: INDV(07-30), KNSA 반만(07-28), BTSG(07-31·추가X)")
    pdf.bullet("신규 1순위: NESR $25–28 분할")
    pdf.bullet("신규 대기: JBHT $260–275, EXTR $27–29, BTSG $58–62")
    pdf.bullet("비추격: DAVE, SEZL, KRYS 고점, TGTX(미스 패턴)")

    pdf.h2("보유 포트폴리오 메모 (참고)")
    pdf.bullet("ECPG avg $92.32 — 서프라이즈 최상, 코어 홀드")
    pdf.bullet("ASTH avg $45.10 — 최근 턴, 홀드")
    pdf.bullet("INDV avg $40.99 — Beat 머신, 추가 금지·실적 관전")
    pdf.bullet("BTSG avg $68.38 — 추가 금지, 07-31 대기")
    pdf.bullet("현금 ~$7.42 — 추격보다 적립·대기 우선")

    pdf.ln(6)
    pdf.set_font("noto", "", 8)
    pdf.set_text_color(90, 90, 90)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, "데이터 기준일: 2026-07-17 종가 / 보고서일: 2026-07-18")
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, "다음 트리거: 심층분석(티커1, 티커2, ...) → 채팅 요약 + MD/PDF 본문")


def main():
    pdf = Report()
    write_cover(pdf)
    write_surprise_summary(pdf)
    # Rank order for reading: same as chase priority for usability
    order = ["ECPG", "ASTH", "NESR", "KNSA", "INDV", "JBHT", "EXTR", "BTSG", "VCYT", "TGTX", "KRYS", "DAVE", "SEZL"]
    by = {t["ticker"]: t for t in TICKERS}
    for i, tk in enumerate(order, 1):
        write_ticker(pdf, i, by[tk])
    write_ranking(pdf)

    data = pdf.output()
    for p in OUT_PATHS:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        print(f"Wrote {p} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
