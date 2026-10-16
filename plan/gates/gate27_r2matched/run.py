#!/usr/bin/env python3
"""Gate 27 — R2 projection-matched dense baseline (Normal_r64).

Design (frozen pre-run): plan/gates/gate27_r2matched/design.md.
One variable vs the as-run Normal: attn o_lora_rank 128 -> 64 (the compressed
cells' rank). Protocol imported from the same harness the v2 matrix cells used
(gate2 loaders + gate3_harness.train_and_eval), so per-seed pairing holds.

Usage (from repo root, uv env):
  ~/.uv_env/py311/bin/python plan/gates/gate27_r2matched/run.py --dry-run
  ~/.uv_env/py311/bin/python plan/gates/gate27_r2matched/run.py --smoke
  ~/.uv_env/py311/bin/python plan/gates/gate27_r2matched/run.py --full

Writes ONLY to plan/gates/gate27_r2matched/results/normal_r64.jsonl (append-only,
idempotent). No historical file is touched.
"""
import argparse
import datetime
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for p in (REPO_ROOT,
          os.path.join(REPO_ROOT, "plan", "gates", "gate2"),
          os.path.join(REPO_ROOT, "plan", "gates", "gate3")):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch

from model import CSATimeSeriesModel, NormalTimeSeriesModel
from normal_attention import NormalAttention
from plan.gates.gate2.gate2_factorial import (
    make_loaders as g2_loaders, EPOCHS, NUM_FEATURES, build_all_cells,
)
from gate3_harness import train_and_eval

PROVENANCE = "gate27/uv-torch2.6.0/r2-projection-matched"
RESULTS_PATH = os.path.join(HERE, "results", "normal_r64.jsonl")

SEEDS = [42, 123, 2024, 7, 99, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12,
         13, 14, 15, 16, 17, 18, 19, 20, 21]

# Frozen expected counts (design.md; as-run values cross-checked against
# plan/gates/gate0/gate0_registry.json).
NORMAL_ATTN, NORMAL_FULL = 102496, 355200
MATCHED_ATTN, MATCHED_FULL = 61536, 314240
DELTA = NORMAL_FULL - MATCHED_FULL          # 40,960, all in the O path

SMOKE_TRAIN_BATCHES = 40
SMOKE_VAL_BATCHES = 10


class NormalR64TimeSeriesModel(CSATimeSeriesModel):
    """As-run Normal (model.NormalTimeSeriesModel) with o_lora_rank=64 only.

    Everything else is copied verbatim from model.py:88-98 so the single
    changed variable is the output-projection rank.
    """

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
            o_lora_rank=64,        # <- the one variable (as-run Normal: 128)
        )


def count_params(module):
    return sum(p.numel() for p in module.parameters())


def dry_run():
    print("== Gate27 dry-run: matched baseline parameter check ==")
    torch.manual_seed(0)
    ref = NormalTimeSeriesModel(NUM_FEATURES)
    torch.manual_seed(0)
    matched = NormalR64TimeSeriesModel(NUM_FEATURES)

    ref_attn, ref_full = count_params(ref.attn), count_params(ref)
    m_attn, m_full = count_params(matched.attn), count_params(matched)
    print(f"  as-run Normal : attn={ref_attn} full={ref_full}")
    print(f"  Normal_r64    : attn={m_attn} full={m_full}")
    print(f"  delta         : attn={ref_attn - m_attn} full={ref_full - m_full}")

    ok = (ref_attn, ref_full) == (NORMAL_ATTN, NORMAL_FULL)
    ok &= (m_attn, m_full) == (MATCHED_ATTN, MATCHED_FULL)

    # The delta must sit entirely in the O projection.
    for name in ("q_a_proj", "q_b_proj", "o_a_proj", "o_b_proj"):
        a, b = count_params(getattr(ref.attn, name)), count_params(getattr(matched.attn, name))
        print(f"  {name:9s}: r128 {a:6d} vs r64 {b:6d}  (delta {a - b})")
        if name.startswith("o_"):
            continue
        ok &= a == b
    o_delta = (count_params(ref.attn.o_a_proj) - count_params(matched.attn.o_a_proj)
               + count_params(ref.attn.o_b_proj) - count_params(matched.attn.o_b_proj))
    ok &= o_delta == DELTA

    # Everything outside attn must be byte-identical in size.
    non_attn_ref = ref_full - ref_attn
    non_attn_m = m_full - m_attn
    print(f"  outside attention: r128 {non_attn_ref} vs r64 {non_attn_m}")
    ok &= non_attn_ref == non_attn_m

    # Equalization contract: the compressed cells' o rank is 64 (same as matched).
    _ta, _tf, configs = build_all_cells()
    ranks = {cell: cfg["o_lora_rank"] for cell, cfg in configs.items()}
    print(f"  compressed-cell o_lora_rank: {ranks}")
    ok &= all(r == 64 for r in ranks.values())

    if not ok:
        raise SystemExit("dry-run FAILED: parameter counts deviate from the frozen expectation")
    print("dry-run OK — single variable is the output-projection rank")
    return 0


def smoke(threads):
    torch.set_num_threads(threads)
    print("== Gate27 smoke: 1 epoch, bounded subsets, saves nothing ==")
    seed = 42
    train_loader, val_loader, _ = g2_loaders(seed, smoke=True)
    print(f"  train batches={len(train_loader)} val batches={len(val_loader)}")
    for name, cls in (("Normal (r128)", NormalTimeSeriesModel),
                      ("Normal_r64", NormalR64TimeSeriesModel)):
        torch.manual_seed(seed)
        model = cls(NUM_FEATURES)
        t0 = time.time()
        train_mse, val_mse, _ = train_and_eval(model, train_loader, val_loader,
                                               None, epochs=1)
        print(f"  [{name}] train_mse={train_mse:.6f} val_mse={val_mse:.6f} "
              f"({time.time() - t0:.0f}s)")
    print("[smoke] done — nothing saved")
    return 0


def load_completed():
    done = set()
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    done.add(int(json.loads(line)["seed"]))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    return done


def append(rec):
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


def run_full(threads):
    torch.set_num_threads(threads)
    done = load_completed()
    plan = [s for s in SEEDS if s not in done]
    print(f"=== Gate27 Normal_r64: {len(plan)} pending of {len(SEEDS)} seeds "
          f"(already done: {sorted(done)}) ===", flush=True)
    for i, seed in enumerate(plan, 1):
        print(f"--- [{i}/{len(plan)}] seed={seed} START "
              f"{datetime.datetime.now(datetime.timezone.utc).strftime('%FT%TZ')} ---",
              flush=True)
        t0 = time.time()
        train_loader, val_loader, test_loader = g2_loaders(seed, smoke=False)
        torch.manual_seed(seed)          # seed before model init (gate15 order)
        model = NormalR64TimeSeriesModel(NUM_FEATURES)
        final_train, final_val, test_mse = train_and_eval(
            model, train_loader, val_loader, test_loader, epochs=EPOCHS)
        rec = {
            "cell_name": "Normal_r64",
            "seed": seed,
            "val_mse": round(final_val, 8),
            "test_mse": round(test_mse, 8),
            "final_train_mse": round(final_train, 8),
            "attn_params": count_params(model.attn),
            "full_params": count_params(model),
            "o_lora_rank": 64,
            "provenance": PROVENANCE,
            "completed_utc": datetime.datetime.now(datetime.timezone.utc)
                             .strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        append(rec)
        print(f"      FINAL val_mse={final_val:.6f} test_mse={test_mse:.6f} "
              f"train_mse={final_train:.6f} (elapsed {time.time() - t0:.0f}s)")
        print(f"      appended: {json.dumps(rec)}", flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Gate 27 — R2 projection-matched dense baseline")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="parameter check only")
    mode.add_argument("--smoke", action="store_true", help="1 epoch on bounded subsets; saves nothing")
    mode.add_argument("--full", action="store_true", help="25 seeds, 10 epochs; appends to results/normal_r64.jsonl")
    parser.add_argument("--threads", type=int, default=8, help="torch.set_num_threads (default 8)")
    args = parser.parse_args()

    if args.full:
        return run_full(args.threads)
    if args.smoke:
        return smoke(args.threads)
    return dry_run()


if __name__ == "__main__":
    sys.exit(main())
