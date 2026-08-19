import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ──────────────────────────────────────────────────────────────────────────────
# 1. Core Utilities (RoPE, RMSNorm, GroupedLinear)
# ──────────────────────────────────────────────────────────────────────────────

class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps
    def forward(self, x):
        x = x.float()
        x = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return (self.weight * x).to(self.weight.dtype)

class UnweightedRMSNorm(nn.Module):
    def __init__(self, eps=1e-6):
        super().__init__()
        self.eps = eps
    def forward(self, x):
        return (x * torch.rsqrt(x.float().square().mean(-1, keepdim=True) + self.eps)).to(x.dtype)

class RotaryEmbedding(nn.Module):
    def __init__(self, head_dim, rope_head_dim, base=10000.0):
        super().__init__()
        self.dim = rope_head_dim
        inv_freq = 1.0 / (base ** (torch.arange(0, self.dim, 2).float() / self.dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)

    @torch.no_grad()
    def forward(self, x, position_ids):
        inv_freq = self.inv_freq[None, :, None].float().expand(position_ids.shape[0], -1, 1).to(x.device)
        pos = position_ids[:, None, :].float()
        freqs = (inv_freq @ pos).transpose(1, 2)
        return freqs.cos().to(x.dtype), freqs.sin().to(x.dtype)

def rotate_half(x):
    x1 = x[..., 0::2]
    x2 = x[..., 1::2]
    return torch.stack((-x2, x1), dim=-1).flatten(-2)

def apply_rotary_pos_emb(x, cos, sin, unsqueeze_dim=1):
    cos = cos.repeat_interleave(2, dim=-1).unsqueeze(unsqueeze_dim)
    sin = sin.repeat_interleave(2, dim=-1).unsqueeze(unsqueeze_dim)
    rope_dim = cos.shape[-1]
    nope, rope = x[..., :-rope_dim], x[..., -rope_dim:]
    rotated = (rope.float() * cos + rotate_half(rope).float() * sin).to(x.dtype)
    return torch.cat([nope, rotated], dim=-1)

class GroupedLinear(nn.Linear):
    def __init__(self, in_features_per_group, out_features, n_groups, bias=False):
        super().__init__(in_features_per_group, out_features, bias=bias)
        self.n_groups = n_groups
    def forward(self, x):
        input_shape = x.shape[:-2]
        hidden_dim = x.shape[-1]
        w = self.weight.view(self.n_groups, -1, hidden_dim).transpose(1, 2)
        x = x.reshape(-1, self.n_groups, hidden_dim).transpose(0, 1)
        y = torch.bmm(x, w).transpose(0, 1)
        return y.reshape(*input_shape, self.n_groups, -1)


# ──────────────────────────────────────────────────────────────────────────────
# 2. Base CSA Attention (shared logic for all variants)
# ──────────────────────────────────────────────────────────────────────────────

class BaseCSAAttention(nn.Module):
    """Shared base for CSA attention variants.

    Subclasses must implement:
        _compress_kv(hidden_states, n_win, usable) -> [B, 1, n_win, head_dim]
        _compress_idx(hidden_states, n_win, usable) -> [B, 1, n_win, index_head_dim]
    """
    def __init__(self, hidden_size, num_heads, head_dim, q_lora_rank,
                 compress_rate=4, index_topk=8, index_n_heads=4, index_head_dim=32,
                 sliding_window=16, o_groups=4, o_lora_rank=128, rope_theta=10000.0):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.compress_rate = compress_rate
        self.index_topk = index_topk
        self.index_n_heads = index_n_heads
        self.index_head_dim = index_head_dim
        self.sliding_window = sliding_window
        self.o_groups = o_groups
        self.rope_head_dim = head_dim // 4
        self.rotary_emb = RotaryEmbedding(head_dim, self.rope_head_dim, base=rope_theta)

        self.q_a_proj = nn.Linear(hidden_size, q_lora_rank, bias=False)
        self.q_a_norm = RMSNorm(q_lora_rank)
        self.q_b_proj = nn.Linear(q_lora_rank, num_heads * head_dim, bias=False)
        self.q_b_norm = UnweightedRMSNorm()
        self.kv_proj = nn.Linear(hidden_size, head_dim, bias=False)
        self.kv_norm = RMSNorm(head_dim)
        self.o_a_proj = GroupedLinear(num_heads * head_dim // o_groups, o_groups * o_lora_rank, o_groups)
        self.o_b_proj = nn.Linear(o_groups * o_lora_rank, hidden_size, bias=False)
        self.sinks = nn.Parameter(torch.zeros(num_heads))

        self.comp_kv_proj = nn.Linear(hidden_size, 2 * head_dim, bias=False)
        self.comp_norm = RMSNorm(head_dim)

        self.idx_kv_proj = nn.Linear(hidden_size, 2 * index_head_dim, bias=False)
        self.idx_norm = RMSNorm(index_head_dim)
        self.idx_q_proj = nn.Linear(q_lora_rank, num_heads * index_head_dim, bias=False)
        self.idx_weights_proj = nn.Linear(hidden_size, num_heads, bias=False)

    def _flat_two_series_compress(self, hidden_states, n_win, usable, kv_proj, gate_proj, pos_bias, norm, dim, m=None):
        if m is None:
            m = self.compress_rate
        B = hidden_states.shape[0]
        comp_kv = kv_proj(hidden_states[:, :usable]).view(B, n_win, m, 2 * dim)
        comp_gate = gate_proj(hidden_states[:, :usable]).view(B, n_win, m, 2 * dim) + pos_bias

        new_kv = torch.zeros(B, n_win, 2 * m, dim, device=hidden_states.device)
        new_kv[:, :, m:] = comp_kv[..., dim:]
        if n_win > 1:
            new_kv[:, 1:, :m] = comp_kv[:, :-1, :, :dim]

        weights = F.softmax(comp_gate.view(B, n_win, 2 * m, dim), dim=2)
        compressed = norm((new_kv * weights).sum(dim=2))

        win_positions = (torch.arange(n_win, device=hidden_states.device) * m).unsqueeze(0).expand(B, -1)
        cos, sin = self.rotary_emb(compressed, win_positions)
        compressed = apply_rotary_pos_emb(compressed.unsqueeze(1), cos, sin).squeeze(1)
        return compressed.unsqueeze(1)

    def _compress_kv(self, hidden_states, n_win, usable):
        raise NotImplementedError

    def _compress_idx(self, hidden_states, n_win, usable):
        raise NotImplementedError

    def _postprocess_block_bias(self, block_bias, compressed_kv):
        """Expand block bias to match compressed KV seq len (override for multi-scale)."""
        return block_bias

    def _build_idx_positions(self, S, device):
        """Return (positions, scales) for each index token.

        Each index token represents original positions [pos, pos+scale-1].
        Default: flat blocking — n_win tokens each of size m.
        """
        m = self.compress_rate
        n_win = S // m
        pos = torch.arange(n_win, device=device) * m
        scale = torch.full((n_win,), m, device=device)
        return pos, scale

    def _index_query(self, q, q_residual, cos, sin, B, S):
        """Project the low-rank query residual for index scoring.

        Base: learned per-head low-rank projection (idx_q_proj) + RoPE.
        Subclasses may reuse the main Q instead (e.g. ExpertPlusPlus).
        """
        q_idx = self.idx_q_proj(q_residual).view(B, S, self.num_heads, self.index_head_dim).transpose(1, 2)
        return apply_rotary_pos_emb(q_idx, cos, sin)

    def _postprocess_topk(self, top_k_indices, index_scores, n_idx, S, device):
        """Map router output to the KV-block indices used by `_attend`.

        Base: identity — index tokens ARE KV blocks (shared granularity).
        Subclasses with decoupled index/KV granularity (e.g. ExpertPlusPlus)
        map 4:1 index tokens onto 8:1 KV blocks here.
        """
        return top_k_indices, n_idx

    def _attend(self, q, kv, compressed_kv, top_k_indices, n_idx, cos, sin, B, S, D):
        """Dense attention over sliding window + ALL compressed blocks.

        Non-selected blocks are masked to -inf via block bias (their softmax
        weight is exactly 0). Returns raw attn_output [B, H, S, D] (no -sin RoPE).
        """
        block_bias = torch.full((B, 1, S, n_idx + 1), float('-inf'), device=q.device)
        block_bias.scatter_(-1, top_k_indices.unsqueeze(1), 0.0)
        block_bias = block_bias[..., :n_idx]
        block_bias = self._postprocess_block_bias(block_bias, compressed_kv)

        actual_window = min(self.sliding_window, S)
        sw_k = kv[:, :, -actual_window:, :]

        total_k = torch.cat([sw_k, compressed_kv], dim=2)
        total_v = total_k

        q_pos_sw = torch.arange(S, device=q.device).unsqueeze(1)
        k_pos_sw = torch.arange(S - actual_window, S, device=q.device).unsqueeze(0)
        sw_mask = torch.where(k_pos_sw > q_pos_sw, float('-inf'), 0.0)
        sw_mask = sw_mask.unsqueeze(0).unsqueeze(0).expand(B, 1, -1, -1)

        final_mask = torch.cat([sw_mask, block_bias], dim=-1)

        attn_weights = torch.matmul(q, total_k.transpose(2, 3)) * (D ** -0.5)
        attn_weights = attn_weights + final_mask

        sinks = self.sinks.reshape(1, -1, 1, 1).expand(B, -1, S, -1)
        combined = torch.cat([attn_weights, sinks], dim=-1)
        combined = combined - combined.max(dim=-1, keepdim=True).values
        probs = F.softmax(combined, dim=-1, dtype=combined.dtype)
        scores = probs[..., :-1]

        return torch.matmul(scores.to(total_v.dtype), total_v)

    def forward(self, hidden_states, position_ids=None):
        B, S, _ = hidden_states.shape
        if position_ids is None:
            position_ids = torch.arange(S, device=hidden_states.device).unsqueeze(0).expand(B, -1)
        H, D, m = self.num_heads, self.head_dim, self.compress_rate

        cos, sin = self.rotary_emb(hidden_states, position_ids)

        q_residual = self.q_a_norm(self.q_a_proj(hidden_states))
        q = self.q_b_proj(q_residual).view(B, S, H, D).transpose(1, 2)
        q = self.q_b_norm(q)
        q = apply_rotary_pos_emb(q, cos, sin)

        kv = self.kv_norm(self.kv_proj(hidden_states)).view(B, S, 1, D).transpose(1, 2)
        kv = apply_rotary_pos_emb(kv, cos, sin)

        n_win = S // m
        usable = n_win * m

        compressed_kv = self._compress_kv(hidden_states, n_win, usable)
        compressed_idx = self._compress_idx(hidden_states, n_win, usable)
        n_idx = compressed_idx.shape[2]

        q_idx = self._index_query(q, q_residual, cos, sin, B, S)

        scores = torch.matmul(q_idx.float(), compressed_idx.transpose(-1, -2).float())
        scores = F.relu(scores) * (self.index_head_dim ** -0.5)
        weights = self.idx_weights_proj(hidden_states).float() * (self.index_n_heads ** -0.5)
        index_scores = (scores.permute(0, 2, 1, 3) * weights.unsqueeze(-1)).sum(dim=2)

        top_k = min(self.index_topk, n_idx)
        q_pos = torch.arange(S, device=hidden_states.device)
        idx_pos, idx_scale = self._build_idx_positions(S, hidden_states.device)
        future_mask = (idx_pos + idx_scale - 1).unsqueeze(0) > q_pos.view(-1, 1)
        index_scores = index_scores.masked_fill(future_mask, float('-inf'))

        top_k_indices = index_scores.topk(top_k, dim=-1).indices
        safe = top_k_indices.clamp(0, n_idx - 1)
        oob = top_k_indices >= n_idx
        invalid = (idx_pos[safe] + idx_scale[safe] - 1 > q_pos.view(1, -1, 1)) | oob
        top_k_indices = torch.where(invalid, n_idx, top_k_indices)

        # Allow subclasses to map index tokens onto coarser KV blocks
        top_k_indices, n_idx = self._postprocess_topk(top_k_indices, index_scores, n_idx, S, hidden_states.device)

        attn_output = self._attend(q, kv, compressed_kv, top_k_indices, n_idx, cos, sin, B, S, D)
        attn_output = apply_rotary_pos_emb(attn_output, cos, -sin)

        grouped = attn_output.transpose(1, 2).reshape(B, S, self.o_groups, -1)
        grouped = self.o_a_proj(grouped).flatten(2)
        return self.o_b_proj(grouped)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Flat V4 CSA Attention
# ──────────────────────────────────────────────────────────────────────────────

class CSAAttention(BaseCSAAttention):
    """Flat two-series compressor + flat two-series indexer (original V4)."""
    def __init__(self, hidden_size, num_heads, head_dim, q_lora_rank,
                 compress_rate=4, index_topk=8, index_n_heads=4, index_head_dim=32,
                 sliding_window=16, o_groups=4, o_lora_rank=128, rope_theta=10000.0):
        super().__init__(hidden_size, num_heads, head_dim, q_lora_rank,
                         compress_rate, index_topk, index_n_heads, index_head_dim,
                         sliding_window, o_groups, o_lora_rank, rope_theta)

        self.comp_gate_proj = nn.Linear(hidden_size, 2 * head_dim, bias=False)
        self.comp_position_bias = nn.Parameter(torch.zeros(compress_rate, 2 * head_dim))

        self.idx_gate_proj = nn.Linear(hidden_size, 2 * index_head_dim, bias=False)
        self.idx_position_bias = nn.Parameter(torch.zeros(compress_rate, 2 * index_head_dim))

    def _compress_kv(self, hidden_states, n_win, usable):
        return self._flat_two_series_compress(
            hidden_states, n_win, usable,
            self.comp_kv_proj, self.comp_gate_proj, self.comp_position_bias,
            self.comp_norm, self.head_dim
        )

    def _compress_idx(self, hidden_states, n_win, usable):
        return self._flat_two_series_compress(
            hidden_states, n_win, usable,
            self.idx_kv_proj, self.idx_gate_proj, self.idx_position_bias,
            self.idx_norm, self.index_head_dim
        )


if __name__ == "__main__":
    B, S = 2, 64
    hidden = torch.randn(B, S, 512)
    pos = torch.arange(S).unsqueeze(0).expand(B, -1)

    attn = CSAAttention(
        hidden_size=512, num_heads=8, head_dim=64, q_lora_rank=128,
        compress_rate=4, index_topk=8, index_n_heads=4, index_head_dim=32,
        sliding_window=16, o_groups=4, o_lora_rank=64
    )

    out = attn(hidden, pos)
    print(f"Input shape:  {hidden.shape}")
    print(f"Output shape: {out.shape}")
    print("Faithful DeepSeek-V4 CSA Attention executed successfully!")
