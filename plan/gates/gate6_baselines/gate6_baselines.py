#!/usr/bin/env python3
"""Gate 6 — external baselines under the frozen direct-96 task (Gate-6 scope).

Purpose: close the paper's largest acknowledged gap (no external baselines) by
running two standard published forecasting baselines under the IDENTICAL frozen
protocol used by Gates 2/3 (task, split, normalization, optimizer, schedule,
seeds), so results are protocol-comparable with the in-family runs:

  DLinear  : Liu et al. 2023 (LTSF-Linear, AAAI 2023), channel-shared
             configuration (individual=False, the script default): series
             decomposition (moving average, kernel 25) + one seasonal and
             one trend Linear applied to every channel. NOTE: the official
             script trains DLinear at lr=5e-3; this harness keeps the
             frozen protocol's lr=1e-4 for protocol comparability, which
             may under-train the linear head (declared limitation).
  PatchTST : Nie et al. 2023 (ICLR 2023), channel-independent, official
             supervised ETTh1 configuration: patch 16, stride 8 (31 patches),
             d_model 16, n_heads 4, e_layers 3, d_ff 128, GELU, dropout 0.3,
             learnable pos emb, RevIN, flatten head.

Protocol (plan/benchmark_protocol.md — byte-identical contract to gate3):
  AdamW lr=1e-4 wd=1e-5, grad clip 10.0, batch 32, 10 epochs FIXED, no
  scheduler/warm-up, fp32 CPU, threads=8, paired seeds {42,123,2024,7,99};
  torch.manual_seed(seed) before data load AND model init (same seeding order
  as gate3_harness, so DataLoader shuffle order is paired per seed).
  Task: direct-96, L=256, H=96, pooled [B,H,F] MSE, standardized units.

Deviation note (declared): baselines keep their PUBLISHED architecture choices
(channel independence, RevIN/decomposition, dropout) rather than the family's
auxiliary contract — the comparison freezes the protocol, not the architecture.
This mirrors standard practice and is stated in the paper.

CLI modes:
  --dry-run : print config + param counts. No training.
  --smoke   : 1 epoch on bounded subsets; prints MSE + time estimate; saves nothing.
  --full    : 10 epochs, full protocol; APPENDS one JSON line to
              plan/gates/gate6_baselines/results/<dataset>.jsonl
              (idempotent per (variant, seed)).

Exit codes: 0 on success; non-zero on failure.
"""
import argparse
import datetime
import json
import math
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
# gate3 dir (dataset registry) is a sibling of this script's directory
GATE3_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gate3")
if GATE3_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(GATE3_DIR))

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset

from dataset import ETTForecastDataset
import gate3_datasets as g3

# ── Frozen task constants (plan/gates/gate1/gate1_task.md) ─────────────────────
LOOKBACK = 256
HORIZON = 96
BATCH_SIZE = 32

# ── Protocol (plan/benchmark_protocol.md) ──────────────────────────────────────
LR = 1e-4
WEIGHT_DECAY = 1e-5
CLIP = 10.0
EPOCHS = 10
SEEDS = [42, 123, 2024, 7, 99]

VARIANTS = ("DLinear", "PatchTST")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
SMOKE_TRAIN_BATCHES = 40
SMOKE_VAL_BATCHES = 10


# ═══════════════════════════════════════════════════════════════════════════════
# DLinear (Liu et al., AAAI 2023) — channel-independent, published form
# ═══════════════════════════════════════════════════════════════════════════════
class MovingAvg(nn.Module):
    """Moving-average smoothing with edge replication padding (kernel 25, as published)."""

    def __init__(self, kernel_size):
        super().__init__()
        self.kernel_size = kernel_size

    def forward(self, x):                      # x: [B, L, F]
        front = x[:, 0:1, :].repeat(1, (self.kernel_size - 1) // 2, 1)
        end = x[:, -1:, :].repeat(1, self.kernel_size - 1 - (self.kernel_size - 1) // 2, 1)
        x = torch.cat([front, x, end], dim=1)
        x = x.unfold(dimension=1, size=self.kernel_size, step=1).mean(dim=-1)
        return x                               # [B, L, F]


class SeriesDecomp(nn.Module):
    def __init__(self, kernel_size):
        super().__init__()
        self.moving_avg = MovingAvg(kernel_size)

    def forward(self, x):
        trend = self.moving_avg(x)
        return x - trend, trend


class DLinear(nn.Module):
    """Channel-independent DLinear: one seasonal + one trend Linear per channel.

    Implemented as a single Linear over the flattened channel axis (shared
    weights across channels = channel-independent, as published).
    """

    def __init__(self, num_features, lookback=LOOKBACK, horizon=HORIZON, kernel_size=25):
        super().__init__()
        self.decomp = SeriesDecomp(kernel_size)
        self.linear_seasonal = nn.Linear(lookback, horizon)
        self.linear_trend = nn.Linear(lookback, horizon)

    def forward(self, x):                      # x: [B, L, F]
        seasonal, trend = self.decomp(x)
        # channel-independent: apply the SAME linear to every channel
        s = self.linear_seasonal(seasonal.permute(0, 2, 1)).permute(0, 2, 1)
        t = self.linear_trend(trend.permute(0, 2, 1)).permute(0, 2, 1)
        return s + t                           # [B, H, F]


# ═══════════════════════════════════════════════════════════════════════════════
# PatchTST (Nie et al., ICLR 2023) — channel-independent, published core
# ═══════════════════════════════════════════════════════════════════════════════
class RevIN(nn.Module):
    """Reversible instance normalization (per instance, per channel; eps 1e-5)."""

    def __init__(self, eps=1e-5):
        super().__init__()
        self.eps = eps

    def forward(self, x, mode):
        if mode == "norm":
            self._mean = x.mean(dim=1, keepdim=True).detach()
            self._std = (x.var(dim=1, keepdim=True, unbiased=False) + self.eps).sqrt().detach()
            return (x - self._mean) / self._std
        if mode == "denorm":
            return x * self._std + self._mean
        raise ValueError(mode)


class PatchTST(nn.Module):
    def __init__(self, num_features, lookback=LOOKBACK, horizon=HORIZON,
                 patch_len=16, stride=8, d_model=16, n_heads=4, e_layers=3,
                 d_ff=128, dropout=0.3):
        super().__init__()
        self.patch_len, self.stride = patch_len, stride
        self.num_patches = (lookback - patch_len) // stride + 1
        self.revin = RevIN()
        # patch embedding: Linear on each patch (equivalent to the published Conv1d
        # with kernel=stride=patch_len at stride 'stride' on non-overlapping patches;
        # here patches overlap, so Linear-on-unfold is the faithful form)
        self.patch_embed = nn.Linear(patch_len, d_model)
        self.pos_emb = nn.Parameter(torch.randn(1, self.num_patches, d_model) * 0.02)
        self.dropout = nn.Dropout(dropout)
        layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=n_heads,
                                           dim_feedforward=d_ff, dropout=dropout,
                                           activation="gelu", batch_first=True,
                                           norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, num_layers=e_layers)
        self.head = nn.Linear(self.num_patches * d_model, horizon)

    def forward(self, x):                      # x: [B, L, F]
        B, L, F = x.shape
        z = self.revin(x, "norm")                                  # [B, L, F]
        z = z.permute(0, 2, 1)                                     # [B, F, L]
        z = z.unfold(dimension=2, size=self.patch_len, step=self.stride)  # [B, F, P, patch]
        P = z.shape[2]
        assert P == self.num_patches, f"patches {P} != {self.num_patches}"
        z = z.reshape(B * F, P, self.patch_len)
        z = self.dropout(self.patch_embed(z) + self.pos_emb)       # [B*F, P, D]
        z = self.encoder(z)                                        # [B*F, P, D]
        y = self.head(z.flatten(1))                                # [B*F, H]
        y = y.reshape(B, F, HORIZON).permute(0, 2, 1)              # [B, H, F]
        return self.revin(y, "denorm")


# ═══════════════════════════════════════════════════════════════════════════════
# Harness (protocol identical to gate3_harness.py)
# ═══════════════════════════════════════════════════════════════════════════════
def build_model(dataset_name, variant, seed):
    F = g3.DATASETS[dataset_name][3]
    torch.manual_seed(seed)           # determinism: seed before model init (as gate3)
    if variant == "DLinear":
        return DLinear(F)
    if variant == "PatchTST":
        return PatchTST(F)
    raise ValueError(variant)


def count_params(model):
    return sum(p.numel() for p in model.parameters())


def make_loaders(dataset_name, seed, smoke):
    """Seed BEFORE data loading (shuffle order from torch RNG; as gate3)."""
    torch.manual_seed(seed)
    tr, va, te, _ = g3.preprocess(dataset_name)
    mk = lambda d: ETTForecastDataset(d, lookback=LOOKBACK, horizon=HORIZON)
    train_ds, val_ds, test_ds = mk(tr), mk(va), mk(te)
    if smoke:
        train_ds = Subset(train_ds, range(SMOKE_TRAIN_BATCHES * BATCH_SIZE))
        val_ds = Subset(val_ds, range(SMOKE_VAL_BATCHES * BATCH_SIZE))
        return (DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True),
                DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False), None)
    return (DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True),
            DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False),
            DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False))


@torch.no_grad()
def evaluate(model, loader):
    model.eval()
    total, n = 0.0, 0
    for x, y in loader:
        out = model(x)
        assert out.shape == (x.shape[0], HORIZON, x.shape[2]), \
            f"bad output shape {tuple(out.shape)}"
        total += F.mse_loss(out, y).item() * x.shape[0]
        n += x.shape[0]
    return total / n if n else float("nan")


def train_and_eval(model, train_loader, val_loader, test_loader, epochs):
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    final_train, final_val = None, None
    for epoch in range(1, epochs + 1):
        model.train()
        total, n = 0.0, 0
        for x, y in train_loader:
            optimizer.zero_grad()
            out = model(x)
            assert out.shape == (x.shape[0], HORIZON, x.shape[2]), \
                f"bad output shape {tuple(out.shape)}"
            loss = F.mse_loss(out, y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            optimizer.step()
            total += loss.item() * x.shape[0]
            n += x.shape[0]
        final_train = total / n
        final_val = evaluate(model, val_loader)
        if not math.isfinite(final_train) or not math.isfinite(final_val):
            raise RuntimeError(f"non-finite loss at epoch {epoch}: "
                               f"train={final_train} val={final_val}")
        print(f"      epoch {epoch:2d}/{epochs}  train_mse={final_train:.6f}  "
              f"val_mse={final_val:.6f}", flush=True)
    test_mse = evaluate(model, test_loader) if test_loader is not None else None
    return final_train, final_val, test_mse


def load_completed(results_path):
    done = set()
    if os.path.exists(results_path):
        with open(results_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    done.add((rec["variant"], int(rec["seed"])))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    return done


def results_path(dataset_name):
    return os.path.join(RESULTS_DIR, f"{dataset_name}.jsonl")


def print_config(dataset_name, variant, threads, smoke=False):
    F = g3.DATASETS[dataset_name][3]
    print(f"== Gate 6 baseline harness (CPU PyTorch, threads={threads}, "
          f"dataset={dataset_name}, variant={variant}, F={F}) ==", flush=True)
    print(f"  task: frozen direct-96, L={LOOKBACK}, H={HORIZON}, batch={BATCH_SIZE}")
    print(f"  protocol: AdamW lr={LR} wd={WEIGHT_DECAY} clip={CLIP} epochs={EPOCHS} "
          f"(fixed), no scheduler/warm-up, fp32")
    wc = g3.window_counts(dataset_name)
    print(f"  windows: train={wc['train']} val={wc['val']} test={wc['test']} "
          f"(batches: {wc['train'] // BATCH_SIZE} / {wc['val'] // BATCH_SIZE} / "
          f"{wc['test'] // BATCH_SIZE})")


def run_dry_run(dataset_name, variant):
    print_config(dataset_name, variant, 8)
    for seed in [42]:
        model = build_model(dataset_name, variant, seed=seed)
        print(f"  params: total={count_params(model)}")
    return 0


def run_smoke(dataset_name, variant, seed, threads):
    print_config(dataset_name, variant, threads, smoke=True)
    t0 = time.time()
    train_loader, val_loader, _ = make_loaders(dataset_name, seed, smoke=True)
    print(f"[smoke] train batches={len(train_loader)} val batches={len(val_loader)}")
    model = build_model(dataset_name, variant, seed)
    print(f"  params: total={count_params(model)}")
    train_mse, val_mse, _ = train_and_eval(model, train_loader, val_loader, None, epochs=1)
    dt = time.time() - t0
    per_batch = dt / len(train_loader)
    full_batches = g3.window_counts(dataset_name)["train"] // BATCH_SIZE
    est_min = per_batch * full_batches * EPOCHS / 60.0
    print(f"      smoke train_mse={train_mse:.6f} val_mse={val_mse:.6f}")
    print(f"      [estimate] {per_batch:.2f} s/batch -> full 10-epoch run ~{est_min:.0f} min")
    print("[smoke] done — nothing saved")
    return 0


def run_full(dataset_name, variant, seed, threads):
    # Declared omissions (2026-09-01/03, user decisions):
    #  - traffic/PatchTST: 862-ch channel-independence ≈ 13 h/seed CPU
    #  - electricity/PatchTST: 321-ch ≈ 8 h/seed CPU
    #  - weather/PatchTST: 21-ch ≈ 3 h/seed (harmless but same confounded
    #    anchor; PatchTST cut entirely 2026-09-03 — adds no message beyond
    #    DLinear's, and DeepSeek-V4's own evaluation is internal-only)
    # Skipped with an explicit reason so the audit reports them as declared,
    # not missing. All DLinear runs are unaffected.
    if variant == "PatchTST" and dataset_name in ("solar", "electricity",
                                                   "weather", "traffic"):
        print(f"[gate6] DECLARED OMISSION: {dataset_name}/{variant} seed={seed} "
              f"skipped — PatchTST anchor cut (user decision 2026-09-03; heavy "
              f"CPU tail, no message beyond DLinear); see README gate6 notes",
              flush=True)
        return 0
    print_config(dataset_name, variant, threads)
    path = results_path(dataset_name)
    done = load_completed(path)
    if (variant, seed) in done:
        print(f"[full] ({variant}, seed={seed}) already completed — skipping (idempotent)")
        return 0
    train_loader, val_loader, test_loader = make_loaders(dataset_name, seed, smoke=False)
    print(f"[full] train batches={len(train_loader)} val batches={len(val_loader)} "
          f"test batches={len(test_loader)}", flush=True)
    t0 = time.time()
    model = build_model(dataset_name, variant, seed)
    final_train, final_val, test_mse = train_and_eval(
        model, train_loader, val_loader, test_loader, epochs=EPOCHS)
    rec = {
        "dataset": dataset_name,
        "variant": variant,
        "cell": None,
        "seed": seed,
        "val_mse": round(final_val, 8),
        "test_mse": round(test_mse, 8),
        "final_train_mse": round(final_train, 8),
        "attn_params": count_params(model),
        "full_params": count_params(model),
        "n_train_batches": len(train_loader),
        "n_val_batches": len(val_loader),
        "n_test_batches": len(test_loader),
        "completed_utc": datetime.datetime.now(datetime.timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"      FINAL test_mse={test_mse:.6f} train_mse={final_train:.6f} "
          f"(elapsed {time.time() - t0:.0f}s)", flush=True)
    print(f"      appended: {json.dumps(rec)}", flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description="Gate 6 external-baselines harness")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    p.add_argument("--dataset", required=True, choices=sorted(g3.DATASETS))
    p.add_argument("--variant", required=True, choices=sorted(VARIANTS))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--threads", type=int, default=8)
    args = p.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)

    if args.full:
        return run_full(args.dataset, args.variant, args.seed, args.threads)
    if args.smoke:
        return run_smoke(args.dataset, args.variant, args.seed, args.threads)
    return run_dry_run(args.dataset, args.variant)


if __name__ == "__main__":
    sys.exit(main())
