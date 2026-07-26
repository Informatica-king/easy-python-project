# Fund model comparison — study 20260726

- Events: **10948** · Tickers in live rescore: **70**
- Live model: **v2 weights** S47 / E25 / D14 / B14 (quality off)
- v2.1: same weights + quality gates (NPM×0.6, accel depth)
- Proposed: new study weights + v2.1 quality

## 1. Weight table

| Factor | Live v2 | Prior study | New study | Δ vs live |
|---|---:|---:|---:|---:|
| S (`eps_surprise`) | 47 | 47 | 47 | +0 |
| E (`opm_d`) | 25 | 25 | 27 | +2 |
| B (`eps_dyoy`) | 14 | 14 | 14 | +0 |
| D (`sales_dyoy`) | 14 | 14 | 12 | -2 |

## 2. Live universe score summary

- **mean live_v2**: 48.0
- **mean v2.1_quality**: 39.6
- **mean proposed**: 40.4
- **Spearman(live, v2.1)**: 0.958
- **Spearman(live, proposed)**: 0.962
- **Spearman(v2.1, proposed)**: 0.998
- **Top20 retention live↔v2.1**: 85%
- **Top20 retention live↔proposed**: 85%
- **margin_source=opm %**: 76%

## 3. New study raw Spearman (factor vs mkt-adj ret)

```
        factor     n  spearman   pearson
  eps_surprise 10916  0.187255  0.039784
    sales_dyoy  5182  0.081345  0.003993
     sales_qoq  6482  0.077876  0.058158
         opm_d  6478  0.076811  0.054451
         npm_d  6603  0.056537  0.031220
     sales_yoy  7489  0.048487  0.034317
      eps_dyoy  7072  0.037168  0.004332
    sales_dqoq  5076  0.033369  0.001722
       eps_qoq  7951  0.027891  0.001136
       eps_yoy  9584  0.026450  0.006345
      eps_dqoq  6362  0.014886 -0.007461
sales_surprise     0       NaN       NaN
```

### Prior study (2026-07-19) Spearman

```
        factor     n  spearman   pearson
  eps_surprise 10227  0.186627  0.056915
    sales_dyoy  4893  0.089216  0.004149
     sales_qoq  6069  0.080480  0.058595
         opm_d  5677  0.075814 -0.005776
         npm_d  6717  0.054243 -0.004028
     sales_yoy  7064  0.049538  0.035853
      eps_dyoy  6701  0.038021  0.004596
    sales_dqoq  4719  0.028637  0.001997
       eps_yoy  9075  0.027260  0.010139
       eps_qoq  7504  0.026811  0.000911
      eps_dqoq  5965  0.012080 -0.007655
sales_surprise     0       NaN       NaN
```

## 4. Recommendation

**판정 (2026-07-26): 가중치 변경 불필요. v2 가중치 유지 + v2.1 quality 레이어만 프로덕션 적용.**

근거:
- 신규 스터디 제안 **S47 / E27 / B14 / D12** — live 대비 요인당 **±2pt 이내**
- prior study(2026-07-19)와도 사실상 동일 (E +2, D −2만)
- 라이브 유니버스에서 proposed↔v2.1 Spearman **0.998** → 순위 거의 동일
- 실질적 점수 변화는 quality 게이트(평균 48→40)에서 발생하며, 가중치 재배분이 아님
- OPM 커버 개선 후에도 팩터 부호·순위 안정 (surprise ≫ opm_d ≈ sales_dyoy > eps_dyoy)

승인 요청: **v2.1 quality를 live 기본으로 채택**, 가중치는 S47/E25/D14/B14 유지.
