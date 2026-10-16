#!/usr/bin/env python3
"""Gate 30 — R4 analysis: route stability across training.

Reads results/route_snapshots.jsonl (raw per-epoch block sets), computes the
predeclared metrics from design.md, writes analysis.json + analysis.md.

Metric: mean Jaccard overlap of selected valid-KV-block sets per (row, position)
pair between epoch pairs (1,10), (1,5), (5,10); both-empty = 1.0, one-empty = 0.0;
plus the fraction of positions whose set is exactly unchanged.

Usage: ~/.uv_env/py311/bin/python plan/gates/gate30_r4routes/analysis.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IN_JSONL = os.path.join(HERE, "results", "route_snapshots.jsonl")
OUT_JSON = os.path.join(HERE, "analysis.json")
OUT_MD = os.path.join(HERE, "analysis.md")


def jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def compare(rec_a, rec_b):
    ja, jb = rec_a["sets"], rec_b["sets"]
    vals, unchanged, n = [], 0, 0
    for ra, rb in zip(ja, jb):
        for sa, sb in zip(ra, rb):
            j = jaccard(sa, sb)
            vals.append(j)
            unchanged += int(set(sa) == set(sb))
            n += 1
    return {"mean_jaccard": sum(vals) / n,
            "frac_unchanged": unchanged / n,
            "n_positions": n}


def mean_set_size(rec):
    sizes = [len(s) for r in rec["sets"] for s in r]
    return sum(sizes) / len(sizes)


def main():
    recs = [json.loads(l) for l in open(IN_JSONL)]
    by_epoch = {r["epoch"]: r for r in recs}
    ep = sorted(by_epoch)
    first, last = ep[0], ep[-1]
    mid = ep[len(ep) // 2]
    out = {
        "provenance": recs[0]["provenance"],
        "dataset": recs[0]["dataset"],
        "cell": recs[0]["cell"],
        "seed": recs[0]["seed"],
        "epochs": ep,
        "val_mse": {e: by_epoch[e]["val_mse"] for e in ep},
        "mean_set_size": {e: mean_set_size(by_epoch[e]) for e in ep},
        "score_entropy_mean": {e: by_epoch[e].get("score_entropy_mean") for e in ep},
        "candidates_mean": {e: by_epoch[e].get("candidates_mean") for e in ep},
        "jaccard_1_vs_last": compare(by_epoch[first], by_epoch[last]),
        "jaccard_1_vs_mid": compare(by_epoch[first], by_epoch[mid]),
        "jaccard_mid_vs_last": compare(by_epoch[mid], by_epoch[last]),
    }
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)

    jm = out["jaccard_1_vs_last"]
    rule = ("stable in practice (>= 0.9)" if jm["mean_jaccard"] >= 0.9
            else "drift present (< 0.9): report the measured drift")
    md = f"""# Gate 30 — R4 route-stability analysis

Single-seed descriptive probe: (8,4) cell, ETTh1, frozen protocol, seed 42; the
selected KV-block set per query position is snapshotted on the fixed first
validation batch after every epoch. Metric and rule frozen in `design.md`.

## Result

| Epoch pair | Mean Jaccard | Fraction unchanged | Positions |
|---|---|---|---|
| {first} vs {last} | {jm['mean_jaccard']:.4f} | {jm['frac_unchanged']:.4f} | {jm['n_positions']} |
| {first} vs {mid} | {out['jaccard_1_vs_mid']['mean_jaccard']:.4f} | {out['jaccard_1_vs_mid']['frac_unchanged']:.4f} | {out['jaccard_1_vs_mid']['n_positions']} |
| {mid} vs {last} | {out['jaccard_mid_vs_last']['mean_jaccard']:.4f} | {out['jaccard_mid_vs_last']['frac_unchanged']:.4f} | {out['jaccard_mid_vs_last']['n_positions']} |

Val MSE by epoch: {json.dumps(out['val_mse'])}.
Mean selected-set size by epoch: {json.dumps({k: round(v, 3) for k, v in out['mean_set_size'].items()})}.
Route-score entropy (mean over positions) by epoch: {json.dumps(out['score_entropy_mean'])}.
Mean finite candidates per position by epoch: {json.dumps(out['candidates_mean'])}.

**Predeclared rule applied:** mean Jaccard epoch {first} vs {last} = {jm['mean_jaccard']:.4f} -> {rule}.

## Scope

One seed, one cell, one fixed validation batch (see design.md); descriptive, no
significance claim. The trained-indexer half of R4 (D3) stays parked.
"""
    with open(OUT_MD, "w") as f:
        f.write(md)
    print(md)
    print(f"wrote {OUT_JSON}, {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
