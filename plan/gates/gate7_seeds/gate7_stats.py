#!/usr/bin/env python3
"""Gate 7 — integrity audit + stats for the seed-power extension.

Merges Gate-7 runs (20 new seeds) with the Gate-2 manifest (5 original
paired seeds) into a 25-seed factorial, then runs the analysis the paper
deferred (roadmap item 1):
  - per-cell mean/std
  - main effects with per-seed signs
  - paired Wilcoxon: DRRA vs CSA, and each cell vs Normal (n=25;
    two-sided floor p = 2/2^25 ~ 6e-8)
  - Holm correction across the 5 pre-registered contrasts
  - mixed-effects-style main-effects check: paired t on per-seed
    main-effect differences (beta2 > beta1 directional test), plus
    Wilcoxon on per-seed (c_R effect - c_KV effect)

Usage: .venv-gate6/bin/python gate7_stats.py
"""
import glob
import json
import os
from collections import defaultdict

import numpy as np
from scipy.stats import wilcoxon, ttest_rel

GATE7 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "gate7.jsonl")
GATE2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gate2",
                     "gate2_results.jsonl")

cells = defaultdict(dict)          # cell_name -> seed -> val
for line in open(GATE2):
    r = json.loads(line)
    if r["cell"] is None:
        continue                      # factorial file holds compressed cells only
    name = f"({r['cell'][0]},{r['cell'][1]})"
    name = {"(4,4)": "CSA(4,4)", "(8,4)": "DRRA(8,4)"}.get(name, name)
    cells[name][r["seed"]] = r["val_mse"]
# Normal's 5 original seeds live in the baseline-gate manifest (cell is a
# string there); its ETTh1 rows are bit-identical to gate3's Normal rows
# (pipeline-fidelity audit, README "Number provenance").
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "baseline",
                        "baseline_normal_results.jsonl")
for line in open(BASELINE):
    r = json.loads(line)
    if r["cell"] == "Normal":
        cells["Normal"][r["seed"]] = r["val_mse"]
for line in open(GATE7):
    r = json.loads(line)
    cells[r["cell_name"]][r["seed"]] = r["val_mse"]

print("cell sizes:", {k: len(v) for k, v in cells.items()})
sizes = {len(v) for v in cells.values()}
if sizes != {25}:
    print(f"WARNING: expected 25 seeds per cell, got {sizes} — results below are "
          f"partial (gate7 may still be running; this script is idempotent)")

order = ["Normal", "CSA(4,4)", "DRRA(8,4)", "(4,8)", "(8,8)"]
present = [c for c in order if cells.get(c)]
if not present:
    raise SystemExit("no gate7 data yet")
seeds = sorted(set.intersection(*[set(cells[c]) for c in present]))
missing_cells = [c for c in order if c not in present]
print(f"paired seeds usable: n={len(seeds)} across {len(present)} cells"
      + (f" (missing cells: {missing_cells})" if missing_cells else "") + "\n")

means = {c: np.mean([cells[c][s] for s in seeds]) for c in present}
stds = {c: np.std([cells[c][s] for s in seeds], ddof=1) for c in present}
for c in present:
    print(f"{c:9s} {means[c]:.4f} ± {stds[c]:.4f}")

# main effects per seed (paired)
eff_kv = [( (cells["DRRA(8,4)"][s] + cells["(8,8)"][s]) / 2
          - (cells["CSA(4,4)"][s] + cells["(4,8)"][s]) / 2) for s in seeds]
eff_r = [( (cells["(4,8)"][s] + cells["(8,8)"][s]) / 2
          - (cells["CSA(4,4)"][s] + cells["DRRA(8,4)"][s]) / 2) for s in seeds]
print(f"\nmain effect c_KV (4->8): {np.mean(eff_kv):+.4f}  "
      f"(sign consistent {sum(1 for e in eff_kv if e < 0)}/{len(eff_kv)})")
print(f"main effect c_R  (4->8): {np.mean(eff_r):+.4f}  "
      f"(sign consistent {sum(1 for e in eff_r if e > 0)}/{len(eff_r)})")

print("\npaired Wilcoxon (two-sided) on validation MSE:")
raw = []
contrasts = [c for c in [
    ("DRRA vs CSA", ["DRRA(8,4)"], ["CSA(4,4)"]),
    ("DRRA vs Normal", ["DRRA(8,4)"], ["Normal"]),
    ("CSA vs Normal", ["CSA(4,4)"], ["Normal"]),
    ("(4,8) vs Normal", ["(4,8)"], ["Normal"]),
    ("(8,8) vs Normal", ["(8,8)"], ["Normal"]),
] if all(b in present for b in c[1] + c[2])]
pvals = {}
for name, a_cells, b_cells in contrasts:
    a = np.mean([cells[c][s] for c in a_cells], axis=0) if len(a_cells) > 1 else \
        np.array([cells[a_cells[0]][s] for s in seeds])
    b = np.mean([cells[c][s] for c in b_cells], axis=0) if len(b_cells) > 1 else \
        np.array([cells[b_cells[0]][s] for s in seeds])
    try:
        p = float(wilcoxon(a, b, method="approx").pvalue)
    except ValueError:
        p = 1.0
    pvals[name] = p
    raw.append(p)
    print(f"  {name:18s} p = {p:.3e}   (mean diff {np.mean(a-b):+.4f})")

# Holm across the 5 contrasts
def holm(ps):
    m = len(ps)
    order_idx = np.argsort(ps)
    adj = [0] * m
    running = 0.0
    for rank, idx in enumerate(order_idx):
        val = (m - rank) * ps[idx]
        running = max(running, val)
        adj[idx] = min(1.0, running)
    return adj
adj = holm(raw)
print("\nHolm-adjusted:")
for (name, *_), p in zip(contrasts, adj):
    print(f"  {name:18s} p_adj = {p:.3e}  {'*' if p < 0.05 else ''}")

# beta2 > beta1 directional check (paired)
diff = np.array(eff_r) - np.array(eff_kv)
t, p_t = ttest_rel(eff_r, eff_kv)
try:
    p_w = float(wilcoxon(eff_r, eff_kv, method="approx").pvalue)
except ValueError:
    p_w = 1.0
print(f"\nH1 strict form (c_R effect > c_KV effect, per-seed paired): "
      f"mean diff {np.mean(diff):+.4f}, t={t:.2f}, paired-t p={p_t:.3e}, "
      f"Wilcoxon p={p_w:.3e}")
print(f"  -> {'SUPPORTED' if p_w < 0.05 and np.mean(diff) > 0 else 'not established'} "
      f"at n={len(seeds)}")
