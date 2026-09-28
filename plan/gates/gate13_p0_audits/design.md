# Gate 13 — P0 audits design (pre-registered, do not edit after runs start)

Status: DESIGN | Updated: 2026-09-28 | Depends: none | Blocks: all Stage-2
Tasks: `pre-publication-tasks/A_last_query_audit.md` (A-1/A-2), `B2_router_learning.md` (B2-1)

Frozen task: `plan/gates/gate1/gate1_task.md` — direct-96, `x=[B,256,7]` → `out=[B,96,7]`, train-only z-score, strictly causal.

## A-1 — last-query equivalence + forecast-required cost

**Question:** does full-sequence attention + full-sequence MLP equal last-query-only compute for the forecast? If yes, reported O(L²)/speedup numbers overstate forecast-required cost.

**Why suspected:** `model.py:CSATimeSeriesModel.forward` does `attn(x)` over all 256 → `norm1/MLP/norm2` over all 256 → `output_proj(x[:, -1, :])`. Only position 255 feeds the head.

**Configs (exact constructors, no edits to source):**
- Normal: `NormalTimeSeriesModel(7)` → `NormalAttention` (full S×S causal, tied K=V, RoPE, no sink).
- CSA (4,4): `CSATimeSeriesModel(7)` → `CSAAttention(compress_rate=4, index_topk=16, sliding_window=32)`.
- DRRA (8,4): `ExpertPlusPlusTimeSeriesModel(7)` → `ExpertPlusPlusAttention(compress_rate=8, index_compress_rate=4, index_topk=16, sliding_window=16)`.
- Known confound (record, don't fix here): sliding_window 32 (CSA) vs 16 (DRRA) vs full (Normal); projection ranks/o_groups differ — see E-4.

**Last-query path (replicated in audit script, source untouched):**
- Embed: `h = input_proj(x) + pos_embedding` (same).
- Attention, query position 255 only:
  - Normal: `q255 = Q(h[:,255:256])` attends to all `K/V(h)` positions 0..255 (causal = all) → O(L) scores, not O(L²).
  - CSA/DRRA: `q255` attends to sliding-window tail + compressed blocks + sink, with same top-k mask the full forward computed for q=255 (reuse `top_k_indices[:,255,:]` from a full forward to isolate compute question from selection question; plus a second variant that recomputes selection from q255 alone — both reported).
- Norm/MLP position 255 only: `h255 → norm1 → MLP → norm2 → output_proj → [B,96,7]`.
- Full path: stock `model(x)`.

**Checks:**
1. Equality: `max|out_full − out_last|`, fp32 tol 1e-5 (1e-4 CPU-GEMM note), fixed batch (torch.manual_seed(0), B=2, L=256, F=7, standardized randn) + 3 seeds (0, 42, 123). Must hold for all 3 configs (both selection variants for CSA/DRRA).
2. Cost: report per-config (a) full-layer vs (b) forecast-required — MACs by analytic count (attention scores + projections + last-pos-only MLP) + wall latency (M2 CPU, `torch.no_grad`, sync, alternating head-to-head, 25 rounds × 30 passes, B=32/L=256, same protocol as Gate-5).
3. Artifact: `plan/gates/gate13_p0_audits/last_query_audit.json` (equality + costs) + `.md` summary. Verdict: EQUIVALENT (report both costs from now on) or NOT-EQUIVALENT (stop, debug full-forward dependence on earlier positions).

**Acceptance (A-1):** equality table 3 configs × 3 seeds + both cost columns. Unblocks A-2 (canonical B32 latency re-run on last-query paths).

## B2-1 — router grad audit (does the indexer learn via task loss?)

**Question:** hard `topk → scatter(0/-inf) → _attend` leaves `index_scores` unused downstream (`attention.py:BaseCSAAttention.forward`, EPP same + `del idx_q_proj`). Do indexer-exclusive params get nonzero grads from task MSE?

**Method (architecture-dependent, data-independent — synthetic batch valid):**
- Models: CSA (4,4) + DRRA (8,4) via constructors above, train mode, fp32 CPU, seed 42.
- Batch: `x=[2,256,7]` standardized randn, `y=[2,96,7]` randn (synthetic; grad-path existence does not depend on ETTh1 values — note as limitation, real-data rerun only if synthetic shows learning).
- Loss: `MSELoss(model(x), y)`, backward once. Record per-parameter `.grad` norm + `param.data` delta after one SGD step (lr=1e-3).
- Param groups:
  - indexer-exclusive: `idx_kv_proj, idx_gate_proj, idx_position_bias, idx_norm, idx_weights_proj` (+ `idx_q_proj` CSA only; EPP deleted by design, `_index_query` returns main Q).
  - compressor contrast: `comp_kv_proj, comp_gate_proj, comp_position_bias, comp_norm`.
  - shared path: `q_a_proj, q_b_proj, kv_proj, o_*`, sinks.
- Artifact: `router_grad_audit.json/md` with table grad-norm per param + verdict per group: LEARNS (norm > 1e-12) / DOES-NOT-LEARN (≈0).
- Expected (pre-registered): indexer-exclusive ≈ 0 (hard top-k dead-end); shared/compressor > 0. If indexer shows nonzero, inspect path (e.g. via `idx_weights_proj` continuous mixing — note: `weights` multiplies scores BEFORE topk in `forward`, so `idx_weights_proj` MAY get grads even though selection is hard; report it separately, not as proof routing learns).

**Acceptance (B2-1):** table + LEARNS/DOES-NOT-LEARN verdict. Unblocks B2-2 decision: (a) disclose fixed router vs (b) redesign + re-train.

## Out of scope here (explicitly deferred)

- B1-2 unique-block counts + B1-3 matched-budget control (next design).
- A-2 canonical latency re-run (needs A-1 green).
- Real ETTh1 data loader wiring (only if synthetic audit is inconclusive).
- Any source edits — audit scripts replicate paths without touching `model.py`/`attention.py`.

## Repro commands (after scripts land)

```
~/.uv_env/py311/bin/python plan/gates/gate13_p0_audits/last_query_audit.py
~/.uv_env/py311/bin/python plan/gates/gate13_p0_audits/router_grad_audit.py
```
(canonical env: `~/.uv_env/py311`, torch 2.6.0 per lock; do not use repo `.venv` — no torch)
