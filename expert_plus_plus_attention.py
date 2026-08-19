"""ExpertPlusPlus: decoupled granularity — 8:1 KV content + 4:1 routing.

Why this design (vs ExpertFlat and Flat):

  Flat          = 4:1 KV content, 4:1 routing granularity, dense 96-col attention.
                  Best accuracy (0.1085) but slowest attention (9.11 ms).
  ExpertFlat    = 8:1 KV content, 8:1 routing granularity, dense 64-col attention.
                  Fastest (1.34×) but worst accuracy (0.1102) — BOTH granularities
                  were coarsened, so routing decisions lost precision.
  ExpertPlusPlus= 8:1 KV content (fast: 64-col dense attention), but 4:1 ROUTING
                  granularity (64 fine-grained index tokens, like Flat).

The routing granularity — how precisely a query can choose which history to
attend — is what keeps Flat's accuracy. The KV content ratio only affects
speed (fewer dense attention columns). ExpertFlat coarsened both; we decouple
them and keep the fine 4:1 router.

Additional cuts (all compute-only, no routing-quality loss):
  1. Shared-Q routing — the main per-head Q (RoPE'd + normalized) serves as the
     index query; idx_q_proj is dropped entirely.
  2. Slim O bottleneck — o_lora_rank=64 vs Flat's 128 (~34% fewer params).
  3. Dense attention is used (NOT sparse gather): on CPU, dense GEMMs over 64
     columns beat per-query gather+bmm even though only ~16 blocks are used.

Mechanism of the fine router on coarse blocks:
  - 64 index tokens at 4:1 granularity (positions [4t, 4t+3]), scored by the
    shared Q (identical logic to Flat).
  - Each 8:1 KV block j covers positions [8j, 8j+7] == index tokens {2j, 2j+1}.
  - A query's top-16 index tokens map onto ≤16 KV blocks; a block whose later
    half is still in the future (8j+7 > q) is masked to prevent leakage.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from attention import BaseCSAAttention


class ExpertPlusPlusAttention(BaseCSAAttention):
    """Decoupled-granularity CSA: 8:1 KV + 4:1 routing, shared-Q, slim O.

    Requires head_dim == index_head_dim (both 32 in our config) so the main
    per-head Q can serve as the routing query.
    """
    def __init__(self, hidden_size, num_heads, head_dim, q_lora_rank,
                 compress_rate=8, index_compress_rate=4, index_topk=16,
                 index_n_heads=4, index_head_dim=32, sliding_window=32,
                 o_groups=4, o_lora_rank=64, rope_theta=10000.0):
        super().__init__(hidden_size, num_heads, head_dim, q_lora_rank,
                         compress_rate, index_topk, index_n_heads, index_head_dim,
                         sliding_window, o_groups, o_lora_rank, rope_theta)

        self.index_compress_rate = index_compress_rate

        # KV compressor: 8:1 per-dim softmax overlap (m = compress_rate)
        self.comp_gate_proj = nn.Linear(hidden_size, 2 * head_dim, bias=False)
        self.comp_position_bias = nn.Parameter(torch.zeros(compress_rate, 2 * head_dim))

        # Indexer: 4:1 per-dim softmax overlap (m = index_compress_rate)
        self.idx_gate_proj = nn.Linear(hidden_size, 2 * index_head_dim, bias=False)
        self.idx_position_bias = nn.Parameter(torch.zeros(index_compress_rate, 2 * index_head_dim))

        # Shared-Q routing: idx_q_proj is unused (we route with the main Q).
        del self.idx_q_proj

    # ── Compressors (decoupled granularities) ────────────────────────────────
    def _compress_kv(self, hidden_states, n_win, usable):
        """8:1 KV compression via per-dimension softmax overlap (Flat's mechanism)."""
        return self._flat_two_series_compress(
            hidden_states, n_win, usable,
            self.comp_kv_proj, self.comp_gate_proj, self.comp_position_bias,
            self.comp_norm, self.head_dim, m=self.compress_rate
        )

    def _compress_idx(self, hidden_states, n_win, usable):
        """4:1 index compression — the FINE routing granularity that keeps accuracy."""
        n_idx = usable // self.index_compress_rate
        return self._flat_two_series_compress(
            hidden_states, n_idx, usable,
            self.idx_kv_proj, self.idx_gate_proj, self.idx_position_bias,
            self.idx_norm, self.index_head_dim, m=self.index_compress_rate
        )

    # ── Routing ──────────────────────────────────────────────────────────────
    def _index_query(self, q, q_residual, cos, sin, B, S):
        """Routing uses the main Q directly — already RoPE'd + normalized."""
        return q

    def _build_idx_positions(self, S, device):
        """Index tokens live at 4:1 granularity (64 tokens), independent of KV rate."""
        m = self.index_compress_rate
        n_idx = S // m
        pos = torch.arange(n_idx, device=device) * m
        scale = torch.full((n_idx,), m, device=device)
        return pos, scale

    def _postprocess_topk(self, top_k_indices, index_scores, n_idx, S, device):
        """Map 4:1 index tokens onto 8:1 KV blocks with future-safety.

        Block j (positions [8j, 8j+7]) == index tokens {2j, 2j+1}. A token in
        [0, n_idx) maps to block t // 2. A block is only safe to read when its
        ENTIRE span is in the past (8j+7 <= q), otherwise it leaks future
        positions — mask it via the n_idx sentinel (dropped by _attend).
        """
        n_kv = S // self.compress_rate
        # Preserve the n_idx sentinel (invalid/future tokens) as n_kv.
        sentinel = top_k_indices >= n_idx
        # sentinel maps to 63 → clamp to 31 → then masked below
        blocks = top_k_indices.clamp(0, n_idx - 1) // 2          # [B,S,top_k]
        block_end = (blocks * self.compress_rate + (self.compress_rate - 1))  # 8j+7
        q_pos = torch.arange(S, device=device).view(1, -1, 1)
        safe = block_end <= q_pos
        kv_blocks = torch.where(safe, blocks, n_kv)              # sentinel n_kv
        kv_blocks = torch.where(sentinel, n_kv, kv_blocks)       # never unmask a sentinel
        return kv_blocks, n_kv

    # Dense `_attend` is inherited from BaseCSAAttention (window + all 32 KV
    # blocks = 64 columns, non-selected blocks masked to -inf).


if __name__ == "__main__":
    B, S = 2, 64
    hidden = torch.randn(B, S, 512)
    pos = torch.arange(S).unsqueeze(0).expand(B, -1)

    attn = ExpertPlusPlusAttention(
        hidden_size=512, num_heads=8, head_dim=64, q_lora_rank=128,
        compress_rate=8, index_compress_rate=4, index_topk=8,
        index_n_heads=4, index_head_dim=64, sliding_window=16,
        o_groups=4, o_lora_rank=128
    )
    out = attn(hidden, pos)
    loss = out.square().mean()
    loss.backward()
    print(f"ExpertPlusPlusAttention OK: {out.shape}, loss={loss.item():.4f}, "
          f"params={sum(p.numel() for p in attn.parameters())/1e6:.2f}M")
    print(f"  KV blocks={S // attn.compress_rate} (8:1), "
          f"index tokens={S // attn.index_compress_rate} (4:1), "
          f"total KV={S // attn.compress_rate + min(attn.sliding_window, S)} + 1 sink")
