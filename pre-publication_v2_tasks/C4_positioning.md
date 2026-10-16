# C4 — Positioning, related work, figure logic and the selection guide

**Status:** TODO · **Cost:** 1–2 days of writing plus one held-out validation · **Depends:** C1/R2 for the
strengthened claim, D4 for the title

**Verdict:** PARTIAL KEEP — only the MoBA paragraph is kept; the selection guide and the validation study stay parked.
**Start when:** Phase 2, in any writing slot. About 30 min.
**Title change (D4)** is a separate decision, taken only after C1 reports.

**Source:** Q1 review §8 "Reframe the manuscript around a useful conditional finding" (PDF p. 9; lines 437–480): "Recommended title and contribution" (line 439), "Update the closest-work comparison substantively" (line 446), "Replace the principal figures" (line 456).

## What the review asked

Keep the two-axis design study as the paper's identity, and reframe the contribution as an explanation
supported by controlled comparisons and meaningful execution costs rather than a claim to have invented
the mechanisms. Replace repeated defensive scope statements with a compact limitations section. Update
the closest-work comparison substantively: MoBA varies block granularity while adjusting top-k to hold
sparsity constant, so the independently compressed content stream and the realized-budget controls need
explicit discussion; Native Sparse Attention already distinguishes compression from selection blocks, so
separating the granularities is not unprecedented; The Sparse Frontier emphasizes task- and
execution-stage-dependent trade-offs, so the opportunity is a forecasting-specific explanatory study,
not another sparse-attention leaderboard. Identify the (4,4) cell as an equal-rate configuration rather
than a full DeepSeek reproduction, with the training, window, score and implementation differences
stated. Rebuild the principal figures around execution geometry, interaction effects, matched controls,
a mechanistic map and an accuracy-resource frontier, and order the results as identification, mechanism,
generalization, practical value. Move development history, stale experiments, unrelated surrogate work
and purely extrapolated energy calculations out of the central narrative, while keeping negative results
that are still informative. For reuse: release the controls and synthetic tests as a documented
benchmark, and validate a selection guide on held-out cases, reporting its regret relative to the best
tested configuration including failures. The recommended title is
*"When Does Compressed Attention Help Time-Series Forecasting? Separating Compression, Routing, and Computational Cost"*.

## What already holds

- The design-study identity, the pre-registered contrasts, the negative results (synthetic probes,
  exchange-rate validation, weather test error), the surrogate thread already moved to an appendix item,
  and the disclosure that the (4,4) cell adopts DeepSeek's rate point without equivalence (the name
  marks the configuration).
- Native Sparse Attention and The Sparse Frontier are already discussed in the related-work section, and
  the paper already states that no prior work it knows of varies the two axes independently.
- The limitations section is already compact and itemized.

## What is left

- [x] **Add MoBA** to the related-work discussion (block granularity with top-k adjusted to hold sparsity
      constant) and contrast it with the independently compressed content stream and the realized-budget
      controls. Done 2026-10-16: `paper/sections/related_work.tex` §2.1 (new paragraph naming
      \citep{lu2025moba}, verified 2026-10-16 against the arXiv listing; `paper/references.bib`),
      contrasting (i) raw-cache blocks vs.\ our separately compressed index stream, (ii) joint block
      size/$k$ reporting vs.\ our fixed top-$k$ (pointing at §4.8's realized-budget readings), and
      (iii) MoBA's trained selection pathway vs.\ our gradient-free indexer. Rebuilt clean; 31 pp.
- [ ] **D4 — decide the title** and, if adopted, update the running title, abstract framing and file
      headers. The current title is locked in `../pre-publication-tasks/00_title.md`.
- [ ] **Figure logic.** The review's five-figure plan maps onto the current set as: execution geometry
      (Figure 1, done), interaction effects (Figure 3, done), matched controls (does not exist until R2
      and C1 run), mechanistic map (Figure 4 and the probes, partial), accuracy-resource frontier
      (Figure 6, currently full-layer — R6 fixes this).
- [ ] **Compact the defensive scope statements** once the controls land, replacing repeated disclaimers
      with the compact limitations section.
- [ ] **Selection guide.** Fit a small rule that maps signal properties, token geometry and realized
      budget to the recommended configuration, then validate it on held-out cases: report accuracy
      relative to the best tested configuration on those cases (regret) including the failures.
- [ ] **Documented benchmark.** Package the controls and the synthetic generators as a small,
      documented benchmark with a one-command run, which is what makes the paper citable beyond its own
      result.

## Acceptance

The related-work comparison names MoBA and states the difference in one paragraph; the figure set
contains a matched-controls figure and a deployment-relevant frontier; and a selection guide is validated
on held-out cases with regret reported, or the guide is dropped and the claim stays descriptive.

## Evidence pointers

- `paper/sections/related_work.tex` (NSA, Sparse Frontier, DeepSeek-V4, MLA already covered)
- `paper/sections/discussion.tex` "What this paper does not claim" and the limitations list
- `paper/sections/appendix.tex` future-work items, including the documentable benchmark idea
- `../pre-publication-tasks/00_title.md` (the locked current title)

## Log

- 2026-10-16: created from the review's positioning section and the manager's email.
- 2026-10-16: MoBA paragraph landed in §2.1 with the bib entry (kept scope complete). The title (D4),
  figure logic (R2/C1 pending), scope compaction, selection guide and benchmark packaging remain
  parked per the verdict.
