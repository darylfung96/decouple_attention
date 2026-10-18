# v2 (Q1-review) program — settled choices and current state (project notes)

Owner files: `pre-publication_v2_tasks/DECISIONS.md` (decisions), `README.md` (dashboard),
`EXECUTION_PLAN.md` (phases), `../pre-publication-tasks/STATUS.md` (session resume point). This note is
the durable-memory copy; if it disagrees with the trackers, the trackers win.

## Settled 2026-10-16

- **D1 = Option A** (scope): S1 + R2 (projection-matched dense) + R6 (forecast-required figure) +
  R5 probes (regenerated) + R4 probe (route stability) + C1 all-block control. ≈15–20 h total.
  R3 (matched information budget), R7 (transfer re-run), C2, C5 stay narrowed as stated limits.
  Stop rule if the venue call (Q-6) stays open past M2: stop after Phase 3 and submit the narrowed paper.
- **Gate directories created this pass** (new-run-new-dir convention; historical gates never rewritten):
  `plan/gates/gate26_r5probes/` (R5: probe regeneration + causality suite) and
  `plan/gates/gate30_r4routes/` (R4: route-stability probe). Numbers 27–29 are reserved by the runbook
  for R2/C1/R3.

## Findings worth remembering (2026-10-16/17)

- **R2 (projection-matched dense baseline, `plan/gates/gate27_r2matched/`)**: all four compressed
  cells keep their accuracy advantage when the dense baseline is retrained with the compressed cells'
  rank-64 output projection (paired val deltas −0.110 to −0.178 MSE, every 95% interval below zero,
  21–25/25 seeds). The matched dense model is *better* than the as-run Normal (0.7910 vs 0.8389 val;
  −0.048 [−0.088, −0.008]) — the rank-128 output projection was overfitting on ETTh1, so the as-run
  Normal was not a conservative reference. Consequence: the accuracy claim holds against the matched
  baseline; the MAC saving at matched projection is 7.8% (not 20.4%), and the matched model's latency
  is 0.951× Normal on the full-layer path (4-model round-robin probe, anchored to the released run).

- **Post-mapping-fix probe regeneration changes only the equal-rate (4,4) cell.** Normal and (8,4)
  regenerate bit-identically to the pre-fix run ((8,4) kept its bit-exact legacy path). (4,4) moved and
  flips one qualitative claim: it is now lowest in every change-point distance bucket. Its delayed-copy
  range widened to 0.00129–0.00318, and the stale (4,4) smoothness Pearson (−0.31) was corrected to
  −0.35. `paper/scripts/verify_manuscript.py` has a stale-token list that blocks the rounded form
  `0.0032`; use the exact stored precision `0.00318` in text.
- **Route stability (R4, (8,4), seed 42, ETTh1)**: selected sets drift across training (mean Jaccard
  epoch 1 vs 10 = 0.83, 37% of positions unchanged) while the routed amount is flat (≈10 of 32 blocks,
  route-score entropy ≈3.13). The paper states: membership follows upstream feature drift; the routing
  amount does not.
- **Forecast-required accounting leads Figure 6** (`fig9_perf_speed`, from the released gate13 audit):
  per forecast, dense Normal is fastest (2.6 ms vs 5.8/6.2 at batch 32); full-layer (8,4) is fastest
  (31.7 vs 37.0/40.7 ms).

## Open decisions (owners in DECISIONS.md)

- **D5** non-inferiority margin — no safe default; must be frozen before the C1 control run.
- **D6** R7 handling (default: narrow the claim) and **D7** MAE (default: state the omission): zero-cost,
  close in Phase 6 / before any re-run.
- **Q-6** venue call after the manager's Information Sciences email (bounded paper vs high-aim package).

## Next phases

Phase 1 (S1 packaging; no-input drafts are in the S1 file — author names/affiliations, code license,
release tag, CRediT roles still needed) → Phase 4 (C1 all-block control; **D5 margin must be frozen
first**) → Phase 5 (R3, only if the venue call turns high-aim) → Phase 6 (R7 narrowing). Phase 3 (R2)
is closed (see findings above).
