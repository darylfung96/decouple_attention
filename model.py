from attention import CSAAttention
import torch
import torch.nn as nn

from modified_attention import ModifiedCSAAttention
from normal_attention import NormalAttention
from flat_plus_attention import FlatPlusAttention
from expert_flat_attention import ExpertFlatAttention
from expert_plus_plus_attention import ExpertPlusPlusAttention

# ==========================================
# 2. Minimal Time-Series Transformer Wrapper
# ==========================================
class CSATimeSeriesModel(nn.Module):
    def __init__(self, num_features, hidden_size=128, lookback=256, horizon=96):
        super().__init__()
        self.num_features = num_features
        self.lookback = lookback
        self.horizon = horizon
        
        # Embed each time step's features into the hidden dimension
        self.input_proj = nn.Linear(num_features, hidden_size)
        self.pos_embedding = nn.Parameter(torch.randn(1, lookback, hidden_size))
        
        # Our CSA Attention Block
        self.attn = CSAAttention(
            hidden_size=hidden_size, 
            num_heads=4, 
            head_dim=32, 
            q_lora_rank=64,        # Low-rank projection for queries
            compress_rate=4,       # Compress 4 hours into 1 KV block
            index_topk=16,         # Each query attends to top 16 relevant historical blocks
            sliding_window=32      # Always look at the last 32 hours
        )
        self.norm1 = nn.LayerNorm(hidden_size)
        
        # Simple MLP block
        self.mlp = nn.Sequential(
            nn.Linear(hidden_size, hidden_size * 4),
            nn.GELU(),
            nn.Linear(hidden_size * 4, hidden_size)
        )
        self.norm2 = nn.LayerNorm(hidden_size)
        
        # Output head (FROZEN task, plan/gates/gate1/gate1_task.md §1-2): direct H-step forecast.
        # From the final encoded sequence [B, L, H] we keep the LAST hidden state
        # (position t, K=1) and project to all H*F future values in ONE forward pass.
        # Encoder stack above is untouched (all attention variants identical).
        self.output_proj = nn.Linear(hidden_size, horizon * num_features)

    def forward(self, x):
        # x shape: [Batch, Lookback, Features]
        x = self.input_proj(x) + self.pos_embedding
        
        # Attention + Residual
        attn_out = self.attn(x)
        x = self.norm1(x + attn_out)
        
        # MLP + Residual
        mlp_out = self.mlp(x)
        x = self.norm2(x + mlp_out)
        
        # Direct forecast: [B, H*F] from the last encoded position -> [B, H, F].
        # loss = MSELoss(out, y) with y = data[idx+L : idx+L+H]; no slicing needed.
        out = self.output_proj(x[:, -1, :])                     # [B, H*F]
        out = out.view(-1, self.horizon, self.num_features)     # [B, H, F]
        return out


class ModifiedCSATimeSeriesModel(CSATimeSeriesModel):
    def __init__(self, num_features, hidden_size=128, lookback=256, horizon=96):
        super().__init__(num_features, hidden_size, lookback, horizon)
        self.attn = ModifiedCSAAttention(
            hidden_size=hidden_size, 
            num_heads=4, 
            head_dim=32, 
            q_lora_rank=64,        # Low-rank projection for queries
            compress_rate=4,       # Compress 4 hours into 1 KV block
            index_topk=16,         # Each query attends to top 16 relevant historical blocks
            sliding_window=32      # Always look at the last 32 hours
        )


class NormalTimeSeriesModel(CSATimeSeriesModel):
    """Standard full quadratic attention wrapper."""
    def __init__(self, num_features, hidden_size=128, lookback=256, horizon=96):
        super().__init__(num_features, hidden_size, lookback, horizon)
        self.attn = NormalAttention(
            hidden_size=hidden_size, 
            num_heads=4, 
            head_dim=32, 
            q_lora_rank=64,
            compress_rate=4,       # unused, kept for API compatibility
            index_topk=16,
            sliding_window=32,
            o_groups=4,
            o_lora_rank=128,
        )


class FlatPlusTimeSeriesModel(CSATimeSeriesModel):
    """FlatPlus: gated residual KV + learned linear pool indexer."""
    def __init__(self, num_features, hidden_size=128, lookback=256, horizon=96):
        super().__init__(num_features, hidden_size, lookback, horizon)
        self.attn = FlatPlusAttention(
            hidden_size=hidden_size, 
            num_heads=4, 
            head_dim=32, 
            q_lora_rank=64,
            compress_rate=4,
            index_topk=16,
            sliding_window=32,
        )


class ExpertFlatTimeSeriesModel(CSATimeSeriesModel):
    """ExpertFlat: 8:1 aggressive compression with Flat's proven mechanism."""
    def __init__(self, num_features, hidden_size=128, lookback=256, horizon=96):
        super().__init__(num_features, hidden_size, lookback, horizon)
        self.attn = ExpertFlatAttention(
            hidden_size=hidden_size, 
            num_heads=4, 
            head_dim=32, 
            q_lora_rank=64,
            compress_rate=8,
            index_topk=16,
            sliding_window=32,
        )


class ExpertPlusPlusTimeSeriesModel(CSATimeSeriesModel):
    """ExpertPlusPlus: decoupled granularity — 8:1 KV + 4:1 routing + shared-Q + slim O.

    Target: ≥30% faster than Flat at the SAME accuracy (fine 4:1 router preserved).
    """
    def __init__(self, num_features, hidden_size=128, lookback=256, horizon=96):
        super().__init__(num_features, hidden_size, lookback, horizon)
        self.attn = ExpertPlusPlusAttention(
            hidden_size=hidden_size, 
            num_heads=4, 
            head_dim=32, 
            q_lora_rank=64,
            compress_rate=8,
            index_compress_rate=4,
            index_topk=16,
            sliding_window=16,
            o_groups=4,
            o_lora_rank=64,
        )

    