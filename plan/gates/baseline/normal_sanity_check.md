# NormalAttention Wiring Sanity Check

**Context:** 5-seed frozen task run of `NormalTimeSeriesModel` (full causal attention) was notably worse than compressed variants (0.8416±0.08 vs 0.5967/0.6332). Before leaning on that direction, verify the attention wiring itself (mask leak / scaling / RoPE / causal structure). Gate-1 causality suite already passed future-invariance for Normal; this goes deeper into the attention math.

**Method:** `check_normal_wiring.py` (python3, torch 2.6.0, fp32). Repo hyperparams (model.py): hidden=128, heads=4, head_dim=32, q_lora=64, o_groups=4, o_lora=128; inputs B=2, sequence lengths S ∈ (32, 64, 256). Reference = naive causal masked attention (scores = QKᵀ/√d, additive −inf mask above diagonal, softmax, @V) with the same RoPE convention reimplemented from scratch (interleaved-pair rotation over the last `rope_head_dim` dims).

## Results

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Reference comparison vs naive causal attention | **PASS** | max\|module − naive_ref\| over 3 random runs per S (threshold 1e-3): S=32: **0.0**, S=64: **0.0**, S=256: **1.192093e-07**. Also 0.0 at all S with repo's `apply_rotary_pos_emb`-based ref. Note: the S=256 residual is seed-dependent fp32 accumulation noise (~1e-07). |
| 2a | Causality (weight-level) | **PASS** | max weight at future positions (j>i) = **0.000e+00** (exact); min present+past weight = 6.48e-04 (>0); zeros in probs = 3968/3968 = exactly S(S−1)/2 per head-row. |
| 2b | Causality (perturbation) | **PASS** | Perturbing future tokens j=16, j=31 (Δ=1.0, fresh random input): output invariance at positions i<j, max change = **0.000e+00** (< 1e-6); positions i≥j change by ≥ 2.10e-01 (perturbation effective). |
| 3 | RoPE consistency | **PASS** | Split: rope_head_dim = **8** (last dims), nope = 24, head_dim = 32 (`rope_head_dim = head_dim // 4`). Naive-vs-`apply_rotary_pos_emb`: 0.0 (q and kv). Nope part untouched: 0.0. Rotate-back (cos, −sin) inverse error: 2.4e-07 (fp32). inv_freq uses dim=rope_head_dim=8: exact match. |
| 4 | Tied K=V | **PASS** | `kv_proj` is a single Linear (out=32=head_dim); source `k, v = kv, kv`; k−v max diff = 0.0. Consistent — reference used tied K=V and matched exactly, so no untied mismatch. |
| 5 | Shape / dtype / NaN | **PASS** | out.shape = (2, 32, 128) = [B, S, hidden]; dtype = float32; NaN = 0; Inf = 0. |

## Verdict

**NormalAttention wiring is correct.** No mask leak, no scaling bug (√d = √32), correct causal structure (diagonal allowed, strict future blocked), RoPE applied to the last `rope_head_dim = head_dim//4 = 8` dims with the repo's `apply_rotary_pos_emb` convention, tied K=V consistent, rotate-back with (cos, −sin) matching CSA. The implementation is bit-identical to a from-scratch naive causal masked attention (max diff 0.0 at S=32 and S=64, 1.192093e-07 at S=256 — seed-dependent fp32 accumulation noise).

The worse val/test of the 5-seed Normal run is therefore not explained by an attention-wiring bug — it reflects the model/variant itself (e.g., full quadratic attention without compression/inductive bias on this task). Note: Gate-1 causality suite had already passed future-invariance for Normal; this check confirms the attention math end-to-end.

## Files
- Created: `check_normal_wiring.py` (verification script), `normal_sanity_check.md` (this report).
- Modified: none.
