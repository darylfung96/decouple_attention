# Normal Baseline — Frozen-Task 5-Seed Summary

## Data integrity

| Check | Result | Detail |
|---|---|---|
| (a) Rows present | PASS | 5/5 rows, all `cell == "Normal"` |
| (b) All 5 seeds present | PASS | Seeds {42, 123, 2024, 7, 99} each exactly once |
| (c) No duplicates | PASS | 5 unique (cell, seed) pairs, no repeated seeds |
| (d) Train-range sanity | PASS | final_train_mse min 0.2844 / max 0.2878, span 0.0035; fully inside Gate-2 training range 0.2821–0.3002 → no underfit/overfit outlier |

Coverage: **5/5 rows, 5/5 seeds, 0 duplicates.**

## Normal aggregate

- **Val MSE:** 0.8416 ± 0.0799 (sample std, ddof=1)
- **Test MSE:** 1.0814 ± 0.1106 (sample std, ddof=1)
- **Final train MSE (mean):** 0.2865 (min 0.2844 / max 0.2878)

## Three-way comparison table

| Model | Val mean±std | Test mean | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 0.8416 ± 0.0799 | 1.0814 | — | — |
| CSA/Flat=(4,4) | 0.6332 ± 0.0611 | 0.9079 | −24.76% | −16.04% |
| DRRA=(8,4) | 0.5967 ± 0.0710 | 0.7988 | −29.10% | −26.13% |

Both compressed variants beat Normal on mean val and mean test; (8,4) is best on both. Deltas computed on 4dp means; Normal means from this file, Gate-2 means from `plan/gates/gate2/gate2_summary.md`.

## Paired deltas vs Normal (per-seed table)

Per-seed delta = variant val_mse − Normal val_mse for the same seed (negative = variant beats Normal). Gate-2 per-seed values read from `plan/gates/gate2/gate2_results.jsonl`.

| Model | Deltas by seed (42 / 123 / 2024 / 7 / 99) | Seeds beating Normal |
|---|---|---|
| (4,4) | −0.2623 / −0.1835 / −0.2555 / −0.1745 / −0.1664 | 5 / 5 |
| (8,4) | −0.4108 / −0.2375 / −0.2444 / −0.2476 / −0.0843 | 5 / 5 |

(8,4) has the larger per-seed advantage in 3 of 5 seeds (42, 123, 7); (4,4) has the larger per-seed advantage at seeds 2024 (−0.2555 vs −0.2444) and 99 (−0.1664 vs −0.0843).

## Caveats

- (a) **Single dataset, tiny scale:** All numbers are on one dataset (ETTh1) at CPU-scale, small model — no cross-dataset generalization claim.
- (b) **Params NOT equalized across the three rows:** Normal full_params 355,200 vs (4,4) 348,100 vs (8,4) 348,356. The compressed pair is within ~0.07% of each other, but Normal is ~2.0% larger than (8,4) and ~2.0% larger than (4,4); Normal also carries more attention params (102,496 vs 95,396 / 95,652).
- (c) **Different classes:** The compressed variants were param-equalized with each other (EPP-family); Normal is a different attention class, so the comparison is cross-class, not an ablation within one family.
- (d) **No significance test:** 5 seeds only; all statistics are descriptive (mean ± sample std, per-seed deltas). Treat direction as suggestive, not conclusive.
- (e) **Surprising direction → wiring sanity check:** The compressed variants beating an unmodified baseline by ~25–29% on val (with ~2% more params on Normal's side) is a surprising direction; NormalAttention wiring sanity re-verification completed 2026-08-14 (normal_sanity_check.md — bit-identical to naive causal reference, all 5 checks PASS).
