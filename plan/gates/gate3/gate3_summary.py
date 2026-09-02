#!/usr/bin/env python3
"""Gate 3 summary generator — reads results/*.jsonl, emits gate3_summary.md.

Outputs per-dataset 3-way tables (val mean±std, test mean±std, Δ% vs Normal),
paired per-seed val deltas vs Normal, integrity audit (rows/seeds/dups/params/
train-range/finite), and cross-dataset counts. Descriptive statistics only
(Gate 4 does significance tests). Exit code 0 iff every dataset passes audit.
"""
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

import torch  # noqa: E402

from gate3_harness import build_model, count_attn_params, count_full_params  # noqa: E402
import gate3_datasets as g3  # noqa: E402

RESULTS_DIR = os.path.join(HERE, "results")
OUT_PATH = os.path.join(HERE, "gate3_summary.md")
SEEDS = [42, 123, 2024, 7, 99]
VARIANTS = ["Normal", "Flat", "DRRA"]
DATASET_ORDER = ["etth1", "etth2", "ettm1", "ettm2", "electricity", "traffic",
                 "weather", "exchange", "solar",
                 "syn_sinusoids", "syn_changepoints", "syn_delayedcopy"]


def load_rows(dataset):
    path = os.path.join(RESULTS_DIR, f"{dataset}.jsonl")
    rows = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def expected_params(dataset, variant):
    """Recompute (attn, full) params via the harness builder (seed 42)."""
    torch.manual_seed(42)
    m = build_model(dataset, variant, seed=42)
    return count_attn_params(m), count_full_params(m)


def audit(dataset):
    rows = load_rows(dataset)
    issues = []
    by_key = {}
    for r in rows:
        by_key[(r["variant"], r["seed"])] = r
    for v in VARIANTS:
        for s in SEEDS:
            if (v, s) not in by_key:
                issues.append(f"missing ({v}, seed={s})")
    dups = len(rows) - len(by_key)
    if dups:
        issues.append(f"{dups} duplicate (variant, seed) rows")
    for v in VARIANTS:
        exp = expected_params(dataset, v)
        for s in SEEDS:
            r = by_key.get((v, s))
            if r and (r["attn_params"], r["full_params"]) != exp:
                issues.append(f"{v} seed={s} params {r['attn_params']}/{r['full_params']} "
                              f"!= expected {exp}")
    med = st.median([r["final_train_mse"] for r in rows]) if rows else float("nan")
    for r in rows:
        if not all(map(lambda x: x == x, [r["val_mse"], r["test_mse"], r["final_train_mse"]])):
            issues.append(f"{r['variant']} seed={r['seed']} non-finite MSE")
        elif med == med and not (0.5 * med <= r["final_train_mse"] <= 2.0 * med):
            issues.append(f"{r['variant']} seed={r['seed']} train_mse "
                          f"{r['final_train_mse']:.4f} outside [0.5,2.0]x median {med:.4f}")
    return issues, by_key


def agg(variant_rows):
    vals = [r["val_mse"] for r in variant_rows]
    tests = [r["test_mse"] for r in variant_rows]
    return (st.mean(vals), st.stdev(vals) if len(vals) > 1 else 0.0,
            st.mean(tests), st.stdev(tests) if len(tests) > 1 else 0.0)


def fmt_delta(pct):
    return f"{pct:+.2f}%" if pct == pct else "n/a"


# ── Transposed view: models as rows, datasets as columns ─────────────────────
DATASET_LABELS = {
    "etth1": "ETTh1", "etth2": "ETTh2", "ettm1": "ETTm1", "ettm2": "ETTm2",
    "electricity": "Electricity", "traffic": "Traffic", "weather": "Weather",
    "exchange": "Exchange", "solar": "Solar",
    "syn_sinusoids": "syn-sinusoids", "syn_changepoints": "syn-changepts",
    "syn_delayedcopy": "syn-delayedcopy",
}


def per_dataset_aggs():
    """{dataset: {variant: (val_mean, val_std, test_mean, test_std)}} for the
    datasets with a complete 15/15 row set."""
    aggs = {}
    for ds in DATASET_ORDER:
        issues, by_key = audit(ds)
        if issues or len(load_rows(ds)) != 15:
            continue
        aggs[ds] = {v: agg([by_key[(v, s)] for s in SEEDS]) for v in VARIANTS}
    return aggs


def transposed_rows(aggs):
    """Models-as-rows × datasets-as-columns table. Returns (header, rows):
    header = ["Model"] + dataset labels; each row = (label, [cells...]).
    Best value per dataset column is bolded (val rows among val rows,
    test rows among test rows)."""
    dss = [ds for ds in DATASET_ORDER if ds in aggs]
    header = ["Model"] + [DATASET_LABELS[ds] for ds in dss]

    def best_val(ds):
        return min(aggs[ds][v][0] for v in VARIANTS)

    def best_test(ds):
        return min(aggs[ds][v][2] for v in VARIANTS)

    def b(cell, cond):
        return f"**{cell}**" if cond else cell

    def val_cell(v, ds):
        a = aggs[ds][v]
        return b(f"{a[0]:.4f} ± {a[1]:.4f}", a[0] == best_val(ds))

    def test_cell(v, ds):
        a = aggs[ds][v]
        return b(f"{a[2]:.4f} ± {a[3]:.4f}", a[2] == best_test(ds))

    def delta_cell(v, ds):
        return fmt_delta((aggs[ds][v][0] / aggs[ds]["Normal"][0] - 1) * 100)

    def delta_test_cell(v, ds):
        return fmt_delta((aggs[ds][v][2] / aggs[ds]["Normal"][2] - 1) * 100)

    rows = []
    for v in VARIANTS:
        rows.append((f"{v} val", [val_cell(v, ds) for ds in dss]))
    rows.append(("Δval (4,4) vs Normal", [delta_cell("Flat", ds) for ds in dss]))
    rows.append(("Δval (8,4) vs Normal", [delta_cell("DRRA", ds) for ds in dss]))
    for v in VARIANTS:
        rows.append((f"{v} test", [test_cell(v, ds) for ds in dss]))
    rows.append(("Δtest (4,4) vs Normal", [delta_test_cell("Flat", ds) for ds in dss]))
    rows.append(("Δtest (8,4) vs Normal", [delta_test_cell("DRRA", ds) for ds in dss]))
    return header, rows


def transposed_md(aggs):
    header, rows = transposed_rows(aggs)
    lines = ["| " + " | ".join(header) + " |",
             "|" + "---|" * len(header)]
    for label, cells in rows:
        lines.append("| " + label + " | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def build_md():
    lines = ["# Gate 3 — Dataset-Coverage Summary", "",
             "3-way comparison (Normal / Flat=(4,4) / DRRA=(8,4)) × 5 paired seeds "
             "{42,123,2024,7,99} on 12 datasets under the frozen direct-96 task "
             "(L=256, H=96, train-only z-score, pooled MSE, standardized units). "
             "Descriptive statistics only; significance testing is Gate 4.",
             "", "## Overview — models × datasets (transposed)", "",
             "Validation MSE per dataset, mean ± std over 5 paired seeds "
             "(lower is better). Bold: best value in its dataset column "
             "(val rows among val rows, test rows among test rows).", "",
             transposed_md(per_dataset_aggs()), "",
             "## Integrity audit", ""]
    all_clean = True
    tables = []
    for ds in DATASET_ORDER:
        issues, by_key = audit(ds)
        rows = load_rows(ds)
        clean = not issues and len(rows) == 15
        all_clean &= clean
        lines.append(f"### {ds} — {'PASS' if clean else 'FAIL'}")
        if issues:
            lines += [f"- {i}" for i in issues]
        if len(rows) != 15:
            lines.append(f"- rows present: {len(rows)}/15")
        lines.append("")
        if not clean:
            continue
        n_agg = agg([by_key[("Normal", s)] for s in SEEDS])
        f_agg = agg([by_key[("Flat", s)] for s in SEEDS])
        d_agg = agg([by_key[("DRRA", s)] for s in SEEDS])
        lines += [
            "| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |",
            "|---|---|---|---|---|",
            f"| Normal | {n_agg[0]:.4f} ± {n_agg[1]:.4f} | {n_agg[2]:.4f} ± {n_agg[3]:.4f} | — | — |",
            f"| Flat (4,4) | {f_agg[0]:.4f} ± {f_agg[1]:.4f} | {f_agg[2]:.4f} ± {f_agg[3]:.4f} | "
            f"{fmt_delta((f_agg[0] / n_agg[0] - 1) * 100)} | "
            f"{fmt_delta((f_agg[2] / n_agg[2] - 1) * 100)} |",
            f"| DRRA (8,4) | {d_agg[0]:.4f} ± {d_agg[1]:.4f} | {d_agg[2]:.4f} ± {d_agg[3]:.4f} | "
            f"{fmt_delta((d_agg[0] / n_agg[0] - 1) * 100)} | "
            f"{fmt_delta((d_agg[2] / n_agg[2] - 1) * 100)} |",
            "",
            "Paired per-seed val deltas vs Normal (negative = variant beats Normal):", "",
            "| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |", "|---|---|---|",
        ]
        for v in ("Flat", "DRRA"):
            deltas = [by_key[(v, s)]["val_mse"] - by_key[("Normal", s)]["val_mse"] for s in SEEDS]
            beat = sum(1 for d in deltas if d < 0)
            lines.append(f"| {v} | " + " / ".join(f"{d:+.4f}" for d in deltas) + f" | {beat}/5 |")
        lines.append("")
        tables.append((ds, n_agg, f_agg, d_agg))
    lines += ["## Cross-dataset headline", ""]
    drra_beats = flat_beats = 0
    for ds, n_agg, f_agg, d_agg in tables:
        if d_agg[0] < n_agg[0]:
            drra_beats += 1
        if f_agg[0] < n_agg[0]:
            flat_beats += 1
    lines += [
        f"- Datasets where DRRA (8,4) mean val < Normal: **{drra_beats}/{len(tables)}**",
        f"- Datasets where Flat (4,4) mean val < Normal: **{flat_beats}/{len(tables)}**",
        f"- Datasets with a complete 15/15 row set: **{len(tables)}/12**",
    ]
    with open(OUT_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT_PATH}")
    return all_clean and len(tables) == 12


def build_report():
    """Emit a RESULTS.md-ready 'Dataset Coverage (Gate 3)' section to stdout.

    Uses the same audit/agg logic as build_md(); prints only for datasets with a
    complete 15/15 row set. Returns True iff all 12 datasets are complete.
    """
    aggs = per_dataset_aggs()
    lines = ["## Dataset Coverage (Gate 3)", "",
             "12 datasets × 3 variants (Normal / Flat=(4,4) / DRRA=(8,4)) × 5 paired "
             "seeds {42,123,2024,7,99} under the frozen direct-96 task (L=256, H=96, "
             "train-only z-score, pooled MSE, standardized units). Models as rows, "
             "datasets as columns; bold = best per dataset column (val rows among val "
             "rows, test rows among test rows). Descriptive statistics only; "
             "significance tests are Gate 4. Full per-seed tables + integrity audit: "
             "`plan/gates/gate3/gate3_summary.md`.", "",
             transposed_md(aggs), ""]
    lines.append(f"**Cross-dataset:** DRRA (8,4) beats Normal on mean val in "
                 f"**{sum(1 for ds in aggs if aggs[ds]['DRRA'][0] < aggs[ds]['Normal'][0])}/{len(aggs)}** "
                 f"datasets; Flat (4,4) in "
                 f"**{sum(1 for ds in aggs if aggs[ds]['Flat'][0] < aggs[ds]['Normal'][0])}/{len(aggs)}**; "
                 f"complete row sets **{len(aggs)}/12**.")
    lines += ["",
              "*Caveats: standardized units; params not re-equalized across variants "
              "(~2% attn-param spread); threads=8 sequential; 10-epoch fixed budget; "
              "ETTh1 rows are new runs of the frozen task (bit-identical to the baseline "
              "gate's Normal rows and Gate-2 cells).*",
              ]
    print("\n".join(lines))
    return len(aggs) == 12


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Gate 3 summary/report generator")
    p.add_argument("--report", action="store_true",
                   help="print RESULTS.md-ready section to stdout (no file write)")
    args = p.parse_args()
    if args.report:
        sys.exit(0 if build_report() else 1)
    sys.exit(0 if build_md() else 1)
