# Paper — Dual-Rate Routed Attention for Efficient Long-Horizon Time-Series Forecasting

Workshop-length draft (NeurIPS-style layout) of the DRRA two-axis design
study. **Status: first full draft from current evidence; all statistics are
descriptive (5 seeds, ETTh1 only); Gates 3–5 (datasets, significance,
hardware) are marked as `TODO:` in the text.**

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
  references.bib          10 entries, all verified against the arXiv API
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
| Cell means/stds/trains (Table 1), main effects, per-seed consistency, 3-way table (Table 2), params (Table 3) | `plan/gates/gate2/gate2_summary.md`, `plan/gates/baseline/baseline_normal_summary.md`, `plan/gates/gate2/gate2_design.md`, `plan/gates/gate0/gate0_registry.json` (audited) |
| Figure data (all figures) | `plan/gates/gate2/gate2_results.jsonl` + `plan/gates/baseline/baseline_normal_results.jsonl`, recomputed by `scripts/make_figures.py` — the script prints verification lines against the audited summaries |
| Learning curves (fig 4) | `plan/gates/gate2/gate2_learning_curves.png` (copied) |
| Protocol details (window 16, top-k 16, ranks 64/64, AdamW, seeds) | `plan/gates/gate2/gate2_design.md` §2, `plan/benchmark_protocol.md` |

Derived numbers used in the abstract/intro that are **not** in the audited
summaries verbatim (computed from the audited JSONL manifests, verified by
the figure script's printout):
- all 4 cells beat Normal in 20/20 paired seed comparisons (docs only
  formalized 5/5 for (4,4) and (8,4));
- validation-delta range −18.5% (4,8) to −29.1% (8,4);
- test-delta range −15.3% (8,8) to −26.1% (8,4).

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

## TODO inventory (before submission)

Run `grep -n "TODO:" sections/` (and `NEEDS VERIFICATION`) to see every
marker. Summary:

- **Citations:** C2 "to our knowledge" verified 2026-08-16 via the
  2024–2026 sweep (plan/mini_tasks/c2/2026-08-16-c2-lit-sweep.md + plan/mini_tasks/c2/c2_sweep_log.md)
  — no counterexample found; re-run before submission; FAR and ModernTCN
  entries stay commented out in `references.bib` until verified.
- **Gate 3:** datasets (ETTh2/ETTm1/ETTm2, Electricity, Traffic, Weather,
  Exchange), horizons/lookbacks, external baselines (PatchTST, iTransformer,
  DLinear, Informer, TimesNet, linear/SSM).
- **Gate 4:** significance — mixed-effects model (β₂ > β₁ claim), TOST/ROPE,
  paired Wilcoxon/Friedman + Holm, block bootstrap/HAC for temporal
  dependence.
- **Gate 5:** latency p50/p90/p99 + bootstrap CIs, FLOPs/memory, scaling
  sweeps, cross-hardware.
- **Housekeeping:** real author names/affiliations, official .sty, remove
  all `\todo`/`\needverify` markers, freeze-clean package (lockfile, hashes,
  CI tests).

## Regenerating figures

```bash
cd paper
python3 scripts/make_figures.py    # needs matplotlib + numpy
```

Outputs PDF+PNG into `figures/`. The script cross-checks every derived
number against `plan/gates/gate2/gate2_summary.md` / `plan/gates/baseline/baseline_normal_summary.md`
and prints the results.
