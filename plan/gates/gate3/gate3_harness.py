#!/usr/bin/env python3
"""Gate 3 — dataset-coverage training harness (frozen direct-96 task).

Variants (aux contract identical to Gate 2 / baseline gates):
  Normal : model.NormalTimeSeriesModel  (model.py verbatim, as run in baseline gate)
  Flat   : EPPTimeSeriesModel(F, 4, 4)  (imported verbatim from
           plan/gates/gate2/gate2_factorial.py; ranks (64,64))
  DRRA   : EPPTimeSeriesModel(F, 8, 4)  (champion cell; ranks (64,64))

Protocol (plan/benchmark_protocol.md, byte-identical to gate2_factorial.py):
  AdamW lr=1e-4 wd=1e-5, grad clip 10.0, batch 32, 10 epochs FIXED, no
  scheduler/warm-up/mixed-precision, threads=8, paired seeds {42,123,2024,7,99};
  torch.manual_seed(seed) before data load AND model init.
  Task: direct-96, L=256, H=96, F=dataset channels, pooled [B,H,F] MSE,
  standardized units (plan/gates/gate1/gate1_task.md).

CLI modes:
  --dry-run : print dataset/variant config + verified param counts. No training.
  --smoke   : 1 epoch on bounded subsets (first 40*32 train, 10*32 val); prints
              train/val MSE + estimated full-run time; saves nothing.
  --full    : 10 epochs, full train split (shuffle=True), val each epoch, final
              test; APPENDS one JSON line to plan/gates/gate3/results/<dataset>.jsonl
              (idempotent per (variant, seed)).

Exit codes: 0 on success; non-zero (traceback/message) on failure.
"""
import argparse
import datetime
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset

from model import NormalTimeSeriesModel
from dataset import ETTForecastDataset
import gate3_datasets as g3
from plan.gates.gate2.gate2_factorial import EPPTimeSeriesModel

# ── Frozen task constants (plan/gates/gate1/gate1_task.md) ─────────────────────
LOOKBACK = 256
HORIZON = 96
BATCH_SIZE = 32

# ── Protocol (plan/benchmark_protocol.md) ──────────────────────────────────────
HIDDEN_SIZE = 128
LR = 1e-4
WEIGHT_DECAY = 1e-5
CLIP = 10.0
EPOCHS = 10
SEEDS = [42, 123, 2024, 7, 99]
RANKS = (64, 64)                      # Gate-2 equalized q/o ranks for both cells

# ── Variants ───────────────────────────────────────────────────────────────────
VARIANT_CELLS = {"Normal": None, "Flat": (4, 4), "DRRA": (8, 4)}

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
SMOKE_TRAIN_BATCHES = 40
SMOKE_VAL_BATCHES = 10


def build_model(dataset_name, variant, seed):
    F = g3.DATASETS[dataset_name][3]
    torch.manual_seed(seed)           # determinism: seed before model init
    if variant == "Normal":
        return NormalTimeSeriesModel(num_features=F, hidden_size=HIDDEN_SIZE,
                                     lookback=LOOKBACK, horizon=HORIZON)
    ckv, c_r = VARIANT_CELLS[variant]
    return EPPTimeSeriesModel(F, ckv, c_r, q_lora_rank=RANKS[0], o_lora_rank=RANKS[1])


def count_attn_params(model):
    return sum(p.numel() for p in model.attn.parameters())


def count_full_params(model):
    return sum(p.numel() for p in model.parameters())


def make_loaders(dataset_name, seed, smoke):
    """Seed BEFORE data loading (shuffle order comes from torch RNG)."""
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
    """AdamW lr=1e-4 wd=1e-5, grad clip 10.0. Returns (train, val, test) MSE."""
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
        print(f"      epoch {epoch:2d}/{epochs}  train_mse={final_train:.6f}  "
              f"val_mse={final_val:.6f}")
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


def append_result(results_path, rec):
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def results_path(dataset_name):
    return os.path.join(RESULTS_DIR, f"{dataset_name}.jsonl")


def print_config(dataset_name, variant, seed, threads, smoke=False):
    F = g3.DATASETS[dataset_name][3]
    print(f"== Gate 3 harness (CPU PyTorch, threads={threads}, dataset={dataset_name}, "
          f"variant={variant}, seed={seed}, F={F}) ==")
    print(f"  task: frozen direct-96, L={LOOKBACK}, H={HORIZON}, batch={BATCH_SIZE}")
    print(f"  protocol: AdamW lr={LR} wd={WEIGHT_DECAY} clip={CLIP} epochs={EPOCHS} "
          f"(fixed), no scheduler/warm-up, fp32")
    wc = g3.window_counts(dataset_name)
    print(f"  windows: train={wc['train']} val={wc['val']} test={wc['test']} "
          f"(batches: {wc['train'] // BATCH_SIZE} / {wc['val'] // BATCH_SIZE} / "
          f"{wc['test'] // BATCH_SIZE})")


def run_dry_run(dataset_name, variant):
    print_config(dataset_name, variant, 42, 8)
    model = build_model(dataset_name, variant, seed=42)
    print(f"  params: attn={count_attn_params(model)} full={count_full_params(model)}")
    return 0


def run_smoke(dataset_name, variant, seed, threads):
    print_config(dataset_name, variant, seed, threads, smoke=True)
    t0 = time.time()
    train_loader, val_loader, _ = make_loaders(dataset_name, seed, smoke=True)
    print(f"[smoke] train batches={len(train_loader)} val batches={len(val_loader)}")
    model = build_model(dataset_name, variant, seed)
    print(f"  params: attn={count_attn_params(model)} full={count_full_params(model)}")
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
    print_config(dataset_name, variant, seed, threads)
    path = results_path(dataset_name)
    done = load_completed(path)
    if (variant, seed) in done:
        print(f"[full] ({variant}, seed={seed}) already completed — skipping (idempotent)")
        return 0
    train_loader, val_loader, test_loader = make_loaders(dataset_name, seed, smoke=False)
    print(f"[full] train batches={len(train_loader)} val batches={len(val_loader)} "
          f"test batches={len(test_loader)}")
    t0 = time.time()
    model = build_model(dataset_name, variant, seed)
    final_train, final_val, test_mse = train_and_eval(
        model, train_loader, val_loader, test_loader, epochs=EPOCHS)
    rec = {
        "dataset": dataset_name,
        "variant": variant,
        "cell": list(VARIANT_CELLS[variant]) if VARIANT_CELLS[variant] else None,
        "seed": seed,
        "val_mse": round(final_val, 8),
        "test_mse": round(test_mse, 8),
        "final_train_mse": round(final_train, 8),
        "attn_params": count_attn_params(model),
        "full_params": count_full_params(model),
        "n_train_batches": len(train_loader),
        "n_val_batches": len(val_loader),
        "n_test_batches": len(test_loader),
        "completed_utc": datetime.datetime.now(datetime.timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    append_result(path, rec)
    print(f"      FINAL test_mse={test_mse:.6f} train_mse={final_train:.6f} "
          f"(elapsed {time.time() - t0:.0f}s)")
    print(f"      appended: {json.dumps(rec)}")
    return 0


def main():
    p = argparse.ArgumentParser(description="Gate 3 dataset-coverage harness")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    p.add_argument("--dataset", required=True, choices=sorted(g3.DATASETS))
    p.add_argument("--variant", required=True, choices=sorted(VARIANT_CELLS))
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
