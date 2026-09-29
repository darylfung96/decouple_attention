# D — Decoupling vs compression (DRRA vs equal-rate)

Status: PARTIAL (D-1/D-2/D-4 DONE 2026-09-28; D-3 blocked on B2-2 + runs) | Updated: 2026-09-28 | Evidence: `plan/gates/gate14_c1/c1_recompute.json` (counts) + tex diffs | Depends: D-3 needs B2-2 decision

Reviewer ask: key = dual-rate vs equal-rate, not vs Normal. p=0.093 ns; 4 lower / 6 higher / 2 tied; ETTh2 +32.7% vs equal-rate. Foreground losses; "champion" → "DRRA (8,4)" / "best-mean ETTh1 config". Replicate 4-cell on contrasting datasets > more ETTh1 seeds. Contribution may be task-dependent.

## Tasks

- [x] **D-1.** DONE 2026-09-28 — `grep -rni champion` → 1 hit = bounded definition (`method.tex:135`); all other uses → DRRA $(8,4)$ / best-mean ETTh1 cell. Verified from 25-seed raw: best-of-four DRRA 13 (not 17) vs beats-CSA 17; CSA head-to-head ahead in 8 (no ties). Paper corrected (RQ2 + stats).
- [x] **D-2.** DONE 2026-09-28 — DRRA-vs-CSA val + test promoted: val −0.0385 p=0.096 (17/25, best-of-four 13/25); test −0.0928 [−0.129,−0.057] p<1e-4 (20/25, best-of-four 16/25) as secondary unadjusted contrast.
- [ ] **D-3.** NEW 4-cell × 3 datasets (ETTh2/ETTm2 + Electricity/Traffic + Exchange), 5 seeds, pre-registered, param-equalized. 60 runs. Effort: L (~14–18h CPU). BLOCKED on B2-2 decision.
- [x] **D-4.** DONE 2026-09-28 — task-dependent framing consistent across abstract/intro/discussion/conclusion (signal-dependent + sweep + §5.1 rewrite).
- [ ] **D-5 (PROPOSED 2026-09-29, needs user approval).** Exploratory (16,4) cell: v2 shows (4,4)≈(8,4)≈(8,8), motivating 'KV rate is nearly free while routing stays fine'. (16,4) = 16 KV blocks + 64 index tokens (4 tokens/block) tests this to the limit — flat = stronger decoupling story; knee = boundary found. Requires: generalize `_postprocess_topk` to divisible geometries (block = t // (n_idx/n_kv)); re-equalize ranks (position-bias sizes change); 25-seed ETTh1 (~3h). MUST be labeled exploratory (post-hoc, motivated by v2 — not confirmatory). Do not start before suite-Flat + v2 land.

## Log

- 2026-09-28: Created from review §D; header added.
- 2026-09-28: D-1/D-2/D-4 DONE. D-3 BLOCKED on B2-2. Note: ETTh2 +32.7% vs equal-rate foregrounding rides with D-3 (needs multi-dataset 4-cell); current suite Table coverage unchanged.
- 2026-09-29: v2 refresh: no single best cell (best-of-four 7/8/8/2 val); DRRA−CSA val p=0.62, test −0.0331 p=0.032 (secondary); suite Flat/DRRA 4/12 best-means each. Paper + fig6/9 updated. D-3/D-5 still queued.
- 2026-09-29: D-3 LAUNCHED as Gate16 (design `gate16_d3/gate16_design.md`; 4 cells x ETTh2/Electricity/Exchange x 5 seeds = 60 runs, pid 79776). Q-2+v2 blockers cleared.
