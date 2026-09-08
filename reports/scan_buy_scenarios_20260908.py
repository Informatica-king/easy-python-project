#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thin wrapper → sepa.buy_scenarios (as_of 2026-09-08)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from sepa.buy_scenarios import run_scan

# Last complete US session available at report generation (Tue 09-08 · Labor Day Mon 09-07 → last session Fri 09-05).
ASOF = date(2026, 9, 5)
ROOT = Path(__file__).resolve().parents[1]
RANK_PATH = ROOT / "reports" / "rank_20260908.json"
OUT = ROOT / "reports" / "buy_scenarios_20260908.json"


if __name__ == "__main__":
    run_scan(as_of=ASOF, rank_path=RANK_PATH, out_path=OUT)
