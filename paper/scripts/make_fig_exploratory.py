#!/usr/bin/env python3
"""Exploratory figure: all 7 ETTh1 cells incl. post-hoc (16,4)/(32,4).
Kept OUT of make_figures.py so confirmatory figures never mix exploratory cells.
Reads: gate15_analysis.json (5 factorial cells) + gate18/gate19 ETTh1 rows.
Writes: paper/figures/fig10_exploratory.{pdf,png}
Run: ~/.uv_env/py311/bin/python paper/scripts/make_fig_exploratory.py
"""
import json
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
FIG = REPO / "paper" / "figures"
A = json.load(open(REPO / "plan/gates/gate15_rerun/gate15_analysis.json"))
R18 = [json.loads(l) for l in open(REPO / "plan/gates/gate18_d5/results/etth1.jsonl")]
R19 = [json.loads(l) for l in open(REPO / "plan/gates/gate19_324/results/etth1.jsonl")]

plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.labelsize": 9.5,
                     "axes.titlesize": 9.5, "figure.dpi": 300,
                     "axes.spines.top": False, "axes.spines.right": False})
order = [("CSA (4,4)", A["cell_means_val"]["CSA"]["mean"], A["cell_means_val"]["CSA"]["std"],
          A["cell_means_test"]["CSA"]),
         ("DRRA (8,4)", A["cell_means_val"]["DRRA"]["mean"], A["cell_means_val"]["DRRA"]["std"],
          A["cell_means_test"]["DRRA"]),
         ("(4,8)", A["cell_means_val"]["C48"]["mean"], A["cell_means_val"]["C48"]["std"],
          A["cell_means_test"]["C48"]),
         ("(8,8)", A["cell_means_val"]["C88"]["mean"], A["cell_means_val"]["C88"]["std"],
          A["cell_means_test"]["C88"]),
         ("(16,4)*", float(np.mean([r["val_mse"] for r in R18])),
          float(np.std([r["val_mse"] for r in R18], ddof=1)),
          float(np.mean([r["test_mse"] for r in R18]))),
         ("(32,4)*", float(np.mean([r["val_mse"] for r in R19])),
          float(np.std([r["val_mse"] for r in R19], ddof=1)),
          float(np.mean([r["test_mse"] for r in R19])))]
normal_val, normal_test = 0.8389, 1.0804
labels = [o[0] for o in order]
x = np.arange(len(order))
w = 0.36
fig, ax = plt.subplots(figsize=(6.5, 2.8))
ax.bar(x - w / 2, [o[1] for o in order], width=w, yerr=[o[2] for o in order],
       color="#4C72B0", alpha=0.85, capsize=3, label="Validation")
ax.bar(x + w / 2, [o[3] for o in order], width=w, color="#DD8452", alpha=0.85,
       label="Test")
ax.axhline(normal_val, color="black", linestyle="--", linewidth=0.9)
ax.text(len(order) - 0.4, normal_val + 0.015, "Normal val 0.8389", ha="right", fontsize=8)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=8)
ax.set_ylabel("MSE (standardized)")
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "fig10_exploratory.pdf")
fig.savefig(FIG / "fig10_exploratory.png")
plt.close(fig)
print("means:", [(o[0], round(o[1], 4), round(o[3], 4)) for o in order])
print("wrote fig10_exploratory.pdf/png")
