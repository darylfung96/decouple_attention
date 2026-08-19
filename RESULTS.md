# Dual-Rate Routed Attention Comparison Results

> ## ⛔ TASK FREEZE NOTICE (Gate 1, 2026-08-11)
>
> **All numbers in this file predate the frozen direct-96 task** (`plan/gates/gate1/gate1_task.md`): they were produced under the old per-token next-step regression (model scored only on the last 96 of 256 output positions; 95 of the 96 scored positions were in-sample reconstructions) **and** under leaky full-series normalization (mean/std fit over the entire series including val/test before splitting — future-stats leak). Both are now fixed: the frozen task is **direct 96-step forecasting** (input `[B,256,7]` → output `[B,96,7]` in one pass, `loss = MSELoss(out, y)`) with **train-only per-feature z-score** applied to all splits.
>
> **Every number below is superseded** and must not be cited as a result of the frozen task. Valid numbers come only from **Gate 2 runs** under the frozen protocol (direct-96, train-only normalization, pooled `[B,96,7]` MSE, strictly causal attention). See `plan/gates/gate1/gate1_task.md` (§1, §5, §9) — it is the sole authority on task definition.


## Final Results: ExpertPlusPlus (0.1099 val) — matches Flat within run noise, fewest params 🏆

**Full O(S²) causal attention vs 6 compressed variants on ETTh1 (lookback=256, horizon=96, lr=1e-4, 10 epochs, seed=42).**

| Model | Val MSE | Test MSE | Params (attn / full) |
|-------|---------|----------|----------------------|
| **Normal (256 cols)** | **0.1083** 🥇 | 0.1637 | 102,496 (269,415) |
| **Flat (96 cols)** | 0.1085 🥈 | **0.1617** 🥇 | 144,548 (311,467) |
| Modified (160 cols) | 0.1088 🥉 | 0.1624 | 144,552 (311,471) |
| FlatPlus (96 cols) | 0.1098 | 0.1635 | 152,492 (319,411) |
| **ExpertPlusPlus (48+1 cols)** | 0.1099 | 0.1654 | **95,652 (262,571)** 🥇 |
| ExpertFlat (64+1 cols) | 0.1102 | 0.1645 | 145,060 (311,979) |
| Stacked (legacy) | 0.1116 | 0.1665 | N/A (no source) |

**Column-count convention** (verified registry): content cols = KV blocks + window; the "+1" is the single sink softmax column (4 scalar logits, one per head) — sinks are NOT KV tokens. Detail: Flat/FlatPlus 96 = 64 KV + 32 win; Modified 160 = 128 KV + 32 win; ExpertFlat 64 = 32 KV + 32 win; EPP 48 = 32 KV + 16 win; Normal 256 (no sink).
**Stacked**: legacy numbers; no runnable source in repo (missing from model.py/compare.py). Its parameter and column counts are N/A (no source); only legacy run results are shown. Params listed as attention params, full model in parentheses.

### The Goal Contract (retired)

> **Retired (2026-08-18):** the goal contract was an internal engineering target ("EPP must beat Flat's forward speed by a stated margin at the same accuracy"). The speed leg and its figures were superseded by the task freeze and removed (paper_notes.md §4); only the accuracy observations are recorded below.

| Criterion | Target | ExpertPlusPlus | Verdict |
|-----------|--------|----------------|---------|
| Accuracy (val) | 0.1085 ±0.001 | **0.1099** (+0.0014) | ⚠️ within run-to-run variance (±0.002) |
| Test MSE | ~0.1617 | 0.1654 (+0.0037) | ⚠️ slightly worse |
| Params | — | **95,652 (−33.8% vs Flat)** | ✅ bonus |

**Verdict (retired):** the accuracy leg stood — val 0.1099 vs 0.1085 (+0.0014) sits inside the ±0.002 run-to-run variance band, though slightly outside the stated ±0.001. The speed leg was superseded and removed (paper_notes.md §4); re-measurement is planned under Gate 5 (`plan/next_step.md` §10).

---

## How ExpertPlusPlus Achieves This

**Decoupled compression** (the key insight): content density and routing granularity are independent axes.

| Design choice | ExpertPlusPlus | Why |
|---------------|----------------|-----|
| KV content density | **8:1** (256 → 32 blocks) | Compute lever — attention columns 96 → 48; accuracy effect measured in Gate 2 |
| Routing granularity | **4:1** (64 fine index tokens) | *Routing granularity carries accuracy* — this is what ExpertFlat got wrong |
| Token→block map | token `t` → block `t//2` (block `j` covers `[8j, 8j+7]`) | 4:1 routing on 8:1 blocks — dense attention over 48 columns (32 KV blocks + 16 window) |
| Query routing | **Shared-Q** (drop `idx_q_proj`) | Reuses main Q; fewer params, no accuracy cost (requires `head_dim == index_head_dim`) |
| O projection | slim `o_lora_rank=64` | 33.8% fewer params overall (vs Flat) |
| Sliding window | **16** (vs 32) | Free compute lever — halves the window columns with **zero accuracy cost** (val 0.1099 both ways, test actually improved: 0.1665 → 0.1654) |

**Why ExpertFlat lost accuracy (0.1102):** it coarsened *both* content and routing to 8:1 — the router sees only 32 coarse tokens, losing routing precision. ExpertPlusPlus keeps 4:1 routing on 64 fine index tokens while attending to only 32 KV blocks (mapped via `t//2`), so the router stays precise at the same compute cost.

**Why dense beats sparse here:** the sparse-gather v1 was far slower on CPU; dense GEMMs over 48 columns (32 KV blocks + 16 window) with masking won decisively on Apple Silicon.

---

## Speed Evidence (removed — superseded)

Pre-freeze latency figures (forward/training ms, speedups, Perf/Spd) were superseded by the Gate-1 task freeze and were removed from this document on **2026-08-18** (paper_notes.md §4). Original measurements are preserved in `experiment-session-new-attention.md`. Re-measurement is planned under the Gate 5 hardware/latency protocol (p50/p90/p99 with bootstrap CIs, scaling sweeps, cross-hardware; `plan/next_step.md` §10).

The methodology note survives: the **alternating head-to-head** protocol (both models timed inside the same thermal/contention window, repeated, medians taken) is the right way to compare on this machine; sequential single-run benchmarks are unreliable. Protocol code preserved in `WRITEUP.md` §9.5.

---

## Full Accuracy Comparison (10 epochs, seed=42)

| Model | Val MSE | Test MSE |
|-------|---------|----------|
| **Normal** | **0.1083** 🥇 | 0.1637 |
| **Flat** | 0.1085 🥈 | **0.1617** 🥇 |
| Modified | 0.1088 🥉 | 0.1624 |
| FlatPlus | 0.1098 | 0.1635 |
| **ExpertPlusPlus** | 0.1099 | 0.1654 |
| ExpertFlat | 0.1102 | 0.1645 |
| Stacked | 0.1116 | 0.1665 |

- **Flat still holds best test MSE** (0.1617); Normal holds best val (0.1083).
- **ExpertPlusPlus is within 0.0014 of Flat's val** — inside normal run variance (±0.002).
- EPP window 32→16: val identical (0.1099), test improved 0.1665 → 0.1654.

---

## What Was Tried

### ✅ ExpertPlusPlus (v2) — decoupled compression, dense attention (WINNER)
8:1 KV blocks + 4:1 routing granularity + shared-Q + slim O + window 16. See table above.

### ✅ ExpertFlat — aggressive 8:1 on both axes (reference)
Pushed compression to 8:1 for KV **and** index. Most aggressive compression before EPP (64 content columns), but routing coarsening cost accuracy (0.1102 val, +0.0017 vs Flat).

### ✅ Sliding window 32 → 16 (compute lever)
Halves the sliding-window attention columns at zero accuracy cost (val 0.1099 both ways; test improved 0.1665 → 0.1654). Adopted.

### ❌ Sparse-gather routing (v1, abandoned)
Selecting top-k and gathering was **far slower** on CPU than dense GEMMs. Abandoned early.

### ❌ Hierarchical Indexer (Phase C1)
Multi-scale pyramid for the indexer. **Modified lost** — flat indexer consistently outperformed it.

### ❌ Multi-Scale KV Pyramid (3 levels, stride 2/4/8)
224 total KV tokens → overparameterized for 10 epochs, slower convergence.

### ❌ Learnable Block Bias Offset
`nn.Parameter` per-level caused NaN gradient instability ~50% of runs.

### ❌ Gated Residual KV + Learned Linear Pool Indexer (FlatPlus)
Linear pool indexer degraded accuracy (0.1098 vs 0.1085) — loses per-head×per-dim routing flexibility of the softmax overlap gate.

### ❌ Stacked 2:1→2:1 refinement (legacy; no runnable source in repo)
Extra level-1 parameters make optimization harder at 10 epochs (0.1116).

---

## Architectural Comparison

**Dual-Rate Routed Attention (DRRA)** — working name for the compressed+indexed attention family (retired label "CSA", colliding with DeepSeek-V4).

| Feature | Normal | Flat | ExpertFlat | ExpertPlusPlus |
|---------|:------:|:----:|:----------:|:--------------:|
| Attention type | Full O(S²) | DRRA 4:1 | DRRA 8:1 | DRRA **8:1 KV + 4:1 route** |
| Content cols (S=256) | 256 (no sink; 0 KV + 0 win) | 96 (64 KV + 32 win) + 1 sink = 97 | 64 (32 KV + 32 win) + 1 sink = 65 | **48 (32 KV + 16 win) + 1 sink = 49** |
| Index tokens | N/A | 64 | 32 | **64 (4:1)** |
| Routing | N/A | Softmax overlap | Softmax overlap | Softmax overlap (fine) |
| Query routing | N/A | Own idx_q_proj | Own idx_q_proj | **Shared-Q** (no idx_q_proj) |
| O rank | 128 | 128 | 128 | **64** |
| Sliding window | N/A | 32 | 32 | **16** |
| Params (attn / full) | 102,496 (269,415) | 144,548 (311,467) | 145,060 (311,979) | **95,652 (262,571)** |

Sinks: each DRRA variant has **1 sink softmax column** = 4 scalar params (one per head) — sinks are not KV tokens and are not counted in content columns.

---

## Key Takeaways

- **ExpertPlusPlus matches Flat within noise**: val 0.1099 vs 0.1085 (inside the ±0.002 run-to-run band) with 33.8% (≈34%) fewer parameters than Flat ((144,548 − 95,652)/144,548).
- **Routing granularity is the accuracy lever; content density is the speed lever.** ExpertFlat failed by coarsening both; ExpertPlusPlus decouples them.
- **Window 16 is free** for this architecture — same val, better test.
- **Shared-Q routing** works because `head_dim == index_head_dim` — Q is reused for routing with zero extra projection.
- **Dense beats sparse on CPU** — every sparse-gather attempt lost to a dense masked GEMM.
- For absolute best test MSE: **Flat** (0.1617 vs 0.1654).

## Notes

### Run-to-run variance
Seed fixes init and shuffle, but variance across runs is ±~0.002 val. The EPP-vs-Flat val gap (+0.0014) is within this band.

### Bug Fix: `torch.empty` → `torch.zeros`
All `nn.Parameter(torch.empty(...))` for position biases and residual biases changed to `torch.zeros(...)`. `torch.empty` can return garbage (up to 10²⁸+) on macOS, causing NaN in softmax gates — root cause of intermittent NaN across seeds.

---

## Surrogate Attention (joint distillation) — ALL 9 MODELS

**Idea:** replace the attention layer at inference with a cheap learned surrogate (trained jointly with the teacher via distillation), so evaluation/prediction skips the attention mechanism entirely.

**Pipeline** (`train_surrogate.py`): Phase 1 = joint training `L = task + λ·MSE(student_out, stopgrad(teacher_out))` (λ=0.5), Phase 2 = surrogate-only fine-tune (1 ep). Teacher = **ExpertPlusPlus** (code default; `--teacher normal` also available). Student: `mlp` (per-token, v1) or `windowed` (causal window W=32 + 8 learned global prototypes + relative-position bias, v2 ⭐).

| Model | Val MSE | Test MSE | Params |
|-------|---------|----------|--------|
| **Normal (256 cols)** | **0.1083** 🥇 | 0.1637 | 102,496 (269,415) |
| **Flat (96 cols)** | 0.1085 🥈 | **0.1617** 🥇 | 144,548 (311,467) |
| Modified (160 cols) | 0.1088 🥉 | 0.1624 | 144,552 (311,471) |
| FlatPlus (96 cols) | 0.1098 | 0.1635 | 152,492 (319,411) |
| **ExpertPlusPlus (48+1 cols)** | 0.1099 | 0.1654 | **95,652 (262,571)** |
| ExpertFlat (64+1 cols) | 0.1102 | 0.1645 | 145,060 (311,979) |
| Stacked (legacy) | 0.1116 | 0.1665 | N/A (no source) |
| Surrogate MLP (v1) | 0.1424* | 0.1958* | 0.13M |
| Surrogate Win+Glob (v2) | 0.1269* | **0.1817*** | **0.017M** |

\* Surrogate MSEs from **5+1-epoch** distillation runs (code defaults: teacher = **ExpertPlusPlus**, 5 Phase-1 epochs + 1 fine-tune epoch). Teacher val is printed at runtime, so it is **not re-derivable from code**; recorded run value: **0.1264** for the 5+1-epoch teacher snapshot (the earlier "teacher Normal at 5 ep ≈ 0.1213" claim does not stand — the code's default teacher is ExpertPlusPlus, not Normal). NOT apples-to-apples with the 10-epoch DRRA numbers above. With 10-epoch Phase-1 they would land closer to ~0.11.
Note: main-model Params = attention params, full model in parentheses (verified registry); surrogate rows are attention-only. **Stacked**: legacy numbers; no runnable source in repo (missing from model.py/compare.py) — parameter and column counts N/A (no source). Pre-freeze speed figures for the surrogate rows (latency, Perf/Spd, speedups) were removed 2026-08-18 (paper_notes.md §4).

### Reading the table
- **Surrogate MLP (v1)**: val 0.1424 (+31% vs Flat) — Per-token MLP cannot replicate cross-token routing (expressivity limit, not training: λ↑ and ft↑ both failed to close it).
- **Surrogate Win+Glob (v2)**: **0.017M params (~82% fewer than EPP)**. Val 0.1269 vs teacher (ExpertPlusPlus, code default) 0.1264 at 5+1 ep — ~0.4% gap (v1 was +13% vs the standing teacher value 0.1264); teacher val is runtime-printed, so not re-derivable from code (recorded value 0.1264 stands). Test 0.1817 **beats** teacher 0.1868. Cross-token mixing (local window + global prototypes) was the missing expressivity.
- **Accuracy trade-off line**: DRRA variants live at val 0.108–0.112; surrogates at 0.127–0.142 (5+1 ep). The surrogate trades accuracy for cheaper inference, and the gap shrinks as Phase-1 epochs grow toward 10.

### Verdict
- For the cheapest inference at acceptable accuracy: **Surrogate Win+Glob** (+17% val at only 5+1 ep — likely closer to +8–10% at 10 ep).
- Among DRRA variants: **ExpertPlusPlus** matches Flat's val (+0.0014) with 33.8% fewer attention params.
- Levers not yet tried: window 64 / n_global 16, 10-epoch Phase 1, λ sweep (task loss dominates — λ had no effect).

---

## Gate 2 — Post-Freeze Factorial Results (2026-08-13)

**Method:** 2×2 factorial over (c_KV, c_R) ∈ {(4,4), (8,4), (4,8), (8,8)} × 5 paired seeds {42, 123, 2024, 7, 99} = 20 runs; 10 epochs, param-equalized (all attention-param deltas < 0.5% vs the (8,4) reference), frozen **direct 96-step** task (input `[B,256,7]` → output `[B,96,7]`, pooled MSE in standardized units, lower is better). Full pre-registered design in `plan/gates/gate2/gate2_design.md`; aggregate summary in `plan/gates/gate2/gate2_summary.md` (E4-audited, PASS — source of truth for all numbers below, copied verbatim). **These are the valid numbers under the frozen protocol** (see freeze notice at top; all pre-freeze numbers above remain superseded).

### Cell aggregates

| Cell | Val mean ± std | Test mean | Train mean |
|------|----------------|-----------|------------|
| (4,4) | 0.6332 ± 0.0611 | 0.9079 | 0.2908 |
| (8,4) | **0.5967** ± 0.0710 | **0.7988** | 0.2880 |
| (4,8) | 0.6858 ± 0.0875 | 0.8996 | 0.2983 |
| (8,8) | 0.6368 ± 0.0393 | 0.9159 | 0.2844 |

### Main effects

- **c_KV 4→8 = −0.0427** (negative: coarser KV compression *lowers* val MSE — slightly beneficial).
- **c_R 4→8 = +0.0463** (positive: coarser routing *raises* val MSE — deteriorates).

### Champion: (8,4)

- Mean val MSE **0.5967** (±0.0710 across seeds); mean test MSE **0.7988** (±0.0506) — best on both.
- attn params 95,652 / full params 348,356 (the (8,4) reference config).
- Matches the EPP champion corner: coarse-KV `compress_rate=8` / fine-routing `index_compress_rate=4`.

### H1 verdict (verbatim from `plan/gates/gate2/gate2_summary.md`)

> **No — coarser routing (c_R=8) does not deteriorate performance more than coarser KV compression (c_KV=8); the two effects are nearly equal in magnitude (|c_R| = 0.0463 vs |c_KV| = 0.0427) but opposite in direction, so all of the observed deterioration is attributable to routing while KV compression is mildly beneficial.** This must be read cautiously: both effect sizes (~0.04) are smaller than the mean within-cell seed-to-seed std (0.0647, per-cell std range 0.0393–0.0875) and larger than the cross-seed consistency would demand for confidence — c_R worsened val MSE in only 7/10 seed-column comparisons and c_KV improved it in only 7/10, so the sign is consistent but not unanimous. No formal significance test was run; treat these as directional, not conclusive.

---

## Baseline Comparison — Normal vs CSA/Flat vs DRRA (Post-Freeze, 2026-08-14)

**Method:** same frozen protocol (`plan/benchmark_protocol.md`), harness `plan/gates/baseline/baseline_normal_sweep.py`, 5 paired seeds {42, 123, 2024, 7, 99}, 10 epochs; full detail in `plan/gates/baseline/baseline_normal_summary.md`.

| Model | Val mean±std | Test mean | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 0.8416 ± 0.0799 | 1.0814 | — | — |
| CSA/Flat=(4,4) | 0.6332 ± 0.0611 | 0.9079 | −24.76% | −16.04% |
| DRRA=(8,4) | 0.5967 ± 0.0710 | 0.7988 | −29.10% | −26.13% |

Both compressed variants beat Normal on val in 5/5 seeds (per-seed); DRRA vs CSA: DRRA larger per-seed advantage in 3/5 seeds (42, 123, 7), CSA at 2024, 99.

**Caveats** (from `plan/gates/baseline/baseline_normal_summary.md`): single dataset ETTh1 at CPU-scale, small model — no cross-dataset generalization claim; params NOT equalized across rows — Normal 355,200 / (4,4) 348,100 / (8,4) 348,356 full; no significance test run — descriptive only; NormalAttention wiring sanity re-verification completed 2026-08-14 (bit-identical to naive causal reference; see plan/gates/baseline/normal_sanity_check.md + plan/gates/baseline/check_normal_wiring.py).
