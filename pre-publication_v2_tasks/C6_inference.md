# C6 — Inference: temporal uncertainty, MAE, and a predeclared non-inferiority margin

**Status:** TODO · **Cost:** 3–6 h of analysis and writing, plus runs if rolling origins are added ·
**Depends:** nothing · **Source:** Q1 review §7 (PDF p. 8; `source/q1_review_text.txt` lines 392–430), "Separate three sources of uncertainty" (line 393)

**Verdict:** PARKED, except one sentence: state that the intervals are paired mean differences over 25 seeds and that no equivalence test is run (already the paper's reading).
**Start when:** a referee disputes the intervals or the word "tied"; the margin (D5) is only needed if a new run makes an equivalence claim.

## What the review asked

Three sources of uncertainty must be separated, because one large seed count does not replace the others:
training randomness (already handled by the 25 paired seeds), **temporal** uncertainty (evaluate rolling
forecast origins or independent time blocks and keep per-origin losses), and dataset variation (report
conditional effects per dataset and do not count every seed or related ETT series as an independent
domain). Specifically:

- For per-origin inference use a paired moving-block or another dependence-aware resampling scheme with
  block-length sensitivity; do not bootstrap overlapping windows as independent observations.
- Report **test MSE and MAE**, uncertainty for the interaction and the simple effects, and the
  multiplicity family for the primary contrasts.
- State whether each interval concerns a paired mean, a median or another estimand, because a
  mean-difference interval and a signed-rank test need not agree.
- A non-significant difference is **not** evidence of preserved accuracy: to claim that a cheaper
  configuration retains performance, predefine a defensible non-inferiority margin and estimate whether
  the data support it, choosing the margin before seeing the results.
- Preserve the original five-seed analysis, its extension and the new confirmation as distinguishable
  stages.

## What already holds

- Paired-seed intervals and exact Wilcoxon tests throughout, with the estimand disclosed as a paired mean
  difference; the per-seed conditional effects with intervals were added on 2026-10-16 (R1).
- The seed history is disclosed as a planned merge of five pre-registered seeds with a 20-seed power
  extension, fixed before the extension ran.
- The paper states that it makes no equivalence claims and therefore runs no equivalence tests, and it
  defers HAC and block-bootstrap corrections with the reason that the analysis is at the seed level.

## What is left

- [ ] **MAE.** No manifest records MAE (the run harness stores validation, test and train MSE only). If
      MAE is to be reported, either re-run with the extra metric or state the omission and its reason.
      MSE-only reporting is a common referee request in forecasting venues.
- [ ] **Temporal uncertainty.** Evaluate rolling forecast origins or independent time blocks and retain
      per-origin losses, then use a paired moving-block resampling scheme with a block-length sensitivity
      check. This is the item the reviewer names in the Neurocomputing minimum package as "temporal
      validation". Note that previously inspected test periods cannot become unseen by renaming the
      endpoint, so the holdout must be genuinely fresh.
- [ ] **Non-inferiority.** The paper's "tied within noise" statements (DRRA versus CSA on validation, and
      the PatchTST transfer) should either carry a predeclared margin with a TOST-style test or be
      reworded so that no reader hears "performance preserved". Predeclare the margin now, before any
      new run, so the choice cannot look selected after the fact.
- [ ] **Multiplicity.** State the family for the primary contrasts explicitly (the paper currently lists
      the four reported estimates and their Holm correction for the cell-versus-Normal contrasts; make
      that sentence self-contained).
- [ ] **Interval semantics.** State in one place that all reported intervals are paired mean differences
      from a t interval, alongside the Wilcoxon p-values, so the two are not read as interchangeable.

## Acceptance

Each claim of the form "no significant difference" is either backed by a predeclared non-inferiority
margin or explicitly labelled "not tested for equivalence", every reported interval names its estimand,
and the temporal-validation result exists or the omission is stated with its reason.

## Cost breakdown

MAE: the cheapest honest route is one re-run of the factorial at five seeds (≈2.7 h) plus text, or the
stated omission at zero cost. Temporal validation: a rolling-origin harness over a few folds is a few
hours of code plus runs of the same order as a small suite. Non-inferiority and interval semantics:
analysis and writing only, 1–2 h.

## Evidence pointers

- `plan/gates/gate15_rerun/results/factorial.jsonl` (fields recorded per run — no MAE)
- `paper/sections/experiments.tex` §4.5 statistical treatment; `paper/sections/discussion.tex` descriptive-statistics limitation
- `plan/gates/gate15_rerun/gate15_analyze.py` (the `est()` helper that defines the interval semantics)

## Log

- 2026-10-16: created after checking the review's minimum package against the tracker; this area was
  missing from the first version of this folder.
