# Benchmark Protocol — Dual-Rate Routed Attention (DRRA)

**Status: authoritative for all Gate-2+ runs under the frozen task
(`plan/gates/gate1/gate1_task.md`, direct-96, pooled `[B,96,7]` MSE, standardized units).**
Consolidated from `plan/gates/gate2/gate2_design.md` (pre-registration), `plan/gates/gate2/gate2_factorial.py`
(harness source), `plan/gates/gate2/gate2_sweep.log` (run evidence), and `plan/gates/gate1/gate1_task.md`
(task spec). Values marked [log] are confirmed by the sweep log.

## Training protocol (verified in the Gate-2 sweep)

| Element          | Setting                                          | Evidence |
|------------------|--------------------------------------------------|----------|
| Optimiser        | AdamW, lr = 1e-4                                 | design §2; harness L85/L273 [log: 20 runs] |
| Weight decay     | 1e-5                                             | design §2; harness L86 [log] |
| Gradient clipping| max norm 10.0 (`clip_grad_norm_`)                | design §2; harness L87/L285 |
| Batch size       | 32                                               | design §2; harness L76 |
| Epochs           | 10, FIXED budget                                 | design §6; harness L88/L275 |
| Scheduler        | **none**                                         | harness: no LR schedule object |
| Warm-up          | **none**                                         | harness: no warm-up steps |
| Initialisation   | PyTorch default for all `nn.Linear`/`LayerNorm`; positional embedding `randn` (matches `model.py:23`) | design §2 |
| Mixed precision  | **none** — float32, CPU-only                     | harness: no autocast/GradScaler; log header "CPU PyTorch" |
| Threads          | `torch.set_num_threads(8)`                       | harness L451; log header "threads=8" |
| Deterministic seeding | `torch.manual_seed(seed)` before data load AND before model init (same seed across cells — paired design) | design §5; harness L240/L386/L452 |
| Data             | ETTh1, stride-1 windows, train-only per-feature z-score, chronological 60/20/20 split, val/test `shuffle=False` | gate1_task §3–5 |
| Batch counts     | train 316 / val 98 / test 98                     | [log] |

## Fixed-budget justification (quoted from `plan/gates/gate2/gate2_learning_curves.md` §(c))

> **The fixed 10-epoch budget is justified by the data; there is no evidence of
> under-training.** No cell shows a sustained improvement after epoch 4
> (worst-case single-epoch dip 0.011–0.015 in the (4,4) mean at E5/E7/E8/E10,
> within seed noise), and the only directional movement is a mild upward drift
> in the (4,8) mean (+0.05 by epoch 9, driven by its oscillating seeds). The
> mean last-3-epoch drift across all 20 runs
> is +0.0009 (flat), and best val is reached on average at epoch 6.5 with only
> 5/20 runs still improving in the final three epochs (magnitudes within noise…).
> Training beyond 10 epochs would not recover systematic gains for the *comparison*
> of cells… the fixed 10-epoch budget does **not** bias the 2×2 cell comparison —
> all cells share the identical schedule and all are in the same plateau regime.

## Elements NOT documented (flagged)

| Element | Status |
|---------|--------|
| Optimiser hyperparameters beyond lr/wd (AdamW `betas=(0.9,0.999)`, `eps=1e-8`, PyTorch defaults) | not documented in design; inherited defaults, **flag before submission** |
| Model checkpointing / val selection: reported val & test are from **epoch-10 weights**; no best-val checkpoint selection | not documented in design; explicit now |
| Dropout: **none** in the EPP wrapper (no dropout layers) | not documented in design; explicit now |
| DataLoader `num_workers=0` (PyTorch default; single-process) | not documented in design; explicit now |
| `torch.use_deterministic_algorithms(True)` / cuDNN benchmark flags: **not set** — determinism is seed-level (same seed ⇒ same result on same machine/BLAS); not bit-exact across machines | not set; CPU-only so cuDNN flags are moot, but flag in reproducibility package |
| Hardware details (Apple chip model, macOS version, PyTorch/BLAS versions) | deferred to Gate 5 (§10 of `plan/next_step.md`) |

## Reporting invariants (for the paper)

- All metrics in standardized (z-score) units, pooled MSE over all `(B,96,7)` elements.
- All four cells use the **identical** auxiliary contract (window 16, topk 16, 4 heads,
  head_dim 32, hidden 128, o_groups 4, shared-Q, q/o ranks 64) and differ only in
  (c_KV, c_R) — the cell definition.
- Paired seeds across cells; report all 5 seeds, not just means.