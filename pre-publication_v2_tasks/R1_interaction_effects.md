# R1 — Interaction effects: conditional reading, figure, per-seed intervals

**Status:** DONE (2026-10-16) · **Cost:** none remaining · **Depends:** nothing

**Verdict:** DONE — nothing to start.
**Start when:** never reopened unless the interaction figure or the per-seed intervals change.

**Source:** Q1 review §1 "Correct the statistical interpretation and baseline attribution" (PDF p. 2; `source/q1_review_text.txt` lines 58–108), item "R1. Interpret the interaction using simple effects" (line 60); the mean-reading table is lines 67–83.

## What the review asked

The factorial section said coarsening KV compression helps more when routing is fine, and Table 2 shows
the reverse. The reviewer computed the four conditional effects from the table means and concluded that
the interaction is carried by the poor (4,8) cell, that at `c_KV=8` the finer router does not improve the
mean, and that H1 is algebraically the off-diagonal difference `y(4,8) − y(8,4)` and therefore not
independent confirmation. He asked for an interaction plot as the main factorial figure, for the
conditional effects to be reported, and for their paired intervals to be recomputed from unrounded seed
data, because differences of printed means do not establish significance.

## What the paper now says

- §4.2 reports the interaction (−0.0724, 95% CI [−0.129, −0.016], p = 0.014) and then the four
  conditional effects with per-seed paired 95% intervals and exact Wilcoxon p-values: KV at fine routing
  +0.0042 [−0.044, +0.052], p = 0.62; KV at coarse routing −0.0682 [−0.101, −0.036], p = 0.0001;
  routing at fine content +0.0662 [+0.027, +0.106], p = 0.002; routing at coarse content −0.0062
  [−0.048, +0.035], p = 1.0. It states that the interaction is carried by the (4,8) cell and that the
  main effects are not available as general mechanism statements.
- **Figure 3** (`fig2_main_effects.pdf`) was rebuilt: the left panel plots the four cells as two lines
  joined across the KV rate, so the interaction is visible, and the right panel keeps the two main
  effects with the seed-noise band.
- The abstract, the introduction's contribution (b) and the discussion all state the finding
  conditionally rather than as a rule about routing.
- The H1 paragraph already disclosed that H1 is the off-diagonal contrast and carries no independent
  information, which the reviewer asked to make explicit.

## What is left

Nothing blocking. Two optional polish items, both writing only:

- [ ] State the cross-dataset reversal as a research question in the introduction rather than as a
      limitation. The paper already frames the study around signal dependence (RQ3 and contribution (b)),
      so this is a wording choice, not missing content.
- [ ] If the C2 generalization matrix runs, re-estimate the conditional effects per dataset and add
      them to the coverage table.

## Acceptance

Met: a reader can see the conditional result in the figure and read its uncertainty from the text, and
no part of the paper claims that fine routing is generally better.

## Evidence

- `plan/gates/gate21_simple_effects/simple_effects.{py,json,md}` (intervals, cross-checks)
- `paper/sections/experiments.tex` §4.2, Figure 3 caption
- `paper/sections/abstract.tex`, `introduction.tex`, `discussion.tex`

## Log

- 2026-10-16: closed. Text, figure and intervals in place; intervals reproduce the published main
  effects and interaction exactly (KV −0.0320, routing +0.0300, interaction −0.0724).
