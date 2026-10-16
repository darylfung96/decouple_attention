# R3 — Realized information budget: match unique valid blocks across cells

**Status:** PARTIAL (caveat stated, experiment missing) · **Cost:** 10–15 h + one design call ·
**Depends:** decision D2 (selector rule)

**Verdict:** BORDERLINE — buy only if D1 chooses the high-aim option.
**Start when:** Phase 5, and only after D2 (filling rule) is frozen in `DECISIONS.md`. The rule must exist before the first run; it cannot be chosen after.
**Cost if taken:** 10–15 h, the largest single item on the keep-or-borderline list.

**Source:** Q1 review §2 "Isolate routing resolution and verify what actually changes" (PDF p. 3; lines 115–152), item "R3. Fixed top-k is not a fixed information budget" (line 117).

## What the review asked

The selection budget is a fixed top-k, not a fixed amount of information. At `k=16`, one selected
routing token in (4,8) expands to two KV blocks, while selections in (8,4) can collide on the same block;
the draft itself reports about 14 unique selected blocks for the equal-rate cells against 10 for the
dual-rate cell. The factorial therefore compares complete configurations and does not isolate routing
resolution from realized coverage. The reviewer asked for comparisons that fix the number of unique,
valid KV blocks after mapping and deduplication at each `c_KV`, for the index-to-block aggregation and
budget-filling rules to be stated, for identical causality rules and explicit handling of early queries,
and for logging candidate count, eligible count, unique selections, duplicate rate, selected fraction,
lag distribution and the union of raw-time receptive fields. Because the compressor overlaps adjacent
windows, block count times `c_KV` is not an exact measure of coverage, so he also asked for a separate
coverage-matched sensitivity analysis across `c_KV` rather than a claim that all budgets can be matched.

## What the paper now says

§4.2 has a paragraph titled "What the `c_KV` contrast changes" that states the realized-coverage caveat:
the measured unique selections are about 14 of 64 blocks for equal-rate cells and about 10 of 32 for the
dual-rate cell, so the KV main effect is a statement about the configuration (content density at a fixed
selection count) rather than about content density at matched coverage. It points at the deferred
budget-matched controls. This closes the risk that a reader takes the KV effect for a pure
content-density effect; it does not provide the matched comparison.

## What is left

- [ ] **D2 first:** choose and freeze the filling rule (recommended: score all candidate blocks, take
      them in descending score order, skip duplicates, stop when the budget of unique valid blocks is
      full). State how ties are broken.
- [ ] Implement the budget-filling selector behind a flag so the existing top-k path stays bit-exact
      (the project's rule for new geometries: extend, never restructure the canonical cells).
- [ ] Run the four factorial cells at a matched unique-block budget, 25 paired seeds on ETTh1.
- [ ] Run the coverage-matched sensitivity across `c_KV`: match the raw-time receptive-field union
      (accounting for the overlapping compressor) instead of the block count, and report whether the KV
      effect survives.
- [ ] Log the review's list per cell: candidates, eligible, unique selections, duplicate rate, selected
      fraction, lag distribution, raw-time coverage union.
- [ ] Update §4.2 and Appendix D: either the KV main effect survives budget matching, or the claim
      narrows further and the decoupling statement is restated accordingly.

## Acceptance

A matched-budget table exists beside the fixed-k table, the reviewer's coverage statistics are in the
released log, and the paper says exactly which comparison supports which wording.

## Cost breakdown

Implementation and tests ≈3–5 h; four cells × 25 seeds ≈14 h at 8 min/run; the coverage sensitivity adds
a second small sweep. No GPU.

## Evidence pointers

- `paper/sections/experiments.tex` §4.2 coverage paragraph; `paper/sections/method.tex` §3.3 realized-routing sentence
- `plan/gates/gate13_p0_audits/last_query_latency.json` (current unique-block counts)
- `expert_plus_plus_attention.py` `_postprocess_topk` (the mapping that creates the fan-out and collisions)

## Log

- 2026-10-16: created. Caveat in place; matched comparison not run.
