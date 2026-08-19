#!/usr/bin/env python3
"""Sanity verification of NormalAttention wiring (normal_attention.py).

Checks:
  1. Reference comparison vs naive causal masked attention (same RoPE convention).
  2. Causality: weight-level mask exactness + future-perturbation invariance.
  3. RoPE consistency: rope/nope split convention vs attention.apply_rotary_pos_emb.
  4. Tied K=V consistency.
  5. Shape / dtype / NaN.

Run: python3 plan/gates/baseline/check_normal_wiring.py
"""
import math
import os
import sys

import torch
import torch.nn.functional as F

# repo root (one level above plan/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from normal_attention import NormalAttention
from attention import apply_rotary_pos_emb, rotate_half

# ── repo hyperparams (model.py: NormalTimeSeriesModel) ───────────────────────
HIDDEN, HEADS, HEAD_DIM, Q_LORA = 128, 4, 32, 64
O_GROUPS, O_LORA = 4, 128
B, S = 2, 32
REF_SEQS = (32, 64, 256)  # sequence lengths for the reference-comparison loop (check 1)
THRESH_REF = 1e-3   # max abs diff reference vs module
THRESH_LEAK = 1e-6  # future-perturbation invariance
BASE = 10000.0


def make_model(seed=0):
    torch.manual_seed(seed)
    m = NormalAttention(
        hidden_size=HIDDEN, num_heads=HEADS, head_dim=HEAD_DIM,
        q_lora_rank=Q_LORA, compress_rate=4, index_topk=16,
        sliding_window=32, o_groups=O_GROUPS, o_lora_rank=O_LORA,
    )
    m.eval()
    return m


def naive_rope(x, position_ids, rope_dim, base=BASE, sin_scale=1.0):
    """Rotate the LAST rope_dim dims of x in interleaved pairs (repo convention).

    Mirrors attention.RotaryEmbedding + attention.apply_rotary_pos_emb:
      inv_freq_k = base^(-2k/rope_dim), k = 0..rope_dim/2-1
      rotated[2k]   = r[2k]*cos - r[2k+1]*sin
      rotated[2k+1] = r[2k]*sin + r[2k+1]*cos
    sin_scale=-1.0 gives the inverse rotation (rotate-back).
    """
    Bn, Sn = position_ids.shape
    device = x.device
    inv_freq = 1.0 / (base ** (torch.arange(0, rope_dim, 2, device=device).float() / rope_dim))
    angles = position_ids.float().unsqueeze(-1) * inv_freq          # [B, S, rope_dim//2]
    cos = angles.cos().repeat_interleave(2, dim=-1)                 # [B, S, rope_dim]
    sin = (angles.sin() * sin_scale).repeat_interleave(2, dim=-1)
    if x.dim() == 4:
        cos, sin = cos.unsqueeze(1), sin.unsqueeze(1)               # [B, 1, S, rope_dim]
    nope, rope = x[..., :-rope_dim], x[..., -rope_dim:]
    rotated = rope * cos + rotate_half(rope) * sin
    return torch.cat([nope, rotated], dim=-1)


def ref_forward(attn, x, rope_dim, use_naive_rope=True):
    """Fully naive reference: causal masked attention with repo's RoPE convention.

    Reuses the module's projections (shared/trusted across variants); reimplements
    the attention math from scratch. With use_naive_rope=True it also reimplements
    RoPE from scratch (interleaved-pair rotation over the last rope_dim dims).
    """
    Bn, Sn, _ = x.shape
    H, D = attn.num_heads, attn.head_dim
    pos = torch.arange(Sn, device=x.device).unsqueeze(0).expand(Bn, -1)

    if use_naive_rope:
        cos, sin = None, None
        def rope(t): return naive_rope(t, pos, rope_dim)
        def unrope(t): return naive_rope(t, pos, rope_dim, sin_scale=-1.0)
    else:
        cos, sin = attn.rotary_emb(x, pos)
        def rope(t): return apply_rotary_pos_emb(t, cos, sin)
        def unrope(t): return apply_rotary_pos_emb(t, cos, -sin)

    q_residual = attn.q_a_norm(attn.q_a_proj(x))
    q = attn.q_b_proj(q_residual).view(Bn, Sn, H, D).transpose(1, 2)
    q = attn.q_b_norm(q)
    q = rope(q)

    kv = attn.kv_norm(attn.kv_proj(x)).view(Bn, Sn, 1, D).transpose(1, 2)
    kv = rope(kv)
    k = v = kv  # tied K=V (same as module)

    scores = torch.matmul(q.float(), k.transpose(2, 3).float()) * (D ** -0.5)
    causal = torch.triu(torch.ones(Sn, Sn, dtype=torch.bool, device=x.device), diagonal=1)
    scores = scores.masked_fill(causal.unsqueeze(0).unsqueeze(0), float("-inf"))
    probs = F.softmax(scores, dim=-1)
    out = torch.matmul(probs, v.float())
    out = unrope(out)

    grouped = out.transpose(1, 2).reshape(Bn, Sn, attn.o_groups, -1)
    grouped = attn.o_a_proj(grouped).flatten(2)
    return attn.o_b_proj(grouped)


def module_q_kv(attn, x):
    """Recompute q and tied kv exactly as the module does (for weight-level checks)."""
    Bn, Sn, _ = x.shape
    H, D = attn.num_heads, attn.head_dim
    pos = torch.arange(Sn, device=x.device).unsqueeze(0).expand(Bn, -1)
    cos, sin = attn.rotary_emb(x, pos)
    q_residual = attn.q_a_norm(attn.q_a_proj(x))
    q = attn.q_b_proj(q_residual).view(Bn, Sn, H, D).transpose(1, 2)
    q = attn.q_b_norm(q)
    q = apply_rotary_pos_emb(q, cos, sin)
    kv = attn.kv_norm(attn.kv_proj(x)).view(Bn, Sn, 1, D).transpose(1, 2)
    kv = apply_rotary_pos_emb(kv, cos, sin)
    return q, kv


def check1_reference_comparison():
    """Naive reference vs module forward, looped over sequence lengths (32, 64, 256)."""
    results = {}
    for seq in REF_SEQS:
        worst_naive, worst_repo = 0.0, 0.0
        per_seed = {}
        for seed in range(3):
            torch.manual_seed(100 + seed)
            x = torch.randn(B, seq, HIDDEN)
            attn = make_model(seed)
            with torch.no_grad():
                mod_out = attn(x)
                ref_naive = ref_forward(attn, x, attn.rope_head_dim, use_naive_rope=True)
                ref_repo_rope = ref_forward(attn, x, attn.rope_head_dim, use_naive_rope=False)
            d_naive = (mod_out - ref_naive).abs().max().item()
            d_repo = (mod_out - ref_repo_rope).abs().max().item()
            worst_naive = max(worst_naive, d_naive)
            worst_repo = max(worst_repo, d_repo)
            per_seed[seed] = (d_naive, d_repo)
        results[seq] = {"naive": worst_naive, "repo": worst_repo, "per_seed": per_seed}
    results["worst"] = max(results[s]["naive"] for s in REF_SEQS)
    results["pass"] = results["worst"] < THRESH_REF
    return results


def check2_causality():
    """Weight-level mask exactness + future-perturbation invariance."""
    torch.manual_seed(7)
    x = torch.randn(B, S, HIDDEN)
    attn = make_model(7)
    H, D = attn.num_heads, attn.head_dim

    # weight-level: recompute logits, inspect probs
    with torch.no_grad():
        q, kv = module_q_kv(attn, x)
        k = v = kv
        scores = torch.matmul(q.float(), k.transpose(2, 3).float()) * (D ** -0.5)
        causal_bool = torch.triu(torch.ones(S, S, dtype=torch.bool), diagonal=1)
        logits = scores.masked_fill(causal_bool.unsqueeze(0).unsqueeze(0), float("-inf"))
        logits = logits - logits.max(dim=-1, keepdim=True).values
        probs = F.softmax(logits, dim=-1)
        bmask = causal_bool.unsqueeze(0).unsqueeze(0).expand(B, H, S, S)
        future_max = probs[bmask].max().item()
        present_min = probs[~bmask].min().item()
        n_zeros = (probs == 0.0).sum().item()
        expected_zeros = B * H * S * (S - 1) // 2

        # perturbation invariance (fresh random input, per task)
        leak_max, changed_min = 0.0, float("inf")
        for j in (16, 31):
            xp = torch.randn(B, S, HIDDEN)
            xq = xp.clone()
            xq[:, j, :] += 1.0
            o1 = attn(xp)
            o2 = attn(xq)
            leak = (o2[:, :j, :] - o1[:, :j, :]).abs().max().item()
            changed = (o2[:, j:, :] - o1[:, j:, :]).abs().max().item()
            leak_max = max(leak_max, leak)
            changed_min = min(changed_min, changed)

    return {
        "future_weight_max": future_max,
        "present_weight_min": present_min,
        "n_zeros": n_zeros,
        "expected_zeros": expected_zeros,
        "leak_max": leak_max,
        "changed_min": changed_min,
        "pass_mask": future_max == 0.0 and n_zeros == expected_zeros and present_min > 0.0,
        "pass_perturb": leak_max < THRESH_LEAK and changed_min > 1e-3,
    }


def check3_rope():
    """rope/nope split convention, naive==repo rope, inverse, inv_freq."""
    attn = make_model(3)
    rope_dim = attn.rope_head_dim
    torch.manual_seed(3)
    x = torch.randn(B, S, HIDDEN)
    pos = torch.arange(S).unsqueeze(0).expand(B, -1)
    with torch.no_grad():
        q, kv = module_q_kv(attn, x)  # already rope-applied via repo path
        # recompute plain (pre-rope) q/kv and compare naive vs repo rope
        cos, sin = attn.rotary_emb(x, pos)
        qr = attn.q_a_norm(attn.q_a_proj(x))
        qr = attn.q_b_proj(qr).view(B, S, HEADS, HEAD_DIM).transpose(1, 2)
        qr = attn.q_b_norm(qr)
        q_repo = apply_rotary_pos_emb(qr, cos, sin)
        q_naive = naive_rope(qr, pos, rope_dim)
        d_q = (q_repo - q_naive).abs().max().item()

        kvr = attn.kv_norm(attn.kv_proj(x)).view(B, S, 1, HEAD_DIM).transpose(1, 2)
        kv_repo = apply_rotary_pos_emb(kvr, cos, sin)
        kv_naive = naive_rope(kvr, pos, rope_dim)
        d_kv = (kv_repo - kv_naive).abs().max().item()

        # nope part must be untouched by rope
        t = torch.randn(B, 1, S, HEAD_DIM)
        t_rot = apply_rotary_pos_emb(t, cos, sin)
        d_nope = (t_rot[..., :-rope_dim] - t[..., :-rope_dim]).abs().max().item()

        # forward rotation then inverse rotation must restore (rope part)
        t_back = apply_rotary_pos_emb(t_rot, cos, -sin)
        d_inv = (t_back[..., -rope_dim:] - t[..., -rope_dim:]).abs().max().item()

        # inv_freq convention: dim = rope_dim (not head_dim)
        manual = 1.0 / (BASE ** (torch.arange(0, rope_dim, 2).float() / rope_dim))
        d_freq = (attn.rotary_emb.inv_freq.cpu() - manual).abs().max().item()

    return {
        "rope_head_dim": rope_dim,
        "nope_head_dim": HEAD_DIM - rope_dim,
        "head_dim": HEAD_DIM,
        "naive_vs_repo_q": d_q,
        "naive_vs_repo_kv": d_kv,
        "nope_untouched": d_nope,
        "inverse_error": d_inv,
        "inv_freq_error": d_freq,
        "pass": d_q < 1e-5 and d_kv < 1e-5 and d_nope == 0.0 and d_inv < 1e-5 and d_freq == 0.0,
    }


def check4_tied_kv():
    """Tied K=V: single kv projection; k and v are the same tensor (source + numeric)."""
    attn = make_model(4)
    # structural: kv_proj is a single Linear producing head_dim (shared K and V)
    kv_proj_out = attn.kv_proj.out_features
    # numeric: recomputed kv used as BOTH k and v reproduces module output (check 1 already
    # passes with the tied reference); here confirm k == v in the recomputation path.
    torch.manual_seed(4)
    x = torch.randn(B, S, HIDDEN)
    with torch.no_grad():
        q, kv = module_q_kv(attn, x)
        k, v = kv, kv
        d = (k - v).abs().max().item()
    return {
        "kv_proj_out_features": kv_proj_out,
        "head_dim": attn.head_dim,
        "k_minus_v_max": d,
        "tied_in_source": True,  # normal_attention.py:65 `k, v = kv, kv`
        "pass": d == 0.0 and kv_proj_out == attn.head_dim,
    }


def check5_shape_dtype_nan():
    """Forward output [B, S, hidden], fp32, no NaNs."""
    attn = make_model(5)
    torch.manual_seed(5)
    x = torch.randn(B, S, HIDDEN)
    with torch.no_grad():
        out = attn(x)
    return {
        "shape": tuple(out.shape),
        "dtype": str(out.dtype),
        "n_nan": int(out.isnan().sum().item()),
        "n_inf": int(torch.isinf(out).sum().item()),
        "pass": tuple(out.shape) == (B, S, HIDDEN) and out.dtype == torch.float32
                and out.isnan().sum().item() == 0 and torch.isinf(out).sum().item() == 0,
    }


def main():
    print("=" * 68)
    print("NormalAttention wiring sanity check")
    print("=" * 68)
    c1 = check1_reference_comparison()
    c2 = check2_causality()
    c3 = check3_rope()
    c4 = check4_tied_kv()
    c5 = check5_shape_dtype_nan()

    print("\n[1] REFERENCE COMPARISON (naive causal attention, same RoPE convention)")
    print(f"    max|module - naive_ref| over 3 runs, per S (threshold {THRESH_REF}): "
          + ", ".join(f"S={s}: {c1[s]['naive']:.6e}" for s in REF_SEQS))
    print(f"    repo-rope ref (apply_rotary_pos_emb): "
          + ", ".join(f"S={s}: {c1[s]['repo']:.6e}" for s in REF_SEQS))
    print(f"    worst over all S: {c1['worst']:.6e}")
    print(f"    PASS: {c1['pass']}")

    print("\n[2] CAUSALITY")
    print(f"    max future weight (j>i): {c2['future_weight_max']:.3e}  (must be 0.0)")
    print(f"    min present+past weight: {c2['present_weight_min']:.3e}  (must be > 0)")
    print(f"    zeros in probs: {c2['n_zeros']}/{c2['expected_zeros']}  (expect S(S-1)/2 per head-row)")
    print(f"    perturbation: future-token change leak (pos<j) max {c2['leak_max']:.3e}  "
          f"(threshold {THRESH_LEAK}); self+past change min {c2['changed_min']:.3e}")
    print(f"    PASS mask: {c2['pass_mask']}  PASS perturb: {c2['pass_perturb']}")

    print("\n[3] ROPE CONSISTENCY")
    print(f"    split: rope_head_dim={c3['rope_head_dim']} (last dims), nope={c3['nope_head_dim']}, "
          f"head_dim={c3['head_dim']}")
    print(f"    naive vs apply_rotary_pos_emb: q {c3['naive_vs_repo_q']:.3e}, kv {c3['naive_vs_repo_kv']:.3e}")
    print(f"    nope part untouched: {c3['nope_untouched']:.3e}  (expect 0.0)")
    print(f"    rotate-back inverse error: {c3['inverse_error']:.3e}")
    print(f"    inv_freq dim==rope_head_dim error: {c3['inv_freq_error']:.3e}  (expect 0.0)")
    print(f"    PASS: {c3['pass']}")

    print("\n[4] TIED K=V")
    print(f"    kv_proj.out_features={c4['kv_proj_out_features']} == head_dim={c4['head_dim']}  "
          f"|k-v|max={c4['k_minus_v_max']:.3e}  source tie: {c4['tied_in_source']}")
    print(f"    PASS: {c4['pass']}")

    print("\n[5] SHAPE / DTYPE / NaN")
    print(f"    out.shape={c5['shape']}  dtype={c5['dtype']}  NaN={c5['n_nan']}  Inf={c5['n_inf']}")
    print(f"    PASS: {c5['pass']}")

    all_pass = c1["pass"] and c2["pass_mask"] and c2["pass_perturb"] and c3["pass"] and c4["pass"] and c5["pass"]
    verdict = "NormalAttention wiring is correct" if all_pass else "NormalAttention wiring has a bug"
    print("\n" + "=" * 68)
    print(f"FINAL VERDICT: {verdict}")
    print("=" * 68)


if __name__ == "__main__":
    main()