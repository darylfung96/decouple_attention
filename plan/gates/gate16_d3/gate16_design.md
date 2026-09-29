# Gate16 — D-3 4-cell replication on contrasting datasets (pre-registered 2026-09-29)

Task: `D_decoupling_vs_compression.md` D-3. Gate: P0 blockers cleared (Q-2 closed,
Q-5 fixed + verified, v2 analysis done). Code: fixed `_postprocess_topk`
(identity/t//2/fan-out + raise); mapping regression test passes.

## Design

- Cells: all four (4,4), (8,4), (4,8), (8,8) × datasets {ETTh2, Electricity, Exchange}
  × seeds {42,123,2024,7,99} = 60 runs. Dataset choice (one per regime):
  ETTh2 (contrasting ETT dynamics; as-run +32.7% note to revisit), Electricity
  (large multivariate smooth), Exchange (different dynamics; compression loses).
- Ranks (64,64) all cells (attn params dataset-independent:
  95,396 / 95,652 / 95,652 / 95,908 — same as factorial).
- Frozen: window 16, topk 16, AdamW 1e-4/wd 1e-5/clip 10, batch 32, 10 epochs
  final-weights, train-only z-score, cached data (no network).
- Driver: `--d3` mode in `gate15_run.py` (reuses suite loaders + fixed EPP class).
- Results: NEW files `plan/gates/gate16_d3/results/<dataset>.jsonl` (60 rows).
  Old manifests untouched. Provenance tag `gate16/uv-torch2.6.0/fixed-mapping`.
- Env: `~/.uv_env/py311/bin/python` (torch 2.6.0). Sequential, idempotent resume.

## Analysis (after 60/60)

- Per dataset: cell means, DRRA-vs-CSA + best-of-four + KV/RT/H1-style contrasts
  (5 seeds — descriptive, same stance as suite), ETTh2 +32.7% revisit.
- Output: `gate16_analysis.json/md`. Paper: RQ1-cross-dataset paragraph (D-3 closes
  the "single-dataset factorial" limitation for 3 contrasting regimes).

## Out of scope

- B1-3 matched-budget control (separate design); D-5 (16,4) (needs approval);
  E/F/H Stage-2 (need Q-1).
