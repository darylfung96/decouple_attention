# B1 — Dual-rate operator spec + budget control

Status: PARTIAL (B1-5 FIXED + Gate15 running; B1-1 QUEUED; B1-3/B1-4 TODO) | Updated: 2026-09-28 | Evidence: `plan/gates/gate13_p0_audits/mapping_audit.json/md`, `plan/gates/gate15_rerun/` | Depends: B1-3 needs Q-2; paper number refresh needs Gate15 v2

Reviewer ask: mapping between 64 index tokens / 32 KV blocks (and 32/64 corner) unexplained. Need: index→KV intervals, collisions, coarse→multiple-fine, causality via true receptive fields of overlapping compressors. Fixed top-k ≠ fixed selected blocks/history. Report realized unique blocks + matched-budget control.

Current state:
- Code HAS it: `t//2`, `block_end=8j+7`, `safe = block_end <= q`, sentinel `n_kv=32`, never-unmask guard + `_build_idx_positions` + future-mask in `forward`.
- Paper `method.tex §family-mech` lacks `t//2` rule, collision handling, inverse-corner rule, receptive-field causality.
- No unique-block counts; no matched-budget control.

## Tasks

- [x] **B1-5.** DONE 2026-09-28 RED→FIXED — mapping audit found `t//2` unconditional (correct ONLY for (8,4)). Q-3 DECIDED = option (b): geometry dispatch implemented; (8,4) bitwise-identical 0.0; regression test §5 passes; Gate15 re-running broken cells. Evidence: `mapping_audit.json/md`, `expert_plus_plus_attention.py`, `plan/gates/gate15_rerun/`.
- [x] **B1-1.** DONE 2026-09-28 — algorithm box in `method.tex §family-mech` (per-cell rules, sentinel, block-end safety, backward-only overlap fields, raise rule, pre-fix historical note). Reimplementable from paper alone.
- [x] **B1-2.** DONE 2026-09-28 — synthetic batch (3 seeds × B=2, mechanics data-independent): CSA unique-valid 13.94/16 of 64 blocks (window 32; adjacent Jaccard 0.48); DRRA 10.17/16 of 32 (`//2` collisions: raw 14.18 → 10.17; Jaccard 0.64). Effective cols ≈ 47 (CSA) / 27 (DRRA) vs dense-masked 96/48 (+sink). NOTE: `_attend` is dense-masked (compute stays 96/48); report both. Evidence: `plan/gates/gate13_p0_audits/last_query_latency.json/md`. Real-data rerun only if Stage-2 proceeds.
  - Acceptance: states whether routing effect confounded by budget.
- [ ] **B1-3.** Matched-effective-budget control (pre-register rule). Min 5 seeds × 2 cells. Effort: M. Depends: A-1, B2-1.
  - Acceptance: control in RQ1/appendix.
- [ ] **B1-4.** Causality via overlapping-compressor receptive fields + suite refs (`gate1_causality.py`, `gate1_gradmask.py`).

## Log

- 2026-09-28: Created from review §B1; header added.
- 2026-09-28: B1-2 DONE (effective ≈47/27 vs dense 96/48; DRRA //2 collisions quantified). Next: B1-1 algorithm box (text-only, unblocked).
- 2026-09-28: B1-5 RED→FIXED (Q-3=(b)); Gate15 launched. B1-1 QUEUED; B1-3 needs Q-2; paper numbers refresh needs Gate15 v2.
- 2026-09-28: B1-1 DONE (box in method.tex). B1-3/B1-4 remain blocked (Q-2 / Stage-2).
- 2026-09-28: Q-3 = option (b). FIXED: geometry dispatch in `_postprocess_topk` (identity/fan-out/t//2 + raise); (8,4) bitwise-identical 0.0 vs snapshot; regression test §5 added (passes); dataset.py stale comment fixed. Essential-code-review done (report in session). Gate15 launched: factorial 75 (pid 23972, log `gate15_run.log`); suite-Flat 60 queued after.
