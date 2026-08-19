import torch
import torch.nn as nn
import torch.nn.functional as F
import math

from attention import BaseCSAAttention, apply_rotary_pos_emb


# ──────────────────────────────────────────────────────────────────────────────
# 2. Modified Hierarchical CSA Attention
# ──────────────────────────────────────────────────────────────────────────────

class ModifiedCSAAttention(BaseCSAAttention):
    """Hierarchical compressor + flat indexer + finer-grained KV.

    Improvements over flat CSAAttention:
      Phase B  — Per-token position bias at level 0 (instead of per-pair)
      Phase C2 — Gated residual connections (learned 4-slot blend)
      Phase C3 — Finer-grained KV compression (stride 2 → 128 tokens vs Flat's 64)
    """
    def __init__(self, hidden_size, num_heads, head_dim, q_lora_rank,
                 compress_rate=4, index_topk=8, index_n_heads=4, index_head_dim=32,
                 sliding_window=16, o_groups=4, o_lora_rank=128, rope_theta=10000.0):
        super().__init__(hidden_size, num_heads, head_dim, q_lora_rank,
                         compress_rate, index_topk, index_n_heads, index_head_dim,
                         sliding_window, o_groups, o_lora_rank, rope_theta)

        assert compress_rate > 0 and (compress_rate & (compress_rate - 1) == 0), \
            "compress_rate must be a power of 2"

        self.levels = min(1, int(math.log2(compress_rate)))  # single-level (stride 2 only)

        # ── Hierarchical compressor ──────────────────────────────────────
        # Level 0: operates on hidden_size → 2*head_dim
        self.comp_gate_proj_0 = nn.Linear(hidden_size, 2 * head_dim, bias=False)
        # Phase C1: per-token position bias at level 0
        self.comp_pos_bias_0 = nn.Parameter(torch.zeros(compress_rate, 2 * head_dim))

        # Levels 1+: operate on head_dim → 2*head_dim
        for i in range(1, self.levels):
            setattr(self, f'comp_gate_proj_{i}',
                    nn.Linear(head_dim, 2 * head_dim, bias=False))
            setattr(self, f'comp_pos_bias_{i}',
                    nn.Parameter(torch.zeros(2, 2 * head_dim)))

        # Phase C2: gated residual weights (init low so softmax_out dominates early)
        self.residual_weights = nn.Parameter(torch.full((self.levels, 4), -3.0))

        # ── Flat indexer (Phase B) ───────────────────────────────────────
        self.idx_gate_proj = nn.Linear(hidden_size, 2 * index_head_dim, bias=False)
        self.idx_position_bias = nn.Parameter(torch.zeros(compress_rate, 2 * index_head_dim))

    # ──────────────────────────────────────────────────────────────────────
    # Helper: one hierarchical level
    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def _compress_pair_level(kv, gate, pos_bias, residual_w, dim):
        """2:1 compression with Ca/Cb overlap and gated residual."""
        B = kv.shape[0]
        n_pairs = kv.shape[1] // 2
        if n_pairs == 0:
            return None
        usable = n_pairs * 2

        chunk_kv = kv[:, :usable].view(B, n_pairs, 2, 2 * dim)
        chunk_gate = gate[:, :usable].view(B, n_pairs, 2, 2 * dim)
        if pos_bias is not None:
            # pos_bias shape: (2, 2*dim) → broadcasts over B, n_pairs
            chunk_gate = chunk_gate + pos_bias

        # Build 4-slot overlap window: Ca from prev pair, Cb from current
        new_kv = torch.zeros(B, n_pairs, 4, dim, device=kv.device, dtype=chunk_kv.dtype)
        new_kv[:, :, 2:] = chunk_kv[..., dim:]      # Cb of current
        if n_pairs > 1:
            new_kv[:, 1:, :2] = chunk_kv[:, :-1, :, :dim]  # Ca of prev

        # Softmax gate over the 4 overlap slots
        weights = F.softmax(chunk_gate.view(B, n_pairs, 4, dim), dim=2)
        softmax_out = (new_kv * weights).sum(dim=2)  # [B, n_pairs, dim]

        # Phase C2: gated residual — blend all 4 overlap slots with learned weights
        if residual_w is not None:
            residual = (new_kv * residual_w.view(1, 1, 4, 1)).sum(dim=2)
        else:
            # Fallback: first Ca slot (original behaviour)
            residual = chunk_kv[:, :, 0, :dim]

        return softmax_out + residual

    # ──────────────────────────────────────────────────────────────────────
    # Single-level stride-2 KV compression (Phase C3)
    # ──────────────────────────────────────────────────────────────────────
    def _compress_kv(self, hidden_states, n_win, usable):
        """Single-level 2:1 compression with 4-slot gated residual.

        Each pair of adjacent tokens compresses into 1 KV token via a
        4-slot overlap window with softmax gate + gated residual.
        Output: 128 KV tokens (2× Flat's 64), each RoPE'd at stride 2.
        """
        B, D = hidden_states.shape[0], self.head_dim
        m = self.compress_rate

        # Level 0: project from raw hidden states
        kv = self.comp_kv_proj(hidden_states[:, :usable])           # [B, n_win*m, 2D]
        gate = self.comp_gate_proj_0(hidden_states[:, :usable])
        pos_idx = torch.arange(usable, device=hidden_states.device) % m
        gate = gate + self.comp_pos_bias_0[pos_idx]                 # per-token bias

        res_w = F.softmax(self.residual_weights[0], dim=-1)
        compressed = self._compress_pair_level(kv, gate, None, res_w, D)
        if compressed is None:
            return torch.zeros(B, 1, 1, D, device=hidden_states.device)
        compressed = self.comp_norm(compressed)

        # RoPE at stride 2
        scale = 2
        n_tok = compressed.shape[1]
        positions = (torch.arange(n_tok, device=hidden_states.device) * scale).unsqueeze(0).expand(B, -1)
        cos, sin = self.rotary_emb(compressed, positions)
        return apply_rotary_pos_emb(compressed.unsqueeze(1), cos, sin)  # [B, 1, 128, D]

    # ──────────────────────────────────────────────────────────────────────
    # Flat indexer (Phase B)
    # ──────────────────────────────────────────────────────────────────────
    def _compress_idx(self, hidden_states, n_win, usable):
        return self._flat_two_series_compress(
            hidden_states, n_win, usable,
            self.idx_kv_proj, self.idx_gate_proj, self.idx_position_bias,
            self.idx_norm, self.index_head_dim
        )

    # ──────────────────────────────────────────────────────────────────────
    # Expand block bias to match finer-grained KV count (64 → 128)
    # ──────────────────────────────────────────────────────────────────────
    def _postprocess_block_bias(self, block_bias, compressed_kv):
        """Expand block_bias [B,1,S,64] → [B,1,S,128] to match stride-2 KV tokens."""
        m = self.compress_rate
        tpb = m // 2  # 2 pyramid tokens per index block
        return block_bias.repeat_interleave(tpb, dim=-1)


# ==========================================
# TEST IT
# ==========================================
if __name__ == "__main__":
    B, S = 2, 64
    hidden = torch.randn(B, S, 512)
    pos = torch.arange(S).unsqueeze(0).expand(B, -1)

    print("Testing ModifiedCSAAttention (hierarchical comp + flat indexer)...")
    attn = ModifiedCSAAttention(
        hidden_size=512, num_heads=8, head_dim=64, q_lora_rank=128,
        compress_rate=4, index_topk=8, index_n_heads=4, index_head_dim=32,
        sliding_window=16, o_groups=4, o_lora_rank=64
    )
    out = attn(hidden, pos)
    print(f"Input shape:  {hidden.shape}")
    print(f"Output shape: {out.shape}")
    print("Modified Hierarchical CSA Attention executed successfully!")

    # Also test with compress_rate=8 (3 hierarchical levels)
    print("\nTesting with compress_rate=8 (3 levels)...")
    attn8 = ModifiedCSAAttention(
        hidden_size=512, num_heads=8, head_dim=64, q_lora_rank=128,
        compress_rate=8, index_topk=8, index_n_heads=4, index_head_dim=32,
        sliding_window=16, o_groups=4, o_lora_rank=64
    )
    out8 = attn8(hidden, pos)
    print(f"Input shape:  {hidden.shape}")
    print(f"Output shape: {out8.shape}")
    print("ModifiedCSAAttention (m=8) executed successfully!")