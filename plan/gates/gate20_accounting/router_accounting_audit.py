#!/usr/bin/env python3
"""Gate 20 — component-accounting recheck (tensor-shape audit + corrected accounts).

Why this exists
---------------
The Q1 review (2026-10-16, item R8) asked for the routing term of the released
component accounting to be verified against tensor shapes rather than against a
second copy of the same formula. The original accounting (gate5_bench.py,
count_macs_with_profiler) charged the router `L * (L/c_R) * d_head` MACs per
sequence, i.e. ONE head's dot products. The executed module routes with the
main multi-head query (`_index_query` returns q of shape [B, H, S, d_head], the
index stream is [B, 1, n_idx, d_head]), so the score matmul is
[B, H, S, d_head] @ [B, 1, d_head, n_idx] and the router performs
H * d_head = d = 128 MACs per (query, index-token) pair.

This script measures that empirically: it monkey-patches torch.matmul, runs a
single forward pass through the real attention module for every tested cell,
records every matmul's operand and result shapes, and checks the arithmetic
against them. It then publishes corrected component accounts and every derived
quantity the paper quotes from them (attention-path savings table, whole-layer
projections, sensitivity bands, energy composition, Spearman validation), so no
paper number is left resting on the superseded formula.

Outputs: router_accounting_audit.json (+ .md). No training runs, no model files.

Usage (repo root):
  ~/.uv_env/py311/bin/python plan/gates/gate20_accounting/router_accounting_audit.py
"""
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO_ROOT)

import expert_plus_plus_attention as epp  # noqa: E402

# ---- frozen study geometry (must match paper Table 1 / gate2_factorial.py) --
H, DH, D = 4, 32, 128          # heads, head dim, hidden size (= H * DH)
W, F, HOR = 16, 7, 96          # window, features, horizon
L0 = 256                       # frozen-task lookback
CELLS = [(4, 4), (8, 4), (4, 8), (8, 8), (16, 4), (32, 4)]
GATE5 = os.path.join(REPO_ROOT, "plan", "gates", "gate5", "gate5_results.json")


# ---------------------------------------------------------------- accounting
def attn_normal(L):
    return 2 * H * L * L * DH


def attn_cell(L, ckv):
    return 2 * H * L * (L // ckv + W + 1) * DH


def router_term_old(L, cr):
    """Superseded: one head's dot products (gate5_bench.py charge)."""
    return L * (L // cr) * DH


def router_term(L, cr):
    """As executed: every head scores every index token (H * d_head = d)."""
    return L * (L // cr) * H * DH


def compress_term(L):
    return 2 * L * D * 64 + 2 * L * D * DH


def rest_exact(L, o_rank):
    wrapper = L * F * D + 2 * L * D * (4 * D) + D * (HOR * F)
    q_lora = L * D * 64 + L * 64 * (H * DH)
    kv = L * D * DH
    o_proj = L * (H * DH // 4) * (4 * o_rank) + L * (4 * o_rank) * D
    return wrapper + q_lora + kv + o_proj


def path_normal(L):
    return attn_normal(L)


def path_cell(L, ckv, cr):
    return attn_cell(L, ckv) + router_term(L, cr) + compress_term(L)


def s_attn(L, ckv, cr):
    return 1.0 - path_cell(L, ckv, cr) / path_normal(L)


def s_net(L, d, ckv, cr):
    attn_token = 2 * d * L
    cell_token = (2 * d * (L / ckv + W + 1) + d * L / cr
                  + 2 * d * (64 + DH))
    return 1.0 - (cell_token + 12 * d * d) / (attn_token + 12 * d * d)


def components(L=256):
    out = {}
    o_normal = L * (H * DH // 4) * (4 * 128) + L * (4 * 128) * D
    normal = {"wrapper": rest_exact(L, 128) - (L * D * 64 + L * 64 * H * DH)
              - L * D * DH - o_normal,
              "q_lora": L * D * 64 + L * 64 * (H * DH),
              "kv": L * D * DH,
              "attn": attn_normal(L),
              "o_proj": o_normal}
    normal["total"] = sum(normal.values())
    out["Normal"] = normal
    for name, ckv, cr in (("CSA", 4, 4), ("DRRA", 8, 4)):
        c = {"wrapper": normal["wrapper"], "q_lora": normal["q_lora"],
             "kv": normal["kv"], "attn": attn_cell(L, ckv),
             "router": router_term(L, cr), "compress": compress_term(L),
             "o_proj": L * (H * DH // 4) * (4 * 64) + L * (4 * 64) * D}
        c["total"] = sum(c.values())
        c["router_superseded"] = router_term_old(L, cr)
        c["total_superseded"] = c["total"] - c["router"] + c["router_superseded"]
        out[name] = c
    return out


# --------------------------------------------------- empirical shape audit
def shape_audit():
    """Run one forward pass per cell; record every matmul's shapes."""
    orig = torch.matmul
    calls, rows = [], []

    def spy(a, b):
        r = orig(a, b)
        calls.append((tuple(a.shape), tuple(b.shape), tuple(r.shape)))
        return r

    for ckv, cr in CELLS:
        calls.clear()
        torch.matmul = spy
        m = epp.ExpertPlusPlusAttention(
            D, H, DH, 64, compress_rate=ckv, index_compress_rate=cr,
            index_topk=16, index_n_heads=H, index_head_dim=DH,
            sliding_window=W, o_groups=4, o_lora_rank=64)
        m.eval()
        with torch.no_grad():
            m(torch.randn(1, L0, D))
        torch.matmul = orig

        # matmul 0 = index scoring (router), 1 = scores, 2 = values
        r_idx = calls[0][2]
        n_idx = r_idx[-1]
        macs = int(np.prod(r_idx) * calls[0][0][-1])
        rows.append({
            "cell": [ckv, cr],
            "matmuls": [{"a": list(a), "b": list(b), "r": list(r)}
                        for a, b, r in calls],
            "router_macs_per_seq": macs,
            "router_macs_analytic": router_term(L0, cr),
            "router_macs_superseded": router_term_old(L0, cr),
            "index_tokens": n_idx,
            "index_candidates_expected": L0 // cr,
            "attn_cols_scored": calls[1][2][-1],
            "attn_cols_expected": L0 // ckv + W,
            "match_router": macs == router_term(L0, cr),
            "match_cols": calls[1][2][-1] == L0 // ckv + W,
            "match_index_tokens": n_idx == L0 // cr,
        })
    return rows


def main():
    shape = shape_audit()
    assert all(r["match_router"] and r["match_cols"]
               and r["match_index_tokens"] for r in shape), \
        "shape audit failed — do not publish corrected accounts"

    comp = components(L0)
    g5 = json.load(open(GATE5))
    doc = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "why": ("Q1 review R8: verify the router term against tensor shapes. "
                "Executed router = H*d_head = d MACs per (query, index-token) "
                "pair; the superseded charge counted one head."),
        "geometry": {"H": H, "d_head": DH, "d": D, "W": W, "L0": L0},
        "shape_audit": shape,
        "components_L256": comp,
        "gate5_released_totals": {k: g5["macs"][k]["macs_per_seq"]
                                  for k in ("Normal", "Flat", "DRRA")},
    }

    # ---- derived quantities the paper quotes --------------------------------
    cells = [(4, 4), (8, 4), (16, 4), (32, 4)]
    doc["attention_path_savings_pct"] = {
        "contexts": [256, 1024, 4096, 8192, 32768, 131072],
        "cells": {f"({a},{b})": [round(100 * s_attn(L, a, b), 1)
                                 for L in (256, 1024, 4096, 8192, 32768, 131072)]
                  for a, b in cells},
        "asymptote": {f"({a},{b})": round(100 * (1 - (1 / a + 1 / (2 * b))), 1)
                      for a, b in cells},
    }
    doc["whole_layer_savings_pct_L32768"] = {
        f"d{d}": {"DRRA": round(100 * s_net(32768, d, 8, 4), 1),
                  "(32,4)": round(100 * s_net(32768, d, 32, 4), 1)}
        for d in (128, 512, 1024, 4096)}
    doc["whole_layer_savings_pct_d128"] = {
        f"L{L}": round(100 * s_net(L, 128, 8, 4), 1) for L in (2048, 4096, 32768)}
    doc["whole_layer_savings_pct_L2048_d128_CSA"] = round(
        100 * s_net(2048, 128, 4, 4), 1)
    doc["sensitivity_L32768_DRRA_aux_weight"] = {
        f"x{lam}": round(100 * (1 - (attn_cell(32768, 8)
                       + lam * (router_term(32768, 4) + compress_term(32768)))
                       / path_normal(32768)), 1)
        for lam in (0.5, 1.0, 2.0)}
    doc["sensitivity_single_head_indexer"] = {
        "as_executed_DRRA": round(100 * (1 - (1 / 8 + 1 / (2 * 4))), 1),
        "single_head_indexer_DRRA": round(
            100 * (1 - (attn_cell(32768, 8)
                        + router_term_old(32768, 4) + compress_term(32768))
                       / path_normal(32768)), 1),
    }
    doc["whole_model_saving_pct"] = {
        "DRRA_vs_Normal": round(100 * (1 - comp["DRRA"]["total"]
                                       / comp["Normal"]["total"]), 1),
        "CSA_vs_Normal": round(100 * (1 - comp["CSA"]["total"]
                                      / comp["Normal"]["total"]), 1),
        "DRRA_projection_matched": round(
            100 * (1 - comp["DRRA"]["total"]
                   / (comp["Normal"]["total"]
                      - (comp["Normal"]["o_proj"] - comp["CSA"]["o_proj"]))), 1),
        "projection_share_of_gap_pct": round(
            100 * (comp["Normal"]["o_proj"] - comp["CSA"]["o_proj"])
            / (comp["Normal"]["total"] - comp["DRRA"]["total"]), 1),
        "attention_path_DRRA_vs_Normal": round(
            100 * (1 - path_cell(256, 8, 4) / path_normal(256)), 1),
        "attention_core_DRRA_vs_Normal": round(
            100 * (1 - attn_cell(256, 8) / attn_normal(256)), 1),
        "attention_path_frozen_split_DRRA": {
            "core": attn_cell(256, 8), "router": router_term(256, 4),
            "compressors": compress_term(256)},
    }
    # energy composition at the study operating point (per-token, d=128)
    L = 2048
    dense = path_normal(L) / L + 12 * D * D
    doc["energy_composition_L2048_pct_of_dense_per_token"] = {
        "dense_core": round(100 * (path_normal(L) / L) / dense, 1),
        "CSA": {"core": round(100 * (attn_cell(L, 4) / L) / dense, 1),
                "router_compress": round(
                    100 * (router_term(L, 4) + compress_term(L)) / L / dense, 1)},
        "DRRA": {"core": round(100 * (attn_cell(L, 8) / L) / dense, 1),
                 "router_compress": round(
                     100 * (router_term(L, 4) + compress_term(L)) / L / dense, 1)},
        "fixed_block": round(100 * 12 * D * D / dense, 1),
        "attention_path_saving": {
            "CSA": round(100 * s_attn(L, 4, 4), 1),
            "DRRA": round(100 * s_attn(L, 8, 4), 1)},
        "whole_model_saving": {
            "CSA": round(100 * s_net(L, D, 4, 4), 1),
            "DRRA": round(100 * s_net(L, D, 8, 4), 1)},
    }

    # ---- directional validation against the measured latency sweep ----------
    def _rank(x):
        order = np.argsort(x)
        r = np.empty(len(x), dtype=float)
        r[order] = np.arange(1, len(x) + 1)
        return r

    def _spearman(a, b):
        return float(np.corrcoef(_rank(np.asarray(a, float)),
                                 _rank(np.asarray(b, float)))[0, 1])

    def _pearson(a, b):
        return float(np.corrcoef(np.asarray(a, float),
                                 np.asarray(b, float))[0, 1])

    val = {}
    for B in ("1", "32"):
        lat = g5["l_scale"][B]["latency"]
        t, w, wr, tr = [], [], [], []
        for Lstr, md in lat.items():
            if all(v in md for v in ("Normal", "Flat", "DRRA")):
                Li = int(Lstr)
                for v, pc in (("Normal", path_normal(Li)),
                              ("Flat", path_cell(Li, 4, 4)),
                              ("DRRA", path_cell(Li, 8, 4))):
                    t.append(md[v]["mean_ms_per_batch"])
                    w.append(pc)
            if "Normal" in md and "DRRA" in md:
                Li = int(Lstr)
                wr.append(path_cell(Li, 8, 4) / path_normal(Li))
                tr.append(md["DRRA"]["mean_ms_per_batch"]
                          / md["Normal"]["mean_ms_per_batch"])
        val[f"batch{B}"] = {"spearman_latency_vs_work": round(_spearman(t, w), 3),
                            "n_points": len(t),
                            "pearson_work_ratio_vs_time_ratio": round(_pearson(wr, tr), 3),
                            "n_ratios": len(wr)}
    doc["validation"] = val

    with open(os.path.join(HERE, "router_accounting_audit.json"), "w") as f:
        json.dump(doc, f, indent=1)

    lines = ["# Gate 20 — component-accounting recheck", "",
             f"Generated {doc['generated_utc']} · no training runs.", "",
             "## Shape audit (executed module, L=256)", "",
             "| cell | index tokens | cols scored (excl. sink) | router MACs/seq"
             " (measured) | corrected analytic | superseded charge |",
             "|---|---|---|---|---|---|"]
    for r in shape:
        lines.append(f"| ({r['cell'][0]},{r['cell'][1]}) | {r['index_tokens']} "
                     f"| {r['attn_cols_scored']} | {r['router_macs_per_seq']:,} "
                     f"| {r['router_macs_analytic']:,} "
                     f"| {r['router_macs_superseded']:,} |")
    lines += ["", "## Corrected component accounts at L=256 (MACs/seq)", "",
              "| component | Normal | CSA (4,4) | DRRA (8,4) |", "|---|---|---|---|"]
    for k in ("wrapper", "q_lora", "kv", "attn", "router", "compress", "o_proj"):
        row = []
        for m in ("Normal", "CSA", "DRRA"):
            v = comp[m].get(k)
            row.append("---" if v is None else f"{v:,}")
        lines.append(f"| {k} | " + " | ".join(row) + " |")
    lines.append("| **total** | " + " | ".join(
        f"**{comp[m]['total']:,}**" for m in ("Normal", "CSA", "DRRA")) + " |")
    lines += ["",
              f"Superseded totals: CSA {comp['CSA']['total_superseded']:,}, "
              f"DRRA {comp['DRRA']['total_superseded']:,} "
              f"(released gate5 values).", "",
              "## Derived numbers", "",
              "```", json.dumps({k: v for k, v in doc.items()
                                 if k not in ("shape_audit", "components_L256",
                                              "gate5_released_totals")},
                                indent=1), "```"]
    with open(os.path.join(HERE, "router_accounting_audit.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines[-8:]))
    print(f"\nshapes: all {len(shape)} cells match the corrected analytic term")


if __name__ == "__main__":
    main()
