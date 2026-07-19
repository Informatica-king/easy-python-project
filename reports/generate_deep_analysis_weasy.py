#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild 2026-07-18 deep analysis PDF with NanumGothic (Identity-H) via WeasyPrint."""

from __future__ import annotations

import html
import importlib.util
from pathlib import Path

from weasyprint import HTML

FONT_REG = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD = "/tmp/nanum/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

OUT_PATHS = [
    Path("/opt/cursor/artifacts/NASDAQ_Deep_Analysis_2026-07-18.pdf"),
    Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-18.pdf"),
]

ORDER = [
    "ECPG", "ASTH", "NESR", "KNSA", "INDV", "JBHT", "EXTR",
    "BTSG", "VCYT", "TGTX", "KRYS", "DAVE", "SEZL",
]


def load_tickers():
    path = Path(__file__).with_name("generate_deep_analysis_20260718.py")
    spec = importlib.util.spec_from_file_location("deep_old", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return {t["ticker"]: t for t in mod.TICKERS}


def e(text: str) -> str:
    return html.escape(text)


def section(title: str, body_html: str) -> str:
    return f'<div class="section"><h3>{e(title)}</h3>{body_html}</div>'


def kv_rows(pairs: list[tuple[str, str]]) -> str:
    rows = "".join(
        f'<tr><th>{e(k)}</th><td>{e(v)}</td></tr>' for k, v in pairs
    )
    return f'<table class="kv">{rows}</table>'


def ticker_html(i: int, t: dict) -> str:
    news = "".join(f"<li>{e(n)}</li>" for n in t["news"])
    c = t["conclusion"]
    return f"""
    <section class="ticker">
      <h2>{i}. {e(t['ticker'])} — {e(t['name'])}</h2>
      <p class="price">{e(t['price'])}</p>

      {section('1. One-line Thesis', f"<p>{e(t['thesis'])}</p>")}

      {section('2. 섹터 · 섹터주 특징 · 시총 순위', kv_rows([
          ('섹터', t['sector']),
          ('특징', t['sector_feat']),
          ('시총/순위', t['mcap_rank']),
      ]))}

      {section('3. 핵심 아이템', f"<p>{e(t['items'])}</p>")}

      {section('4. 실적 (YoY+QoQ · 컨센서스 · 서프라이즈 · 전략 비교)', kv_rows([
          ('실적', t['financials']),
          ('컨센서스', t['consensus']),
          ('서프라이즈', t['surprise']),
          ('전략 관점', t['strategy_view']),
      ]))}

      {section('5. 섹터·기업 뉴스 (출처)', f"<ul>{news}</ul>")}

      {section('6. 중단기 시나리오 (BULL / BASE / BEAR)', kv_rows([
          ('BULL', t['bull']),
          ('BASE', t['base']),
          ('BEAR', t['bear']),
          ('Thesis breaker', t['breaker']),
      ]))}

      {section('7. 결론 표', kv_rows([
          ('섹터', c['섹터']),
          ('핵심 아이템', c['핵심 아이템']),
          ('EPS', c['EPS']),
          ('신규진입', c['신규진입']),
          ('탈락', c['탈락']),
          ('Chase', c['Chase']),
      ]))}
    </section>
    """


def build_html(by: dict) -> str:
    surprise_rows = [
        ("ECPG", "4/4", "6연속", "4/4", "최상"),
        ("INDV", "4/4", "4연속+", "4/4", "최상"),
        ("EXTR", "4/4", "4연속", "2/4", "상(매출혼조)"),
        ("SEZL", "4/4", "4연속", "3/4", "상(과열)"),
        ("KRYS", "4/4", "4연속", "4/4", "상(고점)"),
        ("JBHT", "4/4", "4연속", "혼조", "상(반영됨)"),
        ("NESR", "3~4/4", "2~4연속", "3~4/4", "상"),
        ("DAVE", "3/4", "3연속", "4/4", "중상(변동)"),
        ("VCYT", "3/4", "2연속", "4/4", "중상"),
        ("BTSG", "3/4", "1연속", "4/4", "중"),
        ("ASTH", "2/4", "2연속", "4/4", "중(턴)"),
        ("KNSA", "2/4", "1연속", "4/4", "중"),
        ("TGTX", "0/4", "0(4미스)", "2/4", "하"),
    ]
    srows = "".join(
        f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td><td>{e(d)}</td><td>{e(f)}</td></tr>"
        for a, b, c, d, f in surprise_rows
    )

    tickers = "".join(ticker_html(i, by[tk]) for i, tk in enumerate(ORDER, 1))

    rank_rows = [
        ("1", "ECPG", "6연속 Beat + PT 업사이드 + 코어"),
        ("2", "ASTH", "최근 2연속 대형 Beat + 합리적 진입"),
        ("3", "NESR", "연속 Beat + PT 여유 + 분할 가능"),
        ("4", "KNSA", "Rev 완벽·EPS 불안정 → 반만"),
        ("5", "INDV", "Beat 머신 · 07-30 이벤트"),
        ("6", "JBHT", "4연속 Beat · 고점 눌림 대기"),
        ("7", "EXTR", "EPS 4연속 · Rev/PT 약함"),
        ("8", "BTSG", "Rev 강 · 고점 · 추가 금지"),
        ("9", "VCYT", "3/4 Beat · PT≈현재"),
        ("10", "TGTX", "EPS 4연속 미스 감점"),
        ("11", "KRYS", "Beat 우수하나 고점"),
        ("12", "DAVE", "Beat나 PT 대비 과열"),
        ("13", "SEZL", "Beat나 PT 대비 과열"),
    ]
    rrows = "".join(
        f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td></tr>" for a, b, c in rank_rows
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<title>NASDAQ 심층분석 보고서 2026-07-18</title>
<style>
@font-face {{
  font-family: 'NanumReport';
  src: url('file://{FONT_REG}');
  font-weight: 400;
}}
@font-face {{
  font-family: 'NanumReport';
  src: url('file://{FONT_BOLD}');
  font-weight: 700;
}}
@page {{
  size: A4;
  margin: 18mm 14mm 18mm 14mm;
  @bottom-center {{
    content: counter(page);
    font-family: 'NanumReport', sans-serif;
    font-size: 9pt;
    color: #666;
  }};
}}
body {{
  font-family: 'NanumReport', sans-serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #1e1e1e;
}}
h1 {{ font-size: 22pt; color: #142846; margin: 0 0 8pt; }}
h2 {{ font-size: 15pt; color: #19375f; margin: 0 0 6pt; page-break-after: avoid; }}
h3 {{
  font-size: 11pt; color: #14325a; margin: 10pt 0 4pt;
  background: #e6eef8; padding: 5pt 8pt; page-break-after: avoid;
}}
.cover {{ text-align: center; padding-top: 40mm; page-break-after: always; }}
.cover .sub {{ font-size: 14pt; font-weight: 700; margin: 8pt 0 18pt; }}
.cover .meta {{ font-size: 11pt; color: #333; margin: 4pt 0; }}
.cover .disclaimer {{ margin-top: 28pt; font-size: 9pt; color: #777; }}
.ticker {{ page-break-before: always; }}
.price {{ font-size: 9.5pt; color: #333; margin-bottom: 8pt; }}
table.data, table.kv {{
  width: 100%; border-collapse: collapse; margin: 6pt 0 10pt; font-size: 9.5pt;
}}
table.data th {{
  background: #1e3c64; color: #fff; padding: 5pt; border: 1px solid #1e3c64;
}}
table.data td {{
  border: 1px solid #c5d0de; padding: 4pt 5pt; text-align: center;
}}
table.data tr:nth-child(even) td {{ background: #f0f5fa; }}
table.kv th {{
  width: 22%; text-align: left; vertical-align: top;
  background: #f3f6fa; border: 1px solid #d0dae6; padding: 4pt 6pt; font-weight: 700;
}}
table.kv td {{
  border: 1px solid #d0dae6; padding: 4pt 6pt; vertical-align: top;
}}
ul {{ margin: 4pt 0 8pt 16pt; padding: 0; }}
li {{ margin: 2pt 0; }}
.headerbar {{
  font-size: 8.5pt; color: #777; border-bottom: 1px solid #ddd;
  margin-bottom: 10pt; padding-bottom: 3pt;
}}
</style>
</head>
<body>

<section class="cover">
  <h1>NASDAQ 심층분석 보고서</h1>
  <div class="sub">2026년 7월 18일 티커 유니버스</div>
  <p class="meta">전략: NASDAQ 전용 · 중단기 모멘텀 추격 · 어닝 서프라이즈 중시</p>
  <p class="meta">기준가: 2026-07-17 종가</p>
  <p class="meta">PT 출처: StockAnalysis (S&amp;P Global 컨센서스)</p>
  <p class="meta">서프라이즈: ChartMill / Benzinga / MarketBeat / 회사 IR</p>
  <p class="meta" style="margin-top:16pt;font-weight:700;">분석 대상 (13)</p>
  <p class="meta">ECPG · ASTH · NESR · KNSA · INDV · JBHT · EXTR</p>
  <p class="meta">BTSG · VCYT · TGTX · KRYS · DAVE · SEZL</p>
  <p class="meta" style="margin-top:10pt;font-size:9pt;color:#555;">폰트: NanumGothic (CID / Identity-H 임베드)</p>
  <p class="disclaimer">면책: 본 보고서는 투자 권유가 아니며, 공개 자료 기반의 분석 노트입니다.<br/>
  실제 매매 전 최신 시세·공시·리스크를 재확인하십시오.</p>
</section>

<section>
  <div class="headerbar">심층분석 보고서 | 2026-07-18 | NASDAQ Chase Strategy</div>
  <h2>0. 어닝 서프라이즈 요약 (최근 4분기)</h2>
  <p>어닝 서프라이즈 여부는 본 전략의 핵심 필터입니다. EPS Beat 횟수·연속성·매출 Beat를 함께 봅니다.</p>
  <table class="data">
    <thead><tr><th>티커</th><th>EPS</th><th>연속</th><th>Rev</th><th>품질</th></tr></thead>
    <tbody>{srows}</tbody>
  </table>
  <p>가격 참고: 현재가 / 52주 / PT(저·평균·고)는 각 티커 본문에 포함.</p>
</section>

{tickers}

<section class="ticker">
  <h2>투자 우선순위 재편성 (Chase RR)</h2>
  <p>당일 유니버스(13종)만 대상으로 재랭킹. 어닝 서프라이즈 · PT 대비 위치 · 이벤트 · 보유 포지션을 반영.</p>
  <table class="data">
    <thead><tr><th>순위</th><th>티커</th><th>핵심 이유</th></tr></thead>
    <tbody>{rrows}</tbody>
  </table>
  <h3>실행 우선순위</h3>
  <ul>
    <li>유지(코어 홀드): ECPG, ASTH</li>
    <li>관전: INDV(07-30), KNSA 반만(07-28), BTSG(07-31·추가X)</li>
    <li>신규 1순위: NESR $25–28 분할</li>
    <li>신규 대기: JBHT $260–275, EXTR $27–29, BTSG $58–62</li>
    <li>비추격: DAVE, SEZL, KRYS 고점, TGTX(미스 패턴)</li>
  </ul>
  <h3>보유 포트폴리오 메모 (참고)</h3>
  <ul>
    <li>ECPG avg $92.32 — 서프라이즈 최상, 코어 홀드</li>
    <li>ASTH avg $45.10 — 최근 턴, 홀드</li>
    <li>INDV avg $40.99 — Beat 머신, 추가 금지·실적 관전</li>
    <li>BTSG avg $68.38 — 추가 금지, 07-31 대기</li>
    <li>현금 ~$7.42 — 추격보다 적립·대기 우선</li>
  </ul>
  <p style="font-size:9pt;color:#777;margin-top:14pt;">
    데이터 기준일: 2026-07-17 종가 / 보고서일: 2026-07-18 (한글 폰트 수정판)<br/>
    다음 트리거: 심층분석(티커1, 티커2, ...) → 채팅 요약 + MD/PDF 본문
  </p>
</section>

</body>
</html>
"""


def main():
    for p in [FONT_REG, FONT_BOLD]:
        if not Path(p).exists():
            raise SystemExit(f"Missing font: {p}")
    by = load_tickers()
    html_doc = build_html(by)
    # Write HTML debug copy
    html_path = Path("/workspace/reports/NASDAQ_Deep_Analysis_2026-07-18.html")
    html_path.write_text(html_doc, encoding="utf-8")

    pdf_bytes = HTML(string=html_doc, base_url="file:///").write_pdf()
    for out in OUT_PATHS:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf_bytes)
        print(f"Wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
