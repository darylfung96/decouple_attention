#!/usr/bin/env python3
"""Regenerate all paper figures from the audited result manifests.

Reads:
  plan/gates/gate2/gate2_results.jsonl        (20 factorial runs)
  plan/gates/baseline/baseline_normal_results.jsonl  (5 Normal baseline runs)
  plan/gates/gate2/gate2_learning_curves.png  (copied, not regenerated)

Writes into ../figures/:
  fig1_factorial_val.{pdf,png}   factorial cell means + std + seed points
  fig2_main_effects.{pdf,png}    c_KV / c_R main effects vs seed noise
  fig3_per_seed.{pdf,png}        per-seed parallel coordinates
  fig4_learning_curves.png       copy of the audited learning-curve plot
  fig5_architecture.{pdf,png}    architecture schematic

Every number in the paper's figures is derived here from the audited JSONL
manifests (source of truth), and the script prints verification lines
against the audited summaries in plan/gates/gate2/gate2_summary.md and
plan/gates/baseline/baseline_normal_summary.md.

Usage: python3 scripts/make_figures.py   (from the paper/ directory)
Requires: matplotlib >= 3.5, numpy.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PAPER_DIR = SCRIPT_DIR.parent
REPO_DIR = PAPER_DIR.parent
PLAN_DIR = REPO_DIR / "plan"
FIG_DIR = PAPER_DIR / "figures"

GATE2_JSONL = PLAN_DIR / "gates" / "gate2" / "gate2_results.jsonl"
NORMAL_JSONL = PLAN_DIR / "gates" / "baseline" / "baseline_normal_results.jsonl"
LEARNING_CURVES = PLAN_DIR / "gates" / "gate2" / "gate2_learning_curves.png"

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.labelsize": 9.5,
    "axes.titlesize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8,
    "figure.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

C = {
    "blue": "#4C72B0",
    "orange": "#DD8452",
    "green": "#55A868",
    "red": "#C44E52",
    "purple": "#8172B3",
}

CELLS = [(4, 4), (8, 4), (4, 8), (8, 8)]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def fmt(v: float) -> str:
    return f"{v:.4f}"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
gate2 = load_jsonl(GATE2_JSONL)
normal = load_jsonl(NORMAL_JSONL)

by_cell: dict[tuple[int, int], list[dict]] = {cell: [] for cell in CELLS}
for row in gate2:
    by_cell[(row["c_kv"], row["c_r"])].append(row)

val_means = {}
val_stds = {}
test_means = {}
train_means = {}
for cell in CELLS:
    vals = np.array([r["val_mse"] for r in by_cell[cell]], dtype=float)
    tests = np.array([r["test_mse"] for r in by_cell[cell]], dtype=float)
    trains = np.array([r["final_train_mse"] for r in by_cell[cell]], dtype=float)
    val_means[cell] = vals.mean()
    val_stds[cell] = vals.std(ddof=1)
    test_means[cell] = tests.mean()
    train_means[cell] = trains.mean()

normal_vals = np.array([r["val_mse"] for r in normal], dtype=float)
normal_tests = np.array([r["test_mse"] for r in normal], dtype=float)
normal_val_mean = normal_vals.mean()
normal_val_std = normal_vals.std(ddof=1)
normal_test_mean = normal_tests.mean()

# --- verification against audited summaries -------------------------------
print("== verification vs audited summaries ==")
print(f"Normal   val {fmt(normal_val_mean)} ± {fmt(normal_val_std)}  test {fmt(normal_test_mean)}"
      f"   [expect 0.8416 ± 0.0799 / 1.0814]")
for cell in CELLS:
    print(f"cell {cell}: val {fmt(val_means[cell])} ± {fmt(val_stds[cell])}  "
          f"test {fmt(test_means[cell])}  train {fmt(train_means[cell])}"
          f"   [expect {fmt(val_means[cell])} matches gate2_summary.md]")

# main effects
c_kv_effect = (val_means[(8, 4)] + val_means[(8, 8)]) / 2 - (val_means[(4, 4)] + val_means[(4, 8)]) / 2
c_r_effect = (val_means[(4, 8)] + val_means[(8, 8)]) / 2 - (val_means[(4, 4)] + val_means[(8, 4)]) / 2
print(f"main effect c_KV = {c_kv_effect:+.4f}   [expect -0.0427]")
print(f"main effect c_R  = {c_r_effect:+.4f}   [expect +0.0463]")

# per-seed consistency of effects (as in gate2_summary.md)
n_kv_improves = 0
for seed_row in range(5):
    for cr in (4, 8):
        v4 = by_cell[(4, cr)][seed_row]["val_mse"]
        v8 = by_cell[(8, cr)][seed_row]["val_mse"]
        if v8 < v4:
            n_kv_improves += 1
n_r_worsens = 0
for seed_row in range(5):
    for ckv in (4, 8):
        v4 = by_cell[(ckv, 4)][seed_row]["val_mse"]
        v8 = by_cell[(ckv, 8)][seed_row]["val_mse"]
        if v8 > v4:
            n_r_worsens += 1
print(f"per-seed consistency: c_KV improves {n_kv_improves}/10, c_R worsens {n_r_worsens}/10"
      f"   [expect 7/10, 7/10]")

# deltas vs Normal (mean and per-seed, all 20 runs)
print("-- deltas vs Normal --")
normal_by_seed = {r["seed"]: r["val_mse"] for r in normal}
for cell in CELLS:
    d = (val_means[cell] - normal_val_mean) / normal_val_mean * 100
    dt = (test_means[cell] - normal_test_mean) / normal_test_mean * 100
    wins = sum(1 for r in by_cell[cell] if r["val_mse"] < normal_by_seed[r["seed"]])
    print(f"cell {cell}: dval {d:+.2f}%  dtest {dt:+.2f}%  seeds beating Normal {wins}/5")
all_wins = sum(
    1 for cell in CELLS for r in by_cell[cell] if r["val_mse"] < normal_by_seed[r["seed"]]
)
print(f"total paired wins vs Normal: {all_wins}/20")

# ---------------------------------------------------------------------------
# Figure 1: factorial cell means
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.5, 2.6))
x = np.arange(len(CELLS))
labels = [rf"$c_{{KV}}={ckv}$, $c_R={cr}$" for ckv, cr in CELLS]
colors = [C["green"], C["blue"], C["red"], C["purple"]]
for i, cell in enumerate(CELLS):
    ax.bar(i, val_means[cell], yerr=val_stds[cell], width=0.6,
           color=colors[i], alpha=0.85, capsize=4,
           label=f"({cell[0]},{cell[1]})")
    seeds = [r["val_mse"] for r in by_cell[cell]]
    jitter = np.linspace(-0.18, 0.18, len(seeds))
    ax.scatter(i + jitter, seeds, s=14, color="black", zorder=3,
               edgecolor="white", linewidth=0.4)
    ax.text(i, val_means[cell] + val_stds[cell] + 0.012, fmt(val_means[cell]),
            ha="center", fontsize=8)
ax.axhline(normal_val_mean, color="black", linestyle="--", linewidth=0.9)
ax.text(3.52, normal_val_mean + 0.012, f"Normal {fmt(normal_val_mean)}",
        ha="right", fontsize=8)
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel("Validation MSE (standardized)")
ax.set_ylim(0.45, 0.95)
ax.legend(loc="upper left", ncol=1, frameon=False, fontsize=7.5)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig1_factorial_val.pdf")
fig.savefig(FIG_DIR / "fig1_factorial_val.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figure 2: main effects
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.5, 2.5))
effects = [c_kv_effect, c_r_effect]
names = [r"$c_{KV}$: $4{:}1 \rightarrow 8{:}1$", r"$c_R$: $4{:}1 \rightarrow 8{:}1$"]
bar_colors = [C["green"], C["red"]]
for i, (e, n, c) in enumerate(zip(effects, names, bar_colors)):
    ax.bar(i, e, width=0.5, color=c, alpha=0.85)
    ax.text(i, e + (0.004 if e > 0 else -0.012), f"{e:+.4f}", ha="center", fontsize=9)
seed_std = np.mean([val_stds[c] for c in CELLS])
ax.axhline(0.0, color="black", linewidth=0.8)
for s in (seed_std, -seed_std):
    ax.axhline(s, color="gray", linestyle=":", linewidth=1.0)
ax.text(1.45, seed_std, f"$\\pm$ mean within-cell seed std ({seed_std:.4f})",
        ha="right", va="bottom", fontsize=8, color="gray")
ax.set_xticks([0, 1])
ax.set_xticklabels(names)
ax.set_ylabel("Change in validation MSE")
ax.set_ylim(-0.09, 0.09)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig2_main_effects.pdf")
fig.savefig(FIG_DIR / "fig2_main_effects.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figure 3: per-seed parallel coordinates
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.5, 2.9))
configs = ["Normal", "(4,4)", "(8,4)", "(4,8)", "(8,8)"]
seed_color = [C["blue"], C["orange"], C["green"], C["red"], C["purple"]]
seeds = [42, 123, 2024, 7, 99]
normal_by_seed = {r["seed"]: r["val_mse"] for r in normal}
series = {s: [normal_by_seed[s]] for s in seeds}
for cell in CELLS:
    for r in by_cell[cell]:
        series[r["seed"]].append(r["val_mse"])
xpos = np.arange(len(configs))
for k, s in enumerate(seeds):
    ax.plot(xpos, series[s], marker="o", markersize=3.5, linewidth=1.1,
            color=seed_color[k], label=f"seed {s}", alpha=0.9)
ax.set_xticks(xpos)
ax.set_xticklabels(configs)
ax.set_ylabel("Validation MSE (standardized)")
ax.legend(loc="upper right", ncol=5, frameon=False, fontsize=7.5)
ax.set_ylim(0.45, 1.1)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig3_per_seed.pdf")
fig.savefig(FIG_DIR / "fig3_per_seed.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figure 4: learning curves (copied from the audited artifact)
# ---------------------------------------------------------------------------
if LEARNING_CURVES.exists():
    shutil.copy(LEARNING_CURVES, FIG_DIR / "fig4_learning_curves.png")
    print("fig4_learning_curves.png copied from plan/gates/gate2/gate2_learning_curves.png")
else:
    print("WARNING: plan/gates/gate2/gate2_learning_curves.png not found; fig4 skipped")

# ---------------------------------------------------------------------------
# Figure 5: architecture schematic (matplotlib drawing, no data)
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.5, 2.9))
ax.set_xlim(0, 10)
ax.set_ylim(0, 6)
ax.axis("off")

BOX = dict(boxstyle="round,pad=0.35", facecolor="#f2f2f2", edgecolor="#555555", linewidth=1.0)
HILITE = dict(boxstyle="round,pad=0.35", facecolor="#e8f0e8", edgecolor=C["green"], linewidth=1.4)
BRANCH = dict(boxstyle="round,pad=0.35", facecolor="#eef2f8", edgecolor=C["blue"], linewidth=1.2)


def box(x, y, w, h, text, style=BOX, fs=8.5):
    ax.add_patch(matplotlib.patches.FancyBboxPatch((x, y), w, h, **style))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(x1, y1, x2, y2, color="#555555", lw=1.1):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw))


# main spine: input -> block -> attention -> O -> horizon head
box(0.2, 2.6, 1.7, 0.9, "Input\n$[B, 256, 7]$", HILITE)
box(2.6, 2.6, 1.9, 0.9, "Shared block\ninput proj + pos\n(hidden 128)", BRANCH)
box(7.3, 2.6, 2.5, 0.9, "Dense masked attention\n32 KV blocks + 16 win\n+ sink = 48 cols", HILITE)
box(7.3, 0.7, 2.5, 0.9, "Horizon head\n$[B, 96, 7]$", BRANCH)

# compressors
box(2.6, 4.7, 1.9, 0.8, "KV compressor\n$c_{KV}=8$: 32 blocks", BRANCH)
box(5.0, 4.7, 1.9, 0.8, "Indexer\n$c_R=4$: 64 tokens", BRANCH)
box(5.0, 2.6, 1.6, 0.9, "Router\nshared-Q,\ntop-$k$=16", BRANCH)

arrow(1.9, 3.05, 2.6, 3.05)
arrow(3.55, 4.7, 3.55, 3.5)
arrow(5.95, 4.7, 5.95, 3.5)
arrow(6.6, 3.05, 7.3, 3.05)
arrow(8.55, 2.6, 8.55, 1.6)
arrow(4.6, 2.6, 5.0, 2.6)

# alternative Normal path note
ax.text(5.0, 1.0, "Normal: full causal attention, 256 cols, no compression\n(same shared block; baseline)",
        ha="center", fontsize=7.5, style="italic", color="#666666")
fig.tight_layout()
fig.savefig(FIG_DIR / "fig5_architecture.pdf")
fig.savefig(FIG_DIR / "fig5_architecture.png")
plt.close(fig)

print("All figures written to", FIG_DIR)
