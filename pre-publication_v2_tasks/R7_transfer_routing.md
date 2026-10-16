# R7 — Transfer routing: the PatchTST test barely exercises routing

**Status:** PARTIAL (geometry disclosed, re-run missing) · **Cost:** 10–15 h · **Depends:** nothing

**Verdict:** PARKED — handled by narrowing, not by compute, unless D6 chooses otherwise.
**Start when:** Phase 6 for the default (delete the transfer claim, about 30 min of writing). The paid path is 10–15 h and buys only if D1 is the full package.
**Free alternative already in the paper:** the geometry disclosure, which bounds the claim from below.

**Source:** Q1 review §3 (PDF p. 4), item "R7. Check whether the PatchTST experiment actually routes" (line 175).

## What the review asked

With lookback 256, patch length 16 and stride 8, PatchTST carries about 31 tokens, so compression at
`c_R=4` or `8` leaves only a few routing candidates; if `k=16` is retained, the module selects everything
and routing resolution is not meaningfully tested. He asked to report the actual tensor axis, patch
padding, candidate count, `k` and selected fraction, to use a smaller budget or a longer token sequence,
and to verify active selection in every cell. He also asked not to read small transfer effects as
evidence that a strong backbone washes out routing until saturation is excluded, and to include the
original dense PatchTST backbone and a no-routing compressed backbone in both accuracy and speed
comparisons.

## What the geometry actually is

The transfer run (`plan/gates/gate17_e2/gate17_run.py`) uses lookback 256, patch 16, stride 8, hidden 16,
4 heads, head dimension 4, `k=4` (not 16), and window 8. That gives 31 patch tokens, so:

| Cell | usable tokens | candidate index tokens | selection |
|---|---|---|---|
| (4,4) | 28 | 7 | 4 of 7 (active but coarse) |
| (8,4) | 24 | 6 | 4 of 6, mapping to at most 3 coarse blocks |
| (4,8) | 28 | 3 | all 3 selected |
| (8,8) | 24 | 3 | all 3 selected |

So the two coarse-router cells are fully saturated, and the fine-router cells select a large fraction of
a very short candidate list. The attention does act along the patch axis, which is the axis the review
asked about.

## What the paper now says

Appendix C and §4.5 report the 31-token geometry, the candidate counts and the fact that the coarse
router selects every candidate, and they say the tie therefore bounds the transfer claim from below
rather than showing that routing washes out on stronger backbones. The discussion limitation says the
same. This removes the unsupported reading; it does not supply a transfer test in which routing has room
to act.

## What is left

- [ ] Re-run the transfer with a token series long enough for both routing resolutions: lookback 1024
      gives 127 patches, so `c_R=4` leaves about 31 candidates and `c_R=8` about 15, both above `k=4`.
      Alternatively keep lookback 256 and drop to `k=2`, which is cheaper but tests a different regime.
- [ ] Log the selected fraction per cell in the transfer manifest and assert it is below 1 in every
      cell, so the saturation question is answered by the artifact rather than by argument.
- [ ] Add the two missing comparison rows: the unmodified dense PatchTST backbone, and a compressed
      backbone with the router removed (all blocks selected), on both accuracy and forward latency.
- [ ] Update Appendix C, §4.5, the discussion limitation and the transfer table with the new numbers.

## Acceptance

Every cell in the transfer table selects a strict subset of its candidates, the dense and no-router
rows are present, and the transfer conclusion is stated only for the regime that was actually tested.

## Cost breakdown

40 runs at lookback 1024 cost roughly 4–6 times a 256-token run (the PatchTST transfer ran 40 runs in a
few hours at 256 tokens), so ≈10–15 h on CPU, plus the two extra comparison rows in the same sweep. No
GPU.

## Evidence pointers

- `plan/gates/gate17_e2/gate17_run.py` (transfer configuration), `plan/gates/gate17_e2/results/`
- `paper/sections/appendix.tex` transfer paragraph and table; `paper/sections/experiments.tex` §4.5
- geometry check: run the four cells at 31 tokens and read `_compress_idx` output length

## Log

- 2026-10-16: created. Geometry and saturation disclosed; re-run not started.
