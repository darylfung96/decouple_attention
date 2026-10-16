#!/usr/bin/env python3
"""Gate 21 — per-seed conditional (simple) effects of the 2x2 factorial.

Why this exists
---------------
The Q1 review (2026-10-16, item R1) asks for the four conditional effects of the
factorial to be reported with uncertainty computed from the unrounded seed data,
because the values quoted in the manuscript are differences of the printed
4-decimal cell means, which do not establish their significance.

This script rebuilds the merged 25-seed validation matrix exactly as
plan/gates/gate15_rerun/gate15_analyze.py does (kept rows for (8,4)/Normal from
gate2/gate7/baseline, fixed rows for the other three cells from gate15), then
computes per-seed conditional effects with paired 95% intervals, exact Wilcoxon
p-values and sign consistency. No training runs; read-only on the manifests.

Usage (repo root):
  ~/.uv_env/py311/bin/python plan/gates/gate21_simple_effects/simple_effects.py
"""
import json
import os
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

G2 = ROOT / "plan/gates/gate2/gate2_results.jsonl"
G7 = ROOT / "plan/gates/gate7_seeds/results/gate7.jsonl"
BASE = ROOT / "plan/gates/baseline/baseline_normal_results.jsonl"
G15F = ROOT / "plan/gates/gate15_rerun/results/factorial.jsonl"

CELLMAP = {(4, 4): "CSA", (8, 4): "DRRA", (4, 8): "C48", (8, 8): "C88"}
G7MAP = {"CSA(4,4)": "CSA", "DRRA(8,4)": "DRRA", "(4,8)": "C48", "(8,8)": "C88",
         "Normal": "Normal"}


def load_factorial():
    """v2 merge: NEW fixed rows for CSA/C48/C88; KEPT rows for DRRA/Normal."""
    new, old = {}, {}
    for line in G15F.read_text().splitlines():
        r = json.loads(line)
        new[(CELLMAP[tuple(r["cell"])], r["seed"])] = r["val_mse"]
    for line in G2.read_text().splitlines():
        r = json.loads(line)
        old[(CELLMAP[tuple(r["cell"])], r["seed"])] = r["val_mse"]
    for line in G7.read_text().splitlines():
        r = json.loads(line)
        old[(G7MAP[r["cell_name"]], r["seed"])] = r["val_mse"]
    for line in BASE.read_text().splitlines():
        r = json.loads(line)
        old[("Normal", r["seed"])] = r["val_mse"]
    merged = dict(old)
    merged.update(new)          # fixed cells win, as in gate15_analyze.py
    return merged


def est(x):
    x = np.asarray(x, float)
    m = float(x.mean())
    lo, hi = stats.t.interval(0.95, len(x) - 1, loc=m, scale=stats.sem(x))
    wp = float(stats.wilcoxon(x).pvalue)
    return {"mean": round(m, 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "wilcoxon_p": round(wp, 4), "n": int(len(x)),
            "sign_consistent": int((np.sign(x) == np.sign(m)).sum())}


def main():
    m = load_factorial()
    seeds = sorted({s for (_, s) in m})
    def y(cell, s):
        return m[(cell, s)]

    def series(fn):
        return np.array([fn(s) for s in seeds], float)

    effects = {
        "kv_at_cr4":  ("c_KV 4->8 at c_R=4", series(lambda s: y("DRRA", s) - y("CSA", s))),
        "kv_at_cr8":  ("c_KV 4->8 at c_R=8", series(lambda s: y("C88", s) - y("C48", s))),
        "cr_at_ckv4": ("c_R 4->8 at c_KV=4", series(lambda s: y("C48", s) - y("CSA", s))),
        "cr_at_ckv8": ("c_R 4->8 at c_KV=8", series(lambda s: y("C88", s) - y("DRRA", s))),
    }
    out = {"provenance": "gate21/uv-torch2.6.0/read-only", "n_seeds": len(seeds),
           "source": str(G15F.relative_to(ROOT)) + " + kept gate2/gate7/baseline rows",
           "conditional_effects": {}, "cross_checks": {}}
    for k, (label, x) in effects.items():
        out["conditional_effects"][k] = {"label": label, **est(x)}
    # cross-checks that the numbers agree with the published main effects
    kv_main = (effects["kv_at_cr4"][1] + effects["kv_at_cr8"][1]) / 2
    cr_main = (effects["cr_at_ckv4"][1] + effects["cr_at_ckv8"][1]) / 2
    inter = effects["kv_at_cr8"][1] - effects["kv_at_cr4"][1]
    out["cross_checks"] = {"kv_main_mean": round(float(kv_main.mean()), 4),
                           "cr_main_mean": round(float(cr_main.mean()), 4),
                           "interaction_mean": round(float(inter.mean()), 4),
                           "kv_main_est": est(kv_main), "cr_main_est": est(cr_main),
                           "interaction_est": est(inter)}

    with open(HERE / "simple_effects.json", "w") as f:
        json.dump(out, f, indent=1)

    lines = ["# Gate 21 — per-seed conditional effects (Q1 review R1)", "",
             f"{out['n_seeds']} paired seeds, validation MSE, merged v2 matrix.", "",
             "| conditional effect | mean | 95% paired CI | Wilcoxon p | sign |",
             "|---|---|---|---|---|"]
    for k, v in out["conditional_effects"].items():
        lines.append(f"| {v['label']} | {v['mean']:+.4f} | "
                     f"[{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] | "
                     f"{v['wilcoxon_p']:.4f} | {v['sign_consistent']}/25 |")
    lines += ["", "Cross-checks (must reproduce the published values):", ""]
    for k, v in out["cross_checks"].items():
        if isinstance(v, dict):
            lines.append(f"- {k}: {v['mean']:+.4f} [{v['ci95'][0]:+.4f}, "
                         f"{v['ci95'][1]:+.4f}], Wilcoxon p = {v['wilcoxon_p']:.4f}")
        else:
            lines.append(f"- {k}: {v:+.4f}")
    (HERE / "simple_effects.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
