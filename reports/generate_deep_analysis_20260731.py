#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NASDAQ 심층분석 PDF — 2026-07-31 (53종목 · 매수시나리오 A′ 점검) + Chase 스냅샷 + 기술적분석 훅."""

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

REPORT_DATE = date(2026, 7, 31)
DATE_STR = REPORT_DATE.isoformat()
DATE_TAG = DATE_STR

RANK_PATH = Path("/workspace/reports/rank_20260731.json")
QUAL_PATH = Path("/workspace/reports/qual_20260731.json")

HTML_OUT = Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-31.html")
PDF_WORKSPACE = Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-31.pdf")
PDF_ARTIFACT = Path("/opt/cursor/artifacts/NASDAQ_Deep_Analysis_2026-07-31.pdf")
PDF_ASSETS = Path("/workspace/assets/NASDAQ_Deep_Analysis_2026-07-31.pdf")
CHASE_OUT = Path("/workspace/reports/chase_rr_20260731.json")

# Manual qualitative for tickers missing / thin in prior reports
NEW_Q = {
    "EXPE": {
        "name": "Expedia Group",
        "sector": "소비·온라인여행",
        "feat": "OTA·여행 플랫폼",
        "item": "온라인여행. 한줄: Expedia·Hotels.com 등 OTA",
        "fin": "EPS 4/4 · 업사이드 음수·고점권",
        "strat": "고점·프리미엄 · 관망",
        "news": "예약·ADR·매크로 여행수요",
        "bull": "$330–360", "base": "$270–310", "bear": "$220–250",
        "brk": "수요 둔화·가이던스 컷", "eps": "4/4", "entry": "관망",
        "drop": "가이던스 컷", "chase": "중하·고점", "abc": "$280/$305/$340",
    },
    "APA": {
        "name": "APA Corporation",
        "sector": "에너지·E&P",
        "feat": "원유·가스 탐사생산",
        "item": "독립 E&P. 한줄: 북미·이집트 중심 원유·가스",
        "fin": "EPS 4/4 · 업사이드 +13%급",
        "strat": "에너지 베타 · 위성/눌림",
        "news": "유가·생산량·가이던스",
        "bull": "$45–52", "base": "$34–42", "bear": "$26–32",
        "brk": "유가 급락·생산 미스", "eps": "4/4", "entry": "눌림",
        "drop": "가이던스 컷", "chase": "중상·08-05", "abc": "$34/$42/$48",
    },
    "LAUR": {
        "name": "Laureate Education",
        "sector": "소비·교육",
        "feat": "고등교육 서비스",
        "item": "교육. 한줄: 남미 중심 고등교육 캠퍼스·온라인",
        "fin": "EPS 4/4 · 실적일 D0",
        "strat": "실적일 · 이벤트 갭 금지",
        "news": "등록·마진·통화",
        "bull": "$44–50", "base": "$34–42", "bear": "$26–32",
        "brk": "등록 둔화", "eps": "4/4", "entry": "관망",
        "drop": "가이던스 컷", "chase": "중·07-30실적", "abc": "$36/$41/$48",
    },
    "BIIB": {
        "name": "Biogen",
        "sector": "헬스케어·대형제약",
        "feat": "신경계·희귀질환 치료제",
        "item": "바이오제약. 한줄: Alzheimer·MS·희귀질환 포트",
        "fin": "EPS 4/4 · 실적직후",
        "strat": "실적 소화 · 관망/눌림",
        "news": "파이프라인·급여·경쟁",
        "bull": "$240–270", "base": "$190–230", "bear": "$150–180",
        "brk": "임상·급여 악재", "eps": "4/4", "entry": "눌림",
        "drop": "가이던스 컷", "chase": "중·실적직후", "abc": "$190/$230/$255",
    },
}

# Portfolio-aware Chase label overrides — 2026-07-30
LABEL_OVERRIDE = {
    "ALKS": "중·워치",
    "ECPG": "최상·코어·보유·추가금지",
    "ROKU": "상·08-06",
    "HST": "중상·08-05·고점",
    "INDV": "중·청산후워치·08-04",
    "TXG": "하·과열",
    "RELY": "상·08-05·보유위성",
    "APA": "중상·08-05",
    "ADPT": "중상·실적직후·B주의",
    "VCYT": "중·실적직후",
    "SBLK": "중상·08-05·고점주의",
    "CASY": "중·고점",
    "AMRX": "중·보유·추가금지",
    "CHEF": "중·실적직후",
    "PGNY": "중·눌림",
    "DDOG": "중·눌림",
    "VTRS": "중·고점",
    "TVTX": "중상",
    "PEBO": "중",
    "FTNT": "중·실적직후",
    "FA": "중·고점",
    "LIND": "중·고점",
    "RAPP": "상·08-06위성",
    "KRYS": "중·고점",
    "DRH": "중·실적직후",
    "ATLC": "중상·위성",
    "BTSG": "매도·추격금지",
    "CLMT": "하·고점",
    "STLD": "중",
    "JAZZ": "중·고점",
    "INCY": "중·고점",
    "CNXN": "중하",
    "GPRE": "중하",
    "SCSC": "중",
    "CDNA": "중하·실적직후",
    "CBRL": "하·과열",
    "PTGX": "중하·과열",
    "PAGP": "중하·B주의·우선낮음",
    "CRSR": "하·과열",
    "FTRE": "중·과열주의",
    "LQDA": "하·과열",
    "BRKR": "중하·관망",
    "KNSA": "중하",
    "DNTH": "중·임상변동",
    "SEPN": "중·서프약",
    "SENEA": "중하·데이터약",
    "NESR": "중상·보유위성",
    "ACHC": "상·실적직후·SOFT",
    "SHOO": "중·실적직후·B주의·고점",
    "PLPC": "중",
    "BUSE": "중",
    "EXEL": "중·고점주의",
    "TFSL": "중·A′후보·실적직후주의",
}

# One-line+ Chase detail (표시용). 짧은 라벨(chase)은 TA 선정용으로 유지.
CHASE_DETAIL = {
    "TFSL": "중하·실적직후 — 저축은행. 업사이드 약·관망.",
    "EXEL": "중·고점주의 — 바이오. 업사이드 음수면 추격 비추.",
    "BUSE": "중 — 지역은행. 방어적·급등 추격 불필요.",
    "PLPC": "중 — 산업 전선/케이블. RR 중간·신규는 눌림.",
    "SHOO": "중·실적직후·B주의·고점 — B 게이트 통과나 고점·RSI과열 근접. 위성·소액만.",
    "ACHC": "상·실적직후·SOFT — RR 1위. 실적 직후 소화·눌림 전 추격 비추.",
    "NESR": "중상·보유위성 — 포트 3주. 업사이드 양호·추가매수보다 홀드/축소 관찰.",
    "ALKS": "중·워치 — 차기 실적 멀다. RR 상위이나 신규는 눌림·비중 여유 있을 때만.",
    "ECPG": "최상·코어·강등후보 — RR·Beat 상위이나 포트 코어 과비중. 추가금지·1주 축소로 ~20% 유도.",
    "ROKU": "상·08-06 — 플랫폼 RR 양호하나 1주가 소액북 코어급. NO_ADD·실적 전 추격 금지.",
    "HST": "중상·08-05·고점 — 호텔 RR 중상이나 고점근접·업사이드 음수. 추격보다 눌림·실적창 주의.",
    "INDV": "중·청산후워치 — 기청산. 재진입은 새 셋업·비중 여유 있을 때만.",
    "TXG": "하·과열 — PT 대비 프리미엄·고점권. RR 점수와 무관하게 추격 비추천.",
    "RELY": "상·08-05 — 송금 핀테크 Beat·업사이드 큼. 위성급 눌림·실적창 주의.",
    "APA": "중상·08-05 — E&P Beat·업사이드. 에너지 베타·위성 한도·실적 전 추격 금지.",
    "ADPT": "중·실적직후 — 07-29 실적 소화. 가이던스·반응 확인 전 신규 금지.",
    "VCYT": "중·07-30실적 — 실적 D-0. EARN_D5로 분할 차단. 갭 베팅 금지.",
    "SBLK": "중상 — 건화물 베타·업사이드 양호. 위성·테마 온도 확인 후 눌림.",
    "BIIB": "중·실적직후 — 07-29 실적 소화. 대형 바이오·추격보다 반응 확인.",
    "LAUR": "중·07-30실적 — 실적 D-0. 이벤트 갭 금지·결과 후 재평가.",
    "CASY": "중·고점 — Beat는 좋으나 고가·고점 근접. 추격보다 관망.",
    "AMRX": "중·07-30보유·추가금지 — 보유 코어. 실적 D-0 즉흥·추가 매수 금지.",
    "CHEF": "중·실적직후 — 07-29 실적 소화. 결과·가이던스 확인 후.",
    "PGNY": "중·눌림 — RR 중간. 셋업 대기·분할은 눌림에서만.",
    "DDOG": "중·눌림 — 클라우드 관측. 품질은 있으나 추격보다 눌림.",
    "VTRS": "중·고점 — 제네릭. 방어적·고점 근처면 대기.",
    "TVTX": "중상 — 바이오·업사이드. 위성·변동 허용 시에만.",
    "PEBO": "중 — 지방은행. RR 무난·방어적. 급등 추격 불필요.",
    "EXPE": "중하·고점 — OTA 고점·업사이드 음수. 여행 모멘텀 추격 비추.",
    "FTNT": "하·과열 — 보안주 프리미엄. 고점·비싸면 추격 금지.",
    "FA": "중·고점 — 교육/서비스. 업사이드 음수·고점 → 관망.",
    "LIND": "중·고점 — 크루즈/여행. 고점권이면 관망.",
    "RAPP": "상·08-06위성 — 임상 바이너리. 극소 위성·실적/촉매 추격 금지.",
    "KRYS": "중·고점 — 피부과 바이오. 고가·고점 → 관망 우위.",
    "DRH": "중·07-30실적 — 호텔 리츠 실적일. 결과 전 신규 금지.",
    "ATLC": "중상·위성 — 특화금융. 위성 한도 내·추격 금지.",
    "CMPR": "중·실적직후 — 인쇄/커머스 실적 소화. RR 중간.",
    "BTSG": "매도·추격금지 — 모멘텀 소진/리스크. 신규·추격 금지.",
    "CLMT": "하·고점 — 에너지 인프라. 고점·프리미엄 → 하향.",
    "STLD": "중 — 철강. 경기민감·중간 RR.",
    "JAZZ": "중·고점 — 제약. 고점권 관망.",
    "INCY": "중·고점 — 바이오. 업사이드 음수면 추격 비추.",
    "CNXN": "중하 — IT 리셀. 업사이드 약·관망.",
    "GPRE": "중하 — 에탄올/에너지. RR 하위·관망.",
    "SCSC": "중 — IT 유통. 중간·눌림.",
    "CDNA": "중하·07-30실적 — 이식 진단 실적일·서프 약. 이벤트 주의.",
    "CBRL": "하·과열 — 레스토랑 프리미엄·약세. 추격 금지.",
    "PTGX": "중하·과열 — 바이오. 과열·임상 변동.",
    "PAGP": "중하 — MLP/에너지. RR 약·관망.",
    "CRSR": "하·과열 — 게이밍 HW. 프리미엄·약세 추격 금지.",
    "FTRE": "중·과열주의 — 진단 아웃소싱. 변동·과열 주의.",
    "LQDA": "하·과열 — 호흡기 바이오. 고점 추격 금지.",
    "BRKR": "중하·관망 — 분석기기. 촉매 약하면 대기.",
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



def load_buy_scenarios() -> list[dict]:
    p = Path("/workspace/reports/buy_scenarios_20260731.json")
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return list(raw.get("rows") or [])
    return list(raw)


def buy_scenario_section(scenarios: list[dict]) -> str:
    a = [s for s in scenarios if s.get("scenario") == "A"]
    b = [s for s in scenarios if s.get("scenario") == "B"]
    soft = [s for s in scenarios if s.get("scenario") == "SOFT"]
    if a or b:
        names_a = ", ".join(s.get("t", "") for s in a) or "—"
        names_b = ", ".join(s.get("t", "") for s in b) or "—"
        head = (
            f"<div class='portfolio-box' style='border-color:#166534;background:#ecfdf5'>"
            f"<b>매수 시나리오 해당 (A′ 게이트)</b> — A {len(a)}건 ({esc(names_a)}) · "
            f"B {len(b)}건 ({esc(names_b)}) (적극 고지)</div>"
        )
    else:
        head = (
            "<div class='portfolio-box' style='border-color:#9f1239;background:#fff1f2'>"
            "<b>매수 시나리오 A′/B: 0건</b> — RS≥70용 얕은 눌림·돌파 조건 미충족. "
            "SOFT만 참고 · 추격 매수 비추.</div>"
        )
    rows = []
    for s in a + b + soft:
        note = s.get("caution") or (
            "MA20근처" if s.get("near_ma20") else ("스윙L" if s.get("near_l") else "")
        )
        if s.get("above200") and s.get("align"):
            note = (note + " · " if note else "") + "정배열"
        rows.append(
            "<tr>"
            f"<td><b>{esc(s.get('scenario'))}</b></td>"
            f"<td><b>{esc(s.get('t'))}</b></td>"
            f"<td>{fmt_usd_price(s.get('last') or s.get('px'))}</td>"
            f"<td>{s.get('rsi', 0):.0f}</td>"
            f"<td>{s.get('pct_hi', 0)*100:+.1f}%</td>"
            f"<td>{'Y' if s.get('near_l') or s.get('near_ma20') else '—'}</td>"
            f"<td>{'Y' if s.get('breakout') else '—'}</td>"
            f"<td>D{s.get('edays')}</td>"
            f"<td class='small'>{esc(note or '—')}</td>"
            "</tr>"
        )
    table = ""
    if rows:
        table = (
            "<table><tr><th>유형</th><th>티커</th><th>가격</th><th>RSI</th>"
            "<th>고점대비</th><th>지지</th><th>돌파</th><th>실적</th><th>메모</th></tr>"
            + "".join(rows) + "</table>"
        )
    gloss = (
        "<p class='small'>A′=RS≥70용 얕은 눌림(MA200위+정배열+(MA20|스윙L)+RSI42–62+고점−1%~−8%+거래량OK+실적D−5밖). "
        "B=돌파(거래량급증+RSI&lt;70+실적창밖; RSI≥68 주의). SOFT=A′ 근접.</p>"
    )
    return f"<h2>0. 매수 시나리오 점검 A′ (적극 고지)</h2>{head}{table}{gloss}"




def main() -> None:
    rank = json.loads(RANK_PATH.read_text(encoding="utf-8"))
    qual = json.loads(QUAL_PATH.read_text(encoding="utf-8")) if QUAL_PATH.exists() else {}
    rows = rank["rows"]
    tickers = {r["t"]: merge(r, qual) for r in rows}
    order = [r["t"] for r in rows]
    scenarios = load_buy_scenarios()

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
        json.dumps({"as_of": DATE_STR, "source": "심층분석", "rows": chase_rows, "buy_scenarios": scenarios}, ensure_ascii=False, indent=2),
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

    n_a = sum(1 for s in scenarios if s.get("scenario") == "A")
    n_b = sum(1 for s in scenarios if s.get("scenario") == "B")
    n_soft = sum(1 for s in scenarios if s.get("scenario") == "SOFT")

    doc = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"/>
    <title>NASDAQ 심층분석 {DATE_TAG}</title><style>{build_css()}</style></head><body>
    <section class="cover">
      <h1>NASDAQ 심층분석</h1>
      <p class="sub">Chase Risk-Reward · 매수시나리오 A/B 점검 · 50종목 · 오후 갱신</p>
      <p class="meta">기준일 {DATE_TAG} · 라이브 가격/PT/실적일 · 종료 후 기술적분석 자동</p>
      <div class="portfolio-box" style="text-align:left;max-width:560px;margin:24px auto;">
        <b>매수 시나리오 요약</b><br/>
        A(눌림) <b>{n_a}</b> · B(돌파) <b>{n_b}</b> · SOFT(근접) {n_soft}<br/>
        {"→ 해당 종목은 아래 0장에서 적극 고지" if (n_a or n_b) else "→ <b>오늘은 A/B 없음 · 신규매수보다 관망/정리</b>"}
      </div>
      <div class="portfolio-box" style="text-align:left;max-width:560px;margin:16px auto;">
        <b>포트 실행 메모 (7/31)</b><br/>
        보유: ECPG2 · AMRX9 · LASR2 · SCHD3 · NESR3 · RELY3 · 현금~$222(+₩85만 대기≈+$594)<br/>
        LASR: 회복 보유 · 새 무효화(스윙L/MA20) 재설정<br/>
        보유 실적창: RELY·ECPG 08-05 — 추가금지 · ENLT 아님<br/>
        08-04 INDV · 08-05 HST/APA/SBLK · 08-06 ROKU/RAPP/TXG/PGNY — EARN_D5<br/>
        A′고지: TFSL · B주의: ADPT·SHOO·PAGP(고점/RSI)
      </div>
    </section>
    {buy_scenario_section(scenarios)}
    <h2>Surprise / Chase 요약</h2>
    <p class="small">정렬: Chase RR. 가격·PT는 {DATE_TAG} 라이브. 신규: SHOO·PLPC·BUSE·EXEL·NESR·TFSL·ACHC.</p>
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
      <p class="small">다음 단계: 기술적분석() ← chase_rr_20260731.json</p>
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
    print(f"Buy scenarios A={n_a} B={n_b} SOFT={n_soft}")
    try:
        import sys
        _SRC = Path(__file__).resolve().parents[1] / "src"
        if str(_SRC) not in sys.path:
            sys.path.insert(0, str(_SRC))
        from sepa.tech_analysis import after_deep_analysis

        after_deep_analysis(chase_rows, as_of=DATE_STR, report_dir="reports")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] after_deep_analysis skipped: {exc}")


if __name__ == "__main__":
    main()
