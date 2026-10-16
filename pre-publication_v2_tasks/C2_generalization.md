# C2 — Generalization matrix: datasets, horizons, lookbacks, backbones

**Status:** TODO · **Cost:** tens of CPU hours · **Depends:** C1 (mechanism) for the interpretation

**Verdict:** PARKED — scope, not a defect. The paper already has 12 datasets, 25 paired seeds and a cross-dataset replication.
**Start when:** a referee asks for a longer lookback or a second horizon; the admissible response is one lookback on two datasets, not this matrix.
**Never started speculatively.**

**Source:** Q1 review §5 "Expand along dimensions that can change the conclusion" (PDF p. 6; lines 274–326), the dimension table (lines 286–311) and "Keep token axes and data protocols explicit" (line 317).

## What the review asked

Two evaluation tracks, kept separate. The **mechanism track** holds the backbone, normalization,
prediction head and optimization recipe fixed while changing compression, routing and budget controls.
The **practical forecasting track** compares complete systems with validation-selected settings and
equal, disclosed tuning budgets. Then: start with ETTh1, ETTh2, Electricity and Exchange and treat the
rest as broader validation; add horizons 96, 336 and 720 on a planned subset; add lookback 1024 for raw
temporal tokens with patch settings chosen by their actual token count; add one competent multilayer
temporal or patch backbone beside the minimal model; and predefine the confirmatory seed count and the
temporal holdouts before running, so the seed count is not expanded until a threshold is reached. Keep
the token axes explicit: iTransformer operates over variate tokens, so it is a system comparator, not a
module replacement, unless a separate hypothesis is stated. Add a clearly separated standard-benchmark
protocol alongside the frozen 60/20/20 split, with identical forecast origins, target channels,
information availability and train-only scaling within a track, and a fresh temporal holdout (previously
inspected test periods cannot become unseen by renaming the endpoint).

## What already holds

- Twelve datasets at five seeds each, three of them mechanistic synthetics, with the ETTh1 factorial at
  25 seeds; the cross-dataset pattern is reported descriptively and the frozen split is documented.
- The PatchTST transfer partly covers the "competent backbone" item (see R7 for its saturation limit).
- The paper states the limitations the matrix would remove, so nothing here is hidden.

## What is left

- [ ] **Horizons.** Add H = 336 and 720 on a planned subset (the harness supports the horizon as a
      constant; the cost grows with the head size only).
- [ ] **Lookback.** Add L = 1024 for the raw-token backbone, which also moves the appendix scaling
      forecast's frozen anchor.
- [ ] **Backbone.** One competent multilayer backbone (the PatchTST transfer, once R7 is fixed, or a
      multilayer version of the study's own block).
- [ ] **Protocol.** Write the standard-benchmark protocol next to the frozen split, with the shared
      origins and scaling rules, and predefine the confirmatory seeds and holdouts in a design file
      before any run.
- [ ] **Replication discipline.** Predefine the seed count; do not extend to significance. The paper
      already carries the disclosure that the 25-seed ETTh1 set is a planned merge of 5 pre-registered
      seeds with a 20-seed power extension.
- [ ] **iTransformer note.** If added, state the token-axis difference explicitly and use it as a system
      comparator.

## Acceptance

At least one horizon and one lookback beyond the frozen pair, on at least two datasets, with the
mechanism and practical tracks never mixed in the same table, and a design file that predates the runs.

## Cost breakdown

One run at L=256 costs about 8 minutes on the development machine; L=1024 grows roughly linearly in the
attention terms and dominates for dense cells, so budget 4–6× per run at the longer lookback. A
horizon-only sweep is cheap (the head grows, the encoder does not). The full matrix is tens of hours.

## Evidence pointers

- `plan/gates/gate2/gate2_factorial.py` (frozen protocol, horizon and lookback constants)
- `plan/gates/gate3/` (the twelve-dataset suite and its per-dataset manifests)
- `paper/sections/experiments.tex` §4.4 external reference points (the current calibration rows)
- `paper/sections/appendix.tex` future-work items (the deferred scope, already listed)

## Log

- 2026-10-16: created from the review's "expand along dimensions that can change the conclusion".
