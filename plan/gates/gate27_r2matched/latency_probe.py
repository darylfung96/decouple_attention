#!/usr/bin/env python3
"""Gate 27 amendment — latency for the projection-matched dense baseline.

Why: Figure 6 plots accuracy against audited latency. The released audit timed
three models (Normal / CSA (4,4) / DRRA (8,4)); the matched dense baseline needs
its own measurement under the SAME instrument, or its point cannot be placed.
Amendment recorded in design.md (measurement only; no analysis rule changes).

Method: import the canonical instrument (gate13 `last_query_latency.py`), add
Normal_r64 to its CONFIGS/LAST_FNS, run its own equality gate for the new model
(full vs last-query path must agree < 1e-5), then run the canonical 25x30
round-robin timing with four models. The released Normal/CSA/DRRA numbers are
the anchors; the probe reports same-run ratios so a loaded machine shifts all
four series together.

Run: ~/.uv_env/py311/bin/python plan/gates/gate27_r2matched/latency_probe.py
Writes: latency_4model.json / .md (this directory only).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / "plan" / "gates" / "gate13_p0_audits"), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch  # noqa: E402

import last_query_latency as lql  # noqa: E402  (canonical instrument, untouched)
from run import NormalR64TimeSeriesModel  # noqa: E402

OUT_JSON = HERE / "latency_4model.json"
OUT_MD = HERE / "latency_4model.md"
RELEASED = ROOT / "plan" / "gates" / "gate13_p0_audits" / "last_query_latency.json"


def equality_gate_r64():
    """Full vs last-query path must agree for the matched model (instrument gate)."""
    rows = []
    for seed in (0, 42, 123):
        torch.manual_seed(seed)
        model = NormalR64TimeSeriesModel(num_features=7).eval()
        x = torch.randn(2, 256, 7)
        with torch.no_grad():
            ref = lql.full_forward(model, x)
            got = lql.last_forward_normal(model, x)
        d = (ref - got).abs().max().item()
        rows.append({"seed": seed, "maxdiff": d, "pass": bool(d < lql.TOL)})
    return rows


def main():
    gate = equality_gate_r64()
    print("equality gate (Normal_r64 full vs last):", gate)
    if not all(r["pass"] for r in gate):
        raise SystemExit("equality gate FAILED — do not time the last-query path")

    lql.CONFIGS["Normal_r64"] = NormalR64TimeSeriesModel
    lql.LAST_FNS["Normal_r64"] = lql.last_forward_normal

    lat = lql.canonical_latency()
    released = json.load(open(RELEASED))["latency"]

    # Reproduction check: same-run vs released for the three shared models.
    recon = {}
    for name in ("Normal", "CSA_4_4", "DRRA_8_4"):
        for path in ("FULL", "LAST"):
            key = f"{name}_{path}"
            same = lat[key]["mean_ms"]
            rel = released[key]["mean_ms"]
            recon[key] = {"same_run": same, "released": rel, "ratio": same / rel}
    worst = max(abs(v["ratio"] - 1.0) for v in recon.values())
    recon_ok = worst <= 0.15

    # Ratio-anchored placement for the matched model on the released scale.
    anchored = {}
    for path in ("FULL", "LAST"):
        ratio = lat[f"Normal_r64_{path}"]["mean_ms"] / lat[f"Normal_{path}"]["mean_ms"]
        anchored[path] = {"ratio_vs_same_run_Normal": ratio,
                          "released_anchored_ms": released[f"Normal_{path}"]["mean_ms"] * ratio}

    out = {"equality_gate": gate, "latency": lat, "reproduction_vs_released": recon,
           "reproduction_ok_15pct": bool(recon_ok), "worst_ratio_dev": worst,
           "r64_anchored": anchored,
           "method": "gate13 canonical instrument, 4 models round-robin, 25x30, B=32, L=256"}
    OUT_JSON.write_text(json.dumps(out, indent=2))

    L = ["# Gate 27 amendment — matched dense baseline latency", "",
         "Instrument: gate13 `last_query_latency.py`, reused unmodified (4 models, 25x30 round-robin, "
         "B=32, L=256). Equality gate for Normal_r64: "
         + ", ".join(f"seed {r['seed']} {r['maxdiff']:.1e}" for r in gate), "",
         "## Same-run reproduction of the released numbers", "",
         "| config | path | same run (ms) | released (ms) | ratio |", "|---|---|---|---|---|"]
    for k, v in recon.items():
        L.append(f"| {k} | | {v['same_run']:.2f} | {v['released']:.2f} | {v['ratio']:.3f} |")
    L += ["", f"Worst deviation vs released: {worst*100:.1f}% "
              f"({'within' if recon_ok else 'OUTSIDE'} the 15% reproduction band)", "",
          "## Matched model", "",
          "| path | raw same-run (ms) | ratio vs same-run Normal | released-anchored (ms) |",
          "|---|---|---|---|"]
    for path in ("FULL", "LAST"):
        a = anchored[path]
        L.append(f"| {path} | {lat[f'Normal_r64_{path}']['mean_ms']:.2f} | "
                 f"{a['ratio_vs_same_run_Normal']:.3f} | {a['released_anchored_ms']:.2f} |")
    OUT_MD.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\nwrote {OUT_JSON.name}, {OUT_MD.name}")


if __name__ == "__main__":
    main()
