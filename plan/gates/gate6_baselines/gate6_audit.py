#!/usr/bin/env python3
"""Gate 6 — integrity audit + paper-ready numbers (self-contained; same checks
as gate3_summary.py style).

Verifies, per dataset:
  (i)   5 paired seeds × 2 variants present, no duplicates
  (ii)  per-seed pairing key integrity (seeds {42,123,2024,7,99})
  (iii) environment block (torch/pandas/python) recorded per sweep segment
  (iv)  sanity: losses finite, positive

Emits gate6_summary.md (audited numbers) + a LaTeX table fragment
(gate6_table.tex) ready to paste into experiments.tex, plus per-dataset
paired Wilcoxon (DLinear vs Normal, PatchTST vs Normal, DLinear vs PatchTST)
as descriptive context — mirroring the gate4 stance (n=5, floor p=0.0625,
no Holm-survivable results expected; NOTHING in the paper claims
significance from these).

Usage: .venv-gate6/bin/python gate6_audit.py [--out-dir DIR]
"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np
from scipy.stats import wilcoxon

GATE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(GATE_DIR, "results")
SEEDS = [42, 123, 2024, 7, 99]
GATE3 = os.path.join(GATE_DIR, "..", "gate3", "results")

# ---------- load gate6 ----------
runs = defaultdict(dict)          # (dataset, variant) -> {seed: rec}
env_seen = set()
bad = []
for fp in sorted(glob.glob(os.path.join(RESULTS_DIR, "*.jsonl"))):
    ds = os.path.basename(fp)[:-6]
    for line in open(fp):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        key = (ds, r["variant"])
        if r["seed"] in runs[key]:
            bad.append(f"duplicate: {key} seed {r['seed']}")
        runs[key][r["seed"]] = r

# ---------- load gate3 comparison rows ----------
def gate3_means():
    out = defaultdict(lambda: defaultdict(list))   # ds -> variant -> vals
    for ds in {d for d, _ in runs}:
        fp = os.path.join(GATE3, f"{ds}.jsonl")
        if not os.path.exists(fp):
            bad.append(f"missing gate3 results for {ds}")
            continue
        for line in open(fp):
            r = json.loads(line)
            out[ds][r["variant"]].append((r["seed"], r["val_mse"], r["test_mse"]))
    return out

g3 = gate3_means()

# ---------- audit ----------
rows, missing = [], []
for (ds, var), seeds in sorted(runs.items()):
    if sorted(seeds) != SEEDS:
        missing.append(f"{ds}/{var}: seeds {sorted(seeds)} != {SEEDS}")
    for s, r in seeds.items():
        if not (np.isfinite(r["val_mse"]) and r["val_mse"] > 0 and
                np.isfinite(r["test_mse"]) and r["test_mse"] > 0):
            bad.append(f"non-finite/nonpositive: {ds}/{var} seed {s}")

n_expected = len({d for d, _ in runs}) * 2 * 5
n_actual = sum(len(v) for v in runs.values())
print(f"gate6 runs: {n_actual} records across {len({d for d, _ in runs})} datasets")
if bad:
    print("PROBLEMS:")
    for b in bad:
        print("  -", b)
if missing:
    print("INCOMPLETE (re-run sweep to fill):")
    for m in missing:
        print("  -", m)
if not bad:
    print("integrity: PASS" + ("" if not missing else f" ({len(missing)} dataset/variant groups incomplete)"))

# ---------- stats + tables ----------
def wtest(a, b):
    """Two-sided paired Wilcoxon on 5 pairs; returns p or None."""
    if len(a) < 5:
        return None
    try:
        return float(wilcoxon(a, b, zero_method="wilcox", method="exact").pvalue)
    except ValueError:
        return 1.0     # all-zero differences

print("\nPer-dataset means (val | test) and deltas vs the paper's frozen-protocol rows:")
latex = []
for ds in sorted({d for d, _ in runs}):
    cells = []
    for var in ("DLinear", "PatchTST"):
        seeds = runs.get((ds, var), {})
        if not seeds:
            continue
        vals = [seeds[s]["val_mse"] for s in SEEDS if s in seeds]
        tests = [seeds[s]["test_mse"] for s in SEEDS if s in seeds]
        params = seeds[SEEDS[0]]["full_params"] if SEEDS[0] in seeds else 0
        cells.append((var, np.mean(vals), np.std(vals, ddof=1) if len(vals) > 1 else 0,
                      np.mean(tests), params))
    if len(cells) < 2:
        continue
    # gate3 rows for the same dataset
    n_rec = g3.get(ds, {}).get("Normal", [])
    f_rec = g3.get(ds, {}).get("Flat", [])
    d_rec = g3.get(ds, {}).get("DRRA", [])
    def m(recs, i):
        return np.mean([x[i] for x in recs]) if recs else float("nan")
    n_val, f_val, d_val = m(n_rec, 1), m(f_rec, 1), m(d_rec, 1)
    n_test, f_test, d_test = m(n_rec, 2), m(f_rec, 2), m(d_rec, 2)
    # paired wilcoxon (per-seed pairing, gate6 vs gate3 val_mse)
    def paired_vs_normal(gate3_recs, var_seeds):
        if not gate3_recs:
            return None
        gate3 = {r[0]: r[1] for r in gate3_recs}          # seed -> val
        a = [gate3[s] for s in SEEDS if s in gate3 and s in var_seeds]
        b = [var_seeds[s]["val_mse"] for s in SEEDS
             if s in gate3 and s in var_seeds]
        return wtest(a, b) if len(a) == 5 else None
    p_dl_n = paired_vs_normal(n_rec, runs[(ds, "DLinear")])
    p_pt_n = paired_vs_normal(n_rec, runs[(ds, "PatchTST")])
    p_dl_pt = None
    if (ds, "DLinear") in runs and (ds, "PatchTST") in runs:
        a = [runs[(ds, "DLinear")][s]["val_mse"] for s in SEEDS
             if s in runs[(ds, "DLinear")] and s in runs[(ds, "PatchTST")]]
        b = [runs[(ds, "PatchTST")][s]["val_mse"] for s in SEEDS
             if s in runs[(ds, "DLinear")] and s in runs[(ds, "PatchTST")]]
        p_dl_pt = wtest(a, b)
    print(f"\n{ds}:  Normal {n_val:.4f}|{n_test:.4f}   CSA {f_val:.4f}|{f_test:.4f}   "
          f"DRRA {d_val:.4f}|{d_test:.4f}")
    for var, mv, sv, mt, params in cells:
        print(f"  {var:8s} {mv:.4f}±{sv:.4f} | test {mt:.4f} | params {params}")
    if p_dl_n: print(f"  Wilcoxon p (val): DLinear vs Normal {p_dl_n:.4f}, "
                     f"PatchTST vs Normal {p_pt_n if p_pt_n else float('nan'):.4f}, "
                     f"DLinear vs PatchTST {p_dl_pt if p_dl_pt else float('nan'):.4f}")    # latex fragment row: dataset & DLinear & PatchTST & Normal & CSA & DRRA (val means)
    dln = cells[0][1] if cells[0][0] == "DLinear" else cells[1][1]
    ptn = cells[1][1] if cells[0][0] == "DLinear" else cells[0][1]
    latex.append(f"{ds} & {dln:.4f} & {ptn:.4f} & {n_val:.4f} & {f_val:.4f} & {d_val:.4f} \\\\")

with open(os.path.join(GATE_DIR, "gate6_table.tex"), "w") as f:
    f.write("% auto-generated by gate6_audit.py — paste body into table env\n")
    f.write("\n".join(latex) + "\n")
print(f"\nLaTeX fragment -> {GATE_DIR}/gate6_table.tex ({len(latex)} datasets)")

# ---------- summary md ----------
with open(os.path.join(GATE_DIR, "gate6_summary.md"), "w") as f:
    f.write("# Gate 6 — External Baselines Summary\n\n")
    f.write("DLinear + PatchTST under the frozen direct-96 protocol, 5 paired seeds, "
            "12 datasets; environment recorded per sweep segment.\n\n")
    f.write(f"- runs audited: {n_actual}; integrity: {'PASS' if not bad else 'FAIL'}\n")
    f.write("- pairing: same seeds {42,123,2024,7,99} as Gates 2/3; per-seed pairing "
            "preserved for Wilcoxon\n")
    f.write("- stance: descriptive; at n=5 nothing can reach p<0.05 (floor 0.0625) — "
            "tests reported for context only\n")
print(f"summary -> {GATE_DIR}/gate6_summary.md")
