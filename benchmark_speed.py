"""Speed vs Performance benchmark for all CSA attention variants.

Measures:
  - Forward latency (inference): time per forward pass
  - Train throughput (fwd+bwd): time per fwd+bwd step
  - Performance vs speed ratios

Variants:
  1. Flat CSAAttention (CSAAttention) — 64 KV tokens, baseline
  2. ModifiedCSAAttention (single-level stride-2) — 128 KV tokens, current winner
  3. ModifiedStackedCSAAttention (2-level stacked) — 64 KV tokens, failed approach
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import time
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from attention import BaseCSAAttention, CSAAttention, apply_rotary_pos_emb
from modified_attention import ModifiedCSAAttention
from normal_attention import NormalAttention
from flat_plus_attention import FlatPlusAttention
from expert_flat_attention import ExpertFlatAttention
from expert_plus_plus_attention import ExpertPlusPlusAttention
from surrogate_attention import SurrogateAttention, SurrogateAttentionV2


# =============================================================================
# Stacked refinement variant (same 64 KV tokens as Flat)
# =============================================================================
class ModifiedStackedCSAAttention(BaseCSAAttention):
    """Stacked 2:1→2:1 hierarchical compression, keeping only final level.

    Same 64 KV tokens as Flat, but with two rounds of gating.
    Included for fair speed/performance comparison.
    """
    def __init__(self, hidden_size, num_heads, head_dim, q_lora_rank,
                 compress_rate=4, index_topk=8, index_n_heads=4, index_head_dim=32,
                 sliding_window=16, o_groups=4, o_lora_rank=128, rope_theta=10000.0):
        super().__init__(hidden_size, num_heads, head_dim, q_lora_rank,
                         compress_rate, index_topk, index_n_heads, index_head_dim,
                         sliding_window, o_groups, o_lora_rank, rope_theta)

        levels = int(math.log2(compress_rate))  # full depth

        # Level 0: hidden_size → 2*head_dim
        self.comp_gate_proj_0 = nn.Linear(hidden_size, 2 * head_dim, bias=False)
        self.comp_pos_bias_0 = nn.Parameter(torch.zeros(compress_rate, 2 * head_dim))

        # Levels 1+: head_dim → 2*head_dim
        for i in range(1, levels):
            setattr(self, f'comp_gate_proj_{i}',
                    nn.Linear(head_dim, 2 * head_dim, bias=False))
            setattr(self, f'comp_pos_bias_{i}',
                    nn.Parameter(torch.zeros(2, 2 * head_dim)))

        self.residual_weights = nn.Parameter(torch.full((levels, 4), -3.0))

        # Flat indexer
        self.idx_gate_proj = nn.Linear(hidden_size, 2 * index_head_dim, bias=False)
        self.idx_position_bias = nn.Parameter(torch.zeros(compress_rate, 2 * index_head_dim))

    @staticmethod
    def _compress_pair_level(kv, gate, pos_bias, residual_w, dim):
        """2:1 compression with 4-slot overlap and gated residual."""
        B = kv.shape[0]
        n_pairs = kv.shape[1] // 2
        if n_pairs == 0:
            return None
        usable = n_pairs * 2

        chunk_kv = kv[:, :usable].view(B, n_pairs, 2, 2 * dim)
        chunk_gate = gate[:, :usable].view(B, n_pairs, 2, 2 * dim)
        if pos_bias is not None:
            chunk_gate = chunk_gate + pos_bias

        new_kv = torch.zeros(B, n_pairs, 4, dim, device=kv.device, dtype=chunk_kv.dtype)
        new_kv[:, :, 2:] = chunk_kv[..., dim:]
        if n_pairs > 1:
            new_kv[:, 1:, :2] = chunk_kv[:, :-1, :, :dim]

        weights = F.softmax(chunk_gate.view(B, n_pairs, 4, dim), dim=2)
        softmax_out = (new_kv * weights).sum(dim=2)

        if residual_w is not None:
            residual = (new_kv * residual_w.view(1, 1, 4, 1)).sum(dim=2)
        else:
            residual = chunk_kv[:, :, 0, :dim]

        return softmax_out + residual

    def _compress_kv(self, hidden_states, n_win, usable):
        """Stacked 2:1 compression, return only final level (same KV count as Flat)."""
        B, D = hidden_states.shape[0], self.head_dim
        m = self.compress_rate
        L = int(math.log2(m))

        compressed = None
        for l in range(L):
            if l == 0:
                kv = self.comp_kv_proj(hidden_states[:, :usable])
                gate = self.comp_gate_proj_0(hidden_states[:, :usable])
                pos_idx = torch.arange(usable, device=hidden_states.device) % m
                gate = gate + self.comp_pos_bias_0[pos_idx]
            else:
                kv = torch.cat([compressed, compressed], dim=-1)
                gate = getattr(self, f'comp_gate_proj_{l}')(compressed)

            res_w = F.softmax(self.residual_weights[l], dim=-1)
            pb = getattr(self, f'comp_pos_bias_{l}') if l > 0 else None
            compressed = self._compress_pair_level(kv, gate, pb, res_w, D)
            if compressed is None:
                return torch.zeros(B, 1, 1, D, device=hidden_states.device)
            compressed = self.comp_norm(compressed)

        # RoPE at final scale
        scale = 2 ** L
        n_tok = compressed.shape[1]
        positions = (torch.arange(n_tok, device=hidden_states.device) * scale).unsqueeze(0).expand(B, -1)
        cos, sin = self.rotary_emb(compressed, positions)
        return apply_rotary_pos_emb(compressed.unsqueeze(1), cos, sin)

    def _compress_idx(self, hidden_states, n_win, usable):
        return self._flat_two_series_compress(
            hidden_states, n_win, usable,
            self.idx_kv_proj, self.idx_gate_proj, self.idx_position_bias,
            self.idx_norm, self.index_head_dim
        )

    def _postprocess_block_bias(self, block_bias, compressed_kv):
        return block_bias  # no expansion needed, KV count matches index count


# =============================================================================
# Wrapper models (same pattern as model.py)
# =============================================================================
class FlatWrapper(nn.Module):
    def __init__(self, hidden_size=128):
        super().__init__()
        self.attn = CSAAttention(
            hidden_size=hidden_size, num_heads=4, head_dim=32,
            q_lora_rank=64, compress_rate=4, index_topk=16, sliding_window=32)
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x):
        return self.norm(self.attn(x) + x)


class ModifiedWrapper(nn.Module):
    def __init__(self, hidden_size=128):
        super().__init__()
        self.attn = ModifiedCSAAttention(
            hidden_size=hidden_size, num_heads=4, head_dim=32,
            q_lora_rank=64, compress_rate=4, index_topk=16, sliding_window=32)
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x):
        return self.norm(self.attn(x) + x)


class StackedWrapper(nn.Module):
    def __init__(self, hidden_size=128):
        super().__init__()
        self.attn = ModifiedStackedCSAAttention(
            hidden_size=hidden_size, num_heads=4, head_dim=32,
            q_lora_rank=64, compress_rate=4, index_topk=16, sliding_window=32)
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x):
        return self.norm(self.attn(x) + x)


class NormalWrapper(nn.Module):
    def __init__(self, hidden_size=128):
        super().__init__()
        self.attn = NormalAttention(
            hidden_size=hidden_size, num_heads=4, head_dim=32,
            q_lora_rank=64, o_groups=4, o_lora_rank=128)
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x):
        return self.norm(self.attn(x) + x)


class FlatPlusWrapper(nn.Module):
    def __init__(self, hidden_size=128):
        super().__init__()
        self.attn = FlatPlusAttention(
            hidden_size=hidden_size, num_heads=4, head_dim=32,
            q_lora_rank=64, compress_rate=4, index_topk=16, sliding_window=32)
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x):
        return self.norm(self.attn(x) + x)


class ExpertFlatWrapper(nn.Module):
    def __init__(self, hidden_size=128):
        super().__init__()
        self.attn = ExpertFlatAttention(
            hidden_size=hidden_size, num_heads=4, head_dim=32,
            q_lora_rank=64, compress_rate=8, index_topk=16, sliding_window=32)
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x):
        return self.norm(self.attn(x) + x)


class ExpertPlusPlusWrapper(nn.Module):
    def __init__(self, hidden_size=128):
        super().__init__()
        self.attn = ExpertPlusPlusAttention(
            hidden_size=hidden_size, num_heads=4, head_dim=32,
            q_lora_rank=64, compress_rate=8, index_compress_rate=4,
            index_topk=16, sliding_window=16, o_groups=4, o_lora_rank=64)
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x):
        return self.norm(self.attn(x) + x)

class SurrogateWrapper(nn.Module):
    """Per-token MLP surrogate (v1) — distilled from the teacher at train time."""
    def __init__(self, hidden_size=128, expansion=4, num_layers=1):
        super().__init__()
        self.attn = SurrogateAttention(hidden_size, expansion=expansion,
                                       num_layers=num_layers)
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x):
        return self.norm(self.attn(x) + x)


class SurrogateV2Wrapper(nn.Module):
    """Causal windowed + learned-global surrogate (v2)."""
    def __init__(self, hidden_size=128, window=32, n_global=8):
        super().__init__()
        self.attn = SurrogateAttentionV2(hidden_size, window=window, n_global=n_global)
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x):
        return self.norm(self.attn(x) + x)

# =============================================================================
# Benchmark harness
# =============================================================================
def count_params(model):
    return sum(p.numel() for p in model.parameters())


def benchmark(model, name, batch_size=32, seq_len=256, hidden_size=128,
              forward_only=True, num_warmup=20, num_iters=100):
    """Benchmark forward-only (inference) or forward+backward (training)."""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    model.eval() if forward_only else model.train()

    x = torch.randn(batch_size, seq_len, hidden_size, device=device)
    dummy_target = torch.randn(batch_size, seq_len, hidden_size, device=device)

    # Warmup
    for _ in range(num_warmup):
        with torch.set_grad_enabled(not forward_only):
            out = model(x)
            if not forward_only:
                loss = (out - dummy_target).square().mean()
                loss.backward()
                model.zero_grad(set_to_none=True)

    # Sync before timing
    if device.type == 'cuda':
        torch.cuda.synchronize()

    # Timed runs
    torch.cuda.empty_cache() if device.type == 'cuda' else None
    torch.cuda.reset_peak_memory_stats() if device.type == 'cuda' else None

    start = time.perf_counter()
    for _ in range(num_iters):
        with torch.set_grad_enabled(not forward_only):
            out = model(x)
            if not forward_only:
                loss = (out - dummy_target).square().mean()
                loss.backward()
                model.zero_grad(set_to_none=True)

    if device.type == 'cuda':
        torch.cuda.synchronize()

    elapsed = time.perf_counter() - start
    avg_ms = 1000 * elapsed / num_iters

    return {
        'name': name,
        'mode': 'inference' if forward_only else 'training',
        'avg_ms': avg_ms,
        'samples_per_sec': batch_size * num_iters / elapsed if forward_only else batch_size * num_iters / (elapsed * 2),
        'batch_size': batch_size,
        'params_m': count_params(model) / 1e6,
    }


def print_results(results, perf_data):
    """Print formatted results with performance/speed ratios."""
    print(f"\n{'='*90}")
    print(f"{'Variant':<38} {'Val MSE':>9} {'Params(M)':>9} {'Fwd(ms)':>8} {'Trn(ms)':>8}  {'Perf/Spd':>8}  {'Ratio':>6}")
    print(f"{'-'*90}")

    # Find best perf/speed ratio
    best_ratio = float('-inf')
    best_name = None

    for r in results:
        name = r['name']
        fwd_ms = r['avg_ms']
        perf = perf_data.get(name)  # val MSE (lower is better)

    # Build combined table
    fwd_res = {r['name']: r for r in results if r['mode'] == 'inference'}
    trn_res = {r['name']: r for r in results if r['mode'] == 'training'}

    for name in fwd_res:
        f = fwd_res[name]
        t = trn_res.get(name, f)
        perf = perf_data.get(name, 1.0)
        params_m = f['params_m']

        # Performance/speed: lower MSE and lower time = better
        # higher score = better (like "quality per millisecond")
        # We use (1/perf) / time to get "inverse-MSE per millisecond"
        perf_per_fwd_ms = (1.0 / perf) / f['avg_ms'] * 1000  # scale to readable

        ratio = perf_per_fwd_ms
        if ratio > best_ratio:
            best_ratio = ratio
            best_name = name

        print(f"  {name:<36} {perf:>9.4f} {params_m:>9.2f} {f['avg_ms']:>8.2f} {t['avg_ms']:>8.2f}  {perf_per_fwd_ms:>8.1f} {'🏆' if ratio == best_ratio else '':>6}")

    print(f"{'='*90}")
    print(f"  Perf/Spd = (1 / Val MSE) / Forward(ms) × 1000  (higher = better)")
    print(f"  🏆 Best performance/speed ratio: {best_name}")
    print()


def main():
    # Performance data from our runs (Val MSE at 10 epochs, ETTh1)
    # Using the most recent run from each variant
    perf_data = {
        'Flat (64 KV)':       0.1085,  # from compare.py run
        'FlatPlus (64 KV)':   0.1098,  # from compare.py run
        'Normal (256 KV)':    0.1083,  # from compare.py run
        'Modified (128 KV)':  0.1088,  # from compare.py run
        'Stacked (64 KV)':    0.1116,
        'ExpertFlat (68 KV)':   0.1102,  # from compare.py run
        'ExpertPlusPlus (52 KV)': 0.1099,  # from compare.py run
        'Surrogate MLP':        0.1424,  # distilled from Normal (5+1 epochs)
        'Surrogate Win+Glob':   0.1269,  # distilled from Normal (5+1 epochs)
    }

    model_map = {
        'Flat (64 KV)':          lambda: FlatWrapper(),
        'FlatPlus (64 KV)':      lambda: FlatPlusWrapper(),
        'Normal (256 KV)':       lambda: NormalWrapper(),
        'Modified (128 KV)':     lambda: ModifiedWrapper(),
        'Stacked (64 KV)':       lambda: StackedWrapper(),
        'ExpertFlat (68 KV)':    lambda: ExpertFlatWrapper(),
        'ExpertPlusPlus (52 KV)': lambda: ExpertPlusPlusWrapper(),
        'Surrogate MLP':         lambda: SurrogateWrapper(),
        'Surrogate Win+Glob':    lambda: SurrogateV2Wrapper(),
    }

    all_results = []

    for name, builder in model_map.items():
        model = builder()
        params_m = count_params(model) / 1e6

        # Inference (forward only)
        print(f"\n  Benchmarking {name} — inference...")
        fwd_res = benchmark(model, name, forward_only=True)
        all_results.append(fwd_res)

        # Training (forward + backward)
        print(f"  Benchmarking {name} — training...")
        trn_res = benchmark(model, name, forward_only=False)
        all_results.append(trn_res)

        print(f"    Fwd: {fwd_res['avg_ms']:.2f}ms, Trn: {trn_res['avg_ms']:.2f}ms, Params: {params_m:.2f}M")

    print_results(all_results, perf_data)

    # Detailed comparison — data-driven over model_map so new variants
    # (surrogates, etc.) appear automatically.
    print(f"{'='*90}")
    print(f"  DETAILED COMPARISON")
    print(f"{'='*90}")

    names = list(model_map.keys())
    fwd = {n: next(r for r in all_results if r['name'] == n and r['mode'] == 'inference') for n in names}
    trn = {n: next(r for r in all_results if r['name'] == n and r['mode'] == 'training') for n in names}

    header = f"  {'Metric':<24}"
    for n in names:
        header += f" {n[:11]:>12}"
    print(header)
    print(f"  {'-'* (24 + 13 * len(names))}")

    def row(label, fmt, get):
        line = f"  {label:<24}"
        for n in names:
            line += f" {fmt(get(n)):>12}"
        print(line)

    row('Val MSE (↓)', '{:.4f}'.format, lambda n: perf_data.get(n, 1.0))
    row('Param Count (M)', '{:.2f}'.format, lambda n: fwd[n]['params_m'])
    row('Forward Latency (ms)', '{:.2f}'.format, lambda n: fwd[n]['avg_ms'])
    row('Training Step (ms)', '{:.2f}'.format, lambda n: trn[n]['avg_ms'])

    print(f"\n  {'Speed relative to Flat (×)':<40}")
    base_f, base_t = fwd[names[0]]['avg_ms'], trn[names[0]]['avg_ms']
    row('Forward latency', '{:.2f}×'.format, lambda n: base_f / fwd[n]['avg_ms'])
    row('Training step', '{:.2f}×'.format, lambda n: base_t / trn[n]['avg_ms'])

    # Performance/Speed composite
    print(f"\n  {'Composite: (1/ValMSE) / FwdTime × 1000 (↑)':<40}")
    row('Score', '{:.1f}'.format, lambda n: (1.0 / max(perf_data.get(n, 1.0), 1e-6)) / fwd[n]['avg_ms'] * 1000)

    best = max(names, key=lambda n: (1.0 / max(perf_data.get(n, 1.0), 1e-6)) / fwd[n]['avg_ms'] * 1000)
    print(f"\n  🏆 Best performance/speed ratio: {best}")


if __name__ == '__main__':
    main()
