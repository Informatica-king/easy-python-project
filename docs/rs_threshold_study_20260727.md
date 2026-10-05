# RS threshold study (20260727)

Broad scan: Trend Template **without RS gate** (conditions 1–7), then slice RS≥T for T=[50, 60, 70, 80, 90]. Fund scored once; go-equivalent filters (Fund>0, mcap≥$1B) applied per slice. Anal/PDF skipped (ticker-set focus).

## Verdict

- Largest **Fund-set** change band: **60→70** (symdiff=47, removed=47, jaccard=0.703)
- Focus 70 vs 80: stage2 141→91, fund 111→70, fund removed when raising 70→80: 41종
- Fund 중앙값 최고 구간(누적): **RS≥70** (median=42.1, mean=40.39, n=111)
- 70→80 탈락 vs 잔류 Fund 중앙값: 탈락 45.2 / 잔류 38.95 (Δ=-6.25)

## 1. Counts by RS floor

| rs_min | n_stage2 | n_fund | n_dropped | n_median+ | median_fund |
|---|---|---|---|---|---|
| 50 | 242 | 197 | 45 | 100 | 37.7 |
| 60 | 197 | 158 | 39 | 79 | 39.0 |
| 70 | 141 | 111 | 30 | 56 | 42.1 |
| 80 | 91 | 70 | 21 | 35 | 39.0 |
| 90 | 42 | 32 | 10 | 16 | 34.1 |

## 2. Adjacent Fund-set churn (raising RS floor)

| band | n_lo | n_hi | Δn | removed | symdiff | jaccard |
|---|---|---|---|---|---|---|
| 50→60 | 197 | 158 | -39 | 39 | 39 | 0.802 |
| 60→70 | 158 | 111 | -47 | 47 | 47 | 0.703 |
| 70→80 | 111 | 70 | -41 | 41 | 41 | 0.631 |
| 80→90 | 70 | 32 | -38 | 38 | 38 | 0.457 |

### Tickers removed 70→80 (Fund 통과 집합)

AAPL,ALGT,ANDE,APA,AVT,AYA,BLBD,BPOP,CAKE,CASY,CHEF,CMPR,CROX,CSX,DRH,ESLT,FA,GPRE,HST,INCY,JBHT,JOYY,LIVN,LNTH,MIRM,NTRA,PAA,PAGP,PSMT,ROKU,ROST,RPRX,SBLK,SCSC,SENEA,STLD,TRMD,VCTR,VTRS,WERN,WWD

### Tickers only in RS≥70 Fund (not in RS≥80)

AAPL,ALGT,ANDE,APA,AVT,AYA,BLBD,BPOP,CAKE,CASY,CHEF,CMPR,CROX,CSX,DRH,ESLT,FA,GPRE,HST,INCY,JBHT,JOYY,LIVN,LNTH,MIRM,NTRA,PAA,PAGP,PSMT,ROKU,ROST,RPRX,SBLK,SCSC,SENEA,STLD,TRMD,VCTR,VTRS,WERN,WWD

## 3. Adjacent Stage2 churn

| band | n_lo | n_hi | removed | symdiff | jaccard |
|---|---|---|---|---|---|
| 50→60 | 242 | 197 | 45 | 45 | 0.814 |
| 60→70 | 197 | 141 | 56 | 56 | 0.716 |
| 70→80 | 141 | 91 | 50 | 50 | 0.645 |
| 80→90 | 91 | 42 | 49 | 49 | 0.462 |

## 4. Fund score distribution (cumulative RS≥T)

| label | n | mean | std | p10 | p25 | median | p75 | p90 | max | ≥50% | ≥60% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RS≥50 | 197 | 38.21 | 20.07 | 11.86 | 22.1 | 37.7 | 51.2 | 72.0 | 72.0 | 0.269 | 0.162 |
| RS≥60 | 158 | 39.62 | 20.13 | 14.94 | 25.0 | 38.95 | 54.68 | 72.0 | 72.0 | 0.291 | 0.19 |
| RS≥70 | 111 | 40.39 | 20.3 | 14.8 | 25.0 | 42.1 | 54.85 | 72.0 | 72.0 | 0.297 | 0.198 |
| RS≥80 | 70 | 39.61 | 20.42 | 14.53 | 25.0 | 38.95 | 53.8 | 72.0 | 72.0 | 0.271 | 0.186 |
| RS≥90 | 32 | 36.78 | 21.0 | 12.37 | 20.72 | 34.1 | 48.92 | 72.0 | 72.0 | 0.25 | 0.156 |

## 5. Fund score distribution (exclusive RS bands)

Fund 통과 종목만 RS 독점 구간에 배치 (겹치지 않음).

| band | n | mean | std | p25 | median | p75 | ≥50% | ≥60% |
|---|---|---|---|---|---|---|---|---|
| 50–59 | 39 | 32.49 | 19.01 | 12.4 | 31.6 | 47.0 | 0.179 | 0.051 |
| 60–69 | 47 | 37.8 | 19.8 | 23.85 | 30.5 | 50.95 | 0.277 | 0.17 |
| 70–79 | 41 | 41.73 | 20.28 | 25.0 | 45.2 | 56.8 | 0.341 | 0.22 |
| 80–89 | 38 | 41.98 | 19.88 | 25.25 | 44.9 | 55.08 | 0.289 | 0.211 |
| 90+ | 32 | 36.78 | 21.0 | 20.72 | 34.1 | 48.92 | 0.25 | 0.156 |

## 6. Removed vs kept Fund scores (when raising RS floor)

| band | removed_n | rem_med | rem_mean | kept_n | kept_med | kept_mean | Δmedian |
|---|---|---|---|---|---|---|---|
| 50→60 | 39 | 31.6 | 32.49 | 158 | 38.95 | 39.62 | 7.35 |
| 60→70 | 47 | 30.5 | 37.8 | 111 | 42.1 | 40.39 | 11.6 |
| 70→80 | 41 | 45.2 | 41.73 | 70 | 38.95 | 39.61 | -6.25 |
| 80→90 | 38 | 44.9 | 41.98 | 32 | 34.1 | 36.78 | -10.8 |

## 7. How to read

- Raising RS floor **shrinks** sets; `removed` = names that fall out of the go-like Fund list.
- Largest `symdiff_n` band = where the RS knife cuts the most names — tune around there.
- Cumulative distributions nest (RS≥90 ⊂ RS≥80 ⊂ …); exclusive bands show marginal RS quality.
- If raising RS drops median Fund, high-RS names are not automatically higher-Fund.
- Live production today uses **RS≥80** (Trend Template + fund.rs_min).
