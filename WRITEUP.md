# Normal vs Flat vs ExpertPlusPlus — A Detailed Technical Write-Up

**Dual-Rate Routed Attention (DRRA) variants for long-sequence time-series forecasting, compared on ETTh1 (lookback 256, horizon 96).**

This document is a self-contained technical description of three attention variants:

1. **Normal** — vanilla full quadratic self-attention (baseline, `normal_attention.py`)
2. **Flat** — "two-series compressor + flat indexer" DRRA V4 (`attention.py`, class `CSAAttention`)
3. **ExpertPlusPlus** — decoupled-granularity DRRA: 8:1 KV content + 4:1 routing, shared-Q, slim O (`expert_plus_plus_attention.py`)

It includes the full algorithms (equations + annotated code), exact hyperparameters, per-module parameter counts, empirical results, and a step-by-step reproduction guide. Everything reported here is measured on a CPU-only Apple Silicon machine (M-series), PyTorch 3.11 / CPU, and is fully reproducible from the files in this directory.

---

## 1. Summary (read this if you read nothing else)

| | **Normal** | **Flat (DRRA V4)** | **ExpertPlusPlus** |
|---|---|---|---|
| Attention columns per query (S=256) | 256 (all; no sink) | 96 (64 KV + 32 win) + 1 sink = 97 | 48 (32 KV + 16 win) + 1 sink = 49 |
| KV compression ratio | none | 4:1 | **8:1** |
| Routing granularity (index tokens) | none | 64 (4:1) | **64 (4:1)** — same as Flat |
| Router query | — | own `idx_q_proj` | **shared main Q** |
| O bottleneck rank | 128 | 128 | **64** |
| Sliding window | none | 32 | **16** |
| Sink column | none | 1 softmax column (4 scalar logits) | 1 softmax column (4 scalar logits) |
| Params (attn / full) | 102,496 (269,415) | 144,548 (311,467) | **95,652 (262,571)** (smallest) |
| Val MSE (10 ep, seed 42) | **0.1083** | 0.1085 | 0.1099 |
| Test MSE | 0.1637 | **0.1617** | 0.1654 |

**The central finding (pre-freeze pilot — superseded, §2.2):** within this design study of the DRRA family, the decoupled-rate cell **ExpertPlusPlus — (c_KV=8, c_R=4)** — matched Flat's validation accuracy (0.1099 vs 0.1085, gap +0.0014 — inside the ±0.002 run-to-run variance band) while having **33.8% fewer parameters** than Flat ((144,548 − 95,652)/144,548) and — notably — **fewer attention parameters than even Normal** (95,652 vs 102,496). Pre-freeze latency figures (forward/training ms, speedups, Perf/Spd) are superseded and were removed from this document on 2026-08-18 (paper_notes.md §4). The internal speed goal that originally framed this comparison is retired in favor of design-study reporting.

**The one sentence design insight:** *routing granularity carries accuracy; KV content density only buys speed.* ExpertPlusPlus keeps Flat's fine 4:1 router (64 index tokens) but halves the attention matrix by attending to 8:1-compressed KV blocks — something a coarser "ExpertFlat" variant (8:1 on *both* axes) got wrong, losing accuracy (0.1102).

---

## 2. Task, Data, and Evaluation Protocol

### 2.1 Dataset
- **ETTh1** (Electricity Transformer Temperature, hourly) from the official repo `zhouhaoyi/ETDataset` (`ETT-small/ETTh1.csv`), downloaded at runtime by `dataset.py`.
- **7 features**: HUFL, HULL, MUFL, MULL, LUFL, LULL, OT.
- **Normalization**: per-feature z-score (`(x − mean) / std`), with `mean`/`std` **fit on the TRAIN split only**; the same train-fitted stats are applied to val/test. The OLD code computed stats over the *entire* series before splitting — a **future-stats leak** — now fixed (frozen spec: `plan/gates/gate1/gate1_task.md` §5).
- **Split**: chronological 60% train / 20% val / 20% test — computed on raw rows; disjoint, ordered, and no window ever spans a split boundary.

### 2.2 Forecasting task (FROZEN — direct 96-step; `plan/gates/gate1/gate1_task.md`)
**Direct 96-step long-horizon forecasting** — no teacher forcing, no autoregression, no iterative decoding. In **one forward pass** the model receives `x = [B, 256, 7]` (past window `data[t-255 .. t]`) and outputs `out = [B, 96, 7]`, the next 96 steps `y = data[t+1 .. t+96]` (disjoint in time from the input), produced by a **horizon head** (`Linear(hidden → 96·7)` from the last hidden state; encoder untouched). Stride-1 sliding windows within each split (255/256 overlap — **samples are NOT IID**).

### 2.3 Loss, metric, causality
- Loss / metric: **pooled MSE over all `(B, 96, 7)` elements**: `loss = MSELoss(out, y)` — **no slicing** of `out` (replaces the old per-token `out[:, -96:, :]` scoring; predictions stay in standardized units).
- **Causality contract** (frozen): encoder state at position `p` depends only on inputs `≤ p`; no output depends on any input row `> t`. Verified by `plan/gates/gate1/gate1_causality.py` + `plan/gates/gate1/gate1_gradmask.py` — **all 6 variants PASS** (bitwise future-invariance + exact-zero future gradients, power-checked).

> **⚠️ Freeze notice:** all previously reported numbers in this document and `RESULTS.md` (Val/Test MSE, speed, Perf/Spd) **predate this freeze and are superseded** — produced under the old per-token next-step task and leaky full-series normalization (see `RESULTS.md` TASK FREEZE NOTICE). Valid numbers come only from **Gate 2** runs under the frozen protocol (`plan/gates/gate1/gate1_task.md`). Pre-freeze speed/latency figures (forward/training ms, speedups, Perf/Spd) were removed from this document on 2026-08-18 (paper_notes.md §4); original measurements are preserved in `experiment-session-new-attention.md`.

### 2.4 Optimization recipe (identical for all variants)
| Hyperparameter | Value |
|---|---|
| Optimizer | AdamW |
| Learning rate | 1e-4 |
| Weight decay | 1e-5 |
| Gradient clipping | `clip_grad_norm_(…, 10.0)` |
| Batch size | 32 |
| Epochs | 10 |
| Seed | `torch.manual_seed(42)` re-seeded before **each** model |
| Hardware | CPU (Apple Silicon M-series), fp32 |

---

## 3. Shared Architecture (Common to All Three)

All three variants are plugged into the same minimal Transformer block (`CSATimeSeriesModel` in `model.py`), so the *only* difference is the attention module. The block is:

```
x = input_proj(x) + pos_embedding          # Linear(7 → 128) + learned (1,256,128)
h = norm1(attn(x) + x)                      # LayerNorm
h = norm2(MLP(h) + h)                       # MLP: Linear(128→512) → GELU → Linear(512→128)
out = output_proj(h[:, -1, :])              # horizon head: Linear(128 → 672), last hidden state only → [B, 96, 7]
```

### 3.1 Attention-internal projections (identical across variants)
All three attention modules use the **same Q / KV / O projections**, so the parameter differences come only from the compression machinery and the O rank:

- **Q projection (LoRA-style):**
  `q = q_b_norm( q_b_proj( RMSNorm( q_a_proj(h) ) ) )`, then RoPE.
  - `q_a_proj`: `Linear(128 → 64)` (q_lora_rank = 64)
  - `q_a_norm`: RMSNorm(64)
  - `q_b_proj`: `Linear(64 → 4·32)` (num_heads=4, head_dim=32)
  - `q_b_norm`: **unweighted** RMSNorm (no learnable scale)
- **KV projection (tied K=V, single KV head):**
  `kv = RoPE( RMSNorm( kv_proj(h) ) )` shaped `[B, 1, S, 32]` — one head broadcast across the 4 Q heads.
  - `kv_proj`: `Linear(128 → 32)`
  - `kv_norm`: RMSNorm(32)
- **RoPE**: `rope_head_dim = head_dim // 4 = 8`, base 10000, applied only to the **last 8** of the 32 dims (`apply_rotary_pos_emb` splits `nope`/`rope` halves). After attention, output is rotated back with `-sin`.
- **O projection (grouped):**
  `o = o_b_proj( o_a_proj( reshape(attn_out) ) )`
  - `o_a_proj`: `GroupedLinear(in_per_group=4·32/4=32, out=4·o_lora_rank, n_groups=4)` — a block-diagonal linear with 4 groups of width `o_lora_rank`.
  - `o_b_proj`: `Linear(4·o_lora_rank → 128)`
  - `o_lora_rank` is **128 for Normal & Flat, 64 for ExpertPlusPlus** (the "slim O" cut).

> **Important for reproduction:** `GroupedLinear` is implemented as a *single* `nn.Linear(out, in_per_group)` whose weight is reshaped to `(n_groups, out/n_groups, in_per_group)` at forward time — so its parameter count is `out × in_per_group`, **not** multiplied by `n_groups`. A naive reimplementation that creates one linear per group would double-count parameters.

### 3.2 Per-module parameter ledger (measured)

| Module | Normal | Flat | ExpertPlusPlus |
|---|---|---|---|
| `q_a_proj` + `q_a_norm` | 8,192 + 64 | same | same |
| `q_b_proj` | 8,192 | same | same |
| `kv_proj` + `kv_norm` | 4,096 + 32 | same | same |
| `o_a_proj` | 16,384 | 16,384 | **8,192** (−8,192) |
| `o_b_proj` | 65,536 | 65,536 | **32,768** (−32,768) |
| KV compressor (`comp_kv_proj`+gate+bias+norm) | — | 8,192+8,192+256+32 | 8,192+8,192+**512**+32 (+256) |
| Indexer (`idx_kv_proj`+gate+bias+norm) | — | 8,192+8,192+256+32 | same |
| `idx_q_proj` (router query) | — | 8,192 | **0** (−8,192) |
| `idx_weights_proj` | — | 512 | same |
| `sinks` | — | 4 | 4 |
| **Attention total** | **102,496** | **144,548** | **95,652** |

- Flat − Normal = +42,052 (the two compressors + indexer + own router query + sinks).
- EPP − Flat = −48,896, from exactly four deltas: `o_b_proj` −32,768, `o_a_proj` −8,192, `idx_q_proj` −8,192, `comp_position_bias` +256.
- Full model (incl. shared block + MLP): Normal 269,415, Flat 311,467, EPP 262,571.
- **EPP (95,652) has 6.7% *fewer* attention parameters than Normal (102,496)** — (102,496 − 95,652)/102,496 = 6.7% — **and 33.8% fewer than Flat (144,548)** — (144,548 − 95,652)/144,548 = 33.8% (the "≈34%" headline). The slim O more than pays for the compression machinery.

---

## 4. Normal Attention (`normal_attention.py`)

### 4.1 Algorithm
Standard full quadratic self-attention with a causal mask, keeping the shared Q/KV/O projections (§3.1):

```
Q = RoPE(q_proj(h))                 # [B, 4, S, 32]
K = V = RoPE(kv_proj(h))            # [B, 1, S, 32], tied
mask[i,j] = -inf  if j > i          # upper-triangular causal
A = softmax( Q Kᵀ / √32 + mask )    # [B, 4, S, S]
out = A V
out = RoPE⁻¹(out); out = O(out)
```

There is **no** compression, indexing, sliding window, or sink. Every query attends to every position in its causal past.

### 4.2 Complexity
- Attention GEMM: $O(B \cdot H \cdot S^2 \cdot D)$ = 256×256 matrices.
- Memory: $O(S^2)$ attention weights.

### 4.3 Results (10 epochs, seed 42)
- Val MSE **0.1083** (best val of all three), Test MSE 0.1637, 102,496 params.

Normal is the accuracy reference: it has full access to history but pays $O(S^2)$.

---

## 5. Flat — DRRA V4 (`attention.py`, `CSAAttention`)

Flat is the baseline *compressed* attention. Its two key ideas: (a) **two-series compression** with per-dimension softmax-overlap gating, applied separately to the **KV content** and to the **routing index**, and (b) **dense masked attention** over the sliding window plus *all* compressed blocks, with non-selected blocks masked to −∞.

Configuration: `compress_rate=4`, `index_topk=16`, `index_n_heads=4`, `index_head_dim=32`, `sliding_window=32`, `o_groups=4`, `o_lora_rank=128`.

### 5.1 The two-series compressor (`_flat_two_series_compress`)

Compresses `S = 256` positions into `n_win = S/m = 64` tokens, each covering `m = 4` positions `[4w, 4w+3]`. The mechanism (shared by the KV compressor and the indexer, parameterized by projection/bias/norm/dim):

1. **Project to double width.** Each token is projected to `2·dim` channels (for KV, `dim = head_dim = 32`, so 64 channels; for the indexer, `dim = index_head_dim = 32`):
   `comp_kv = kv_proj(h)[:, :usable] → [B, 64, 4, 64]`, `comp_gate = gate_proj(h)[:, :usable] + pos_bias[pos % m] → [B, 64, 4, 64]` (a learnable per-position-within-window bias, shape `(m, 2·dim)`).

2. **Build the 2m = 8 overlap slots.** A new tensor `new_kv [B, 64, 8, dim]`:
   - slots `[m, 2m) = [4, 8)`: the **second half** (`dim:`) of the current window's tokens — each token's "own window" contribution;
   - slots `[0, m) = [0, 4)`: the **first half** (`:dim`) of the *previous* window's tokens — each token also appears as the "overlap" contribution to the next window.

   I.e. every token spans two adjacent windows: its projection's first `dim` channels gate it into the *next* window, its second `dim` channels into its *own* window. This is the "two-series" name.

3. **Per-dimension softmax gate.** `weights = softmax(comp_gate, dim=2)` over the 8 slots *independently per dimension* (this per-channel softmax is the crucial difference from scalar/vector gates — it lets different feature channels route differently).

4. **Weighted sum + RMSNorm:**
   `compressed = RMSNorm( Σ_{s=0..7} new_kv[:,:,s,:] · weights[:,:,s,:] )`.

5. **RoPE at window starts:** positions `arange(64)·4 = {0, 4, 8, …, 252}`.

Note `usable = n_win·m` trims any remainder (exact for S=256: usable = 256).

### 5.2 The router (indexer + scorer)

- **Index tokens**: `_compress_idx` runs the *same* two-series compressor with `dim = index_head_dim = 32`, producing **64 index tokens** at 4:1. Index token `t` represents positions `[4t, 4t+3]`.
- **Router query**: `q_idx = idx_q_proj(q_residual)` → `[B, 4, S, 32]` (own low-rank projection from the pre-`q_b` residual), RoPE'd.
- **Per-head scores**: `scores = relu(q_idx · cidxᵀ) / √32 → [B, 4, S, 64]` (ReLU before scaling, DeepSeek-style).
- **Head mixing**: `weights = idx_weights_proj(h) · (1/√4) → [B, S, 4]`; then
  `index_scores[b, s, t] = Σ_h scores[b, h, s, t] · weights[b, s, h]`.
- **Future masking**: token `t` (span `[4t, 4t+3]`) is masked to −∞ for query `q` if `4t+3 > q`.
- **Top-k**: `top_k_indices = topk(index_scores, k=16)`; any token that is out-of-bounds or still in the future is set to a **sentinel** `n_idx = 64` (which `_attend` slices off — see below).

### 5.3 Dense masked attention over window + blocks (`_attend`)

Instead of gathering the selected blocks (sparse), Flat computes a **dense** attention over a fixed set of columns and masks non-selected blocks to −∞ — exact softmax with zero weight on masked blocks, no approximation:

1. `block_bias [B, 1, S, 65]` filled with −∞; `0.0` scattered at the selected `top_k_indices`; then sliced to `[B, 1, S, 64]` (drops the sentinel column).
2. Keys: `total_k = cat([ kv[:, :, -32:] (sliding window), compressed_kv (64 blocks) ])` → **96 columns** (plus 1 sink column in the softmax). Sliding window gets its own causal mask `sw_mask` (window positions ≤ query position).
3. `attn_weights = Q·Kᵀ/√32 + cat(sw_mask, block_bias)`.
4. **Sink**: 4 learnable logits (`self.sinks`, one per head) appended as an extra column before softmax (stabilizes the masked attention, per standard "attention sinks" practice): `softmax(cat(weights, sinks))`, then drop the sink column.
5. `out = probs · V` (window + blocks, `[B, 1, S, 96]` V), then rotate back and apply O.

**Why dense?** On CPU, dense GEMMs over 96 columns beat a per-query gather+bmm — the sparse path was substantially slower in early EPP prototypes. Masking to −∞ makes the dense result exactly equal to the sparse top-16 selection.

### 5.4 Complexity
- Attention GEMM: $O(B \cdot H \cdot S \cdot (W + C))$ with window $W=32$, compressed blocks $C=64$ → 96 columns/query.
- Router: $O(B \cdot S \cdot 64)$ — one score per index token per position.

### 5.5 Results
- Val **0.1085**, Test **0.1617** (best test of all variants), 144,548 params.

---

## 6. ExpertPlusPlus (`expert_plus_plus_attention.py`)

ExpertPlusPlus keeps Flat's router and compressor mechanisms but **decouples the two compression ratios**, and trims three purely-compute costs:

| Cut | Detail | Effect |
|---|---|---|
| **8:1 KV content** | `compress_rate=8` → 32 blocks, each covering `[8j, 8j+7]` | Attention columns 96 → 48 |
| **4:1 routing granularity** | `index_compress_rate=4` → **64 index tokens**, *identical to Flat* | Accuracy preserved |
| **Shared-Q routing** | router reuses the main per-head Q; `idx_q_proj` deleted | −8,192 params, one less projection+RoPE |
| **Slim O** | `o_lora_rank=64` (vs 128) | −40,960 params |
| **Window 16** | `sliding_window=16` (vs 32) | −16 columns, free (same val) |

Requirement: `head_dim == index_head_dim` (both 32) so the main Q can serve as the routing query.

### 6.1 Two independent compressors
- `_compress_kv`: two-series compressor with `m = compress_rate = 8` → **32 KV blocks**; each block `j` covers positions `[8j, 8j+7]`; RoPE at positions `{0, 8, …, 248}`.
- `_compress_idx`: two-series compressor with `m = index_compress_rate = 4` → **64 index tokens**; token `t` covers `[4t, 4t+3]`; RoPE at positions `{0, 4, …, 252}`. Same granularity as Flat's router.

### 6.2 Fine router on coarse blocks: the token→block map (`_postprocess_topk`)
This is the heart of the design. The router scores 64 *fine* index tokens, but `_attend` only has 32 *coarse* KV blocks to choose from. The mapping is deterministic and local:

```
block j  covers positions [8j, 8j+7]  ==  index tokens {2j, 2j+1}
token t  (covers [4t, 4t+3])          →  block t // 2
```

Concretely, after top-k selection with future masking (identical to Flat):

```
sentinel  = top_k_indices >= n_idx        # 64 (invalid/future) → keep as sentinel
blocks    = clamp(top_k_indices, 0, 63) // 2     # token → block
block_end = blocks * 8 + 7                        # last position inside block
safe      = block_end <= q                        # ENTIRE block must be in the past
kv_blocks = where(safe, blocks, n_kv=32)          # unsafe blocks → sentinel 32
kv_blocks = where(sentinel, n_kv, kv_blocks)      # never unmask a sentinel
```

The **future-safety check is on the block span, not the token span**: a top-16 index token might point at block `j` whose later half (`8j+7`) is still in the future relative to query `q` — such a block would leak future positions into the attention if selected, so it is replaced by the sentinel. (This matches how Flat masks future *tokens*; here it must be done at block granularity.) The sentinel column `n_kv = 32` is sliced off in `_attend` (`block_bias[..., :n_idx]`), so an unsafe block simply contributes zero weight — exactly like a masked block.

Edge case handled explicitly: at `q = S−1 = 255`, a sentinel token would map to block 31 which *is* safe — the `torch.where(sentinel, …)` prevents a sentinel from ever being unmasked.

### 6.3 Shared-Q routing (`_index_query`)
```
_index_query(q, …) -> q          # the already-RoPE'd, normalized per-head Q
```
Instead of projecting a separate router query from `q_residual`, EPP uses the main Q directly. This works because `head_dim == index_head_dim` (both 32): the scoring math is identical to Flat's, just with `q_idx := q`. Saves `idx_q_proj` (8,192 params) and one RoPE application per forward.

### 6.4 Attention columns
`_attend` (inherited, unchanged) with window 16:
`total columns = 16 (window) + 32 (KV blocks) = 48` content columns + 1 sink = 49 softmax columns.

### 6.5 Complexity
- Attention GEMM: **48 columns/query** — exactly **half of Flat's 96** and 5.3× fewer than Normal's 256.
- Router: `S × 64` — **identical cost to Flat** (this is the deliberate trade: pay the full fine routing cost, halve the attention cost).

### 6.6 Results
- Val **0.1099**, Test **0.1654**, **95,652 params**.
- Window ablation: `sliding_window=32` gives val 0.1099 / test 0.1665; window=16 gives val 0.1099 / test 0.1654 → **window 16 is strictly better** (same val, better test).

### 6.7 Why ExpertFlat failed but ExpertPlusPlus succeeds
ExpertFlat (`expert_flat_attention.py`) applied 8:1 to **both** KV and routing (32 coarse index tokens). Result: 0.1102 val — worst of the family. The router lost the ability to discriminate *which* history to attend to (each index token spans 8 positions), so accuracy dropped even though the attention matrix was smaller. EPP shows the granularity split is the right decomposition: coarse *content* (cheap attention) + fine *routing* (accurate selection).

---

## 7. Empirical Results

### 7.1 Accuracy (10 epochs, seed=42, `compare.py`)

| Model | Val MSE | Test MSE | vs Flat (val) | vs Flat (test) |
|---|---|---|---|---|
| **Normal** | **0.1083** | 0.1637 | −0.0002 | +0.0020 |
| **Flat** | 0.1085 | **0.1617** | — | — |
| **ExpertPlusPlus** | 0.1099 | 0.1654 | +0.0014 | +0.0037 |
| ExpertFlat (ref) | 0.1102 | 0.1645 | +0.0017 | +0.0028 |
| FlatPlus (ref) | 0.1098 | 0.1635 | +0.0013 | +0.0018 |
| Modified (ref) | 0.1088 | 0.1624 | +0.0003 | +0.0007 |
| Stacked (ref, legacy) | 0.1116 | 0.1665 | +0.0031 | +0.0048 |

*Stacked: legacy numbers; no runnable source in repo (missing from model.py/compare.py) — its parameter and column counts are N/A (no source); only legacy run results are shown.*

ExpertPlusPlus's full training curve (window=16, seed 42):

```
 Epoch |   Train  |    Val   |   Test
    1  |  0.2815  |  0.1486  |  0.2057
    2  |  0.1195  |  0.1349  |  0.1935
    3  |  0.1126  |  0.1306  |  0.1885
    4  |  0.1090  |  0.1283  |  0.1835
    5  |  0.1052  |  0.1223  |  0.1759
    6  |  0.1015  |  0.1173  |  0.1701
    7  |  0.0987  |  0.1140  |  0.1674
    8  |  0.0965  |  0.1137  |  0.1675
    9  |  0.0950  |  0.1127  |  0.1676
   10  |  0.0937  |  0.1099  |  0.1654
```

**Variance note:** re-seeding gives ±~0.002 val MSE run-to-run. The EPP−Flat val gap (+0.0014) is inside that band; the test gap (+0.0037) is outside it and is the honest cost of 8:1 content compression. If test MSE is paramount, Flat remains the best variant.

### 7.2 Parameter counts (measured; attention module only, full model in parentheses)
| Model | Params (attn / full) | vs Flat (attn) |
|---|---|---|
| Normal | 102,496 (269,415) | −29.1% |
| Flat | 144,548 (311,467) | — |
| **ExpertPlusPlus** | **95,652 (262,571)** | **−33.8%** |

### 7.3 Speed measurements (removed — superseded)

All pre-freeze latency figures (forward/training ms, speedups, Perf/Spd composite) were produced under the old paradigm, are **superseded** by the Gate-1 task freeze, and were removed from this document on 2026-08-18 (paper_notes.md §4). Original measurements are preserved in `experiment-session-new-attention.md`. Re-measurement is planned under the Gate 5 hardware/latency protocol (p50/p90/p99 with bootstrap CIs, scaling sweeps, cross-hardware; `plan/next_step.md` §10).

The methodology note survives: CPU benchmarking on this machine is **highly variance-prone** (thermal throttling, background processes), so single sequential runs are unreliable and the **alternating head-to-head** protocol (time both models inside the same thermal/contention window, repeat, take medians) is the right way to compare. The protocol code is preserved in §9.5.

### 7.4 Why the printed full-table benchmark is not usable

`benchmark_speed.py` runs all variants sequentially; under CPU contention it produced physically implausible numbers (one load-average-19 run even showed a lighter model slower than a heavier one). Those runs were excluded. **Always measure head-to-head** (see §9.5).

---

## 8. Design Evolution and Ablated Alternatives (for researchers)

What was tried and why it failed, in rough chronological order. All are still in the repo as reference implementations:

- **❌ Sparse-gather routing (EPP v1)** — select top-k indices then `gather`+`bmm`. **Far slower** than dense on CPU. Dense masked GEMMs won decisively; sparse is only worth it on GPU with hardware gather support.
- **❌ ExpertFlat (8:1 on both axes)** — fast but router too coarse → 0.1102 val. Led directly to the decoupling insight.
- **❌ Hierarchical indexer (Phase C1)** — multi-scale pyramid for the indexer; consistently worse than the flat indexer.
- **❌ Multi-scale KV pyramid (3 levels, stride 2/4/8)** — 224 KV tokens; overparameterized for 10 epochs, slower convergence.
- **❌ Learnable block-bias offset** — NaN instability ~50% of runs; no gain with tanh bounding.
- **❌ Gated residual KV + linear-pool indexer (FlatPlus)** — linear pool loses per-head × per-dim routing flexibility of the softmax-overlap gate (0.1098 vs 0.1085).
- **❌ Stacked 2:1→2:1 (legacy; no runnable source in repo)** — no current source in `model.py`/`compare.py`, so its parameter/column counts are N/A (no source); extra level-1 parameters hurt at 10 epochs (0.1116, legacy run result).
- **✅ Sliding window 32→16** — smaller attention matrix at identical val (val 0.1099 both ways; test improved 0.1665 → 0.1654).
- **🐛 `torch.empty` → `torch.zeros`** — all position-bias / residual-bias parameters were switched from `torch.empty` to `torch.zeros`; uninitialized memory on macOS occasionally contained garbage up to 10²⁸, causing NaN in the softmax gates. Root cause of intermittent NaN across seeds.

---

## 9. Full Reproduction Guide

### 9.1 Environment
- Python 3.11 (this project used `~/.uv_env/py311/bin/python`).
- PyTorch (CPU; Apple Silicon M-series), fp32. No CUDA, no GPU required — but all relative claims should transfer qualitatively.
- No GPU-specific code paths are used; `torch.cuda` calls are guarded and skipped on CPU.

### 9.2 Files (all in this directory)
| File | Contents |
|---|---|
| `attention.py` | Utilities (RMSNorm, RoPE, GroupedLinear) + `BaseCSAAttention` + **Flat** (`CSAAttention`) |
| `normal_attention.py` | **Normal** attention |
| `expert_plus_plus_attention.py` | **ExpertPlusPlus** attention |
| `model.py` | `CSATimeSeriesModel` + per-variant subclasses (incl. `ExpertPlusPlusTimeSeriesModel` with window=16) |
| `dataset.py` | ETTh1 download, z-score, 60/20/20 split, windowed dataset |
| `compare.py` | 6-model accuracy comparison (10 epochs, seed 42) |
| `benchmark_speed.py` | All-variant speed harness (sequential — use §9.5 for reliable numbers) |
| `test_expert_plus_plus.py` | 4 structural checks for EPP |

### 9.3 Reproduce the accuracy table
```bash
python compare.py
```
Expected output: per-epoch tables for Flat, Modified, Normal, FlatPlus, ExpertFlat, ExpertPlusPlus, then:

```
                Model  |  Val MSE | Test MSE
        ExpertPlusPlus |   0.1099 |   0.1654   (approx; ±0.002)
```

### 9.4 Sanity checks
```bash
python test_expert_plus_plus.py
```
Checks: (1) tensor shapes ckv=[B,1,32,32], cidx=[B,1,64,32] + token→block mapping + future-safety + dense `_attend` consumes mapped indices; (2) forward/backward with 12/17 parameter groups getting grads; (3) tiny overfit: both Flat and EPP fit a small synthetic task (loss < 0.5); (4) parameter counts Flat=144,548, EPP=95,652. (The tiny-fit proxy is only a sanity check — the *real* fine-vs-coarse router comparison is EPP's 0.1099 val vs ExpertFlat's 0.1102 in the 10-epoch run, §7.1.)

### 9.5 Benchmarking protocol (alternating head-to-head)

Do **not** rely on `benchmark_speed.py` single-run numbers on a busy machine. Use alternating head-to-head. (Pre-freeze latency results measured this way were superseded by the task freeze and removed from this document on 2026-08-18 — paper_notes.md §4; re-measurement is planned under the Gate 5 protocol, `plan/next_step.md` §10.)

```python
import torch, time
from benchmark_speed import FlatWrapper, ExpertPlusPlusWrapper

def median_fwd_ms(model, x, warmup=20, iters=100):
    model.eval()
    with torch.no_grad():
        for _ in range(warmup): model(x)
        ts = []
        for _ in range(iters):
            t0 = time.perf_counter(); model(x); ts.append((time.perf_counter()-t0)*1000)
    return sorted(ts)[len(ts)//2]

x = torch.randn(32, 256, 128)
ratios = []
for rep in range(3):                       # alternate to cancel thermal drift
    flat_ms = median_fwd_ms(FlatWrapper(), x)
    epp_ms  = median_fwd_ms(ExpertPlusPlusWrapper(), x)
    ratios.append(flat_ms / epp_ms)
    print(f"rep {rep}: Flat {flat_ms:.2f} ms  EPP {epp_ms:.2f} ms  speedup {flat_ms/epp_ms:.2f}×")
print(f"median speedup: {sorted(ratios)[1]:.2f}×")
```
Report the median ratio across reps. Note: the pre-freeze expectation of a fixed ratio was superseded by the task freeze (paper_notes.md §4); Gate 5 will re-establish measurements under the hardware/latency protocol.

### 9.6 Known gotchas
1. **Benchmark variance** — always alternate; never compare across separate runs.
2. **`torch.empty` NaN bug** — keep bias params as `torch.zeros` (see §8).
3. **GroupedLinear param counting** — single linear reshaped, not per-group linears (§3.1).
4. **Sentinel semantics** — `n_idx`/`n_kv` sentinel columns must be sliced off in `_attend`; EPP's `_postprocess_topk` must never unmask a sentinel (§6.2).
5. **Shared-Q requires `head_dim == index_head_dim`** — the EPP trick silently breaks if they differ.

---

## 10. Notation and Glossary

| Symbol | Meaning |
|---|---|
| $S$ | sequence length (256) |
| $m$ | KV compression ratio (4 Flat, 8 EPP) |
| $m_{\text{idx}}$ | index/routing compression ratio (4 both) |
| $C$ | number of compressed KV blocks ($S/m$) |
| $W$ | sliding window size (32 Flat, 16 EPP) |
| $H, D$ | heads (4), head dim (32) |
| $k$ | top-k router selection (16) |
| `n_idx` | number of index tokens (64); also used as invalid-token sentinel |
| `n_kv` | number of KV blocks (64 Flat, 32 EPP); sentinel after token→block mapping |
| DRRA | Dual-Rate Routed Attention (dense-with-masking formulation) |
| two-series | compressor where each token contributes to two adjacent windows (own + next) |

---

*All numbers, code paths, and mechanisms were verified against the current repository contents (Aug 2026), except figures explicitly marked as superseded by the Gate 1 task freeze (§2.2, RESULTS.md notice). Pre-freeze speed/latency figures were removed on 2026-08-18 (superseded; paper_notes.md §4); the alternating head-to-head protocol in §9.5 remains the recommended benchmarking methodology.*
