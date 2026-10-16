#!/usr/bin/env python3
"""Gate 26 — compare regenerated probes (post-mapping-fix) with Gate 12 history.

Reads gate26_results.json (this run) and ../gate12/gate12_results.json
(historical, read-only), prints the field-by-field comparison the R5 closeout
needs, and writes comparison.json.

Usage: ~/.uv_env/py311/bin/python plan/gates/gate26_r5probes/compare.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NEW = os.path.join(HERE, "gate26_results.json")
OLD = os.path.join(HERE, "..", "gate12", "gate12_results.json")
OUT = os.path.join(HERE, "comparison.json")

VARIANTS = ["Normal", "Flat", "DRRA"]


def main():
    if not os.path.exists(NEW):
        print(f"missing {NEW}; probe run not finished")
        return 1
    new = json.load(open(NEW))
    old = json.load(open(OLD))

    out = {"models": {}, "per_channel_delayedcopy": {}, "cp_distance": {},
           "signal_dependence": {}}

    print("== model val/test MSE: gate12 (historical) -> gate26 (regenerated) ==")
    for k in sorted(new["models"]):
        o, n = old["models"].get(k), new["models"][k]
        print(f"  {k:28s} val {o['val_mse']:.4f} -> {n['val_mse']:.4f}   "
              f"test {o['test_mse']:.4f} -> {n['test_mse']:.4f}")
        out["models"][k] = {"val_old": o["val_mse"], "val_new": n["val_mse"],
                            "test_old": o["test_mse"], "test_new": n["test_mse"]}

    print("\n== (i) delayed-copy per-channel test MSE ==")
    for v in VARIANTS:
        o, n = old["per_channel_delayedcopy"][v], new["per_channel_delayedcopy"][v]
        print(f"  {v:8s} old {['%.5f' % x for x in o]}")
        print(f"  {v:8s} new {['%.5f' % x for x in n]}")
        out["per_channel_delayedcopy"][v] = {"old": o, "new": n}

    print("\n== (ii) change-point distance buckets (mean MSE) ==")
    for v in VARIANTS:
        o, n = old["cp_distance"][v], new["cp_distance"][v]
        for b in o:
            flag = "  <-- changed" if o[b]["mean_mse"] != n[b]["mean_mse"] else ""
            print(f"  {v:8s} {b:10s} {o[b]['mean_mse']:.3f} -> "
                  f"{n[b]['mean_mse']:.3f}{flag}")
        out["cp_distance"][v] = {"old": o, "new": n}
    # who is lowest in every bucket?
    for tag, src in (("gate12", old), ("gate26", new)):
        lows = {}
        for b in old["cp_distance"]["Normal"]:
            lows[b] = min(VARIANTS, key=lambda v: src["cp_distance"][v][b]["mean_mse"])
        print(f"  lowest cell per bucket ({tag}): {lows}")

    print("\n== (iii) signal-dependence correlations ==")
    for v in ("Flat", "DRRA"):
        o, n = old["signal_dependence"][v], new["signal_dependence"][v]
        print(f"  {v:6s} old mean_dval {o['mean_dval_pct']:+.2f}%  "
              f"r_lag1 {o['pearson_dval_vs_lag1']['r']:+.3f} (p={o['pearson_dval_vs_lag1']['p']:.3f})")
        print(f"  {v:6s} new mean_dval {n['mean_dval_pct']:+.2f}%  "
              f"r_lag1 {n['pearson_dval_vs_lag1']['r']:+.3f} (p={n['pearson_dval_vs_lag1']['p']:.3f})")
        out["signal_dependence"][v] = {"old": o, "new": n}

    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
