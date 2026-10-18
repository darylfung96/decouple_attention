# Gate 28 — C1 all-block compression control (design, frozen pre-run)

**Frozen:** 2026-10-17, before the first seed. Owned by the C1 task file
(`pre-publication_v2_tasks/C1_controls.md`); this file is the run contract.

## Question

Is the indexer's **selection** doing work, or is compression alone enough? The control keeps the
compressors, the local window, the head and the projection ranks of the routed cell and removes only the
selection: every index token is selected (`k = n_idx`), which `_postprocess_topk` maps to every safe KV
block.

## Cells (one variable per cell)

| Control | Reference cell | Changed variable | Unchanged |
|---|---|---|---|
| `C1(4,4)` | `Flat` = `(c_KV=4, c_R=4)` | `index_topk`: 16 → 64 (= `n_idx`) | compressors, window 16, ranks, head, readout |
| `C1(8,4)` | `DRRA` = `(c_KV=8, c_R=4)` | `index_topk`: 16 → 64 (= `n_idx`) | same |

`n_idx = usable // index_compress_rate` with `usable = (L // c_KV) · c_KV`, `L = 256` → `n_idx = 64` for
both cells. `c_R = 4` in both, so the index geometry equals the reference cell's and the only difference
is the selection set size.

**No new parameters.** The control is the reference cell's `EPPTimeSeriesModel` with one attribute
changed after construction; the dry run asserts `state_dict` equality bitwise at a fixed seed and equal
attention / full-model parameter counts. MACs are also identical to the reference cell, because
`_attend` computes densely over every compressed column and the selection enters only as a mask
(`block_bias.scatter_`). The control therefore asks an accuracy question at equal compute; it does not
claim a latency change.

## Protocol (unchanged from the factorial manifest)

ETTh1, frozen direct-96 task (lookback 256 → horizon 96), 10 epochs, batch 32, AdamW lr 1e-4 / wd 1e-5 /
clip 10.0, epoch-10 weights, validation = test = last 25%, loaders and training loop imported from
`plan/gates/gate2/gate2_factorial.py` and `plan/gates/gate3/gate3_harness.py`. Same fixed 25 paired seeds,
so every control seed pairs with the reference cell's seed.

## Artifacts

- `results/allblock.jsonl` — new manifest, append-only, one row per (control, seed). Every row records
  `index_topk` (= 64), `n_idx` (= 64), the realized mean safe-block count per query position, and the
  provenance tag `gate28/uv-torch2.6.0/c1-allblock`.
- `run.py --dry-run` — asserts: single variable (bitwise-equal `state_dict`s, equal parameter counts),
  `k = n_idx = 64`, and, on one real validation batch, that the realized selected-block set equals the
  brute-force safe set `{b : b·c_KV + c_KV − 1 <= q}` for every query position, with the routed cell's set
  a strict subset wherever fewer blocks are safe than exist.
- `analysis.py` — paired comparisons of each control against its routed reference cell on the same 25
  seeds (t-interval, relative difference, exact Wilcoxon), plus the branch below.

## D5 margin and branch rule (pre-registered)

`margin = 2%` relative validation MSE, the plan's suggested anchor, applied per cell to
`d = (MSE_control − MSE_reference) / MSE_reference` (positive = routing helps). The margin is read from the
D5 freeze-log line in `pre-publication_v2_tasks/DECISIONS.md`; `analysis.py` refuses to run while D5 is
unfrozen and refuses if the frozen value differs from the one coded here.

### Precision measured before the run (this is why the margin is not the primary output)

On the six existing cell pairs at n=25, the paired relative half-width is **5.3–7.7%** (paired
SD 0.079–0.116 on means near 0.62), i.e. the study resolves differences of roughly 6%, not 2%. A 2%
containment test can only pass if the control and its routed reference have seed-correlation
`>= 0.91`; the same-family cell pairs measure 0.11–0.18. A 3% test needs `>= 0.80`; a 6% test needs
`>= 0.19`.

Accordingly the **primary output is a bound**: the 95% upper limit `U` on the relative accuracy cost of
removing routing. The margin supplies labels, not the headline, and a wide interval is reported as a
bound rather than converted into a verdict. A 6% margin would sit at the study's own resolution limit
and would also contradict the paper's reading of the 5.72% matched-dense difference as meaningful, so it
is rejected.

### Pre-registered secondary test

All-block versus Normal on the same 25 seeds (a large effect, §4.3): if the paired 95% interval's upper
bound is below zero, compression without routing reproduces the paper's headline advantage and the story
does not depend on the selector.

| Outcome (both cells unless noted) | Reading | Paper action |
|---|---|---|
| `d ≥ margin` and the 95% interval's lower bound `> margin` | routing adds accuracy beyond the margin | none; the paper's attribution stands |
| the whole 95% interval lies inside `(−margin, margin)` | all-block is non-inferior: compression suffices | boundary result → retitle per D4 (b) and add the control to §4.6 |
| point estimate inside the margin but the interval is wider | within the margin, not resolvable at n=25 | report `U` as the bound; no retitle |
| `d ≤ −margin` and the interval's upper bound `< −margin` | the router costs accuracy | report plainly; retitle per D4 (b) |
| interval straddles a margin edge | indeterminate at this margin | report as indeterminate; no claim, no retitle |

Mixed outcomes across the two cells are reported as mixed: routing is necessary at the rate where it is,
and the paper says so per cell. Equivalence is declared only on interval containment; a non-significant
test is reported as indeterminate at this margin, never as equivalence.

## What this run cannot show

- A mask-exploiting kernel's latency: the implementation computes every compressed column regardless of
  the mask, so realized columns are reported as a property of the selection, not as saved work.
- Anything about `(4,8)`/`(8,8)`: they are outside the kept cells and not run.
- Anything about a trained indexer: parked by D3 unless this control says routing matters.
