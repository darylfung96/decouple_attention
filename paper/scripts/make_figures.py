#!/usr/bin/env python3
"""Regenerate all paper figures from the audited result manifests.

Reads:
  plan/gates/gate2/gate2_results.jsonl        (20 factorial runs)
  plan/gates/baseline/baseline_normal_results.jsonl  (5 Normal baseline runs)
  plan/gates/gate2/gate2_learning_curves.png  (copied, not regenerated)
  plan/gates/gate3/results/*.jsonl            (180 cross-dataset runs)

Writes into ../figures/:
  fig1_factorial_val.{pdf,png}   factorial cell means + std + seed points
  fig2_main_effects.{pdf,png}    c_KV / c_R main effects vs seed noise
  fig3_per_seed.{pdf,png}        per-seed parallel coordinates
  fig4_learning_curves.png       copy of the audited learning-curve plot
  fig5_architecture.{pdf,png}    architecture schematic
  fig6_dataset_coverage.{pdf,png}  per-dataset Delta-val vs Normal (Gate 3)

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
import sys
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
GATE7_JSONL = PLAN_DIR / "gates" / "gate7_seeds" / "results" / "gate7.jsonl"
NORMAL_JSONL = PLAN_DIR / "gates" / "baseline" / "baseline_normal_results.jsonl"
LEARNING_CURVES = PLAN_DIR / "gates" / "gate2" / "gate2_learning_curves.png"
GATE3_DIR = PLAN_DIR / "gates" / "gate3" / "results"

# v2 mode (post-mapping-fix): `python make_figures.py --v2` substitutes the
# Gate15 re-run rows for the three fixed cells and the suite-Flat column.
# Old manifests are never modified; v2 reads them plus gate15 results.
V2 = "--v2" in sys.argv
G15F_JSONL = PLAN_DIR / "gates" / "gate15_rerun" / "results" / "factorial.jsonl"
G15S_DIR = PLAN_DIR / "gates" / "gate15_rerun" / "results" / "suite_flat"
V2_FIXED_CELLS = [(4, 4), (4, 8), (8, 8)]

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
# Shared analytic model (frozen geometry), used by Figures 12 and 13. Each
# formula is verified for exact equality against the audited component MAC
# accounts at L=256 inside the figure functions; no new runs are performed.
# ---------------------------------------------------------------------------
H, DH, D = 4, 32, 128          # heads, head dim, hidden size (frozen)
W, F, HOR = 16, 7, 96          # window, features, horizon (frozen)


def attn_normal(L):
    return 2 * H * L * L * DH


def attn_cell(L, ckv):
    return 2 * H * L * (L // ckv + W + 1) * DH


def router_term(L, cr):
    """As executed: every head scores every index token.

    The routing query is the main multi-head query ([B, H, S, d_head]) and the
    index stream is [B, 1, n_idx, d_head], so the score matmul is
    [B, H, S, d_head] @ [B, 1, d_head, n_idx]: H * d_head = d MACs per
    (query, index-token) pair. Tensor shapes verified in
    plan/gates/gate20_accounting/router_accounting_audit.py (Q1 review R8);
    the earlier charge of d_head per pair (one head) is superseded.
    """
    return L * (L // cr) * H * DH


def compress_term(L):
    return 2 * L * D * 64 + 2 * L * D * DH


def rest_exact(L, o_rank):
    wrapper = L * F * D + 2 * L * D * (4 * D) + D * (HOR * F)
    q_lora = L * D * 64 + L * 64 * (H * DH)
    kv = L * D * DH
    o_proj = L * (H * DH // 4) * (4 * o_rank) + L * (4 * o_rank) * D
    return wrapper + q_lora + kv + o_proj


def path_normal(L):
    return attn_normal(L)


def path_cell(L, ckv, cr):
    return attn_cell(L, ckv) + router_term(L, cr) + compress_term(L)


def s_attn(L, ckv, cr):
    return 1.0 - path_cell(L, ckv, cr) / path_normal(L)


def s_net(L, d, ckv, cr):
    """Whole-layer projection at width d: dense vs compressed attention
    plus 12 d^2 non-attention MACs per token (q/k/v/o 4 d^2, MLP 8 d^2);
    the family's fixed compressor (rank 64) and indexer (32-dim) are held."""
    a_n = 2 * d * L
    a_c = 2 * d * (L // ckv + W + 1) + d * (L // cr) + 2 * d * (64 + DH)
    return (a_n - a_c) / (a_n + 12 * d * d)


# ---------------------------------------------------------------------------
# Figure 12: structural scaling forecast + energy projection (analytic).
# Standalone:  python scripts/make_figures.py --scaling
#
# The figure extends the measured operating point (L=256) to 128k-token
# contexts using the audited component accounting only; it performs no new
# runs. Every analytic term below is checked for EXACT equality against the
# audited per-component MAC accounts at L=256 (the assertion below), and the
# measured latency ratios are used solely as directional anchors.
# ---------------------------------------------------------------------------
SCALING = "--scaling" in sys.argv


def make_fig12():

    # --- verification against the audited component accounts (exact) --------
    # exact anchors are the gate20-corrected accounts (gate5's router row
    # charged one head per comparison; see gate20 accounting audit); gate5 is
    # still the source of the measured latency sweep used below
    g5 = json.load(open(PLAN_DIR / "gates" / "gate5" / "gate5_results.json"))
    g20 = json.load(open(PLAN_DIR / "gates" / "gate20_accounting" /
                         "router_accounting_audit.json"))
    audited_totals = {k: v["total"] for k, v in g20["components_L256"].items()}
    checks = {
        "Normal": (path_normal(256) + rest_exact(256, 128), "Normal"),
        "CSA": (path_cell(256, 4, 4) + rest_exact(256, 64), "CSA"),
        "DRRA": (path_cell(256, 8, 4) + rest_exact(256, 64), "DRRA"),
    }
    for label, (calc, key) in checks.items():
        audited = audited_totals[key]
        assert calc == audited, f"fig12 {label}: analytic {calc} != audited {audited}"
        print(f"fig12 verify {label}: analytic total {calc / 1e6:.2f} M MACs/seq "
              f"== audited {audited / 1e6:.2f} M/seq (exact)")

    cells = [(4, 4), (8, 4), (16, 4), (32, 4)]
    cell_colors = {(4, 4): C["orange"], (8, 4): C["blue"],
                   (16, 4): C["green"], (32, 4): C["purple"]}
    cell_labels = {(4, 4): "(4,4)", (8, 4): "(8,4)",
                   (16, 4): "(16,4)", (32, 4): "(32,4)"}
    anchors = [(4096, "4k"), (8192, "8k"), (32768, "32k"), (131072, "128k")]
    Ls = np.geomspace(256, 131072, 400)

    fig, axes = plt.subplots(2, 2, figsize=(6.9, 4.9))

    def anchor_lines(ax):
        for a, t in anchors:
            ax.axvline(a, color="#bbbbbb", linewidth=0.6, linestyle=":", zorder=0)
            ax.text(a, 0.985, t, transform=ax.get_xaxis_transform(),
                    ha="center", va="top", fontsize=6.3, color="#888888")

    # (a) tokens per query -------------------------------------------------
    ax = axes[0, 0]
    ax.plot(Ls, Ls, color=C["red"], lw=1.2, label="Normal (dense)")
    for cell in cells:
        ax.plot(Ls, Ls / cell[0] + W + 1, color=cell_colors[cell], lw=1.1,
                label=cell_labels[cell])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Context length $L$ (tokens)")
    ax.set_ylabel("Softmax columns per query")
    ax.legend(frameon=False, fontsize=6.6, loc="upper left", handlelength=1.3)
    anchor_lines(ax)

    # (b) attention-path work savings vs L ----------------------------------
    ax = axes[0, 1]
    ref = np.array([path_normal(L) for L in Ls], dtype=float)
    for cell in cells:
        ckv, cr = cell
        curve = np.array([1.0 - path_cell(L, ckv, cr) / ref[i]
                          for i, L in enumerate(Ls)])
        ax.plot(Ls, 100 * curve, color=cell_colors[cell], lw=1.2,
                label=cell_labels[cell])
        asym = 100 * (1.0 - (1.0 / ckv + 1.0 / (2 * cr)))
        ax.axhline(asym, color=cell_colors[cell], lw=0.7, ls="--", alpha=0.65)
    ax.set_xscale("log")
    ax.set_xlabel("Context length $L$ (tokens)")
    ax.set_ylabel("Attention-path work saved (%)")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=6.6, loc="lower right", handlelength=1.3)
    anchor_lines(ax)

    # (c) whole-layer savings by width + measured anchors -------------------
    ax = axes[1, 0]
    from matplotlib.lines import Line2D

    widths = [128, 512, 1024, 4096]
    wcolors = [C["red"], C["orange"], C["green"], C["blue"]]
    cell_styles = ((8, 4, "-", 1.2, "(8,4)"),
                   (16, 4, (0, (4, 2)), 0.9, "(16,4)"),
                   (32, 4, (0, (1.5, 1.5)), 0.9, "(32,4)"))
    for d, col in zip(widths, wcolors):
        for ckv, cr, ls, lw, _ in cell_styles:
            ax.plot(Ls, 100 * np.array([s_net(L, d, ckv, cr) for L in Ls]),
                    color=col, lw=lw, ls=ls)
    for B, mk in (("32", "D"), ("1", "s")):
        lat = g5["l_scale"][B]["latency"]
        xs, ys = [], []
        for Lstr, md in lat.items():
            if "Normal" in md and "DRRA" in md:
                sav = 100 * (1 - md["DRRA"]["mean_ms_per_batch"]
                             / md["Normal"]["mean_ms_per_batch"])
                if sav >= 0:
                    xs.append(int(Lstr))
                    ys.append(sav)
        ax.plot(xs, ys, linestyle="none", marker=mk, ms=3.8, mfc="none",
                mec="black", mew=0.8)
    leg_w = ax.legend(handles=[Line2D([], [], color=c, lw=1.2, label=f"$d$={d}")
                              for d, c in zip(widths, wcolors)],
                      frameon=False, fontsize=6.6, loc="upper left",
                      handlelength=1.3)
    ax.add_artist(leg_w)
    ax.legend(handles=[
        Line2D([], [], color="#333333", lw=1.2, ls="-", label="(8,4)"),
        Line2D([], [], color="#333333", lw=0.9, ls=(0, (4, 2)), label="(16,4)"),
        Line2D([], [], color="#333333", lw=0.9, ls=(0, (1.5, 1.5)), label="(32,4)")],
        frameon=False, fontsize=6.4, loc="lower right", handlelength=1.3)
    ax.set_xscale("log")
    ax.set_xlabel("Context length $L$ (tokens)")
    ax.set_ylabel("Whole-layer work saved (%)")
    ax.set_ylim(0, 100)
    anchor_lines(ax)

    # (d) asymptotic savings map over the design plane ----------------------
    ax = axes[1, 1]
    ckvs = [2, 4, 8, 16, 32, 64]
    crs = [2, 4, 8]
    grid = np.array([[100 * (1 - (1.0 / ckv + 1.0 / (2 * cr)))
                      for ckv in ckvs] for cr in crs])
    im = ax.imshow(grid, cmap="viridis", origin="lower", aspect="auto",
                   vmin=40, vmax=100)
    ax.set_xticks(range(len(ckvs)))
    ax.set_xticklabels([str(c) for c in ckvs])
    ax.set_yticks(range(len(crs)))
    ax.set_yticklabels([str(c) for c in crs])
    ax.set_xlabel("KV compression rate $c_{KV}$")
    ax.set_ylabel("Routing resolution $c_R$")
    for i in range(len(crs)):
        for j in range(len(ckvs)):
            v = grid[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.5,
                    color="white" if v < 78 else "black")
    tested = {(4, 4), (8, 4), (4, 8), (8, 8), (16, 4), (32, 4)}
    for ckv, cr in tested:
        ax.plot(ckvs.index(ckv), crs.index(cr), marker="s", ms=8.5,
                mfc="none", mec="white", mew=1.1)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label("% saved (limit)", fontsize=7)
    cb.ax.tick_params(labelsize=6.5)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig12_scaling_forecast.pdf")
    fig.savefig(FIG_DIR / "fig12_scaling_forecast.png")
    plt.close(fig)

    # --- printed forecast table (source for the paper's numbers) -----------
    print("fig12: attention-path savings vs Normal (%)")
    print("    L      " + "  ".join(f"({ckv},{cr})" for ckv, cr in cells))
    for L in (256, 1024, 4096, 8192, 32768, 131072):
        print(f"  {L:>6}  " + "  ".join(
            f"{100 * s_attn(L, ckv, cr):>7.1f}" for ckv, cr in cells))
    print("  asymptote  " + "  ".join(
        f"{100 * (1 - (1.0 / ckv + 1.0 / (2 * cr))):>7.1f}"
        for ckv, cr in cells))
    print("fig12: whole-layer savings at L=32768 (%)")
    for d in widths:
        print(f"  d={d:>5}: DRRA {100 * s_net(32768, d, 8, 4):>5.1f}   "
              f"(32,4) {100 * s_net(32768, d, 32, 4):>5.1f}")
    print("fig12: whole-layer savings, study backbone (d=128, DRRA)")
    for L in (2048, 4096, 32768):
        print(f"  L={L:>6}: {100 * s_net(L, 128, 8, 4):>5.1f}")
    print("fig12: sensitivity at L=32768 (DRRA (8,4))")
    core = attn_cell(32768, 8)
    aux = router_term(32768, 4) + compress_term(32768)
    ref32 = path_normal(32768)
    for lam in (0.5, 1.0, 2.0):
        print(f"  auxiliary weight x{lam}: "
              f"{100 * (1 - (core + lam * aux) / ref32):.1f}% saved")
    for h in (1,):
        print(f"  single-head indexer analogue: asymptote "
              f"{100 * (1 - (1 / 8 + 1 / (2 * h * 4))):.1f}% saved")

    # directional validation against the measured latency ratios
    def _rank(x):
        order = np.argsort(x)
        r = np.empty(len(x), dtype=float)
        r[order] = np.arange(1, len(x) + 1)
        return r

    def _spearman(a, b):
        return float(np.corrcoef(_rank(np.asarray(a, float)),
                                 _rank(np.asarray(b, float)))[0, 1])

    def _pearson(a, b):
        return float(np.corrcoef(np.asarray(a, float),
                                 np.asarray(b, float))[0, 1])

    for B in ("1", "32"):
        lat = g5["l_scale"][B]["latency"]
        pts = []
        for Lstr, md in lat.items():
            if all(v in md for v in ("Normal", "Flat", "DRRA")):
                L = int(Lstr)
                pts.append((L, "Normal", path_normal(L)))
                pts.append((L, "Flat", path_cell(L, 4, 4)))
                pts.append((L, "DRRA", path_cell(L, 8, 4)))
        t = [lat[str(L)][v]["mean_ms_per_batch"] for L, v, _ in pts]
        w = [pc for _, _, pc in pts]
        print(f"fig12 validate batch {B}: n={len(pts)}  "
              f"Spearman(latency, attention-path work) = {_spearman(t, w):.3f}")
    for B in ("1", "32"):
        lat = g5["l_scale"][B]["latency"]
        wr, tr = [], []
        for Lstr, md in lat.items():
            if "Normal" in md and "DRRA" in md:
                L = int(Lstr)
                wr.append(path_cell(L, 8, 4) / path_normal(L))
                tr.append(md["DRRA"]["mean_ms_per_batch"]
                          / md["Normal"]["mean_ms_per_batch"])
        print(f"fig12 validate batch {B}: paired DRRA/Normal work-vs-time "
              f"ratio Pearson r = {_pearson(wr, tr):.3f} (n={len(wr)})")


def make_fig13():
    L = 2048
    # same exact anchors as Figure 12: the gate20-corrected accounts
    g20 = json.load(open(PLAN_DIR / "gates" / "gate20_accounting" /
                         "router_accounting_audit.json"))
    audited_totals = {k: v["total"] for k, v in g20["components_L256"].items()}
    checks = {
        "Normal": (path_normal(256) + rest_exact(256, 128), "Normal"),
        "CSA": (path_cell(256, 4, 4) + rest_exact(256, 64), "CSA"),
        "DRRA": (path_cell(256, 8, 4) + rest_exact(256, 64), "DRRA"),
    }
    for label, (calc, key) in checks.items():
        audited = audited_totals[key]
        assert calc == audited, f"fig13 {label}: analytic {calc} != audited {audited}"

    dense = path_normal(L) / L + 12 * D * D          # per-token
    configs = [("Normal", None), ("(4,4)", (4, 4)), ("(8,4)", (8, 4))]
    core, aux, floor = [], [], []
    for _, cell in configs:
        if cell is None:
            c, a = float(path_normal(L)) / L, 0.0
        else:
            c = float(attn_cell(L, cell[0])) / L
            a = float(router_term(L, cell[1]) + compress_term(L)) / L
        core.append(100.0 * c / dense)
        aux.append(100.0 * a / dense)
        floor.append(100.0 * 12 * D * D / dense)

    fig, ax = plt.subplots(figsize=(3.5, 2.9))
    x = np.arange(len(configs))
    bw = 0.52
    ax.bar(x, core, bw, color=C["blue"], label="Attention core")
    ax.bar(x, aux, bw, bottom=core, color="#A8C4E0", label="Router + compressor")
    bottoms = np.array(core) + np.array(aux)
    ax.bar(x, floor, bw, bottom=bottoms, color="#D9D9D9", label="Projections + MLP")
    for xi, ((name, cell), c, a, f) in enumerate(zip(configs, core, aux, floor)):
        for val, bottom, ink in ((c, 0.0, "white"), (a, c, "#333333"),
                                 (f, c + a, "#333333")):
            if val >= 5.0:
                ax.text(xi, bottom + val / 2, f"{val:.1f}", ha="center",
                        va="center", fontsize=6.7, color=ink)
        total = c + a + f
        saved = 0.0 if cell is None else 100 * s_net(L, D, cell[0], cell[1])
        tag = "dense" if total > 99.5 else f"{saved:.1f}% saved"
        ax.text(xi, total + 1.5, tag, ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels([name for name, _ in configs], fontsize=8)
    ax.set_ylabel("Per-token work (% of dense)")
    ax.set_ylim(0, 114)
    ax.legend(frameon=False, fontsize=6.6, loc="upper right", handlelength=1.0,
              borderaxespad=0.4)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig13_energy_composition.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig13_energy_composition.png", bbox_inches="tight")
    plt.close(fig)

    # printed checks (source for the caption's numbers)
    print(f"fig13: per-token work at L={L} (% of dense)")
    for (name, cell), c, a, f in zip(configs, core, aux, floor):
        att = 0.0 if cell is None else 100 * s_attn(L, cell[0], cell[1])
        print(f"  {name:>10}: core {c:5.1f}  aux {a:4.1f}  fixed {f:5.1f}  "
              f"total {c + a + f:5.1f}  saved {100 - (c + a + f):5.1f}  "
              f"attention-path saved {att:5.1f}")


if SCALING:
    make_fig12()
    make_fig13()
    raise SystemExit(0)


# ---------------------------------------------------------------------------
# Data — 25 paired seeds: the 5 pre-registered (gate2 + baseline manifests)
# plus the 20-seed power extension (gate7, byte-identical protocol)
# ---------------------------------------------------------------------------
gate2 = load_jsonl(GATE2_JSONL)
gate7 = load_jsonl(GATE7_JSONL)
normal = load_jsonl(NORMAL_JSONL)

by_seed: dict[tuple[int, int], dict[int, dict]] = {cell: {} for cell in CELLS}
for row in gate2:
    by_seed[(row["c_kv"], row["c_r"])][row["seed"]] = row
for row in gate7:
    if row["cell"] is not None:
        by_seed[tuple(row["cell"])][row["seed"]] = row
normal_by_seed: dict[int, dict] = {r["seed"]: r for r in normal}
for row in gate7:
    if row["cell"] is None:
        normal_by_seed[row["seed"]] = row

if V2:
    # Substitute fixed-mapping re-runs for the three broken cells.
    g15 = load_jsonl(G15F_JSONL)
    for cell in V2_FIXED_CELLS:
        by_seed[cell] = {}
    for row in g15:
        by_seed[(row["c_kv"], row["c_r"])][row["seed"]] = row
    print(f"v2 mode: substituted {len(g15)} Gate15 rows "
          f"for cells {V2_FIXED_CELLS} (kept (8,4)+Normal)")

val_means = {}
val_stds = {}
test_means = {}
train_means = {}
for cell in CELLS:
    seeds = sorted(by_seed[cell])
    assert len(seeds) == 25, f"cell {cell}: expected 25 seeds, got {len(seeds)}"
    vals = np.array([by_seed[cell][s]["val_mse"] for s in seeds], dtype=float)
    tests = np.array([by_seed[cell][s]["test_mse"] for s in seeds], dtype=float)
    trains = np.array([by_seed[cell][s]["final_train_mse"] for s in seeds], dtype=float)
    val_means[cell] = vals.mean()
    val_stds[cell] = vals.std(ddof=1)
    test_means[cell] = tests.mean()
    train_means[cell] = trains.mean()

normal_seeds = sorted(normal_by_seed)
assert len(normal_seeds) == 25, f"Normal: expected 25 seeds, got {len(normal_seeds)}"
normal_vals = np.array([normal_by_seed[s]["val_mse"] for s in normal_seeds], dtype=float)
normal_tests = np.array([normal_by_seed[s]["test_mse"] for s in normal_seeds], dtype=float)
normal_val_mean = normal_vals.mean()
normal_val_std = normal_vals.std(ddof=1)
normal_test_mean = normal_tests.mean()

# --- verification against audited summaries -------------------------------
print("== verification vs audited summaries (n=25: gate2+baseline + gate7) ==")
print(f"Normal   val {fmt(normal_val_mean)} ± {fmt(normal_val_std)}  test {fmt(normal_test_mean)}"
      f"   [expect 0.8389 ± 0.0814 / 1.0804]")
_expect = {(4, 4): 0.6575, (8, 4): 0.6190, (4, 8): 0.6994, (8, 8): 0.6347}
if V2:
    _expect = {(4, 4): 0.6148, (8, 4): 0.6190, (4, 8): 0.6810, (8, 8): 0.6128}
for cell in CELLS:
    print(f"cell {cell}: val {fmt(val_means[cell])} ± {fmt(val_stds[cell])}  "
          f"test {fmt(test_means[cell])}  train {fmt(train_means[cell])}"
          f"   [expect val {_expect[cell]}]")

# main effects
c_kv_effect = (val_means[(8, 4)] + val_means[(8, 8)]) / 2 - (val_means[(4, 4)] + val_means[(4, 8)]) / 2
c_r_effect = (val_means[(4, 8)] + val_means[(8, 8)]) / 2 - (val_means[(4, 4)] + val_means[(8, 4)]) / 2
print(f"main effect c_KV = {c_kv_effect:+.4f}   [expect {'-0.0320' if V2 else '-0.0516'}]")
print(f"main effect c_R  = {c_r_effect:+.4f}   [expect {'+0.0300' if V2 else '+0.0288'}]")

# per-seed consistency of effects (paired by seed, n=25)
n_kv_improves = 0
for s in normal_seeds:
    for cr in (4, 8):
        if by_seed[(8, cr)][s]["val_mse"] < by_seed[(4, cr)][s]["val_mse"]:
            n_kv_improves += 1
n_r_worsens = 0
for s in normal_seeds:
    for ckv in (4, 8):
        if by_seed[(ckv, 8)][s]["val_mse"] > by_seed[(ckv, 4)][s]["val_mse"]:
            n_r_worsens += 1
print(f"per-seed consistency: c_KV improves {n_kv_improves}/50, c_R worsens {n_r_worsens}/50"
      f"   [expect {'37/50, 31/50' if V2 else '38/50, 34/50'}]")

# deltas vs Normal (mean and per-seed, all 100 compressed runs + Normal)
print("-- deltas vs Normal --")
for cell in CELLS:
    d = (val_means[cell] - normal_val_mean) / normal_val_mean * 100
    dt = (test_means[cell] - normal_test_mean) / normal_test_mean * 100
    wins = sum(1 for s in normal_seeds
               if by_seed[cell][s]["val_mse"] < normal_by_seed[s]["val_mse"])
    print(f"cell {cell}: dval {d:+.2f}%  dtest {dt:+.2f}%  seeds beating Normal {wins}/25")
all_wins = sum(
    1 for cell in CELLS for s in normal_seeds
    if by_seed[cell][s]["val_mse"] < normal_by_seed[s]["val_mse"]
)
print(f"total paired wins vs Normal: {all_wins}/100")

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
    seeds = [by_seed[cell][s]["val_mse"] for s in sorted(by_seed[cell])]
    jitter = np.linspace(-0.18, 0.18, len(seeds))
    ax.scatter(i + jitter, seeds, s=14, color="black", zorder=3,
               edgecolor="white", linewidth=0.4)
    _top = max(val_means[cell] + val_stds[cell], max(seeds))
    _lab = _top + 0.015
    if _top < normal_val_mean and _lab + 0.045 > normal_val_mean - 0.01:
        _lab = normal_val_mean + 0.05
    ax.text(i, _lab, fmt(val_means[cell]), ha="center", va="bottom", fontsize=8)
ax.axhline(normal_val_mean, color="black", linestyle="--", linewidth=0.9)
if V2:
    # Exploratory cells as starred side bars (never part of confirmatory stats).
    import json as _json2
    _exp = {"(16,4)*": "gate18_d5", "(32,4)*": "gate19_324"}
    for j, (lab, gate) in enumerate(_exp.items()):
        _rows = [_json2.loads(l) for l in
                 open(PLAN_DIR / "gates" / gate / "results" / "etth1.jsonl")]
        _vals = np.array([r["val_mse"] for r in _rows], dtype=float)
        _i = len(CELLS) + j
        ax.bar(_i, _vals.mean(), yerr=_vals.std(ddof=1), width=0.6,
               color="gray", alpha=0.55, capsize=4, label=lab)
        _jit = np.linspace(-0.18, 0.18, len(_vals))
        ax.scatter(_i + _jit, _vals, s=14, color="black", zorder=3,
                   edgecolor="white", linewidth=0.4)
        _top = max(_vals.mean() + _vals.std(ddof=1), _vals.max())
        _lab = _top + 0.015
        if _top < normal_val_mean and _lab + 0.045 > normal_val_mean - 0.01:
            _lab = normal_val_mean + 0.05
        ax.text(_i, _lab, fmt(_vals.mean()), ha="center", va="bottom", fontsize=8)
    x = np.arange(len(CELLS) + 2)
    labels = labels + ["$(16,4)$*", "$(32,4)$*"]
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel("Validation MSE (standardized)")
ax.set_ylim(0.45, 1.18)
ax.legend(loc="upper left", ncol=2, frameon=False, fontsize=7.5,
          borderaxespad=0.3)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig1_factorial_val.pdf")
fig.savefig(FIG_DIR / "fig1_factorial_val.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figure 2: interaction (conditional effects) + main effects
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.8),
                         gridspec_kw={"width_ratios": [1.0, 0.95]})
ax = axes[0]
for cr, col, mk in ((4, C["blue"], "o"), (8, C["red"], "s")):
    ys = [val_means[(4, cr)], val_means[(8, cr)]]
    es = [val_stds[(4, cr)], val_stds[(8, cr)]]
    ax.errorbar([0, 1], ys, yerr=es, color=col, marker=mk, capsize=3,
                lw=1.3, ms=4.5,
                label=rf"Routing $c_R$: {'fine' if cr == 4 else 'coarse'} ({cr}:1)")
ax.set_xticks([0, 1])
ax.set_xticklabels(["4:1", "8:1"])
ax.set_xlabel(r"KV-cache compression $c_{KV}$ (fine $\rightarrow$ coarse)")
ax.set_ylabel("Validation MSE (lower is better)")
ax.set_ylim(0.50, 0.80)
ax.set_xlim(-0.18, 1.18)
ax.set_title("Error for each compression setting", fontsize=8.5)
ax.legend(frameon=False, fontsize=7.5, loc="upper right")

ax = axes[1]
effects = [c_kv_effect, c_r_effect]
names = ["KV cache\n4:1 \u2192 8:1", "Routing\n4:1 \u2192 8:1"]
bar_colors = [C["green"], C["red"]]
for i, (e, c) in enumerate(zip(effects, bar_colors)):
    ax.bar(i, e, width=0.5, color=c, alpha=0.85)
    _lab = f"{e:+.4f}" + ("  (worse)" if e > 0 else "  (better)")
    ax.text(i, e + (0.006 if e > 0 else -0.014), _lab, ha="center",
            va="bottom" if e > 0 else "top", fontsize=8)
ax.axhline(0.0, color="black", linewidth=0.8)
ax.set_xticks([0, 1])
ax.set_xticklabels(names)
ax.set_ylabel("Change in validation MSE")
ax.set_ylim(-0.06, 0.06)
ax.set_title("Average effect of each setting", fontsize=8.5)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig2_main_effects.pdf")
fig.savefig(FIG_DIR / "fig2_main_effects.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figure 4 (formerly 5): architecture schematic.
# REPLACED BY HAND-DRAWN FIGURE (user, 2026-09-05): the user supplied their
# own fig5_architecture.png (parallel-branch topology); it is converted to
# PDF losslessly (img2pdf) and this script MUST NOT overwrite it. The
# matplotlib schematic below is kept only as a commented fallback.
# Topology note (verified against attention.py forward() and DSV4 §2.3.1):
# the KV compressor and the indexer are PARALLEL branches consuming the same
# hidden states; the router scores index tokens and top-k-selects among KV
# blocks; dense masked attention consumes both branches. Earlier version drew
# a linear chain (compressor → indexer → router) — corrected 2026-09-03.
# ---------------------------------------------------------------------------
FIG5_PNG = FIG_DIR / "fig5_architecture.png"
if not FIG5_PNG.exists():
    raise SystemExit(
        "fig5_architecture.png is missing — it is user-supplied and NOT "
        "regenerated by this script. Restore it from the repository before "
        "re-running (its PDF is img2pdf-converted from the PNG).")

import subprocess
import sys as _sys


def _ensure_fig5_pdf():
    """Convert the user-supplied PNG to the PDF that method.tex includes.
    Skips when the PDF is newer than the PNG (idempotent)."""
    pdf = FIG_DIR / "fig5_architecture.pdf"
    if pdf.exists() and pdf.stat().st_mtime >= FIG5_PNG.stat().st_mtime:
        return
    r = subprocess.run([_sys.executable, "-c",
                        "import img2pdf,sys; open(sys.argv[1],'wb')"
                        ".write(img2pdf.convert(sys.argv[2]))",
                        str(pdf), str(FIG5_PNG)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"img2pdf conversion failed:\n{r.stderr}")
    print("fig5_architecture.pdf regenerated from user-supplied PNG (img2pdf)")


_ensure_fig5_pdf()

if False:  # commented-out matplotlib fallback (kept for reference)
    fig, ax = plt.subplots(figsize=(6.9, 3.1))
    ax.set_xlim(0, 11.2)
    ax.set_ylim(0, 6.2)
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


    # main spine: input -> block -> attention -> horizon head
    box(0.1, 2.3, 1.55, 0.95, "Input\n$[B, 256, 7]$", HILITE)
    box(1.95, 2.3, 1.8, 0.95, "Shared block\ninput proj + pos\n(hidden 128)", BRANCH)
    box(9.15, 2.3, 1.95, 1.45, "Dense masked\nattention\n32 KV + 16 win\n+1 sink = 48+1", HILITE)
    box(9.15, 0.45, 1.95, 0.9, "Horizon head\n$[B, 96, 7]$", BRANCH)

    # two PARALLEL branches off the shared block (both read the same hidden states)
    box(4.35, 4.65, 2.6, 0.9, "KV compressor   (branch 1)\n$c_{KV}{=}8$ → 32 KV blocks", BRANCH)
    box(4.35, 3.35, 2.6, 0.9, "Indexer   (branch 2)\n$c_R{=}4$ → 64 index tokens", BRANCH)
    box(7.25, 3.35, 1.7, 0.9, "Router\nscorer + top-$k$\n($k{=}16$, shared-Q)", BRANCH)

    ax.text(3.62, 4.45, "same hidden\nstates →\nparallel", fontsize=6.6,
            color="#666666", ha="center", va="center", style="italic")
    arrow(1.65, 2.77, 1.95, 2.77)
    arrow(3.75, 3.05, 4.35, 4.85)          # shared block -> KV compressor
    arrow(3.75, 2.77, 4.35, 3.8)           # shared block -> indexer
    arrow(6.95, 3.8, 7.25, 3.8)            # indexer -> router
    arrow(6.95, 5.1, 9.7, 3.8)             # KV blocks -> attention
    ax.text(8.15, 4.85, "32 KV blocks", fontsize=7, color="#555555", ha="center")
    arrow(8.95, 3.8, 9.15, 3.55)           # router selection -> attention
    ax.text(8.62, 4.18, "top-$k$ selection", fontsize=6.8, color="#555555", ha="center")
    arrow(10.12, 2.3, 10.12, 1.35)         # attention -> horizon head

    # alternative Normal path note
    ax.text(4.6, 1.05, "Normal: full causal attention, 256 cols, no compression\n(same shared block; baseline)",
            ha="center", fontsize=7.5, style="italic", color="#666666")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig5_architecture.pdf")
    fig.savefig(FIG_DIR / "fig5_architecture.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figure 6: cross-dataset coverage (Gate 3) — Delta-val vs Normal per dataset
# ---------------------------------------------------------------------------
DATASET_ORDER = ["etth1", "etth2", "ettm1", "ettm2", "electricity", "traffic",
                 "weather", "exchange", "solar",
                 "syn_sinusoids", "syn_changepoints", "syn_delayedcopy"]
SEEDS = [42, 123, 2024, 7, 99]
VARIANTS = ["Normal", "Flat", "DRRA"]

gate3 = {}
for ds in DATASET_ORDER:
    rows = load_jsonl(GATE3_DIR / f"{ds}.jsonl")
    gate3[ds] = {(r["variant"], r["seed"]): r["val_mse"] for r in rows}
if V2:
    # Overlay fixed-mapping suite-Flat rows (variant recorded as Flat-fix).
    n_over = 0
    for ds in DATASET_ORDER:
        for r in load_jsonl(G15S_DIR / f"{ds}.jsonl"):
            gate3[ds][("Flat", r["seed"])] = r["val_mse"]
            n_over += 1
    print(f"v2 mode: overlaid {n_over} Gate15 suite-Flat rows")


def g3_mean(variant):
    return np.array([np.mean([gate3[ds][(variant, s)] for s in SEEDS])
                     for ds in DATASET_ORDER], dtype=float)


normal_mean = g3_mean("Normal")
flat_delta = (g3_mean("Flat") / normal_mean - 1.0) * 100.0
drra_delta = (g3_mean("DRRA") / normal_mean - 1.0) * 100.0
n_flat_wins = int(np.sum(flat_delta < 0))
n_drra_wins = int(np.sum(drra_delta < 0))
print(f"cross-dataset: DRRA beats Normal on mean val {n_drra_wins}/12, "
      f"Flat {n_flat_wins}/12   [expect 8/12, {'8/12' if V2 else '7/12'}]")

fig, ax = plt.subplots(figsize=(6.5, 2.9))
x = np.arange(len(DATASET_ORDER))
w = 0.38
ax.bar(x - w / 2, flat_delta, width=w, color=C["orange"], alpha=0.85, label="$(4,4)$")
ax.bar(x + w / 2, drra_delta, width=w, color=C["blue"], alpha=0.85, label="$(8,4)$")
ax.axhline(0.0, color="black", linewidth=0.8)
labels = ["ETTh1", "ETTh2", "ETTm1", "ETTm2", "Elec", "Traffic", "Weather",
          "Exchange", "Solar", "syn-sin", "syn-cp", "syn-dc"]
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=7.5)
ax.set_ylabel(r"$\Delta$val vs. Normal (%)")
ax.set_ylim(-52, 12)
ax.legend(loc="lower left", frameon=False, fontsize=7.5)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig6_dataset_coverage.pdf")
fig.savefig(FIG_DIR / "fig6_dataset_coverage.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# Figure 5: batch-size scaling of forward latency (Gate 3 companion)
# Single panel: mean ms per sequence vs batch size.
# ---------------------------------------------------------------------------
LATENCY_SCALE = PLAN_DIR / "gates" / "gate3" / "gate3_latency_scale.json"
if LATENCY_SCALE.exists():
    import json as _json
    scale = _json.load(open(LATENCY_SCALE))
    Bs = sorted(int(k) for k in scale["batches"])
    fig, ax = plt.subplots(figsize=(6.5, 2.7))
    style = {"Normal": C["red"], "Flat": C["orange"], "DRRA": C["blue"]}
    for variant, color in style.items():
        seq = [scale["batches"][str(B)][variant]["ms_per_seq"] for B in Bs]
        ax.plot(Bs, seq, marker="o", markersize=3.5, linewidth=1.1, color=color,
                label={"Flat": "$(4,4)$", "DRRA": "$(8,4)$",
                          "Normal": "Normal"}[variant])
    ax.set_xscale("log")
    ax.set_xticks(Bs)
    ax.set_xticklabels([str(B) for B in Bs], fontsize=7.5)
    ax.set_xlabel("Batch size (windows per forward pass)")
    ax.set_ylabel("Mean latency (ms per sequence)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig7_latency_scale.pdf")
    fig.savefig(FIG_DIR / "fig7_latency_scale.png")
    plt.close(fig)
    b1 = scale["batches"]["1"]
    b256 = scale["batches"]["256"]
    print(f"latency scaling: at B=1, DRRA "
          f"{b1['DRRA']['delta_mean_vs_normal_pct']:+.1f}% vs Normal; at B=256, "
          f"DRRA {b256['DRRA']['delta_mean_vs_normal_pct']:+.1f}% (mean "
          f"{b256['DRRA']['mean_ms_per_batch']:.0f} vs "
          f"{b256['Normal']['mean_ms_per_batch']:.0f} ms/batch)")
else:
    print("WARNING: gate3_latency_scale.json not found; fig7 skipped")


# ---------------------------------------------------------------------------
# Figure 5: sequence-length scaling of forward latency (Gate 5)
# ---------------------------------------------------------------------------
GATE5_RESULTS = PLAN_DIR / "gates" / "gate5" / "gate5_results.json"
if GATE5_RESULTS.exists():
    import json as _json
    g5 = _json.load(open(GATE5_RESULTS))
    for B in ("1", "32"):
        if B not in g5.get("l_scale", {}):
            continue
        lat = g5["l_scale"][B]["latency"]
        Ls = sorted(int(k) for k in lat
                       if all(v in lat[k] for v in ("Normal", "Flat", "DRRA")))
        fig, ax = plt.subplots(figsize=(6.5, 2.6))
        style = {"Normal": C["red"], "Flat": C["orange"], "DRRA": C["blue"]}
        for variant, color in style.items():
            ms = [lat[str(L)][variant]["mean_ms_per_batch"] for L in Ls]
            ax.plot(Ls, ms, marker="o", markersize=3.5, linewidth=1.1,
                    color=color,
                    label={"Flat": "$(4,4)$", "DRRA": "$(8,4)$",
                           "Normal": "Normal"}[variant])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xticks(Ls)
        ax.set_xticklabels([str(L) for L in Ls], fontsize=7.5)
        ax.set_xlabel("Sequence length $L$ (lookback)")
        ax.set_ylabel("Mean latency (ms per batch)")
        slope = g5["l_scale"][B]["loglog_slope"]
        _vname = {"Normal": "Normal", "Flat": "(4,4)", "DRRA": "(8,4)"}
        ax.set_title(f"batch {B}; log-log slopes (L$\\geq$512): " +
                     ", ".join(f"{_vname.get(v, v)} {s:.2f}"
                               for v, s in slope.items()),
                     fontsize=7.5)
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        suffix = "" if B == "32" else f"_b{B}"
        fig.savefig(FIG_DIR / f"fig8_lscale{suffix}.pdf")
        fig.savefig(FIG_DIR / f"fig8_lscale{suffix}.png")
        plt.close(fig)
        sl = g5["l_scale"][B]["loglog_slope"]
        print(f"l-scale B={B}: slopes " +
              "  ".join(f"{v} {sl[v]:.2f}" for v in sl) +
              "   [expect ~2: router is O(L^2/c_R)]")
else:
    print("WARNING: gate5_results.json not found; fig8 skipped")


# ---------------------------------------------------------------------------
# Figure 6: performance (ETTh1 mean test loss) vs FORECAST-REQUIRED speed
# (last-query latency, released gate13 audit) as the primary panel, with the
# full-layer frontier as a separately labelled comparison (same audited run);
# lower-left = best; axes zoomed to the measured range; means only (no CIs)
# ---------------------------------------------------------------------------
GATE3_RES = REPO_DIR / "plan" / "gates" / "gate3" / "results"
LAT_JSON = PLAN_DIR / "gates" / "gate3" / "gate3_latency.json"
LAT_SCALE = PLAN_DIR / "gates" / "gate3" / "gate3_latency_scale.json"
LQ_JSON = PLAN_DIR / "gates" / "gate13_p0_audits" / "last_query_latency.json"
if GATE3_RES.exists() and LQ_JSON.exists():
    import json as _json
    SEEDS = [42, 123, 2024, 7, 99]

    # Loss on ETTh1 only: the frozen-task benchmark dataset, whose
    # standardized scale is shared by all three models (per-dataset losses
    # across the suite are NOT comparable and are deliberately not averaged).
    rows = [json.loads(l) for l in open(GATE3_RES / "etth1.jsonl")]
    loss = {v: float(np.mean([r["test_mse"] for r in rows
                              if r["variant"] == v and r["seed"] in SEEDS]))
            for v in ("Normal", "Flat", "DRRA")}
    if V2:
        # Fixed-mapping Flat test mean (same 5 seeds, corrected code).
        g15rows = [json.loads(l) for l in open(G15S_DIR / "etth1.jsonl")]
        loss["Flat"] = float(np.mean([r["test_mse"] for r in g15rows]))
        print(f"v2 mode: fig9 Flat test-loss overridden to {loss['Flat']:.4f}")

    # Forecast-required (last query) and full-layer latencies from ONE audited
    # run (25 rounds x 30 passes round-robin, batch 32, released gate13 log),
    # so the two panels are internally consistent; the batch-256 full-layer
    # numbers live in Table~\ref{tab:speed}.
    lq = _json.load(open(LQ_JSON))["latency"]
    last32 = {"Normal": lq["Normal_LAST"]["mean_ms"],
              "Flat": lq["CSA_4_4_LAST"]["mean_ms"],
              "DRRA": lq["DRRA_8_4_LAST"]["mean_ms"]}
    full32 = {"Normal": lq["Normal_FULL"]["mean_ms"],
              "Flat": lq["CSA_4_4_FULL"]["mean_ms"],
              "DRRA": lq["DRRA_8_4_FULL"]["mean_ms"]}

    # Projection-matched dense baseline (rank-64 output projection): loss from
    # its 25-seed manifest on the same five seeds; latency anchored to the
    # released Normal row by a same-run four-model round-robin measurement
    # (machine load shifts all four series together, so the ratio is what
    # transfers). Added only when that measurement exists.
    R2_LAT = PLAN_DIR / "gates" / "gate27_r2matched" / "latency_4model.json"
    R2_RES = PLAN_DIR / "gates" / "gate27_r2matched" / "results" / "normal_r64.jsonl"
    matched = None
    if V2 and R2_LAT.exists() and R2_RES.exists():
        probe = _json.load(open(R2_LAT))["r64_anchored"]
        mrows = [json.loads(l) for l in open(R2_RES)]
        mloss = float(np.mean([r["test_mse"] for r in mrows
                               if r["seed"] in SEEDS]))
        matched = {"loss": mloss,
                   "last": probe["LAST"]["released_anchored_ms"],
                   "full": probe["FULL"]["released_anchored_ms"]}
        print(f"v2 mode: fig9 projection-matched dense point loss {mloss:.4f} "
              f"LAST {matched['last']:.2f} ms FULL {matched['full']:.2f} ms")

    style = {"Normal": C["red"], "Flat": C["orange"], "DRRA": C["blue"]}
    labels = {"Normal": "Normal", "Flat": "$(4,4)$", "DRRA": "$(8,4)$"}
    ylim = (min(loss.values()) - 0.03, max(loss.values()) + 0.03)
    panels = (
        ("Forecast-required (last query), batch 32", last32, (1.0, 8.0),
         "Speed — mean forecast-required latency (ms)"),
        ("Full layer, batch 32", full32, (29.0, 43.0),
         "Speed — mean forward latency (ms)"),
    )
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.2))
    for ax, (title, xs, xlim, xlabel), mkey in zip(
            axes, panels, ("last", "full")):
        for v in ("Normal", "Flat", "DRRA"):
            ax.scatter(xs[v], loss[v], s=70, color=style[v], zorder=3)
            ax.annotate(labels[v], (xs[v], loss[v]),
                        textcoords="offset points", xytext=(8, -6), fontsize=8)
        if matched is not None:
            ax.scatter(matched[mkey], matched["loss"], s=60, facecolors="none",
                       edgecolors="#555555", linewidths=1.1, zorder=3)
            ax.annotate("Normal-r64", (matched[mkey], matched["loss"]),
                        textcoords="offset points", xytext=(8, 4), fontsize=7.5,
                        color="#333333")
        ax.axhline(loss["Normal"], color="#999999", linewidth=0.6,
                   linestyle="--")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Performance — mean test loss on ETTh1")
        ax.set_title(title, fontsize=8)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        # Neither axis inverted: lower loss = down, lower latency = left
        # (best model = lower-left)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig9_perf_speed.pdf")
    fig.savefig(FIG_DIR / "fig9_perf_speed.png")
    plt.close(fig)
    print("perf-speed: ETTh1 test-loss", {v: round(x, 4) for v, x in loss.items()},
          "| LAST32", {v: round(x, 2) for v, x in last32.items()},
          "| FULL32", {v: round(x, 2) for v, x in full32.items()})
else:
    print("WARNING: gate13 last-query audit JSON not found; fig9 skipped")

make_fig12()
make_fig13()

print("All figures written to", FIG_DIR)
