#!/usr/bin/env python3
"""Gate 3 companion — batch-size scaling of forward-pass latency (frozen protocol).

Measures forward latency for Normal / Flat=(4,4) / DRRA=(8,4) at batch sizes
{1, 8, 16, 32, 64, 100, 128, 256} under the frozen task shapes (L=256, H=96,
F=7, fp32, 8 threads) on the development machine, with the alternating
head-to-head protocol per batch size (15 rounds; within each round the three
models are timed in rotation; 15 timed passes per model per round after 5
warm-up passes). Reports mean (primary), p90/p99 (ms per batch), ms per
sequence (mean/B), 95% percentile bootstrap CI on the mean, and throughput.

Output: plan/gates/gate3/gate3_latency_scale.json + printed table.
Exit 0 on success. New measurements only — no pre-freeze figures.
"""
import argparse
import json
import os
import statistics as st
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import torch  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate3_harness import build_model, VARIANT_CELLS  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "gate3_latency_scale.json")

LOOKBACK = 256
HORIZON = 96
FEATURES = 7
THREADS = 8
ROUNDS = 15
PASSES = 15
WARMUP = 5
BOOTSTRAP_N = 10000
SEED = 42
INPUT_SEED = 0
BATCHES = [1, 8, 16, 32, 64, 100, 128, 256]


def percentile(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def bootstrap_ci(round_medians, n=BOOTSTRAP_N, alpha=0.05, stat=st.mean):
    import random
    rng = random.Random(1234)
    est = stat(round_medians)
    if not round_medians:
        return est, est
    resampled = sorted(stat(rng.choices(round_medians, k=len(round_medians)))
                       for _ in range(n))
    return resampled[int(n * alpha / 2)], resampled[int(n * (1 - alpha / 2)) - 1]


def main():
    p = argparse.ArgumentParser(description="Gate 3 batch-scaling latency benchmark")
    p.add_argument("--rounds", type=int, default=ROUNDS)
    p.add_argument("--passes", type=int, default=PASSES)
    p.add_argument("--warmup", type=int, default=WARMUP)
    p.add_argument("--threads", type=int, default=THREADS)
    p.add_argument("--out", default=OUT_PATH)
    p.add_argument("--batch", type=int, nargs="*", default=None,
                   help="batch sizes to sweep (default: %(default)s all)")
    args = p.parse_args()
    batches = args.batch or BATCHES

    torch.set_num_threads(args.threads)

    models = {}
    for variant in sorted(VARIANT_CELLS):
        torch.manual_seed(SEED)
        m = build_model("etth1", variant, seed=SEED)
        m.eval()
        models[variant] = m

    result = {"task": {"L": LOOKBACK, "H": HORIZON, "F": FEATURES,
                       "threads": args.threads},
              "machine": {"torch": torch.__version__}, "batches": {}}

    for B in batches:
        torch.manual_seed(INPUT_SEED)
        x = torch.randn(B, LOOKBACK, FEATURES)
        for variant, m in models.items():
            with torch.no_grad():
                for _ in range(args.warmup):
                    m(x)
        per_model = {v: [] for v in models}
        for r in range(1, args.rounds + 1):
            for variant, m in models.items():
                times = []
                with torch.no_grad():
                    for _ in range(args.passes):
                        t0 = time.perf_counter()
                        m(x)
                        times.append(time.perf_counter() - t0)
                per_model[variant].append(st.median(times))
        entry = {}
        normal_mean_ms = st.mean(per_model["Normal"]) * 1e3
        for variant in per_model:
            ms = [t * 1e3 for t in per_model[variant]]
            mean = st.mean(ms)
            lo, hi = bootstrap_ci(per_model[variant], stat=st.mean)
            entry[variant] = {
                "mean_ms_per_batch": round(mean, 3),
                "p90_ms_per_batch": round(percentile(ms, 0.9), 3),
                "p99_ms_per_batch": round(percentile(ms, 0.99), 3),
                "mean_ci95_ms": [round(lo * 1e3, 3), round(hi * 1e3, 3)],
                "ms_per_seq": round(mean / B, 4),
                "throughput_seqs_per_s": round(B / (mean / 1e3), 1),
                "delta_mean_vs_normal_pct": round((mean / normal_mean_ms - 1) * 100, 2)
                if variant != "Normal" else 0.0,
            }
        result["batches"][str(B)] = entry
        row = "  ".join(f"{v}: {entry[v]['mean_ms_per_batch']:.1f} ms/batch "
                        f"({entry[v]['ms_per_seq']:.3f} ms/seq)"
                        for v in models)
        print(f"B={B:4d}: {row}")

    with open(args.out, "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
