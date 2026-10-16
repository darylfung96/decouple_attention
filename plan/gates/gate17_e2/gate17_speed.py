#!/usr/bin/env python3
"""Gate17 speed addendum: forward latency of the 4 PatchTST-grafted cells.

Same protocol family as the minimal-backbone Table speed run:
round-robin alternating across cells within each round (shared
thermal/contention window), warm-up excluded, B=32/L=256/F=7 random batch,
fp32 CPU. PatchTST head reads all patches, so only the FULL path exists
(no last-query variant).

Run: ~/.uv_env/py311/bin/python plan/gates/gate17_e2/gate17_speed.py
"""
import json
import statistics
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "plan" / "gates" / "gate17_e2"))

from plan.gates.gate17_e2.gate17_run import PatchTSTCells  # noqa: E402

ROUNDS, PASSES = 25, 30
CELLS = [(4, 4), (8, 4), (4, 8), (8, 8)]
NAMES = {(4, 4): "CSA", (8, 4): "DRRA", (4, 8): "C48", (8, 8): "C88"}
OUT_JSON = HERE / "gate17_speed.json"
OUT_MD = HERE / "gate17_speed.md"


def main():
    torch.set_num_threads(8)
    torch.manual_seed(42)
    models = {}
    for cell in CELLS:
        torch.manual_seed(42)
        models[cell] = PatchTSTCells(7, cell[0], cell[1]).eval()
    # shape check
    xb_check = torch.randn(2, 256, 7)
    with torch.no_grad():
        for cell, m in models.items():
            out = m(xb_check)
            assert tuple(out.shape) == (2, 96, 7), (cell, tuple(out.shape))
    print("shapes OK (all cells [B,96,7])", flush=True)
    torch.manual_seed(1)
    xb = torch.randn(32, 256, 7)
    with torch.no_grad():
        for m in models.values():
            for _ in range(5):
                m(xb)
        rt = {c: [] for c in CELLS}
        for _ in range(ROUNDS):
            for c in CELLS:
                t0 = time.perf_counter()
                for _ in range(PASSES):
                    models[c](xb)
                rt[c].append((time.perf_counter() - t0) / PASSES * 1000)
    res = {"latency": {}, "env": {"torch": torch.__version__},
           "protocol": "25 rounds x 30 passes, B=32/L=256/F=7, round-robin, 8 threads, fp32"}
    for c in CELLS:
        ts = rt[c]
        med = statistics.median(ts)
        res["latency"][f"{NAMES[c]}"] = {
            "mean_ms": statistics.mean(ts),
            "median_ms": med,
            "stdev_ms": statistics.stdev(ts),
            "min_ms": min(ts),
            "max_ms": max(ts),
        }
    base = res["latency"]["CSA"]["mean_ms"]
    for c in CELLS:
        n = NAMES[c]
        res["latency"][n]["vs_CSA"] = round(base / res["latency"][n]["mean_ms"], 3)
    OUT_JSON.write_text(json.dumps(res, indent=2))
    lines = ["# Gate17 PatchTST-transfer speed (FULL only, 25x30 round-robin B32)", "",
             "| cell | mean ms | median ms | stdev | vs CSA |",
             "|---|---|---|---|---|"]
    for c in CELLS:
        r = res["latency"][NAMES[c]]
        lines.append(f"| {NAMES[c]} {c} | {r['mean_ms']:.2f} | {r['median_ms']:.2f} | "
                     f"{r['stdev_ms']:.2f} | {r['vs_CSA']:.2f}x |")
    OUT_MD.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT_JSON} {OUT_MD}")


if __name__ == "__main__":
    main()
