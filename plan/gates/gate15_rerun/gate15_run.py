#!/usr/bin/env python3
"""Gate 15 — option-(b) re-run driver: re-train ONLY misrouted cells, fixed mapping.

Design: plan/gates/gate15_rerun/gate15_design.md (pre-registered).
Reuses gate2/gate3 code paths by import (EPPTimeSeriesModel, train/evaluate,
loaders); results go to NEW files only (old manifests untouched).

Usage (from repo root, uv env):
  ~/.uv_env/py311/bin/python plan/gates/gate15_rerun/gate15_run.py --dry-run
  ~/.uv_env/py311/bin/python plan/gates/gate15_rerun/gate15_run.py --factorial   # 75 runs
  ~/.uv_env/py311/bin/python plan/gates/gate15_rerun/gate15_run.py --suite-flat  # 60 runs
"""
import argparse
import datetime
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
GATE2_DIR = os.path.join(REPO_ROOT, "plan", "gates", "gate2")
if GATE2_DIR not in sys.path:
    sys.path.insert(0, GATE2_DIR)
GATE3_DIR = os.path.join(REPO_ROOT, "plan", "gates", "gate3")
if GATE3_DIR not in sys.path:
    sys.path.insert(0, GATE3_DIR)

import torch
import torch.nn as nn  # noqa: F401

from plan.gates.gate2.gate2_factorial import (
    EPPTimeSeriesModel, train_and_eval, make_loaders as g2_loaders,
    evaluate as g2_evaluate, count_attn_params, count_full_params,
    EPOCHS, LR, WEIGHT_DECAY, CLIP, NUM_FEATURES,
)
import gate3_datasets as g3
from dataset import ETTForecastDataset
from torch.utils.data import DataLoader

PROVENANCE = "gate15/uv-torch2.6.0/fixed-mapping"
RESULTS_DIR = os.path.join(HERE, "results")
FACT_PATH = os.path.join(RESULTS_DIR, "factorial.jsonl")
SUITE_DIR = os.path.join(RESULTS_DIR, "suite_flat")

FACTORIAL_CELLS = [(4, 4), (4, 8), (8, 8)]  # broken cells only; (8,4)+Normal kept
FACTORIAL_SEEDS = [42, 123, 2024, 7, 99, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12,
                   13, 14, 15, 16, 17, 18, 19, 20, 21]
SUITE_SEEDS = [42, 123, 2024, 7, 99]
SUITE_DATASETS = sorted(g3.DATASETS)


def load_completed(path, key):
    done = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    done.add(key(rec))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    return done


def append(path, rec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def dry_run():
    print("== Gate15 dry-run: param counts must match published (mapping adds 0 params) ==")
    expect = {(4, 4): 95396, (4, 8): 95652, (8, 8): 95908}
    ok = True
    for cell in FACTORIAL_CELLS:
        torch.manual_seed(42)
        m = EPPTimeSeriesModel(NUM_FEATURES, cell[0], cell[1],
                               q_lora_rank=64, o_lora_rank=64)
        ap, fp = count_attn_params(m), count_full_params(m)
        match = ap == expect[cell]
        ok &= match
        print(f"  {cell}: attn={ap} full={fp} expected_attn={expect[cell]} "
              f"{'OK' if match else 'MISMATCH'}")
    # mapping regression gate
    import subprocess
    r = subprocess.run([sys.executable, "-m", "pytest", "--version"],
                       capture_output=True)
    print("  (mapping regression: test_expert_plus_plus.py §5 — run separately)")
    if not ok:
        raise SystemExit("dry-run FAILED: param counts changed")
    print("dry-run OK")
    return 0


def run_factorial(threads):
    torch.set_num_threads(threads)
    done = load_completed(FACT_PATH, lambda r: (tuple(r["cell"]), int(r["seed"])))
    plan = [(c, s) for c in FACTORIAL_CELLS for s in FACTORIAL_SEEDS
            if (c, s) not in done]
    print(f"=== Gate15 factorial: {len(plan)} pending (3 cells x 25 seeds) ===", flush=True)
    for i, ((ckv, c_r), seed) in enumerate(plan, 1):
        print(f"--- [{i}/{len(plan)}] ({ckv},{c_r}) seed={seed} START "
              f"{datetime.datetime.now(datetime.timezone.utc).strftime('%FT%TZ')} ---",
              flush=True)
        t0 = time.time()
        train_loader, val_loader, test_loader = g2_loaders(seed, smoke=False)
        torch.manual_seed(seed)
        model = EPPTimeSeriesModel(NUM_FEATURES, ckv, c_r,
                                   q_lora_rank=64, o_lora_rank=64)
        final_train, final_val, test_mse = train_and_eval(
            model, train_loader, val_loader, test_loader, epochs=EPOCHS)
        rec = {"cell": [ckv, c_r], "seed": seed,
               "val_mse": round(final_val, 8), "test_mse": round(test_mse, 8),
               "final_train_mse": round(final_train, 8),
               "attn_params": count_attn_params(model),
               "full_params": count_full_params(model),
               "c_kv": ckv, "c_r": c_r, "provenance": PROVENANCE,
               "completed_utc": datetime.datetime.now(datetime.timezone.utc)
                                .strftime("%Y-%m-%dT%H:%M:%SZ"),
               "elapsed_s": round(time.time() - t0, 1)}
        append(FACT_PATH, rec)
        print(f"      FINAL val={final_val:.6f} test={test_mse:.6f} "
              f"({rec['elapsed_s']}s)", flush=True)
    print("=== Gate15 factorial complete ===", flush=True)
    return 0


def suite_loaders(dataset_name, seed):
    torch.manual_seed(seed)
    tr, va, te, _ = g3.preprocess(dataset_name)
    mk = lambda d: ETTForecastDataset(d, lookback=256, horizon=96)
    return (DataLoader(mk(tr), batch_size=32, shuffle=True),
            DataLoader(mk(va), batch_size=32, shuffle=False),
            DataLoader(mk(te), batch_size=32, shuffle=False))


def run_suite_flat(threads):
    torch.set_num_threads(threads)
    total_plan = []
    for ds in SUITE_DATASETS:
        path = os.path.join(SUITE_DIR, f"{ds}.jsonl")
        done = load_completed(path, lambda r: int(r["seed"]))
        for s in SUITE_SEEDS:
            if s not in done:
                total_plan.append((ds, s))
    print(f"=== Gate15 suite-flat: {len(total_plan)} pending (12 ds x 5 seeds) ===",
          flush=True)
    for i, (ds, seed) in enumerate(total_plan, 1):
        F = g3.DATASETS[ds][3]
        print(f"--- [{i}/{len(total_plan)}] {ds} Flat seed={seed} START "
              f"{datetime.datetime.now(datetime.timezone.utc).strftime('%FT%TZ')} ---",
              flush=True)
        t0 = time.time()
        train_loader, val_loader, test_loader = suite_loaders(ds, seed)
        torch.manual_seed(seed)
        model = EPPTimeSeriesModel(F, 4, 4, q_lora_rank=64, o_lora_rank=64)
        final_train, final_val, test_mse = train_and_eval(
            model, train_loader, val_loader, test_loader, epochs=EPOCHS)
        rec = {"dataset": ds, "variant": "Flat-fix", "cell": [4, 4], "seed": seed,
               "val_mse": round(final_val, 8), "test_mse": round(test_mse, 8),
               "final_train_mse": round(final_train, 8),
               "attn_params": count_attn_params(model),
               "full_params": count_full_params(model),
               "provenance": PROVENANCE,
               "completed_utc": datetime.datetime.now(datetime.timezone.utc)
                                .strftime("%Y-%m-%dT%H:%M:%SZ"),
               "elapsed_s": round(time.time() - t0, 1)}
        append(os.path.join(SUITE_DIR, f"{ds}.jsonl"), rec)
        print(f"      FINAL val={final_val:.6f} test={test_mse:.6f} "
              f"({rec['elapsed_s']}s)", flush=True)
    print("=== Gate15 suite-flat complete ===", flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description="Gate 15 option-(b) re-run driver")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--factorial", action="store_true")
    mode.add_argument("--suite-flat", action="store_true")
    p.add_argument("--threads", type=int, default=8)
    args = p.parse_args()
    if args.dry_run:
        return dry_run()
    if args.factorial:
        return run_factorial(args.threads)
    return run_suite_flat(args.threads)


if __name__ == "__main__":
    sys.exit(main())
