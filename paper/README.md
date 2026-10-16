# Paper — Decoupling Compression and Routing in Attention for Time-Series Forecasting

Workshop-length draft (NeurIPS-style layout) of the DRRA two-axis design
study. **Status: complete draft.** Gates 2–5 (factorial, 12-dataset
coverage, minimal statistics, dev-machine systems) done; **Gate15 v2 DONE**
(factorial 75 re-runs under fixed mapping + suite-Flat 60, merged to 25 paired seeds: compressed>full attention is
Holm-significant, p <= 3.3e-6; H1 decoupling supported, exact p = 0.0074, interaction p = 0.014);
**Gate 6 DONE** (external reference points: DLinear ×12 datasets, PatchTST
×8, frozen protocol; anchors-not-peers framing). Learning-curve figure
(fig4) retained from the pre-registered-seed runs.

## Project layout

```
paper/
  main.tex                entry point; preamble + document skeleton
  neurips_2026.sty        self-contained layout fallback (see below)
  sections/
    abstract.tex          abstract
    introduction.tex      framing + contributions (a)–(d) + non-claims
    related_work.tex      verified citations only; C2 flagged
    method.tex            frozen task, family, compressor/router, factorial
    experiments.tex       RQ1 factorial, RQ2 vs Normal, efficiency
    discussion.tex        decoupling insight, limitations, non-claims
    conclusion.tex
    appendix.tex          negative results, surrogate, reproducibility, roadmap
  references.bib          16 entries, all verified against the arXiv API
  figures/                regenerable figures (see scripts/)
  scripts/
    make_figures.py       reads the audited JSONL manifests and draws figures
```

## Getting it into Overleaf

1. Create a new Overleaf project **from the "NeurIPS 2026" template**
   (template gallery) — this gives you the official `neurips_2026.sty`.
2. Upload/replace `main.tex`, the `sections/` and `figures/` folders, and
   `references.bib`.
3. Compile: `pdflatex` → `bibtex` → `pdflatex` → `pdflatex` (Overleaf does
   this automatically with the "pdfLaTeX" compiler).

**Style file note:** `neurips_2026.sty` in this folder is a minimal,
self-contained *fallback* that reproduces the NeurIPS look (single column,
10pt Times, 1in margins, natbib author–year). It exists so the project can
be compiled anywhere; before submission, replace it with the official style
file from Overleaf's NeurIPS template. The preamble of `main.tex` is
written to match the official template, so the swap requires no content
changes.

## Number provenance (every number in the paper)

| Paper number | Source of truth |
|---|---|
| Factorial cell means/stds/trains (Table 1), main effects, per-seed consistency, 25-seed stats (Section stats), RQ2 deltas (Table 2) | `plan/gates/gate2/gate2_results.jsonl` + `plan/gates/gate7_seeds/results/gate7.jsonl` + `plan/gates/baseline/baseline_normal_results.jsonl` (25-seed merge, audited) |
| Cross-dataset table (tab:coverage), Figure data (fig6/7/8/9) | `plan/gates/gate3/results/*.jsonl` + latency JSONs, recomputed by `scripts/make_figures.py` — the script prints verification lines against the audited summaries |
| External reference points (tab:refpoints) | `plan/gates/gate6_baselines/results/*.jsonl` (DLinear ×12, PatchTST ×8, 5 paired seeds; audited by `gate6_audit.py`; facts in `gate6_facts.json`) |
| Protocol details (window 16, top-k 16, ranks 64/64, AdamW, seeds) | `plan/gates/gate2/gate2_design.md` §2, `plan/benchmark_protocol.md` |
| Scaling forecast + energy projection (§4.8, App. D, `fig12_scaling_forecast`) | `paper/scripts/make_figures.py --scaling` reads `plan/gates/gate5/gate5_results.json`; asserts exact equality with the released per-component MAC accounts at L=256; prints the anchor/sensitivity tables used in the text |

Derived numbers used in the abstract/intro that are **not** in the audited
summaries verbatim (computed from the audited JSONL manifests, verified by
the figure script's printout):
- all 4 compressed cells beat Normal in 95/100 paired seed comparisons
  (CSA 24, DRRA 24, C48 22, C88 25);
- mean validation deltas -18.8% (4,8) to -27.0% (8,8); per-seed range
  −48.3% to +9.9%;
- test-delta range -18.82% (4,4) to -21.89% (8,4); v2 sources: `plan/gates/gate15_rerun/gate15_analysis.json`, `gate16_d3`, `gate17_e2` (+`gate17_speed`), `gate18_d5`, `gate19_324`.

## Honesty checklist (mirrors plan/paper_notes.md §3)

The draft must never claim: a novel sparse-attention mechanism; SOTA
forecasting accuracy; statistical equivalence ("statistically identical");
subquadratic complexity beyond structural column counts; "zero-accuracy-
cost"; IID samples. All pre-freeze pilot numbers (val ~0.11, 1.32× speed,
22.42 ms, −33.8% vs Flat) are **superseded** and must not appear as results
— grep the draft for `superseded` to confirm they are only referenced as
excluded. The pre-freeze speed/latency figures were removed from the
pre-paper drafts (`RESULTS.md`, `WRITEUP.md`, `PUBLICATION.md`) on
2026-08-18 (`plan/paper_notes.md` §4); original measurements live only in
`experiment-session-new-attention.md`.

The scaling/energy material (§4.8, App. D) is a **model-based projection
from arithmetic counts, never a measurement**: the headline saving is
coefficient-free under a uniform work-proportional energy model; write
"projected", not "measured energy"; no joules; the latency validation is
directional and single-machine.

## TODO inventory (before submission)

Run `grep -n "TODO:" sections/` (and `NEEDS VERIFICATION`) to see every
marker. Summary:

- **Citations:** C2 "to our knowledge" verified 2026-08-16 via the
  2024–2026 sweep (plan/mini_tasks/c2/2026-08-16-c2-lit-sweep.md + plan/mini_tasks/c2/c2_sweep_log.md)
  — no counterexample found; re-run before submission; FAR and ModernTCN
  entries stay commented out in `references.bib` until verified. Dataset
  sourcing verified 2026-09-01 (lai2018lstnet, wu2021autoformer).
- **Gate 3: datasets DONE 2026-08-25** — 12 datasets × 3 variants × 5 seeds
  = 180 runs under the frozen protocol (`plan/gates/gate3/gate3_summary.md`,
  E-audited; RESULTS.md "Dataset Coverage (Gate 3)"; paper §RQ3 +
  Fig. 6). Remaining from §6: horizons/lookbacks grid. External baselines
  (DLinear, PatchTST under the frozen protocol) = Gate 6, in progress
  2026-09-01 (`plan/gates/gate6_baselines/`; iTransformer/Informer/TimesNet
  remain roadmap item 3).
- **Gate 4: minimal pass DONE 2026-08-25** — per-dataset exact paired
  Wilcoxon + Holm, cross-dataset sign tests, bootstrap CIs on the mean
  Δval (`plan/gates/gate4/gate4_stats.md`); nothing survives correction at
  n=5 (floor p=0.0625) and the paper says so. Mixed-effects/HAC/TOST
  deferred with written justification (no equivalence claims; seed-level
  analysis).
- **Gate 5: dev-machine systems measurements DONE 2026-08-27** — mean/p90/p99
  latency + bootstrap CIs, throughput, batch scaling 1–256, lookback scaling
  128–4096, analytic MACs, peak memory, training time
  (`plan/gates/gate5/gate5_summary.md`). Skipped by decision (no hardware /
  out of design-study scope): cross-hardware (Linux x86, GPU) and
  depth/width ablations — future work, not pre-submission blockers.
- **Housekeeping:** real author names/affiliations, official .sty, remove
  all `\todo`/`\needverify` markers, freeze-clean package (lockfile, hashes,
  CI tests).

## Regenerating figures

```bash
cd paper
python3 scripts/make_figures.py    # needs matplotlib + numpy
```

The scaling forecast is standalone (it reads the audited systems JSON and
asserts exact equality with the released component accounts at L=256
before drawing):

```bash
cd paper
python3 scripts/make_figures.py --scaling
```

Outputs PDF+PNG into `figures/`. The script cross-checks every derived
number against `plan/gates/gate2/gate2_summary.md` / `plan/gates/baseline/baseline_normal_summary.md`
and prints the results.
