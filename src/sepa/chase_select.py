"""Chase RR snapshot I/O and **pick-pool** selection (좋은 종목 본선).

Used by:
- ``기술적분석()`` shortlist
- ``포폴()`` / ``sepa.pick_pool`` — primary stock quality universe

Timing (GO/WAIT) is separate — see ``sepa.timing_gate``.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

# Exclude if chase label matches any of these (substring or startswith rules)
_EXCLUDE_SUBSTR = ("과열", "매도", "추격금지", "비적합", "최하", "중하")
_INCLUDE_PREFIX = ("최상", "상", "중상")  # checked in order; "상" also matches "상·…"
MAX_BUY_CANDIDATES = 12
CHASE_TOP_MID_RANK = 10  # rank<=10 and label starts with 중 (not 중하) → include


@dataclass(frozen=True)
class ChaseRow:
    rank: int
    ticker: str
    chase: str
    px: float | None = None
    earn_date: str | None = None


def _norm_ticker(t: str) -> str:
    return str(t).strip().upper()


def parse_chase_rows(raw_rows: Iterable[dict[str, Any]]) -> list[ChaseRow]:
    rows: list[ChaseRow] = []
    for r in raw_rows:
        t = _norm_ticker(r.get("ticker") or r.get("t") or "")
        if not t:
            continue
        chase = str(r.get("chase") or "").strip()
        rank = int(r.get("rank") or r.get("rr") or 999)
        px = r.get("px") if r.get("px") is not None else r.get("price")
        earn = r.get("earn_date") or r.get("earnDate")
        rows.append(
            ChaseRow(
                rank=rank,
                ticker=t,
                chase=chase,
                px=float(px) if px is not None and px != "" else None,
                earn_date=str(earn)[:10] if earn else None,
            )
        )
    rows.sort(key=lambda x: x.rank)
    return rows


def is_excluded(chase: str) -> bool:
    c = chase.strip()
    if not c or c == "—":
        return True
    for s in _EXCLUDE_SUBSTR:
        if s in c:
            return True
    # "하·과열" / "하·고점" — but not "상" containing nothing; avoid matching "중상"
    if re.match(r"^하($|[·\-])", c):
        return True
    return False


def is_included(row: ChaseRow) -> bool:
    if is_excluded(row.chase):
        return False
    c = row.chase.strip()
    if "분할" in c:
        return True
    # prefix tiers: 최상 / 중상 before bare 상
    if c.startswith("최상") or c.startswith("중상"):
        return True
    if c.startswith("상"):
        return True
    if c.startswith("중") and row.rank <= CHASE_TOP_MID_RANK:
        return True
    return False


def select_buy_candidates(
    rows: list[ChaseRow],
    *,
    max_n: int = MAX_BUY_CANDIDATES,
) -> list[ChaseRow]:
    """Return Chase-ordered buy-consideration names (≤ max_n)."""
    picked: list[ChaseRow] = []
    seen: set[str] = set()
    for row in sorted(rows, key=lambda x: x.rank):
        if row.ticker in seen:
            continue
        if not is_included(row):
            continue
        seen.add(row.ticker)
        picked.append(row)
        if len(picked) >= max_n:
            break
    return picked


def write_chase_snapshot(
    rows: list[dict[str, Any]] | list[ChaseRow],
    path: str | Path,
    *,
    as_of: str | date | None = None,
    source: str = "심층분석",
) -> Path:
    """Persist Chase RR snapshot for post-deep 기술적분석 auto-run."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows and isinstance(rows[0], ChaseRow):
        serial = [asdict(r) for r in rows]  # type: ignore[arg-type]
    else:
        serial = []
        for r in rows:  # type: ignore[assignment]
            d = dict(r)  # type: ignore[arg-type]
            d["ticker"] = _norm_ticker(d.get("ticker") or d.get("t") or "")
            serial.append(d)
    payload = {
        "as_of": str(as_of or date.today())[:10],
        "source": source,
        "rows": serial,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_chase_snapshot(path: str | Path) -> tuple[str, list[ChaseRow]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    as_of = str(data.get("as_of") or "")[:10]
    return as_of, parse_chase_rows(data.get("rows") or [])


def latest_chase_snapshot(report_dir: str | Path = "reports") -> Path | None:
    paths = sorted(Path(report_dir).glob("chase_rr_*.json"))
    return paths[-1] if paths else None
