# Gate 30 — R4 route-stability probe (design, frozen before run)

Written 2026-10-16, before the run. Phase 2, item R4 (`../R4_route_stability.md`).

## Question

The paper states the indexer receives no task gradient (B2-1: indexer grads exactly 0.000e+00) and, after
the manuscript wording fix, claims "no task gradient", **not** "fixed route". Does the selected KV-block
set drift during training anyway — through the shared main-Q pathway that the router reads and the
optimizer does update? This probe replaces the unverified caveat with a measurement.

## Configuration

- Cell: `DRRA` = (8,4) — the paper's primary cell (fixed at the (8,4) geometry; one cell, as scoped).
- Task: ETTh1, frozen protocol (L=256, H=96, 10 epochs, batch 32, AdamW lr=1e-4 wd=1e-5 clip 10,
  threads 8, fp32). Single seed 42. Training code replicates `gate3_harness.train_and_eval` line for
  line; the only addition is the probe read-out (one extra `no_grad` forward per epoch).
- Probe read-out: a **fixed validation batch** (the first batch of the shuffled-off val loader, 32
  windows × 256 positions, captured once before training) is forwarded once after each epoch.
  The hook records, per query position, the **set of unique valid KV blocks** actually read
  (post-`_postprocess_topk`; the `n_kv` sentinel is dropped).
- Instrumentation: instance-level wrap of `_postprocess_topk` in the driver; the source module is
  untouched, and the same forward path is used for training and probing.
- Raw record: `results/route_snapshots.jsonl`, one line per epoch: epoch, val_mse, and the per-row,
  per-position block sets for the fixed batch. Append-only.

## Metric (predeclared)

Over all (row, position) pairs, the Jaccard overlap `|A ∩ B| / |A ∪ B|` of epoch-1 vs epoch-10 sets,
where both-empty counts as 1.0 and one-empty counts as 0.0. Reported: mean Jaccard, the fraction of
positions whose set is exactly unchanged, and the same statistics for epoch 1 vs 5 and 5 vs 10 (a
trajectory view), plus mean set size per epoch.

## Predeclared interpretation rule

- If mean Jaccard (epoch 1 vs 10) ≥ 0.9: the selected sets are stable in practice across training;
  the manuscript may say so, with the number and the single-seed scope.
- Otherwise: the sets do drift; the manuscript reports the measured drift with the number, and the
  "no task gradient" statement stands as the mechanism while the drift is disclosed as descriptive.
- Either way this is a **descriptive single-seed probe** (as the paper's other mechanism probes);
  it does not become a significance claim, and no other claim attaches to it.

## Cost and scope control

One 10-epoch ETTh1 run, ≈8–10 min CPU. The trained-indexer half of R4 stays parked behind D3.
The probe trains nothing new regarding the model: identical config to the released (8,4) row.

## Amendment 1 (2026-10-16, pre-run: entropy read-out added)

The task file (`../R4_route_stability.md`) asks for "the selected-block overlap and the score entropy
on a fixed probe batch". The design above covers overlap only, so before any run: also record, per
epoch, the route-score entropy per query position over the finite (valid) candidates —
`H = -Σ p log p` with p = softmax of the masked index scores (masked to `-inf` for future tokens, so
only valid candidates contribute) — summarized as mean ± std across all (row, position) pairs, plus
the mean number of finite candidates per position. Raw selections stay as specified; entropy is
recorded as per-epoch summary statistics (not raw tensors) to keep the JSONL compact. Same
predeclared interpretation: descriptive single-seed probe, no significance claim.
