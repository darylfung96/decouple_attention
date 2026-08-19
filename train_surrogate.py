"""Joint distillation of a per-token surrogate attention from ExpertPlusPlus.

Idea: ExpertPlusPlus is the best accuracy/speed trade-off among the CSA
variants, but its attention block is still the slowest part of the model
(Q/KV projections + 2 compressors + router/top-k + dense `_attend` + O
projections). Train a cheap per-token MLP (SurrogateAttention) to imitate it,
then swap the surrogate in at evaluation/prediction time.

Phase 1 — Joint distillation (both trainable):
    L = L_task(teacher path) + lambda * MSE(student(h), stopgrad(teacher(h)))

Phase 2 — Surrogate-only fine-tune (teacher not called → effectively frozen):
    L = L_task(surrogate path)
    This co-adapts the downstream layers (norm1/mlp/norm2/output_proj) to the
    surrogate's outputs, closing the train/inference gap of the swap.

Evaluation reports:
    - Teacher path   : val/test MSE (accuracy champion, no swap)
    - Surrogate path : val/test MSE (what you get at inference with the swap)
    - Distillation gap: MSE(student(h), teacher(h)) on the val set
    - Speed          : end-to-end forward (teacher vs surrogate) + block-only

Usage:
    python train_surrogate.py --epochs 5 --finetune-epochs 1 --distill-lambda 0.5
"""
import argparse
import time

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from dataset import ETTForecastDataset, download_and_preprocess_etth1
from expert_plus_plus_attention import ExpertPlusPlusAttention
from normal_attention import NormalAttention
from surrogate_attention import SurrogateAttention, SurrogateAttentionV2


# ==========================================
# Model: teacher (ExpertPlusPlus) + surrogate student, shared downstream
# ==========================================
def build_teacher(teacher_type, hidden_size):
    """Build the teacher attention block for the given type."""
    if teacher_type == 'expertplusplus':
        # Same config as ExpertPlusPlusTimeSeriesModel
        return ExpertPlusPlusAttention(
            hidden_size=hidden_size, num_heads=4, head_dim=32, q_lora_rank=64,
            compress_rate=8, index_compress_rate=4, index_topk=16,
            sliding_window=32, o_groups=4, o_lora_rank=64)
    if teacher_type == 'normal':
        # Same config as NormalTimeSeriesModel (full O(S²) attention)
        return NormalAttention(
            hidden_size=hidden_size, num_heads=4, head_dim=32, q_lora_rank=64,
            compress_rate=4, index_topk=16, sliding_window=32,
            o_groups=4, o_lora_rank=128)
    raise ValueError(f"Unknown teacher type: {teacher_type}")


def build_surrogate(surrogate_type, hidden_size, window=32, n_global=8,
                    expansion=4, num_layers=1):
    """Build the surrogate student for the given type."""
    if surrogate_type == 'mlp':
        return SurrogateAttention(hidden_size, expansion=expansion,
                                  num_layers=num_layers)
    if surrogate_type == 'windowed':
        return SurrogateAttentionV2(hidden_size, window=window, n_global=n_global)
    raise ValueError(f"Unknown surrogate type: {surrogate_type}")


class JointSurrogateTimeSeriesModel(nn.Module):
    def __init__(self, num_features, hidden_size=128, lookback=256, horizon=96,
                 distill_lambda=0.5, teacher_type='expertplusplus',
                 surrogate_type='mlp', window=32, n_global=8,
                 expansion=4, num_layers=1):
        super().__init__()
        self.num_features = num_features
        self.lookback = lookback
        self.horizon = horizon
        self.distill_lambda = distill_lambda
        self.teacher_type = teacher_type
        self.surrogate_type = surrogate_type
        # False → teacher path (task + distillation). True → surrogate only.
        self.use_surrogate = False

        # Embedding (shared by both paths) — same as CSATimeSeriesModel
        self.input_proj = nn.Linear(num_features, hidden_size)
        self.pos_embedding = nn.Parameter(torch.randn(1, lookback, hidden_size))

        # Teacher: chosen attention block
        self.attn = build_teacher(teacher_type, hidden_size)

        # Student: chosen surrogate
        self.surrogate = build_surrogate(surrogate_type, hidden_size,
                                         window=window, n_global=n_global,
                                         expansion=expansion,
                                         num_layers=num_layers)

        # Shared downstream (same as CSATimeSeriesModel, incl. frozen-task head:
        # direct [B, H, F] forecast from the last encoded position).
        self.norm1 = nn.LayerNorm(hidden_size)
        self.mlp = nn.Sequential(
            nn.Linear(hidden_size, hidden_size * 4),
            nn.GELU(),
            nn.Linear(hidden_size * 4, hidden_size),
        )
        self.norm2 = nn.LayerNorm(hidden_size)
        self.output_proj = nn.Linear(hidden_size, horizon * num_features)

    def forward(self, x, return_distill=False):
        h = self.input_proj(x) + self.pos_embedding

        if self.use_surrogate:
            attn_out = self.surrogate(h)
            distill = None
        else:
            teacher_out = self.attn(h)
            student_out = self.surrogate(h)
            distill = F.mse_loss(student_out, teacher_out.detach())
            attn_out = teacher_out

        z = self.norm2(self.mlp(self.norm1(h + attn_out)))
        out = self.output_proj(z[:, -1, :])                    # [B, H*F]
        out = out.view(-1, self.horizon, self.num_features)    # [B, H, F]
        return (out, distill) if return_distill else out

    def param_report(self):
        t = sum(p.numel() for p in self.attn.parameters())
        s = sum(p.numel() for p in self.surrogate.parameters())
        return {'teacher_attn': t / 1e6, 'surrogate': s / 1e6,
                'total': sum(p.numel() for p in self.parameters()) / 1e6}


# ==========================================
# Evaluation
# ==========================================
@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total = 0.0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        out = model(x)  # [B, H, F]; full horizon scored against y (frozen task)
        loss = criterion(out, y)
        total += loss.item()
    return total / len(loader)


@torch.no_grad()
def distillation_gap(model, loader, device):
    """MSE(student(h), teacher(h)) averaged over the loader."""
    model.eval()
    model.use_surrogate = False
    total = 0.0
    n = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        h = model.input_proj(x) + model.pos_embedding
        total += F.mse_loss(model.surrogate(h), model.attn(h)).item()
        n += 1
    return total / n


def timeit(fn, iters=50, warmup=10):
    for _ in range(warmup):
        fn()
    t0 = time.perf_counter()
    for _ in range(iters):
        fn()
    return 1000 * (time.perf_counter() - t0) / iters


# ==========================================
# Main
# ==========================================
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--epochs', type=int, default=5)
    ap.add_argument('--finetune-epochs', type=int, default=1)
    ap.add_argument('--distill-lambda', type=float, default=0.5)
    ap.add_argument('--teacher', type=str, default='expertplusplus',
                    choices=['expertplusplus', 'normal'],
                    help='Teacher attention block to distill from')
    ap.add_argument('--surrogate', type=str, default='mlp',
                    choices=['mlp', 'windowed'],
                    help='Surrogate student: per-token MLP or windowed+global')
    ap.add_argument('--window', type=int, default=32,
                    help='Window size for the windowed surrogate')
    ap.add_argument('--n-global', type=int, default=8,
                    help='Learned global prototypes for the windowed surrogate')
    ap.add_argument('--expansion', type=int, default=4,
                    help='MLP surrogate width = hidden_size * expansion (v1)')
    ap.add_argument('--layers', type=int, default=1,
                    help='Number of hidden layers in the MLP surrogate (v1)')
    ap.add_argument('--batch-size', type=int, default=32)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    print(f"Teacher: {args.teacher}  | Surrogate: {args.surrogate}  "
          f"(window={args.window}, n-global={args.n_global})")
    if args.surrogate == 'mlp':
        print(f"  MLP v1: expansion={args.expansion} (width={128*args.expansion}), "
              f"layers={args.layers}")
    print(f"  distill-lambda={args.distill_lambda}, finetune-epochs={args.finetune_epochs}")

    LOOKBACK, HORIZON = 256, 96

    # 1. Data
    train_data, val_data, test_data = download_and_preprocess_etth1()
    train_loader = DataLoader(ETTForecastDataset(train_data, LOOKBACK, HORIZON),
                              batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(ETTForecastDataset(val_data, LOOKBACK, HORIZON),
                            batch_size=args.batch_size, shuffle=False)
    test_loader = DataLoader(ETTForecastDataset(test_data, LOOKBACK, HORIZON),
                             batch_size=args.batch_size, shuffle=False)

    # 2. Model + optimizer
    num_features = train_data.shape[1]
    model = JointSurrogateTimeSeriesModel(num_features=num_features, hidden_size=128,
                                          lookback=LOOKBACK, horizon=HORIZON,
                                          distill_lambda=args.distill_lambda,
                                          teacher_type=args.teacher,
                                          surrogate_type=args.surrogate,
                                          window=args.window,
                                          n_global=args.n_global,
                                          expansion=args.expansion,
                                          num_layers=args.layers).to(device)
    p = model.param_report()
    print(f"Params — teacher_attn={p['teacher_attn']:.3f}M, "
          f"surrogate={p['surrogate']:.3f}M, total={p['total']:.3f}M")

    criterion = nn.MSELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)

    # 3. Phase 1 — joint distillation
    print(f"\n=== Phase 1: Joint distillation ({args.epochs} epochs) ===")
    print(f"  L = L_task(teacher) + {args.distill_lambda} * MSE(student, stopgrad(teacher))")
    for epoch in range(args.epochs):
        model.train()
        model.use_surrogate = False
        t_task = t_dist = 0.0
        n = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            out, distill = model(x, return_distill=True)
            task = criterion(out, y)  # out=[B,96,7], full horizon scored
            (task + args.distill_lambda * distill).backward()
            optimizer.step()
            t_task += task.item()
            t_dist += distill.item()
            n += 1
        val = evaluate(model, val_loader, criterion, device)
        print(f"  Epoch {epoch+1}/{args.epochs} | task={t_task/n:.4f} "
              f"distill={t_dist/n:.4f} | val(teacher)={val:.4f}")

    # 4. Phase 2 — surrogate-only fine-tune (teacher frozen by not being called)
    print(f"\n=== Phase 2: Surrogate-only fine-tune ({args.finetune_epochs} epochs) ===")
    model.use_surrogate = True
    for epoch in range(args.finetune_epochs):
        model.train()
        t_task = 0.0
        n = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)  # out=[B,96,7], full horizon scored
            loss.backward()
            optimizer.step()
            t_task += loss.item()
            n += 1
        val = evaluate(model, val_loader, criterion, device)
        print(f"  Epoch {epoch+1}/{args.finetune_epochs} | task(surrogate)={t_task/n:.4f} "
              f"| val(surrogate)={val:.4f}")

    # 5. Evaluation: teacher path vs surrogate path
    model.eval()
    model.use_surrogate = False
    val_teacher = evaluate(model, val_loader, criterion, device)
    test_teacher = evaluate(model, test_loader, criterion, device)

    model.use_surrogate = True
    val_surrogate = evaluate(model, val_loader, criterion, device)
    test_surrogate = evaluate(model, test_loader, criterion, device)

    gap = distillation_gap(model, val_loader, device)

    print("\n" + "=" * 72)
    print(f"  {'Path':<22} {'Val MSE':>9} {'Test MSE':>9}")
    print(f"  {'-'*72}")
    print(f"  {'Teacher (' + model.teacher_type + ')':<22} {val_teacher:>9.4f} {test_teacher:>9.4f}")
    print(f"  {'Surrogate (swap-in)':<22} {val_surrogate:>9.4f} {test_surrogate:>9.4f}")
    print(f"  {'Distillation gap (val)':<22} {gap:>9.4f} {'—':>9}")
    print("=" * 72)

    # 6. Speed benchmark (same weights, only the attention block differs)
    print("\n=== Speed benchmark (batch=32, seq=256, same trained weights) ===")
    xb = torch.randn(32, LOOKBACK, num_features, device=device)
    hb = model.input_proj(xb) + model.pos_embedding

    model.use_surrogate = False
    full_teacher_ms = timeit(lambda: model(xb))
    block_teacher_ms = timeit(lambda: model.attn(hb))

    model.use_surrogate = True
    full_surrogate_ms = timeit(lambda: model(xb))
    block_surrogate_ms = timeit(lambda: model.surrogate(hb))

    print(f"  {'Component':<28} {'Teacher (ms)':>12} {'Surrogate (ms)':>14} {'Speedup':>9}")
    print(f"  {'-'*72}")
    print(f"  {'Attention block only':<28} {block_teacher_ms:>12.2f} {block_surrogate_ms:>14.2f} "
          f"{block_teacher_ms/block_surrogate_ms:>8.1f}×")
    print(f"  {'End-to-end forward':<28} {full_teacher_ms:>12.2f} {full_surrogate_ms:>14.2f} "
          f"{full_teacher_ms/full_surrogate_ms:>8.1f}×")
    print("=" * 72)
