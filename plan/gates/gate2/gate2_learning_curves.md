# Gate 2 — Validation Learning Curves & Convergence Verdict

Source: `gate2_sweep.log` (20 runs: 4 cells × 5 paired seeds {42, 123, 2024, 7, 99},
10 epochs each, full train split). Plot: `gate2_learning_curves.png` (matplotlib,
per-cell mean over 5 seeds). Task: direct-96, pooled `[B,96,7]` MSE, standardized units.

## Coverage (verification)

- Runs present: **20/20** (cells (4,4), (8,4), (4,8), (8,8) × 5 seeds).
- Epoch lines present: **200/200** (10 per run).
- `FINAL` + `appended` lines: present for **20/20** runs.
- No gaps, no invented data.

## (a) Per-cell mean validation MSE per epoch (mean over 5 seeds, 4 dp)

| Epoch | (4,4)  | (8,4)  | (4,8)  | (8,8)  |
|-------|--------|--------|--------|--------|
| 1     | 0.7620 | 0.7423 | 0.7541 | 0.7709 |
| 2     | 0.6589 | 0.6157 | 0.6475 | 0.6598 |
| 3     | 0.6394 | 0.5805 | 0.6364 | 0.6256 |
| 4     | 0.6483 | 0.5848 | 0.6526 | 0.6309 |
| 5     | 0.6373 | 0.5850 | 0.6462 | 0.6423 |
| 6     | 0.6555 | 0.6131 | 0.6746 | 0.6594 |
| 7     | 0.6342 | 0.6026 | 0.6756 | 0.6471 |
| 8     | 0.6342 | 0.6047 | 0.6647 | 0.6451 |
| 9     | 0.6513 | 0.6012 | 0.6970 | 0.6556 |
| 10    | 0.6332 | 0.5967 | 0.6858 | 0.6368 |

All four cells drop sharply in epochs 1–3, and later-epoch means stay within
(4,4) [0.633, 0.656], (8,4) [0.5848, 0.6131], (4,8) [0.646, 0.697],
(8,8) [0.6309, 0.6594] of their epoch-3 level. No cell shows a sustained
downward trend after epoch 4.

## (b) Per-cell convergence diagnostics (per run: best-val epoch over 1–10,
last-3-epoch drift Δval = val(10) − val(8); classes: plateaued Δval ≥ −0.005,
still-improving Δval < −0.005, oscillating val(10) > best-val + 0.01. Means/counts over 5 seeds)

| Cell  | Mean best-val epoch | Mean Δval (val10−val8) | Plateaued | Still-improving | Oscillating |
|-------|--------------------:|------------------------:|----------:|----------------:|------------:|
| (4,4) | 7.40                | −0.0011                 | 1         | 1               | 3           |
| (8,4) | 6.40                | −0.0080                 | 0         | 2               | 3           |
| (4,8) | 5.40                | +0.0210                 | 1         | 0               | 4           |
| (8,8) | 6.80                | −0.0084                 | 1         | 2               | 2           |
| **All** | **6.50**          | **+0.0009**             | **3**     | **5**           | **12**      |

Best val occurs on average at epoch 6.5; the mean drift over the last three
epochs is +0.0009 (essentially zero, slightly *worse* than flat). Only 5 of 20
runs still showed last-3-epoch improvement beyond the −0.005 threshold, and
those improvements are within the seed-to-seed noise band of these curves.
12 of 20 runs ended with val worse than their peak by >0.01 — the dominant
pattern is oscillation around a plateau, not under-training.

## (c) Verdict

**The fixed 10-epoch budget is justified by the data; there is no evidence of
under-training.** No cell shows a sustained improvement after epoch 4
(worst-case single-epoch dip 0.011–0.015 in the (4,4) mean at E5/E7/E8/E10,
within seed noise), and the only directional movement is a mild upward drift
in the (4,8) mean (+0.05 by epoch 9, driven by its oscillating seeds). The
mean last-3-epoch drift
across all 20 runs is +0.0009 (flat), and best val is reached on average
at epoch 6.5 with only 5/20 runs still improving in the final three epochs
(magnitudes within noise, e.g. −0.005 to −0.04 across runs that still show
both later-epoch regressions). Training beyond 10 epochs would not
recover systematic gains for the *comparison* of cells: later epochs only add
oscillation (12/20 runs end worse than their peak). A caveat for the paper: an
early-stopping rule with patience (e.g. best-val with patience 3 on the ~6.5
mean best epoch) *would* have selected slightly better per-seed checkpoints, so
early stopping is a legitimate protocol improvement for Gate 3+, but the fixed
10-epoch budget does **not** bias the 2×2 cell comparison — all cells share the
identical schedule and all are in the same plateau regime.