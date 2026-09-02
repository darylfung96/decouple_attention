#!/usr/bin/env python3
"""Gate 3 companion — forward-pass latency benchmark (NEW measurements, frozen protocol).

Measures wall-clock forward latency for the three compared configurations
(Normal, Flat=(4,4), DRRA=(8,4)) under the frozen task shapes (L=256, H=96,
F=7, batch 32, fp32, 8 threads) on the development machine, using the
alternating head-to-head protocol (the methodology that survived the
pre-freeze speed-claim removal; see plan/paper_notes.md §4 and the removal
notes in WRITEUP.md/RESULTS.md — the OLD pilot-era figures are superseded and
are NOT reproduced here; everything in this script's output is measured now).

Protocol:
  - one shared fixed input tensor [32, 256, 7] (torch.manual_seed(0))
  - warm-up: 10 passes per model (excluded)
  - 25 rounds; in each round the three models are timed in rotation
    (alternating head-to-head: same thermal/contention window per round),
    30 timed passes per model per round
  - per model: per-round medians -> mean (primary), p90/p99, and
    95% percentile bootstrap CI on the mean (10,000 resamples)
  - throughput = batch_size / mean forward time
  - torch.set_num_threads(8), eval mode, no_grad, deterministic seeds

Output: plan/gates/gate3/gate3_latency.json (machine + per-model stats) and a
printed summary. Exit 0 on success.
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
                        "gate3_latency.json")

LOOKBACK = 256
HORIZON = 96
FEATURES = 7
BATCH = 32
THREADS = 8
ROUNDS = 25
PASSES = 30
WARMUP = 10
BOOTSTRAP_N = 10000
SEED = 42          # model init seed (frozen protocol)
INPUT_SEED = 0     # shared input tensor


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
    lo = hi = est
    if round_medians:
        resampled = [stat(rng.choices(round_medians, k=len(round_medians)))
                     for _ in range(n)]
        resampled.sort()
        lo = resampled[int(n * alpha / 2)]
        hi = resampled[int(n * (1 - alpha / 2)) - 1]
    return lo, hi


def main():
    p = argparse.ArgumentParser(description="Gate 3 latency benchmark (frozen protocol)")
    p.add_argument("--rounds", type=int, default=ROUNDS)
    p.add_argument("--passes", type=int, default=PASSES)
    p.add_argument("--warmup", type=int, default=WARMUP)
    p.add_argument("--threads", type=int, default=THREADS)
    p.add_argument("--out", default=OUT_PATH)
    args = p.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(INPUT_SEED)
    x = torch.randn(BATCH, LOOKBACK, FEATURES)

    models = {}
    for variant in sorted(VARIANT_CELLS):
        torch.manual_seed(SEED)          # frozen protocol: seed before init
        m = build_model("etth1", variant, seed=SEED)
        m.eval()
        models[variant] = m

    # warm-up (excluded)
    for variant, m in models.items():
        with torch.no_grad():
            for _ in range(args.warmup):
                m(x)

    per_model = {v: [] for v in models}   # per-round medians, seconds
    for r in range(1, args.rounds + 1):
        round_medians = {}
        for variant, m in models.items():   # rotation within each round
            times = []
            with torch.no_grad():
                for _ in range(args.passes):
                    t0 = time.perf_counter()
                    m(x)
                    times.append(time.perf_counter() - t0)
            round_medians[variant] = st.median(times)
        for v, t in round_medians.items():
            per_model[v].append(t)
        if r % 5 == 0 or r == 1:
            print(f"  round {r:2d}/{args.rounds}: " +
                  "  ".join(f"{v} {st.median(per_model[v])*1e3:.2f} ms"
                            for v in per_model))

    result = {"machine": {}, "models": {}}
    try:
        import platform
        result["machine"] = {
            "platform": platform.platform(),
            "cpu": platform.processor(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "threads": args.threads,
            "chip": None,
        }
        import subprocess
        chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                              capture_output=True, text=True).stdout.strip()
        cores = subprocess.run(["sysctl", "-n", "hw.ncpu"],
                               capture_output=True, text=True).stdout.strip()
        mem = subprocess.run(["sysctl", "-n", "hw.memsize"],
                             capture_output=True, text=True).stdout.strip()
        result["machine"].update({"chip": chip, "cores": cores, "mem_bytes": mem})
    except Exception as e:  # pragma: no cover
        result["machine"]["note"] = f"machine details incomplete: {e}"

    normal_mean = st.mean(per_model["Normal"])
    for variant in per_model:
        ms = [t * 1e3 for t in per_model[variant]]
        mean, p90, p99 = st.mean(ms), percentile(ms, 0.9), percentile(ms, 0.99)
        lo, hi = bootstrap_ci(per_model[variant], stat=st.mean)
        result["models"][variant] = {
            "mean_ms": round(mean, 4),
            "p90_ms": round(p90, 4),
            "p99_ms": round(p99, 4),
            "mean_ci95_ms": [round(lo * 1e3, 4), round(hi * 1e3, 4)],
            "throughput_batches_per_s": round(1.0 / st.mean(per_model[variant]), 2),
            "delta_mean_vs_normal_pct": round((mean / (normal_mean * 1e3) - 1) * 100, 2)
            if variant != "Normal" else 0.0,
            "rounds": len(ms),
            "passes_per_round": args.passes,
        }
        print(f"\n{variant}: mean {mean:.3f} ms  p90 {p90:.3f} ms  p99 {p99:.3f} ms  "
              f"mean 95% CI [{lo*1e3:.3f}, {hi*1e3:.3f}] ms  "
              f"throughput {1.0/st.mean(per_model[variant]):.1f} batches/s")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
