import torch
import torch.nn as nn
import torch.nn.functional as F
import math

from attention import RMSNorm, UnweightedRMSNorm, RotaryEmbedding, GroupedLinear, apply_rotary_pos_emb


# ──────────────────────────────────────────────────────────────────────────────
# Normal Full Self-Attention (vanilla Transformer-style)
# ──────────────────────────────────────────────────────────────────────────────

class NormalAttention(nn.Module):
    """Standard quadratic multi-head self-attention with RoPE.

    Matches the same Q/KV/output projections as CSA variants, but does
    full S × S attention over ALL tokens — no compression, no indexing,
    no sliding window, no sink tokens.

    Forward: Q(K,V) over every position with causal masking.
    O(S²) compute and memory.
    """
    def __init__(self, hidden_size, num_heads, head_dim, q_lora_rank,
                 compress_rate=4, index_topk=8, index_n_heads=4, index_head_dim=32,
                 sliding_window=16, o_groups=4, o_lora_rank=128, rope_theta=10000.0,
                 **kwargs):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.o_groups = o_groups
        self.rope_head_dim = head_dim // 4
        self.rotary_emb = RotaryEmbedding(head_dim, self.rope_head_dim, base=rope_theta)

        # Same Q projection as CSA (LoRA-style)
        self.q_a_proj = nn.Linear(hidden_size, q_lora_rank, bias=False)
        self.q_a_norm = RMSNorm(q_lora_rank)
        self.q_b_proj = nn.Linear(q_lora_rank, num_heads * head_dim, bias=False)
        self.q_b_norm = UnweightedRMSNorm()

        # Same KV projection (tied K=V, matching CSA convention)
        self.kv_proj = nn.Linear(hidden_size, head_dim, bias=False)
        self.kv_norm = RMSNorm(head_dim)

        # Same output projection
        self.o_a_proj = GroupedLinear(num_heads * head_dim // o_groups, o_groups * o_lora_rank, o_groups)
        self.o_b_proj = nn.Linear(o_groups * o_lora_rank, hidden_size, bias=False)

    def forward(self, hidden_states, position_ids=None):
        B, S, _ = hidden_states.shape
        if position_ids is None:
            position_ids = torch.arange(S, device=hidden_states.device).unsqueeze(0).expand(B, -1)
        H, D = self.num_heads, self.head_dim

        cos, sin = self.rotary_emb(hidden_states, position_ids)

        # Q projection (same as CSA)
        q_residual = self.q_a_norm(self.q_a_proj(hidden_states))
        q = self.q_b_proj(q_residual).view(B, S, H, D).transpose(1, 2)
        q = self.q_b_norm(q)
        q = apply_rotary_pos_emb(q, cos, sin)

        # KV projection — tied K=V (same as CSA convention)
        kv = self.kv_norm(self.kv_proj(hidden_states)).view(B, S, 1, D).transpose(1, 2)
        kv = apply_rotary_pos_emb(kv, cos, sin)
        k, v = kv, kv  # tied K=V

        # Causal mask (standard upper triangular)
        causal_mask = torch.triu(torch.full((S, S), float('-inf'), device=hidden_states.device), diagonal=1)
        causal_mask = causal_mask.unsqueeze(0).unsqueeze(0)  # [1, 1, S, S]

        # Full attention: [B, H, S, D] × [B, 1, S, D]^T → [B, H, S, S]
        attn_weights = torch.matmul(q, k.transpose(2, 3).float()) * (D ** -0.5)
        attn_weights = attn_weights + causal_mask

        # Softmax + attend to V
        attn_weights = attn_weights - attn_weights.max(dim=-1, keepdim=True).values
        probs = F.softmax(attn_weights, dim=-1, dtype=attn_weights.dtype)
        attn_output = torch.matmul(probs, v.to(probs.dtype))

        # Rotate back (same as CSA)
        attn_output = apply_rotary_pos_emb(attn_output, cos, -sin)

        # Output projection (same as CSA)
        grouped = attn_output.transpose(1, 2).reshape(B, S, self.o_groups, -1)
        grouped = self.o_a_proj(grouped).flatten(2)
        return self.o_b_proj(grouped)
