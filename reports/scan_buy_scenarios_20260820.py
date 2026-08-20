#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thin wrapper → sepa.buy_scenarios (as_of 2026-08-20)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from sepa.buy_scenarios import run_scan

# Last complete US session available at report generation (pre Aug-20 open).
ASOF = date(2026, 8, 19)
ROOT = Path(__file__).resolve().parents[1]
RANK_PATH = ROOT / "reports" / "rank_20260820.json"
OUT = ROOT / "reports" / "buy_scenarios_20260820.json"


if __name__ == "__main__":
    run_scan(as_of=ASOF, rank_path=RANK_PATH, out_path=OUT)
