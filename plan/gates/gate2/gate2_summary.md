# Gate 2 Factorial Summary

2x2 factorial sweep over (c_KV, c_R) ∈ {(4,4), (8,4), (4,8), (8,8)} × 5 seeds {42, 123, 2024, 7, 99} = 20 runs. Direct 96-step long-horizon forecasting, pooled MSE in standardized units. Lower is better.

## Data integrity

| Check | Result | Detail |
|---|---|---|
| (a) Param equalization vs (8,4) ref (attn 95,652 / full 348,356) | PASS | Max attn delta 0.2676% (95,396 / 95,908), max full delta 0.0735% (348,100 / 348,612); all < 0.5% |
| (b) Training matched (final_train_mse range ≤ 0.02) | PASS | Range 0.2821–0.3002, span 0.0181 |
| (c) All 20 rows present | PASS | 20/20 rows, all 5 seeds in every cell, no duplicates |

## Per-cell aggregates

| Cell | Mean val | Std val | Mean test | Std test | Mean train |
|---|---|---|---|---|---|
| (4,4) | 0.6332 | 0.0611 | 0.9079 | 0.0557 | 0.2908 |
| (8,4) | **0.5967** | 0.0710 | **0.7988** | 0.0506 | 0.2880 |
| (4,8) | 0.6858 | 0.0875 | 0.8996 | 0.0740 | 0.2983 |
| (8,8) | 0.6368 | 0.0393 | 0.9159 | 0.0317 | 0.2844 |

Champion on mean val and mean test: **(8,4)**.

## Pairwise seed deltas vs (4,4)

Per-seed val_mse delta relative to (4,4) baseline of the same seed (negative = beats baseline).

| Cell | Deltas by seed (42/123/2024/7/99) | Seeds beating baseline |
|---|---|---|
| (8,4) | −0.1485 / −0.0540 / +0.0111 / −0.0730 / +0.0821 | 3 / 5 |
| (4,8) | +0.0519 / +0.0739 / +0.0747 / −0.0366 / +0.0991 | 1 / 5 |
| (8,8) | −0.0369 / −0.0547 / +0.0447 / −0.0025 / +0.0673 | 3 / 5 |

## Main effects

- **c_KV 4→8** = mean val of {(8,4),(8,8)} − mean val of {(4,4),(4,8)} = 0.6167 − 0.6595 = **−0.0427** (negative: coarser KV compression *lowers* val MSE, i.e. slightly beneficial). Consistent direction: improves in 3/5 seeds at c_R=4 and 4/5 seeds at c_R=8.
- **c_R 4→8** = mean val of {(4,8),(8,8)} − mean val of {(4,4),(8,4)} = 0.6613 − 0.6150 = **+0.0463** (positive: coarser routing *raises* val MSE, i.e. deteriorates). Consistent direction: worsens in 4/5 seeds at c_KV=4 and 3/5 seeds at c_KV=8.

## H1 verdict

**No — coarser routing (c_R=8) does not deteriorate performance more than coarser KV compression (c_KV=8); the two effects are nearly equal in magnitude (|c_R| = 0.0463 vs |c_KV| = 0.0427) but opposite in direction, so all of the observed deterioration is attributable to routing while KV compression is mildly beneficial.** This must be read cautiously: both effect sizes (~0.04) are smaller than the mean within-cell seed-to-seed std (0.0647, per-cell std range 0.0393–0.0875) and larger than the cross-seed consistency would demand for confidence — c_R worsened val MSE in only 7/10 seed-column comparisons and c_KV improved it in only 7/10, so the sign is consistent but not unanimous. No formal significance test was run; treat these as directional, not conclusive.

## Champion config

- **Cell: (c_KV=8, c_R=4)**
- attn_params: 95,652 / full_params: 348,356 (the (8,4) reference)
- Mean val MSE: 0.5967 (±0.0710 across seeds); mean test MSE: 0.7988 (±0.0506)
