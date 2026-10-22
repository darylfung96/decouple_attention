#!/usr/bin/env python3
"""Figure: PatchTST-backbone transfer, performance vs speed (4 cells).

X = forward latency B32 mean (25 rounds x 30, round-robin, same machine);
Y = validation MSE mean over 5 seeds (ETTh1 left, ETTh2 right).
Points are means only (no error bars); accuracy ties, speed separates.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# TrueType, not Type 3: submission PDFs must not embed Type 3 fonts.
plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})

REPO = Path(__file__).resolve().parents[2]
G17 = REPO / "plan" / "gates" / "gate17_e2"
FIG = REPO / "paper" / "figures"

ana = json.loads((G17 / "gate17_analysis.json").read_text())
spd = json.loads((G17 / "gate17_speed.json").read_text())

ORDER = [("CSA", (4, 4)), ("DRRA", (8, 4)), ("C48", (4, 8)), ("C88", (8, 8))]
KEYS = {"CSA": "CSA", "DRRA": "DRRA", "C48": "C48", "C88": "C88"}
VAL = {
    "etth1": {"CSA": ana["etth1"]["means"]["CSA"], "DRRA": ana["etth1"]["means"]["DRRA"],
              "C48": ana["etth1"]["means"]["C48"], "C88": ana["etth1"]["means"]["C88"]},
    "etth2": {"CSA": ana["etth2"]["means"]["CSA"], "DRRA": ana["etth2"]["means"]["DRRA"],
              "C48": ana["etth2"]["means"]["C48"], "C88": ana["etth2"]["means"]["C88"]},
}
LAT = {k: spd["latency"][k]["mean_ms"] for k in ("CSA", "DRRA", "C48", "C88")}

COLORS = {"CSA": "#2ca02c", "DRRA": "#1f77b4", "C48": "#d62728", "C88": "#9467bd"}
LABELS = {"CSA": "$(4,4)$", "DRRA": "$(8,4)$", "C48": "$(4,8)$", "C88": "$(8,8)$"}
# Per-cell label offsets (points) and alignment: keep numerals clear of the
# markers and of each other in both panels.
LOFF = {"CSA": (-7, 5), "DRRA": (7, -12), "C48": (7, 6), "C88": (7, 6)}
LHAL = {"CSA": "right"}

fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.0), sharex=True)
for ax, ds, title in zip(axes, ("etth1", "etth2"), ("ETTh1", "ETTh2")):
    ys = np.array([VAL[ds][k] for k in ("CSA", "DRRA", "C48", "C88")])
    xs = np.array([LAT[k] for k in ("CSA", "DRRA", "C48", "C88")])
    pad = max(0.002, (ys.max() - ys.min()) * 0.6 + 0.001)
    for k in ("CSA", "DRRA", "C48", "C88"):
        ax.scatter(LAT[k], VAL[ds][k], s=70, color=COLORS[k], zorder=3)
        ax.annotate(LABELS[k], (LAT[k], VAL[ds][k]),
                    textcoords="offset points", xytext=LOFF[k], fontsize=8,
                    ha=LHAL.get(k, "left"))
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("Speed — mean forward latency B32 (ms)")
    ax.set_xlim(min(xs) - 1.5, max(xs) + 1.5)
    ax.set_ylim(ys.min() - pad, ys.max() + pad)
    ax.tick_params(labelsize=7.5)
axes[0].set_ylabel("Performance — mean val MSE (5 seeds)")
fig.tight_layout()
fig.savefig(FIG / "fig11_transfer_speed.pdf")
fig.savefig(FIG / "fig11_transfer_speed.png", dpi=150)
plt.close(fig)
print("wrote fig11_transfer_speed.pdf/png")
print("lat", {k: round(LAT[k], 2) for k in LAT},
      "etth1", {k: VAL["etth1"][k] for k in VAL["etth1"]},
      "etth2", {k: VAL["etth2"][k] for k in VAL["etth2"]})
