# Gate 1 Causality Audit Report (gate1_task.md §8)

**Date:** 2026-08-12
**Companion scripts:** `gate1_causality.py`, `gate1_gradmask.py`, shared helper `_gate1_common.py`
**Scope:** 6 variants (CSA, ModifiedCSA, Normal, FlatPlus, ExpertFlat, ExpertPlusPlus), num_features=7, L=256, H=128, fresh eval-mode models, x = randn(2,256,7) seed 42. Encoder state = post-norm2 output via forward hook on `model.norm2` (head excluded; tested separately e2e).

## Commands used (run from repo root)
```
python3 gate1_causality.py     # exit 0
python3 gate1_gradmask.py      # exit 0
```

## Results — per-variant PASS/FAIL (both scripts)

| variant | causality probes p=32/128/224 (future-invariant, power, e2e) | gradmask probes p=64/192 (future zero, power) |
|---|---|---|
| CSA | PASS (3/3 × 3 checks) | PASS (2/2 × 2 checks) |
| ModifiedCSA | PASS | PASS |
| Normal | PASS | PASS |
| FlatPlus | PASS | PASS |
| ExpertFlat | PASS | PASS |
| ExpertPlusPlus | PASS | PASS |

**ALL 6 VARIANTS PASS.** Exit codes: causality 0, gradmask 0. Future-perturbation invariance is bitwise (`torch.equal` True); gradient mask is exactly zero (`count_nonzero == 0`) for all future regions; power/e2e checks confirm the tests have teeth (past perturbations and last-16-row perturbations change outputs).

## Failure details
- **No model variant failed.** One TEST bug was found and fixed (see below); no changes to `model.py` or any attention module.

## Test fix applied (documented for the audit)
- First gradmask run showed `h_p.sum()` power-check failing on every variant (nz_past = 0 or ~1e-8 noise). Root cause: every model ends in LayerNorm; its Jacobian rows sum to ~0 for fresh models (weight init = 1, mean-centering), so the unweighted sum functional measures ~float32-epsilon gradients for ANY input dependency (standalone check: `grad(LN(z)[:,p].sum(), z)` max = 1.19e-7). Fixed by probing with a fixed seeded random projection `(h_p * probe_w).sum()` (seed 1234), which is O(1) for any real dependency and remains exactly 0 in the masked future. The future-mask check (exactly zero) was already correct in the original run and stayed correct.
