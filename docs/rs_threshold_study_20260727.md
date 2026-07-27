# RS threshold study (20260727)

Broad scan: Trend Template **without RS gate** (conditions 1–7), then slice RS≥T for T=[50, 60, 70, 80, 90]. Fund scored once; go-equivalent filters (Fund>0, mcap≥$1B) applied per slice. Anal/PDF skipped (ticker-set focus).

## Verdict

- Largest **Fund-set** change band: **60→70** (symdiff=47, removed=47, jaccard=0.703)
- Focus 70 vs 80: stage2 141→91, fund 111→70, fund removed when raising 70→80: 41종

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

## 4. How to read

- Raising RS floor **shrinks** sets; `removed` = names that fall out of the go-like Fund list.
- Largest `symdiff_n` band = where the RS knife cuts the most names — tune around there.
- Live production today uses **RS≥80** (Trend Template + fund.rs_min).
