# A-2 + B1-2 design (pre-registered 2026-09-28, do not edit after runs start)

Canonical env: `~/.uv_env/py311/bin/python` (torch 2.6.0). Tasks: `A_last_query_audit.md` (A-2), `B1_operator_spec.md` (B1-2).

## A-2 — canonical latency: full-layer vs forecast-required

**Paths per config** (Normal / CSA(4,4) / DRRA(8,4), constructors as in `design.md`):
- FULL: stock `model(x)`.
- LAST: replicated last-query forward in-script (source untouched):
  - `h = input_proj(x) + pos_embedding` (full — feeds K/V + compressors, honest cost).
  - Q single-token: `q_a/q_b` on `h[:,255:256]` + RoPE with `position_ids=[[255]]` (exact: `RotaryEmbedding` only uses x for device/dtype).
  - K/V + compressors FULL (both variants); index K-side (`compressed_idx`) FULL.
  - Selection two variants: (a) reuse full-forward `top_k_indices[:,255:256]` (isolates compute); (b) recompute from `q_1` alone (true standalone; q=255 sees all blocks, no future mask; CSA via `idx_q_proj`, EPP shared-Q). Report (a)==(b) selection match rate.
  - Single-row `_attend` replication (q_pos=255; sliding-window mask all-visible; block_bias scattered from single-row topk; sinks S=1), `-sin` RoPE single, `o_a/o_b` single, `norm1→MLP→norm2` single token, head → `[B,96,7]`.

**Correctness gate (before timing):** `max|out_LAST − out_FULL|` < 1e-5 on fixed batch (seeds 0,42,123, B=2). If fail: stop, debug replication.

**Protocol (canonical, Gate-5-compatible):** M2 CPU, `torch.no_grad`, B=32/L=256/F=7 standardized randn batch (fixed seed 0); 25 rounds × 30 passes; round-robin alternation across all 6 paths (3 configs × FULL/LAST) within each round (shared machine noise); report mean ± stdev ms + paired per-round deltas (LAST−FULL) with mean ± 95% CI. Selection variant (b) timed; variant (a) equality-only.

**Artifact:** `last_query_latency.json/md` (equality table + selection-match + 6-path latency + paired deltas). Acceptance (A-2): paired forecast-required deltas; two costs distinguished.

## B1-2 — realized unique blocks/query (same script, inference-only)

Fixed standardized batch (seeds 0,42,123, B=2), full forward with hooks capturing post-`_postprocess_topk` indices (i.e. actual KV-block ids incl. `n_kv` sentinel):
- Per query: unique valid blocks (excl. sentinel), count distribution (mean/min/max over 256 queries × seeds).
- CSA: expect ≤16 unique of 64 blocks (+32 window + sink → actual dense cols vs "96+1" assumption).
- DRRA: expect ≤16 unique of 32 blocks (with `//2` collision count: raw 16 index tokens → unique KV blocks; +16 window + sink vs "48+1").
- Selection overlap: mean pairwise Jaccard of selected-block sets across adjacent queries (routing-stability descriptor, no claim).
- Limitation noted: synthetic batch — column-count mechanics are data-independent; real-data rerun only if Stage-2 proceeds.

**Artifact:** same JSON/MD (`unique_blocks` section). Acceptance (B1-2): table actual vs assumed dense columns.

## Out of scope

- B1-1 backfill-source decisions, B1-3 matched-budget control, B2-2 decision, any training.

## Amendment A2-1 (2026-09-28, pre-results: equality gate FAILED first run)

- Symptom: LAST vs FULL maxdiff ~1e-2 all configs (Normal 1.1e-2, CSA 1-2e-2, DRRA 3-5e-2); selection (a)==(b) held.
- Root cause (audit-script bug, source untouched): `q_b_norm` applied BEFORE
  `.view().transpose()` in `_single_q` and both full-Q recomputations. Source applies it
  AFTER transpose (per-head over D=32, not joint over H*D=128). Found by chained-vs-
  stepwise bisection (q diff 0.93 pre-fix). kv path unaffected (single head).
- Fix: norm-after-transpose at all 3 sites; re-ran gate. Lesson: copy source line order
  verbatim for norm placement; never reorder from memory.

## Amendment A2-2 (2026-09-28, pre-results: timing closure bug)

- Symptom: LAST latencies ~1e-4 ms (100ns) — implausible; equality gate unaffected
  (it calls forwards directly).
- Root cause (audit-script bug): LAST timing lambdas never applied to the model —
  `fns[key](xb)` built the inner lambda instead of running the forward (missing
  `(models[n])` application that the FULL line had). Fixed; warmup now real.
