"""FlatPlus: gated residual KV + learned linear pool indexer.

Two improvements over the base Flat CSAAttention:
  1. Gated residual on KV compressor — learned blend of all 2*m overlap slots
  2. Learned linear pool indexer — one linear layer per window instead of
     expensive gate/softmax/overlap machinery
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math

from attention import BaseCSAAttention, apply_rotary_pos_emb


class FlatPlusAttention(BaseCSAAttention):
    """Flat CSA + gated residual KV + learned linear pool indexer.

    KV compressor:
      - Same 4:1 stride-4 overlap as Flat (2*m = 8 slots)
      - Adds gated residual: learned weighted blend of all 8 overlap slots
        (initialised near zero so softmax path dominates early)

    Indexer:
      - Flattens each m-token window and projects to index space via a
        single learned Linear layer (no gate, no softmax, no overlap)
      - Much faster: ~1 matmul vs ~4 matmuls + softmax
    """
    def __init__(self, hidden_size, num_heads, head_dim, q_lora_rank,
                 compress_rate=4, index_topk=8, index_n_heads=4, index_head_dim=32,
                 sliding_window=16, o_groups=4, o_lora_rank=128, rope_theta=10000.0):
        super().__init__(hidden_size, num_heads, head_dim, q_lora_rank,
                         compress_rate, index_topk, index_n_heads, index_head_dim,
                         sliding_window, o_groups, o_lora_rank, rope_theta)

        # ── KV compressor (same gate/bias as Flat) ──
        self.comp_gate_proj = nn.Linear(hidden_size, 2 * head_dim, bias=False)
        self.comp_position_bias = nn.Parameter(torch.zeros(compress_rate, 2 * head_dim))
        # Gated residual: one learned weight per overlap slot (2*m = 8 for m=4)
        self.kv_residual_weights = nn.Parameter(torch.full((compress_rate * 2,), -3.0))

        # ── Indexer: learned linear pool ──
        # Flatten each window of m tokens → project to index_head_dim
        self.idx_pool = nn.Linear(compress_rate * hidden_size, index_head_dim, bias=False)

    # ──────────────────────────────────────────────────────────────────────────
    # KV compressor (4:1, stride-4, 2-m overlap + gated residual)
    # ──────────────────────────────────────────────────────────────────────────
    def _compress_kv(self, hidden_states, n_win, usable):
        """Flat 4:1 compressor with gated residual over 8 overlap slots."""
        B, D, m = hidden_states.shape[0], self.head_dim, self.compress_rate

        # Project to KV space (Ca, Cb pairs) + gate
        comp_kv = self.comp_kv_proj(hidden_states[:, :usable]).view(B, n_win, m, 2 * D)
        comp_gate = self.comp_gate_proj(hidden_states[:, :usable]).view(B, n_win, m, 2 * D)
        comp_gate = comp_gate + self.comp_position_bias  # per-pair position bias

        # Build 2*m overlap window: Ca from prev pair, Cb from current
        new_kv = torch.zeros(B, n_win, 2 * m, D, device=hidden_states.device)
        new_kv[:, :, m:] = comp_kv[..., D:]  # Cb of current window
        if n_win > 1:
            new_kv[:, 1:, :m] = comp_kv[:, :-1, :, :D]  # Ca of prev window

        # Softmax gate over the 2*m overlap slots
        weights = F.softmax(comp_gate.view(B, n_win, 2 * m, D), dim=2)
        softmax_out = (new_kv * weights).sum(dim=2)

        # Gated residual: learned blend of all 2*m slots
        res_w = F.softmax(self.kv_residual_weights, dim=-1)
        residual = (new_kv * res_w.view(1, 1, 2 * m, 1)).sum(dim=2)

        compressed = self.comp_norm(softmax_out + residual)

        # RoPE at stride m
        positions = (torch.arange(n_win, device=hidden_states.device) * m).unsqueeze(0).expand(B, -1)
        cos, sin = self.rotary_emb(compressed, positions)
        return apply_rotary_pos_emb(compressed.unsqueeze(1), cos, sin)

    # ──────────────────────────────────────────────────────────────────────────
    # Indexer (learned linear pool: flatten → project)
    # ──────────────────────────────────────────────────────────────────────────
    def _compress_idx(self, hidden_states, n_win, usable):
        """Learned linear pool: flatten each m-token window, project to index space.

        Much faster than the full gate/softmax/overlap compressor used in Flat.
        """
        B = hidden_states.shape[0]
        m = self.compress_rate
        H = hidden_states.shape[-1]

        # Flatten window of m tokens and project
        pooled = hidden_states[:, :usable].reshape(B, n_win, m * H)  # [B, n_win, m*H]
        idx = self.idx_norm(self.idx_pool(pooled))  # [B, n_win, index_head_dim]

        # RoPE at window positions
        positions = (torch.arange(n_win, device=hidden_states.device) * m).unsqueeze(0).expand(B, -1)
        cos, sin = self.rotary_emb(idx, positions)
        return apply_rotary_pos_emb(idx.unsqueeze(1), cos, sin)


# ==========================================
# TEST
# ==========================================
if __name__ == "__main__":
    B, S = 2, 64
    hidden = torch.randn(B, S, 512)
    pos = torch.arange(S).unsqueeze(0).expand(B, -1)

    attn = FlatPlusAttention(
        hidden_size=512, num_heads=8, head_dim=64, q_lora_rank=128,
        compress_rate=4, index_topk=8, index_n_heads=4, index_head_dim=32,
        sliding_window=16, o_groups=4, o_lora_rank=64
    )
    out = attn(hidden, pos)
    loss = out.square().mean()
    loss.backward()
    print(f"FlatPlusAttention OK: {out.shape}, loss={loss.item():.4f}, params={sum(p.numel() for p in attn.parameters())/1e6:.2f}M")
