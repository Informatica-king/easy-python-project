#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NASDAQ 심층분석 PDF — 2026-07-26 (35종목) + Chase 스냅샷 + 기술적분석 훅."""

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

REPORT_DATE = date(2026, 7, 26)
DATE_STR = REPORT_DATE.isoformat()
DATE_TAG = DATE_STR

RANK_PATH = Path("/tmp/rank_20260726.json")
QUAL_PATH = Path("/tmp/qual_20260726.json")

HTML_OUT = Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-26.html")
PDF_WORKSPACE = Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-26.pdf")
PDF_ARTIFACT = Path("/opt/cursor/artifacts/NASDAQ_Deep_Analysis_2026-07-26.pdf")
PDF_ASSETS = Path("/workspace/assets/NASDAQ_Deep_Analysis_2026-07-26.pdf")
CHASE_OUT = Path("/workspace/reports/chase_rr_20260726.json")

# Manual qualitative for tickers missing from prior reports
NEW_Q = {
    "CBRL": {
        "name": "Cracker Barrel",
        "sector": "소비·레스토랑",
        "feat": "캐주얼 다이닝·로드사이드",
        "item": "레스토랑 체인. 한줄: 크래커배럴 매장·리테일",
        "fin": "EPS 혼조 · PT 프리미엄(고점 근접)",
        "strat": "고점·프리미엄 · 관망",
        "news": "동일점 매출·마진",
        "bull": "$60–70",
        "base": "$48–58",
        "bear": "$35–45",
        "brk": "트래픽·마진 악화",
        "eps": "2/4",
        "entry": "관망",
        "drop": "가이던스 컷",
        "chase": "하·과열",
        "abc": "$50/$55/$65",
    },
    "CRWD": {
        "name": "CrowdStrike",
        "sector": "IT·사이버보안",
        "feat": "클라우드 EDR·보안 플랫폼",
        "item": "엔드포인트 보안. 한줄: Falcon 플랫폼 사이버보안 SaaS",
        "fin": "EPS 4/4 Beat · 메가캡 성장",
        "strat": "품질高·업사이드 얇음 · 눌림",
        "news": "보안 예산·ARR",
        "bull": "$220–260",
        "base": "$170–200",
        "bear": "$130–160",
        "brk": "성장 둔화·대형 장애",
        "eps": "4/4 Beat",
        "entry": "눌림",
        "drop": "가이던스 컷",
        "chase": "중·눌림",
        "abc": "$190/$210/$250",
    },
    "CRNX": {
        "name": "Crinetics Pharmaceuticals",
        "sector": "바이오·내분비",
        "feat": "경구 내분비 신약",
        "item": "내분비 바이오. 한줄: 경구 비펩타이드 내분비 치료제",
        "fin": "임상단계 · 서프라이즈 약",
        "strat": "임상·이벤트 변동 · 위성만",
        "news": "파이프라인·승인 일정",
        "bull": "$100–130",
        "base": "$70–95",
        "bear": "$40–60",
        "brk": "임상/규제 실패",
        "eps": "1/4",
        "entry": "관망/극소",
        "drop": "임상 실패",
        "chase": "중하·임상",
        "abc": "$80/$90/$120",
    },
}

# Portfolio-aware Chase label overrides — 2026-07-26 (주말·NEO D-2)
LABEL_OVERRIDE = {
    "LASR": "상·08-06",
    "NEO": "최상·07-28이벤트·보유",
    "ECPG": "최상·코어보유·추가금지",
    "ALKS": "중·07-28워치",
    "INDV": "상·시드·추가금지",
    "ACHC": "중·07-28고점대기",
    "TXG": "하·과열",
    "VCYT": "중하·07-30과열",
    "NESR": "상·분할·밴드대기",
    "AMRX": "중·07-30보유·추가금지",
    "DDOG": "중·눌림",
    "NWPX": "하·과열",
    "PGNY": "중·눌림",
    "EXTR": "중·고점",
    "LIND": "중·고점",
    "TVTX": "중상",
    "FTNT": "하·과열",
    "KRYS": "중·고점",
    "RAPP": "상·08-06",
    "ATLC": "중상·위성",
    "DAVE": "하·과열",
    "CLMT": "하·고점",
    "BTSG": "매도·07-31추격금지",
    "JAZZ": "중·고점",
    "CBRL": "하·과열",
    "FTRE": "중·07-29과열주의",
    "CDNA": "하·07-30과열",
    "ICHR": "중하·관망",
    "PTGX": "중하·과열",
    "BRKR": "중하·관망",
    "LQDA": "하·과열",
    "DNTH": "중·임상변동",
    "KYMR": "중하·서프약",
    "KNSA": "중하·07-28반만",
    "SEPN": "중·서프약",
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
        <tr><td>Chase</td><td><b>{esc(q.get('chase'))}</b></td></tr>
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
            f"<td>{esc(q.get('earnDate'))}</td><td>{esc(q.get('chase'))}</td></tr>"
        )

    body = "".join(ticker_section(tickers[t]) for t in order)
    final_rows = []
    for t in order:
        q = tickers[t]
        final_rows.append(
            f"<tr><td>{q['rank']}</td><td><b>{esc(t)}</b></td>"
            f"<td>{fmt_usd_price(q['px'])}</td><td>{fmt_usd_price(q['ptA'])}</td>"
            f"<td>{fmt_pct(q['upside'])}</td><td>{esc(q['chase'])}</td></tr>"
        )

    doc = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"/>
    <title>NASDAQ 심층분석 {DATE_TAG}</title><style>{build_css()}</style></head><body>
    <section class="cover">
      <h1>NASDAQ 심층분석</h1>
      <p class="sub">Chase Risk-Reward · 실적 서프라이즈 · 35종목</p>
      <p class="meta">기준일 {DATE_TAG} · 라이브 가격/PT/실적일 · 종료 후 기술적분석 자동</p>
      <div class="portfolio-box" style="text-align:left;max-width:520px;margin:24px auto;">
        <b>포트 실행 메모 (7/26 주말)</b><br/>
        보유: NEO · ECPG · AMRX · MU · NESR · INDV · CRDO(소액)<br/>
        청산: ASTH · 본 리스트에 MU/CRDO 미포함<br/>
        이벤트: NEO/ALKS/ACHC/KNSA 07-28 · NWPX/FTNT/FTRE 07-29 · AMRX/VCYT/CDNA 07-30<br/>
        NESR: $25–27 밴드만 · ECPG stop $80 · NEO stop $12 / tp1 $16<br/>
        과열·바이너리 추격 금지 · NEO 실적 전 전종목 NO_ADD
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
