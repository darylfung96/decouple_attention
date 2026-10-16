# L — Q1 review triage (manager's 2026-10-16 email + PDF)

Status: IN PROGRESS (L-1 DONE, L-2 DONE; L-3/L-4 are manager decisions)
Source: `Q1_Journal_Technical_Review_and_Revision_Plan.pdf` (12 pp, 2026-10-16, review of a
27-page `NewTransformer.pdf`) plus the accompanying email (Information Sciences as an
alternative target, with MEAformer and PMformer suggested as comparators).
Owner files touched this pass: `paper/sections/{experiments,appendix,abstract,introduction,method,discussion,conclusion}.tex`,
`paper/scripts/make_figures.py`, `plan/gates/gate20_accounting/`, `plan/gates/gate19_324/MANIFEST_NOTE.md`,
`pre-publication-tasks/K_scaling_energy.md`.

## The short answer

Of the review's eight P0 items, three were already fixed in the draft the manager saw
(last-query reframing, the off-diagonal disclosure for H1, the stale-checkpoint disclosure);
three were real wording or scope defects, which are now fixed; two were real numerical
defects, which are now fixed and propagated. Everything else in the PDF is a research
program that needs new training runs, and it belongs to a venue decision, not to a revision
pass: the bounded paper is sound as it stands, and the extra runs buy ambition, not validity.

## Item-by-item against the current draft

| Review item | Status in the draft | What this pass did |
|---|---|---|
| R1 interaction interpretation | **Partly real.** The printed numbers were never wrong, but the §4.2 sentence said coarsening KV "helps more when routing is fine" and the abstract and discussion read the routing main effect as a general rule. Both are wrong readings: the interaction is carried by the (4,8) cell, and at `c_KV=8` the finer router adds nothing (0.6128 coarse vs 0.6190 fine on the mean). | Fixed, including the review's sub-requirement of per-seed intervals: the four conditional effects now carry paired 95% CIs and exact Wilcoxon p-values from the unrounded seed matrix (`plan/gates/gate21_simple_effects/`): KV at fine routing +0.0042 [−0.044, +0.052], p=0.62; KV at coarse routing −0.0682 [−0.101, −0.036], p=0.0001; routing at fine content +0.0662 [+0.027, +0.106], p=0.002; routing at coarse content −0.0062 [−0.048, +0.035], p=1.0. Abstract, introduction and discussion say the finding is conditional, and Figure 2 is now an interaction plot with a main-effects panel. |
| R2 attention vs projection savings | **Real.** The rank-128 dense output projection vs the rank-64 compressed bottleneck was disclosed in App. D but never quantified, so the "22% fewer MACs" headline misattributed the saving. | Fixed: the output projection is 10.49M of the 15.66M whole-model gap (66.9%); matching the ranks leaves 7.8% whole-model against 30.9% on the attention path (core −80.9%). §4.6, App. D and the conclusion all state both figures. A projection-matched retrain is deferred (it is a new baseline, not a text fix). |
| R3 fixed top-k is not a fixed budget | **Real limitation, now stated.** The draft disclosed the unique-block counts (≈14/64 vs ≈10/32) but not that the `c_KV` contrast therefore changes realized coverage. | Fixed: §4.2 now says the KV main effect is a statement about the configuration (content density at a fixed selection count), not about matched realized coverage, and points at the deferral. Budget-matched and coverage-matched controls remain deferred. |
| R4 "routing fixed at initialization" | **Real overclaim.** Zero task gradient does not make the route constant, because the index scores come from trainable upstream features. The gradient audit only shows gradient isolation. | Fixed in all four places (abstract, method, discussion limits, audit table): "no learning signal reaches the selector; route membership still follows the drift of upstream features". Route-overlap probes remain deferred. |
| R5 stale mechanism probes | **Already disclosed.** The draft says probes (i)–(ii) predate the mapping correction and are kept as as-run historical values. The causality evidence has a scope limit that the draft did not state: the perturbation suite runs at the frozen geometry, and the per-cell mapping regression covers future-safety per rate pair, but index-score-masking and tie-breaking probes at every rate pair are not run. | No re-run. App. D now states the coverage limit explicitly; regenerating the two probes stays deferred (two runs, but the paragraph already reads as history). |
| R6 forecast-required cost | **Already done.** The draft leads with the audit and reports the reviewer's own ranges (Normal 2.6–3.9 ms vs compressed 5.8–9.5 ms) and states that efficiency claims are made against the last-query baseline. | No change beyond the numbers that moved with the accounting fix. |
| R7 PatchTST transfer routes? | **Real and previously undisclosed.** With 31 patch tokens and `k=4`, the `c_R=8` cells have 3 candidates and select all of them, and the `c_R=4` cells select 4 of 6–7. | Fixed: App. C and §4.5 now report the token geometry and say the tie bounds the transfer test from below instead of showing that routing washes out on strong backbones. A `k=4`/longer-token rerun is deferred. |
| R8 accounting (softmax columns, `h_I`, `d_I`) | **Real defect (the most serious).** The router term charged one head per index-token comparison; the executed matmul is `[B,H,S,d_h] × [B,1,d_h,M]`, so the true cost is `h·d_h = d = 128` MACs per pair, four times the charge. Separately, the (32,4) softmax-column cell read "16+1" where the code's `L/c_KV + W + 1` gives 24+1. | Fixed: `plan/gates/gate20_accounting/` audits the shapes and republishes the accounts (CSA 61.72→63.30M, DRRA 59.63→61.20M). Every dependent number moved: router 0.52→2.10M, `W_C` router term `d_h L²/c_R → d L²/c_R`, `S∞ = 1 − (1/c_KV + 1/(2c_R))`, frozen-context savings 18.4/30.9/37.1/40.2%, asymptotes 62.5/75.0/81.2/84.4%, whole-model 20.4% (matched 7.8%), whole-layer d=128 50.5% at L=2048, `ρ=1.000/0.992`. Figures 12–13 regenerated; §4.6, §4.8, App. D, conclusion, abstract updated. One side effect of the fix is reported honestly: the measured end-to-end saving now exceeds the arithmetic projection at both anchors (56.2 vs 50.5; 63.3 vs 60.8), which the memory-bound dense baseline explains. |

Reviews' P1 items (decisive controls, multi-horizon/lookback, extra backbones, GPU timing,
energy measurement, held-out selection guide, MEAformer/PMformer comparators) are all
**new runs**. None of them is a correction, and the paper already carries them as the
appendix future-work list, so nothing in this pass depends on them.

## What is deferred, and what it would cost

| Deferred item | Why it is deferred | Cost |
|---|---|---|
| All-block compressed control (compression with no router) | This is the review's decisive control and our own cheapest one: the attention core is already dense-masked over all compressed columns, so the control is a retrain, not a kernel. | ≈7 h (2 `c_KV` values × 25 seeds on ETTh1 at the measured 8 min/run). |
| Projection-matched dense baseline | Removes the last accounting confound the review names. | ≈3–4 h (25 seeds). |
| Other controls: window-only, random/recent/even selection, mean pooling, trained indexer | Each answers a mechanism question the current paper leaves as interpretation. | ≈20–30 h for the set, in the review's suggested order. |
| Budget-matched selection (R3) and coverage-matched sensitivity | Needs a new selector filling rule plus its own runs. | ≈10 h plus a design decision on the aggregation rule. |
| Multi-horizon (96/336/720) and lookback 1024 | Generalization of the factorial; the harness supports it. | tens of hours (the 12-dataset suite is the breadth substitute today). |
| GPU/second-platform timing, energy measurement | Different hardware and instrumentation; the paper claims neither. | not estimated here. |
| MEAformer, PMformer comparators (email) | Needs faithful third-party implementations under the frozen protocol plus per-model tuning budgets; the review itself warns that identical optimizers are not a fair best-achievable comparison. | days of engineering plus GPU time. |

Total for the "Neurocomputing/Information Sciences" package the review describes: roughly the
30–50 CPU hours already flagged as Q-1, plus the external-baseline engineering. That is the
venue decision the manager is asking for, not a revision.

## Handover notes for the next session

- The three artifacts a reviewer will check first are all in place: the accounting audit
  (`plan/gates/gate20_accounting/router_accounting_audit.{py,json,md}`), the interaction figure
  (`paper/figures/fig2_main_effects.*`, now two panels), and the PatchTST token geometry
  (App. C paragraph). The fourth, added after the first pass, is the per-seed conditional-effect
  audit (`plan/gates/gate21_simple_effects/`), which supplies the intervals the review's R1 asked for.
- `make_figures.py` now asserts against the gate20 accounts; the old gate5 numbers are
  superseded for the router row only. Do not "fix" gate5_results.json — it is the historical record.
- Anything that quotes MAC savings must quote the matched-projection pair (20.4% whole-model,
  7.8% projection-matched, 30.9% attention path), never the old 22%.
- Still not run, in the order the review ranks them: projection-matched dense baseline (R2),
  budget/coverage-matched selection (R3), route-overlap probe (R4), causality coverage probes (R5),
  PatchTST re-run at k=4 or a longer token series (R7).
