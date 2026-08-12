"""Competitor share + revenue-mix helpers for 수익구조분석().

**REQUIRED chapter** — every ``수익구조분석(TICKER)`` PDF must include the
compete section (점유율 Δpp + 피어 매출 믹스), regardless of template
(clinical / royalty / operating). Generators must:

1. Add/extend ``PEER_PROFILES[TICKER]``
2. Call ``build_compete_charts(TICKER, chart_dir)`` (raises if profile missing)
3. Insert ``render_compete_section_html(...)`` into the HTML body

Two layers (ticker configs in PEER_PROFILES):

1) **Industry share** — curated market-share panels (e.g. CTV device SOV)
   with period-over-period change (pp). Sources cited in profile.

2) **Peer revenue mix** — comparable segment buckets (%) for the ticker
   vs named peers, plus optional TTM revenue scale from yfinance.

Usage::

    from sepa.rev_compete import build_compete_charts, render_compete_section_html
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
    "ZD": {
        "sector_ko": "디지털 미디어·Martech (심층: 광고/콘텐츠 + SaaS)",
        "share_title": "상장 디지털미디어·인터랙티브 피어셋 스케일 점유 (추정)",
        "share_as_of": "2026 · TTM/스케일 근사 vs 전년",
        "share_note": (
            "디지털 미디어·인터랙티브 성격 상장 피어셋 상대 스케일. "
            "IAC/MTCH는 데이팅·비디오 혼합이라 절대 광고점유와 다름 — 방향 비교용."
        ),
        "share_rows": [
            ("IAC", 28.0, 30.0),
            ("Ziff Davis", 22.0, 20.0),
            ("Match Group", 20.0, 21.0),
            ("Yelp", 16.0, 15.0),
            ("Others (listed)", 14.0, 14.0),
        ],
        "share_source": "Directional share of selected US-listed digital media/interactive peers (est.)",
        "mix_buckets": ["Ads/Content", "SaaS/Sub", "Other"],
        "mix_as_of": "Q2'26 continuing ops 근사",
        "mix_rows": [
            {
                "key": "ZD",
                "name": "ZD",
                "subject": True,
                "yf": "ZD",
                "mix": {"Ads/Content": 76.0, "SaaS/Sub": 24.0, "Other": 0.0},
                "note": "Health+Tech+Gaming≈광고/콘텐츠 · Cyber/Martech≈SaaS (Q2 매출비중 근사)",
            },
            {
                "key": "IAC",
                "name": "IAC",
                "subject": False,
                "yf": "IAC",
                "mix": {"Ads/Content": 55.0, "SaaS/Sub": 35.0, "Other": 10.0},
                "note": "닷대시·앙길라 등 혼합 근사",
            },
            {
                "key": "MTCH",
                "name": "MTCH",
                "subject": False,
                "yf": "MTCH",
                "mix": {"Ads/Content": 15.0, "SaaS/Sub": 85.0, "Other": 0.0},
                "note": "구독(데이팅) 편중",
            },
            {
                "key": "YELP",
                "name": "YELP",
                "subject": False,
                "yf": "YELP",
                "mix": {"Ads/Content": 90.0, "SaaS/Sub": 8.0, "Other": 2.0},
                "note": "로컬 광고 중심",
            },
        ],
        "mix_note": (
            "버킷 Ads/Content · SaaS/Sub · Other로 정규화. "
            "ZD는 Connectivity 매각 후 계속영업 4세그먼트 비중 근사."
        ),
    },
    "VSAT": {
        "sector_ko": "위성통신·방산 SATCOM (심층: Comm Services + DAT)",
        "share_title": "상장 위성통신·모빌리티 SATCOM 피어셋 점유 (추정)",
        "share_as_of": "2026 · 상업·정부 SATCOM 스케일 근사 vs 전년",
        "share_note": (
            "위성통신·모빌리티 상장 피어셋 상대 스케일. "
            "Starlink(비상장) 제외 — 상장셋 내 순위·Δpp 감각용."
        ),
        "share_rows": [
            ("Viasat", 34.0, 32.0),
            ("EchoStar/SATS", 26.0, 28.0),
            ("Iridium", 18.0, 17.0),
            ("Globalstar", 10.0, 11.0),
            ("Others (listed)", 12.0, 12.0),
        ],
        "share_source": "Directional share of selected US-listed satcom peers (est., ex-Starlink)",
        "mix_buckets": ["Comm Services", "DAT/Defense", "Other"],
        "mix_as_of": "Q1 FY27",
        "mix_rows": [
            {
                "key": "VSAT",
                "name": "VSAT",
                "subject": True,
                "yf": "VSAT",
                "mix": {"Comm Services": 71.0, "DAT/Defense": 29.0, "Other": 0.0},
                "note": "Q1 FY27 Comm $825M / DAT $331M",
            },
            {
                "key": "SATS",
                "name": "SATS",
                "subject": False,
                "yf": "SATS",
                "mix": {"Comm Services": 80.0, "DAT/Defense": 15.0, "Other": 5.0},
                "note": "위성·브로드밴드 혼합 근사",
            },
            {
                "key": "IRDM",
                "name": "IRDM",
                "subject": False,
                "yf": "IRDM",
                "mix": {"Comm Services": 92.0, "DAT/Defense": 5.0, "Other": 3.0},
                "note": "MSS 서비스 편중",
            },
            {
                "key": "GSAT",
                "name": "GSAT",
                "subject": False,
                "yf": "GSAT",
                "mix": {"Comm Services": 88.0, "DAT/Defense": 7.0, "Other": 5.0},
                "note": "MSS/IoT 근사",
            },
        ],
        "mix_note": (
            "버킷 Comm Services / DAT·Defense / Other. "
            "VSAT는 항공·정부 SATCOM이 Comm 성장축, DAT는 수주 선행."
        ),
    },
    "ANAB": {
        "sector_ko": "바이오 로열티·금융협업 (심층: Jemperli/imsidolimab)",
        "share_title": "상장 로열티·바이오파이낸스 피어셋 스케일 점유 (추정)",
        "share_as_of": "2026 · 로열티/협업 매출 스케일 근사 vs 전년",
        "share_note": (
            "로열티·바이오파이낸스 성격 상장 피어셋 상대 스케일. "
            "RPRX는 대규모 로열티 집합체라 ANAB(단일 프랜차이즈)와 절대 비교 주의."
        ),
        "share_rows": [
            ("Royalty Pharma", 48.0, 47.0),
            ("AnaptysBio", 18.0, 14.0),
            ("Ligand", 16.0, 17.0),
            ("Others (listed)", 18.0, 22.0),
        ],
        "share_source": "Directional share of selected US-listed royalty/biopharma finance peers (est.)",
        "mix_buckets": ["Product Royalties", "Other Collab", "Interest/Other"],
        "mix_as_of": "Q1'26",
        "mix_rows": [
            {
                "key": "ANAB",
                "name": "ANAB",
                "subject": True,
                "yf": "ANAB",
                "mix": {"Product Royalties": 96.5, "Other Collab": 3.5, "Interest/Other": 0.0},
                "note": "Q1 collab $25.6M 중 Jemperli 로열티 $24.7M",
            },
            {
                "key": "RPRX",
                "name": "RPRX",
                "subject": False,
                "yf": "RPRX",
                "mix": {"Product Royalties": 95.0, "Other Collab": 3.0, "Interest/Other": 2.0},
                "note": "다각화 로열티 포트 근사",
            },
            {
                "key": "LGND",
                "name": "LGND",
                "subject": False,
                "yf": "LGND",
                "mix": {"Product Royalties": 70.0, "Other Collab": 25.0, "Interest/Other": 5.0},
                "note": "로열티+캡티브 혼합 근사",
            },
        ],
        "mix_note": (
            "버킷 Product Royalties / Other Collab / Interest. "
            "ANAB는 Sagard 선취로 현금≠회계매출 — 믹스는 인식 매출 기준."
        ),
    },
    "SYRE": {
        "sector_ko": "헬스케어·IBD 임상항체 (심층: SKYLINE/SKYWAY)",
        "share_title": "IBD·면역 임상단계 상장 피어셋 관심/스케일 점유 (추정)",
        "share_as_of": "2026 · 임상 IBD/면역 피어 시총·파이프라인 근사 vs 전년",
        "share_note": (
            "제품매출 없는 임상단계 IBD/면역 피어셋의 상대 관심·스케일. "
            "ABBV/JNJ 상업 IBD와 절대 점유 비교 아님 — 파이프라인 경쟁 방향용."
        ),
        "share_rows": [
            ("Spyre", 32.0, 18.0),
            ("Roivant/Imm. basket", 24.0, 26.0),
            ("Other IBD clinical", 22.0, 28.0),
            ("TL1A/IL-23 peers", 14.0, 16.0),
            ("Others", 8.0, 12.0),
        ],
        "share_source": "Directional mindshare/scale among selected IBD clinical-stage peers (est.)",
        "mix_buckets": ["Product", "Collab/Milestone", "Interest"],
        "mix_as_of": "Q2'26 P&L 성격",
        "mix_rows": [
            {
                "key": "SYRE",
                "name": "SYRE",
                "subject": True,
                "yf": "SYRE",
                "mix": {"Product": 0.0, "Collab/Milestone": 80.0, "Interest": 20.0},
                "note": "제품 $0 · H1 레거시 마일스톤 이익 + 이자 (손익 성격 정규화)",
            },
            {
                "key": "RAPP",
                "name": "RAPP",
                "subject": False,
                "yf": "RAPP",
                "mix": {"Product": 0.0, "Collab/Milestone": 82.0, "Interest": 18.0},
                "note": "협업 upfront 중심 임상사 근사",
            },
            {
                "key": "DNTH",
                "name": "DNTH",
                "subject": False,
                "yf": "DNTH",
                "mix": {"Product": 0.0, "Collab/Milestone": 6.0, "Interest": 94.0},
                "note": "Q2 License≪Interest",
            },
        ],
        "mix_note": (
            "임상사 공통: Product≈0. 버킷은 손익 ‘현금성 유입’ 성격 비교용. "
            "절대 시장점유 아님."
        ),
    },
    "DNTH": {
        "sector_ko": "헬스케어·보체/신경근육 자가면역 (심층: claseprubart)",
        "share_title": "gMG·CIDP·보체 경로 상장 피어셋 스케일 점유 (추정)",
        "share_as_of": "2026 · gMG/CIDP/보체 피어 시총·파이프라인 근사 vs 전년",
        "share_note": (
            "gMG·CIDP·보체 억제 관련 상장 피어셋 상대 스케일. "
            "ARGX는 상업화 제품 보유 — 임상단계 DNTH와 절대 점유 비교 주의."
        ),
        "share_rows": [
            ("argenx", 40.0, 38.0),
            ("Dianthus", 22.0, 12.0),
            ("Other complement", 20.0, 24.0),
            ("Other gMG/CIDP", 12.0, 16.0),
            ("Others", 6.0, 10.0),
        ],
        "share_source": "Directional scale among selected gMG/CIDP/complement peers (est.)",
        "mix_buckets": ["Product", "License/Collab", "Interest"],
        "mix_as_of": "Q2'26",
        "mix_rows": [
            {
                "key": "DNTH",
                "name": "DNTH",
                "subject": True,
                "yf": "DNTH",
                "mix": {"Product": 0.0, "License/Collab": 6.0, "Interest": 94.0},
                "note": "Q2 License $0.76M · Interest $11.5M",
            },
            {
                "key": "ARGX",
                "name": "ARGX",
                "subject": False,
                "yf": "ARGX",
                "mix": {"Product": 92.0, "License/Collab": 5.0, "Interest": 3.0},
                "note": "Vyvgart 등 제품매출 중심",
            },
            {
                "key": "ALNY",
                "name": "ALNY",
                "subject": False,
                "yf": "ALNY",
                "mix": {"Product": 88.0, "License/Collab": 8.0, "Interest": 4.0},
                "note": "상업 제품+협업 근사",
            },
        ],
        "mix_note": (
            "DNTH는 제품매출 전 · 이자≫라이선스. "
            "상업화 피어(ARGX)와 믹스 대비로 ‘아직 전’임을 시각화."
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
    "LASR": {
        "sector_ko": "테크·광전자 (심층: 고출력 반도체·광섬유 레이저 / A&D)",
        "share_title": "상장 고출력 레이저·포토닉스 피어셋 스케일 점유 (추정)",
        "share_as_of": "2026 · TTM/스케일 근사 vs 전년",
        "share_note": (
            "고출력 레이저·포토닉스 상장 피어셋 상대 스케일. "
            "COHR/IPGP는 산업·통신 믹스가 커서 LASR A&D 편중 점유와 다름 — 방향 비교용."
        ),
        "share_rows": [
            ("Coherent", 42.0, 41.0),
            ("IPG Photonics", 28.0, 30.0),
            ("Lumentum", 18.0, 17.5),
            ("nLIGHT", 7.0, 5.5),
            ("Others (listed)", 5.0, 6.0),
        ],
        "share_source": "Directional share of selected US-listed high-power laser/photonics peers (est.)",
        "mix_buckets": ["Aerospace & Defense", "Industrial", "Microfabrication"],
        "mix_as_of": "Q1'26 (또는 최근 공시 근사)",
        "mix_rows": [
            {
                "key": "LASR",
                "name": "LASR",
                "subject": True,
                "yf": "LASR",
                "mix": {"Aerospace & Defense": 69.0, "Industrial": 15.0, "Microfabrication": 16.0},
                "note": "Q1'26 A&D $55.1M / Ind $12.0M / Micro $13.0M",
            },
            {
                "key": "IPGP",
                "name": "IPGP",
                "subject": False,
                "yf": "IPGP",
                "mix": {"Aerospace & Defense": 8.0, "Industrial": 78.0, "Microfabrication": 14.0},
                "note": "산업 절삭·용접 편중 근사",
            },
            {
                "key": "COHR",
                "name": "COHR",
                "subject": False,
                "yf": "COHR",
                "mix": {"Aerospace & Defense": 18.0, "Industrial": 52.0, "Microfabrication": 30.0},
                "note": "산업·통신·생명과학 혼합 근사",
            },
            {
                "key": "LITE",
                "name": "LITE",
                "subject": False,
                "yf": "LITE",
                "mix": {"Aerospace & Defense": 5.0, "Industrial": 25.0, "Microfabrication": 70.0},
                "note": "통신·옵토 편중 · 버킷 근사",
            },
        ],
        "mix_note": (
            "버킷은 A&D / Industrial / Microfabrication으로 정규화. "
            "LASR Q1'26 최종시장 공시. 피어는 공시 세그먼트가 달라 근사 — 방향 비교용."
        ),
    },
    "AMRX": {
        "sector_ko": "헬스케어·제네릭·스페셜티 제약 (심층: Affordable · Specialty · AvKARE)",
        "share_title": "상장 제네릭·복합제형 피어셋 스케일 점유 (추정)",
        "share_as_of": "2026 · TTM/스케일 근사 vs 전년",
        "share_note": (
            "미국·글로벌 제네릭/복합제형 상장 피어셋 상대 스케일. "
            "TEVA·VTRS는 글로벌 대형이라 AMRX 미국 복잡제네릭·Specialty 점유와 다름 — 방향 비교용."
        ),
        "share_rows": [
            ("Teva", 32.0, 33.0),
            ("Viatris", 26.0, 27.0),
            ("Amneal", 14.0, 12.5),
            ("Perrigo", 12.0, 12.5),
            ("Others (listed)", 16.0, 15.0),
        ],
        "share_source": "Directional share of selected US-listed generics/specialty peers by scale (est.)",
        "mix_buckets": ["Affordable/Generics", "Specialty/Brand", "Dist/Other"],
        "mix_as_of": "Q2'26 revenue mix",
        "mix_rows": [
            {
                "key": "AMRX",
                "name": "AMRX",
                "subject": True,
                "yf": "AMRX",
                "mix": {"Affordable/Generics": 61.5, "Specialty/Brand": 18.8, "Dist/Other": 19.7},
                "note": "Q2'26 AM $490M / Spec $149.3M / AvKARE $157M",
            },
            {
                "key": "TEVA",
                "name": "TEVA",
                "subject": False,
                "yf": "TEVA",
                "mix": {"Affordable/Generics": 55.0, "Specialty/Brand": 35.0, "Dist/Other": 10.0},
                "note": "글로벌 제네릭+혁신/Specialty 혼합 근사",
            },
            {
                "key": "VTRS",
                "name": "VTRS",
                "subject": False,
                "yf": "VTRS",
                "mix": {"Affordable/Generics": 70.0, "Specialty/Brand": 20.0, "Dist/Other": 10.0},
                "note": "제네릭·브랜드 혼합 · 구조조정 중 근사",
            },
            {
                "key": "PRGO",
                "name": "PRGO",
                "subject": False,
                "yf": "PRGO",
                "mix": {"Affordable/Generics": 40.0, "Specialty/Brand": 15.0, "Dist/Other": 45.0},
                "note": "OTC·소비자헬스 편중 근사",
            },
        ],
        "mix_note": (
            "버킷은 Affordable/Generics / Specialty·Brand / Dist·Other로 정규화. "
            "AMRX Q2'26 세그먼트 공시. 피어는 공시 세그먼트가 달라 근사."
        ),
    },
    "ECPG": {
        "sector_ko": "전문금융 · 부실채권(NPL) 매입·회수 (심층: Specialty Finance)",
        "share_title": "상장 NPL 채무매입 피어셋 스케일 점유 (추정)",
        "share_as_of": "2026 · 회수/스케일 근사 vs 전년",
        "share_note": (
            "미국·글로벌 소비자 NPL 매입 상장 피어셋 상대 스케일. "
            "사모·지역 매입사·은행 내수 회수는 제외 — 공개 피어 방향 비교용."
        ),
        "share_rows": [
            ("Encore (ECPG)", 38.0, 35.0),
            ("PRA Group (PRAA)", 28.0, 29.0),
            ("Others (listed/est.)", 34.0, 36.0),
        ],
        "share_source": "Directional share of selected US-listed NPL buyers by collections/scale (est.)",
        "mix_buckets": ["Debt Purchasing", "Servicing", "Other"],
        "mix_as_of": "Q1'26 (또는 최근 공시 근사)",
        "mix_rows": [
            {
                "key": "ECPG",
                "name": "ECPG",
                "subject": True,
                "yf": "ECPG",
                "mix": {"Debt Purchasing": 95.2, "Servicing": 4.3, "Other": 0.4},
                "note": "Q1'26 Debt purch $452.8M / Servicing $20.6M / Other $2.0M",
            },
            {
                "key": "PRAA",
                "name": "PRAA",
                "subject": False,
                "yf": "PRAA",
                "mix": {"Debt Purchasing": 92.0, "Servicing": 6.0, "Other": 2.0},
                "note": "채무매입 중심 · 유럽·미주 믹스 근사",
            },
        ],
        "mix_note": (
            "버킷은 Debt Purchasing / Servicing / Other로 정규화. "
            "ECPG는 미국 MCM 회수·ERC 중심. 피어는 공시 세그먼트가 달라 근사."
        ),
    },
    "FTRE": {
        "sector_ko": "헬스케어 · CRO 임상개발 아웃소싱 (심층: Clinical Services)",
        "share_title": "글로벌 임상 CRO 피어셋 스케일 점유 (추정)",
        "share_as_of": "2025–26 · 임상/개발 매출 스케일 근사 vs 전년",
        "share_note": (
            "상장 대형·중형 CRO 임상개발 매출 스케일 상대 점유. "
            "전임상(CRL 일부)·랩 진단(LH)은 정의가 달라 제외·축소. "
            "절대 시장점유율이 아니라 피어셋 방향 비교용."
        ),
        "share_rows": [
            ("IQVIA (IQV)", 28.0, 27.5),
            ("ICON (ICLR)", 14.0, 13.5),
            ("Medpace (MEDP)", 4.5, 4.0),
            ("Fortrea (FTRE)", 4.2, 4.4),
            ("Others (listed/est.)", 49.3, 50.6),
        ],
        "share_source": "Directional share of selected listed CROs by clinical/dev revenue scale (est.)",
        "mix_buckets": ["Full-service/Hybrid", "FSP", "ClinPharm/Other"],
        "mix_as_of": "Q2'26 서술·피어 공시 근사 (FTRE는 단일 Clinical Services 세그먼트)",
        "mix_rows": [
            {
                "key": "FTRE",
                "name": "FTRE",
                "subject": True,
                "yf": "FTRE",
                "mix": {"Full-service/Hybrid": 72.0, "FSP": 18.0, "ClinPharm/Other": 10.0},
                "note": "단일 Clinical Services · FSP 수요↓ · ClinPharm 상쇄(서술 근사)",
            },
            {
                "key": "IQV",
                "name": "IQV",
                "subject": False,
                "yf": "IQV",
                "mix": {"Full-service/Hybrid": 55.0, "FSP": 15.0, "ClinPharm/Other": 30.0},
                "note": "Research+Tech 혼재 → ClinPharm/Other에 테크·데이터 흡수 근사",
            },
            {
                "key": "ICLR",
                "name": "ICLR",
                "subject": False,
                "yf": "ICLR",
                "mix": {"Full-service/Hybrid": 80.0, "FSP": 12.0, "ClinPharm/Other": 8.0},
                "note": "풀서비스 임상 중심",
            },
            {
                "key": "MEDP",
                "name": "MEDP",
                "subject": False,
                "yf": "MEDP",
                "mix": {"Full-service/Hybrid": 90.0, "FSP": 5.0, "ClinPharm/Other": 5.0},
                "note": "고마진 풀서비스 · 치료영역 집중",
            },
        ],
        "mix_note": (
            "버킷은 Full-service/Hybrid / FSP / ClinPharm·Other로 정규화. "
            "FTRE는 공시상 단일 세그먼트라 전달모델 서술에 맞춘 근사 — 방향 비교용."
        ),
    },
    "CMPR": {
        "sector_ko": "산업재 · 대량맞춤 인쇄·프로모 (심층: Mass Customization)",
        "share_title": "상장 특수인쇄·마케팅제품 피어셋 스케일 점유 (추정)",
        "share_as_of": "FY'25–26 · 매출 스케일 근사 vs 전년",
        "share_note": (
            "상장 특수인쇄·마케팅 제품 피어셋 상대 스케일. "
            "Canva·로컬카피숍·아마존 인쇄는 비상장/혼재로 제외. "
            "절대 시장점유율이 아니라 피어셋 방향 비교용."
        ),
        "share_rows": [
            ("Cimpress (CMPR)", 52.0, 50.5),
            ("Deluxe (DLX)", 30.0, 31.0),
            ("Ennis (EBF)", 5.5, 5.8),
            ("Others (listed/est.)", 12.5, 12.7),
        ],
        "share_source": "Directional share of selected US-listed specialty print/marketing peers by revenue scale (est.)",
        "mix_buckets": ["Vista (DTC)", "Upload & Print", "National Pen+Other"],
        "mix_as_of": "Q4 FY'26 (FY ends Jun) · 세그먼트 매출(내부거래 제거 전) 정규화",
        "mix_rows": [
            {
                "key": "CMPR",
                "name": "CMPR",
                "subject": True,
                "yf": "CMPR",
                "mix": {"Vista (DTC)": 49.0, "Upload & Print": 34.4, "National Pen+Other": 16.6},
                "note": "Q4: Vista $486M / U&P $342M / NP+Other $164M (elim 전)",
            },
            {
                "key": "DLX",
                "name": "DLX",
                "subject": False,
                "yf": "DLX",
                "mix": {"Vista (DTC)": 25.0, "Upload & Print": 35.0, "National Pen+Other": 40.0},
                "note": "수표·마케팅솔루션·프로모 혼재 → 버킷 근사",
            },
            {
                "key": "EBF",
                "name": "EBF",
                "subject": False,
                "yf": "EBF",
                "mix": {"Vista (DTC)": 10.0, "Upload & Print": 75.0, "National Pen+Other": 15.0},
                "note": "상업인쇄·양식 중심",
            },
        ],
        "mix_note": (
            "버킷은 Vista(DTC) / Upload&Print(PrintBrothers+Print Group) / National Pen+Other로 정규화. "
            "피어는 공시 세그먼트가 달라 근사 — 방향 비교용."
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


# Name hints for share-row subject matching (display names ≠ ticker).
SUBJECT_SHARE_ALIASES: dict[str, tuple[str, ...]] = {
    "ROKU": ("roku",),
    "RELY": ("remitly",),
    "PEBO": ("peoples",),
    "SBLK": ("star bulk",),
    "CLMT": ("calumet",),
    "TXG": ("10x",),
    "ACHC": ("acadia",),
    "NESR": ("nesr",),
    "LASR": ("nlight",),
    "ECPG": ("encore",),
    "AMRX": ("amneal",),
    "FTRE": ("fortrea",),
    "CMPR": ("cimpress", "vistaprint", "vista"),
    "ZD": ("ziff davis", "ziff"),
    "VSAT": ("viasat",),
    "ANAB": ("anaptys",),
    "SYRE": ("spyre",),
    "DNTH": ("dianthus",),
}


def is_subject_share_name(ticker: str, name: str) -> bool:
    """True if *name* is the subject company in a share panel."""
    t = ticker.upper()
    n = (name or "").strip()
    nu = n.upper()
    if not n:
        return False
    if nu == t or t in nu:
        return True
    for hint in SUBJECT_SHARE_ALIASES.get(t, ()):
        if hint.lower() in n.lower():
            return True
    return False


def subject_share_row_from_profile(ticker: str, prof: dict[str, Any] | None = None) -> ShareRow | None:
    """Return the subject's ShareRow from a PEER_PROFILES entry (offline)."""
    t = ticker.upper()
    prof = prof or get_profile(t)
    if not prof:
        return None
    rows = [ShareRow(n, c, p) for n, c, p in prof.get("share_rows", [])]
    for r in rows:
        if is_subject_share_name(t, r.name):
            return r
    # Fallback: mix_rows subject display name ↔ share row
    for m in prof.get("mix_rows", []):
        if not m.get("subject"):
            continue
        key = str(m.get("name") or m.get("key") or "")
        for r in rows:
            ru, ku = r.name.upper(), key.upper()
            if ku and (ku in ru or ru in ku or is_subject_share_name(t, r.name)):
                return r
    return None


def subject_share_delta(ticker: str) -> float | None:
    row = subject_share_row_from_profile(ticker)
    return None if row is None else float(row.delta_pp)


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
        hit = is_subject_share_name(bundle.ticker, n)
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


class CompeteProfileError(RuntimeError):
    """Raised when 수익구조분석 lacks a PEER_PROFILES entry (chapter is mandatory)."""


def render_compete_section_html(
    charts: dict[str, Path],
    bundle: CompeteBundle,
    *,
    img_b64_fn,
    gloss_fn=None,
    easy_share: str = "",
    easy_mix: str = "",
    gloss_share: list[tuple[str, str]] | None = None,
    gloss_mix: list[tuple[str, str]] | None = None,
    heading_share: str = "1-B. 심층 섹터 경쟁 점유율 · 변화",
    heading_mix: str = "1-C. 경쟁사 매출 구조 비율 비교",
) -> str:
    """Standard compete HTML block for 수익구조분석 PDFs (mandatory chapter)."""

    def _fig(path: Path, caption: str) -> str:
        return (
            f"<figure><img src='data:image/png;base64,{img_b64_fn(path)}'/>"
            f"<figcaption>{caption}</figcaption></figure>"
        )

    def _gloss(items: list[tuple[str, str]] | None) -> str:
        if not items:
            return ""
        if gloss_fn is not None:
            return gloss_fn(items)
        lis = "".join(f"<li><span class='term'>{a}</span> — {b}</li>" for a, b in items)
        return (
            "<div class='gloss'><div class='gloss-title'>이 블록 용어 주석</div>"
            f"<ul>{lis}</ul></div>"
        )

    share_rows = "".join(
        f"<tr><td>{r.name}</td><td>{r.current:.1f}%</td><td>{r.prior:.1f}%</td>"
        f"<td>{r.delta_pp:+.1f}pp</td></tr>"
        for r in bundle.share_rows
    )
    mix_head = "".join(f"<th>{b}</th>" for b in bundle.mix_buckets)
    mix_body = []
    for r in bundle.mix_rows:
        cells = "".join(f"<td>{r['mix'].get(b, 0):.1f}%</td>" for b in bundle.mix_buckets)
        tag = " <b>(대상)</b>" if r.get("subject") else ""
        mix_body.append(
            f"<tr><td>{r['name']}{tag}</td>{cells}"
            f"<td class='small'>{r.get('note', '')}</td></tr>"
        )
    ttm_fig = _fig(charts["ttm"], "TTM 매출 규모") if "ttm" in charts else ""
    easy_s = easy_share or (
        f"<div class='easy'><b>쉽게:</b> <b>{bundle.ticker}</b>의 피어셋 상대 점유·변화(Δpp)다. "
        "절대 글로벌 점유가 아니라 방향·순위 감각용이다.</div>"
    )
    easy_m = easy_mix or (
        "<div class='easy'><b>쉽게:</b> 같은 버킷으로 맞춰 본 매출(또는 손익) 구조 비교다. "
        "공시 세그먼트가 달라 근사치다.</div>"
    )
    return f"""
<h2>{heading_share}</h2>
<p><b>섹터</b> {bundle.sector_ko}</p>
{easy_s}
{_fig(charts['share'], bundle.share_title)}
{_fig(charts['delta'], '점유율 변화 (pp)')}
<table>
  <tr><th>플레이어</th><th>현재</th><th>전년추정</th><th>Δ</th></tr>
  {share_rows}
</table>
<p class="small">{bundle.share_note}<br/>출처: {bundle.share_source} · {bundle.share_as_of}</p>
{_gloss(gloss_share)}

<h2>{heading_mix}</h2>
{easy_m}
{_fig(charts['mix'], '매출 믹스 스택 비교')}
{ttm_fig}
<table>
  <tr><th>티커</th>{mix_head}<th>메모</th></tr>
  {''.join(mix_body)}
</table>
<p class="small">{bundle.mix_note} · {bundle.mix_as_of}</p>
{_gloss(gloss_mix)}
"""


def build_compete_charts(
    ticker: str,
    chart_dir: str | Path,
    *,
    require: bool = True,
) -> tuple[CompeteBundle | None, dict[str, Path]]:
    """Return bundle + chart paths (share, delta, mix, optional ttm).

    ``require=True`` (default): missing ``PEER_PROFILES`` entry raises
    ``CompeteProfileError`` — 수익구조분석 경쟁 챕터는 템플릿 무관 필수.
    """
    bundle = load_compete_bundle(ticker)
    if bundle is None:
        if require:
            raise CompeteProfileError(
                f"수익구조분석({ticker.upper()})에 PEER_PROFILES 항목이 없습니다. "
                "sepa.rev_compete.PEER_PROFILES에 점유율·매출믹스 프로필을 추가하세요."
            )
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
