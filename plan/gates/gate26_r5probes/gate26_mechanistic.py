#!/usr/bin/env python3
"""Gate 26 — R5 probe regeneration (mechanistic probes, post-mapping-fix).

Copy of plan/gates/gate12/gate12_mechanistic.py; only the output paths and this
header differ. Protocol is byte-identical to Gate 12 (one variable against it:
the implementation version, i.e. the 2026-09-28 mapping fix). Gate 12's artifacts
are historical and are never overwritten; see design.md for the frozen rule.

Trains the three compared variants (Normal, Flat=(4,4), DRRA=(8,4)) on the
two mechanistic synthetic datasets (seed 42, frozen protocol, checkpoints
saved), then runs three analyses:

  (1) Lag-resolved per-channel error on syn_delayedcopy. Channels 0-4 are
      periodic with lags {96,128,168,224,256} (exact-offset copy targets,
      fully in-window); channels 5-6 are pure noise (floor). Per-channel
      test MSE per model answers: which models reproduce exact in-window
      offsets, and does error grow with lag?
  (2) Change-point distance stratification on syn_changepoints. Per-window
      test MSE bucketed by "rows since the last level change at the forecast
      start" (0-100 / 100-500 / 500-1000 / 1000-2000): models that weight
      recent context more heavily degrade less right after a change.
  (3) Signal-dependence correlation (H4, cross-dataset): per-dataset lag-1
      autocorrelation and roughness (mean |dx|/std) of the standardized
      train split vs the per-dataset Δval% vs Normal (from the Gate-3
      results); Pearson + Spearman across the 12 datasets.

Output: plan/gates/gate26_r5probes/gate26_results.json (summary written by hand
as gate26_summary.md).
"""
import json
import os
import statistics as st
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import numpy as np
import torch  # noqa: E402
from scipy import stats as sps  # noqa: E402

GATE3_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gate3")
sys.path.insert(0, GATE3_DIR)
from gate3_harness import (build_model, make_loaders, train_and_eval,  # noqa: E402
                           VARIANT_CELLS)
import gate3_datasets as g3  # noqa: E402
from dataset import ETTForecastDataset  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CKPT_DIR = os.path.join(HERE, "checkpoints")
OUT_JSON = os.path.join(HERE, "gate26_results.json")
OUT_MD = os.path.join(HERE, "gate26_summary.md")

VARIANTS = ["Normal", "Flat", "DRRA"]
SEED = 42
L, H = 256, 96
N_CHANGE = 2000          # syn_changepoints: level changes at t = 2000k
N_TOTAL = 20000
BOOT_N = 10000


def per_channel_mse(model, loader, n_channels):
    """Per-channel mean squared error over the loader (mean over batches and
    horizon positions). NOTE: divide the channel sums by H as well — an
    earlier version divided by the sample count only, inflating values by
    the horizon length (96)."""
    tot = np.zeros(n_channels)
    n = 0
    with torch.no_grad():
        for x, y in loader:
            out = model(x)
            se = (out - y) ** 2                      # [B, H, F]
            tot += se.sum(dim=(0, 1)).numpy()
            n += x.shape[0]
    return tot / (n * H)


def window_mse_by_distance(model, dataset_name):
    """Per-window MSE bucketed by rows-since-last-change at horizon start."""
    tr, va, te, _ = g3.preprocess(dataset_name)
    s2 = int(len(tr) + len(va))                      # test split start (absolute)
    ds = ETTForecastDataset(te, lookback=L, horizon=H)
    loader = DataLoader(ds, batch_size=32, shuffle=False)
    per_win = []
    with torch.no_grad():
        for bi, (x, y) in enumerate(loader):
            out = model(x)
            mse = ((out - y) ** 2).mean(dim=(1, 2))  # [B]
            for j in range(x.shape[0]):
                per_win.append(float(mse[j]))
    # window i (split-local): horizon start absolute = s2 + i + L
    buckets = {"0-100": [], "100-500": [], "500-1000": [], "1000-2000": []}
    for i, mse in enumerate(per_win):
        hs = s2 + i + L
        last_cp = (hs // N_CHANGE) * N_CHANGE
        d = hs - last_cp
        if d < 100:
            buckets["0-100"].append(mse)
        elif d < 500:
            buckets["100-500"].append(mse)
        elif d < 1000:
            buckets["500-1000"].append(mse)
        else:
            buckets["1000-2000"].append(mse)
    return {k: {"mean_mse": round(st.mean(v), 4), "n": len(v)}
            for k, v in buckets.items()}


def signal_stats(dataset_name):
    tr, _, _, _ = g3.preprocess(dataset_name)
    ac = [float(np.corrcoef(tr[:-1, c], tr[1:, c])[0, 1]) for c in range(tr.shape[1])]
    rough = [float(np.abs(np.diff(tr[:, c], axis=0)).mean() / tr[:, c].std())
             for c in range(tr.shape[1])]
    return {"lag1_autocorr": round(st.mean(ac), 4),
            "roughness": round(st.mean(rough), 4)}


def main():
    torch.set_num_threads(8)
    os.makedirs(CKPT_DIR, exist_ok=True)
    result = {"models": {}, "per_channel_delayedcopy": {}, "cp_distance": {},
              "signal_dependence": {}}

    # ── train + keep models ────────────────────────────────────────────────
    trained = {}
    for ds in ("syn_delayedcopy", "syn_changepoints"):
        for v in VARIANTS:
            print(f"[train] {ds} {v} seed={SEED}")
            train_loader, val_loader, test_loader = make_loaders(ds, SEED, smoke=False)
            model = build_model(ds, v, SEED)
            t0 = time.time()
            tr_mse, val_mse, test_mse = train_and_eval(
                model, train_loader, val_loader, test_loader, epochs=10)
            ckpt = os.path.join(CKPT_DIR, f"{ds}_{v}_{SEED}.pt")
            torch.save(model.state_dict(), ckpt)
            trained[(ds, v)] = model
            result["models"][f"{ds}_{v}"] = {
                "val_mse": round(val_mse, 6), "test_mse": round(test_mse, 6),
                "final_train_mse": round(tr_mse, 6),
                "checkpoint": os.path.relpath(ckpt, REPO_ROOT)}
            print(f"  val {val_mse:.4f} test {test_mse:.4f} ({time.time()-t0:.0f}s)")

    # ── (1) lag-resolved per-channel error on delayedcopy ──────────────────
    _, _, te, _ = g3.preprocess("syn_delayedcopy")
    loader = DataLoader(ETTForecastDataset(te, lookback=L, horizon=H),
                        batch_size=32, shuffle=False)
    for v in VARIANTS:
        pcm = per_channel_mse(trained[("syn_delayedcopy", v)], loader, 7)
        result["per_channel_delayedcopy"][v] = [round(float(x), 5) for x in pcm]
        print(f"[per-channel] {v}: " + " ".join(f"{x:.4f}" for x in pcm))

    # ── (2) change-point distance stratification ───────────────────────────
    for v in VARIANTS:
        result["cp_distance"][v] = window_mse_by_distance(
            trained[("syn_changepoints", v)], "syn_changepoints")
        print(f"[cp-distance] {v}: " + "  ".join(
            f"{k}={d['mean_mse']:.3f}(n={d['n']})" for k, d in result["cp_distance"][v].items()))

    # ── (3) signal-dependence correlation (H4) ─────────────────────────────
    ds_list = ["etth1", "etth2", "ettm1", "ettm2", "electricity", "traffic",
               "weather", "exchange", "solar",
               "syn_sinusoids", "syn_changepoints", "syn_delayedcopy"]

    SEEDS = [42, 123, 2024, 7, 99]

    def mean_v(ds, v):
        rr = [json.loads(l) for l in open(
            os.path.join(GATE3_DIR, "results", f"{ds}.jsonl"))]
        return st.mean([r["val_mse"] for r in rr if r["variant"] == v])

    sig = {ds: signal_stats(ds) for ds in ds_list}
    for v in ("Flat", "DRRA"):
        deltas = np.array([(mean_v(ds, v) / mean_v(ds, "Normal") - 1) * 100
                           for ds in ds_list])
        acs = np.array([sig[ds]["lag1_autocorr"] for ds in ds_list])
        rough = np.array([sig[ds]["roughness"] for ds in ds_list])
        pr = sps.pearsonr(acs, deltas)
        sr = sps.spearmanr(acs, deltas)
        pr2 = sps.pearsonr(rough, deltas)
        sr2 = sps.spearmanr(rough, deltas)
        result["signal_dependence"][v] = {
            "mean_dval_pct": round(float(deltas.mean()), 2),
            "pearson_dval_vs_lag1": {"r": round(float(pr[0]), 3), "p": round(float(pr[1]), 4)},
            "spearman_dval_vs_lag1": {"rho": round(float(sr[0]), 3), "p": round(float(sr[1]), 4)},
            "pearson_dval_vs_roughness": {"r": round(float(pr2[0]), 3), "p": round(float(pr2[1]), 4)},
            "spearman_dval_vs_roughness": {"rho": round(float(sr2[0]), 3), "p": round(float(sr2[1]), 4)},
        }
        print(f"[signal-dep] {v}: Δval {deltas.mean():+.2f}% | vs lag1: r={pr[0]:+.3f} (p={pr[1]:.3f}) "
              f"rho={sr[0]:+.3f} | vs roughness: r={pr2[0]:+.3f}")

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
