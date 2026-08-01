"""Competitor share + revenue-mix helpers for 수익구조분석().

Two layers (ticker configs in PEER_PROFILES):

1) **Industry share** — curated market-share panels (e.g. CTV device SOV)
   with period-over-period change (pp). Sources cited in profile.

2) **Peer revenue mix** — comparable segment buckets (%) for the ticker
   vs named peers, plus optional TTM revenue scale from yfinance.

Usage::

    from sepa.rev_compete import build_compete_charts, get_profile
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

# ---------------------------------------------------------------------------
# Profiles — extend per ticker used in 수익구조분석
# ---------------------------------------------------------------------------

PEER_PROFILES: dict[str, dict[str, Any]] = {
    "ROKU": {
        "sector_ko": "CTV·스트리밍 플랫폼 (심층: 통신·엔터테인먼트)",
        "share_title": "북미 CTV 디바이스 Share of Voice (프로그램매틱)",
        "share_as_of": "Q1'26 vs Q1'25 · Pixalate",
        "share_note": (
            "Pixalate CTV Device Market Share (프로그램매틱 SOV). "
            "Amazon/Samsung/Apple/LG는 비상장 사업부·복합기업이라 매출점유와 다름 — "
            "OS·디바이스 레이어 경쟁 점유율."
        ),
        "share_rows": [
            # name, current_pct, prior_pct
            ("Roku", 36.0, 38.0),
            ("Amazon Fire TV", 19.0, 18.0),
            ("Samsung Smart TV", 15.0, 12.0),
            ("Apple TV", 13.0, 13.0),
            ("LG", 10.0, 5.0),
        ],
        "share_source": "Pixalate Q1 2026 / Q1 2025 CTV Device Market Share",
        # Revenue mix: same bucket keys for stacked comparison
        "mix_buckets": ["Advertising", "Subscriptions", "Devices/Other"],
        "mix_as_of": "Q1'26 (또는 최근 공시 근사)",
        "mix_rows": [
            # ticker_or_name, display, is_subject, mix dict (must sum ~100), optional yf ticker for TTM
            {
                "key": "ROKU",
                "name": "ROKU",
                "subject": True,
                "yf": "ROKU",
                "mix": {"Advertising": 49.1, "Subscriptions": 41.5, "Devices/Other": 9.4},
                "note": "Q1'26 Ad $613M / Sub $519M / Dev $118M",
            },
            {
                "key": "SPOT",
                "name": "SPOT",
                "subject": False,
                "yf": "SPOT",
                "mix": {"Advertising": 8.5, "Subscriptions": 91.5, "Devices/Other": 0.0},
                "note": "Q1'26 Premium 중심 · Ad-supported 소비중 (근사)",
            },
            {
                "key": "NFLX",
                "name": "NFLX",
                "subject": False,
                "yf": "NFLX",
                "mix": {"Advertising": 6.0, "Subscriptions": 94.0, "Devices/Other": 0.0},
                "note": "구독 본체 · 광고 티어 성장 중(연간 광고~$3B 가이던스 대비 소비중 근사)",
            },
            {
                "key": "FUBO",
                "name": "FUBO",
                "subject": False,
                "yf": "FUBO",
                "mix": {"Advertising": 18.0, "Subscriptions": 82.0, "Devices/Other": 0.0},
                "note": "라이브TV 구독+광고 하이브리드 근사",
            },
        ],
        "mix_note": (
            "버킷은 비교를 위해 Advertising / Subscriptions / Devices·Other로 정규화. "
            "피어는 공시 세그먼트가 달라 근사치 — 방향 비교용."
        ),
    },
    "RELY": {
        "sector_ko": "핀테크·크로스보더 송금 (심층: 금융)",
        "share_title": "글로벌 송금 시장 점유율 (추정)",
        "share_as_of": "2026 est. vs 2025 est. · VMR 계열 근사",
        "share_note": (
            "전 세계 송금(현금·디지털 혼재) 추정 점유율. "
            "정의가 리포트마다 달라 절대치보다 Δpp·상대 순위 비교용. "
            "Remitly는 디지털·지갑 지급 강세, WU는 에이전트 네트워크 규모."
        ),
        "share_rows": [
            ("Western Union", 11.5, 12.0),
            ("Wise", 4.0, 4.2),
            ("Remitly", 2.3, 1.9),
            ("MoneyGram", 2.1, 2.2),
            ("WorldRemit", 1.1, 1.3),
        ],
        "share_source": "Verified Market Research digital remittance share estimates (2026 vs prior)",
        "mix_buckets": ["Consumer Remittance", "Business/Platform", "Other"],
        "mix_as_of": "Q1'26 / 최근 공시 근사",
        "mix_rows": [
            {
                "key": "RELY",
                "name": "RELY",
                "subject": True,
                "yf": "RELY",
                "mix": {"Consumer Remittance": 95.0, "Business/Platform": 5.0, "Other": 0.0},
                "note": "단일세그먼트 · Growth Accelerators(~5% FY26 가이던스) 포함",
            },
            {
                "key": "TW",
                "name": "TW",
                "subject": False,
                "yf": "TW",
                "mix": {"Consumer Remittance": 62.0, "Business/Platform": 38.0, "Other": 0.0},
                "note": "Personal vs Platform/Business 근사 (공시 혼합)",
            },
            {
                "key": "WU",
                "name": "WU",
                "subject": False,
                "yf": "WU",
                "mix": {"Consumer Remittance": 78.0, "Business/Platform": 22.0, "Other": 0.0},
                "note": "Consumer Money Transfer 중심 · B2B/기타 근사",
            },
        ],
        "mix_note": (
            "버킷은 Consumer Remittance / Business·Platform / Other로 정규화. "
            "RELY Growth Accelerators(고액송금·비즈니스·리시버 등)~5%를 Business/Platform에 배치."
        ),
    },
    "PEBO": {
        "sector_ko": "금융·지역은행 (심층: 오하이오 커뮤니티뱅크)",
        "share_title": "오하이오·인접 지역은행 예금 점유 (추정)",
        "share_as_of": "2026 est. vs 2025 est. · 방향 비교용",
        "share_note": (
            "오하이오+인접 예금 시장 추정 점유율. 대형(HBAN/FITB/KEY)과 커뮤니티(PEBO/WSBC)를 한 차트에 둔 "
            "상대 위치용. 절대치보다 Δpp·순위 감각이 목적."
        ),
        "share_rows": [
            ("Huntington", 15.2, 15.0),
            ("Fifth Third", 10.8, 11.0),
            ("KeyCorp", 7.3, 7.5),
            ("WesBanco", 2.9, 2.8),
            ("Peoples", 1.6, 1.5),
        ],
        "share_source": "Directional OH+contiguous deposit-share estimates (community/regional set)",
        "mix_buckets": ["Net Interest Income", "Fee Income", "Other/Gains"],
        "mix_as_of": "Q2'26 (또는 최근 분기 근사)",
        "mix_rows": [
            {
                "key": "PEBO",
                "name": "PEBO",
                "subject": True,
                "yf": "PEBO",
                "mix": {"Net Interest Income": 76.2, "Fee Income": 23.8, "Other/Gains": 0.0},
                "note": "NII $92.7M + Fee ex G/L $29.0M (증권매각손실은 제외 정의)",
            },
            {
                "key": "HBAN",
                "name": "HBAN",
                "subject": False,
                "yf": "HBAN",
                "mix": {"Net Interest Income": 72.0, "Fee Income": 26.0, "Other/Gains": 2.0},
                "note": "대형 지역은행 · 수수료 다각화 근사",
            },
            {
                "key": "FITB",
                "name": "FITB",
                "subject": False,
                "yf": "FITB",
                "mix": {"Net Interest Income": 70.0, "Fee Income": 28.0, "Other/Gains": 2.0},
                "note": "대형 지역은행 · 카드·WM 수수료 비중 상대 큼(근사)",
            },
            {
                "key": "WSBC",
                "name": "WSBC",
                "subject": False,
                "yf": "WSBC",
                "mix": {"Net Interest Income": 78.0, "Fee Income": 21.0, "Other/Gains": 1.0},
                "note": "중형 커뮤니티 · NII 편중 유사",
            },
        ],
        "mix_note": (
            "버킷은 NII / Fee(ex gains) / Other·Gains로 정규화. "
            "PEBO Q2는 AFS 매각손실($8.2M)이 GAAP 비이자에 잡히나, 운영 믹스는 Fee ex G/L 기준으로 표시."
        ),
    },
    "SBLK": {
        "sector_ko": "산업·해운 건화물 (심층: Dry Bulk)",
        "share_title": "상장 건화물 피어셋 DWT·스케일 점유 (추정)",
        "share_as_of": "2026 · fully-delivered 기준 근사",
        "share_note": (
            "미국·유럽 상장 순수 건화물 피어 대비 상대 스케일. "
            "SBLK는 fully delivered ~141척·14.0M dwt로 피어셋 내 최대급. "
            "절대 글로벌 해운 점유와 다름 — 상장 피어 비교용."
        ),
        "share_rows": [
            ("Star Bulk", 32.0, 30.0),
            ("Genco", 14.0, 14.5),
            ("Safe Bulkers", 9.0, 9.5),
            ("Diana Shipping", 7.0, 8.0),
            ("Others (listed)", 38.0, 38.0),
        ],
        "share_source": "Directional share of selected US-listed dry-bulk peer DWT/scale (est.)",
        "mix_buckets": ["Cape/Newcastlemax", "Panamax/Kamsarmax", "Ultramax/Supramax"],
        "mix_as_of": "Q1'26 revenue contribution",
        "mix_rows": [
            {
                "key": "SBLK",
                "name": "SBLK",
                "subject": True,
                "yf": "SBLK",
                "mix": {"Cape/Newcastlemax": 33.0, "Panamax/Kamsarmax": 29.0, "Ultramax/Supramax": 38.0},
                "note": "Q1'26 rev mix · TCE Cape $26.6k / Panamax $15.8k / Ultra $16.1k",
            },
            {
                "key": "GNK",
                "name": "GNK",
                "subject": False,
                "yf": "GNK",
                "mix": {"Cape/Newcastlemax": 22.0, "Panamax/Kamsarmax": 40.0, "Ultramax/Supramax": 38.0},
                "note": "중형 편중 근사 (공개 세그먼트 혼합)",
            },
            {
                "key": "SB",
                "name": "SB",
                "subject": False,
                "yf": "SB",
                "mix": {"Cape/Newcastlemax": 15.0, "Panamax/Kamsarmax": 45.0, "Ultramax/Supramax": 40.0},
                "note": "Panamax·Handy 성격 강 (근사)",
            },
            {
                "key": "DSX",
                "name": "DSX",
                "subject": False,
                "yf": "DSX",
                "mix": {"Cape/Newcastlemax": 25.0, "Panamax/Kamsarmax": 35.0, "Ultramax/Supramax": 40.0},
                "note": "다변화 선대 · 소형 시총 (근사)",
            },
        ],
        "mix_note": (
            "버킷은 선급(Cape / Panamax / Ultramax) 매출 기여로 정규화. "
            "피어는 공시 포맷이 달라 근사 — 방향 비교용."
        ),
    },
    "CLMT": {
        "sector_ko": "소재·특수석유제품 / 재생연료 (심층: Specialty + Renewables)",
        "share_title": "특수제품·재생연료 상장 피어셋 스케일 점유 (추정)",
        "share_as_of": "2026 · TTM 매출/스케일 근사",
        "share_note": (
            "특수 윤활·용제·왁스 + 재생디젤/SAF 성격의 상장 피어 대비 상대 스케일. "
            "절대 시장점유가 아님 — 피어셋 비교용."
        ),
        "share_rows": [
            ("PBF Energy", 28.0, 27.0),
            ("HF Sinclair", 22.0, 22.5),
            ("Calumet", 14.0, 12.0),
            ("Green Plains", 9.0, 10.0),
            ("Others (listed)", 27.0, 28.5),
        ],
        "share_source": "Directional share of selected US-listed specialty/renewables-adjacent peers (est.)",
        "mix_buckets": ["Specialty Products", "Montana/Renewables", "Performance Brands"],
        "mix_as_of": "Q1'26 sales mix (SPS disclosed; PB/MR approx)",
        "mix_rows": [
            {
                "key": "CLMT",
                "name": "CLMT",
                "subject": True,
                "yf": "CLMT",
                "mix": {"Specialty Products": 68.5, "Montana/Renewables": 25.0, "Performance Brands": 6.5},
                "note": "SPS sales $705M / total $1.03B · Adj EBITDA+TaxAttr $50.1M",
            },
            {
                "key": "PBF",
                "name": "PBF",
                "subject": False,
                "yf": "PBF",
                "mix": {"Specialty Products": 15.0, "Montana/Renewables": 75.0, "Performance Brands": 10.0},
                "note": "정유·연료 중심 근사 (재생 일부)",
            },
            {
                "key": "DINO",
                "name": "DINO",
                "subject": False,
                "yf": "DINO",
                "mix": {"Specialty Products": 20.0, "Montana/Renewables": 70.0, "Performance Brands": 10.0},
                "note": "정유·윤활 혼합 근사",
            },
            {
                "key": "GPRE",
                "name": "GPRE",
                "subject": False,
                "yf": "GPRE",
                "mix": {"Specialty Products": 10.0, "Montana/Renewables": 85.0, "Performance Brands": 5.0},
                "note": "바이오연료/에탄올 편중 근사",
            },
        ],
        "mix_note": (
            "버킷은 Specialty Products / Montana·Renewables / Performance Brands로 정규화. "
            "피어는 공시 세그먼트가 달라 근사 — 방향 비교용."
        ),
    },
    "TXG": {
        "sector_ko": "헬스케어·생명과학 툴 (심층: 단일세포·공간전사체)",
        "share_title": "상장 단일세포·공간·시퀀싱툴 피어셋 점유 (추정)",
        "share_as_of": "2026 · SC/Spatial 중심 근사 vs 전년",
        "share_note": (
            "단일세포·공간전사체 중심의 상장 툴 피어셋 상대 점유. "
            "Illumina는 NGS 전체 스케일이 커서 SC 전용 점유와 다름 — 방향·순위 비교용. "
            "절대 글로벌 시장점유가 아님."
        ),
        "share_rows": [
            ("10x Genomics", 38.0, 35.0),
            ("Illumina", 24.0, 26.0),
            ("Bio-Techne", 14.0, 13.5),
            ("Twist", 12.0, 11.0),
            ("PacBio", 8.0, 9.5),
            ("Others (listed)", 4.0, 5.0),
        ],
        "share_source": "Directional share of selected US-listed SC/spatial/seq-tools peers (est.)",
        "mix_buckets": ["Consumables", "Instruments", "Services/Other"],
        "mix_as_of": "Q1'26 (또는 최근 공시 근사)",
        "mix_rows": [
            {
                "key": "TXG",
                "name": "TXG",
                "subject": True,
                "yf": "TXG",
                "mix": {"Consumables": 86.0, "Instruments": 7.5, "Services/Other": 6.5},
                "note": "Q1'26 Cons $129.8M / Inst $11.3M / Svc+Lic ~$9.7M",
            },
            {
                "key": "ILMN",
                "name": "ILMN",
                "subject": False,
                "yf": "ILMN",
                "mix": {"Consumables": 72.0, "Instruments": 18.0, "Services/Other": 10.0},
                "note": "NGS 소모품 편중 · 장비·서비스 근사",
            },
            {
                "key": "TECH",
                "name": "TECH",
                "subject": False,
                "yf": "TECH",
                "mix": {"Consumables": 82.0, "Instruments": 8.0, "Services/Other": 10.0},
                "note": "시약·키트 중심 근사",
            },
            {
                "key": "TWST",
                "name": "TWST",
                "subject": False,
                "yf": "TWST",
                "mix": {"Consumables": 88.0, "Instruments": 2.0, "Services/Other": 10.0},
                "note": "합성 DNA·키트 성격 · 장비 비중 낮음(근사)",
            },
            {
                "key": "PACB",
                "name": "PACB",
                "subject": False,
                "yf": "PACB",
                "mix": {"Consumables": 55.0, "Instruments": 35.0, "Services/Other": 10.0},
                "note": "장기 시퀀서 장비 비중 상대 큼(근사)",
            },
        ],
        "mix_note": (
            "버킷은 Consumables / Instruments / Services·Other로 정규화. "
            "피어는 공시 세그먼트가 달라 근사 — 방향 비교용. TXG는 소모품 ~86%가 본체."
        ),
    },
    "ACHC": {
        "sector_ko": "헬스케어·행동건강 시설 (심층: Acute·CTC·Specialty·RTC)",
        "share_title": "상장 행동건강·시설 피어셋 스케일 점유 (추정)",
        "share_as_of": "2026 · TTM/스케일 근사 vs 전년",
        "share_note": (
            "행동건강·시설 성격의 상장 피어셋 상대 스케일. "
            "UHS는 급성병원+행동건강 혼합이라 절대 행동건강 점유와 다름 — 방향 비교용."
        ),
        "share_rows": [
            ("UHS (beh. incl.)", 34.0, 33.0),
            ("Acadia", 22.0, 23.0),
            ("Select/Ensign", 18.0, 18.5),
            ("Tenet (adj.)", 14.0, 14.5),
            ("Others (listed)", 12.0, 11.0),
        ],
        "share_source": "Directional share of selected US-listed behavioral/facility peers (est.)",
        "mix_buckets": ["Acute Psych", "Specialty+RTC", "CTC"],
        "mix_as_of": "Q2'26 revenue mix",
        "mix_rows": [
            {
                "key": "ACHC",
                "name": "ACHC",
                "subject": True,
                "yf": "ACHC",
                "mix": {"Acute Psych": 57.1, "Specialty+RTC": 26.6, "CTC": 16.3},
                "note": "Q2'26 Acute $494.6 / Spec $133.5 / RTC $96.5 / CTC $141.2",
            },
            {
                "key": "UHS",
                "name": "UHS",
                "subject": False,
                "yf": "UHS",
                "mix": {"Acute Psych": 35.0, "Specialty+RTC": 45.0, "CTC": 20.0},
                "note": "급성병원 본체 + 행동건강 혼합 근사",
            },
            {
                "key": "ENSG",
                "name": "ENSG",
                "subject": False,
                "yf": "ENSG",
                "mix": {"Acute Psych": 10.0, "Specialty+RTC": 85.0, "CTC": 5.0},
                "note": "요양·포스트어큐트 편중 근사",
            },
            {
                "key": "THC",
                "name": "THC",
                "subject": False,
                "yf": "THC",
                "mix": {"Acute Psych": 70.0, "Specialty+RTC": 25.0, "CTC": 5.0},
                "note": "급성병원 중심 근사",
            },
        ],
        "mix_note": (
            "버킷은 Acute Psych / Specialty+RTC / CTC로 정규화. "
            "ACHC Q2'26 공시 라인 합산. 피어는 공시 세그먼트가 달라 근사."
        ),
    },
    "NESR": {
        "sector_ko": "에너지·오일필드 서비스 (심층: MENA OFS)",
        "share_title": "상장 OFS 피어셋 스케일 점유 (추정)",
        "share_as_of": "2026 · TTM/스케일 근사 vs 전년",
        "share_note": (
            "글로벌·MENA OFS 상장 피어셋 상대 스케일. "
            "SLB/HAL/BKR는 글로벌 메이저라 NESR MENA 현지 점유와 다름 — 방향 비교용."
        ),
        "share_rows": [
            ("SLB", 38.0, 38.5),
            ("Halliburton", 24.0, 24.5),
            ("Baker Hughes", 20.0, 19.5),
            ("NESR", 8.0, 6.5),
            ("Others (listed)", 10.0, 11.0),
        ],
        "share_source": "Directional share of selected US-listed OFS peers by scale (est.)",
        "mix_buckets": ["Production Services", "Drilling & Evaluation", "Other"],
        "mix_as_of": "Q1'26 (또는 최근 공시 근사)",
        "mix_rows": [
            {
                "key": "NESR",
                "name": "NESR",
                "subject": True,
                "yf": "NESR",
                "mix": {"Production Services": 60.0, "Drilling & Evaluation": 40.0, "Other": 0.0},
                "note": "Q1'26 Prod ~$241M / D&E ~$164M · MENA ~99.6%",
            },
            {
                "key": "SLB",
                "name": "SLB",
                "subject": False,
                "yf": "SLB",
                "mix": {"Production Services": 35.0, "Drilling & Evaluation": 45.0, "Other": 20.0},
                "note": "글로벌 · 디지털/장비 포함 근사",
            },
            {
                "key": "HAL",
                "name": "HAL",
                "subject": False,
                "yf": "HAL",
                "mix": {"Production Services": 55.0, "Drilling & Evaluation": 35.0, "Other": 10.0},
                "note": "Completion/Production 강세 근사",
            },
            {
                "key": "BKR",
                "name": "BKR",
                "subject": False,
                "yf": "BKR",
                "mix": {"Production Services": 40.0, "Drilling & Evaluation": 35.0, "Other": 25.0},
                "note": "OFSE+산업/에너지기술 혼합 근사",
            },
        ],
        "mix_note": (
            "버킷은 Production / Drilling&Evaluation / Other로 정규화. "
            "NESR는 MENA 생산서비스 편중. 피어는 공시 세그먼트가 달라 근사."
        ),
    },
}


@dataclass
class ShareRow:
    name: str
    current: float
    prior: float

    @property
    def delta_pp(self) -> float:
        return self.current - self.prior


@dataclass
class CompeteBundle:
    ticker: str
    sector_ko: str
    share_title: str
    share_as_of: str
    share_note: str
    share_source: str
    share_rows: list[ShareRow]
    mix_buckets: list[str]
    mix_as_of: str
    mix_note: str
    mix_rows: list[dict[str, Any]]
    ttm_revenue: dict[str, float] = field(default_factory=dict)


def get_profile(ticker: str) -> dict[str, Any] | None:
    return PEER_PROFILES.get(ticker.upper())


def _setup_font():
    fm.fontManager.addfont(FONT_REG)
    fm.fontManager.addfont(FONT_BOLD)
    prop = fm.FontProperties(fname=FONT_REG)
    prop_b = fm.FontProperties(fname=FONT_BOLD)
    plt.rcParams["font.family"] = prop.get_name()
    plt.rcParams["axes.unicode_minus"] = False
    return prop, prop_b


def _ttm_revenue(yf_ticker: str) -> float | None:
    try:
        tk = yf.Ticker(yf_ticker)
        # prefer income statement trailing
        fin = tk.financials
        if fin is not None and not fin.empty:
            # first column = most recent annual
            for idx in fin.index:
                if "Total Revenue" in str(idx) or str(idx).lower() == "total revenue":
                    val = fin.loc[idx].iloc[0]
                    if val is not None and not (isinstance(val, float) and np.isnan(val)):
                        return float(val)
        info = tk.info or {}
        # totalRevenue often TTM
        tr = info.get("totalRevenue")
        if tr:
            return float(tr)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ttm revenue fail %s: %s", yf_ticker, exc)
    return None


def load_compete_bundle(ticker: str) -> CompeteBundle | None:
    prof = get_profile(ticker)
    if not prof:
        return None
    share_rows = [ShareRow(n, c, p) for n, c, p in prof["share_rows"]]
    mix_rows = list(prof["mix_rows"])
    ttm: dict[str, float] = {}
    for row in mix_rows:
        yft = row.get("yf")
        if not yft:
            continue
        rev = _ttm_revenue(yft)
        if rev is not None:
            ttm[row["name"]] = rev
    return CompeteBundle(
        ticker=ticker.upper(),
        sector_ko=prof["sector_ko"],
        share_title=prof["share_title"],
        share_as_of=prof["share_as_of"],
        share_note=prof["share_note"],
        share_source=prof["share_source"],
        share_rows=share_rows,
        mix_buckets=list(prof["mix_buckets"]),
        mix_as_of=prof["mix_as_of"],
        mix_note=prof["mix_note"],
        mix_rows=mix_rows,
        ttm_revenue=ttm,
    )


def chart_share_level(bundle: CompeteBundle, out: Path, *, prop, prop_b) -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 4.0))
    names = [r.name for r in bundle.share_rows]
    vals = [r.current for r in bundle.share_rows]
    colors = []
    for n in names:
        hit = (
            n.upper() == bundle.ticker
            or ("Roku" in n and bundle.ticker == "ROKU")
            or ("Remitly" in n and bundle.ticker == "RELY")
            or ("Peoples" in n and bundle.ticker == "PEBO")
            or ("Star Bulk" in n and bundle.ticker == "SBLK")
            or ("Calumet" in n and bundle.ticker == "CLMT")
            or ("10x" in n and bundle.ticker == "TXG")
            or ("Acadia" in n and bundle.ticker == "ACHC")
            or ("NESR" in n and bundle.ticker == "NESR")
        )
        colors.append(("#6c2bd9" if bundle.ticker == "ROKU" else "#0ea5e9") if hit else "#64748b")
    bars = ax.barh(names[::-1], vals[::-1], color=colors[::-1], height=0.55)
    ax.set_xlabel("%", fontproperties=prop)
    ax.set_title(bundle.share_title, fontproperties=prop_b, fontsize=11)
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 0.4, b.get_y() + b.get_height() / 2, f"{v:.0f}%", va="center", fontproperties=prop, fontsize=8)
    ax.set_xlim(0, max(vals) * 1.25)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(prop)
    ax.text(0.99, -0.12, bundle.share_as_of, transform=ax.transAxes, ha="right", fontproperties=prop, fontsize=7, color="#64748b")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def chart_share_delta(bundle: CompeteBundle, out: Path, *, prop, prop_b) -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    names = [r.name for r in bundle.share_rows]
    deltas = [r.delta_pp for r in bundle.share_rows]
    colors = ["#cb181d" if d >= 0 else "#2171b5" for d in deltas]  # KR: red up / blue down
    y = np.arange(len(names))
    ax.barh(y, deltas, color=colors, height=0.55)
    ax.axvline(0, color="#94a3b8", lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontproperties=prop)
    ax.set_xlabel("점유율 변화 (pp)", fontproperties=prop)
    ax.set_title("경쟁 점유율 변화 (현재 - 전년동기)", fontproperties=prop_b, fontsize=11)
    ax.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x:g}".replace("\u2212", "-"))
    )
    for i, d in enumerate(deltas):
        label = f"{d:+.0f}pp".replace("\u2212", "-")
        ax.text(d + (0.15 if d >= 0 else -0.15), i, label, va="center",
                ha="left" if d >= 0 else "right", fontproperties=prop, fontsize=8)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def chart_mix_compare(bundle: CompeteBundle, out: Path, *, prop, prop_b) -> Path:
    buckets = bundle.mix_buckets
    palette = ["#0e7490", "#047857", "#a16207", "#64748b"]
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    labels = [r["name"] for r in bundle.mix_rows]
    x = np.arange(len(labels))
    bottom = np.zeros(len(labels))
    for i, b in enumerate(buckets):
        vals = np.array([float(r["mix"].get(b, 0.0)) for r in bundle.mix_rows])
        ax.bar(x, vals, bottom=bottom, width=0.55, color=palette[i % len(palette)], label=b, edgecolor="white", linewidth=0.6)
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontproperties=prop_b, fontsize=9)
    ax.set_ylabel("매출 구성 %", fontproperties=prop)
    ax.set_ylim(0, 105)
    ax.set_title(f"경쟁사 매출 구조 비율 비교 · {bundle.mix_as_of}", fontproperties=prop_b, fontsize=11)
    ax.legend(prop=prop, fontsize=8, loc="upper right")
    # highlight subject tick label color
    for i, r in enumerate(bundle.mix_rows):
        if r.get("subject"):
            ax.get_xticklabels()[i].set_color("#6c2bd9")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def chart_ttm_scale(bundle: CompeteBundle, out: Path, *, prop, prop_b) -> Path | None:
    if not bundle.ttm_revenue:
        return None
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    names = [r["name"] for r in bundle.mix_rows if r["name"] in bundle.ttm_revenue]
    vals = [bundle.ttm_revenue[n] / 1e9 for n in names]
    colors = ["#6c2bd9" if n == bundle.ticker or any(r["name"] == n and r.get("subject") for r in bundle.mix_rows) else "#94a3b8" for n in names]
    bars = ax.bar(names, vals, color=colors, width=0.55)
    ax.set_ylabel("TTM 매출 ($B)", fontproperties=prop)
    ax.set_title("규모 감각 — TTM 매출 (피어 대비)", fontproperties=prop_b, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.02, f"{v:.1f}", ha="center", fontproperties=prop, fontsize=8)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(prop_b)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def build_compete_charts(ticker: str, chart_dir: str | Path) -> tuple[CompeteBundle | None, dict[str, Path]]:
    """Return bundle + chart paths (share, delta, mix, optional ttm)."""
    bundle = load_compete_bundle(ticker)
    if bundle is None:
        return None, {}
    prop, prop_b = _setup_font()
    chart_dir = Path(chart_dir)
    paths = {
        "share": chart_share_level(bundle, chart_dir / "10_compete_share.png", prop=prop, prop_b=prop_b),
        "delta": chart_share_delta(bundle, chart_dir / "11_compete_delta.png", prop=prop, prop_b=prop_b),
        "mix": chart_mix_compare(bundle, chart_dir / "12_compete_mix.png", prop=prop, prop_b=prop_b),
    }
    ttm = chart_ttm_scale(bundle, chart_dir / "13_compete_ttm.png", prop=prop, prop_b=prop_b)
    if ttm is not None:
        paths["ttm"] = ttm
    return bundle, paths
