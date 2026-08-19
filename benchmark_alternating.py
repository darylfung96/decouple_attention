"""Contention-robust alternating benchmark (forward-only).

Sequential per-model benchmarks on this machine are unreliable (CPU
thermal/contention drift: same model ranged 22-273 ms across runs). The
alternating head-to-head protocol normalizes drift because every model is
measured in the same short time window, interleaved per rep.

Protocol (same as RESULTS.md):
  - reps = 3 passes over the model list, order shuffled each rep
  - within each model: warmup runs then timed runs (benchmark_speed.benchmark)
  - report the MEDIAN of each model's 3 timings, plus ratio vs Flat
"""
import argparse
import random
import statistics

import torch
import torch.nn as nn

from benchmark_speed import (FlatWrapper, NormalWrapper, ModifiedWrapper,
                             StackedWrapper, FlatPlusWrapper, ExpertFlatWrapper,
                             ExpertPlusPlusWrapper, SurrogateWrapper,
                             SurrogateV2Wrapper, benchmark, count_params)

MODELS = {
    'Flat (64 KV)':        lambda: FlatWrapper(),
    'FlatPlus (64 KV)':    lambda: FlatPlusWrapper(),
    'Normal (256 KV)':     lambda: NormalWrapper(),
    'Modified (128 KV)':   lambda: ModifiedWrapper(),
    'Stacked (64 KV)':     lambda: StackedWrapper(),
    'ExpertFlat (68 KV)':  lambda: ExpertFlatWrapper(),
    'ExpertPlusPlus (52 KV)': lambda: ExpertPlusPlusWrapper(),
    'Surrogate MLP':       lambda: SurrogateWrapper(),
    'Surrogate Win+Glob':  lambda: SurrogateV2Wrapper(),
}

# Val MSE (10 epochs, ETTh1, from RESULTS.md / trained surrogates at 5+1 epochs)
VAL_MSE = {
    'Flat (64 KV)':          0.1085,
    'FlatPlus (64 KV)':      0.1098,
    'Normal (256 KV)':       0.1083,
    'Modified (128 KV)':     0.1088,
    'Stacked (64 KV)':       0.1116,
    'ExpertFlat (68 KV)':    0.1102,
    'ExpertPlusPlus (52 KV)': 0.1099,
    'Surrogate MLP':         0.1424,   # distilled from Normal, 5+1 epochs
    'Surrogate Win+Glob':    0.1269,   # distilled from Normal, 5+1 epochs
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reps', type=int, default=3)
    ap.add_argument('--only', type=str, default=None,
                    help='Comma-separated subset of model names to benchmark')
    ap.add_argument('--iters', type=int, default=100)
    args = ap.parse_args()

    names = list(MODELS.keys())
    if args.only:
        names = [n.strip() for n in args.only.split(',') if n.strip() in MODELS]

    timings = {n: [] for n in names}
    print("Alternating head-to-head (forward-only, batch=32, seq=256) "
          f"— {args.reps} reps")
    for rep in range(args.reps):
        order = names[:]
        random.Random(rep).shuffle(order)
        for name in order:
            model = MODELS[name]()
            r = benchmark(model, name, forward_only=True, num_iters=args.iters)
            timings[name].append(r['avg_ms'])
            print(f"  rep {rep} {name}: {r['avg_ms']:.2f} ms", flush=True)

    print(f"\n{'='*90}")
    print(f"{'Model':<26} {'Val MSE':>9} {'Params(M)':>9} {'Fwd(ms)':>9} "
          f"{'Perf/Spd':>9} {'vs Flat':>8} {'vs EPP':>8}")
    print(f"{'-'*90}")

    flat_med = statistics.median(timings['Flat (64 KV)']) if 'Flat (64 KV)' in timings else None
    epp_med = statistics.median(timings['ExpertPlusPlus (52 KV)']) if 'ExpertPlusPlus (52 KV)' in timings else None

    for name in names:
        med = statistics.median(timings[name])
        perf = VAL_MSE[name]
        pspd = (1.0 / perf) / med * 1000
        vs_f = f"{flat_med / med:.2f}×" if flat_med else '—'
        vs_e = f"{epp_med / med:.2f}×" if epp_med else '—'
        params = count_params(MODELS[name]()) / 1e6
        print(f"{name:<26} {perf:>9.4f} {params:>9.2f} {med:>9.2f} "
              f"{pspd:>9.1f} {vs_f:>8} {vs_e:>8}")

    print(f"\n  Perf/Spd = (1 / Val MSE) / Fwd(ms) × 1000  (higher = better)")
    print(f"  NOTE: surrogate val MSEs are from 5+1-epoch distillation runs;")
    print(f"        CSA variants are 10-epoch results from RESULTS.md.")


if __name__ == '__main__':
    main()
