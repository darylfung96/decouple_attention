# R8 — Accounting: router term, (32,4) columns, recomputed totals

**Status:** DONE (2026-10-16) · **Cost:** none remaining, 0.5 h optional strengthening ·
**Depends:** nothing

**Verdict:** DONE — nothing to start.
**Start when:** never reopened unless a new configuration is added to the accounting table.

**Source:** Q1 review §3 (PDF p. 4), item "R8. Reconcile the remaining accounting before extrapolation" (line 188).

## What the review asked

Three things. (1) Table 1 lists 17 softmax columns for (32,4), but the table's own formula
`C + W + 1` gives `256/32 + 16 + 1 = 25`; check whether the table or the window changed. (2) Expose the
number `h_I` and the dimension `d_I` of the scoring heads, because the dot-product routing term is
generally `h_I · d_I · N_Q · (L/c_R)`, and Equation 2 assumes a particular head arrangement that needs
tensor-shape verification. (3) Recompute every affected total and scaling curve afterwards, noting that
matching one script to another script that shares its assumptions is not independent validation.

## What was found and fixed

Both defects were real, and the head question exposed a third.

| Finding | Before | After |
|---|---|---|
| (32,4) softmax columns | 16 + 1 = 17 (inconsistent with the table's own formula) | 24 + 1 = 25, matching `L/c_KV + W + 1` and the executed module |
| Router arithmetic | Charged one head per (query, index-token) comparison, 0.52M MACs per sequence | Every head of the shared query scores every index token, `h·d_h = d = 128` MACs per pair, 2.10M per sequence |
| Compressed totals at L=256 | CSA 61.72M, DRRA 59.63M | CSA 63.30M, DRRA 61.20M |

Everything derived from those totals moved with them: the router term in Equation 2 became `d L²/c_R`;
the asymptotic saving became `S∞ = 1 − (1/c_KV + 1/(2c_R))`; the frozen-context savings became
18.4 / 30.9 / 37.1 / 40.2% and the asymptotes 62.5 / 75.0 / 81.2 / 84.4%; the whole-model saving became
20.4% (7.8% projection-matched); the whole-layer saving at d=128 became 50.5% at L=2048 and 60.8% at
L=4096; the auxiliary-weighting band became 81.1 / 74.7 / 61.9%; and the latency rank correlation became
ρ = 1.000 at batch 32 and 0.992 at batch 1. Figures 8 and 9 and Table 8 were regenerated; Tables 10 and
11, §4.6, §4.8, Appendix D, the conclusion and the abstract were updated.

The head disclosure the reviewer wanted is now in the paper in plain form: the routing query is the main
multi-head query and the index stream is single-headed, so the score matmul runs at
`[B, H, S, d_h] × [B, 1, d_h, M]` and costs `h d_h = d = 128` MACs per pair — which is `h_I = h = 4` and
`d_I = d_h = 32` in his notation.

## Evidence

- `plan/gates/gate20_accounting/router_accounting_audit.py` runs the real module for all six cells,
  records every matmul's operand and result shapes, asserts the analytic arithmetic against those shapes,
  and writes the corrected accounts plus every derived number to `router_accounting_audit.{json,md}`.
- `paper/scripts/make_figures.py` now asserts its totals against the gate20 audit before drawing, so a
  future drift fails loudly instead of silently redrawing.
- `paper/main.pdf` (31 pp) and `paper/scripts/verify_manuscript.py` (0 failures).

## What is left

Optional, and it answers the reviewer's independence point rather than a defect:

- [ ] Add an independent FLOP count for one or two cells using a profiler counter
      (`torch.utils.flop_counter.FlopCounterMode`) and check it against the analytic total, so the
      arithmetic rests on three methods (analytic formula, executed tensor shapes, profiler) rather than
      two. The earlier benchmark noted that `torch.profiler` returned empty input shapes on this build,
      so use the FLOP counter instead. About 30 minutes.

## Acceptance

Met. The accounts match the executed shapes, the (32,4) row is consistent with the formula and the code,
and no derived number in the paper rests on the superseded charge.

## Log

- 2026-10-16: closed. Audit run, accounts republished, all derived numbers and figures updated.
