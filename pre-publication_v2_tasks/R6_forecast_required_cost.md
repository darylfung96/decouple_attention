# R6 — Forecast-required cost as the headline efficiency view

**Status:** PARTIAL (measurements exist, the main figure still uses the full-layer path) ·
**Cost:** 0.5–1 h of figure and text work · **Depends:** nothing

**Verdict:** KEEP — one figure stands between the paper and the reviewer's reporting standard.
**Start when:** Phase 2, after R5 (so the figure quotes settled numbers). Data already exists; no runs.
**Ships with:** the R2 matched row on the same frontier if Phase 3 has landed.

**Source:** Q1 review §3 "Use the forecast-required path and nondegenerate routing" (PDF p. 4; lines 159–196), item "R6. Make optimized forecasting cost the primary comparison" (line 161).

## What the review asked

The last-query audit in the draft reports the dense baseline as faster than the compressed cells under
forecast-required accounting (Normal 2.6–3.9 ms against compressed 5.8–9.5 ms per batch-32 pass), which
reverses the full-layer ranking. That comparison must lead the efficiency results and the
accuracy-latency frontier. He asked to report full-layer timings separately from forecast-required
timings, to optimize every comparator legitimately, and to replace the frontier figure with the
deployment-relevant one.

## What the paper now says

The audit is in §4.7 with both paths reported, the reversal is stated in plain words, and the efficiency
claims are explicitly made against the last-query baseline. The measurements themselves come from
`plan/gates/gate13_p0_audits/last_query_latency.json` (equivalence verified to about 5×10⁻⁷).

What the review's last sentence has not been done: **Figure 6** (`fig9_perf_speed.pdf`) plots mean test
loss against **full-layer** forward latency at batch 32 and batch 256. The deployment-relevant graph is
the forecast-required path, which is currently a table row rather than the frontier.

## What is left

- [x] Rebuild Figure 6 with forecast-required latency on the x-axis as the primary panel, keeping the
      full-layer frontier as a second, clearly labelled panel (both at batch 32, from the same audited
      gate13 run; batch 256 full-layer numbers remain in Table speed). Done 2026-10-16:
      `paper/scripts/make_figures.py` (fig9 block now reads
      `plan/gates/gate13_p0_audits/last_query_latency.json`), regenerated
      `paper/figures/fig9_perf_speed.pdf/.png` via `make_figures.py --v2`;
      printed check `perf-speed: ... LAST32 {Normal 2.62, (4,4) 6.18, (8,4) 5.82} | FULL32 {Normal 40.73, (4,4) 36.96, (8,4) 31.74}`.
- [x] Point the §4.7 synthesis and the deployment reading in the conclusion at the new figure, and keep
      one sentence that says the full-layer view is retained because it is the honest comparison for
      architectures whose head needs all temporal positions. Done 2026-10-16:
      `paper/sections/experiments.tex` §4.7 "Combined performance--speed view" paragraph and the
      Figure 6 caption rewritten; `paper/sections/conclusion.tex` deployment paragraph now cites
      Figure~\ref{fig:perf-speed}. `verify_manuscript.py` passes (0 failures); rebuild clean (31 pp).
- [ ] If R2 lands, put the projection-matched dense baseline on the same frontier. (Pending Phase 3.)

## Acceptance

The paper's efficiency figure answers "what does one forecast cost", not "what does a full forward pass
cost", and no sentence claims per-forecast efficiency from full-layer numbers.

## Cost breakdown

Figure code and caption ≈30 min; text edits ≈15 min. No runs.

## Evidence pointers

- `plan/gates/gate13_p0_audits/last_query_latency.json` (forecast-required numbers, unique blocks)
- `paper/sections/experiments.tex` §4.7 and the Figure 6 caption
- `paper/scripts/make_figures.py` `make_fig9`-equivalent block (performance versus speed)

## Log

- 2026-10-16: created. Reporting gap identified: both paths are in the text, the frontier figure is not.
- 2026-10-16: DONE (own scope). Figure 6 rebuilt with the forecast-required (last-query) path as the
  primary panel and the full-layer path as a labelled comparison, both from the released gate13 audit
  (single run, batch 32); §4.7 paragraph and caption rewritten so the accounting reversal leads and
  the full-layer view is retained only for heads that need all temporal outputs; conclusion deployment
  paragraph cites the figure. Evidence: `paper/scripts/make_figures.py` (fig9 block),
  `paper/figures/fig9_perf_speed.pdf/.png`, `paper/sections/experiments.tex` §4.7 + caption,
  `paper/sections/conclusion.tex`, `verify_manuscript.py` 0 failures, clean rebuild. The R2 matched row
  on the frontier stays open as a Phase 3 landing step (tracked there, not here).
- 2026-10-19 (verification): two corrections. (i) The paired figure $-5.2\pm0.9$ ms was DRRA$-$CSA, not CSA$-$Normal; CSA$-$Normal is $-3.8\pm1.6$ ms (gate13 log). Both are now stated with their comparanda. (ii) The drift claim "level shifts 6--9% between runs" was not supported by the paper's own runs (Normal measures 40.7, 42.0 and 52.5 ms across the three logged sessions); replaced with those three levels. Last-query ranges narrowed to the two runs whose JSON ships (Normal 2.6--3.0, CSA 6.2--7.3, DRRA 5.8--6.8 ms; ~17% session gap) because the wider range's upper values came from a contended run whose output file was overwritten during the A-2 rerun. "bit-exact ~5e-7" replaced by the measured bound $\le7.2\times10^{-7}$.

