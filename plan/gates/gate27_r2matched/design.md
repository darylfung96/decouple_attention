# Gate 27 — R2: projection-matched dense baseline (design, frozen pre-run)

**Frozen:** 2026-10-16, before any training. Owner: `pre-publication_v2_tasks/R2_projection_matched_baseline.md`
(Phase 3 recipe: `pre-publication_v2_tasks/RUNBOOK.md` §"Phase 3 recipe").
**Rule:** one variable vs the as-run Normal baseline — the output-projection rank. Nothing else changes.

## Question

The dense baseline carries a rank-128 output projection (`o_lora_rank=128`) while every compressed cell
carries rank 64; the published MAC accounting charges that asymmetry as 10.49M of the 15.66M whole-model
gap (the headline 20.4% whole-model saving becomes 7.8% at matched projection). The reviewer asked
whether the compressed cells' **accuracy** advantage also depends on that projection. This run trains
the matched baseline so the question is answered by measurement, not by arithmetic.

## Variant definition (the one variable)

`Normal_r64` = the as-run Normal model (`model.NormalTimeSeriesModel`) with exactly one change:
`NormalAttention.o_lora_rank` 128 → 64. Everything else is copied verbatim:

| attribute | as-run Normal | Normal_r64 | compressed cells |
|---|---|---|---|
| q_lora_rank | 64 | 64 | 64 |
| o_lora_rank | 128 | **64** | 64 |
| o_groups / num_heads / head_dim | 4 / 4 / 32 | 4 / 4 / 32 | 4 / 4 / 32 |
| sliding_window / index_topk | 32 / 16 | 32 / 16 | 32 / 16 |
| compressor / indexer modules | none | none | present (the design under test) |
| encoder stack, head, init, protocol | identical | identical | identical |

Normalization (LayerNorm placement, RMS over head dim inside attention), positional treatment
(learned `pos_embedding` added on the input; RoPE inside attention as built), and sink handling are
untouched because no other module is touched. The as-run Normal model and its 25 released rows are kept
as the as-run reference; no historical manifest is edited.

## Expected parameter counts (asserted in `--dry-run`, not assumed)

- as-run Normal: attn 102,496 · full 355,200 (matches `plan/gates/gate0/gate0_registry.json`).
- Normal_r64: attn 61,536 · full 314,240.
- Δ = 40,960, located entirely in `o_a_proj` (16,384 → 8,192) and `o_b_proj` (65,536 → 32,768).

## Protocol (identical to the v2 matrix cells)

Same harness as the compressed rows: `gate2_factorial.make_loaders` (seed applied before model init and
before data loading, exactly as `gate15_run.py` does) + `gate3_harness.train_and_eval` (AdamW lr 1e-4,
wd 1e-5, clip 10.0, 10 epochs fixed, batch 32, ETTh1, threads 8). Seeds: the fixed 25 paired seeds
`42 123 2024 7 99 1 2 3 4 5 6 8 9 10 11 12 13 14 15 16 17 18 19 20 21`.

**New manifest only:** `plan/gates/gate27_r2matched/results/normal_r64.jsonl` (append-only, idempotent,
provenance `gate27/uv-torch2.6.0/r2-projection-matched`). Historical manifests and gate outputs untouched.

Cost: 25 runs × ≈8 min ≈ 3.5 h, CPU, no GPU.

## Analysis plan (frozen)

Primary metric: validation MSE; secondary: test MSE. Paired per-seed differences (n = 25) with 95%
t-intervals, Wilcoxon signed-rank p and sign consistency, same estimator as
`gate15_rerun/gate15_analyze.py::est`.

1. `Normal_r64 − Normal` — the projection's own effect on the dense model.
2. `cell − Normal_r64` for each of the four factorial cells — the design effect at matched projection.
3. `cell − Normal` (legacy) — the published headline, recomputed as a reference row.

MAC context (same accounting as the paper): at L = 256 per sequence, as-run Normal 76.86M,
Normal_r64 66.38M, (8,4) 61.20M — i.e. the matched comparison isolates 7.8% (not 20.4%) whole-model
saving before accuracy is considered. `analysis.py` asserts these published percentages as its
self-check.

## Predeclared decision rule

For each compressed cell independently:

- **Interval for (cell − Normal_r64) entirely below 0** → the accuracy claim holds against the
  projection-matched dense baseline; the paper states the matched comparison as the primary accuracy
  statement and keeps the as-run Normal only as the released reference.
- **Interval includes 0 or is positive** → the claim for that cell is narrowed to the attention path
  (where the MAC saving is exact and projector-free) and the text says so explicitly; no sentence may
  state "beats full attention" for that cell without the matched baseline beside it.

Either branch is a publishable outcome; the rule above fixes the text in advance.

## Landing plan (after the run)

§4.6 (attribution sentence), the accuracy table (matched row beside Normal), Figure 6 (matched row on
the frontier — the R6 residual), and the abstract/conclusion efficiency sentences naming their source.

## Log

- 2026-10-16: created and frozen before the first training run. No results yet.
