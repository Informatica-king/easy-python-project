#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NASDAQ 심층분석 PDF — 2026-08-12 (60종목 · 매수시나리오 A′ 점검) + Chase 스냅샷 + 기술적분석 훅."""

from __future__ import annotations

import html
import json
import math
import shutil
from datetime import date
from pathlib import Path

from weasyprint import HTML

from sepa.share_gain import annotate_text, assess_share_gain, enrich_qual_fields

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

REPORT_DATE = date(2026, 8, 12)
DATE_STR = REPORT_DATE.isoformat()
DATE_TAG = DATE_STR

RANK_PATH = Path("/workspace/reports/rank_20260812.json")
QUAL_PATH = Path("/workspace/reports/qual_20260812.json")

HTML_OUT = Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-08-12.html")
PDF_WORKSPACE = Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-08-12.pdf")
PDF_ARTIFACT = Path("/opt/cursor/artifacts/NASDAQ_Deep_Analysis_2026-08-12.pdf")
PDF_ASSETS = Path("/workspace/assets/NASDAQ_Deep_Analysis_2026-08-12.pdf")
CHASE_OUT = Path("/workspace/reports/chase_rr_20260812.json")

# Manual qualitative for tickers missing / thin in prior reports
NEW_Q = {
    "CGNX": {
        "name": "Cognex",
        "sector": "IT·산업비전",
        "feat": "머신비전·바코드",
        "item": "산업 자동화. 한줄: 공장·물류 머신비전 시스템",
        "fin": "EPS 4/4 · 업사이드 +18%급 · 08-05",
        "strat": "EARN_D5 · 위성/눌림",
        "news": "공장캡ex·물류자동화",
        "bull": "$85–100", "base": "$60–78", "bear": "$45–58",
        "brk": "캡ex 둔화·가이던스 컷", "eps": "4/4", "entry": "관망",
        "drop": "가이던스 컷", "chase": "중상·08-05", "abc": "$60/$75/$90",
    },
    "IESC": {
        "name": "IES Holdings",
        "sector": "산업·전기설비",
        "feat": "전기·통신 인프라 시공",
        "item": "전기설비. 한줄: 상업·산업 전기·통신 인프라",
        "fin": "EPS 4/4 · 업사이드 음수·고점권",
        "strat": "급등 후 고점 · 추격 비추",
        "news": "수주·마진·인력",
        "bull": "$800–900", "base": "$600–740", "bear": "$450–580",
        "brk": "수주 둔화", "eps": "4/4", "entry": "관망",
        "drop": "가이던스 컷", "chase": "중·고점주의", "abc": "$600/$720/$850",
    },
    "APA": {
        "name": "APA Corporation",
        "sector": "에너지·E&P",
        "feat": "원유·가스 탐사생산",
        "item": "독립 E&P. 한줄: 북미·이집트 중심 원유·가스",
        "fin": "EPS 4/4 · 업사이드 +11%급 · 08-05",
        "strat": "에너지 베타 · 위성/눌림 · EARN_D5",
        "news": "유가·생산량·가이던스",
        "bull": "$45–52", "base": "$34–42", "bear": "$26–32",
        "brk": "유가 급락·생산 미스", "eps": "4/4", "entry": "관망",
        "drop": "가이던스 컷", "chase": "중상·08-05", "abc": "$34/$42/$48",
    },
    "LAUR": {
        "name": "Laureate Education",
        "sector": "소비·교육",
        "feat": "고등교육 서비스",
        "item": "교육. 한줄: 남미 중심 고등교육 캠퍼스·온라인",
        "fin": "EPS 4/4 · A′ 게이트",
        "strat": "A′ 소액 분할 가능 · 추격 금지",
        "news": "등록·마진·통화",
        "bull": "$44–50", "base": "$34–42", "bear": "$26–32",
        "brk": "등록 둔화", "eps": "4/4", "entry": "분할검토",
        "drop": "가이던스 컷", "chase": "중·A′후보", "abc": "$36/$41/$48",
    },
    "CMPR": {
        "name": "Cimpress",
        "sector": "소비·인쇄커머스",
        "feat": "대량맞춤 인쇄·커머스",
        "item": "인쇄 커머스. 한줄: Vistaprint 등 대량맞춤 인쇄",
        "fin": "EPS 3/4 · A′ 게이트",
        "strat": "A′ 위성 소액 · 추격 금지",
        "news": "주문·마진·광고비",
        "bull": "$120–140", "base": "$90–110", "bear": "$70–85",
        "brk": "수요 둔화", "eps": "3/4", "entry": "분할검토",
        "drop": "가이던스 컷", "chase": "중·A′후보", "abc": "$90/$110/$130",
    },
}

# Portfolio-aware Chase label overrides — 2026-07-30
LABEL_OVERRIDE = {
    "ALKS": "중상·SOFT·워치",
    "ECPG": "최상·품질A·보유·추가금지",
    "ROKU": "상·08-06",
    "HST": "중상·08-05·고점",
    "INDV": "중·청산후워치·08-04",
    "TXG": "중·품질C·보유4주·천장OVER·추가금지",
    "APA": "중상·08-05",
    "ADPT": "중·SOFT·실적직후",
    "SBLK": "중상·08-05·고점주의",
    "CASY": "중·SOFT·고점주의",
    "AMRX": "중·품질B·보유10주·추가금지",
    "LASR": "중상·품질B·보유·추가금지·08-06",
    "RELY": "중·08-08청산후워치·추격금지",
    "CHEF": "중·고점주의",
    "PGNY": "중·08-06",
    "DDOG": "중·08-06",
    "VTRS": "중·08-06",
    "TVTX": "중상·08-04",
    "PEBO": "중",
    "FTNT": "중·A′후보",
    "FA": "중·08-06·고점",
    "LIND": "중·08-03·고점",
    "RAPP": "상·08-06위성",
    "KRYS": "중·08-03·고점",
    "DRH": "중·실적직후·고점",
    "ATLC": "중상·08-06위성",
    "CLMT": "하·과열",
    "STLD": "중",
    "JAZZ": "중·A′후보",
    "INCY": "중·SOFT",
    "CNXN": "중하",
    "GPRE": "중하·08-06",
    "SCSC": "중",
    "CDNA": "중하·실적직후·과열",
    "CBRL": "하·과열",
    "PTGX": "중하·08-06",
    "PAGP": "중하·우선낮음",
    "CRSR": "하·과열·08-06",
    "FTRE": "중·과열주의",
    "LQDA": "하·과열",
    "BRKR": "중하·08-04",
    "KNSA": "중하",
    "DNTH": "중·08-06·임상변동",
    "SEPN": "중·SOFT·서프약",
    "SENEA": "중하·08-06·데이터약",
    "NESR": "중·08-11청산후워치·추격금지",
    "ACHC": "상·실적직후",
    "SHOO": "중·실적직후·고점",
    "TFSL": "중·SOFT",
    "LAUR": "중·A′후보",
    "CMPR": "중·품질C·보유·추가금지",
    "CGNX": "중상·08-05",
    "IESC": "중·고점주의",
}

# One-line+ Chase detail (표시용). 짧은 라벨(chase)은 TA 선정용으로 유지.
CHASE_DETAIL = {
    "LAUR": "중·A′후보 — 교육. A′ 게이트 통과(MA20근처·RSI57·고점−6%). 분할은 소액·추격 금지.",
    "FTNT": "중·품질B·보유1주·추가금지 — A′로테이션 신규. NO_ADD·추격 금지.",
    "CMPR": "중·품질C·보유·추가금지 — 유니버스 외·1주. 추가금지.",
    "TFSL": "중·SOFT — 저축은행. A′ 근접(RSI63·고점−5%). 업사이드 음수·관망 우위.",
    "SHOO": "중·실적직후·고점 — 07-30 실적 소화. 고점권이면 신규보다 관망.",
    "ACHC": "상·실적직후 — RR 1위. 실적 직후 소화·눌림 전 추격 비추.",
    "NESR": "중상·품질C·SOFT·보유·추가금지 — 한도OVER. 홀드/축소 관찰.",
    "ALKS": "중상·SOFT·워치 — RR 2위·A′ 근접(스윙L). 실적 멀다·눌림·비중 여유 시.",
    "ECPG": "최상·품질A·추가금지 — 8/5 실적직후 소화. 천장권·추가·갭추격 금지.",
    "ROKU": "상·08-06 — 플랫폼 RR 양호·EARN_D5. NO_ADD·실적 전 추격 금지.",
    "HST": "중상·08-05·고점 — 호텔 RR 중상·업사이드 음수·EARN_D5. 추격 비추.",
    "INDV": "중·청산후워치·08-04 — 기청산·EARN_D5. 재진입은 새 셋업·비중 여유 시.",
    "TXG": "하·과열·품질C·보유3주·추가금지 — 비중OVER·오늘(08-06) AMC. 물타기·추격 금지.",
    "APA": "중상·08-05 — E&P Beat·업사이드·EARN_D5. 위성 한도·추격 금지.",
    "ADPT": "중·SOFT·실적직후 — A′ 근접(고점−8% 경계). 소화 확인 후.",
    "SBLK": "중상·08-05·고점주의 — 건화물·EARN_D5. 위성·눌림만.",
    "CASY": "중·SOFT·고점주의 — A′ 근접·고가주. 추격보다 관망.",
    "AMRX": "중·품질B·보유·추가금지 — 한도10% OVER. 즉흥·추가 매수 금지.",
    "LASR": "중상·품질B·보유·추가금지 — 오늘(08-06) EARN_D5 AMC. 추격·추가 금지.",
    "RELY": "중·08-08청산후워치 — SCSC/FTNT 로테이션. 추격 재매수 금지.",
    "CHEF": "중·고점주의 — RSI 과열권. 추격 금지·눌림 대기.",
    "PGNY": "중·08-06 — RR 중간·EARN_D5. 분할은 실적 후 눌림만.",
    "DDOG": "중·08-06 — 클라우드 관측·EARN_D5. 추격보다 눌림.",
    "VTRS": "중·08-06 — 제네릭·EARN_D5. 방어적·대기.",
    "TVTX": "중상·08-04 — 바이오·업사이드·EARN_D5. 위성·변동 허용 시.",
    "PEBO": "중 — 지방은행. RR 무난·방어적. 급등 추격 불필요.",
    "FA": "중·08-06·고점 — 업사이드 음수·EARN_D5 → 관망.",
    "LIND": "중·08-03·고점 — 크루즈/여행·EARN_D5. 고점권 관망.",
    "RAPP": "상·08-06위성 — 임상 바이너리·EARN_D5. 극소 위성만.",
    "KRYS": "중·08-03·고점 — 피부과 바이오·EARN_D5. 고가 관망.",
    "DRH": "중·실적직후·고점 — 호텔 리츠. RSI 과열·추격 비추.",
    "ATLC": "중상·08-06위성 — 특화금융·EARN_D5. 위성 한도.",
    "CLMT": "하·과열 — 특수제품+재생. PT 프리미엄·고점·08-07. 추격 금지.",
    "STLD": "중 — 철강. 경기민감·중간 RR.",
    "JAZZ": "중·A′후보 — 제약. A′ 게이트(MA20근처·RSI56·고점−4%). 위성·소액·추격 금지.",
    "INCY": "중·SOFT — A′ 근접(고점−10%). 업사이드 작으면 대기.",
    "CNXN": "중하 — IT 리셀. 업사이드 약·관망.",
    "GPRE": "중하·08-06 — 에탄올/에너지·EARN_D5. RR 하위.",
    "SCSC": "중 — IT 유통. 중간·눌림.",
    "CDNA": "중하·실적직후·과열 — RSI·급등 과열. 추격 금지.",
    "CBRL": "하·과열 — 레스토랑 프리미엄. 추격 금지.",
    "PTGX": "중하·08-06 — 바이오·EARN_D5. 임상 변동.",
    "PAGP": "중하 — MLP/에너지. RR 약·관망.",
    "CRSR": "하·과열·08-06 — 게이밍 HW·EARN_D5. 추격 금지.",
    "FTRE": "중·과열주의 — 진단 아웃소싱. 변동·과열 주의.",
    "LQDA": "하·과열 — 호흡기 바이오. 고점 추격 금지.",
    "BRKR": "중하·08-04 — 분석기기·EARN_D5. 대기.",
    "KNSA": "중하 — 바이오. 서프/업사이드 약.",
    "DNTH": "중·08-06·임상변동 — EARN_D5·임상 이벤트. 위성·소액만.",
    "SEPN": "중·SOFT·서프약 — A′ 근접·서프라이즈 약. 신중.",
    "SENEA": "중하·08-06·데이터약 — EPS 이력 빈약·EARN_D5. 관망.",
    "CGNX": "중상·08-05 — 머신비전·업사이드·EARN_D5. 위성·실적창 주의.",
    "IESC": "중·고점주의 — 전기설비. 급등·고점권이면 추격 비추.",
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


def build_chase_detail(label: str, r: dict, share_note: str = "") -> str:
    """Display line (≥1 sentence). Keep short `label` for TA rules."""
    t = r["t"]
    if t in CHASE_DETAIL:
        base = CHASE_DETAIL[t]
        return annotate_text(base, share_note) if share_note else base
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
    detail = ""
    for k, v in bits.items():
        if label.startswith(k) or k in label[:4]:
            detail = f"{label} — {v}"
            break
    if not detail:
        if "과열" in label:
            detail = f"{label} — 고점·프리미엄 구간. 점수와 별개로 추격 비추천."
        else:
            detail = f"{label} — 업사이드 {ups} · 고점근접 {near} · EPS {beat} · 실적 {earn}."
    return annotate_text(detail, share_note) if share_note else detail


def merge(r: dict, qual: dict) -> dict:
    t = r["t"]
    q = dict(qual.get(t, {}))
    q.update(NEW_Q.get(t, {}))
    # 경쟁점유 꾸준 상승 → 전략 코멘트·가산 메타
    sg = assess_share_gain(t)
    if sg.strat_note:
        q = enrich_qual_fields(q, sg)
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
    q["chase_detail"] = build_chase_detail(q["chase"], r, share_note=sg.chase_note)
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
    q["share_delta_pp"] = r.get("share_delta_pp", sg.delta_pp)
    q["share_bonus"] = r.get("share_bonus", sg.bonus)
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
    p = Path("/workspace/reports/buy_scenarios_20260812.json")
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
    head = (
        "<div class='portfolio-box' style='border-color:#0f766e;background:#f0fdfa'>"
        "<b>매수 신호 구조 (2026-08 개편)</b> — "
        "<b>① 본선(Chase 좋은 종목)</b> ∩ <b>② 타이밍 GO</b> → 실행. "
        "아래 A/B/SOFT는 <u>타이밍만</u> (종목 선발이 아님). "
        f"GO_A(구 A′) {len(a)} · GO_B(구 B·프리마켓 기본 WAIT) {len(b)} · WAIT/SOFT {len(soft)}. "
        "실행창 KR 17:30~20:55 지정가.</div>"
    )
    rows = []
    for s in a + b + soft:
        timing = {"A": "GO_A", "B": "WAIT(B비실행)", "SOFT": "WAIT"}.get(
            str(s.get("scenario") or "").upper(), "WAIT"
        )
        note = s.get("caution") or (
            "MA20근처" if s.get("near_ma20") else ("스윙L" if s.get("near_l") else "")
        )
        if s.get("above200") and s.get("align"):
            note = (note + " · " if note else "") + "정배열"
        rows.append(
            "<tr>"
            f"<td><b>{esc(timing)}</b></td>"
            f"<td class='small'>{esc(s.get('scenario'))}</td>"
            f"<td><b>{esc(s.get('t'))}</b></td>"
            f"<td>{fmt_usd_price(s.get('last') or s.get('px'))}</td>"
            f"<td>{s.get('rsi', 0):.0f}</td>"
            f"<td>{s.get('pct_hi', 0)*100:+.1f}%</td>"
            f"<td>{'Y' if s.get('near_l') or s.get('near_ma20') else '—'}</td>"
            f"<td>{'Y' if s.get('breakout') else '—'}</td>"
            f"<td>D{s.get('edays')}</td>"
            f"<td class='small'>{esc(s.get('earn_source') or '—')}</td>"
            f"<td class='small'>{esc(note or '—')}</td>"
            "</tr>"
        )
    table = ""
    if rows:
        table = (
            "<table><tr><th>타이밍</th><th>구표기</th><th>티커</th><th>가격</th><th>RSI</th>"
            "<th>고점대비</th><th>지지</th><th>돌파</th><th>실적</th><th>출처</th><th>메모</th></tr>"
            + "".join(rows) + "</table>"
        )
    gloss = (
        "<p class='small'>"
        "<b>좋은 종목</b>=Chase 본선(상/중상…) · "
        "<b>좋은 타이밍</b>=GO_A 눌림(구 A′: MA200위+정배열+MA20/스윙L+RSI42–62+고점−1%~−8%+volOK). "
        "GO_B 돌파는 군인 프리마켓 OS에서 기본 WAIT. "
        "확정 실적 D−5만 하드블록(earn_confirmed/portfolio · 추정일은 주의). "
        "WAIT 종목은 후보에서 지우지 않음."
        "</p>"
    )
    return f"<h2>0. 매수 신호 — 본선 ∩ 타이밍 (적극 고지)</h2>{head}{table}{gloss}"




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
      <p class="sub">Chase 본선 · 타이밍 GO · 확정 EARN_D5 · 60종 · 군인 프리마켓 실행</p>
      <p class="meta">기준일 {DATE_TAG} · 라이브 가격/PT/실적일 · earn_confirmed SSOT · 종료 후 기술적분석 자동</p>
      <div class="portfolio-box" style="text-align:left;max-width:560px;margin:24px auto;">
        <b>매수 신호 요약 (본선 ∩ 타이밍)</b><br/>
        GO_A(A) <b>{n_a}</b> · GO_B(B·기본 WAIT) <b>{n_b}</b> · WAIT/SOFT {n_soft}<br/>
        {"→ 타이밍 히트는 0장 · 실행은 본선∩GO만 · 저녁창 지정가" if (n_a or n_b) else "→ <b>오늘은 GO_A 없음 · 본선 워치·현금 유지</b>"}
      </div>
      <div class="portfolio-box" style="text-align:left;max-width:560px;margin:16px auto;">
        <b>포트 실행 메모 (8/12 스냅)</b><br/>
        보유: TXG4 · CMPR2 · ECPG2 · AMRX10 · FTNT1 · SCSC3 · 주식~$1,097 · 현금합≈$548<br/>
        NESR 08-11 전량매도(익절) · LASR/RELY 기청산 · 등급한도 A≤18% B≤10% C≤6% · 전원 NO_ADD<br/>
        TXG 천장OVER(~21%) · SCSC 확정 EARN~08-20(D5) · AMRX −8.7% stop접근<br/>
        ANAB Yahoo 8/12=추정(확정 SSOT 미수록·하드블록 아님) · 실행창 17:30~20:55 지정가 · PDF=GitHub Release만
      </div>
    </section>
    {buy_scenario_section(scenarios)}
    <h2>Surprise / Chase 요약</h2>
    <p class="small">정렬: Chase RR. 가격·PT는 {DATE_TAG} 라이브. 60종 · 신규: BLZE·FSLY·ICUI·NVCR·TILE·DIOD·DXCM·TSEM·NTRA·LITE·ATEX·ANAB·APA·HALO·BCRX 등.<br/>
    가산: 경쟁점유 Δ≥+0.3pp → +0.35 (마진유지 시 +0.15 추가 · 마진악화 시 가산취소). 해당 종목 strat/Chase에 코멘트.</p>
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
      <p class="small">다음 단계: 기술적분석() ← chase_rr_20260812.json</p>
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
    # Mobile download: GitHub Release (artifacts/ local paths do NOT work for the user)
    try:
        from sepa.artifacts import print_release_result, publish_deep_pdf_release

        notes = (
            f"## NASDAQ 심층분석 ({DATE_TAG}) · {len(order)}종 · earn SSOT retest\n\n"
            f"Chase 본선 ∩ 타이밍 GO · earn_confirmed.yaml\n\n"
            f"- **GO_A(A):** {n_a} · **GO_B(B):** {n_b} · **WAIT(SOFT):** {n_soft}\n"
            f"- Top Chase: {', '.join(order[:10])}\n"
            f"- ANAB 8/12=estimate (not confirmed hard-block)\n"
        )
        rel = publish_deep_pdf_release(PDF_WORKSPACE, as_of=DATE_TAG, notes=notes)
        print_release_result(rel, label="심층분석 PDF")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub Release publish skipped: {exc}")
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
