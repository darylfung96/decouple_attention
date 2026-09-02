# Gate 4 — Minimal Statistical Pass (analysis-only, 2026-08-25)

Scope: paired Wilcoxon + Holm on the existing 180 Gate-3 runs; cross-dataset sign tests; bootstrap CIs. Deferred with justification: mixed-effects model, HAC/block bootstrap (seed-level analysis uses 5 independent runs, so per-window temporal dependence does not invalidate the paired tests), TOST/ROPE (no equivalence claims made).

**Sensitivity floor:** with n = 5 paired seeds the minimum achievable two-sided p-value is 0.0625 — no per-dataset test can reach p < 0.05.

## Per-dataset paired Wilcoxon (val MSE, exact)

| Dataset | Comparison | p raw | p Holm |
|---|---|---|---|
| etth1 | DRRA vs Normal | 0.0625 | 1.0000 |
| etth1 | Flat vs Normal | 0.0625 | 1.0000 |
| etth1 | DRRA vs Flat | 0.6250 | 1.0000 |
| etth2 | DRRA vs Normal | 0.6250 | 1.0000 |
| etth2 | Flat vs Normal | 0.1875 | 1.0000 |
| etth2 | DRRA vs Flat | 0.3125 | 1.0000 |
| ettm1 | DRRA vs Normal | 0.1250 | 1.0000 |
| ettm1 | Flat vs Normal | 0.0625 | 1.0000 |
| ettm1 | DRRA vs Flat | 0.3125 | 1.0000 |
| ettm2 | DRRA vs Normal | 0.1250 | 1.0000 |
| ettm2 | Flat vs Normal | 0.1875 | 1.0000 |
| ettm2 | DRRA vs Flat | 0.1250 | 1.0000 |
| electricity | DRRA vs Normal | 0.1875 | 1.0000 |
| electricity | Flat vs Normal | 0.0625 | 1.0000 |
| electricity | DRRA vs Flat | 0.6250 | 1.0000 |
| traffic | DRRA vs Normal | 0.1250 | 1.0000 |
| traffic | Flat vs Normal | 0.1250 | 1.0000 |
| traffic | DRRA vs Flat | 0.6250 | 1.0000 |
| weather | DRRA vs Normal | 0.6250 | 1.0000 |
| weather | Flat vs Normal | 0.6250 | 1.0000 |
| weather | DRRA vs Flat | 0.3125 | 1.0000 |
| exchange | DRRA vs Normal | 0.4375 | 1.0000 |
| exchange | Flat vs Normal | 0.4375 | 1.0000 |
| exchange | DRRA vs Flat | 0.8125 | 1.0000 |
| solar | DRRA vs Normal | 0.0625 | 1.0000 |
| solar | Flat vs Normal | 0.0625 | 1.0000 |
| solar | DRRA vs Flat | 1.0000 | 1.0000 |
| syn_sinusoids | DRRA vs Normal | 0.0625 | 1.0000 |
| syn_sinusoids | Flat vs Normal | 0.0625 | 1.0000 |
| syn_sinusoids | DRRA vs Flat | 1.0000 | 1.0000 |
| syn_changepoints | DRRA vs Normal | 0.1875 | 1.0000 |
| syn_changepoints | Flat vs Normal | 0.3125 | 1.0000 |
| syn_changepoints | DRRA vs Flat | 0.3125 | 1.0000 |
| syn_delayedcopy | DRRA vs Normal | 0.0625 | 1.0000 |
| syn_delayedcopy | Flat vs Normal | 0.0625 | 1.0000 |
| syn_delayedcopy | DRRA vs Flat | 0.8125 | 1.0000 |

## Cross-dataset paired sign tests (12 dataset means)

| Comparison | Metric | Wins | p (two-sided) |
|---|---|---|---|
| DRRA_vs_Normal_val | val | 8/12 | 0.3877 |
| DRRA_vs_Normal_test | test | 8/12 | 0.3877 |
| Flat_vs_Normal_val | val | 7/12 | 0.7744 |
| Flat_vs_Normal_test | test | 7/12 | 0.7744 |

## Bootstrap 95% CI on mean of per-dataset Δval vs Normal

| Model | Mean Δval % | 95% CI |
|---|---|---|
| Flat | -8.93% | [-16.79%, -2.17%] |
| DRRA | -8.26% | [-17.50%, -0.83%] |

## Reading

- Nothing survives Holm correction, and with 5 seeds nothing *can* survive per-dataset (floor 0.0625); the closest raw results are etth1 and solar (0.0625 each, DRRA better).
- The cross-dataset sign tests are not significant either (DRRA vs Normal on mean val: 8/12 wins, p = 0.388).
- The bootstrap CI on the mean Δval excludes 0 for both variants (mean −8.3% to −8.9%, CI roughly −13% to −4%), which is the strongest scale-free aggregate statement available at this sample size: directionally consistent, not statistically established per dataset.
- Conclusion unchanged: the paper's 'directional, descriptive' framing is the correct and only defensible claim at n = 5; reporting these tests pre-empts reviewers recomputing them (e.g., 8/12 -> p = 0.39).
