# F — Forecasting validation + test-primary

Status: PARTIAL | Updated: 2026-09-28 | Evidence: test reported; H/L accuracy + MAE + chronology missing | Depends: F-3 needs A/B

Reviewer ask: L=256/H=96 only (longer L latency-only). Add H∈{96,336,720} + L∈{256,512,1024}. Test MSE+MAE primary; val for selection; headlines not val-based. Seed randomness ≠ future-period/dataset uncertainty. Chronology: 5-seed + 20-extension separately + combined.

## Tasks

- [ ] **F-1.** Headline switch: recompute win-counts on test (+MAE); abstract/intro/RQ3 test-primary. Effort: S.
- [ ] **F-2.** Add MAE columns (check checkpoint retention; `gate12/checkpoints/` exists for syn; Gate-2/3?). Effort: S-M.
- [ ] **F-3.** NEW sweeps: H∈{96,336,720}@L=256 + L∈{256,512,1024}@H=96; Normal/CSA/DRRA × 5 seeds; ETTh1 (+1 contrast). H first. Effort: L.
- [ ] **F-4.** Chronology appendix: 5 vs 20 vs 25 separately + seed lists + design docs. Effort: S.
- [ ] **F-5.** Uncertainty language uniform: 25 seeds = training randomness on fixed dataset.

## Log

- 2026-09-28: Created from review §F; header added.
