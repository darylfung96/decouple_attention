# C-1 factorial recompute (25 unrounded seeds)

Design: `c1_design.md` | rows: 125 (25 seeds x 5 configs, no duplicates)

## Estimates (validation MSE)

| estimate | mean | 95% CI | Wilcoxon p | t p | sign x/25 |
|---|---|---|---|---|---|
| KV_main | -0.0516 | [-0.0811,-0.0222] | 0.0018156766891479492 | 0.0014 | 19/25 |
| routing_main | +0.0288 | [+0.0060,+0.0516] | 0.012466490268707275 | 0.0153 | 19/25 |
| interaction | -0.0262 | [-0.0710,+0.0185] | 0.312333345413208 | 0.2379 | 14/25 |
| H1_routing_minus_KV | +0.0804 | [+0.0347,+0.1262] | 0.002255260944366455 | 0.0013 | 19/25 |
| DRRA_minus_CSA | -0.0385 | [-0.0822,+0.0053] | 0.09573346376419067 | 0.0819 | 17/25 |
| CSA_minus_Normal | -0.1814 | [-0.2243,-0.1386] | 1.7881393432617188e-07 | 0.0000 | 24/25 |
| DRRA_minus_Normal | -0.2199 | [-0.2708,-0.1691] | 1.7881393432617188e-07 | 0.0000 | 24/25 |

H1 ≡ off-diagonal identity maxdiff: 2.22e-16

## Counts

best-of-four: `{'DRRA': 13, 'C88': 6, 'CSA': 5, 'C48': 1}` | beats-CSA: `{'DRRA': 17, 'C48': 5, 'C88': 17, 'Normal': 1}` | beats-Normal: `{'CSA': 24, 'DRRA': 24, 'C48': 24, 'C88': 24}` (total 96/100)

## D-2 test side (unrounded test MSE)

test means: `{'CSA': 0.9367590444, 'DRRA': 0.8439637568, 'C48': 0.9242718216, 'C88': 0.9184045392, 'Normal': 1.080447802}`
DRRA-CSA test: mean -0.0928 CI [-0.1286,-0.0570] Wilcoxon 0.0000 sign 20/25
test best-of-four: `{'DRRA': 16, 'C88': 4, 'CSA': 3, 'C48': 2}` | test beats-CSA: `{'DRRA': 20, 'C48': 14, 'C88': 18}`

## Paper verification

- DRRA_mean: paper 0.619 vs recomputed 0.618989 → MATCH
- DRRA_std: paper 0.0827 vs recomputed 0.082682 → MATCH
- CSA_mean: paper 0.6575 vs recomputed 0.657473 → MATCH
- CSA_std: paper 0.0686 vs recomputed 0.068606 → MATCH
- C48_mean: paper 0.6994 vs recomputed 0.699419 → MATCH
- C88_mean: paper 0.6347 vs recomputed 0.634693 → MATCH
- Normal_mean: paper 0.8389 vs recomputed 0.838913 → MATCH
- KV: paper -0.0516 vs recomputed -0.051605 → MATCH
- RT: paper 0.0288 vs recomputed 0.028825 → MATCH
- H1: paper 0.08 vs recomputed 0.080430 → MISMATCH
- H1_wilcox: paper 0.0032 vs recomputed 0.002255 → MISMATCH
- H1_t: paper 0.0013 vs recomputed 0.001344 → MATCH
