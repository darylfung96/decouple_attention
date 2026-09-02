#!/usr/bin/env python3
"""Gate 3 — mechanistic synthetic datasets (deterministic, seed 0).

Three families, each N=20,000 rows x 7 channels, written as headerless numeric
CSVs to plan/gates/gate3/data/syn_<name>.csv and consumed by the SAME
gate3_datasets pipeline (60/20/20 split, train-only z-score, stride-1 windows).

1. syn_sinusoids    x_c(t) = A_c sin(2*pi*t/T_c + phi_c) + eps, eps~N(0, 0.1^2)
                     T = [24, 48, 96, 168, 336, 720, 1440]  (daily..2-month)
                     A = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]
                     phi = [0, .5, 1, 1.5, 2, 2.5, 3]
2. syn_changepoints piecewise-constant mean; change points at t = 2000, 4000,
                     ..., 18000; each channel's level shifts by N(0,1) at each
                     boundary; noise sigma 0.1. (Probes post-change adaptation.)
3. syn_delayedcopy  channels periodic with period = lag in [96, 128, 168, 224,
                     256] (5 channels) + 2 pure-noise channels. A period-L
                     channel satisfies y[t+1..t+96] = x[t+1-L .. t+96-L] for
                     L in [96, 256] (copy property, fully in-window) — probes
                     whether routed/compressed attention can reproduce
                     exact-offset in-window content at block granularity.

Determinism: same seed -> byte-identical CSV (SHA-256 recorded in the manifest
on --regenerate).
"""
import argparse
import hashlib
import os

import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
N = 20000
CHANNELS = 7
SEED = 0
NOISE_SIGMA = 0.1


def gen_sinusoids():
    rng = np.random.default_rng(SEED)
    t = np.arange(N, dtype=np.float64)[:, None]
    periods = np.array([24, 48, 96, 168, 336, 720, 1440], dtype=np.float64)
    amps = np.array([1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2])
    phases = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
    x = amps * np.sin(2.0 * np.pi * t / periods + phases)
    return x + NOISE_SIGMA * rng.standard_normal((N, CHANNELS))


def gen_changepoints():
    rng = np.random.default_rng(SEED)
    nseg = N // 2000 + 1
    seg_levels = np.cumsum(rng.standard_normal((nseg, CHANNELS)), axis=0)
    seg = np.minimum(np.arange(N) // 2000, nseg - 1)
    x = seg_levels[seg]
    return x + NOISE_SIGMA * rng.standard_normal((N, CHANNELS))


def gen_delayedcopy():
    rng = np.random.default_rng(SEED)
    t = np.arange(N, dtype=np.float64)[:, None]
    lags = np.array([96, 128, 168, 224, 256], dtype=np.float64)
    phases = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    copy = np.sin(2.0 * np.pi * t / lags + phases)   # period = lag => copy property
    x = np.zeros((N, CHANNELS))
    x[:, :5] = copy
    x[:, 5:] = NOISE_SIGMA * rng.standard_normal((N, 2))  # unpredictable channels
    return x


GENERATORS = {"sinusoids": gen_sinusoids, "changepoints": gen_changepoints,
              "delayedcopy": gen_delayedcopy}


def write_all():
    os.makedirs(DATA_DIR, exist_ok=True)
    hashes = {}
    for name, gen in GENERATORS.items():
        path = os.path.join(DATA_DIR, f"syn_{name}.csv")
        np.savetxt(path, gen(), fmt="%.8f", delimiter=",")
        hashes[name] = hashlib.sha256(open(path, "rb").read()).hexdigest()
        print(f"  syn_{name}: {N}x{CHANNELS} sha256={hashes[name][:16]}...")
    return hashes


def check_all():
    import io
    bad = []
    for name, gen in GENERATORS.items():
        path = os.path.join(DATA_DIR, f"syn_{name}.csv")
        if not os.path.exists(path):
            bad.append(f"syn_{name}: missing")
            continue
        x = np.loadtxt(path, delimiter=",")
        if x.shape != (N, CHANNELS):
            bad.append(f"syn_{name}: shape {x.shape}")
            continue
        # Determinism = byte-identity: savetxt output for a fresh generation must
        # equal the on-disk file (%.8f rounding makes float equality unsuitable).
        buf = io.BytesIO()
        np.savetxt(buf, gen(), fmt="%.8f", delimiter=",")
        if buf.getvalue() != open(path, "rb").read():
            bad.append(f"syn_{name}: not deterministic (regeneration bytes differ)")
    if bad:
        raise SystemExit("\n".join(bad))
    print("ALL SYNTHETIC CHECKS PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Gate 3 synthetic datasets")
    p.add_argument("--regenerate", action="store_true", help="(re)write the 3 CSVs")
    args = p.parse_args()
    if args.regenerate:
        write_all()
    check_all()
