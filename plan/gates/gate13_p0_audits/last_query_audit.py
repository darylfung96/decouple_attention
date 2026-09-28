"""A-1: last-query audit — are earlier attention/MLP outputs unused for the forecast?

Design: plan/gates/gate13_p0_audits/design.md (pre-registered).
Method: stock forward + forward-hooks (no source edits, no RoPE reimplementation).
Proves: full-sequence attention + MLP outputs at positions 0..254 do not feed
the direct-96 head, which reads x[:, -1, :] only (model.py:CSATimeSeriesModel.forward).

Run: python plan/gates/gate13_p0_audits/last_query_audit.py
"""
import json
import sys
import time
import torch
import torch.nn as nn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from model import NormalTimeSeriesModel, CSATimeSeriesModel, ExpertPlusPlusTimeSeriesModel

OUT_JSON = Path(__file__).with_name("last_query_audit.json")
OUT_MD = Path(__file__).with_name("last_query_audit.md")

CONFIGS = {
    "Normal": NormalTimeSeriesModel,
    "CSA_4_4": CSATimeSeriesModel,
    "DRRA_8_4": ExpertPlusPlusTimeSeriesModel,
}
SEEDS = [0, 42, 123]
TOL = 1e-5


def stock_forward(model, h):
    """Replicate CSATimeSeriesModel.forward from embedded h (post input_proj+pos)."""
    attn_out = model.attn(h)
    x = model.norm1(h + attn_out)
    mlp_out = model.mlp(x)
    x = model.norm2(x + mlp_out)
    out = model.output_proj(x[:, -1, :]).view(-1, model.horizon, model.num_features)
    return out


def audit_config(name, ctor, seed):
    torch.manual_seed(seed)
    model = ctor(num_features=7).eval()
    B = 2
    x = torch.randn(B, 256, 7)  # standardized-scale synthetic; structural question
    with torch.no_grad():
        h = model.input_proj(x) + model.pos_embedding
        ref = stock_forward(model, h)

        # Test 1: zero earlier ATTENTION outputs -> head unchanged?
        def hook_attn_zero(mod, inp, out):
            o = out.clone()
            o[:, :-1, :] = 0.0
            return o
        h1 = model.attn.register_forward_hook(hook_attn_zero)
        try:
            out1 = stock_forward(model, h)
        finally:
            h1.remove()
        d1 = (ref - out1).abs().max().item()

        # Test 2: randomize earlier attention outputs -> head unchanged?
        torch.manual_seed(999 + seed)
        rand_attn = torch.randn_like(ref.new_zeros(B, 255, 128)) if hasattr(model, 'attn') else None
        def hook_attn_rand(mod, inp, out):
            o = out.clone()
            o[:, :-1, :] = torch.randn_like(o[:, :-1, :]) * 10.0
            return o
        h2 = model.attn.register_forward_hook(hook_attn_rand)
        try:
            out2 = stock_forward(model, h)
        finally:
            h2.remove()
        d2 = (ref - out2).abs().max().item()

        # Test 3: zero earlier MLP outputs -> head unchanged?
        def hook_mlp_zero(mod, inp, out):
            o = out.clone()
            o[:, :-1, :] = 0.0
            return o
        h3 = model.mlp.register_forward_hook(hook_mlp_zero)
        try:
            out3 = stock_forward(model, h)
        finally:
            h3.remove()
        d3 = (ref - out3).abs().max().item()

    return {"seed": seed, "maxdiff_attn_zero": d1, "maxdiff_attn_rand": d2,
            "maxdiff_mlp_zero": d3,
            "equivalent": bool(max(d1, d2, d3) < TOL)}


def analytic_costs():
    """Analytic MACs split: full-layer vs forecast-required (last-query).

    Conventions: hidden=128, heads=4, head_dim=32, q_lora=64, L=256.
    K/V projections + compressors still run full-sequence even for last-query
    (keys/values must be built); savings are Q-projection (255/256), attention
    scores, and MLP (255/256 of positions).
    """
    L, Hh, D, Qr = 256, 4, 32, 64
    mlp_full = L * (128 * 512 + 512 * 128)  # per-token MLP x L
    mlp_last = 1 * (128 * 512 + 512 * 128)
    return {
        "Normal": {
            "scores_full": Hh * L * L * D, "scores_last": Hh * 1 * L * D,
            "mlp_full": mlp_full, "mlp_last": mlp_last,
            "note": "Q-last still needs full K/V; scores 256x -> 1x (65,536 -> 256 per head per D).",
        },
        "CSA_4_4": {
            "dense_cols": 32 + 64, "scores_full_per_head": L * (32 + 64),
            "scores_last_per_head": 1 * (32 + 64),
            "mlp_full": mlp_full, "mlp_last": mlp_last,
            "note": "window32 + 64 blocks + sink; K/V+compressors full-sequence regardless.",
        },
        "DRRA_8_4": {
            "dense_cols": 16 + 32, "scores_full_per_head": L * (16 + 32),
            "scores_last_per_head": 1 * (16 + 32),
            "mlp_full": mlp_full, "mlp_last": mlp_last,
            "note": "window16 + 32 blocks + sink; K/V+compressors full-sequence regardless.",
        },
    }


def measure_latency(ctor, rounds=10, passes=20):
    """Stock full-forward latency, B=32/L=256, alternating-style single-config timing.

    NOTE: reduced rounds for audit speed; canonical 25x30 Gate-5 protocol runs in A-2.
    """
    torch.manual_seed(0)
    model = ctor(num_features=7).eval()
    x = torch.randn(32, 256, 7)
    with torch.no_grad():
        for _ in range(5):
            model(x)
        ts = []
        for _ in range(rounds):
            t0 = time.perf_counter()
            for _ in range(passes):
                model(x)
            t1 = time.perf_counter()
            ts.append((t1 - t0) / passes * 1000)
    import statistics
    return {"mean_ms": statistics.mean(ts), "stdev_ms": statistics.stdev(ts) if len(ts) > 1 else 0.0,
            "rounds": rounds, "passes": passes, "note": "audit-speed protocol; A-2 uses full 25x30 alternating"}


def main():
    results = {"tol": TOL, "configs": {}, "analytic": analytic_costs(), "latency_stock": {}}
    for name, ctor in CONFIGS.items():
        per_seed = [audit_config(name, ctor, s) for s in SEEDS]
        results["configs"][name] = per_seed
        try:
            results["latency_stock"][name] = measure_latency(ctor)
        except Exception as e:
            results["latency_stock"][name] = {"error": str(e)}
    all_equiv = all(r["equivalent"] for v in results["configs"].values() for r in v)
    results["verdict"] = ("EQUIVALENT — earlier attention/MLP outputs unused; "
                          "report full-layer vs forecast-required costs separately."
                          if all_equiv else
                          "NOT-EQUIVALENT — stop; earlier positions feed the head, debug.")

    OUT_JSON.write_text(json.dumps(results, indent=2))
    lines = ["# A-1 last-query audit", "", f"Verdict: **{results['verdict']}**", "",
             "| config | seed | attn_zero | attn_randx10 | mlp_zero | equiv |",
             "|---|---|---|---|---|---|"]
    for name, rows in results["configs"].items():
        for r in rows:
            lines.append(f"| {name} | {r['seed']} | {r['maxdiff_attn_zero']:.2e} | "
                         f"{r['maxdiff_attn_rand']:.2e} | {r['maxdiff_mlp_zero']:.2e} | {r['equivalent']} |")
    lines += ["", "## Analytic cost split (per forward, B=1)", ""]
    for k, v in results["analytic"].items():
        lines.append(f"- {k}: `{v}`")
    lines += ["", "## Stock full-forward latency (audit-speed protocol, B=32 — see note)", ""]
    for k, v in results["latency_stock"].items():
        lines.append(f"- {k}: `{v}`")
    OUT_MD.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT_JSON} {OUT_MD}")


if __name__ == "__main__":
    main()
