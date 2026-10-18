# R2 — Mechanism-matched dense baseline (same projection ranks)

**Status:** DONE (2026-10-17) · **Cost:** ~6 h wall (25 seeds under machine load) · **Depends:** nothing
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

- [x] Add a `Normal-rank64` variant — done (`gate27_r2matched/run.py`, one variable: attn `o_lora_rank`
      128 → 64; every other attribute copied from `model.NormalTimeSeriesModel`). `--dry-run` asserts
      Δ = 40,960 params, all in `o_a_proj`/`o_b_proj`, everything outside attention identical, and all
      four compressed cells at o=64.
- [x] Trained on the frozen protocol, 25 paired seeds, new manifest `results/normal_r64.jsonl`
      (append-only; historical manifests untouched). Smoke passed; equality gate for the last-query path
      passes (7e-7).
- [x] Compared against Normal and the four cells with paired intervals (`analysis.json` / `.md`):
      Normal-r64 − Normal val −0.048 [−0.088, −0.008]; each cell − Normal-r64 val: CSA −0.176, DRRA
      −0.172, C48 −0.110, C88 −0.178, every interval excluding zero, 21–25/25 seeds.
- [x] Headline decision — the predeclared rule returned **KEEP for all four cells**: matching the
      projection makes the dense model *better* (not worse), so the as-run Normal was not a conservative
      reference, and the accuracy advantage is not a projection artifact. The claim is stated against
      the matched baseline in §4.3/§4.6, the abstract and the conclusion.
- [x] Frontier figure — a fourth (open) marker added to both panels of Figure 6, placed at
      loss 1.0251 (same five seeds) and latencies anchored to the released Normal by a same-run
      four-model round-robin probe (`latency_probe.py`, `latency_4model.json`: FULL ratio 0.951,
      LAST 1.034; the released-three reproduction is 1.03–1.09 on FULL and a uniform ~1.17 on LAST
      under load, which the same-run ratio absorbs).

## Acceptance

- [x] Matched baseline row beside Normal in both accuracy tables (Table 3 as-run vs matched with Δ
      columns; Table 2 factorial), on the Figure 6 frontier, and the efficiency claims name their
      source (§4.3, §4.6, abstract, conclusion, Appendix D + audit table).

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
- 2026-10-17: **R2 COMPLETE.** 25/25 seeds (last finished 00:26Z); `analysis.py` applied the frozen
  rule → **all four cells KEEP at the matched projection**. Means (val): CSA 0.6148, C88 0.6128, DRRA
  0.6190, C48 0.6810, Normal-r64 0.7910, Normal 0.8389. Key paired intervals (val): cell − Normal-r64
  CSA −0.1762 [−0.2174, −0.1349], DRRA −0.1720 [−0.2150, −0.1290], C48 −0.1100 [−0.1486, −0.0713],
  C88 −0.1782 [−0.2219, −0.1344]; Normal-r64 − Normal −0.0480 [−0.0881, −0.0078]. Read: the rank-128
  projection was overfitting on ETTh1, so matching it *helps* the dense model — the accuracy gap is not
  a projection artifact. Landed: Table 2 and Table 3 rows, §4.3 and §4.6 attribution text, abstract
  clause, conclusion, Appendix D note + audit-table row, Figure 6 fourth marker. `verify_manuscript.py`
  0 failures; 31 pp clean.
- 2026-10-17 (audit pass): verified the landing is complete and consistent — §4.3 opening now names
  the matched row, the data-integrity paragraph registers the separate 25-run manifest, §4.6 states the
  matched comparisons are robustness analyses (not additional confirmatory tests) and corrects the
  pre-existing mislabel "five pre-registered cell-vs-Normal contrasts" (the five include DRRA-vs-CSA),
  and `paper/README.md`'s provenance map gains rows for this gate (and the R4/R5/R1/accounting artefacts
  that were missing). Full-text check of the PDF: `verify_manuscript.py` 0 failures, 0 unresolved refs,
  31 pp; the matched numbers appear in exactly the intended places (0.7910 ×4, 0.0649/1.0281 ×2,
  0.2975 ×1, −0.110/−0.178 ×3, 21–25 ×2).
- 2026-10-17 (final audit): two more fixes from the number cross-check — Table 3's caption claimed
  percentages were computed on the 4-decimal means while the table (all rows, pre-existing) uses the
  underlying means; the caption now states the actual rule and the Normal-r64 test delta is −4.85% (was
  −4.84%, the only row that had followed the stale rule). Appendix D now prints the matched account
  (76.86M → 66.38M) so the 7.8% is traceable inside the paper. Evidence logs for the three new gates
  (R5, R4, R2: run/tests/comparison/analysis) were force-added to git under the `*.log` ignore rule, as
  the paper's "released logs" claims require; historical gate logs stay as they were.
- 2026-10-17 (language pass): proofread every inserted passage as rendered — abstract now defines the
  treatment in words ("a dense retrain whose output projection is matched to the compressed cells'
  rank") instead of using the undefined compound "projection-matched"; fixed a self-reference inside
  §4.6 ("the comparisons of Section 4.6" → "reported below"); "wider" → "higher-rank"; intro's
  limitations clause re-attached to the claim; appendix "retrained too" → "trained end to end, not
  merely re-accounted"; §4.1 manifest sentence rewritten; figure caption anchoring phrased for readers.
