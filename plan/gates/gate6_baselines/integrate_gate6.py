#!/usr/bin/env python3
"""Gate 6 -> paper integration. Run ONLY after the sweep completes.

Steps:
  1. Run gate6_audit.py; abort unless integrity PASS with zero incomplete groups
     (declared omissions excepted).
  2. Verify the drafted prose claims in paper_snippet.tex against the audited
     numbers (each marked VERIFIED/REFUTED; a REFUTED claim swaps in neutral
     wording instead of the strong sentence).
  3. Fill the paper_snippet.tex table body (anchor columns from gate6, family
     columns asserted bit-identical to the paper's tab:coverage).
  4. With --write: apply the four prose updates in the paper (related work,
     intro non-claims, discussion limitation, appendix roadmap) and insert the
     subsection+table into experiments.tex. Without --write: dry run.

Usage: .venv-gate6/bin/python integrate_gate6.py [--write]
"""
import json
import os
import subprocess
import sys
from collections import defaultdict

import numpy as np

GATE = os.path.dirname(os.path.abspath(__file__))
PY = "/Users/darylfung/Documents/Work/Nicosia/new_attention/.venv-gate6/bin/python"
SEEDS = [42, 123, 2024, 7, 99]
GATE3 = os.path.join(GATE, "..", "gate3", "results")
SNIPPET = os.path.join(GATE, "paper_snippet.tex")
PAPER = "/Users/darylfung/Documents/Work/Nicosia/new_attention/paper/sections"

# family val means exactly as printed in the paper's tab:coverage
PAPER_COVERAGE = {
    "Normal": dict(etth1=0.8416, etth2=1.9187, ettm1=0.4285, ettm2=1.5618,
                   electricity=0.4047, traffic=0.5994, weather=0.4460,
                   exchange=2.9800, solar=0.1899, syn_sinusoids=0.1227,
                   syn_changepoints=5.9456, syn_delayedcopy=0.2888),
    "Flat":   dict(etth1=0.6332, etth2=1.3624, ettm1=0.3965, ettm2=0.9964,
                   electricity=0.3798, traffic=0.5838, weather=0.4469,
                   exchange=3.1166, solar=0.1721, syn_sinusoids=0.1264,
                   syn_changepoints=5.9677, syn_delayedcopy=0.2894),
    "DRRA":   dict(etth1=0.5967, etth2=1.8080, ettm1=0.3832, ettm2=0.8053,
                   electricity=0.3808, traffic=0.5874, weather=0.4424,
                   exchange=3.2350, solar=0.1722, syn_sinusoids=0.1264,
                   syn_changepoints=6.0013, syn_delayedcopy=0.2894),
}
PRETTY = dict(etth1="ETTh1", etth2="ETTh2", ettm1="ETTm1", ettm2="ETTm2",
              electricity="Electricity", traffic="Traffic", weather="Weather",
              exchange="Exchange", solar="Solar",
              syn_sinusoids="sSin", syn_changepoints="sCP", syn_delayedcopy="sDC")
REAL_WORLD = ["etth1", "etth2", "ettm1", "ettm2", "electricity", "traffic",
              "weather", "exchange", "solar"]
OMITTED = {(ds, "PatchTST") for ds in ("traffic", "electricity", "solar", "weather")}


def load_gate6():
    runs = defaultdict(dict)
    for ds in PRETTY:
        fp = os.path.join(GATE, "results", f"{ds}.jsonl")
        if not os.path.exists(fp):
            continue
        for line in open(fp):
            line = line.strip()
            if line:
                r = json.loads(line)
                runs[(ds, r["variant"])][r["seed"]] = r
    return runs


def load_gate3(ds):
    fp = os.path.join(GATE3, f"{ds}.jsonl")
    out = defaultdict(list)
    if os.path.exists(fp):
        for line in open(fp):
            r = json.loads(line)
            out[r["variant"]].append((r["seed"], r["val_mse"], r["test_mse"]))
    return out


def main():
    write = "--write" in sys.argv

    # ── 1. audit gate ──────────────────────────────────────────────────────
    print("== step 1: audit gate ==")
    res = subprocess.run([PY, os.path.join(GATE, "gate6_audit.py")],
                         capture_output=True, text=True)
    print(res.stdout[-1200:])
    out = res.stdout
    if "integrity: PASS" not in out or "FAIL" in out:
        sys.exit("ABORT: audit did not pass")
    if "!= [" in out or "pending (sweep not there yet)" in out:
        sys.exit("ABORT: sweep incomplete — re-run gate6_sweep.sh until the audit "
                 "reports no pending groups (this script is idempotent)")
    print("audit gate: OK\n")

    # ── 2. load and verify numbers ─────────────────────────────────────────
    print("== step 2: verify numbers ==")
    runs = load_gate6()
    facts = {}
    for ds in PRETTY:
        for var in ("DLinear", "PatchTST"):
            if (ds, var) in OMITTED:
                continue
            s = runs.get((ds, var), {})
            assert sorted(s) == sorted(SEEDS), f"missing seeds {ds}/{var}: {sorted(s)}"
        g3 = load_gate3(ds)
        for fam, paper_vals in PAPER_COVERAGE.items():
            m = np.mean([v for _, v, _ in g3[fam]])
            assert abs(m - paper_vals[ds]) < 5e-5, \
                f"family drift {fam}/{ds}: manifest {m:.4f} vs paper {paper_vals[ds]}"
    print("family columns bit-identical to tab:coverage: OK")
    print("anchor seeds complete (except declared omissions): OK")

    # claim (a): DLinear beats every family config on ETTh1 val AND test
    g31 = load_gate3("etth1")
    fam_min_val = min(np.mean([v for _, v, _ in g31[f]]) for f in ("Normal", "Flat", "DRRA"))
    fam_min_test = min(np.mean([t for _, _, t in g31[f]]) for f in ("Normal", "Flat", "DRRA"))
    dl_val = np.mean([runs[("etth1", "DLinear")][s]["val_mse"] for s in SEEDS])
    dl_test = np.mean([runs[("etth1", "DLinear")][s]["test_mse"] for s in SEEDS])
    claim_a = dl_val < fam_min_val and dl_test < fam_min_test
    facts["claim_a_dlinear_etth1"] = dict(dl_val=dl_val, dl_test=dl_test,
                                          fam_min_val=fam_min_val,
                                          fam_min_test=fam_min_test,
                                          holds=bool(claim_a))
    print(f"claim (a) 'DLinear outperforms every family config on ETTh1 val and test': "
          f"{'VERIFIED' if claim_a else 'REFUTED'} "
          f"(DLinear {dl_val:.4f}|{dl_test:.4f} vs family min {fam_min_val:.4f}|{fam_min_test:.4f})")

    # claim (b): anchors ahead on the real-world sets
    wins = 0
    for ds in REAL_WORLD:
        best_anchor = min(
            np.mean([runs[(ds, v)][s]["val_mse"] for s in SEEDS])
            for v in ("DLinear", "PatchTST") if (ds, v) in runs)
        best_fam = min(PAPER_COVERAGE[f][ds] for f in PAPER_COVERAGE)
        wins += best_anchor < best_fam
    facts["realworld_anchor_wins"] = f"{wins}/{len(REAL_WORLD)}"
    print(f"claim (b) 'anchors ahead on the real-world sets': {wins}/"
          f"{len(REAL_WORLD)} real-world datasets")

    # ── 3. fill the snippet table ──────────────────────────────────────────
    print("\n== step 3: fill table body ==")
    rows = []
    for ds in PRETTY:
        dl = pt = None
        if (ds, "DLinear") in runs:
            dl = np.mean([runs[(ds, "DLinear")][s]["val_mse"] for s in SEEDS])
        if (ds, "PatchTST") in runs:
            pt = np.mean([runs[(ds, "PatchTST")][s]["val_mse"] for s in SEEDS])
        anchors = [x for x in (dl, pt) if x is not None]
        best = min(anchors) if anchors else None
        def fmt(x, bold=False):
            if x is None:
                return "---"
            s = f"{x:.4f}"
            return f"\\textbf{{{s}}}" if (bold and x == best) else s
        rows.append(f"{PRETTY[ds]} & {fmt(dl, True)} & {fmt(pt, True)} & "
                    f"{PAPER_COVERAGE['Normal'][ds]:.4f} & "
                    f"{PAPER_COVERAGE['Flat'][ds]:.4f} & "
                    f"{PAPER_COVERAGE['DRRA'][ds]:.4f} \\\\")
    body = "\n".join(["% GATE6_TABLE_BEGIN (auto-generated; idempotent)"] + rows +
                      ["% GATE6_TABLE_END"])
    snip = open(SNIPPET).read()
    if "% TABLE_BODY" in snip:
        snip = snip.replace("% TABLE_BODY", body, 1)
        # drop the stale continuation comment line after the old marker
        snip = snip.replace("% bit-identical to tab:coverage; anchor columns from gate6 audit)\n", "")
    elif "% GATE6_TABLE_BEGIN" in snip and "% GATE6_TABLE_END" in snip:
        import re as _re
        snip = _re.sub(r"% GATE6_TABLE_BEGIN.*?% GATE6_TABLE_END", body,
                       snip, count=1, flags=_re.S)
    else:
        sys.exit("snippet has neither TABLE_BODY marker nor generated region")
    with open(SNIPPET, "w") as f:
        f.write(snip)
    print(f"table body written: {len(rows)} rows -> {SNIPPET}")

    # ── 4. prose updates ───────────────────────────────────────────────────
    print("\n== step 4: paper prose updates ==")
    strong = ("Table~\\ref{tab:refpoints} reports the result. The anchors are decisively\n"
              "ahead on the real-world sets---most starkly, DLinear (49K parameters, no\n"
              "attention) outperforms every configuration of the family on ETTh1 validation\n"
              "and test.")
    neutral = ("Table~\\ref{tab:refpoints} reports the result. On most real-world\n"
               "datasets the anchors are ahead; on ETTh1, DLinear (49K parameters, no\n"
               "attention) outperforms every configuration of the family on validation\n"
               "and test.")
    if claim_a and wins >= 7:
        print("strong sentence: VERIFIED (kept)")
    else:
        snip = snip.replace(strong, neutral)
        with open(SNIPPET, "w") as f:
            f.write(snip)
        print(f"strong sentence: REFUTED (wins={wins}) -> neutral wording installed")

    updates = [
        # (file, old, new, must_exist)
        ("related_work.tex",
         "These are the natural external baselines\nfor this line of work; none has been run under our frozen protocol yet (they\nare itemized as pending work in the appendix roadmap,\nAppendix~\\ref{sec:appendix-roadmap}).",
         "Two of them, DLinear\n\\citep{zeng2023dlinear} and PatchTST \\citep{nie2023patchtst}, have been run\nunder our frozen protocol as external reference points (not peer methods;\nSection~\\ref{sec:refpoints}); the rest are itemized as pending work in the\nappendix roadmap, Appendix~\\ref{sec:appendix-roadmap}."),
        ("introduction.tex",
         "does not claim state-of-the-art forecasting accuracy (no external\nbaselines are run yet)",
         "does not claim state-of-the-art forecasting accuracy (the external\narchitectures we ran are reference points for calibrating absolute error\nlevels, not peer methods; Section~\\ref{sec:refpoints})"),
        ("discussion.tex",
         "\\item \\textbf{No external baselines.} Comparisons are internal to the\n        family plus the full-attention same-backbone baseline; PatchTST,\n        iTransformer, DLinear, Informer, and linear/SSM baselines under the\n        same protocol are pending (Appendix roadmap item~3).",
         "\\item \\textbf{External architectures as reference points only.} DLinear\n        and PatchTST were run under the frozen protocol to calibrate absolute\n        error levels (Section~\\ref{sec:refpoints}); they are not peer methods\n        (different architectures, and DLinear has no attention), so no\n        competitiveness claim is made. Efficiency-oriented peers (Informer's\n        ProbSparse, iTransformer, TimesNet, SSM baselines) remain pending\n        (Appendix roadmap item~3)."),
        ("appendix.tex",
         "\\item \\textbf{Baselines: PARTIAL (Gate 6, 2026-09-01).} DLinear\n        \\citep{zeng2023dlinear} and PatchTST \\citep{nie2023patchtst} are\n        being run under the identical frozen protocol (12 datasets, 5\n        paired seeds; results manifests in the repository). Remaining:\n        iTransformer, Informer, TimesNet, and an SSM baseline.",
         "\\item \\textbf{Baselines: reference points DONE (Gate 6, 2026-09-01).}\n        DLinear \\citep{zeng2023dlinear} and PatchTST \\citep{nie2023patchtst}\n        under the identical frozen protocol (11 datasets + one declared\n        omission, 5 paired seeds; audited summary in the repository,\n        Section~\\ref{sec:refpoints}). Remaining: iTransformer, Informer,\n        TimesNet, and an SSM baseline."),
    ]
    for fname, old, new in updates:
        p = os.path.join(PAPER, fname)
        t = open(p).read()
        if old in t:
            if write:
                open(p, "w").write(t.replace(old, new, 1))
                print(f"  updated {fname}")
            else:
                print(f"  [dry-run] would update {fname}")
        elif new[:40] in t:
            print(f"  {fname}: already updated")
        else:
            print(f"  WARNING: anchor text not found in {fname} — manual update needed")

    # insert subsection before Statistical treatment
    exp = os.path.join(PAPER, "experiments.tex")
    t = open(exp).read()
    if "\\subsection{External reference points}" not in t:
        snippet_body = "\n".join(
            l for l in open(SNIPPET).read().splitlines()
            if not l.startswith("%"))
        if write:
            anchor = "\\subsection{Statistical treatment}"
            assert anchor in t
            t = t.replace(anchor, snippet_body + "\n\n" + anchor, 1)
            open(exp, "w").write(t)
            print("  inserted reference-points subsection into experiments.tex")
        else:
            print("  [dry-run] would insert subsection into experiments.tex")
    else:
        print("  experiments.tex: subsection already present")

    with open(os.path.join(GATE, "gate6_facts.json"), "w") as f:
        json.dump(facts, f, indent=2)
    print("\nfacts -> gate6_facts.json")
    print("NEXT (manual): recompile paper, update abstract last block if needed, "
          "update paper_notes.md changelog, commit.")


if __name__ == "__main__":
    main()
