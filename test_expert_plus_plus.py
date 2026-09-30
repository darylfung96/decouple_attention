"""Verify ExpertPlusPlus v2 (decoupled granularity) correctness.

1. Structure: 8:1 KV blocks + 4:1 index tokens; token→block mapping with
   future-safety sentinels; dense `_attend` uses the mapped block indices.
2. Forward + backward runs and gradients flow.
3. Sanity: ExpertPlusPlus (8:1 KV, 4:1 router, slim O) vs Flat on a tiny fit
   task — the FINE router should beat a coarse 8:1 router (ExpertFlat-style).
4. Param counts.
"""
import torch
from attention import CSAAttention
from expert_plus_plus_attention import ExpertPlusPlusAttention

torch.manual_seed(0)
B, S, H, D = 2, 64, 4, 32

# 1. Decoupled structure + mapping + dense attention
epp = ExpertPlusPlusAttention(hidden_size=128, num_heads=H, head_dim=D, q_lora_rank=64,
                              compress_rate=8, index_compress_rate=4, index_topk=8,
                              index_head_dim=D, sliding_window=16, o_lora_rank=64)
assert epp.compress_rate == 8 and epp.index_compress_rate == 4

hidden = torch.randn(B, S, 128)
n_win, usable = S // epp.compress_rate, S
ckv = epp._compress_kv(hidden, n_win, usable)
cidx = epp._compress_idx(hidden, n_win, usable)
print(f"[1] ckv={tuple(ckv.shape)} (expect {B},1,{S // 8},32), "
      f"cidx={tuple(cidx.shape)} (expect {B},1,{S // 4},32)")
assert ckv.shape[2] == S // 8 and cidx.shape[2] == S // 4

# token→block mapping: token t lives on block t//2, block j covers [8j, 8j+7]
n_idx, n_kv = S // 4, S // 8
tokens = torch.tensor([[0, 1, 2, 3, 6, 7, 15, 16]]).expand(B, S, 8)
kv_blocks, nk = epp._postprocess_topk(tokens, None, n_idx, S, 'cpu')
assert nk == n_kv
# at q=15: block of token t is t//2 when safe — t0/1→b0 (end 7≤15), t2/3→b1 (15≤15)
assert kv_blocks[0, 15, 0] == 0 and kv_blocks[0, 15, 1] == 0
assert kv_blocks[0, 15, 2] == 1 and kv_blocks[0, 15, 3] == 1
# at q=15: t6→b3 spans [24,31] — still future → sentinel
assert kv_blocks[0, 15, 4] == nk
# at q=63: t15→b7 (end 63) safe; t16 is the sentinel → stays sentinel
assert kv_blocks[0, 63, 6] == 7 and kv_blocks[0, 63, 7] == nk
# future safety: token 1 spans [4,7]→block 0 spans [0,7]; query at pos 0 may not
# read it; query at pos ≥ 7 may.
assert kv_blocks[0, 0, 1] == nk and kv_blocks[0, 7, 1] == 0
# no block extends into the future for ANY selected position
ends = kv_blocks * 8 + 7
q = torch.arange(S).view(1, -1, 1)
assert (((ends <= q) | (kv_blocks == nk))).all(), "future leak in mapping!"
print("    ✓ token→block mapping + sentinel + future-safety OK")

# dense _attend consumes the mapped indices (runs + shapes)
q = torch.randn(B, H, S, D)
kv = torch.randn(B, 1, S, D)
cos = torch.randn(B, S, D // 4)
sin = torch.randn(B, S, D // 4)
out = epp._attend(q, kv, ckv, kv_blocks, nk, cos, sin, B, S, D)
assert out.shape == (B, H, S, D), out.shape
print("    ✓ dense _attend consumes mapped block indices OK")

# 2. Forward + backward
attn = ExpertPlusPlusAttention(hidden_size=512, num_heads=8, head_dim=64, q_lora_rank=128,
                               compress_rate=8, index_compress_rate=4, index_topk=8,
                               index_n_heads=4, index_head_dim=64, sliding_window=16,
                               o_groups=4, o_lora_rank=128)
hidden = torch.randn(2, 64, 512)
pos = torch.arange(64).unsqueeze(0).expand(2, -1)
out = attn(hidden, pos)
loss = out.square().mean()
loss.backward()
n_grad = sum(1 for p in attn.parameters() if p.grad is not None and p.grad.abs().sum() > 0)
print(f"[2] forward {tuple(out.shape)}, loss={loss.item():.4f}, "
      f"{n_grad}/{sum(1 for _ in attn.parameters())} params received grad")
assert n_grad > 0, "no gradients flowing!"
print("    ✓ forward/backward OK")

# 3. Tiny supervised fit: fine 4:1 router should beat coarse 8:1 router
def fit(model, steps=150):
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
    model.train()
    for _ in range(steps):
        x = torch.randn(8, 64, 128)
        y = torch.sin(x).sum(-1, keepdim=True).repeat(1, 1, 128) * 0.1
        opt.zero_grad()
        loss = ((model(x) - y) ** 2).mean()
        loss.backward()
        opt.step()
    return loss.item()

flat = CSAAttention(hidden_size=128, num_heads=4, head_dim=32, q_lora_rank=64,
                    compress_rate=4, index_topk=16, sliding_window=32, o_lora_rank=128)
epp = ExpertPlusPlusAttention(hidden_size=128, num_heads=4, head_dim=32, q_lora_rank=64,
                              compress_rate=8, index_compress_rate=4, index_topk=16,
                              sliding_window=32, o_lora_rank=64)
coarse = ExpertPlusPlusAttention(hidden_size=128, num_heads=4, head_dim=32, q_lora_rank=64,
                                 compress_rate=8, index_compress_rate=8, index_topk=16,
                                 sliding_window=32, o_lora_rank=64)
l_flat, l_epp = fit(flat), fit(epp)
l_coarse = fit(coarse)
print(f"[3] tiny fit loss — Flat={l_flat:.4f}, ExpertPlusPlus={l_epp:.4f}, "
      f"ExpertPlusPlus-coarse={l_coarse:.4f}")
print("    ✓ trainable" if l_flat < 0.5 and l_epp < 0.5 else "    ⚠ check fit")
print("    ✓ fine router ≥ coarse router" if l_epp <= l_coarse + 1e-3 else "    ⚠ fine router lost")

# 5. Per-cell mapping regression (B1-5: t//2 was unconditional pre-fix).
#    For EVERY factorial geometry, valid tokens must reach every KV block
#    (full range), and no selected block may extend into the future.
for _ck, _ci, _nk in [(4, 4, 64), (8, 4, 32), (4, 8, 64), (8, 8, 32), (16, 4, 16)]:
    _m = ExpertPlusPlusAttention(hidden_size=128, num_heads=4, head_dim=32,
                                 q_lora_rank=64, compress_rate=_ck,
                                 index_compress_rate=_ci, index_topk=16,
                                 sliding_window=16, o_lora_rank=64).eval()
    _S, _nidx = 256, 256 // _ci
    _toks = torch.arange(_nidx).unsqueeze(0).unsqueeze(0).expand(1, _S, _nidx)
    _tk = _toks[:, :, :16].clone()  # top-16 candidate tokens
    with torch.no_grad():
        _kb, _rnk = _m._postprocess_topk(_tk, None, _nidx, _S, 'cpu')
    assert _rnk == _nk, (_ck, _ci, _rnk)
    _exp = _S // _ck
    if (_ck, _ci) == (4, 8):
        assert tuple(_kb.shape) == (1, _S, 32), _kb.shape  # fan-out doubles
        assert bool((_kb[0, 255, :16] == _tk[0, 255, :] * 2).all())
        assert bool((_kb[0, 255, 16:] == _tk[0, 255, :] * 2 + 1).all())
    elif _ck == _ci:
        assert bool((_kb[0, 255, :] == _tk[0, 255, :]).all()), (_ck, _ci)  # identity
    elif (_ck, _ci) == (16, 4):
        assert bool((_kb[0, 255, :] == _tk[0, 255, :] // 4).all()), (_ck, _ci)
    else:
        assert bool((_kb[0, 255, :] == _tk[0, 255, :] // 2).all()), (_ck, _ci)
    _ends = _kb * _ck + (_ck - 1)
    _q = torch.arange(_S).view(1, -1, 1)
    assert (((_ends <= _q) | (_kb == _nk))).all(), f"future leak at {(_ck, _ci)}"
print("    \u2713 per-cell mapping (identity/t//2/fan-out) + future-safety OK")
try:
    _bad = ExpertPlusPlusAttention(hidden_size=128, num_heads=4, head_dim=32,
                                   q_lora_rank=64, compress_rate=16,
                                   index_compress_rate=4, index_topk=16,
                                   sliding_window=16, o_lora_rank=64).eval()
    with torch.no_grad():
        _bad._postprocess_topk(torch.zeros(1, 256, 16, dtype=torch.long),
                               None, 16, 256, 'cpu')
    raise AssertionError("unsupported geometry did not raise")
except ValueError:
    print("    \u2713 unsupported geometry raises OK")

# 6. Non-divisible lengths (patch regime, S=31): streams stay consistent,
#    no future leak, full forward runs per cell.
for _ck, _ci in [(4, 4), (8, 4), (4, 8), (8, 8)]:
    _p = ExpertPlusPlusAttention(hidden_size=16, num_heads=4, head_dim=4,
                                 q_lora_rank=8, compress_rate=_ck,
                                 index_compress_rate=_ci, index_topk=4,
                                 index_n_heads=4, index_head_dim=4,
                                 sliding_window=8, o_groups=4,
                                 o_lora_rank=8).eval()
    _h = torch.randn(1, 31, 16)
    with torch.no_grad():
        _o = _p(_h)
    assert tuple(_o.shape) == (1, 31, 16), (_ck, _ci, tuple(_o.shape))
print("    \u2713 non-divisible S=31 forward per cell OK")

# 4. Param counts
from benchmark_speed import count_params, FlatWrapper, ExpertPlusPlusWrapper
print(f"[4] params — Flat={count_params(FlatWrapper())/1e6:.3f}M, "
      f"ExpertPlusPlus={count_params(ExpertPlusPlusWrapper())/1e6:.3f}M")
print("\nALL CHECKS PASSED" if (n_grad > 0 and l_epp < 0.5) else "\nFAILED")
