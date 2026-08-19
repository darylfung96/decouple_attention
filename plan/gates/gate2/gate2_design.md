# Gate 2 — Strict 2×2 Factorial (c_KV × c_R), ExpertPlusPlus family

Frozen task: `plan/gates/gate1/gate1_task.md` (direct-96, L=256, H=96, 7 features, train-only
z-score, pooled `[B,96,7]` MSE, strictly causal attention). Harness:
`gate2_factorial.py` (new file; no existing repo file modified; attention
modules untouched — `ExpertPlusPlusAttention` reused verbatim).

## 1. Factorial design (c_KV = compress_rate, c_R = index_compress_rate)

| Cell  | c_KV | c_R | q_lora_rank | o_lora_rank | attn params | full params | Δ vs (8,4) |
|-------|------|-----|-------------|-------------|-------------|-------------|------------|
| (4,4) | 4    | 4   | 64          | 64          | 95,396      | 348,100     | −0.268%    |
| (8,4) | 8    | 4   | 64          | 64          | 95,652      | 348,356     | 0.000% (target, champion) |
| (4,8) | 4    | 8   | 64          | 64          | 95,652      | 348,356     | 0.000%    |
| (8,8) | 8    | 8   | 64          | 64          | 95,908      | 348,612     | +0.268%   |

## 2. Aux-identical contract (ALL cells byte-identical, per `gate2_factorial.py`)

sliding_window=16 · index_topk=16 · num_heads=4 · head_dim=32 · hidden=128 ·
o_groups=4 · shared-Q routing (idx_q_proj deleted, as in champion) ·
index_head_dim=32 · horizon head Linear(128→672) on last hidden state →
`[B,96,7]` · AdamW lr=1e-4 wd=1e-5 · grad clip 10.0 · batch 32 · 10 epochs ·
L=256 · H=96 · ETTh1 train-only z-score (`download_and_preprocess_etth1(return_stats=True)`
+ `ETTForecastDataset`, imported from `dataset.py`) · positional embedding init
`randn` (matches `model.py:23`).

## 3. Equalization strategy + rationale

- **Target** = attention-param count of (8,4) at q=o=64 (= 95,652). Search
  q_lora_rank × o_lora_rank over 32..128 step 16, instantiate each candidate,
  minimize |attn_params − target| (tie-break: closest to champion ranks 64/64).
- **Why ranks, not window/topk/heads:** sliding_window and index_topk are part
  of the *aux contract* (task mandate); o_groups/heads/hidden define the
  architecture. compress_rate and index_compress_rate define the cell. Only the
  low-rank bottlenecks (q_lora_rank, o_lora_rank) are free compute-quality knobs
  already in the champion design, so equalization there changes neither the
  routing/compression semantics nor the attention field.
- **Result:** the champion ranks (64,64) are argmin for *every* cell — the only
  per-cell Δ comes from the position-bias sizes (compress_rate×64 +
  index_compress_rate×64), which are part of the cell definition. Δ = ±256
  params (±0.268%). No rank change is beneficial: one rank step moves ≥4,112
  params (4.3%), so the lattice minimum is exactly what we keep.
- **Observation (faithful reproduction):** the indexer pathway (idx_kv_proj,
  idx_gate_proj, idx_position_bias, idx_norm, idx_weights_proj) receives no
  gradient in ANY cell — routing flows through `topk().indices`
  (non-differentiable). The champion `ExpertPlusPlusTimeSeriesModel` shows the
  identical 5 dead params; this is a pre-existing family property, reproduced
  exactly, not a harness change.

## 4. Tolerance policy

Enforced at runtime: |Δ|/target ≤ **0.5%** for all cells (hard fail = non-zero
exit). Preferred ≤0.2% is NOT lattice-reachable (step granularity 4.3%); 0.268%
is the global minimum and is accepted. If the search ever misses tolerance it
widens to step 8 up to rank 160, then raises.

## 5. Seeds

{42, 123, 2024, 7, 99} — same seed across all cells (paired design, Gate 4
mixed-effects model). `--seed N` sets torch.manual_seed before model init AND
before data loading (shuffle order).

## 6. Training budget

10 epochs, full train split (shuffle=True), val every epoch (shuffle=False),
final test eval — the existing protocol. Convergence-based stopping is deferred
to Gate 2 item 5 (`plan/next_step.md`); fixed budget is a declared limitation.

## 7. Runtime estimate + background launch

Measured by Gate-2 audit (this Mac, `--threads 8`, full 316-batch train split):
~420–430 s/epoch (train-only ~324 s, plus per-epoch val over 98 batches) × 10
epochs ≈ **~70 min/cell**, ~4.7 h for all 4 cells (one seed), ~23 h for the full
5-seed sweep. Launch each seed as a background job, e.g.:
`nohup python3 gate2_factorial.py --full --seed 42 > gate2_seed42.log 2>&1 &`
`gate2_results.jsonl` makes reruns idempotent (completed (cell,seed) lines
are skipped), so jobs are resumable after interruption.

## 8. Results schema (`gate2_results.jsonl`, one JSON object per line)

`{cell: [c_kv, c_r], seed, val_mse, test_mse, final_train_mse, attn_params,
full_params, c_kv, c_r, completed_utc}` — val/test = pooled `[B,96,7]` MSE on
all windows (z-score units), completed_utc = ISO-8601 UTC.
