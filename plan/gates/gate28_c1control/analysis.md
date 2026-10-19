# Gate 28 — C1 all-block compression control: analysis

D5 margin: **2.0%** relative validation MSE (freeze row: | 2026-10-18 | D5 | **2% relative validation MSE for the label, with the bound as the primary output** — the label applies per cell to (MSE_ctrl − MSE_ref)/MSE_ref; non-inferiority is declared only on interval containment, and the 95% upper limit U on the relative cost of removing routing is reported as the headline whatever the label says | the anchor is decision-relevant (~1/10 of the 19–27% headline) and strict relative to the paper's own reading of the 5.72% matched-dense difference; the pre-run precision check shows n=25 resolves ~6% (paired half-widths 5.3–7.7%, a 2% test would need seed-correlation ≥ 0.91), so a binary verdict at 2% is pre-declared unavailable rather than manufactured | Daryl (delegated; investigated recommendation) |)

| Comparison | control val MSE | Δ MSE [95% CI] | Δ rel [95% CI] | Wilcoxon p | all-block better | branch |
|---|---|---|---|---|---|---|
| C1(4,4) vs CSA | 0.7727 | +0.1579 [+0.1125, +0.2034] | +27.09% [+18.87%, +35.30%] | 1.192e-07 | 1/25 | routed_better |
| C1(8,4) vs DRRA | 0.6857 | +0.0667 [+0.0206, +0.1128] | +11.82% [+4.58%, +19.07%] | 0.001453 | 5/25 | routed_better |

**Overall: routing_confirmed** — routing pays for itself beyond the margin; no paper change beyond reporting the control.

Primary bound: removing routing costs at most **35.3%** relative validation MSE (95% upper limit, worst cell).

Pre-registered secondary test (all-block vs Normal): C1(4,4) -0.0662 [-0.1122, -0.0201], 18/25; C1(8,4) -0.1532 [-0.2031, -0.1033], 24/25 — compression alone reproduces the headline advantage.

Equivalence is declared only on interval containment inside the margin; a non-significant test is reported as indeterminate, never as equivalence. At n=25 the empirical paired resolution is 5.3-7.7% relative, so a 2% criterion is usually unavailable and the bound is the deliverable.

Realized selection: C1(4,4) 31.75 of 64 blocks per query (routed reference: 9.91 of 32 for (8,4), 13.94 of 64 for (4,4) on the dry-run batch); C1(8,4) 15.62 of 32 blocks per query (routed reference: 9.91 of 32 for (8,4), 13.94 of 64 for (4,4) on the dry-run batch).

Note: MACs and parameters are identical to the reference cells; the control changes which blocks are unmasked, not the work performed.
