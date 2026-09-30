#!/usr/bin/env python3
"""Gate 17 — E-2 PatchTST-backbone transfer driver.

Design: plan/gates/gate17_e2/gate17_design.md (pre-registered).
Published PatchTST backbone verbatim except each encoder layer's self-attention
is replaced by our cell attention (pre-norm, same FFN/dropout/head/RevIN).
Results go to NEW files only (old manifests untouched).

Usage (repo root, uv env):
  ~/.uv_env/py311/bin/python plan/gates/gate17_e2/gate17_run.py --dry-run
  ~/.uv_env/py311/bin/python plan/gates/gate17_e2/gate17_run.py --full   # 40 runs
"""
import argparse
import datetime
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for p in [REPO_ROOT,
          os.path.join(REPO_ROOT, "plan", "gates", "gate6_baselines"),
          os.path.join(REPO_ROOT, "plan", "gates", "gate3")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from expert_plus_plus_attention import ExpertPlusPlusAttention
from dataset import ETTForecastDataset
import gate3_datasets as g3
from gate6_baselines import RevIN, LR, WEIGHT_DECAY, CLIP, EPOCHS, BATCH_SIZE

LOOKBACK, HORIZON = 256, 96
D_MODEL, N_HEADS, HEAD_DIM = 16, 4, 4
Q_RANK = O_RANK = 8
O_GROUPS, WINDOW, TOPK = 4, 8, 4
CELLS = [(4, 4), (8, 4), (4, 8), (8, 8)]
DATASETS = ["etth1", "etth2"]
SEEDS = [42, 123, 2024, 7, 99]
PROVENANCE = "gate17/uv-torch2.6.0/fixed-mapping"
RESULTS_DIR = os.path.join(HERE, "results")


class CellEncoderLayer(nn.Module):
    """Pre-norm encoder layer with our cell attention (mirrors norm_first=True)."""

    def __init__(self, ckv, c_r):
        super().__init__()
        self.attn = ExpertPlusPlusAttention(
            hidden_size=D_MODEL, num_heads=N_HEADS, head_dim=HEAD_DIM,
            q_lora_rank=Q_RANK, compress_rate=ckv, index_compress_rate=c_r,
            index_topk=TOPK, index_n_heads=N_HEADS, index_head_dim=HEAD_DIM,
            sliding_window=WINDOW, o_groups=O_GROUPS, o_lora_rank=O_RANK)
        self.norm1 = nn.LayerNorm(D_MODEL)
        self.norm2 = nn.LayerNorm(D_MODEL)
        self.ffn = nn.Sequential(nn.Linear(D_MODEL, 128), nn.GELU(),
                                 nn.Linear(128, D_MODEL))

    def forward(self, z):
        z = z + self.attn(self.norm1(z))
        return z + self.ffn(self.norm2(z))


class PatchTSTCells(nn.Module):
    """PatchTST backbone (published config) with cell attention in all 3 layers."""

    def __init__(self, num_features, ckv, c_r, patch_len=16, stride=8, dropout=0.3):
        super().__init__()
        self.patch_len, self.stride = patch_len, stride
        self.num_patches = (LOOKBACK - patch_len) // stride + 1
        self.revin = RevIN()
        self.patch_embed = nn.Linear(patch_len, D_MODEL)
        self.pos_emb = nn.Parameter(torch.randn(1, self.num_patches, D_MODEL) * 0.02)
        self.dropout = nn.Dropout(dropout)
        self.layers = nn.ModuleList([CellEncoderLayer(ckv, c_r) for _ in range(3)])
        self.head = nn.Linear(self.num_patches * D_MODEL, HORIZON)

    def forward(self, x):                      # x: [B, L, F]
        B, L, F = x.shape
        z = self.revin(x, "norm")
        z = z.permute(0, 2, 1)
        z = z.unfold(dimension=2, size=self.patch_len, step=self.stride)
        assert z.shape[2] == self.num_patches
        z = z.reshape(B * F, self.num_patches, self.patch_len)
        z = self.dropout(self.patch_embed(z) + self.pos_emb)
        for layer in self.layers:
            z = layer(z)
        y = self.head(z.flatten(1))
        y = y.reshape(B, F, HORIZON).permute(0, 2, 1)
        return self.revin(y, "denorm")


def build_model(num_features, cell, seed):
    torch.manual_seed(seed)
    return PatchTSTCells(num_features, cell[0], cell[1])


def count_attn_params(model):
    return sum(p.numel() for l in model.layers for p in l.attn.parameters())


def make_loaders(dataset_name, seed):
    torch.manual_seed(seed)
    tr, va, te, _ = g3.preprocess(dataset_name)
    mk = lambda d: ETTForecastDataset(d, lookback=LOOKBACK, horizon=HORIZON)
    return (DataLoader(mk(tr), batch_size=BATCH_SIZE, shuffle=True),
            DataLoader(mk(va), batch_size=BATCH_SIZE, shuffle=False),
            DataLoader(mk(te), batch_size=BATCH_SIZE, shuffle=False))


@torch.no_grad()
def evaluate(model, loader):
    model.eval()
    total, n = 0.0, 0
    for x, y in loader:
        out = model(x)
        assert out.shape == (x.shape[0], HORIZON, x.shape[2]), tuple(out.shape)
        total += F.mse_loss(out, y).item() * x.shape[0]
        n += x.shape[0]
    return total / n if n else float("nan")


def train_and_eval(model, train_loader, val_loader, test_loader):
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    final_train = final_val = None
    for epoch in range(1, EPOCHS + 1):
        model.train()
        total, n = 0.0, 0
        for x, y in train_loader:
            optimizer.zero_grad()
            out = model(x)
            loss = F.mse_loss(out, y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            optimizer.step()
            total += loss.item() * x.shape[0]
            n += x.shape[0]
        final_train, final_val = total / n, evaluate(model, val_loader)
        print(f"      epoch {epoch:2d}/{EPOCHS}  train={final_train:.6f}  "
              f"val={final_val:.6f}", flush=True)
    return final_train, final_val, evaluate(model, test_loader)


def load_completed(path):
    done = set()
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                done.add((tuple(rec["cell"]), int(rec["seed"])))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return done


def append(path, rec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def dry_run():
    print("== Gate17 dry-run: param ledger (ranks fixed at 8,8) ==")
    for cell in CELLS:
        torch.manual_seed(42)
        m = PatchTSTCells(7, cell[0], cell[1])
        print(f"  {cell}: attn={count_attn_params(m)} "
              f"full={sum(p.numel() for p in m.parameters())}")
    print("dry-run OK (deltas are position-bias sizes by design)")
    return 0


def run_full(threads):
    torch.set_num_threads(threads)
    total_plan = []
    for ds in DATASETS:
        path = os.path.join(RESULTS_DIR, f"{ds}.jsonl")
        done = load_completed(path)
        for cell in CELLS:
            for s in SEEDS:
                if (cell, s) not in done:
                    total_plan.append((ds, cell, s))
    print(f"=== Gate17: {len(total_plan)} pending (4 cells x 2 ds x 5 seeds) ===",
          flush=True)
    for i, (ds, cell, seed) in enumerate(total_plan, 1):
        F = g3.DATASETS[ds][3]
        print(f"--- [{i}/{len(total_plan)}] {ds} {cell} seed={seed} START "
              f"{datetime.datetime.now(datetime.timezone.utc).strftime('%FT%TZ')} ---",
              flush=True)
        t0 = time.time()
        train_loader, val_loader, test_loader = make_loaders(ds, seed)
        model = build_model(F, cell, seed)
        final_train, final_val, test_mse = train_and_eval(
            model, train_loader, val_loader, test_loader)
        rec = {"dataset": ds, "cell": list(cell), "seed": seed,
               "val_mse": round(final_val, 8), "test_mse": round(test_mse, 8),
               "final_train_mse": round(final_train, 8),
               "attn_params": count_attn_params(model),
               "full_params": sum(p.numel() for p in model.parameters()),
               "provenance": PROVENANCE,
               "completed_utc": datetime.datetime.now(datetime.timezone.utc)
                                .strftime("%Y-%m-%dT%H:%M:%SZ"),
               "elapsed_s": round(time.time() - t0, 1)}
        append(os.path.join(RESULTS_DIR, f"{ds}.jsonl"), rec)
        print(f"      FINAL val={final_val:.6f} test={test_mse:.6f} "
              f"({rec['elapsed_s']}s)", flush=True)
    print("=== Gate17 complete ===", flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description="Gate 17 PatchTST transfer")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--full", action="store_true")
    p.add_argument("--threads", type=int, default=8)
    args = p.parse_args()
    if args.dry_run:
        return dry_run()
    return run_full(args.threads)


if __name__ == "__main__":
    sys.exit(main())
