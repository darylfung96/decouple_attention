# Gate 28 — C1 all-block control: analysis (rule pre-registered in design.md).

# Reads the new manifest, pairs it with the two routed reference cells on the same
# 25 seeds (arrays reproduced by gate15_analyze.load_factorial, read-only), and
# applies the D5 branch. Refuses to run until D5 is frozen in DECISIONS.md at the
# value coded here — equivalence wording chosen after seeing results is inadmissible.
#
# Run: ~/.uv_env/py311/bin/python plan/gates/gate28_c1control/analysis.py
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

sys.path.insert(0, str(ROOT / "plan" / "gates" / "gate15_rerun"))
from gate15_analyze import est, load_factorial  # noqa: E402

RESULTS = HERE / "results" / "allblock.jsonl"
OUT_JSON = HERE / "analysis.json"
OUT_MD = HERE / "analysis.md"
DECISIONS = ROOT / "pre-publication_v2_tasks" / "DECISIONS.md"

# Design.md froze this value; the freeze log must agree.
MARGIN_REL = 0.02

CONTROLS = {"C1(4,4)": ("CSA", 4), "C1(8,4)": ("DRRA", 8)}


def frozen_margin():
    text = DECISIONS.read_text()
    rows = [l for l in text.splitlines()
            if re.match(r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*D5\s*\|", l)]
    if not rows:
        raise SystemExit(
            "D5 is not frozen in DECISIONS.md — the design forbids interpreting\n"
            "this control before the margin is stated. Freeze D5, then re-run.")
    row = rows[-1]
    pcts = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", row)]
    if not pcts:
        raise SystemExit(f"no percentage found in the D5 freeze row: {row}")
    margin = pcts[0] / 100.0
    if abs(margin - MARGIN_REL) > 1e-12:
        raise SystemExit(
            f"frozen D5 margin {margin:.4f} != coded MARGIN_REL {MARGIN_REL:.4f}; "
            "update analysis.py before running it")
    return row, margin


def load_controls():
    rows = {}
    for line in RESULTS.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows.setdefault(r["cell_name"], {})[int(r["seed"])] = r
    return rows


def classify(e_rel, margin):
    lo, hi = e_rel["ci95"]
    if lo > margin:
        return "routed_better"
    if hi < -margin:
        return "allblock_better"
    if lo > -margin and hi < margin:
        return "within_margin"
    if -margin < e_rel["mean"] < margin:
        return "within_margin_unresolved"
    return "indeterminate"


READING = {
    "routed_better": "routing adds accuracy beyond the margin (paper's attribution stands)",
    "within_margin": "all-block is non-inferior at this margin (boundary -> D4 b)",
    "within_margin_unresolved": "point estimate inside the margin but n=25 cannot resolve it; "
                                "report the bound, no claim",
    "allblock_better": "the router costs accuracy (report plainly -> D4 b)",
    "indeterminate": "interval straddles a margin edge (report as indeterminate, no claim)",
}


def main():
    row, margin = frozen_margin()
    if not RESULTS.exists():
        raise SystemExit(f"no results yet: {RESULTS} — run --full first")
    seeds, Y, T = load_factorial()
    ctrl = load_controls()

    res = {
        "provenance": "gate28 all-block rows (new) + gate15/kept legacy rows (read-only)",
        "d5_freeze_row": row.strip(),
        "margin_rel": margin,
        "n_seeds": len(seeds),
        "seeds": list(seeds),
        "cells": {},
    }

    for name, (ref, ck) in CONTROLS.items():
        assert name in ctrl, f"missing control rows: {name}"
        missing = [s for s in seeds if s not in ctrl[name]]
        assert not missing, f"{name}: missing seeds {missing}"
        v = np.array([ctrl[name][s]["val_mse"] for s in seeds])
        t = np.array([ctrl[name][s]["test_mse"] for s in seeds])
        d_abs = v - Y[ref]
        d_rel = d_abs / Y[ref]
        e_abs, e_rel = est(d_abs), est(d_rel)
        branch = classify(e_rel, margin)
        d_normal = v - Y["Normal"]
        e_normal = est(d_normal)
        first = ctrl[name][seeds[0]]
        res["cells"][name] = {
            "reference": ref,
            "ckv": ck,
            "mean_val": float(v.mean()),
            "mean_val_reference": float(Y[ref].mean()),
            "mean_test": float(t.mean()),
            "mean_test_reference": float(T[ref].mean()),
            "delta_abs": e_abs,
            "delta_rel": e_rel,
            "allblock_better_count_val": int((v < Y[ref]).sum()),
            "realized_blocks_mean": first["realized_blocks_mean"],
            "n_blocks": first["n_blocks"],
            "index_topk": first["index_topk"],
            "n_idx": first["n_idx"],
            "branch": branch,
            "reading": READING[branch],
            # primary output: upper 95% limit on the relative cost of removing routing
            "bound_rel_upper": max(float(e_rel["ci95"][1]), 0.0),
            # pre-registered secondary test: all-block vs Normal (large effect)
            "vs_Normal": e_normal,
            "beats_Normal_count_val": int((v < Y["Normal"]).sum()),
            "compression_alone_reproduces_headline": bool(e_normal["ci95"][1] < 0),
        }

    branches = {c: res["cells"][c]["branch"] for c in CONTROLS}
    res["bound_rel_upper"] = max(res["cells"][c]["bound_rel_upper"] for c in CONTROLS)
    res["compression_alone"] = all(
        res["cells"][c]["compression_alone_reproduces_headline"] for c in CONTROLS)
    if all(b in ("within_margin", "allblock_better") for b in branches.values()):
        overall = ("boundary", "compression without routing suffices at this margin; "
                   "retitle per D4 (b) and add the control to the paper")
    elif all(b == "routed_better" for b in branches.values()):
        overall = ("routing_confirmed", "routing pays for itself beyond the margin; "
                   "no paper change beyond reporting the control")
    elif all(b in ("within_margin", "within_margin_unresolved", "allblock_better")
             for b in branches.values()):
        overall = ("bounded", "no cell shows routing helping beyond the margin; the "
                   "deliverable is the bound U = "
                   f"{100*res['bound_rel_upper']:.1f}% on the relative cost of "
                   "removing routing")
    elif "indeterminate" in branches.values():
        overall = ("indeterminate", "at least one cell is indeterminate at this margin; "
                   "report the intervals, make no equivalence claim")
    else:
        overall = ("mixed", "the two cells disagree; report per cell, no single verdict")
    res["overall"], res["overall_reading"] = overall[0], overall[1]

    OUT_JSON.write_text(json.dumps(res, indent=2))

    def line(tag, c):
        e = res["cells"][c]
        a, r = e["delta_abs"], e["delta_rel"]
        return (f"| {tag} vs {e['reference']} | {e['mean_val']:.4f} | "
                f"{a['mean']:+.4f} [{a['ci95'][0]:+.4f}, {a['ci95'][1]:+.4f}] | "
                f"{100*r['mean']:+.2f}% [{100*r['ci95'][0]:+.2f}%, "
                f"{100*r['ci95'][1]:+.2f}%] | {r['wilcoxon_p']:.4g} | "
                f"{e['allblock_better_count_val']}/25 | {e['branch']} |")

    md = [
        "# Gate 28 — C1 all-block compression control: analysis", "",
        f"D5 margin: **{100*margin:.1f}%** relative validation MSE "
        f"(freeze row: {row.strip()})", "",
        "| Comparison | control val MSE | Δ MSE [95% CI] | Δ rel [95% CI] | Wilcoxon p | all-block better | branch |",
        "|---|---|---|---|---|---|---|",
    ]
    md += [line(c, c) for c in CONTROLS]
    md += ["", f"**Overall: {res['overall']}** — {res['overall_reading']}.", "",
           f"Primary bound: removing routing costs at most **{100*res['bound_rel_upper']:.1f}%** "
           "relative validation MSE (95% upper limit, worst cell).", "",
           "Pre-registered secondary test (all-block vs Normal): " + "; ".join(
               f"{c} {e['vs_Normal']['mean']:+.4f} "
               f"[{e['vs_Normal']['ci95'][0]:+.4f}, {e['vs_Normal']['ci95'][1]:+.4f}], "
               f"{e['beats_Normal_count_val']}/25"
               for c, e in res["cells"].items())
           + (" — compression alone reproduces the headline advantage."
              if res["compression_alone"] else " — compression alone does not reproduce it."), "",
           "Equivalence is declared only on interval containment inside the margin; a "
           "non-significant test is reported as indeterminate, never as equivalence. At n=25 "
           "the empirical paired resolution is 5.3-7.7% relative, so a 2% criterion is "
           "usually unavailable and the bound is the deliverable.", "",
           "Realized selection: " + "; ".join(
               f"{c} {res['cells'][c]['realized_blocks_mean']:.2f} of "
               f"{res['cells'][c]['n_blocks']} blocks per query "
               f"(routed reference: 9.91 of 32 for (8,4), 13.94 of 64 for (4,4) "
               f"on the dry-run batch)"
               for c in CONTROLS) + ".", "",
           "Note: MACs and parameters are identical to the reference cells; the "
           "control changes which blocks are unmasked, not the work performed."]
    OUT_MD.write_text("\n".join(md) + "\n")
    print("\n".join(md[len(md)-1-len(CONTROLS)-4:]))
    print(f"\nwrote {OUT_JSON.name} and {OUT_MD.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
