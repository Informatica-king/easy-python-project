"""경제뉴스() PDF report builder — detailed overnight US session brief."""

from __future__ import annotations

import html
from pathlib import Path

from weasyprint import HTML

from sepa.econ_news_data import BarSnap, EconNewsBundle, Headline
from sepa.econ_sector_viz import board_to_data_uri

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"


def esc(s) -> str:
    return html.escape(str(s) if s is not None else "—")


def pct(v: float | None, digits: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v * 100:+.{digits}f}%"


def num(v: float | None, digits: int = 2) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.{digits}f}"


def vol_ratio(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.2f}x"


def _css() -> str:
    return f"""
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_REG}'); font-weight:normal; }}
    @font-face {{ font-family:'NanumGothic'; src:url('file://{FONT_BOLD}'); font-weight:bold; }}
    @page {{ size:A4; margin:12mm 11mm 14mm 11mm;
      @bottom-center {{ content:"경제뉴스 — " counter(page);
        font-size:8pt; color:#666; font-family:'NanumGothic',sans-serif; }} }}
    body {{ font-family:'NanumGothic',sans-serif; font-size:9.2pt; line-height:1.42; color:#1a1a1a; }}
    h1 {{ font-size:20pt; margin:0 0 6px; color:#1e3a5f; }}
    h2 {{ font-size:12.5pt; margin:12px 0 5px; border-bottom:2px solid #0f766e; padding-bottom:3px; color:#1e3a5f;
      page-break-after:avoid; }}
    h3 {{ font-size:10.5pt; margin:8px 0 4px; color:#0f766e; }}
    .cover {{ page-break-after:always; min-height:250mm; display:flex; flex-direction:column;
      justify-content:center; padding:20px;
      background:linear-gradient(160deg,#eef6f5 0%,#e8eef6 50%,#f7f3ea 100%); border-radius:8px; }}
    .mood {{ font-size:14pt; color:#0f766e; margin:10px 0; font-weight:700; }}
    .bullets {{ text-align:left; max-width:520px; margin:16px auto; background:#fff; padding:12px 16px;
      border-left:4px solid #1e3a5f; }}
    .bullets li {{ margin:6px 0; }}
    .meta {{ color:#555; font-size:9pt; margin-top:18px; }}
    table {{ width:100%; border-collapse:collapse; font-size:8pt; margin:6px 0 10px; }}
    th,td {{ border:1px solid #ccc; padding:3px 5px; vertical-align:top; }}
    th {{ background:#edf2f7; }}
    tr:nth-child(even) td {{ background:#fafafa; }}
    .pos {{ color:#166534; font-weight:700; }}
    .neg {{ color:#9f1239; font-weight:700; }}
    .box {{ background:#fffbeb; border:1px solid #d69e2e; padding:8px 10px; margin:8px 0; }}
    .easy {{ background:#f0fdfa; border-left:4px solid #0f766e; padding:7px 10px; margin:6px 0; font-size:8.5pt; }}
    .small {{ font-size:7.5pt; color:#555; }}
    .tag {{ display:inline-block; background:#dbeafe; padding:1px 6px; border-radius:3px; font-size:7.5pt; margin:1px; }}
    .section {{ page-break-inside:avoid; }}
    ul.tight li {{ margin:2px 0; }}
    .sector-board {{ page-break-inside:avoid; margin:8px 0 12px; }}
    .sector-board img {{ width:100%; height:auto; border:1px solid #e2e8f0; border-radius:4px; }}
    """


def _chg_cell(v: float | None) -> str:
    cls = "pos" if (v or 0) >= 0 else "neg"
    return f"<td class='{cls}'>{pct(v)}</td>"


def _bar_rows(rows: list[BarSnap]) -> str:
    out = []
    for r in rows:
        out.append(
            "<tr>"
            f"<td><b>{esc(r.ticker)}</b><br/><span class='small'>{esc(r.name)}</span></td>"
            f"<td>{num(r.close)}</td>"
            f"{_chg_cell(r.change_pct)}"
            f"<td>{num(r.low)}–{num(r.high)}</td>"
            f"<td>{num(r.volume, 0)}</td>"
            f"<td>{vol_ratio(r.vol_ratio)}</td>"
            "</tr>"
        )
    return "\n".join(out)


def _sector_news_link(bundle: EconNewsBundle, sector_name: str) -> str:
    # map ETF korean name loosely to news tags
    tag_map = {
        "기술": "기술",
        "금융": "금융",
        "에너지": "에너지",
        "헬스케어": "헬스케어",
        "임의소비": "소비",
        "필수소비": "소비",
    }
    # also semiconductor via SMH handled separately
    want = None
    for k, v in tag_map.items():
        if k in sector_name:
            want = v
            break
    if "반도체" in sector_name:
        want = "반도체"
    hits = []
    for h in bundle.headlines:
        if want and want in h.sector_tags:
            hits.append(h.title)
        elif want == "반도체" and any(x in h.title.lower() for x in ("chip", "semi", "memory", "micron", "nvidia")):
            hits.append(h.title)
    if not hits:
        # fallback: any headline
        return "관련 헤드라인 약함 — 가격 움직임 중심 해석"
    return hits[0][:90]


def _interpret_sector(r: BarSnap, news_line: str, hot: bool) -> str:
    direction = "유입" if r.change_pct >= 0 else "이탈"
    vol = ""
    if r.vol_ratio and r.vol_ratio >= 1.3:
        vol = " · 거래량 동반↑"
    elif r.vol_ratio and r.vol_ratio <= 0.7:
        vol = " · 거래량 한산"
    tone = "주목" if hot else "주의/회피"
    return f"{tone}: 자금 {direction}{vol}. 뉴스: {news_line}"


def render_html(bundle: EconNewsBundle) -> str:
    sess = bundle.session_date.isoformat()
    hot = bundle.sectors[:4]
    cold = list(reversed(bundle.sectors[-4:])) if len(bundle.sectors) >= 4 else list(reversed(bundle.sectors))

    sector_detail_rows = []
    for r in bundle.sectors:
        news_line = _sector_news_link(bundle, r.name)
        is_hot = r in hot[:3]
        sector_detail_rows.append(
            "<tr>"
            f"<td><b>{esc(r.name)}</b> ({esc(r.ticker)})</td>"
            f"{_chg_cell(r.change_pct)}"
            f"<td>{vol_ratio(r.vol_ratio)}</td>"
            f"<td class='small'>{esc(news_line)}</td>"
            f"<td class='small'>{esc(_interpret_sector(r, news_line, is_hot))}</td>"
            "</tr>"
        )

    # index deep dives
    idx_by = {i.ticker: i for i in bundle.indices}
    index_blocks = []
    for key, why_hint in (
        ("SPY", "미국 대형주 전반 · 매크로/실적 온도계"),
        ("QQQ", "성장·빅테크 · 금리·AI 테마 민감"),
        ("IWM", "소형주 · 위험선호/유동성 민감"),
        ("SMH", "반도체·AI 하드웨어 자금 흐름"),
        ("^VIX", "변동성 · 공포/안도 게이지 (상승=불안)"),
    ):
        r = idx_by.get(key)
        if not r:
            continue
        index_blocks.append(
            f"<h3>{esc(r.name)} ({esc(r.ticker)})</h3>"
            f"<p>종가 <b>{num(r.close)}</b> · 등락 <b>{pct(r.change_pct)}</b> · "
            f"장중 {num(r.low)}–{num(r.high)} · 거래량/평균 {vol_ratio(r.vol_ratio)}</p>"
            f"<p class='small'>{esc(why_hint)}</p>"
        )

    # reason synthesis from headlines + moves
    spy = idx_by.get("SPY")
    qqq = idx_by.get("QQQ")
    smh = idx_by.get("SMH")
    vix = idx_by.get("^VIX")
    reasons = []
    if smh and abs(smh.change_pct) >= 0.01:
        reasons.append(f"반도체(SMH) {pct(smh.change_pct)} — AI/메모리 테마가 지수 방향에 기여")
    if qqq and spy and abs(qqq.change_pct - spy.change_pct) >= 0.003:
        if qqq.change_pct > spy.change_pct:
            reasons.append("나스닥(성장주)이 S&P 대비 강세 — 빅테크·성장 선호")
        else:
            reasons.append("나스닥이 S&P 대비 약세 — 성장주 차익/금리 민감 가능")
    if vix:
        if vix.change_pct > 0.05:
            reasons.append(f"VIX {pct(vix.change_pct)} 상승 — 헤지·불안 수요 증가")
        elif vix.change_pct < -0.05:
            reasons.append(f"VIX {pct(vix.change_pct)} 하락 — 변동성 완화·위험선호 보강")
    # top headlines as drivers
    for h in bundle.headlines[:5]:
        if h.sector_tags:
            reasons.append(f"[{'/'.join(h.sector_tags)}] {h.title[:100]}")
    if not reasons:
        reasons.append("뚜렷한 단일 촉매보다 섹터 로테이션·개별 실적 혼재 가능성")

    # portfolio
    port_rows = []
    for p in bundle.portfolio:
        role_k = "보유" if p.role == "hold" else "워치"
        hl = "<br/>".join(esc(x[:80]) for x in p.headlines[:3]) or "—"
        impact = p.note
        if p.change_pct is not None:
            if abs(p.change_pct) >= 0.03:
                impact += " · 전일 변동 큼 → 갭/지정가 재확인"
            elif abs(p.change_pct) >= 0.015:
                impact += " · 중간 변동 → 테마 연동 점검"
            else:
                impact += " · 상대적으로 조용"
        port_rows.append(
            "<tr>"
            f"<td><b>{esc(p.ticker)}</b><br/><span class='tag'>{role_k}</span></td>"
            f"<td>{num(p.close)}</td>"
            f"{_chg_cell(p.change_pct)}"
            f"<td class='small'>{esc(impact)}</td>"
            f"<td class='small'>{hl}</td>"
            "</tr>"
        )

    # checklist — aligned to current portfolio_watch.yaml OS
    held = [p.ticker for p in bundle.portfolio if p.role == "hold"]
    n_held = len(held) or 7
    checklist = [
        f"저녁창(17:30~20:55) 전: 보유 {n_held}종 호가·갭 확인 · 시장가/돌파추격 금지",
        "매수 = 본선(Chase) ∩ 타이밍 GO · WAIT는 워치 유지 · 지정가·상한·갭VOID",
        "확정 EARN_D5만 신규/분할 하드블록 · 추정 실적일은 주의",
        "보유 전원 NO_ADD · 물타기 금지 · SCHD 재매수 비우선",
        "현금바닥 $150 유지 · 동일종목 중복주문 금지",
    ]

    headline_rows = []
    for h in bundle.headlines[:25]:
        tags = ",".join(h.sector_tags) if h.sector_tags else "—"
        headline_rows.append(
            "<tr>"
            f"<td>{esc(h.source)}</td>"
            f"<td>{esc(h.title)}</td>"
            f"<td class='small'>{esc(tags)}</td>"
            f"<td class='small'>{esc(h.published)}</td>"
            "</tr>"
        )

    bullets = "".join(f"<li>{esc(b)}</li>" for b in bundle.bullets)

    sector_board_html = ""
    if bundle.sector_board_png and Path(bundle.sector_board_png).exists():
        uri = board_to_data_uri(Path(bundle.sector_board_png))
        sector_board_html = f"""
<h2>1-A. 섹터 시총 비중 · 등락 히트맵</h2>
<div class="easy"><b>쉽게:</b> 왼쪽은 <b>큰 업종 순위</b>, 오른쪽은 <b>넓이=자금 규모(ETF AUM)</b>·
색=<b>전일 등락</b>(빨강↑ 파랑↓). S&amp;P GICS 11섹터 Select Sector ETF 기준.</div>
<div class="sector-board"><img src="{uri}" alt="sector board treemap"/></div>
<p class="small">비중 = 각 섹터 ETF totalAssets / 합계(시가총액 근사 프록시). 등락 = 세션 종가 vs 직전 종가.
진짜 S&amp;P 구성비와는 다를 수 있음 · 로테이션·온도 파악용.</p>
"""

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"/><title>경제뉴스 {sess}</title>
<style>{_css()}</style></head><body>
<section class="cover">
  <div style="text-align:center">
    <h1>경제뉴스</h1>
    <p style="font-size:13pt;color:#444">미국 정규장 하룻밤 브리핑 · {sess}</p>
    <p class="mood">{esc(bundle.mood)}</p>
    <div class="bullets"><ol>{bullets}</ol></div>
    <p class="meta">생성 {esc(bundle.generated_at)} · 보유+워치 영향 포함 · 뉴스 RSS 자동수집</p>
    <p class="small">폰 통제 전 저장용 · 투자 권유 아님 · 시세는 지연/조정주가 가능</p>
  </div>
</section>

<h2>1. 증시 자금 이동 요약</h2>
<div class="easy"><b>쉽게:</b> ‘어느 바구니로 돈이 몰렸고, 거래는 평소보다 활발했나’를 먼저 봅니다.</div>
<table>
  <tr><th>지표</th><th>종가</th><th>등락</th><th>장중</th><th>거래량</th><th>vs20일</th></tr>
  {_bar_rows(bundle.indices)}
</table>
<table>
  <tr><th>섹터ETF</th><th>종가</th><th>등락</th><th>장중</th><th>거래량</th><th>vs20일</th></tr>
  {_bar_rows(bundle.sectors)}
</table>
<p class="small">vs20일 = 당일 거래량 / 최근 20일 평균. 1.3x↑면 관심 증가, 0.7x↓면 한산.</p>
{sector_board_html}

<h2>2. 주목 섹터 · 이탈 섹터 (+뉴스 해석)</h2>
<div class="section">
<h3>핫 (상위)</h3>
<ul class="tight">{"".join(f"<li><b>{esc(r.name)}</b> {pct(r.change_pct)} · vol {vol_ratio(r.vol_ratio)}</li>" for r in hot)}</ul>
<h3>콜드 (하위)</h3>
<ul class="tight">{"".join(f"<li><b>{esc(r.name)}</b> {pct(r.change_pct)} · vol {vol_ratio(r.vol_ratio)}</li>" for r in cold)}</ul>
</div>
<table>
  <tr><th>섹터</th><th>등락</th><th>거래량</th><th>연관 뉴스</th><th>해석</th></tr>
  {''.join(sector_detail_rows)}
</table>
<div class="box">해석은 ETF 등락·거래량과 RSS 헤드라인 키워드를 자동 매칭한 결과입니다.
뉴스-가격 인과를 단정하지 말고, <b>가설</b>로 읽으세요.</div>

<h2>3. 대표 지수 변화 분석</h2>
{''.join(index_blocks)}
<h3>움직인 이유로 보이는 요인</h3>
<ul>{''.join(f"<li>{esc(r)}</li>" for r in reasons[:8])}</ul>
<div class="easy"><b>최신 동향 읽법:</b> SPY와 QQQ가 같은 방향이면 ‘전체 위험선호/회피’,
어긋나면 ‘스타일 로테이션(성장↔가치/소형)’. SMH가 단독 급등이면 AI/반도체 테마 장.</div>

<h2>4. 내 포트폴리오(보유+워치) 영향</h2>
<table>
  <tr><th>티커</th><th>종가</th><th>등락</th><th>영향·메모</th><th>관련 뉴스(자동)</th></tr>
  {''.join(port_rows)}
</table>
<div class="box">
<b>배분과의 연결 (현행 룰)</b><br/>
품질등급 A≤18%·B≤10%·C≤6% · 절대천장20% · Top3≤50% · 보유 NO_ADD ·
매수=본선∩GO · 저녁창 지정가 · SCHD 청산(완충=현금) · 현금바닥 $150 ·
확정 EARN_D5만 하드블록 · 갭추격 금지
</div>

<h2>5. 다음 장·오늘은 이렇게</h2>
<ol>{''.join(f"<li>{esc(c)}</li>" for c in checklist)}</ol>
<p class="small">이 보고서는 ‘야간 브리핑’이지 매수 신호가 아닙니다.
매수 = 본선(Chase pick_pool) ∩ 타이밍 GO · 실행은 KR 17:30~20:55 지정가만.</p>

<h2>6. 헤드라인 부록 (자동수집)</h2>
<table>
  <tr><th>출처</th><th>제목</th><th>태그</th><th>시각</th></tr>
  {''.join(headline_rows)}
</table>
<p class="small">RSS: Yahoo Finance · CNBC · MarketWatch + yfinance 종목 뉴스.
세션일 {sess} · 생성기 sepa.econ_news · 투자 권유 아님.</p>
</body></html>
"""


def write_pdf(bundle: EconNewsBundle, out_paths: list[Path]) -> Path:
    html = render_html(bundle)
    primary = out_paths[0]
    primary.parent.mkdir(parents=True, exist_ok=True)
    html_path = primary.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    pdf_bytes = HTML(filename=str(html_path)).write_pdf()
    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf_bytes)
    return primary
