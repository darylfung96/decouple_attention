# R4 — Route stability: does the selected set drift during training?

**Status:** PARTIAL (wording fixed, probe missing) · **Cost:** ≈0.5 h probe, 3–4 h per extra control ·
**Depends:** nothing

**Verdict:** KEEP for the probe; the trained-indexer half is parked behind D3.
**Start when:** Phase 2, after R5 (the probe reports beside numbers R5 may move). About 30 min plus an 8–10 min run.
**Reopens later only if** C1 shows the router is doing real work and D3 changes.

**Source:** Q1 review §2 (PDF p. 3), item "R4. An untrained indexer is not necessarily a fixed route" (line 131).

## What the review asked

The router reuses queries and hidden representations produced by trainable components. Even if
indexer-exclusive parameters receive no direct task-loss gradient, the selected blocks can change as
those inputs change, so "routing is fixed at initialization" is not established by a gradient audit. He
asked for route overlap and entropy tracked on fixed probe inputs at initialization and across epochs,
saved parameter snapshots, a distinction between a missing gradient and a zero gradient including actual
optimizer updates, separate random seeds for backbone, indexer and data loader, a comparison against a
genuinely fixed mask and against an explicitly trained selector, and, for a learned-routing control, the
extra training cost and test-time requirements.

## What the paper now says

All four places (abstract, §3.3, the limitations list, the audit table) now say the indexer receives no
task gradient, that this shows gradient isolation rather than literal route constancy, and that route
membership still follows the drift of upstream features. The audit table row reads "No task gradient —
all indexer grads exactly 0, both variants (route membership itself not probed)", so the gap is visible
rather than implied.

## What is left

- [x] **Cheap probe.** Done 2026-10-16 as `plan/gates/gate30_r4routes/` (design.md frozen pre-run;
      runbook scopes one cell, so the probe covers (8,4) rather than both cells). Result: the selected
      sets are not fixed — mean Jaccard epoch 1 vs 10 = 0.8312 with 36.8% of positions unchanged
      (1 vs 6: 0.8563; 6 vs 10: 0.9106) — while the routed amount is flat: set size ≈10.02 of 32 blocks
      and route-score entropy ≈3.13 across all ten epochs (Amendment 1 added the entropy read-out
      pre-run). Val MSE 0.782 → 0.584. Evidence: `results/route_snapshots.jsonl`, `analysis.json`,
      `analysis.md`, `run.log`.
- [x] **Zero versus missing gradient.** `plan/gates/gate13_p0_audits/router_grad_audit.json` already
      records both `grad_norm` and `sgd_delta` per parameter: every indexer-exclusive parameter has
      both exactly 0.000e+00 (the parameter is present in the optimizer, not absent from the graph).
      The method section sentence now states this explicitly.
- [ ] **Seed separation.** Not run; the frozen design is a single-seed descriptive probe (runbook scope).
      Listed as a scope limit, not an open intent.
- [ ] **Controls (optional, D3).** Parked per D3 (keep the non-learned indexer); reopens only if C1
      shows the router is doing real work.
- [x] Update the paper: the caveat is kept and the measurement placed beside it. Done 2026-10-16 —
      §4.3 probe (iv) added (drift measured, amount flat) and the descriptive qualifier updated;
      method §3.3 now says the drift is measured rather than deferred; audit-table router-gradient row
      carries the measured numbers. `verify_manuscript.py` 0 failures; rebuild clean (31 pp).

## Acceptance

The paper states a measured route-stability result (overlap and entropy across epochs), and either the
limitation is removed or it is stated as "routes drift by X% while accuracy is unchanged".

## Cost breakdown

Probe harness and analysis ≈30 min including the run (one seed, two cells, 10 epochs ≈ 16 minutes of
compute). Fixed-mask and trained-selector controls: implementation plus 25 seeds each ≈ 3–4 h per
control.

## Evidence pointers

- `plan/gates/gate13_p0_audits/router_grad_audit.json` (gradient and `sgd_delta` per parameter)
- `paper/sections/method.tex` §3.3; `paper/sections/discussion.tex` limitations; `paper/sections/appendix.tex` audit table
- `plan/gates/gate2/gate2_factorial.py:271` `train_and_eval` (currently saves no per-epoch state)

## Log

- 2026-10-16: created. Wording corrected in four places; probe not run.
- 2026-10-16: code ready and frozen pre-run — `plan/gates/gate30_r4routes/design.md` (with Amendment 1
  adding the route-score entropy read-out the task file asks for), `run.py` (single (8,4) cell, seed 42,
  ETTh1, frozen protocol replica with an instance-level `_postprocess_topk` hook; fixed val batch
  snapshotted per epoch), `analysis.py` (Jaccard overlap + unchanged fraction + entropy trend). Queued
  to run after gate26 (R5) so training runs never interleave. The two-cell variant and seed separation
  stay out of scope (runbook scopes one cell); trained-indexer controls stay parked behind D3.
- 2026-10-16: **R4 COMPLETE.** Ran after gate26 (17 min). Result per the predeclared rule: drift present
  (mean Jaccard 0.83 < 0.9) → the measured drift is reported: membership drifts (37% of positions keep
  their exact set between first and final epoch) while the amount is constant (≈10 of 32 blocks;
  entropy ≈3.13 flat). Paper: §4.3 probe (iv), method §3.3 sentence, audit-table row (0.83 and the
  ≈10-of-32 detail). Verify 0 failures; 31 pp clean.
