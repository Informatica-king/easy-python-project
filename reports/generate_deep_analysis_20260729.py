#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NASDAQ 심층분석 PDF — 2026-07-29 (49종목) + Chase 스냅샷 + 기술적분석 훅."""

from __future__ import annotations

import html
import json
import math
import shutil
from datetime import date
from pathlib import Path

from weasyprint import HTML

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

REPORT_DATE = date(2026, 7, 29)
DATE_STR = REPORT_DATE.isoformat()
DATE_TAG = DATE_STR

RANK_PATH = Path("/tmp/rank_20260729.json")
QUAL_PATH = Path("/tmp/qual_20260729_full.json")

HTML_OUT = Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-29.html")
PDF_WORKSPACE = Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-29.pdf")
PDF_ARTIFACT = Path("/opt/cursor/artifacts/NASDAQ_Deep_Analysis_2026-07-29.pdf")
PDF_ASSETS = Path("/workspace/assets/NASDAQ_Deep_Analysis_2026-07-29.pdf")
CHASE_OUT = Path("/workspace/reports/chase_rr_20260729.json")

# Manual qualitative for tickers missing / thin in prior reports
NEW_Q = {
    "IART": {
        "name": "Integra LifeSciences",
        "sector": "헬스케어·의료기기",
        "feat": "신경·조직재생 의료기기",
        "item": "의료기기. 한줄: 신경외과·상처·조직기술",
        "fin": "EPS 4/4 · 업사이드 음수·고점권",
        "strat": "퀄리티 혼조 · 관망/눌림",
        "news": "병원 캐펙스·리콜·가이던스",
        "bull": "$24–28", "base": "$18–22", "bear": "$12–16",
        "brk": "가이던스 컷·리콜", "eps": "4/4", "entry": "관망",
        "drop": "가이던스 컷", "chase": "중·고점", "abc": "$18/$22/$26",
    },
    "ADPT": {
        "name": "Adaptive Biotechnologies",
        "sector": "헬스케어·진단",
        "feat": "면역 시퀀싱·MRD",
        "item": "진단·바이오. 한줄: clonoSEQ 등 면역레퍼토리",
        "fin": "EPS 4/4 · 성장·변동",
        "strat": "진단 모멘텀 · 위성/관망",
        "news": "임상·보험급여·경쟁",
        "bull": "$28–35", "base": "$18–24", "bear": "$10–15",
        "brk": "급여·임상 실패", "eps": "4/4", "entry": "눌림",
        "drop": "가이던스 컷", "chase": "중·07-29실적", "abc": "$20/$24/$30",
    },
    "RELY": {
        "name": "Remitly",
        "sector": "금융·핀테크",
        "feat": "국제송금 플랫폼",
        "item": "핀테크. 한줄: 크로스보더 송금 앱",
        "fin": "EPS 4/4 · 업사이드 +25%급",
        "strat": "성장 핀테크 · 눌림/분할검토",
        "news": "송금량·마진·규제",
        "bull": "$30–36", "base": "$22–28", "bear": "$14–18",
        "brk": "성장 둔화·규제", "eps": "4/4", "entry": "눌림",
        "drop": "가이던스 컷", "chase": "상·08-05", "abc": "$24/$28/$34",
    },
    "CRSR": {
        "name": "Corsair Gaming",
        "sector": "IT·게이밍하드웨어",
        "feat": "게이밍 PC·주변기기",
        "item": "하드웨어. 한줄: 게이밍 부품·주변기기",
        "fin": "EPS 2/4 · PT 프리미엄",
        "strat": "과열·약세 · 관망",
        "news": "PC 수요·재고",
        "bull": "$14–18", "base": "$9–12", "bear": "$6–8",
        "brk": "수요 둔화", "eps": "2/4", "entry": "관망",
        "drop": "가이던스 컷", "chase": "하·과열", "abc": "$9/$11/$15",
    },
    "PEBO": {
        "name": "Peoples Bancorp",
        "sector": "금융·지방은행",
        "feat": "지역은행",
        "item": "은행. 한줄: 오하이오 중심 커뮤니티뱅크",
        "fin": "EPS 4/4 · 금리·신용",
        "strat": "방어적 금융 · 중·눌림",
        "news": "NIM·신용비용",
        "bull": "$48–55", "base": "$38–45", "bear": "$28–34",
        "brk": "신용 악화", "eps": "4/4", "entry": "눌림",
        "drop": "가이던스 컷", "chase": "중", "abc": "$40/$45/$52",
    },
    "CNXN": {
        "name": "PC Connection",
        "sector": "IT·유통",
        "feat": "IT 솔루션 유통",
        "item": "IT 리셀러. 한줄: B2B IT 제품·서비스",
        "fin": "EPS 3/4 · 업사이드 음수",
        "strat": "고점·프리미엄 · 관망",
        "news": "기업 IT 지출",
        "bull": "$90–100", "base": "$70–85", "bear": "$55–65",
        "brk": "수요 둔화", "eps": "3/4", "entry": "관망",
        "drop": "가이던스 컷", "chase": "중하", "abc": "$75/$85/$95",
    },
    "CBRL": {
        "name": "Cracker Barrel",
        "sector": "소비·레스토랑",
        "feat": "캐주얼 다이닝·로드사이드",
        "item": "레스토랑 체인. 한줄: 크래커배럴 매장·리테일",
        "fin": "EPS 혼조 · PT 프리미엄",
        "strat": "고점·프리미엄 · 관망",
        "news": "동일점 매출·마진",
        "bull": "$60–70", "base": "$48–58", "bear": "$35–45",
        "brk": "트래픽·마진 악화", "eps": "2/4", "entry": "관망",
        "drop": "가이던스 컷", "chase": "하·과열", "abc": "$50/$55/$65",
    },
}

# Portfolio-aware Chase label overrides — 2026-07-29
LABEL_OVERRIDE = {
    "ALKS": "중·실적직후워치",
    "ECPG": "최상·코어·강등후보",
    "ROKU": "상·08-06",
    "ACHC": "중·실적직후",
    "HST": "중상·눌림",
    "INDV": "중·청산후워치",
    "RELY": "상·08-05",
    "TXG": "하·과열",
    "ADPT": "중·07-29실적",
    "VCYT": "중하·07-30과열",
    "SBLK": "중상",
    "CASY": "중·고점",
    "AMRX": "중·07-30보유·추가금지",
    "PGNY": "중·눌림",
    "DDOG": "중·눌림",
    "CHEF": "중·07-29실적",
    "VTRS": "중·눌림",
    "IART": "중·고점",
    "FTNT": "하·과열",
    "PEBO": "중",
    "TVTX": "중상",
    "FA": "중·눌림",
    "LIND": "중·고점",
    "RAPP": "상·08-06위성",
    "ANDE": "중상",
    "DRH": "중상",
    "KRYS": "중·고점",
    "ATLC": "중상·위성",
    "CLMT": "하·고점",
    "CMPR": "중",
    "BTSG": "매도·추격금지",
    "STLD": "중",
    "JAZZ": "중·고점",
    "INCY": "중·고점",
    "SCSC": "중",
    "CNXN": "중하",
    "GPRE": "중하",
    "CBRL": "하·과열",
    "FTRE": "중·과열주의",
    "CDNA": "하·과열",
    "PAGP": "중하",
    "PTGX": "중하·과열",
    "LQDA": "하·과열",
    "BRKR": "중하·관망",
    "CRSR": "하·과열",
    "KNSA": "중하",
    "DNTH": "중·임상변동",
    "SEPN": "중·서프약",
    "SENEA": "중하·데이터약",
}

# One-line+ Chase detail (표시용). 짧은 라벨(chase)은 TA 선정용으로 유지.
CHASE_DETAIL = {
    "ALKS": "중·실적직후워치 — 실적 직후라 신규 분할 보류. 보유/관심은 가이던스·반응 확인 후 눌림만.",
    "ECPG": "최상·코어·강등후보 — RR·Beat 상위이나 포트 코어 과비중. 추가금지·1주 축소로 ~20% 유도.",
    "ROKU": "상·08-06 — 플랫폼 RR 양호하나 1주 가격이 소액북 코어급. NO_ADD·실적 전 추격 금지.",
    "ACHC": "중·실적직후 — 실적 직후 소화 구간. 추격보다 반응·가이던스 확인 후 재평가.",
    "HST": "중상·눌림 — 호텔 섹터 RR 중상. 고점 근접이면 분할보다 눌림 대기.",
    "INDV": "중·청산후워치 — 기청산 종목. 재진입은 새 셋업·비중 여유 있을 때만.",
    "RELY": "상·08-05 — 송금 핀테크 Beat·업사이드 큼. 위성급 눌림·실적창 주의.",
    "TXG": "하·과열 — PT 대비 프리미엄·고점권. RR 점수와 무관하게 추격 비추천.",
    "ADPT": "중·07-29실적 — 실적 D-0. EARN_D5로 분할 차단. 결과 확인 전 신규 금지.",
    "VCYT": "중하·07-30과열 — 실적 임박·고점권. 이벤트 갭 베팅 금지.",
    "SBLK": "중상 — 건화물 베타·업사이드 양호. 위성·테마 온도 확인 후 눌림.",
    "CASY": "중·고점 — Beat는 좋으나 고가·고점 근접. 추격보다 관망.",
    "AMRX": "중·07-30보유·추가금지 — 보유 코어. 실적 D-1~0 즉흥·추가 매수 금지.",
    "PGNY": "중·눌림 — RR 중간. 셋업 대기·분할은 눌림에서만.",
    "DDOG": "중·눌림 — 클라우드 관측. 품질은 있으나 추격보다 눌림.",
    "CHEF": "중·07-29실적 — 실적일. 결과 전 신규 금지·보유만.",
    "VTRS": "중·눌림 — 제네릭. 방어적·고점 근처면 대기.",
    "IART": "중·고점 — 의료기기. 업사이드 음수·고점권 → 관망.",
    "FTNT": "하·과열 — 보안주 프리미엄. 고점·비싸면 추격 금지.",
    "PEBO": "중 — 지방은행. RR 무난·방어적. 급등 추격 불필요.",
    "TVTX": "중상 — 바이오·업사이드. 위성·변동 허용 시에만.",
    "FA": "중·눌림 — 교육/서비스. 눌림 대기.",
    "LIND": "중·고점 — 크루즈/여행. 고점권이면 관망.",
    "RAPP": "상·08-06위성 — 임상 바이너리. 극소 위성·실적/촉매 추격 금지.",
    "ANDE": "중상 — 농산물 유통. TA 분할후보여도 EARN_D5면 대기.",
    "DRH": "중상 — 호텔 리츠. 중상 RR·고점이면 눌림.",
    "KRYS": "중·고점 — 피부과 바이오. 고가·고점 → 관망 우위.",
    "ATLC": "중상·위성 — 특화금융. 위성 한도 내·추격 금지.",
    "CLMT": "하·고점 — 에너지 인프라. 고점·프리미엄 → 하향.",
    "CMPR": "중 — 인쇄/커머스. RR 중간·특별 촉매 없으면 대기.",
    "BTSG": "매도·추격금지 — 모멘텀 소진/리스크. 신규·추격 금지.",
    "STLD": "중 — 철강. 경기민감·중간 RR.",
    "JAZZ": "중·고점 — 제약. 고점권 관망.",
    "INCY": "중·고점 — 바이오. 업사이드 음수면 추격 비추.",
    "SCSC": "중 — IT 유통. 중간·눌림.",
    "CNXN": "중하 — IT 리셀. 업사이드 약·관망.",
    "GPRE": "중하 — 에탄올/에너지. RR 하위·관망.",
    "CBRL": "하·과열 — 레스토랑 프리미엄·약세. 추격 금지.",
    "FTRE": "중·과열주의 — 진단 아웃소싱. 변동·과열 주의.",
    "CDNA": "하·과열 — 이식 진단. 고점·이벤트 주의.",
    "PAGP": "중하 — MLP/에너지. RR 약·관망.",
    "PTGX": "중하·과열 — 바이오. 과열·임상 변동.",
    "LQDA": "하·과열 — 호흡기 바이오. 고점 추격 금지.",
    "BRKR": "중하·관망 — 분석기기. 촉매 약하면 대기.",
    "CRSR": "하·과열 — 게이밍 HW. 프리미엄·약세 추격 금지.",
    "KNSA": "중하 — 바이오. 서프/업사이드 약.",
    "DNTH": "중·임상변동 — 임상 이벤트 지배. 위성·소액만.",
    "SEPN": "중·서프약 — 업사이드 있어도 서프라이즈 약. 신중.",
    "SENEA": "중하·데이터약 — EPS 이력 빈약. 데이터 보강 전 관망.",
}


def fmt_usd_price(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if v >= 1000:
        return f"${v:,.0f}"
    if v >= 100:
        return f"${v:,.2f}"
    return f"${v:.2f}"


def fmt_pct(v, digits=1) -> str:
    if v is None:
        return "—"
    return f"{v * 100:+.{digits}f}%"


def fmt_mcap(m) -> str:
    if not m:
        return "—"
    if m >= 1e12:
        return f"${m / 1e12:.2f}T"
    if m >= 1e9:
        return f"${m / 1e9:.2f}B"
    if m >= 1e6:
        return f"${m / 1e6:.0f}M"
    return str(m)


def fmt_ratio(v) -> str:
    if v is None:
        return "—"
    return f"{v:.0%}"


def esc(s) -> str:
    return html.escape(str(s) if s is not None else "—")


def assign_chase(r: dict) -> str:
    t = r["t"]
    if t in LABEL_OVERRIDE:
        return LABEL_OVERRIDE[t]
    ups = r.get("upside")
    near = r.get("near_high") or 0
    if ups is not None and ups < -0.15 and near >= 0.95:
        return "하·과열"
    if ups is not None and ups > 0.2 and (r.get("epsBeat") or 0) >= 3:
        return "상"
    if r["rank"] <= 10:
        return "상"
    if r["rank"] <= 20:
        return "중"
    return "중하"


def build_chase_detail(label: str, r: dict) -> str:
    """Display line (≥1 sentence). Keep short `label` for TA rules."""
    t = r["t"]
    if t in CHASE_DETAIL:
        return CHASE_DETAIL[t]
    ups = fmt_pct(r.get("upside"))
    near = fmt_ratio(r.get("near_high"))
    earn = r.get("earnDate") or "—"
    beat = f"{r.get('epsBeat') or 0}/{r.get('epsN') or 0}"
    bits = {
        "최상": "Chase RR 최상위권. 실행은 포트 비중·이벤트 창을 먼저 본다.",
        "상": f"RR 상위. 업사이드 {ups} · 고점근접 {near} · 실적 {earn}. 추격보다 눌림·비중 확인.",
        "중상": f"RR 중상. EPS {beat} · 업사이드 {ups}. 위성·분할 후보이나 고점이면 대기.",
        "중하": f"RR 중하위. 업사이드 {ups} · 고점 {near}. 신규보다 관망.",
        "중": f"RR 중간. EPS {beat} · 실적 {earn}. 셋업·눌림 확인 후.",
        "하": f"RR 하향/비선호. 업사이드 {ups} · 고점 {near}. 추격 금지.",
        "매도": "모멘텀·리스크 비적합. 신규·추격 금지.",
    }
    for k, v in bits.items():
        if label.startswith(k) or k in label[:4]:
            return f"{label} — {v}"
    if "과열" in label:
        return f"{label} — 고점·프리미엄 구간. 점수와 별개로 추격 비추천."
    return f"{label} — 업사이드 {ups} · 고점근접 {near} · EPS {beat} · 실적 {earn}."


def merge(r: dict, qual: dict) -> dict:
    t = r["t"]
    q = dict(qual.get(t, {}))
    q.update(NEW_Q.get(t, {}))
    q["t"] = t
    q["rank"] = r["rank"]
    q["px"] = r["px"]
    q["h"] = r["h"]
    q["l"] = r["l"]
    q["ptA"] = r["ptA"]
    q["ptL"] = r["ptL"]
    q["ptH"] = r["ptH"]
    q["upside"] = r["upside"]
    q["near_high"] = r["near_high"]
    q["prem"] = r.get("prem")
    q["mcap_num"] = r.get("mcap")
    q["mcap"] = q.get("mcap") or fmt_mcap(r.get("mcap"))
    q["name"] = q.get("name") or r.get("name") or t
    q["sector"] = q.get("sector") or r.get("sector") or "—"
    q["feat"] = q.get("feat") or r.get("industry") or "—"
    q["earnDate"] = r.get("earnDate") or "—"
    q["epsBeat"] = r.get("epsBeat")
    q["epsN"] = r.get("epsN")
    q["avgSurp"] = r.get("avgSurp")
    q["eps"] = q.get("eps") or (f"{r['epsBeat']}/{r['epsN']}" if r.get("epsN") else "—")
    q["sur"] = q.get("sur") or f"EPS{q['eps']}"
    rec = r.get("rec") or "—"
    q["cons"] = q.get("cons") or f"{rec} PT평균{fmt_usd_price(r['ptA'])} ({fmt_pct(r['upside'])})"
    q["chase"] = assign_chase(r)
    q["chase_detail"] = build_chase_detail(q["chase"], r)
    q["item"] = q.get("item") or q.get("name") or t
    q["fin"] = q.get("fin") or "—"
    q["strat"] = q.get("strat") or "—"
    q["news"] = q.get("news") or "—"
    q["bull"] = q.get("bull") or "—"
    q["base"] = q.get("base") or "—"
    q["bear"] = q.get("bear") or "—"
    q["brk"] = q.get("brk") or "—"
    q["entry"] = q.get("entry") or "—"
    q["drop"] = q.get("drop") or "—"
    q["abc"] = q.get("abc") or f"{fmt_usd_price(r['ptA'])}"
    return q


def thesis_line(q: dict) -> str:
    strat = q.get("strat") or ""
    if strat and strat != "—":
        return strat.split("→")[0].strip() if "→" in strat else strat[:140]
    return f"{q.get('sector')} — {q.get('feat')}"


def build_css() -> str:
    return f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:14mm 12mm 16mm 12mm;
      @bottom-center {{ content:"NASDAQ 심층분석 {DATE_TAG} — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }}
    }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.5pt; line-height:1.45; color:#1a1a1a; }}
    h1 {{ font-size:22pt; margin:0 0 8px; }}
    h2 {{ font-size:13pt; margin:14px 0 6px; border-bottom:2px solid #2c5282; padding-bottom:3px; }}
    h3 {{ font-size:11pt; margin:10px 0 4px; color:#2c5282; }}
    .cover {{ page-break-after:always; min-height:240mm; display:flex; flex-direction:column;
      justify-content:center; text-align:center; }}
    .sub {{ font-size:12pt; color:#444; margin-top:12px; }}
    .meta {{ font-size:10pt; color:#555; margin-top:24px; }}
    table {{ width:100%; border-collapse:collapse; font-size:8pt; margin:8px 0; }}
    th,td {{ border:1px solid #ccc; padding:3px 5px; vertical-align:top; }}
    th {{ background:#edf2f7; font-weight:bold; }}
    tr:nth-child(even) td {{ background:#fafafa; }}
    td.chase {{ font-size:7.5pt; line-height:1.35; min-width:42%; }}
    .ticker-section {{ page-break-before:always; }}
    .ticker-head {{ background:#2c5282; color:#fff; padding:8px 10px; margin:0 0 8px; font-size:12pt; font-weight:bold; }}
    .tag {{ display:inline-block; background:#bee3f8; padding:1px 6px; border-radius:3px; font-size:8pt; margin:1px; }}
    .conclusion td:first-child {{ font-weight:bold; width:22%; background:#f7fafc; }}
    .portfolio-box {{ background:#fffaf0; border:1px solid #d69e2e; padding:10px; margin:10px 0; }}
    .small {{ font-size:8pt; color:#555; }}
    """


def ticker_section(q: dict) -> str:
    t = q["t"]
    return f"""
    <section class="ticker-section" id="{esc(t)}">
      <div class="ticker-head">#{q['rank']} {esc(t)} — {esc(q.get('name', t))}</div>
      <div>
        <span class="tag">현재 {fmt_usd_price(q['px'])}</span>
        <span class="tag">PT {fmt_usd_price(q['ptL'])}–{fmt_usd_price(q['ptH'])} (평균 {fmt_usd_price(q['ptA'])})</span>
        <span class="tag">업사이드 {fmt_pct(q['upside'])}</span>
        <span class="tag">52주 {fmt_usd_price(q.get('l'))}–{fmt_usd_price(q.get('h'))}</span>
        <span class="tag">고점근접 {fmt_ratio(q.get('near_high'))}</span>
      </div>
      <h3>1. 한줄 Thesis</h3>
      <p>{esc(thesis_line(q))}</p>
      <h3>2. 섹터 · 특성 · 시총</h3>
      <p><b>섹터</b> {esc(q.get('sector'))} · <b>특성</b> {esc(q.get('feat'))} · <b>시총</b> {esc(q.get('mcap'))}</p>
      <h3>3. 핵심 제품</h3>
      <p>{esc(q.get('item'))}</p>
      <h3>4. 재무 · 컨센서스 · 서프라이즈 · 전략</h3>
      <p>{esc(q.get('fin'))}</p>
      <p><b>컨센서스</b> {esc(q.get('cons'))}</p>
      <p><b>서프라이즈</b> {esc(q.get('sur'))}

        (평균 EPS 서프라이즈 {fmt_pct(q.get('avgSurp'), 2) if q.get('avgSurp') is not None else '—'})</p>
      <p><b>전략</b> {esc(q.get('strat'))}</p>
      <h3>5. 섹터 뉴스 · 출처</h3>
      <p>{esc(q.get('news'))} · 실적일 <b>{esc(q.get('earnDate'))}</b></p>
      <h3>6. Bull / Base / Bear · Breakers</h3>
      <p>Bull {esc(q.get('bull'))} · Base {esc(q.get('base'))} · Bear {esc(q.get('bear'))}</p>
      <p><b>Breaker</b> {esc(q.get('brk'))} · ABC {esc(q.get('abc'))}</p>
      <h3>7. 결론 표</h3>
      <table class="conclusion">
        <tr><td>섹터</td><td>{esc(q.get('sector'))}</td></tr>
        <tr><td>핵심</td><td>{esc(str(q.get('item',''))[:90])}</td></tr>
        <tr><td>EPS</td><td>{esc(q.get('eps'))}</td></tr>
        <tr><td>신규진입</td><td>{esc(q.get('entry'))}</td></tr>
        <tr><td>탈락</td><td>{esc(q.get('drop'))}</td></tr>
        <tr><td>Chase</td><td><b>{esc(q.get('chase'))}</b><br/><span class="small">{esc(q.get('chase_detail'))}</span></td></tr>
      </table>
    </section>
    """


def main() -> None:
    rank = json.loads(RANK_PATH.read_text(encoding="utf-8"))
    qual = json.loads(QUAL_PATH.read_text(encoding="utf-8")) if QUAL_PATH.exists() else {}
    rows = rank["rows"]
    tickers = {r["t"]: merge(r, qual) for r in rows}
    order = [r["t"] for r in rows]

    # Chase snapshot for 기술적분석 auto
    chase_rows = []
    for r in rows:
        q = tickers[r["t"]]
        chase_rows.append({
            "rank": r["rank"],
            "ticker": r["t"],
            "chase": q["chase"],
            "chase_detail": q.get("chase_detail"),
            "px": r["px"],
            "earn_date": r.get("earnDate"),
        })
    CHASE_OUT.parent.mkdir(parents=True, exist_ok=True)
    CHASE_OUT.write_text(
        json.dumps({"as_of": DATE_STR, "source": "심층분석", "rows": chase_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Chase snapshot {CHASE_OUT}")

    summary_rows = []
    for t in order:
        q = tickers[t]
        summary_rows.append(
            f"<tr><td>{q['rank']}</td><td><b>{esc(t)}</b></td>"
            f"<td>{fmt_usd_price(q['px'])}</td><td>{fmt_usd_price(q['ptA'])}</td>"
            f"<td>{fmt_pct(q['upside'])}</td>"
            f"<td>{q.get('epsBeat','—')}/{q.get('epsN','—')}</td>"
            f"<td>{esc(q.get('earnDate'))}</td>"
            f"<td class='chase'><b>{esc(q.get('chase'))}</b><br/>{esc(q.get('chase_detail'))}</td></tr>"
        )

    body = "".join(ticker_section(tickers[t]) for t in order)
    final_rows = []
    for t in order:
        q = tickers[t]
        final_rows.append(
            f"<tr><td>{q['rank']}</td><td><b>{esc(t)}</b></td>"
            f"<td>{fmt_usd_price(q['px'])}</td><td>{fmt_usd_price(q['ptA'])}</td>"
            f"<td>{fmt_pct(q['upside'])}</td>"
            f"<td class='chase'><b>{esc(q['chase'])}</b><br/>{esc(q.get('chase_detail'))}</td></tr>"
        )

    doc = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"/>
    <title>NASDAQ 심층분석 {DATE_TAG}</title><style>{build_css()}</style></head><body>
    <section class="cover">
      <h1>NASDAQ 심층분석</h1>
      <p class="sub">Chase Risk-Reward · 실적 서프라이즈 · 49종목</p>
      <p class="meta">기준일 {DATE_TAG} · 라이브 가격/PT/실적일 · 종료 후 기술적분석 자동</p>
      <div class="portfolio-box" style="text-align:left;max-width:540px;margin:24px auto;">
        <b>포트 실행 메모 (7/29 · MU/CRDO 매도대기)</b><br/>
        보유: ECPG · AMRX · LASR · SCHD · NESR(4) · MU/CRDO 전량매도 대기<br/>
        평가~$946 · USD~$196 · 체결후 현금~$459(~45%) 가정<br/>
        정리: ECPG 2→1 · NESR 4→3 · LASR 무효$60.50 · AMRX 07-30 즉흥금지<br/>
        이벤트: CHEF/ADPT 07-29 · AMRX/VCYT 07-30 · RELY/ECPG/HST 08-05 · ROKU/RAPP 08-06<br/>
        과열·반도체 추격 금지 · 신규매수보다 리스크축소 우선
      </div>
    </section>
    <h2>Surprise / Chase 요약</h2>
    <p class="small">정렬: Chase RR. 가격·PT는 {DATE_TAG} 라이브.</p>
    <table>
      <tr><th>#</th><th>티커</th><th>가격</th><th>PT</th><th>업사이드</th><th>EPS B/N</th><th>실적일</th><th>Chase</th></tr>
      {''.join(summary_rows)}
    </table>
    {body}
    <section class="ticker-section">
      <h2>최종 Chase RR 순위 + 실행</h2>
      <table>
        <tr><th>#</th><th>티커</th><th>가격</th><th>PT</th><th>업사이드</th><th>Chase</th></tr>
        {''.join(final_rows)}
      </table>
      <p class="small">다음 단계: 기술적분석() ← chase_rr_{DATE_TAG.replace('-','')}.json 자동 선정</p>
    </section>
    </body></html>
    """
    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(doc, encoding="utf-8")
    print(f"HTML {HTML_OUT} {HTML_OUT.stat().st_size}")
    pdf = HTML(filename=str(HTML_OUT)).write_pdf()
    for p in (PDF_WORKSPACE, PDF_ARTIFACT, PDF_ASSETS):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf)
        print(f"PDF {p} {p.stat().st_size}")
    print("Top-12 Chase:", ", ".join(order[:12]))


if __name__ == "__main__":
    main()
