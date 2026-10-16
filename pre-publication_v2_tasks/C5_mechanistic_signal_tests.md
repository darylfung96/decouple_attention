# C5 — Mechanistic and signal-controlled tests

**Status:** TODO · **Cost:** 15–25 h · **Depends:** nothing, but benefits from R3 (budget matching)
**Source:** Q1 review §6 "Build a mechanism-level contribution that others can reuse" (PDF p. 7; `source/q1_review_text.txt` lines 333–385): the signal-family table (lines 339–360) and "A useful analytical starting point" (line 366). Named in the Neurocomputing minimum package as "the mechanistic tests should support the explanation" (line 525).

**Verdict:** PARKED — the paper never claims a mechanism and says so explicitly, so this is a different paper's work.
**Start when:** a referee says the mechanism is asserted rather than shown; the admissible response points at the explicit unverified-mechanism statement and offers these families as future work.

## What the review asked

Replace the suggestive correlation (lag-1 autocorrelation versus compression advantage, r ≈ −0.3 with
p ≈ 0.3) with controlled signal tests, because a descriptive correlation is not an established
explanation. Three synthetic families, each with independent knobs and measurements beyond pooled MSE:

| Family | Vary independently | Measure beyond pooled MSE |
|---|---|---|
| Smooth latent signal plus noise | signal bandwidth, observation noise, compression rate; state whether the target is noisy or latent | predictive-signal distortion, noise attenuation, per-horizon error |
| Random-content delayed recall | fresh episodes, in-window lag, event alignment; provide an observable lag cue where needed | recall error on recoverable channels, selected-block coverage of the target |
| Localized predictive events | event width, lag, block-boundary alignment; avoid targets needing unobserved random content | event localization, amplitude error, sensitivity to compression |

He also asks for two specific things the paper currently gets wrong or omits:

1. **Do not call the compressor a low-pass filter without measuring it.** A nonlinear, gated,
   overlapping compressor should be compared against a specified linear filter, and its empirical
   response recorded.
2. **An elementary diagnostic.** With `o_full` the uncompressed attention output, `o_all` attention to
   all compressed blocks and `o_route` the routed output, the triangle inequality gives
   `‖o_full − o_route‖ ≤ ‖o_full − o_all‖ + ‖o_all − o_route‖`, and with retained mass bounded and the
   discarded mass `τ`, renormalization gives `‖o_all − o_route‖ ≤ 2 V_max τ`. Measure compression
   discrepancy and discarded mass, then test whether they predict the observed rate effects — and
   measure forecast changes under targeted interventions, because an attention-output bound alone does
   not establish predictive importance. The reviewer labels this a proposed diagnostic, not a novelty
   claim.

## What already holds

- Three mechanistic synthetic families exist (known-period sinusoids, change-points, delayed-copy) at
  five paired seeds, and the exact-recall probes are where compression loses, which is the paper's
  sharpest negative result.
- The smoothness correlation is reported with its p-value and explicitly labelled descriptive.
- The paper states that the mechanism is unverified and does not claim a filtration reading.

## What is left

- [ ] Build the three controlled generators with independent knobs (bandwidth, noise, event width, lag,
      alignment, compression rate) and pre-register the predictions before running.
- [ ] Add the beyond-MSE measurements: signal distortion and noise attenuation, per-horizon error, recall
      error on recoverable channels, selected-block coverage of the target event, localization error.
- [ ] Add a specified linear filter (for example a fixed moving average at the same output block count)
      and measure the learned compressor's empirical response against it; then either make the filtering
      statement with evidence or drop it.
- [ ] Implement the discrepancy/mass diagnostic for one or two cells and test whether it predicts the
      rate effects; report the result even if it does not.
- [ ] Add targeted interventions (forcing a specific block set, removing the top-1 selected block) and
      measure the forecast change.
- [ ] Rewrite §4.3 around the controlled results, keeping the negative results.

## Acceptance

At least one controlled signal property predicts a rate effect with an interval, or the paper reports
the negative result; the filter comparison replaces the unmeasured filtering language; and every
mechanism sentence in the discussion points at a measurement rather than an interpretation.

## Cost breakdown

Generators and analysis code ≈8–12 h; runs are single-seed and cheap (each synthetic family is small),
so most of the cost is implementation and writing rather than compute.

## Evidence pointers

- `plan/gates/gate3/gate3_datasets.py` (synthetic generators currently in use)
- `plan/gates/gate12/gate12_mechanistic.py` (existing probe harness, currently single-seed)
- `paper/sections/experiments.tex` §4.3 (mechanism probes), `paper/sections/discussion.tex` (candidate explanations)

## Log

- 2026-10-16: created. This area was missing from the first version of this folder and was added after
  checking the review's minimum package against the tracker.
