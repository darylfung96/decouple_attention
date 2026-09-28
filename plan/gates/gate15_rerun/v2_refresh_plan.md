# V2 refresh plan — where Gate15's new numbers propagate (written 2026-09-28, executes after Gate15 completes)

Scope rule: ONLY rows from misrouted cells change — factorial (4,4)/(4,8)/(8,8),
suite Flat. Kept everywhere: (8,4)/DRRA, Normal, DLinear, PatchTST.
Old manifests are never modified; v2 reads old-kept + gate15-new rows.

## A. New analysis outputs (v2, all in `plan/gates/gate15_rerun/`)

- A-1 `gate15_analysis.json/md`: merged 25-seed factorial (new 44/48/88 + kept 84/Normal)
  with the FULL C-1 estimate set (cell means/stds/train-means, Beats-CSA, best-of-four,
  beats-Normal, KV/RT/interaction + CIs + exact tests, H1 + tests, DRRA−CSA val AND test).
- A-2 `suite_flat_v2.json/md`: merged 12-dataset suite (new Flat + kept DRRA/Normal):
  per-dataset means, bold markers, x/12 counts, DRRA-vs-Flat + Flat-vs-Normal exact tests,
  bootstrap CI on mean Δval (Flat), sign tests, Tab:refpoints Flat column.
- A-3 `c1_recompute` v2 run (extend script with v2 merge) + `gate4_stats` rerun on merged
  suite inputs (output to gate15 dir; gate4 outputs untouched).
- A-4 per-epoch curves parsed from `gate15_run.log` → `curves_v2.json` (for fig4 regen;
  the driver prints per-epoch train/val lines; no separate curve logging exists).

## B. Paper updates (`paper/sections/`)

Factorial (experiments.tex RQ1 + stats):
- B-1 `Tab:factorial`: (4,4)/(4,8)/(8,8) rows (val mean±std, test mean, train mean,
  Beats-CSA). Normal + DRRA rows kept.
- B-2 RQ1 prose: worst-cell identity + value; "every compressed cell beats" x/25s;
  96/100 roll-up; 17-vs-13 sentence family (head-to-head vs best-of-four, val).
- B-3 Main-effects paragraph: KV/RT means + CIs + 19/25s (recompute — may move).
- B-4 H1 paragraph: contrast mean + exact p-values (may cross 0.05 — see decision D-1).
- B-5 Interaction sentence (currently ns −0.0262 — recompute).
- B-6 fig1/fig2/fig3 captions + figures (see C).
RQ2 + stats:
- B-7 RQ2 prose + `Tab:baseline` CSA row (means, Δs, x/25) + wiring § (unchanged).
- B-8 Stats §: H1 p, DRRA-vs-CSA val (p + counts) AND test (currently p<1e-4 — the
  old test-side edge is partly mapping artifact; expect shrinkage), cell-vs-Normal
  Holm p's, best-of-four counts, merge-provenance sentence (extend with gate15).
Suite (RQ3 + refpoints + stats):
- B-9 `Tab:coverage` Flat row (12 means) + bold markers + "7/12" count + RQ3 prose
  win/loss lists touching CSA + bootstrap CI (Flat) + sign tests.
- B-10 Per-dataset exact tests: Flat-vs-Normal and DRRA-vs-Flat rows (suite stats §).
- B-11 `Tab:refpoints` Flat column (12 numbers; anchors + Normal + DRRA kept).
- B-12 Inversion paragraph (I-4): sSin/sDC one-sided p's involve Flat — recompute.
Front/back matter:
- B-13 abstract findings 2 (effect sizes + H1 p) and 4 (x/12 CSA).
- B-14 intro contribution (b) (effects + H1 p + DRRA-vs-CSA p).
- B-15 conclusion ¶1 (same numbers).
- B-16 discussion §5.1 (effects, H1 p, interaction, DRRA-vs-CSA p) + H2 accuracy leg.
- B-17 appendix repro: add gate15 results + v2 analysis to artifact list.
- B-18 `paper/README.md` traceability: gate15 + v2 mapping.

## C. Figures to regenerate (`paper/scripts/make_figures.py` needs a v2 input mode)

- fig1_factorial_val, fig2_main_effects, fig3 per-seed coords (factorial cells).
- fig4_learning_curves (from A-4 curves JSON; old png is gate2-era).
- fig6_dataset_coverage (Flat row), fig9_perf_speed (ETTh1 test means incl. CSA).
- fig5 (schematic, (8,4)-drawn — KEEP, unaffected).
- fig7/fig8 latency — KEEP with one-line justification (mapping changes VALUES not
  compute: `_attend` stays dense over identical column sets, so wall-clock is
  unaffected in expectation; no re-measurement needed).

## D. Explicitly NOT updated (with reason, to preempt confusion)

- `Tab:configs` params + MACs (geometry/counts unchanged by mapping fix).
- `Tab:speed` + L-scale numbers (compute-identical; see C).
- (8,4)/DRRA + Normal + DLinear + PatchTST rows everywhere (verified unaffected).
- gate2/gate3/gate4/gate7 manifests (frozen as-run history; v2 lives in gate15).
- gate12 Flat-checkpoint probes (separate flagged rerun; H-scope, needs new checkpoints).

## E. Decision checkpoint (before B-4/B-8 text is finalized)

- D-1: if v2 H1 or DRRA-vs-CSA cross significance lines in EITHER direction, the
  surrounding claims (title lock stands regardless — it promises decoupling as a
  study, not a direction) get reworded; manager reviews v2 JSON before text edits.
- D-2: v2 text pass waits for Q-2 (router disclosure) so both confounds land in one edit.

## F. Acceptance

- Every B-item traces to a v2 JSON value; `grep` sweep (5.3/champion/7-10/stale-p)
  re-run clean; braces/$ balanced; figure PDFs regenerated from v2 inputs only.
