# VCP parameter analysis (20260726)

Universe: **stage2_20260726.csv** (n=91). Research only — live weights/params unchanged.

## Verdict

- Live VCP params are **literature-aligned defaults**, not empirically optimized — and that is OK for a timing filter.
- On this universe, live valid setups today = 0 / 91 (dominant reject: base too short).
- Relaxing `base_min_weeks` raises coverage but historical WATCHLIST quality did not improve vs baseline in this sample.
- Do **not** raise `contraction_decay` just to get more hits — median max_step_ratio ≫ 1 means patterns are not VCPs.
- Keep production params; use presets only for research / optional operator modes.

## 1. Live funnel (today)

| reason_cat | n | pct |
| --- | --- | --- |
| 베이스 기간 부족 | 80 | 87.9 |
| 베이스 낙폭 과다 | 4 | 4.4 |
| 수축이 점점 얕아지지 않음 | 4 | 4.4 |
| 수축 횟수 12회 | 1 | 1.1 |
| 수축 횟수 7회 | 1 | 1.1 |
| 거래량 고갈 부족 | 1 | 1.1 |

## 2. Base length distribution

mean=17.1d  median=14.0d  p25=8.0d  p75=18.0d

| min weeks | days | share of names |
|---|---|---|
| 3 | 15 | 47.3% |
| 4 | 20 | 23.1% |
| 5 | 25 | 12.1% |
| 6 | 30 | 7.7% |
| 8 | 40 | 4.4% |

## 3. Structure after relaxing only `base_min_weeks=3`

Gates: {'base_short': 48, 'structure': 38, 'base_deep': 5}
Among structure-eligible: tighten_ok (decay≤0.75) = **10.5%**

n_merged median=4.0, max_step_ratio median=1.66 (>1 means a later contraction deeper than prior — fails classic VCP).

## 4. Preset comparison (today)

| preset | n | valid | valid_pct | BREAKOUT | WATCHLIST | FORMING | EXTENDED | NONE | top_reasons |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| live | 91 | 0 | 0.0 | 0 | 0 | 0 | 0 | 91 | 베이스 기간 부족:80; 베이스 낙폭 과다:4; 수축이 점점 얕아지지 않음:4; 수축 횟수 12회:1; 수축 횟수 7회:1 |
| minervini_strict | 91 | 0 | 0.0 | 0 | 0 | 0 | 0 | 91 | 베이스 기간 부족:80; 베이스 낙폭 과다:4; 수축이 점점 얕아지지 않음:4; 수축 횟수 12회:1; 수축 횟수 7회:1 |
| base3 | 91 | 2 | 2.2 | 0 | 1 | 1 | 0 | 89 | 베이스 기간 부족:48; 수축이 점점 얕아지지 않음:31; 베이스 낙폭 과다:5; 수축 횟수 7회:2; 거래량 고갈 부족:2 |
| leader_relaxed | 91 | 2 | 2.2 | 0 | 0 | 2 | 0 | 89 | 베이스 기간 부족:48; 수축이 점점 얕아지지 않음:27; 수축 횟수 1회:7; 베이스 낙폭 과다:2; OK:FORMING:2 |

## 5. OAT sensitivity (today) — live row highlighted in CSV

Under live params, valid setup rate today ≈ **0.0%** (full grid: `vcp_oat_20260726.csv`).

| param | live value | live valid% | best value | best valid% |
|---|---|---|---|---|
| `base_min_weeks` | 5.0 | 0.0 | 3.0 | 2.2 |
| `breakout_vol_mult` | 1.5 | 0.0 | 1.2 | 0.0 |
| `contraction_decay` | 0.75 | 0.0 | 0.5 | 0.0 |
| `contraction_min_retrace` | 0.5 | 0.0 | 0.3 | 0.0 |
| `dryup_days` | 5.0 | 0.0 | 3.0 | 0.0 |
| `dryup_ratio` | 0.6 | 0.0 | 0.8 | 1.1 |
| `final_contraction_max` | 0.1 | 0.0 | 0.08 | 0.0 |
| `max_base_depth` | 0.35 | 0.0 | 0.25 | 0.0 |
| `max_contractions` | 6.0 | 0.0 | 4.0 | 0.0 |
| `max_extension` | 0.05 | 0.0 | 0.03 | 0.0 |
| `swing_threshold` | 0.03 | 0.0 | 0.02 | 0.0 |
| `watch_zone_pct` | 0.05 | 0.0 | 0.03 | 0.0 |

## 6. Historical weekly as-of (~1y, step=5d)

Baseline median fwd10 (all ticker×dates): **3.11%**

| preset | n_eval | n_setups | hit_rate_pct | BREAKOUT | WATCHLIST | FORMING | EXTENDED |
| --- | --- | --- | --- | --- | --- | --- | --- |
| live | 4574 | 11 | 0.24 | 1 | 5 | 2 | 3 |
| minervini_strict | 4574 | 5 | 0.109 | 1 | 2 | 0 | 2 |
| base3 | 4574 | 34 | 0.743 | 3 | 22 | 2 | 7 |
| leader_relaxed | 4574 | 79 | 1.727 | 8 | 55 | 5 | 11 |

### live forward returns by signal

| signal | n | med_fwd5 | med_fwd10 | med_fwd20 | mean_fwd10 | edge_vs_base_med_fwd10 |
| --- | --- | --- | --- | --- | --- | --- |
| WATCHLIST | 5 | 0.2 | 6.6 | 13.48 | 4.59 | 3.5 |
| EXTENDED | 3 | 6.35 | 10.57 | 6.63 | 6.06 | 7.46 |
| FORMING | 2 | 0.54 | 2.19 | 2.88 | 2.19 | -0.92 |
| BREAKOUT | 1 | 13.86 | 10.65 | 13.56 | 10.65 | 7.54 |

### minervini_strict forward returns by signal

| signal | n | med_fwd5 | med_fwd10 | med_fwd20 | mean_fwd10 | edge_vs_base_med_fwd10 |
| --- | --- | --- | --- | --- | --- | --- |
| EXTENDED | 2 | 12.4 | 11.24 | 9.33 | 11.24 | 8.14 |
| WATCHLIST | 2 | 1.2 | 3.45 | 16.06 | 3.45 | 0.35 |
| BREAKOUT | 1 | 13.86 | 10.65 | 13.56 | 10.65 | 7.54 |

### base3 forward returns by signal

| signal | n | med_fwd5 | med_fwd10 | med_fwd20 | mean_fwd10 | edge_vs_base_med_fwd10 |
| --- | --- | --- | --- | --- | --- | --- |
| WATCHLIST | 22 | 0.01 | 1.88 | 5.55 | 2.54 | -1.23 |
| EXTENDED | 7 | 6.35 | 11.92 | 5.94 | 9.6 | 8.81 |
| BREAKOUT | 3 | 5.08 | 7.58 | 13.56 | 7.95 | 4.47 |
| FORMING | 2 | 0.54 | 2.19 | 2.88 | 2.19 | -0.92 |

### leader_relaxed forward returns by signal

| signal | n | med_fwd5 | med_fwd10 | med_fwd20 | mean_fwd10 | edge_vs_base_med_fwd10 |
| --- | --- | --- | --- | --- | --- | --- |
| WATCHLIST | 55 | 1.22 | 2.98 | 5.93 | 3.9 | -0.13 |
| EXTENDED | 11 | 0.06 | 1.44 | 4.23 | 3.14 | -1.67 |
| BREAKOUT | 8 | -1.86 | 6.6 | 13.67 | 8.86 | 3.49 |
| FORMING | 5 | 1.81 | 1.25 | 0.12 | -0.49 | -1.85 |

## 7. Interpretation

Classic VCP needs a multi-week base with *sequentially shallower* contractions and volume dry-up. Today's Stage2/Fund cohort is dominated by RS leaders sitting near highs, so `base_min_weeks=5` rejects most names before structure is even tested. That is consistent with the definition, not a bug.

Loosening `base_min_weeks` alone raises coverage slightly but does **not** create many true VCPs — the next wall is non-tightening contractions (`max_step_ratio` often >1.5). Raising `contraction_decay` toward 1.0+ increases hit rate by abandoning Minervini's tightening rule.

Historical scan (small n): live setups are rare but WATCHLIST/BREAKOUT median fwd10 was above baseline in this sample; `base3` and `leader_relaxed` added quantity with weaker or flat edge. Treat as provisional — sample size is tiny.

## 8. Recommendation

| Parameter | Keep live? | Note |
|---|---|---|
| `base_min_weeks=5` | **Yes** | Core VCP length; optional research preset `base3` only |
| `contraction_decay=0.75` | **Yes** | Already looser than half-rule (0.5); do not raise to chase hits |
| `contraction_min_retrace=0.5` | **Yes** | Needed to merge ZigZag noise (D7) |
| `dryup_ratio=0.6` | **Yes** | Secondary today; revisit when more setups exist |
| `max_base_depth=0.35` | **Yes** | Rare failure mode on this cohort |
| signal zones (`watch`/`extension`/`vol`) | **Yes** | Too few events to retune |

**Do not change production VCP params based on today's zero-hit Stage2 snapshot.** Next step if desired: larger event study on multi-year full-universe VCP fires (not Stage2-only).
