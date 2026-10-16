# Gate 26 — R5 probe regeneration summary (post-mapping-fix)

Run 2026-10-16. Script `gate26_mechanistic.py` (copy of gate12, output paths redirected;
gate12 artifacts untouched). Frozen rule in `design.md`; comparison vs Gate 12 in
`comparison.log` / `comparison.json`.

**Result: the mapping fix changes exactly one cell's probes — the equal-rate (4,4) cell.**
Normal and DRRA (8,4) regenerate **bit-identically** to Gate 12 (their code paths were
unchanged by the fix; (8,4) keeps its bit-exact legacy path, Normal has no mapping).
The (4,4) cell moves from the wrong unconditional `t//2` mapping to identity, and its probe
numbers change — including one qualitative flip:

1. **Delayed-copy per-channel MSE (i).** Copy channels (lags 96/128/168/224/256):
   Normal 0.00070/0.00079/0.00071/0.00068/0.00071 (unchanged);
   (4,4) 0.00144/0.00130/0.00129/0.00167/**0.00318** (was 0.00127/0.00156/0.00208/0.00198/0.00220);
   (8,4) unchanged (0.00134/0.00129/0.00127/0.00218/0.00256). Noise floor ≈1.045 (all cells).
   Reading stands: all cells solve the exact-offset copy (3 orders of magnitude below the floor),
   Normal is ~2× more precise, compressed cells show a mild lag gradient. The combined
   compressed-cell range in the paper must widen to 0.0013--0.0032.
2. **Change-point buckets (ii) — QUALITATIVE FLIP.** (4,4) improves in every bucket
   (0–100: 10.268→10.225; 100–500: 11.640→11.551; 500–1000: 12.106→12.011;
   1000–2000: 12.109→12.015) and is now **lowest in every bucket** (previously (8,4) was
   lowest in three of four). The paper sentence claiming (8,4)-lowest-everywhere must be
   replaced by the new reading.
3. **Signal-dependence (iii).** Identical to Gate 12 (computed from frozen suite manifests):
   mean Δval −8.93% (4,4) / −8.26% (8,4); Pearson vs lag-1 autocorrelation −0.35 (p = 0.27)
   and −0.29 (p = 0.36); Spearman −0.22 / −0.25. The paper's current "(4,4) r = −0.31" is
   stale against both Gate 12 and Gate 26 (both −0.35): corrected in this pass.

**Causality coverage (tests, not training).** `test_r5_causality.py` passes at all six rate
pairs at S=256 with (A) adversarial future-noise masking (bitwise-identical past output, token
set and block tensor; no future token/block ever selected), (B) tie duplication, and (C) the
S=31 patch regime with per-block safety and fan-out pairing; coverage diagnostic: at S=31 the
(4,8) cell cannot reach block 6 via selection (index tokens cover up to block 5). Log:
`tests.log`. This replaces the appendix's "not yet run" clause in the next text pass.

**Predeclared rule applied:** rule 2 (qualitative statement flips → text takes the new reading).
No mechanism claim strengthened beyond the probe.
