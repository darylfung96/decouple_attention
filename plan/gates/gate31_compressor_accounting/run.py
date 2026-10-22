#!/usr/bin/env python3
"""Gate 31 — measure the executed compressor projections at L=256.

No training, no model files: one forward pass per cell with forward hooks on
the four compressor projections. Writes results.json.

Usage (repo root):
  ~/.uv_env/py311/bin/python plan/gates/gate31_compressor_accounting/run.py
"""
import json
import os
import sys
from datetime import datetime, timezone

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)

from expert_plus_plus_attention import ExpertPlusPlusAttention  # noqa: E402

D, DH, L = 128, 32, 256
NAMES = ["comp_kv_proj", "comp_gate_proj", "idx_kv_proj", "idx_gate_proj"]


def measure(ckv, cr):
    m = ExpertPlusPlusAttention(hidden_size=D, num_heads=4, head_dim=DH,
                                q_lora_rank=64, compress_rate=ckv,
                                index_compress_rate=cr, index_topk=16,
                                sliding_window=16, o_groups=4, o_lora_rank=64)
    x = torch.randn(1, L, D)
    counts, hooks = {}, []
    for name in NAMES:
        mod = getattr(m, name)

        def hook(mod_, inp, out, name=name):
            a = inp[0]
            n = a.numel() // a.shape[-1]
            counts[name] = counts.get(name, 0) + n * mod_.in_features * mod_.out_features

        hooks.append(mod.register_forward_hook(hook))
    with torch.no_grad():
        m(x)
    for h in hooks:
        h.remove()
    widths = {name: getattr(m, name).out_features for name in NAMES}
    return counts, widths


def main():
    out = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "geometry": {"d": D, "d_h": DH, "L": L},
        "paper_term": 2 * L * D * (64 + DH),
        "cells": {},
    }
    for cell in [(4, 4), (8, 4)]:
        counts, widths = measure(*cell)
        total = sum(counts[k] for k in NAMES)
        out["cells"][f"{cell}"] = {
            "per_projection": counts,
            "projection_widths": widths,
            "total": total,
            "per_token": total // L,
        }
        print(f"cell {cell}: widths {widths}")
        print(f"  per projection {counts}")
        print(f"  total {total:,d}  ({total // L:,d} MACs/token)")
        assert all(w == 2 * DH for w in widths.values()), widths
        assert total == 4 * L * D * 2 * DH, total
    out["executed_total"] = out["cells"]["(4, 4)"]["total"]
    out["undercount"] = out["executed_total"] - out["paper_term"]
    assert out["executed_total"] == 8_388_608, out["executed_total"]
    assert out["paper_term"] == 6_291_456, out["paper_term"]
    path = os.path.join(HERE, "results.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {path}")
    print(f"executed {out['executed_total']:,d} vs paper {out['paper_term']:,d} "
          f"(undercount {out['undercount']:,d} = "
          f"{100 * out['undercount'] / out['executed_total']:.1f}% of compressors)")


if __name__ == "__main__":
    main()
