"""SurrogateAttention: per-token MLP that learns to imitate a CSA attention block.

Motivation: the CSA attention block (Q/KV projections, compressors, router,
dense `_attend`, O projections) is the slowest part of the model even in its
fastest variant (ExpertPlusPlus). We train a cheap per-token MLP to reproduce
the attention block's *output*, then swap it in at evaluation/prediction time.

This is a pointwise function (no cross-token mixing): it can only learn the
average context vector each token should receive, so it cannot match the
teacher's routing fidelity. It *can* learn position-dependent behaviour because
the input `hidden_states` already contains the model's learned positional
embedding (input_proj(x) + pos_embedding), so causality is trivially preserved.

Training (joint distillation, see train_surrogate.py):
    L = L_task(teacher) + lambda * MSE(student(h), stopgrad(teacher(h)))
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class SurrogateAttention(nn.Module):
    """Per-token MLP student. Signature-compatible with BaseCSAAttention:

        forward(hidden_states, position_ids=None) -> [B, S, hidden_size]

    Width/depth are configurable (expansion, num_layers) so the per-token
    function family can be scaled up when fidelity demands more capacity.
    """
    def __init__(self, hidden_size, expansion=4, num_layers=1):
        super().__init__()
        self.hidden_size = hidden_size
        width = hidden_size * expansion
        layers = [nn.Linear(hidden_size, width), nn.GELU()]
        for _ in range(num_layers - 1):
            layers.append(nn.Linear(width, width))
            layers.append(nn.GELU())
        layers.append(nn.Linear(width, hidden_size))
        self.net = nn.Sequential(*layers)

    def forward(self, hidden_states, position_ids=None):
        # position_ids ignored: position is already baked into `hidden_states`
        # via the model's learned positional embedding.
        return self.net(hidden_states)


class SurrogateAttentionV2(nn.Module):
    """Causal windowed attention + learned global prototypes (Surrogate v2).

    Why v2: the per-token MLP (v1) cannot do ANY cross-token mixing, which
    caps its fidelity at ~82% of the teacher. v2 adds cheap mixing:

      - Local: each position attends to the previous `window` tokens with
        learned Q/K/V projections (causal by construction, no future leak).
        Computed with a padded `unfold`, so cost is O(S·window·d) — not S².
      - Global: `n_global` learned key/value prototypes (input-independent,
        like the CSA sink tokens). This is a fixed amortized pattern the
        student can use to mimic the teacher's long-range routing on average.
      - Relative position bias per window offset (ALiBi-style), mirroring the
        teacher's per-block position bias.

    Still far cheaper than the teacher: ~17k params, no compression, no RoPE,
    no top-k, no dense `_attend` machinery.
    """
    def __init__(self, hidden_size, window=32, n_global=8, attn_dim=32):
        super().__init__()
        self.hidden_size = hidden_size
        self.window = window
        self.attn_dim = attn_dim

        self.q_proj = nn.Linear(hidden_size, attn_dim, bias=False)
        self.k_proj = nn.Linear(hidden_size, attn_dim, bias=False)
        self.v_proj = nn.Linear(hidden_size, attn_dim, bias=False)
        self.o_proj = nn.Linear(attn_dim, hidden_size, bias=False)

        # Learned global prototypes (input-independent → causal-safe)
        self.global_k = nn.Parameter(torch.randn(n_global, attn_dim) * 0.02)
        self.global_v = nn.Parameter(torch.randn(n_global, attn_dim) * 0.02)

        # Position bias: window offsets (oldest→newest) then global slots
        self.rel_bias = nn.Parameter(torch.zeros(window + n_global))

    def forward(self, hidden_states, position_ids=None):
        B, S, _ = hidden_states.shape
        W, G = self.window, self.global_k.shape[0]
        d = self.attn_dim

        q = self.q_proj(hidden_states)                       # [B, S, d]
        k = self.k_proj(hidden_states)                       # [B, S, d]
        v = self.v_proj(hidden_states)                       # [B, S, d]

        # Pad W-1 zeros at the start so position t's window [t-W+1, t] lines up
        # with a fixed offset slice (zeros contribute 0 score/value).
        k_pad = F.pad(k, (0, 0, W - 1, 0))                   # [B, S+W-1, d]
        v_pad = F.pad(v, (0, 0, W - 1, 0))
        kw = k_pad.unfold(1, W, 1)                           # [B, S, d, W]
        vw = v_pad.unfold(1, W, 1)                           # [B, S, d, W]

        local_scores = torch.einsum('bsd,bsdw->bsw', q, kw)      # [B, S, W]
        global_scores = torch.einsum('bsd,gd->bsg', q, self.global_k)  # [B, S, G]

        scores = torch.cat([local_scores, global_scores], dim=-1)  # [B, S, W+G]
        scores = scores + self.rel_bias.view(1, 1, -1)
        probs = F.softmax(scores, dim=-1)

        p_local, p_global = probs[..., :W], probs[..., W:]
        out_local = torch.einsum('bsw,bsdw->bsd', p_local, vw)        # [B, S, d]
        out_global = torch.einsum('bsg,gd->bsd', p_global, self.global_v)

        return self.o_proj(out_local + out_global)


if __name__ == "__main__":
    for cls in (SurrogateAttention, SurrogateAttentionV2):
        m = cls(128)
        x = torch.randn(2, 64, 128)
        out = m(x)
        loss = out.square().mean()
        loss.backward()
        print(f"{cls.__name__} OK: {tuple(out.shape)}, "
              f"params={sum(p.numel() for p in m.parameters())/1e6:.3f}M")
