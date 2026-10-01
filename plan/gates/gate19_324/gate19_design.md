# Gate19 — exploratory (32,4) probe (pre-registered 2026-10-01, answers "why stop at 16?")

Task: D-5 family extension. Motivation: (16,4) was best-mean, inviting the reviewer
question. STATUS: EXPLORATORY — bounds the claim, never confirms it.

## Design

- Cell (32,4): 8 KV blocks + 64 index tokens (8 tokens/block, t//8) via the existing
  generalized branch (verified exact + future-safe; no source change needed).
- Ranks KEPT at (64,64) (rate-only comparison stays clean); attn-param delta +1.6%
  vs (8,4) target — disclosed, accepted for an exploratory probe.
- Frozen: window 16, topk 16, AdamW 1e-4/wd 1e-5/clip 10, batch 32, 10 epochs
  final-weights, train-only z-score, ETTh1 cached data, 25 paired seeds.
- 25 runs → NEW file `plan/gates/gate19_324/results/etth1.jsonl`.
- Env: uv python torch 2.6.0, sequential, idempotent resume.

## Reading rules (written before launch)

- (32,4) ≈ 0.58–0.62 → profile flat out to 32:1; reviewer question answered with data.
- (32,4) clearly worse → knee found between 16:1 and 32:1; bounds the claim.
- Either way: one RQ1 sentence + discussion bound tweak; exploratory cells stay out of
  the confirmatory tables. A further (64,4) is NOT planned — 4 KV blocks is the
  sensible floor for this study (stated in the paper sentence).
