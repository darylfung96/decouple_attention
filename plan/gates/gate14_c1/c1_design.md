# C-1 recompute design (pre-registered 2026-09-28)

Task: `C_factorial_reanalysis.md` C-1 (also feeds D-1, I-1, I-3, C-5 verification).
Env: `~/.uv_env/py311/bin/python` (scipy 1.15.3). No training; merged manifests only.

## Inputs

- `plan/gates/gate2/gate2_results.jsonl`: 20 rows = 4 cells × 5 pre-registered seeds {7,42,99,123,2024} (val/test/final_train, unrounded float).
- `plan/gates/gate7_seeds/results/gate7.jsonl`: 100 rows = 5 configs × 20 seeds {1..21 excl 7} (adds Normal + 20-seed extension).
- Merge key: (config, seed). Config map: gate2 `cell:[4,4]`→CSA, `[8,4]`→DRRA, `[4,8]`, `[8,8]`; gate7 `cell_name`. Overlap check: gate7 seeds exclude 7 but include 42/99/123/2024? Seed list {1..21 excl 7} = includes NO pre-registered seeds except... pre-reg {42,123,2024,7,99} — 42/123/2024/99 not in 1..21, so disjoint except seed 7 excluded. Expect 25 unique seeds × 5 configs = 125 rows, no duplicates. ASSERT all of this; stop on mismatch.

## Estimates (per-seed, validation MSE, unrounded)

- KV main: `mean(y84,y88) − mean(y44,y48)`; routing main: `mean(y48,y88) − mean(y44,y84)`.
- Interaction: `(y88−y84) − (y48−y44)`.
- H1 contrast: routing − KV per seed (≡ y48−y84 off-diagonal; report identity as check).
- DRRA−CSA per seed; each cell − Normal per seed.
- Stats per estimate: mean, 95% CI (paired t), Wilcoxon signed-rank, paired t-test.
- Counts: sign consistency per effect (x/25); Beats-CSA per cell (x/25); best-of-four per seed (which cell min; ties noted); seeds beating Normal per cell; 96/100 roll-up.
- Reproduction check vs paper: cell means/stds (0.6190±0.0827 etc.), −0.0516/+0.0288, 19/25s, 17s, H1 +0.080 p=0.0032/0.0013, DRRA-vs-CSA p=0.093, 24/25s. Print MATCH/MISMATCH per value (tol 5e-5 for rounded).

## Artifact

`plan/gates/gate14_c1/c1_recompute.json` (+ `.md` summary). Acceptance (C-1): all four estimates + CIs + tests from unrounded seeds; verification table vs paper.
Out of scope: text rewrites (C-2..C-5 follow from JSON).
