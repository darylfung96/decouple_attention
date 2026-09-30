# Gate18 — D-5 exploratory (16,4) probe (pre-registered 2026-09-30, user approved)

Task: `D_decoupling_vs_compression.md` D-5. Hypothesis (from v2): KV rate is nearly
free while routing stays fine (c_R=4); (16,4) tests it at the limit.
STATUS: EXPLORATORY (post-hoc, motivated by v2) — can bound the claim, never confirm it.

## Design

- Cell (16,4): 16 KV blocks + 64 index tokens (4 tokens/block, t//4) via the
  generalized many-to-one branch (verified exact + future-safe; (8,4) still
  bitwise-identical).
- Ranks KEPT at (64,64) (rate-only comparison stays clean); attn-param delta
  +0.535% vs (8,4) target — disclosed, just over the 0.5% factorial tolerance,
  accepted for an exploratory probe.
- Frozen: window 16, topk 16, AdamW 1e-4/wd 1e-5/clip 10, batch 32, 10 epochs
  final-weights, train-only z-score, ETTh1 cached data, 25 seeds
  {42,123,2024,7,99 + 1..21 excl 7} (paired with factorial).
- 25 runs → NEW file `plan/gates/gate18_d5/results/etth1.jsonl` (old manifests untouched).
- Env: uv python torch 2.6.0, sequential, idempotent resume.

## Reading rules (written before launch)

- (16,4) ≈ 0.61–0.62 → KV rate 4→8→16 flat: stronger decoupling story.
- (16,4) clearly worse → knee found: content density bites at 16:1; bounds the claim.
- Either way: one paragraph in RQ1 + discussion bound update; no factorial-table merge
  (exploratory cell stays out of the confirmatory tables).
