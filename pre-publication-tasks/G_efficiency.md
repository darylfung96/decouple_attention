# G — Efficiency corrections

Status: DONE (G-1…G-4 all 2026-09-28) | Updated: 2026-09-28 | Evidence: tex diffs + `last_query_latency.json` (paired) + `references.bib` (dao2022flashattention) | Depends: none

Reviewer ask: (i) 49 complete vs 256 = 5.22× not 5.33×; 81→49 not half. (ii) paired within-round diff/ratio; CI overlap ≠ paired uncertainty (49.3 vs 52.5ms). (iii) B1 +31% qualifies deployment; B1 vs batched separate. (iv) 8GB = materializing impl (FlashAttention for GPU). (v) MACs ≠ energy.

Current: B1 +30.8% disclosed (`Fig:latency-scale`); CPU-only; no subquadratic (1.40/1.42/1.72); MACs caveated (MLP 33.9M dominates).

## Tasks

- [x] **G-1.** DONE — 5.22× (256/49 complete; 48 non-sink) in method×2, abstract, intro, conclusion×2, experiments×3; 81→49 = three-fifths (discussion). `grep 5\.3` → 0 (surrogate 5.3× removed via I-7).
- [x] **G-2.** DONE — paired within-round deltas from 25-round round-robin rerun (DRRA−Normal −9.0±1.7ms, DRRA−CSA −5.2±0.9ms; directional-only stance kept) + forecast-required companion (Normal 2.6–3.9 / CSA 6.2–9.5 / DRRA 5.8–8.6ms; dense-last fastest). Gate-5 JSON had no per-round logs, so A-2 rerun served as the paired source (logged in G file deviation: accepted, same protocol family).
- [x] **G-3.** DONE — deployment reading qualified to batched operating points + batch-1 exception (conclusion); B1 vs batched kept separate (existing Fig + text).
- [x] **G-4.** DONE — 8GB = materializing-impl (FlashAttention cite + bib entry); MACs-are-not-energy stated (compute paragraph, cross-ref from conclusion).

## Log

- 2026-09-28: Created from review §G; header added.
- 2026-09-28: G-1…G-4 DONE.
