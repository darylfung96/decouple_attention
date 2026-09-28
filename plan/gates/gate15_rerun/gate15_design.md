# Gate 15 — option-(b) re-run design (pre-registered 2026-09-28, user decision "do b")

Task: `B1_operator_spec.md` B1-5 → re-train misrouted cells with fixed mapping.
Code fix: `expert_plus_plus_attention.py:_postprocess_topk` geometry dispatch
(verified: (8,4) bitwise-identical 0.0 vs pre-fix snapshot; all cells map correctly;
unsupported geometries raise; `test_expert_plus_plus.py` §5 regression added, suite passes).

## Scope (minimal re-run: only broken cells)

- Factorial ETTh1: cells (4,4), (4,8), (8,8) × 25 seeds (5 pre-reg {42,123,2024,7,99}
  + 20 ext {1..21 excl 7}) = 75 runs. KEEP existing (8,4) + Normal (unaffected).
- Suite: variant Flat only × 12 datasets × 5 seeds {42,123,2024,7,99} = 60 runs.
  KEEP existing DRRA + Normal.
- Frozen everything else: ranks (64,64) all cells (mapping fix adds zero params —
  verify via dry-run counts 95,396/95,652/95,908), window 16, topk 16, AdamW
  1e-4/wd 1e-5/clip 10, batch 32, 10 epochs final-weights, train-only z-score,
  same seeds (paired with kept runs), same cached data (`gate3/data/`, no network).

## No-contamination rule

- Old manifests (`gate2_results.jsonl`, `gate7.jsonl`, `gate3/results/*.jsonl`)
  are NEVER modified. New results → `plan/gates/gate15/results/`
  (`factorial.jsonl`, `suite_flat/<dataset>.jsonl`).
- Analysis v2 merges old-kept + new-fixed rows; old numbers stay quoted as
  as-run where referenced.

## Interpreter / env disclosure

- ALL new runs: `~/.uv_env/py311/bin/python` (torch 2.6.0, matches lock).
- Old runs mixed builds (uv 3.11 + homebrew 3.13 pyc found); merge log records
  per-row provenance (old files keep theirs; new rows tagged `gate15/uv-torch2.6.0`).
  Seed-pairing is by seed label; CPU fp32 same algorithm — statistically comparable.

## Protocol deviations from old harnesses (deliberate, logged)

- Shuffle order is reseeded per run identically to old harnesses (same code path);
  NOT "improved" to common-random-numbers — protocol must stay comparable.
- Driver reuses `EPPTimeSeriesModel`, `train_and_eval`, loaders from gate2/gate3
  modules (import, not copy); only the run-loop + paths are gate15's (precedent: gate7).

## Launch order + acceptance

1. mapping regression test passes (done) + dry-run counts match (gate before launch).
2. Factorial 75 first (RQ1 core), then suite Flat 60. Sequential, one background job,
   idempotent resume (`load_completed` on new files), log `gate15_run.log`.
3. Merge + C-1 recompute v2 → `gate15_analysis.json`; paper RQ1/H1/D-2 numbers update
   from v2 ONLY (Stage-2 text pass, after B2-2).
4. Follow-ups flagged (not this gate): gate12 Flat-checkpoint probes rerun on new
   checkpoints; D-3 multi-dataset 4-cell still needs B2-2.

## Out of scope

- (8,4)/Normal re-runs (verified unaffected); B2-2 router decision; paper text updates.
