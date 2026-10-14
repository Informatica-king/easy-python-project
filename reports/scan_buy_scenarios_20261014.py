#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thin wrapper → sepa.buy_scenarios (as_of 2026-10-14)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from sepa.buy_scenarios import run_scan

# 운영일 수 10-14 · 일봉은 전일(화 10-13) 종가까지.
ASOF = date(2026, 10, 14)
ROOT = Path(__file__).resolve().parents[1]
RANK_PATH = ROOT / "reports" / "rank_20261014.json"
OUT = ROOT / "reports" / "buy_scenarios_20261014.json"


if __name__ == "__main__":
    run_scan(as_of=ASOF, rank_path=RANK_PATH, out_path=OUT)
