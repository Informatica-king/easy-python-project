#!/usr/bin/env python3
"""NASDAQ 심층분석 PDF/HTML 생성 — 2026-07-21."""
from __future__ import annotations

import html
import json
import shutil
from copy import deepcopy
from datetime import date
from pathlib import Path

from weasyprint import HTML

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

REPORT_DATE = date(2026, 7, 21)
DATE_STR = REPORT_DATE.isoformat()
DATE_TAG = REPORT_DATE.strftime("%Y-%m-%d")

RANK_PATH = Path("/tmp/rank_20260721.json")
DEEP_PATH = Path("/tmp/deep_20260721.json")
PREV_PATH = Path("/tmp/prev_T.json")

HTML_OUT = Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-21.html")
PDF_WORKSPACE = Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-21.pdf")
PDF_ARTIFACT = Path("/opt/cursor/artifacts/NASDAQ_Deep_Analysis_2026-07-21.pdf")

CHASE_ORDER = [
    "NEO", "ECPG", "SLS", "ALKS", "TVTX", "RAPP", "NESR", "TXG", "LIND", "ACHC",
    "ASTH", "AMRX", "VCYT", "KRYS", "FROG", "JBHT", "XMTR", "SEZL", "BTSG", "FTRE",
    "PGNY", "JAZZ", "CMPR", "DNTH", "SEPN", "NWPX", "BAND", "DAVE", "CLMT", "LFST",
    "KYMR", "LQDA", "PTGX", "KNSA", "FA", "CDNA", "WERN", "FTNT",
]

CHASE_LABEL_OVERRIDE = {
    "NEO": "최상",
    "ECPG": "최상·코어",
    "SLS": "상·위성",
    "ALKS": "상·07-28",
    "NESR": "상·분할보유",
    "ASTH": "상·코어보유",
    "ACHC": "중·07-28대기",
    "WERN": "중·07-28",
    "FTRE": "중·07-29",
    "CMPR": "중·07-29",
    "BAND": "중하·07-29과열",
    "NWPX": "중하·과열",
    "FTNT": "하·과열",
    "AMRX": "중상·07-30반만",
    "CDNA": "하·07-30과열",
    "VCYT": "중하·07-30",
    "BTSG": "매도·07-31추격금지",
    "KNSA": "중상·07-28반만",
    "FA": "중하·과열",
    "DAVE": "최하·과열",
    "CLMT": "하·고점",
    "XMTR": "중·고점눌림",
}

NEW_QUALITATIVE = {
    "PGNY": {
        "name": "Progyny",
        "sector": "헬스케어·불임복지",
        "feat": "고용주단위·네트워크병원",
        "mcap": "~$2.5B",
        "item": "불임·가족계획 복지. 한줄: 기업이 직원에게 제공하는 IVF 등 생식의료 혜택 관리",
        "fin": "Q1 매출$322M(+1%YoY) EPS$0.50 Beat",
        "cons": "Strong Buy PT$30.5",
        "sur": "EPS4/4 Rev4/4 연속Beat",
        "strat": "성장둔화·PT근접→관망·08-06콜",
        "news": "Progyny IR; ~08-06실적",
        "bull": "$34–38",
        "base": "$29–33",
        "bear": "$22–26",
        "brk": "고용주예산삭감·이용률둔화",
        "eps": "4/4 Beat",
        "entry": "$27–30눌림",
        "drop": "가이드하향",
        "chase": "중·눌림",
        "abc": "$31/$34/$37",
        "rev_model": "고용주 계약 기반 PMPM 수수료 + 네트워크 클리닉 이용 연동.",
        "tam": "미국 생식의료 복지 시장 확대(자기부담 고비용).",
        "weight_cap": "신규 2% 상한",
    },
    "WERN": {
        "name": "Werner Enterprises",
        "sector": "산업·트럭운송",
        "feat": "운임사이클·연료·기사부족",
        "mcap": "~$2.8B",
        "item": "트럭·물류. 한줄: 미국 장거리 트럭 운송·물류",
        "fin": "Q1 EPS$0.02(턴어라운드) Rev+14%",
        "cons": "Hold PT$42.5",
        "sur": "EPS2/4 Rev3/4 변동성",
        "strat": "07-28실적 이벤트·고점근접→반만",
        "news": "07-28실적; 운임 사이클 바닥 관측 논의",
        "bull": "$48–55",
        "base": "$42–47",
        "bear": "$32–38",
        "brk": "운임재하락·비용재상승",
        "eps": "2/4",
        "entry": "$40–43실적후",
        "drop": "가이드미스",
        "chase": "중·07-28",
        "abc": "$44/$48/$52",
        "rev_model": "계약·스팟 트럭마일 + 물류 부가서비스.",
        "tam": "미국 트럭화물 시장(경기·재고사이클 민감).",
        "weight_cap": "이벤트성 1–2%",
    },
}

SLOT_EXTRA_TICKERS = {
    "NEO", "ECPG", "SLS", "ALKS", "NESR", "RAPP", "SEPN", "DNTH", "PGNY", "WERN",
}


def fmt_usd(v: float | None, *, signed: bool = False) -> str:
    if v is None:
        return "—"
    sign = ""
    if signed and v > 0:
        sign = "+"
    elif signed and v < 0:
        sign = ""
    av = abs(v)
    if av >= 1000:
        body = f"{av:,.0f}"
    elif av >= 100:
        body = f"{av:.0f}"
    else:
        body = f"{av:.2f}"
    return f"{sign}${body}" if not (signed and v >= 0) else f"+${body}" if signed else f"${body}"


def fmt_usd_price(v: float | None) -> str:
    if v is None:
        return "—"
    if v >= 100:
        return f"${v:,.2f}"
    return f"${v:.2f}"


def fmt_mcap(m: float | None) -> str:
    if m is None:
        return "—"
    if m >= 1e12:
        return f"${m / 1e12:.2f}T"
    if m >= 1e9:
        return f"${m / 1e9:.2f}B"
    if m >= 1e6:
        return f"${m / 1e6:.0f}M"
    return fmt_usd(m)


def fmt_pct(v: float | None, digits: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v * 100:+.{digits}f}%"


def fmt_ratio(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.0%}"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def build_rank_map(rank_data: dict) -> dict[str, dict]:
    return {r["t"]: r for r in rank_data["rows"]}


def refresh_cons(pt_a: float, upside: float, rec: str | None) -> str:
    rec_k = {"buy": "Buy", "strong_buy": "Strong Buy", "hold": "Hold", "none": "—"}.get(
        rec or "", rec or "—"
    )
    return f"{rec_k} PT평균{fmt_usd_price(pt_a)} ({fmt_pct(upside)} 업사이드)"


def merge_ticker(t: str, rank: dict, deep: dict, prev: dict) -> dict:
    r = rank[t]
    d = deep.get(t, {})
    if t in prev:
        q = deepcopy(prev[t])
    elif t in NEW_QUALITATIVE:
        q = deepcopy(NEW_QUALITATIVE[t])
    else:
        q = {
            "name": r.get("name", t),
            "sector": r.get("sector", ""),
            "feat": r.get("industry", ""),
            "mcap": fmt_mcap(r.get("mcap")),
            "item": r.get("name", t),
            "fin": "—",
            "cons": refresh_cons(r["ptA"], r["upside"], r.get("rec")),
            "sur": f"EPS{r.get('epsBeat', '—')}/{r.get('epsN', '—')}",
            "strat": "—",
            "news": f"실적 {r.get('earnDate', '—')}",
            "bull": "—",
            "base": "—",
            "bear": "—",
            "brk": "—",
            "eps": f"{r.get('epsBeat', '—')}/{r.get('epsN', '—')}",
            "entry": "—",
            "drop": "—",
            "chase": "—",
            "abc": "—",
        }

    q["px"] = r["px"]
    q["h"] = r.get("h")
    q["l"] = r.get("l")
    q["ptL"] = r.get("ptL")
    q["ptA"] = r.get("ptA")
    q["ptH"] = r.get("ptH")
    q["upside"] = r.get("upside")
    q["prem"] = r.get("prem")
    q["near_high"] = r.get("near_high")
    q["earnDate"] = r.get("earnDate")
    q["score"] = r.get("score")
    q["rank"] = r.get("rank")
    q["rec"] = r.get("rec")
    q["avgSurp"] = r.get("avgSurp")
    q["epsBeat"] = r.get("epsBeat")
    q["epsN"] = r.get("epsN")
    q["revG"] = r.get("revG")
    q["name_en"] = r.get("name", q.get("name", t))

    q["cons"] = refresh_cons(r["ptA"], r["upside"], r.get("rec"))
    prem = r.get("prem") or 0
    if prem > 0.08:
        q["cons"] += f" · 현재가 PT대비 {fmt_pct(prem)} 프리미엄"
    elif prem < -0.05:
        q["cons"] += f" · PT대비 {fmt_pct(abs(prem))} 할인"

    # live financial snippet from deep
    if d:
        parts = []
        if d.get("revG") is not None:
            parts.append(f"Rev YoY {fmt_pct(d['revG'])}")
        if d.get("lastEpsA") is not None:
            parts.append(f"최근EPS 실적{d['lastEpsA']}")
        if d.get("gm") is not None:
            parts.append(f"GM {fmt_ratio(d['gm'])}")
        if parts and q.get("fin", "—") == "—":
            q["fin"] = " · ".join(parts)
        elif parts:
            q["fin_live"] = " · ".join(parts)

    if t in CHASE_LABEL_OVERRIDE:
        q["chase"] = CHASE_LABEL_OVERRIDE[t]
    elif "chase" not in q or not q["chase"]:
        q["chase"] = "중"

    earn = r.get("earnDate")
    if earn and earn >= "2026-07-21" and earn <= "2026-08-15":
        if "news" in q and earn not in q["news"]:
            q["news"] = f"{earn} 실적 예정 · {q.get('news', '')}"

    return q


def esc(s) -> str:
    return html.escape(str(s) if s is not None else "—")


def thesis_line(t: str, q: dict) -> str:
    defaults = {
        "NEO": "암진단 볼륨 회복 + 연속 EPS 서프라이즈로 07-28 촉매.",
        "ECPG": "NPL 회수 사이클 + Beat 머신 — 코어 보유, 고점 추격 금지.",
        "SLS": "항암 바이너리; PT 업사이드 크나 임상 리스크.",
        "ALKS": "매출 Beat vs EPS 변동 — 07-28 실적 전 이벤트 관리.",
        "PGNY": "생식의료 복지 수요는 구조적이나 성장 둔화·밸류에이션 균형.",
        "WERN": "트럭 사이클 턴어라운드 베팅; 07-28 실적이 분기점.",
    }
    if t in defaults:
        return defaults[t]
    # one-liner from strat + cons
    strat = q.get("strat", "")
    if strat and strat != "—":
        return strat.split("→")[0].strip() if "→" in strat else strat[:120]
    return f"{q.get('sector', '')} — {q.get('feat', '')} 관점 모멘텀 점검."


def build_css() -> str:
    return f"""
    @font-face {{
      font-family: 'NanumGothic';
      src: url('file://{FONT_REG}');
      font-weight: normal;
    }}
    @font-face {{
      font-family: 'NanumGothic';
      src: url('file://{FONT_BOLD}');
      font-weight: bold;
    }}
    @page {{
      size: A4;
      margin: 14mm 12mm 16mm 12mm;
      @bottom-center {{
        content: "NASDAQ 심층분석 {DATE_TAG} — " counter(page);
        font-size: 8pt;
        color: #666;
        font-family: 'NanumGothic', sans-serif;
      }}
    }}
    body {{
      font-family: 'NanumGothic', sans-serif;
      font-size: 9.5pt;
      line-height: 1.45;
      color: #1a1a1a;
    }}
    h1 {{ font-size: 22pt; margin: 0 0 8px; }}
    h2 {{ font-size: 13pt; margin: 14px 0 6px; border-bottom: 2px solid #2c5282; padding-bottom: 3px; }}
    h3 {{ font-size: 11pt; margin: 10px 0 4px; color: #2c5282; }}
    .cover {{
      page-break-after: always;
      min-height: 250mm;
      display: flex;
      flex-direction: column;
      justify-content: center;
      text-align: center;
    }}
    .cover .sub {{ font-size: 12pt; color: #444; margin-top: 12px; }}
    .meta {{ font-size: 10pt; color: #555; margin-top: 24px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 8pt;
      margin: 8px 0;
    }}
    th, td {{
      border: 1px solid #ccc;
      padding: 3px 5px;
      vertical-align: top;
    }}
    th {{ background: #edf2f7; font-weight: bold; }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    .summary-block {{ page-break-after: always; }}
    .ticker-section {{ page-break-before: always; }}
    .ticker-head {{
      background: #2c5282;
      color: #fff;
      padding: 8px 10px;
      margin: 0 0 8px;
      font-size: 12pt;
      font-weight: bold;
    }}
    .price-row {{ font-size: 10pt; margin-bottom: 8px; }}
    .conclusion td:first-child {{ font-weight: bold; width: 22%; background: #f7fafc; }}
    .small {{ font-size: 8pt; color: #555; }}
    .portfolio-box {{
      background: #fffaf0;
      border: 1px solid #d69e2e;
      padding: 10px;
      margin: 10px 0;
    }}
    .tag {{ display: inline-block; background: #bee3f8; padding: 1px 6px; border-radius: 3px; font-size: 8pt; }}
    """


def summary_table_rows(tickers: dict[str, dict]) -> str:
    rows = []
    for i, t in enumerate(CHASE_ORDER, 1):
        q = tickers[t]
        rows.append(
            f"<tr><td>{i}</td><td><b>{esc(t)}</b></td>"
            f"<td>{fmt_usd_price(q['px'])}</td>"
            f"<td>{fmt_usd_price(q['ptA'])}</td>"
            f"<td>{fmt_pct(q['upside'])}</td>"
            f"<td>{fmt_pct(q.get('prem'))}</td>"
            f"<td>{q.get('epsBeat', '—')}/{q.get('epsN', '—')}</td>"
            f"<td>{fmt_pct(q.get('avgSurp'), 2) if q.get('avgSurp') is not None else '—'}</td>"
            f"<td>{esc(q.get('earnDate', '—'))}</td>"
            f"<td>{esc(q.get('chase', ''))}</td></tr>"
        )
    return "\n".join(rows)


def ticker_section(t: str, q: dict) -> str:
    extras = ""
    if t in SLOT_EXTRA_TICKERS:
        rm = q.get("rev_model") or q.get("rev_model", "")
        if t in NEW_QUALITATIVE:
            rm = NEW_QUALITATIVE[t].get("rev_model", "")
        if rm:
            extras += f"<p><b>수익구조</b> {esc(rm)}</p>"
        tam = q.get("tam") or NEW_QUALITATIVE.get(t, {}).get("tam", "")
        if tam:
            extras += f"<p><b>TAM 힌트</b> {esc(tam)}</p>"
        wc = q.get("weight_cap") or NEW_QUALITATIVE.get(t, {}).get("weight_cap", "")
        if wc:
            extras += f"<p><b>비중 상한</b> {esc(wc)}</p>"
        if t == "NESR":
            extras += "<p><b>비중 상한</b> 분할매수만; 버퍼 $280–320, $25–27 구간은 수요일 이후</p>"
        if t == "ECPG":
            extras += "<p><b>비중 상한</b> 코어 보유 — 고점 추가금지</p>"

    fin_block = esc(q.get("fin", "—"))
    if q.get("fin_live"):
        fin_block += f"<br/><span class='small'>라이브: {esc(q['fin_live'])}</span>"

    return f"""
    <section class="ticker-section" id="{esc(t)}">
      <div class="ticker-head">#{q.get('rank', '—')} {esc(t)} — {esc(q.get('name', t))}</div>
      <div class="price-row">
        <span class="tag">현재 {fmt_usd_price(q['px'])}</span>
        <span class="tag">PT {fmt_usd_price(q['ptL'])}–{fmt_usd_price(q['ptH'])} (평균 {fmt_usd_price(q['ptA'])})</span>
        <span class="tag">업사이드 {fmt_pct(q['upside'])}</span>
        <span class="tag">52주 고저 {fmt_usd_price(q.get('l'))}–{fmt_usd_price(q.get('h'))}</span>
        <span class="tag">고점근접 {fmt_ratio(q.get('near_high'))}</span>
      </div>

      <h3>1. 한줄 Thesis</h3>
      <p>{esc(thesis_line(t, q))}</p>

      <h3>2. 섹터 · 특성 · 시총</h3>
      <p><b>섹터</b> {esc(q.get('sector', '—'))} · <b>특성</b> {esc(q.get('feat', '—'))} · <b>시총</b> {esc(q.get('mcap', fmt_mcap(q.get('mcap_num'))))}</p>

      <h3>3. 핵심 제품</h3>
      <p>{esc(q.get('item', '—'))}</p>

      <h3>4. 재무 · 컨센서스 · 서프라이즈 · 전략 비교</h3>
      <p>{fin_block}</p>
      <p><b>컨센서스</b> {esc(q.get('cons', '—'))}</p>
      <p><b>서프라이즈</b> {esc(q.get('sur', '—'))} (평균 EPS 서프라이즈 {fmt_pct(q.get('avgSurp'), 2) if q.get('avgSurp') is not None else '—'})</p>
      <p><b>전략</b> {esc(q.get('strat', '—'))}</p>

      <h3>5. 섹터 뉴스 · 출처</h3>
      <p>{esc(q.get('news', '—'))} · 실적일 <b>{esc(q.get('earnDate', '—'))}</b> (라이브 데이터)</p>

      <h3>6. Bull / Base / Bear · Breakers</h3>
      <p>Bull {esc(q.get('bull', '—'))} · Base {esc(q.get('base', '—'))} · Bear {esc(q.get('bear', '—'))}</p>
      <p><b>Breaker</b> {esc(q.get('brk', '—'))} · ABC {esc(q.get('abc', '—'))}</p>

      <h3>7. 결론 표</h3>
      <table class="conclusion">
        <tr><td>섹터</td><td>{esc(q.get('sector', '—'))}</td></tr>
        <tr><td>핵심</td><td>{esc(q.get('item', '—')[:80])}</td></tr>
        <tr><td>EPS</td><td>{esc(q.get('eps', '—'))}</td></tr>
        <tr><td>신규진입</td><td>{esc(q.get('entry', '—'))}</td></tr>
        <tr><td>탈락</td><td>{esc(q.get('drop', '—'))}</td></tr>
        <tr><td>Chase</td><td><b>{esc(q.get('chase', '—'))}</b></td></tr>
      </table>
      {extras}
    </section>
    """


def build_html(tickers: dict[str, dict]) -> str:
    portfolio = """
    <div class="portfolio-box">
      <h2>포트폴리오 실행 요약 (2026-07-21)</h2>
      <ul>
        <li><b>보유</b>: ECPG 2주(코어·고점 무추가), ASTH 3주(코어), NESR 2주(분할보유·수요일 이후 $25–27만), INDV 1주(오늘 리스트 외)</li>
        <li><b>청산</b>: BTSG +4.3% — 07-31 실적 전 고점 재매수 금지</li>
        <li><b>유동성</b>: 현금 ~$134 + 수요일 ~$811 유입 예정 → NESR 버퍼 $280–320 확보</li>
        <li><b>전략</b>: 단중기 모멘텀 + 실적 서프라이즈 필터; PT 프리미엄 추격 회피 (FTNT, FA, NWPX, DAVE, CLMT, CDNA, XMTR 고점)</li>
        <li><b>이벤트 주간</b>: 07-28 ACHC/ALKS/NEO/WERN/KNSA · 07-29 FTRE/CMPR/BAND/NWPX/FTNT · 07-30 AMRX/CDNA/VCYT · 07-31 BTSG(관망)</li>
      </ul>
    </div>
    """

    chase_final = summary_table_rows(tickers)

    body_sections = "".join(ticker_section(t, tickers[t]) for t in CHASE_ORDER)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8"/>
  <title>NASDAQ 심층분석 {DATE_TAG}</title>
  <style>{build_css()}</style>
</head>
<body>
  <div class="cover">
    <h1>NASDAQ 심층분석</h1>
    <p class="sub">Chase Risk-Reward · 실적 서프라이즈 · 38종목</p>
    <p class="meta">기준일 {DATE_TAG}<br/>데이터: rank/deep 라이브 JSON · 질적 prev_T 갱신</p>
    <p class="meta">전략: 단중기 모멘텀 · PT 프리미엄 추격 회피</p>
  </div>

  <div class="summary-block">
    <h2>Surprise / Chase 요약</h2>
    <p class="small">정렬: Chase RR (고정). 가격·PT·업사이드는 {DATE_TAG} 라이브.</p>
    <table>
      <thead>
        <tr>
          <th>#</th><th>티커</th><th>가격</th><th>PT</th><th>업사이드</th><th>PT프리미엄</th>
          <th>EPS B/N</th><th>평균Surp</th><th>실적일</th><th>Chase</th>
        </tr>
      </thead>
      <tbody>
        {summary_table_rows(tickers)}
      </tbody>
    </table>
  </div>

  {body_sections}

  <section class="ticker-section">
    <h2>최종 Chase RR 순위 + 실행</h2>
    <table>
      <thead>
        <tr><th>#</th><th>티커</th><th>가격</th><th>PT</th><th>업사이드</th><th>Chase</th></tr>
      </thead>
      <tbody>
        {''.join(
            f"<tr><td>{i}</td><td><b>{esc(t)}</b></td><td>{fmt_usd_price(tickers[t]['px'])}</td>"
            f"<td>{fmt_usd_price(tickers[t]['ptA'])}</td><td>{fmt_pct(tickers[t]['upside'])}</td>"
            f"<td>{esc(tickers[t]['chase'])}</td></tr>"
            for i, t in enumerate(CHASE_ORDER, 1)
        )}
      </tbody>
    </table>
    {portfolio}
  </section>
</body>
</html>
"""


def main() -> None:
    rank_data = load_json(RANK_PATH)
    deep_data = load_json(DEEP_PATH)
    prev_data = load_json(PREV_PATH)
    rank_map = build_rank_map(rank_data)

    missing = [t for t in CHASE_ORDER if t not in rank_map]
    if missing:
        raise SystemExit(f"Missing tickers in rank JSON: {missing}")

    tickers = {t: merge_ticker(t, rank_map, deep_data, prev_data) for t in CHASE_ORDER}

    html_doc = build_html(tickers)
    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(html_doc, encoding="utf-8")

    PDF_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    html_obj = HTML(string=html_doc, base_url=str(HTML_OUT.parent))
    html_obj.write_pdf(PDF_WORKSPACE)
    shutil.copy2(PDF_WORKSPACE, PDF_ARTIFACT)

    size = PDF_WORKSPACE.stat().st_size
    print(f"HTML: {HTML_OUT}")
    print(f"PDF:  {PDF_WORKSPACE} ({size:,} bytes)")
    print(f"PDF:  {PDF_ARTIFACT}")
    print("Top-10 Chase:", ", ".join(CHASE_ORDER[:10]))


if __name__ == "__main__":
    main()
