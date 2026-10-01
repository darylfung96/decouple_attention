#!/usr/bin/env python3
"""Gate 19 — exploratory (32,4) probe driver. Design: gate19_design.md."""
import argparse, datetime, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for p in [REPO_ROOT, os.path.join(REPO_ROOT, "plan", "gates", "gate2")]:
    if p not in sys.path:
        sys.path.insert(0, p)
import torch
from plan.gates.gate2.gate2_factorial import (
    EPPTimeSeriesModel, train_and_eval, make_loaders,
    count_attn_params, count_full_params, EPOCHS, NUM_FEATURES)
RESULTS = os.path.join(HERE, "results", "etth1.jsonl")
SEEDS = [42, 123, 2024, 7, 99, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
def load_completed():
    done = set()
    if os.path.exists(RESULTS):
        for line in open(RESULTS):
            line = line.strip()
            if not line:
                continue
            try:
                done.add(int(json.loads(line)["seed"]))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return done
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--threads", type=int, default=8)
    args = p.parse_args()
    torch.set_num_threads(args.threads)
    plan = [s for s in SEEDS if s not in load_completed()]
    print(f"=== Gate19: {len(plan)} pending ((32,4) x 25 seeds) ===", flush=True)
    for i, seed in enumerate(plan, 1):
        print(f"--- [{i}/{len(plan)}] (32,4) seed={seed} START "
              f"{datetime.datetime.now(datetime.timezone.utc).strftime('%FT%TZ')} ---", flush=True)
        t0 = time.time()
        tr, va, te = make_loaders(seed, smoke=False)
        torch.manual_seed(seed)
        model = EPPTimeSeriesModel(NUM_FEATURES, 32, 4, q_lora_rank=64, o_lora_rank=64)
        ft, fv, te_mse = train_and_eval(model, tr, va, te, epochs=EPOCHS)
        rec = {"cell": [16, 4], "seed": seed, "val_mse": round(fv, 8),
               "test_mse": round(te_mse, 8), "final_train_mse": round(ft, 8),
               "attn_params": count_attn_params(model),
               "full_params": count_full_params(model),
               "provenance": "gate19/uv-torch2.6.0/exploratory",
               "completed_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "elapsed_s": round(time.time() - t0, 1)}
        os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
        with open(RESULTS, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"      FINAL val={fv:.6f} test={te_mse:.6f} ({rec['elapsed_s']}s)", flush=True)
    print("=== Gate19 complete ===", flush=True)
    return 0
if __name__ == "__main__":
    sys.exit(main())
