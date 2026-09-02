#!/usr/bin/env python3
"""Gate 7 — seed-power extension of the Gate-2 factorial (paper major-gap #2).

Goal: raise the factorial from 5 to 20 paired seeds so the decoupled-rate
claim can be tested rather than only described. The original five seeds
{42, 123, 2024, 7, 99} already exist in gate2/gate3 manifests and are NOT
re-run; this gate adds seeds 5..24 minus those five (20 new seeds), giving
25 paired seeds per cell when combined.

Everything else is byte-identical to the frozen protocol (gate2_factorial.py
via gate3_harness.py): ETTh1 direct-96, L=256, H=96, batch 32, AdamW
lr=1e-4 wd=1e-5, clip 10, 10 epochs fixed, fp32 CPU, 8 threads;
torch.manual_seed(seed) before data load AND model init.

Results append to plan/gates/gate7_seeds/results/gate7.jsonl, one JSON line
per (cell, seed), with the same fields as gate2/gate3 records plus
"gate": "gate7".

CLI:
  --dry-run : print plan + param counts, run nothing
  --smoke   : 1 epoch, bounded subsets, nothing saved
  --full    : run all pending (cell, seed) pairs (idempotent)

Planned analysis (gate7_stats.py, after completion): paired Wilcoxon on
n=25 (two-sided floor p = 2/2^25), main-effects regression with seed
covariates, Holm correction across the 4 pre-registered cell contrasts.
"""
import argparse
import datetime
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
GATE3_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gate3")
if GATE3_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(GATE3_DIR))

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset

from dataset import ETTForecastDataset
import gate3_datasets as g3
import gate3_harness as h3
from plan.gates.gate2.gate2_factorial import EPPTimeSeriesModel

# Frozen protocol constants (mirror gate3_harness exactly)
LOOKBACK, HORIZON, BATCH_SIZE = 256, 96, 32
LR, WEIGHT_DECAY, CLIP, EPOCHS = 1e-4, 1e-5, 10.0, 10
EXISTING_SEEDS = [42, 123, 2024, 7, 99]
# exactly 20 new seeds (total 25 paired seeds when merged with the Gate-2 five)
NEW_SEEDS = [s for s in range(1, 100) if s not in EXISTING_SEEDS][:20]
CELLS = {"CSA(4,4)": (4, 4), "DRRA(8,4)": (8, 4), "(4,8)": (4, 8), "(8,8)": (8, 8),
         "Normal": None}
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
RESULTS_PATH = os.path.join(RESULTS_DIR, "gate7.jsonl")
SMOKE_TRAIN_BATCHES, SMOKE_VAL_BATCHES = 40, 10


def build_model(cell, seed):
    torch.manual_seed(seed)
    if cell is None:
        from model import NormalTimeSeriesModel
        return NormalTimeSeriesModel(num_features=7, hidden_size=128,
                                     lookback=LOOKBACK, horizon=HORIZON)
    ckv, c_r = cell
    return EPPTimeSeriesModel(7, ckv, c_r, q_lora_rank=64, o_lora_rank=64)


def make_loaders(seed, smoke=False):
    torch.manual_seed(seed)
    tr, va, te, _ = g3.preprocess("etth1")
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


def load_completed():
    done = set()
    if os.path.exists(RESULTS_PATH):
        for line in open(RESULTS_PATH):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                done.add((rec["cell_name"], int(rec["seed"])))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return done


@torch.no_grad()
def evaluate(model, loader):
    model.eval()
    total, n = 0.0, 0
    for x, y in loader:
        out = model(x)
        total += F.mse_loss(out, y).item() * x.shape[0]
        n += x.shape[0]
    return total / n


def run_one(cell_name, cell, seed, threads=8):
    torch.set_num_threads(threads)
    torch.manual_seed(seed)
    model = build_model(cell, seed)
    train_loader, val_loader, test_loader = make_loaders(seed)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    t0 = time.time()
    final_train = final_val = None
    for epoch in range(1, EPOCHS + 1):
        model.train()
        total, n = 0.0, 0
        for x, y in train_loader:
            optimizer.zero_grad()
            loss = F.mse_loss(model(x), y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            optimizer.step()
            total += loss.item() * x.shape[0]
            n += x.shape[0]
        final_train, final_val = total / n, evaluate(model, val_loader)
        print(f"      epoch {epoch:2d}/{EPOCHS}  train={final_train:.6f}  "
              f"val={final_val:.6f}", flush=True)
    test_mse = evaluate(model, test_loader)
    rec = {
        "gate": "gate7", "dataset": "etth1", "cell_name": cell_name,
        "cell": list(cell) if cell else None, "seed": seed,
        "val_mse": round(final_val, 8), "test_mse": round(test_mse, 8),
        "final_train_mse": round(final_train, 8),
        "attn_params": sum(p.numel() for p in model.attn.parameters()),
        "full_params": sum(p.numel() for p in model.parameters()),
        "completed_utc": datetime.datetime.now(datetime.timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_s": round(time.time() - t0, 1),
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"      FINAL val={final_val:.6f} test={test_mse:.6f} "
          f"({rec['elapsed_s']}s)", flush=True)


def main():
    p = argparse.ArgumentParser(description="Gate 7 seed-power extension")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    p.add_argument("--threads", type=int, default=8)
    args = p.parse_args()

    if args.dry_run:
        print(f"new seeds: {NEW_SEEDS} (n={len(NEW_SEEDS)})")
        print(f"cells: {list(CELLS)}")
        print(f"pending runs: {len(NEW_SEEDS) * len(CELLS)}")
        for name, cell in CELLS.items():
            m = build_model(cell, 5)
            print(f"  {name}: attn={sum(p.numel() for p in m.attn.parameters())} "
                  f"full={sum(p.numel() for p in m.parameters())}")
        return 0
    if args.smoke:
        torch.set_num_threads(8)
        model = build_model((4, 4), 5)
        tr, va, _ = make_loaders(5, smoke=True)[:2] + (None,)
        opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
        for x, y in tr:
            opt.zero_grad(); loss = F.mse_loss(model(x), y)
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), CLIP); opt.step()
        print(f"[smoke] train={loss.item():.6f} val={evaluate(model, va):.6f} — nothing saved")
        return 0

    done = load_completed()
    plan = [(n, c, s) for n, c in CELLS.items() for s in NEW_SEEDS
            if (n, s) not in done]
    print(f"=== Gate 7 seed extension: {len(plan)} pending runs "
          f"(cells x seeds {len(CELLS)}x{len(NEW_SEEDS)}, done {len(done)}) ===",
          flush=True)
    for i, (name, cell, seed) in enumerate(plan, 1):
        print(f"--- [{i}/{len(plan)}] {name} seed={seed} START "
              f"{datetime.datetime.now(datetime.timezone.utc).strftime('%FT%TZ')} ---",
              flush=True)
        run_one(name, cell, seed, threads=args.threads)
    print("=== Gate 7 complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
