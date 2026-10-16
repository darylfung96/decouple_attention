# R2 — Mechanism-matched dense baseline (same projection ranks)

**Status:** PARTIAL (claim fixed, experiment missing) · **Cost:** 3–4 h · **Depends:** nothing
**Blocks:** the "every headline improvement is attributable" submission condition

**Verdict:** KEEP — the last accounting confound on the main headline.
**Start when:** Phase 3, immediately; nothing blocks it. If R6 is done first, the matched row lands on the new frontier in the same pass.
**Trigger to reopen after closing:** no.

**Source:** Q1 review §1 (PDF p. 2), item "R2. Separate attention savings from projection savings" (line 92); the submission condition it ends with is line 106.

## What the review asked

The dense baseline carries a rank-128 output projection and the compressed cells carry a rank-64
bottleneck. Table 9 (now Table 10) charges these 20.97M and 10.49M MACs, so 10.48M of the 17.23M MAC
saving is the projection alone. The reviewer's accounting gives a projection-matched advantage of about
10% instead of the 22% headline at the time. He asked for a mechanism-matched dense baseline with the
same projection ranks, normalization, positional treatment and compatible sink treatment, keeping the
original Normal model as an as-run reference, and for every headline improvement to state which source
it comes from: compression, routing, changed projections, the prediction head, or an implementation
choice.

## What the paper now says

- §4.6 states the three numbers explicitly: 20.4% whole-model MAC saving, 7.8% when the projection ranks
  are matched, 30.9% on the attention path with the attention core falling 80.9%.
- Appendix D names the projection asymmetry as 10.49M of the 15.66M gap and repeats the matched figure.
- The conclusion carries the matched pair, so no reader sees the 20.4% without the 7.8% beside it.

This is a disclosure fix. It computes what the reviewer's sensitivity calculation computes; it does
**not** retrain the baseline, so it cannot say whether the compressed cells still beat a dense model
whose projection was made equal.

## What is left

- [ ] Add a `Normal-rank64` variant: identical to the as-run Normal except the output projection uses
      the compressed cells' rank 64 (and any other rank that the equalization contract touches), with
      the same normalization, positional treatment and sink handling.
- [ ] Train it on the frozen protocol with the same 25 paired seeds and the same harness
      (`plan/gates/gate2/gate2_factorial.py`), writing a new manifest, never editing old ones.
- [ ] Compare it against Normal and the four factorial cells on validation and test MSE, and report the
      paired per-seed differences with intervals.
- [ ] Decide what happens to the headline if the matched baseline closes part of the gap: the sentence
      "every compressed cell beats full attention" must then be stated against the matched baseline, or
      the claim is narrowed to the attention path.
- [ ] Add the variant to the accuracy-versus-cost frontier when R6 rebuilds Figure 6.

## Acceptance

A row for the projection-matched dense baseline appears beside Normal in the accuracy tables and the
frontier figure, and every efficiency claim in the abstract, §4.6 and the conclusion names its source.

## Cost breakdown

25 runs × ≈8 min ≈ 3.5 h on the development machine, plus about 30 minutes of code and writing. No GPU.

## Evidence pointers

- `paper/sections/experiments.tex` §4.6; `paper/sections/appendix.tex` operation-counts paragraph
- `paper/scripts/make_figures.py` (`rest_exact`, `o_proj` with `o_rank` 128 vs 64)
- `plan/gates/gate2/gate2_factorial.py` (training harness and parameter counting)

## Log

- 2026-10-16: created. Disclosure done; retrain not started.
- 2026-10-16: **Phase 3 in flight.** Design frozen pre-run (`plan/gates/gate27_r2matched/design.md`:
  one variable = attn `o_lora_rank` 128 → 64, everything else copied from `model.NormalTimeSeriesModel`;
  expected params 61,536 / 314,240, Δ = 40,960 all in the O path). `run.py --dry-run` asserts the single
  variable and the equalization contract (all four compressed cells at o=64); `--smoke` trains both
  variants once on bounded subsets. Full run launched 2026-10-16T18:34Z: 25 paired seeds →
  `results/normal_r64.jsonl` (new manifest only; ~4 h). `analysis.py` frozen with the run: paired
  intervals for `Normal_r64 − Normal`, `cell − Normal_r64` (primary), `cell − Normal` (reference), the
  predeclared KEEP/NARROW decision per cell, and the MAC self-check (20.4% / 7.8%).
  First seed (42) validated at 18:58Z: val 0.7610 / test 0.9988 — the matched baseline is far stronger
  than the as-run Normal (val 0.9656 / test 1.2605 on the same seed) at equal train MSE (~0.29), i.e. the
  rank-128 projection was overfitting; this is exactly the outcome the predeclared rule was written for.
  Cost reality: ~24 min/seed under concurrent machine load (the old 8 min/seed figure assumed an idle
  machine), so the 25-seed run is ~8–10 h; it appends per seed and is idempotent across restarts.
