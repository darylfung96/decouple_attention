# Gate17 — E-2 PatchTST-backbone transfer (pre-registered 2026-09-30, user approved Q-1)

Task: `E_backbone_controls.md` E-2. Question: does the decoupling (routing > KV)
survive outside our minimal single-block backbone?

## Transplant design (published backbone kept verbatim except the attention)

- Backbone: gate6 `PatchTST` verbatim — RevIN, patch 16/stride 8 (≈31 patches at
  L=256), patch-embed + pos, channel-independent batching, head, dropout 0.3,
  AdamW 1e-4/wd 1e-5/clip 10, batch 32, 10 epochs final-weights, same loaders/seeds.
- ONLY change: each of the 3 `TransformerEncoderLayer`s becomes
  [LayerNorm → our-attention → residual → LayerNorm → FFN(d_ff=128, GELU) → residual]
  (pre-norm, mirroring the published `norm_first=True`).
- Our-attention dims adapted to patch regime: hidden=d_model=16, heads=4,
  head_dim=4, index_head_dim=4 (shared-Q valid), q_lora_rank=o_lora_rank=8,
  o_groups=4, sliding_window=8, index_topk=4.
- Cells: (c_KV, c_R) ∈ {(4,4),(8,4),(4,8),(8,8)} on the patch stream.
  S≈31 is not divisible: usable = n_win*m (28 for m=4; 24 for m=8) oldest patches;
  newest patches stay reachable via the sliding window (documented, same for all cells).
- (4,8) boundary note: only 3 index candidates at usable 28 (topk→3) — the cell is a
  near-no-router extreme; reported as a boundary condition, not a fair routing test.
- Equalization: ranks fixed at (8,8) for all cells (target (8,4)); report attn-param
  deltas (position-bias sizes only, as in gate2). No rank search (lattice too coarse
  at this width; documented).
- Mapping: fixed `_postprocess_topk` dispatch covers all four geometries; raise on
  anything else. Mapping regression probe re-run at S=31 before launch.

## Runs

- 4 cells × {ETTh1, ETTh2} × seeds {42,123,2024,7,99} = 40 runs, NEW files
  `plan/gates/gate17_e2/results/<dataset>.jsonl` (old manifests untouched).
- Stance: descriptive (5 seeds/dataset, same as suite); success = same SIGN STRUCTURE
  (routing effect > KV effect per seed), not significance.
- Env: uv python torch 2.6.0, sequential, idempotent resume, provenance tag.

## Acceptance

- Smoke: shapes [B,96,F], grads flow (compressor+shared nonzero; indexer zero —
  fixed-router disclosure applies here too), per-cell mapping ranges at S=31.
- Dry-run param ledger per cell.
- Analysis: `gate17_analysis.json/md` (cell means, KV/RT/H1-style per-seed contrasts,
  best-of-four, beats-Normal equivalent).

## Out of scope

- B1-3 matched-budget controls (separate); changing published hyperparams
  (patch/stride/depth/dropout stay); wide datasets (ETTh1/ETTh2 only — speed).
