# Baseline — what is already done before these v2 tasks (pass of 2026-10-16)

This file is the record that the v2 tasks build on. Read it first: several review items are already
closed in the manuscript, so their task files list only what is genuinely left.

## Trigger

The manager sent a 12-page technical review plus an email proposing Information Sciences. The review's
P0 list has eight items (R1–R8). Three of them were already satisfied in the draft he read, four were
claim or scope defects, and two were real arithmetic defects. The pass below fixed the six live ones.
No model was retrained; every accuracy number in the paper is unchanged.

## The two arithmetic fixes

| # | Defect | Was | Now | Evidence |
|---|---|---|---|---|
| 1 | The router cost was counted for one head; the module scores each index token with every head of the shared query | Router 0.52M MACs/seq; totals 61.72M / 59.63M; whole-model saving 22%; frozen attention-path saving 40.2%; DRRA asymptote 84.4% | Router 2.10M; totals 63.30M / 61.20M; saving 20.4% (7.8% projection-matched); path saving 30.9%; asymptote 75.0% | `plan/gates/gate20_accounting/router_accounting_audit.{py,json,md}` — a tensor-shape audit of the executed module, all six cells |
| 2 | The (32,4) exploratory row printed the wrong softmax-column count | 16 + 1 = 17 columns | 24 + 1 = 25 columns, which is what `L/c_KV + W + 1` gives and what the code does | `paper/sections/method.tex:235` |

## The four claim fixes

1. **Interaction direction.** The factorial section said coarsening KV "helps more when routing is fine";
   the numbers say the opposite. It now reports the four conditional effects with paired per-seed 95%
   intervals and exact Wilcoxon p-values, and the abstract, introduction and discussion state the
   finding conditionally. Source: `plan/gates/gate21_simple_effects/`.
2. **"Routing is fixed at initialization".** A zero gradient proves no learning signal reaches the
   indexer, not that the selected set never moves. All four places now say the indexer receives no task
   gradient, that the audit shows gradient isolation rather than route constancy, and that route
   membership follows upstream feature drift.
3. **"A strong backbone washes out routing".** In the PatchTST transfer the series becomes 31 patch
   tokens, so the coarse-router cells select every candidate index token. The appendix and §4.5 now
   report that geometry and say the tie bounds the transfer claim from below.
4. **Efficiency headline.** The dense baseline uses a rank-128 output projection and the compressed
   cells use rank 64, which is 10.49M of the 15.66M whole-model MAC gap. The paper now states all three
   figures (20.4% whole-model, 7.8% projection-matched, 30.9% attention path) in §4.6, Appendix D and
   the conclusion.

## New artifacts created in this pass

| Artifact | What it holds |
|---|---|
| `plan/gates/gate20_accounting/` | The executed-matmul shape audit and the corrected per-component accounts with every derived number (savings table, whole-layer projections, sensitivity bands, energy composition, latency-rank validation). |
| `plan/gates/gate21_simple_effects/` | The four conditional effects with paired 95% intervals, Wilcoxon p-values and sign consistency; cross-checked to reproduce the published main effects and interaction exactly. |
| `plan/gates/gate19_324/MANIFEST_NOTE.md` | Explains that the shipped (32,4) rows carry a stale `cell` label while their values are correctly attributed by parameter count; the driver now writes the right label for future runs. |
| `../pre-publication-tasks/L_q1_review_triage.md` | Item-by-item triage of the review against the draft, including what was already done and what stays deferred. |
| this folder | The v2 program (R1–R8 and C1–C4). |

## Figure and table map (file name is not the printed number)

This caused confusion once, so it is written down: LaTeX numbers figures in order of appearance, and
the file names carry older numbers.

| Printed number | File name | What it is |
|---|---|---|
| Figure 2 | `fig1_factorial_val.pdf` | factorial cell means with seed points |
| Figure 3 | `fig2_main_effects.pdf` | conditional effects (left) and main effects (right) |
| Figure 8 | `fig12_scaling_forecast.pdf` | structural scaling forecast, four panels |
| Figure 9 | `fig13_energy_composition.pdf` | per-token work-to-energy composition at L=2048 |
| Table 1 | `method.tex` | configuration geometry and parameters |
| Table 8 | `experiments.tex` | attention-path savings versus context |
| Table 10 | `appendix.tex` | forward component accounts at L=256 |
| Table 11 | `appendix.tex` | verification-audit outcomes |

## Canonical numbers after this pass (use these, never the superseded ones)

- Per-component MACs at L=256, per sequence: Normal 76.86M, CSA 63.30M, DRRA 61.20M. Router 2.10M,
  attention core 3.21M, compressors 6.29M for DRRA.
- Whole-model saving: DRRA 20.4%, CSA 17.6%, projection-matched 7.8%, attention path 30.9%,
  attention core 80.9%.
- Attention-path savings versus dense (percent), cells (4,4)/(8,4)/(16,4)/(32,4):
  L=256: 18.4 / 30.9 / 37.1 / 40.2; L=32768: 62.2 / 74.7 / 80.9 / 84.0; asymptote: 62.5 / 75.0 / 81.2 / 84.4.
- Whole-layer saving for the study backbone (d=128): 50.5% at L=2048, 60.8% at L=4096.
- Sensitivity at 32k for DRRA: auxiliary weight ×0.5 → 81.1%, ×1 → 74.7%, ×2 → 61.9%.
- Conditional effects on ETTh1 (validation MSE, 25 paired seeds): KV at fine routing +0.0042
  [−0.044, +0.052]; KV at coarse routing −0.0682 [−0.101, −0.036]; routing at fine content +0.0662
  [+0.027, +0.106]; routing at coarse content −0.0062 [−0.048, +0.035].

## State of the manuscript

31 pages, compiles clean (no overfull boxes, no undefined references), and
`paper/scripts/verify_manuscript.py` reports zero failures. The data-driven figures were regenerated
from `make_figures.py --v2`, which now asserts its accounting against the gate20 audit before drawing.

## How to reproduce this pass

```
~/.uv_env/py311/bin/python plan/gates/gate20_accounting/router_accounting_audit.py
~/.uv_env/py311/bin/python plan/gates/gate21_simple_effects/simple_effects.py
cd paper && ~/.uv_env/py311/bin/python scripts/make_figures.py --v2
cd paper && ../tectonic -X compile main.tex
~/.uv_env/py311/bin/python paper/scripts/verify_manuscript.py
```
