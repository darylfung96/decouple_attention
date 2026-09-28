"""B2-1: router grad audit — does the indexer learn via task MSE?

Design: plan/gates/gate13_p0_audits/design.md (pre-registered).
Method: one training step on synthetic standardized batch (architecture question,
data-independent); per-param grad norms + one-SGD-step deltas; indexer-exclusive
vs compressor vs shared groups reported separately.

Pre-registered expectation: indexer-exclusive ~0 (hard top-k dead-end), with the
possible exception of idx_weights_proj (continuous pre-topk mixing — reported
separately, NOT proof routing learns).

Run: python plan/gates/gate13_p0_audits/router_grad_audit.py
"""
import json
import sys
import torch
import torch.nn as nn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from model import CSATimeSeriesModel, ExpertPlusPlusTimeSeriesModel

OUT_JSON = Path(__file__).with_name("router_grad_audit.json")
OUT_MD = Path(__file__).with_name("router_grad_audit.md")

INDEXER_SUBSTR = ["idx_kv_proj", "idx_gate_proj", "idx_position_bias", "idx_norm",
                  "idx_weights_proj", "idx_q_proj"]


def group_of(name):
    if any(s in name for s in INDEXER_SUBSTR):
        return "indexer-exclusive"
    if "comp_" in name:
        return "compressor"
    return "shared/other"


def audit(ctor, label):
    torch.manual_seed(42)
    model = ctor(num_features=7).train()
    x = torch.randn(2, 256, 7)
    y = torch.randn(2, 96, 7)
    model.zero_grad()
    out = model(x)
    loss = nn.MSELoss()(out, y)
    loss.backward()
    rows = []
    for name, p in model.named_parameters():
        g = 0.0 if p.grad is None else float(p.grad.detach().float().norm().item())
        rows.append({"param": name, "group": group_of("." + name + ".") if False else group_of(name),
                     "grad_norm": g, "has_grad": bool(p.grad is not None)})
    # One SGD step deltas
    before = {n: p.detach().clone() for n, p in model.named_parameters()}
    with torch.no_grad():
        for p in model.parameters():
            if p.grad is not None:
                p -= 1e-3 * p.grad
    for r in rows:
        d = (dict(model.named_parameters())[r["param"]].detach() - before[r["param"]]).float().norm().item()
        r["sgd_delta"] = float(d)
    idx_rows = [r for r in rows if r["group"] == "indexer-exclusive"]
    idx_learns = any(r["grad_norm"] > 1e-12 for r in idx_rows)
    return {"model": label, "loss": float(loss.item()), "rows": rows,
            "indexer_learns": bool(idx_learns)}


def main():
    results = {"seed": 42, "batch": "[2,256,7]->[2,96,7] synthetic standardized",
               "audits": [audit(CSATimeSeriesModel, "CSA_4_4"),
                          audit(ExpertPlusPlusTimeSeriesModel, "DRRA_8_4")]}
    verdicts = []
    for a in results["audits"]:
        idx = [(r["param"], r["grad_norm"]) for r in a["rows"] if r["group"] == "indexer-exclusive"]
        verdicts.append(f"{a['model']}: indexer {'LEARN (nonzero grads: ' + str(idx) + ')' if a['indexer_learns'] else 'DOES-NOT-LEARN (all ~0)'}")
    results["verdict"] = " | ".join(verdicts)
    OUT_JSON.write_text(json.dumps(results, indent=2))
    lines = ["# B2-1 router grad audit", "", f"Verdict: **{results['verdict']}**", "",
             "Note: `idx_weights_proj` mixes continuously BEFORE topk — nonzero there alone is not proof routing learns; "
             "selection-path params (`idx_kv_proj/idx_gate_proj/idx_position_bias/idx_norm`, CSA `idx_q_proj`) are the test.", ""]
    for a in results["audits"]:
        lines += [f"## {a['model']} (loss {a['loss']:.4f})", "",
                  "| param | group | grad_norm | sgd_delta |", "|---|---|---|---|"]
        for r in a["rows"]:
            lines.append(f"| {r['param']} | {r['group']} | {r['grad_norm']:.3e} | {r['sgd_delta']:.3e} |")
        lines.append("")
    OUT_MD.write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nwrote {OUT_JSON} {OUT_MD}")


if __name__ == "__main__":
    main()
