#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thin wrapper → sepa.buy_scenarios (as_of 2026-08-06)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from sepa.buy_scenarios import run_scan

ASOF = date(2026, 8, 6)
ROOT = Path(__file__).resolve().parents[1]
RANK_PATH = ROOT / "reports" / "rank_20260806.json"
OUT = ROOT / "reports" / "buy_scenarios_20260806.json"


if __name__ == "__main__":
    run_scan(as_of=ASOF, rank_path=RANK_PATH, out_path=OUT)
