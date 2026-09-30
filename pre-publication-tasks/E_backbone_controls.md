# E — Relevance beyond weak backbone

Status: PARTIAL | Updated: 2026-09-28 | Evidence: Gate-6 DONE (`gate6_baselines/results/`, `Tab:refpoints`); backbone + controls missing | Depends: E-2 needs B2

Reviewer ask: gaps not marginal (ETTh1 0.3521 vs 0.5967; Exchange 0.3000 vs 3.2350; syn-changepts 0.0622 vs 6.0013). Survive in ≥1 credible temporal-attention backbone (else fixed). Controls: compression w/o routing, local-only, fixed/random at matched budget. Match dense baseline — wiring audit ≠ isolation.

## Tasks

- [ ] **E-1.** Keep Gate-6 (verify `gate6_facts.json` vs reviewer Table-5; keep no-competitiveness language). Verify-only. Effort: S. Status: DONE-verify.
- [ ] **E-2.** NEW backbone transfer: ONE credible temporal-attention backbone; c_KV × c_R cells, else fixed; 5 seeds ETTh1 + 1 contrast; audited. Effort: L.
- [ ] **E-3.** Diagnostic controls at matched budget: all-blocks, window-only, fixed/random. Effort: M (≥3×5×2 runs).
- [ ] **E-4.** Baseline equalization note: list structural confounds beyond rates with ledger; or equalize.

## Log

- 2026-09-28: Created from review §E; header added.
- 2026-09-30: E-2 LAUNCHED as Gate17 (design `gate17_e2/gate17_design.md`; PatchTST backbone verbatim except cell attention; 4 cells x ETTh1/ETTh2 x 5 seeds = 40 runs, pid 14187). Two robustness fixes en route (usable-derived index count, idx truncation; both proven no-ops at divisible S; S=31 regression test added). Q-1 answered by manager (PatchTST approved).
- 2026-09-30: E-2 COMPLETE (40/40, `gate17_analysis.json`). PatchTST backbone: all four cells tied within noise on both datasets (ETTh1 0.370–0.375, ETTh2 0.256–0.261; effects ~0.003, 10x below minimal backbone). Reading: rate effects are backbone-relative, transfer inconclusive-not-negative. Absolute levels match published PatchTST (0.360/0.265), so the transplant is sane. Paper: single-block bullet extended.
