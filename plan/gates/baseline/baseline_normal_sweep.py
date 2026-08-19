#!/usr/bin/env python3
"""Normal (full causal attention) baseline sweep under the frozen direct-96 task.

Companion to plan/gates/gate2/gate2_factorial.py: produces the Normal leg of the 3-way
comparison (Normal vs CSA/Flat vs DRRA). CSA/Flat cells (4,4)/(8,4) and DRRA
(8,4) rows already live in plan/gates/gate2/gate2_results.jsonl; this harness appends the
Normal rows to plan/gates/baseline/baseline_normal_results.jsonl with the SAME 10-key schema.

Frozen task: plan/gates/gate1/gate1_task.md (direct-96, L=256, H=96, 7 features, train-only
z-score, pooled [B,96,7] MSE, strictly causal attention). Repo: CPU PyTorch, no
git. NEW FILE ONLY — no existing repo file is modified; model.py /
normal_attention.py are used verbatim.

Protocol (plan/benchmark_protocol.md, IDENTICAL to gate2_factorial.py):
  AdamW lr=1e-4 wd=1e-5, grad clip 10.0, batch 32, 10 epochs FIXED, no
  scheduler, no warm-up, PyTorch default init, no mixed precision,
  torch.set_num_threads(8). Seeded BEFORE model init AND BEFORE data load
  (paired-design: same 5 seeds as Gate-2: 42, 123, 2024, 7, 99).

Model: model.NormalTimeSeriesModel — full quadratic causal attention
(NormalAttention, normal_attention.py:13), same encoder stack + frozen horizon
head (Linear(128->672) on the last hidden state -> [B,96,7]) as all variants.
Params verified against plan/gates/gate0/gate0_registry.json ("Normal"): attn=102,496,
full=355,200.

CLI modes:
  --dry-run : print config + verified param counts. No training.
  --smoke   : 1 epoch on bounded subsets (first 40*32 train windows,
              10*32 val); prints train/val MSE; saves nothing.
  --full --seed N : 10 epochs, full train split (shuffle=True), val each epoch,
              final test eval; APPENDS one JSON line to
              plan/gates/baseline/baseline_normal_results.jsonl. Idempotent: a completed
              ("Normal", seed) line is skipped on rerun.

Exit codes: 0 on success; non-zero (with traceback/message) on failure.
"""
import argparse
import datetime
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset

from model import NormalTimeSeriesModel
from dataset import download_and_preprocess_etth1, ETTForecastDataset

# ── Frozen task constants (plan/gates/gate1/gate1_task.md) ───────────────────────────────
NUM_FEATURES = 7
LOOKBACK = 256
HORIZON = 96
BATCH_SIZE = 32

# ── Aux contract (IDENTICAL to gate2_factorial.py) ───────────────────────────
HIDDEN_SIZE = 128
NUM_HEADS = 4
HEAD_DIM = 32
LR = 1e-4
WEIGHT_DECAY = 1e-5
CLIP = 10.0
EPOCHS = 10

# ── Paired seeds (same as Gate-2 cells in plan/gates/gate2/gate2_results.jsonl) ─────────
SEEDS = [42, 123, 2024, 7, 99]

# ── Verified param counts (plan/gates/gate0/gate0_registry.json, "Normal") ───────────────
NORMAL_ATTN_PARAMS = 102496
NORMAL_FULL_PARAMS = 355200

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "baseline_normal_results.jsonl")

SMOKE_TRAIN_BATCHES = 40
SMOKE_VAL_BATCHES = 10


# ── 1) Model builder (model.py verbatim — zero duplication) ─────────────────
def build_model(seed):
    torch.manual_seed(seed)          # determinism: seed before model init
    return NormalTimeSeriesModel(num_features=NUM_FEATURES,
                                 hidden_size=HIDDEN_SIZE,
                                 lookback=LOOKBACK,
                                 horizon=HORIZON)


def count_attn_params(model):
    return sum(p.numel() for p in model.attn.parameters())


def count_full_params(model):
    return sum(p.numel() for p in model.parameters())


# ── 2) Data (reused from dataset.py — zero duplication) ─────────────────────
def load_datasets():
    train_raw, val_raw, test_raw, _stats = download_and_preprocess_etth1(return_stats=True)
    return (ETTForecastDataset(train_raw),
            ETTForecastDataset(val_raw),
            ETTForecastDataset(test_raw))


def make_loaders(seed, smoke):
    """Seed BEFORE data loading (shuffle order comes from torch RNG)."""
    torch.manual_seed(seed)
    train_ds, val_ds, test_ds = load_datasets()
    if smoke:
        train_ds = Subset(train_ds, range(SMOKE_TRAIN_BATCHES * BATCH_SIZE))
        val_ds = Subset(val_ds, range(SMOKE_VAL_BATCHES * BATCH_SIZE))
        return (
            DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True),
            DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False),
            None,
        )
    return (
        DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True),
        DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False),
        DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False),
    )


# ── 3) Training / evaluation (identical loop to gate2_factorial.py) ─────────
@torch.no_grad()
def evaluate(model, loader):
    model.eval()
    total, n = 0.0, 0
    for x, y in loader:
        out = model(x)
        assert out.shape == (x.shape[0], HORIZON, NUM_FEATURES), \
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
            assert out.shape == (x.shape[0], HORIZON, NUM_FEATURES), \
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


# ── 4) Reporting / results persistence ───────────────────────────────────────
def print_config(threads, seed, smoke=False):
    print(f"== Normal baseline sweep (CPU PyTorch, threads={threads}, seed={seed}) ==")
    print(f"  model: NormalTimeSeriesModel (full causal attention, NormalAttention)")
    print(f"  task: frozen direct-96, L={LOOKBACK}, H={HORIZON}, F={NUM_FEATURES}, "
          f"batch={BATCH_SIZE}")
    print(f"  aux: hidden={HIDDEN_SIZE} heads={NUM_HEADS} head_dim={HEAD_DIM}")
    print(f"  protocol: AdamW lr={LR} wd={WEIGHT_DECAY} clip={CLIP} "
          f"epochs={EPOCHS} (fixed), no scheduler, no warm-up, fp32")
    if smoke:
        print(f"  [smoke] 1 epoch, train={SMOKE_TRAIN_BATCHES}x{BATCH_SIZE} windows, "
              f"val={SMOKE_VAL_BATCHES}x{BATCH_SIZE} windows — saves nothing")
    else:
        print(f"  seeds: {SEEDS} (paired with Gate-2); run one per --full --seed N")


def print_param_check():
    torch.manual_seed(42)
    model = NormalTimeSeriesModel(num_features=NUM_FEATURES,
                                  hidden_size=HIDDEN_SIZE,
                                  lookback=LOOKBACK,
                                  horizon=HORIZON)
    attn_p = count_attn_params(model)
    full_p = count_full_params(model)
    status = "OK" if (attn_p, full_p) == (NORMAL_ATTN_PARAMS, NORMAL_FULL_PARAMS) \
        else "MISMATCH"
    print(f"  param check [{status}]: attn={attn_p} full={full_p} "
          f"(registry: attn={NORMAL_ATTN_PARAMS} full={NORMAL_FULL_PARAMS})")
    if status == "MISMATCH":
        raise RuntimeError(
            f"Normal param counts drifted from registry: got attn={attn_p} "
            f"full={full_p}, registry has attn={NORMAL_ATTN_PARAMS} "
            f"full={NORMAL_FULL_PARAMS}")
    return attn_p, full_p


def load_completed(results_path):
    done = set()
    if os.path.exists(results_path):
        with open(results_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("cell") == "Normal":
                        done.add(int(rec["seed"]))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    return done


def append_result(results_path, rec):
    with open(results_path, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ── 5) Modes ─────────────────────────────────────────────────────────────────
def run_dry_run():
    print("  [dry-run] config only — no training, nothing saved")
    print_param_check()
    return 0


def run_smoke(seed):
    train_loader, val_loader, _ = make_loaders(seed, smoke=True)
    print(f"[smoke] train batches={len(train_loader)} val batches={len(val_loader)}")
    torch.manual_seed(seed)
    model = build_model(seed)
    print(f"  params: attn={count_attn_params(model)} full={count_full_params(model)}")
    train_mse, val_mse, _ = train_and_eval(model, train_loader, val_loader,
                                           None, epochs=1)
    print(f"      smoke train_mse={train_mse:.6f} val_mse={val_mse:.6f}")
    print("[smoke] done — nothing saved")
    return 0


def run_full(seed):
    done = load_completed(RESULTS_PATH)
    if seed in done:
        print(f"[full] seed={seed} already completed (skipping, idempotent) — "
              f"cell 'Normal' present in {RESULTS_PATH}")
        return 0
    print(f"\n[full] cell=Normal seed={seed}, {EPOCHS} epochs, full train split "
          f"(shuffle=True), val each epoch, final test eval. Results -> {RESULTS_PATH}")
    train_loader, val_loader, test_loader = make_loaders(seed, smoke=False)
    print(f"[full] train batches={len(train_loader)} val batches={len(val_loader)} "
          f"test batches={len(test_loader)}")
    cell_start = time.time()
    print("  cell Normal:")
    model = build_model(seed)          # seed already set inside build_model
    final_train, final_val, test_mse = train_and_eval(
        model, train_loader, val_loader, test_loader, epochs=EPOCHS)
    attn_p = count_attn_params(model)
    full_p = count_full_params(model)
    rec = {
        "cell": "Normal",
        "seed": seed,
        "val_mse": round(final_val, 8),
        "test_mse": round(test_mse, 8),
        "final_train_mse": round(final_train, 8),
        "attn_params": attn_p,
        "full_params": full_p,
        "c_kv": None,
        "c_r": None,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    append_result(RESULTS_PATH, rec)
    print(f"      FINAL test_mse={test_mse:.6f} train_mse={final_train:.6f} "
          f"attn_params={attn_p} full_params={full_p} "
          f"(elapsed {time.time() - cell_start:.0f}s)")
    print(f"      appended: {json.dumps(rec)}")
    return 0


# ── 6) CLI ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Normal (full causal attention) baseline sweep — frozen "
                    "direct-96 task, paired with Gate-2 seeds.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="print config + verified param counts; no training")
    mode.add_argument("--smoke", action="store_true",
                      help="1 epoch on bounded subsets; saves nothing")
    mode.add_argument("--full", action="store_true",
                      help="full 10-epoch training, val each epoch, final test; "
                           "appends to plan/gates/baseline/baseline_normal_results.jsonl "
                           "(idempotent per seed)")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed for model init + data loading (default 42)")
    parser.add_argument("--threads", type=int, default=8,
                        help="torch.set_num_threads (default 8)")
    args = parser.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)          # seed before ANY model init / data loading

    print_config(args.threads, args.seed, smoke=args.smoke)

    if args.full:
        return run_full(args.seed)
    if args.smoke:
        return run_smoke(args.seed)
    return run_dry_run()


if __name__ == "__main__":
    sys.exit(main())
