# R5 — Evidential chain: regenerate pre-fix probes, extend causality coverage

**Status:** PARTIAL · **Cost:** ≈30 min of runs + 1–2 h of tests · **Depends:** nothing

**Verdict:** KEEP — the cheapest item that removes a standing caveat.
**Start when:** Phase 2, first. The probes predate the mapping fix, so this runs before anything that would quote §4.3.
**Note:** the re-run needs a new output directory; the gate12 artifacts are historical and must not be overwritten.

**Source:** Q1 review §2 (PDF p. 3), item "R5. Rebuild the evidential chain after the mapping correction" (line 143).

## What the review asked

Two things. First, some mechanism probes come from checkpoints that predate the mapping correction, so
they cannot substantiate the corrected method's mechanism; regenerate them from a single versioned
implementation, or remove them from the evidential argument while keeping their development history in
the archive. Second, extend the future-invariance suite to indexer scores, block boundaries, ties,
padding and every tested rate pair, because zero future gradients alone cannot exclude future dependence
through a hard discrete selector, and state the coverage of the perturbation checks rather than assuming
a failure.

## What the paper now says

- §4.3 already labels the two affected probes as as-run historical values that predate the mapping
  correction and states that their re-run is future work. So the reviewer's "they cannot substantiate
  the corrected method" is answered by disclosure, not by re-running.
- Appendix D (Reproducibility) now states the coverage limit explicitly: all six variants pass
  future-invariance and exact-zero-future-gradient checks at the frozen geometry; the per-cell mapping
  regression extends the future-safety guard to every tested rate pair and to non-divisible lengths
  (the 31-token PatchTST regime); dedicated index-score-masking and tie-breaking probes at every rate
  pair are not yet run.

## What is left

- [x] **Regenerate the two probes (≈20–30 min).** Done 2026-10-16: `plan/gates/gate26_r5probes/`
      (design.md frozen first; gate12 untouched). Normal and DRRA (8,4) regenerate bit-identically to
      Gate 12 ((8,4) keeps its bit-exact legacy path; Normal has no mapping); the equal-rate (4,4) cell
      changes — its delayed-copy values moved (0.00129–0.00318) and, **qualitative flip**, (4,4) is now
      lowest in every change-point bucket (was (8,4) in three of four). Evidence:
      `gate26_results.json`, `gate26_summary.md`, `comparison.log/json`. §4.3 updated per the predeclared
      rule 2 (historical caveat deleted; range widened to 0.0013–0.00318; (4,4)-lowest reading in;
      signal-dependence (4,4) Pearson corrected from a stale −0.31 to −0.35, matching both Gate 12 and
      Gate 26). Appendix reproducibility paragraph and audit table now state the causality coverage
      (new rows: mechanism-probe regeneration; masking/ties PASS). `verify_manuscript.py` 0 failures;
      rebuilt clean, 31 pp.
- [x] **Extend the causality suite (1–2 h of test code, no training).** Done 2026-10-16:
      `plan/gates/gate26_r5probes/test_r5_causality.py` + `tests.log` (exit 0). Covers, for all six
      tested rate pairs (4,4)/(8,4)/(4,8)/(8,8)/(16,4)/(32,4) at S=256: (A) index-score masking with an
      adversarial future half (extreme noise): past output, selected token set and mapped block tensor
      are bitwise identical to the clean run, and no selected token/block violates the safety predicate
      (span ends <= q); (B) tie probe (a past hidden state duplicated into the next position): same
      bitwise invariance; (C) non-divisible length S=31 (patch regime) per cell: forward runs, per-block
      safety, fan-out pairing for (4,8) verified against the module's two-half layout, coverage printed
      — a diagnostic found: at S=31 the (4,8) cell cannot reach block 6 via selection (index tokens cover
      up to block 5), blocks 0–6 of 7 reachable in (4,4), all blocks reachable in (8,4)/(8,8); recorded
      as coverage, not a failure.
- [x] Update the reproducibility paragraph and the audit table with the new coverage, replacing the
      "not yet run" clause. Done 2026-10-16: `paper/sections/appendix.tex` (reproducibility paragraph +
      two audit-table rows: mechanism-probe regeneration; causality masking/ties PASS at all six rate
      pairs).

## Acceptance

Every mechanism number in §4.3 comes from the current implementation, and the causality coverage sentence
matches what the tests actually check, per rate pair.

## Cost breakdown

Probe re-runs: two single-seed jobs, ≈20–30 min on CPU. Test extension: 1–2 h of writing plus seconds of
compute. No GPU.

## Evidence pointers

- `plan/gates/gate1/gate1_causality_report.md` (current six-variant audit)
- `plan/gates/gate12/gate12_mechanistic.py` and `plan/gates/gate12/checkpoints/` (probe runs and weights)
- `test_expert_plus_plus.py` sections 5 and 6 (per-cell mapping regression, 31-token regime)
- `paper/sections/experiments.tex` §4.3; `paper/sections/appendix.tex` reproducibility paragraph

## Log

- 2026-10-16: created. Coverage limit stated in the appendix; probes not regenerated; suite not extended.
- 2026-10-16: causality suite extended and passing (6 rate pairs at S=256; 4 cells at S=31); probe
  re-run launched as `plan/gates/gate26_r5probes/` (design.md frozen first; output dir separate from
  gate12; training still in flight at log time).
- 2026-10-16: **R5 COMPLETE.** Run finished (~90 min CPU, six 10-epoch trainings). Regeneration result:
  Normal and (8,4) bit-identical; (4,4) changed, with one qualitative flip (lowest in every
  change-point bucket). §4.3, the appendix reproducibility text and the audit table updated; a stale
  (4,4) Pearson (−0.31 → −0.35) corrected against both runs. Verify 0 failures; 31 pp clean.
  Acceptance met: every mechanism number in §4.3 now comes from the current implementation, and the
  causality-coverage sentence matches what the suite actually checks, per rate pair (the S=31 (4,8)
  block-6 selectivity gap is recorded as a coverage diagnostic in `gate26_summary.md`).
