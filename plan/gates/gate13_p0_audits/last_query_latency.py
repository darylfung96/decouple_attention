"""A-2 + B1-2: canonical full-vs-last latency + realized unique-block counts.

Design: plan/gates/gate13_p0_audits/a2_b12_design.md (pre-registered).
Source untouched — last-query paths replicated in-script and gated on
equality (< 1e-5) before timing. Canonical env: ~/.uv_env/py311 (torch 2.6.0).

Run: ~/.uv_env/py311/bin/python plan/gates/gate13_p0_audits/last_query_latency.py
"""
import json
import statistics
import sys
import time
import torch
import torch.nn.functional as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from model import NormalTimeSeriesModel, CSATimeSeriesModel, ExpertPlusPlusTimeSeriesModel
from attention import apply_rotary_pos_emb

OUT_JSON = Path(__file__).with_name("last_query_latency.json")
OUT_MD = Path(__file__).with_name("last_query_latency.md")

CONFIGS = {"Normal": NormalTimeSeriesModel, "CSA_4_4": CSATimeSeriesModel,
           "DRRA_8_4": ExpertPlusPlusTimeSeriesModel}
LAST_POS = 255
TOL = 1e-5
ROUNDS, PASSES = 25, 30


def full_forward(model, x):
    return model(x)


def _embed(model, x):
    return model.input_proj(x) + model.pos_embedding


def _single_q(attn, h1, pos_id=255):
    """Exact single-token Q + RoPE (position 255)."""
    B = h1.shape[0]
    pos_1 = torch.full((B, 1), pos_id, device=h1.device, dtype=torch.long)
    cos_1, sin_1 = attn.rotary_emb(h1, pos_1)
    q_r1 = attn.q_a_norm(attn.q_a_proj(h1))
    H, D = attn.num_heads, attn.head_dim
    # SOURCE ORDER: view+transpose first, then q_b_norm (per-head over D=32,
    # not joint over H*D=128) — matches NormalAttention/BaseCSAAttention.forward.
    q_1 = attn.q_b_proj(q_r1).view(B, 1, H, D).transpose(1, 2)
    q_1 = attn.q_b_norm(q_1)
    return apply_rotary_pos_emb(q_1, cos_1, sin_1), q_r1, cos_1, sin_1


def last_forward_normal(model, x):
    attn = model.attn
    B, S, _ = x.shape
    H, D = attn.num_heads, attn.head_dim
    h = _embed(model, x)
    pos_full = torch.arange(S, device=x.device).unsqueeze(0).expand(B, -1)
    cos_f, sin_f = attn.rotary_emb(h, pos_full)
    kv = attn.kv_norm(attn.kv_proj(h)).view(B, S, 1, D).transpose(1, 2)
    kv = apply_rotary_pos_emb(kv, cos_f, sin_f)
    q_1, _, cos_1, sin_1 = _single_q(attn, h[:, LAST_POS:LAST_POS + 1, :])
    w = torch.matmul(q_1, kv.transpose(2, 3).float()) * (D ** -0.5)
    w = w - w.max(dim=-1, keepdim=True).values  # all K <= 255 visible, no mask
    probs = F.softmax(w, dim=-1, dtype=w.dtype)
    o = torch.matmul(probs, kv.to(probs.dtype))
    o = apply_rotary_pos_emb(o, cos_1, -sin_1)
    grouped = o.transpose(1, 2).reshape(B, 1, attn.o_groups, -1)
    o = attn.o_b_proj(attn.o_a_proj(grouped).flatten(2))
    h1 = h[:, LAST_POS:LAST_POS + 1, :]
    t = model.norm1(h1 + o)
    t = model.norm2(t + model.mlp(t))
    return model.output_proj(t[:, -1, :]).view(B, model.horizon, model.num_features)


def _full_selection(attn, h, q, q_res, cos_f, sin_f, B, S):
    """Verbatim copy of BaseCSAAttention.forward selection block (for variant-a + B1-2)."""
    n_win = S // attn.compress_rate
    usable = n_win * attn.compress_rate
    compressed_kv = attn._compress_kv(h, n_win, usable)
    compressed_idx = attn._compress_idx(h, n_win, usable)
    n_idx = compressed_idx.shape[2]
    q_idx = attn._index_query(q, q_res, cos_f, sin_f, B, S)
    scores = torch.matmul(q_idx.float(), compressed_idx.transpose(-1, -2).float())
    scores = F.relu(scores) * (attn.index_head_dim ** -0.5)
    weights = attn.idx_weights_proj(h).float() * (attn.index_n_heads ** -0.5)
    index_scores = (scores.permute(0, 2, 1, 3) * weights.unsqueeze(-1)).sum(dim=2)
    top_k = min(attn.index_topk, n_idx)
    q_pos = torch.arange(S, device=h.device)
    idx_pos, idx_scale = attn._build_idx_positions(S, h.device)
    future_mask = (idx_pos + idx_scale - 1).unsqueeze(0) > q_pos.view(-1, 1)
    index_scores = index_scores.masked_fill(future_mask, float('-inf'))
    top_k_indices = index_scores.topk(top_k, dim=-1).indices
    safe = top_k_indices.clamp(0, n_idx - 1)
    oob = top_k_indices >= n_idx
    invalid = (idx_pos[safe] + idx_scale[safe] - 1 > q_pos.view(1, -1, 1)) | oob
    top_k_indices = torch.where(invalid, n_idx, top_k_indices)
    kv_blocks, n_kv = attn._postprocess_topk(top_k_indices, index_scores, n_idx, S, h.device)
    return compressed_kv, kv_blocks, n_kv, top_k_indices, n_idx


def last_forward_csa(model, x):
    """Standalone last-query forward (selection recomputed from q_1 = variant b)."""
    attn = model.attn
    B, S, _ = x.shape
    H, D = attn.num_heads, attn.head_dim
    h = _embed(model, x)
    pos_full = torch.arange(S, device=x.device).unsqueeze(0).expand(B, -1)
    cos_f, sin_f = attn.rotary_emb(h, pos_full)
    kv = attn.kv_norm(attn.kv_proj(h)).view(B, S, 1, D).transpose(1, 2)
    kv = apply_rotary_pos_emb(kv, cos_f, sin_f)
    n_win = S // attn.compress_rate
    usable = n_win * attn.compress_rate
    compressed_kv = attn._compress_kv(h, n_win, usable)
    compressed_idx = attn._compress_idx(h, n_win, usable)
    n_idx = compressed_idx.shape[2]

    h1 = h[:, LAST_POS:LAST_POS + 1, :]
    q_1, q_r1, cos_1, sin_1 = _single_q(attn, h1)
    # _index_query needs correctly-shaped q ([B,H,1,D]); base uses q_residual, EPP returns q.
    q_idx_1 = attn._index_query(q_1, q_r1, cos_1, sin_1, B, 1)
    scores_1 = torch.matmul(q_idx_1.float(), compressed_idx.transpose(-1, -2).float())
    scores_1 = F.relu(scores_1) * (attn.index_head_dim ** -0.5)
    weights_1 = attn.idx_weights_proj(h1).float() * (attn.index_n_heads ** -0.5)
    iscores_1 = (scores_1.permute(0, 2, 1, 3) * weights_1.unsqueeze(-1)).sum(dim=2)
    top_k = min(attn.index_topk, n_idx)
    idx_pos, idx_scale = attn._build_idx_positions(S, h.device)
    # q=255: assert every candidate block is fully in the past (no future mask needed)
    assert bool(((idx_pos + idx_scale - 1) <= LAST_POS).all()), "unexpected future block at q=255"
    topk_1 = iscores_1.topk(top_k, dim=-1).indices  # [B,1,topk]
    assert bool((topk_1 < n_idx).all()), "OOB index at q=255"
    if type(attn).__name__ == "ExpertPlusPlusAttention":
        # inline single-row of EPP._postprocess_topk (verified vs full row in gate)
        blocks = (topk_1.clamp(0, n_idx - 1) // 2)
        assert bool(((blocks * attn.compress_rate + attn.compress_rate - 1) <= LAST_POS).all())
        kv_idx_1, n_kv = blocks, S // attn.compress_rate
    else:
        kv_idx_1, n_kv = attn._postprocess_topk(topk_1, iscores_1, n_idx, 1, h.device)

    # single-row _attend replication (q_pos=255 → sliding window fully visible)
    # NOTE: block bias is sized by n_kv (KV blocks), not n_idx (index tokens) —
    # they differ for DRRA (32 vs 64); _attend receives post-_postprocess_topk n_idx=n_kv.
    n_kv = S // attn.compress_rate
    actual_window = min(attn.sliding_window, S)
    sw_k = kv[:, :, -actual_window:, :]
    total_k = torch.cat([sw_k, compressed_kv], dim=2)
    block_bias = torch.full((B, 1, 1, n_kv + 1), float('-inf'), device=x.device)
    block_bias.scatter_(-1, kv_idx_1.unsqueeze(1), 0.0)
    block_bias = block_bias[..., :n_kv]
    block_bias = attn._postprocess_block_bias(block_bias, compressed_kv)
    sw_mask = torch.zeros((B, 1, 1, actual_window), device=x.device)
    final_mask = torch.cat([sw_mask, block_bias], dim=-1)
    w = torch.matmul(q_1, total_k.transpose(2, 3)) * (D ** -0.5) + final_mask
    sinks = attn.sinks.reshape(1, -1, 1, 1).expand(B, -1, 1, -1)
    combined = torch.cat([w, sinks], dim=-1)
    combined = combined - combined.max(dim=-1, keepdim=True).values
    probs = F.softmax(combined, dim=-1, dtype=combined.dtype)[..., :-1]
    o = torch.matmul(probs.to(total_k.dtype), total_k)
    o = apply_rotary_pos_emb(o, cos_1, -sin_1)
    grouped = o.transpose(1, 2).reshape(B, 1, attn.o_groups, -1)
    o = attn.o_b_proj(attn.o_a_proj(grouped).flatten(2))
    t = model.norm1(h1 + o)
    t = model.norm2(t + model.mlp(t))
    return model.output_proj(t[:, -1, :]).view(B, model.horizon, model.num_features), topk_1


LAST_FNS = {"Normal": last_forward_normal, "CSA_4_4": lambda m, x: last_forward_csa(m, x)[0],
            "DRRA_8_4": lambda m, x: last_forward_csa(m, x)[0]}


def equality_gate():
    rows = []
    for name, ctor in CONFIGS.items():
        for seed in (0, 42, 123):
            torch.manual_seed(seed)
            model = ctor(num_features=7).eval()
            x = torch.randn(2, 256, 7)
            with torch.no_grad():
                ref = full_forward(model, x)
                if name == "Normal":
                    got = last_forward_normal(model, x)
                    sel = "n/a"
                else:
                    got, topk_1 = last_forward_csa(model, x)
                    # variant-a vs variant-b selection match at q=255
                    h = _embed(model, x)
                    B, S = 2, 256
                    attn = model.attn
                    pos_full = torch.arange(S).unsqueeze(0).expand(B, -1)
                    cos_f, sin_f = attn.rotary_emb(h, pos_full)
                    q_res = attn.q_a_norm(attn.q_a_proj(h))
                    Hh, Dd = attn.num_heads, attn.head_dim
                    q = attn.q_b_proj(q_res).view(B, S, Hh, Dd).transpose(1, 2)
                    q = attn.q_b_norm(q)  # source order: norm AFTER transpose
                    q = apply_rotary_pos_emb(q, cos_f, sin_f)
                    _, kvb_a, _, _, _ = _full_selection(attn, h, q, q_res, cos_f, sin_f, B, S)
                    sel = bool((kvb_a[:, 255:256, :] == (
                        (topk_1 // 2) if name == "DRRA_8_4"
                        else topk_1)).all())
                d = (ref - got).abs().max().item()
                rows.append({"config": name, "seed": seed, "maxdiff": d,
                             "pass": bool(d < TOL), "sel_match_ab": sel})
    return rows


def canonical_latency():
    torch.manual_seed(0)
    models = {n: ctor(num_features=7).eval() for n, ctor in CONFIGS.items()}
    xb = torch.randn(32, 256, 7)
    paths = [(n, "FULL") for n in CONFIGS] + [(n, "LAST") for n in CONFIGS]
    fns = {(n, "FULL"): (lambda m: (lambda x: full_forward(m, x)))(models[n]) for n in CONFIGS}
    fns.update({(n, "LAST"): (lambda m, fn=LAST_FNS[n]: (lambda x: fn(m, x)))(models[n])
                for n in CONFIGS})
    with torch.no_grad():
        for key in paths:
            for _ in range(5):
                fns[key](xb)
        round_times = {k: [] for k in paths}
        for _ in range(ROUNDS):
            for key in paths:  # round-robin alternation: shared machine noise
                t0 = time.perf_counter()
                for _ in range(PASSES):
                    fns[key](xb)
                round_times[key].append((time.perf_counter() - t0) / PASSES * 1000)
    out = {}
    for key in paths:
        ts = round_times[key]
        out[f"{key[0]}_{key[1]}"] = {"mean_ms": statistics.mean(ts),
                                     "stdev_ms": statistics.stdev(ts), "rounds": ROUNDS,
                                     "passes": PASSES}
    for n in CONFIGS:
        f, l = round_times[(n, "FULL")], round_times[(n, "LAST")]
        deltas = [b - a for a, b in zip(f, l)]
        m, sd = statistics.mean(deltas), statistics.stdev(deltas)
        out[f"{n}_paired_LAST_minus_FULL"] = {"mean_ms": m, "stdev_ms": sd,
                                              "ci95": 1.96 * sd / (ROUNDS ** 0.5)}
    # G-2: cross-model paired FULL deltas (same round-robin rounds share noise)
    for a, b in [("DRRA_8_4", "Normal"), ("CSA_4_4", "Normal"), ("DRRA_8_4", "CSA_4_4")]:
        fa, fb = round_times[(a, "FULL")], round_times[(b, "FULL")]
        deltas = [x - y for x, y in zip(fa, fb)]
        m, sd = statistics.mean(deltas), statistics.stdev(deltas)
        out[f"paired_FULL_{a}_minus_{b}"] = {"mean_ms": m, "stdev_ms": sd,
                                              "ci95": 1.96 * sd / (ROUNDS ** 0.5)}
    return out


def unique_blocks():
    """B1-2: realized unique KV blocks/query (post-postprocess, sentinel excluded)."""
    res = {}
    for name in ("CSA_4_4", "DRRA_8_4"):
        ctor = CONFIGS[name]
        per_q_counts, jaccards, raw_topk_unique = [], [], []
        for seed in (0, 42, 123):
            torch.manual_seed(seed)
            model = ctor(num_features=7).eval()
            attn = model.attn
            x = torch.randn(2, 256, 7)
            with torch.no_grad():
                h = _embed(model, x)
                B, S = 2, 256
                pos_full = torch.arange(S).unsqueeze(0).expand(B, -1)
                cos_f, sin_f = attn.rotary_emb(h, pos_full)
                q_res = attn.q_a_norm(attn.q_a_proj(h))
                Hh, Dd = attn.num_heads, attn.head_dim
                q = attn.q_b_proj(q_res).view(B, S, Hh, Dd).transpose(1, 2)
                q = attn.q_b_norm(q)  # source order: norm AFTER transpose
                q = apply_rotary_pos_emb(q, cos_f, sin_f)
                _, kvb, n_kv, raw, _ = _full_selection(attn, h, q, q_res, cos_f, sin_f, B, S)
                valid = kvb.clamp(0, n_kv - 1)  # sentinel n_kv → clamped; mask it out
                mask = kvb < n_kv
                for b in range(B):
                    sets = [set(valid[b, q_][mask[b, q_]].tolist()) for q_ in range(S)]
                    per_q_counts += [len(s) for s in sets]
                    raw_topk_unique += [len(set(raw[b, q_].tolist())) for q_ in range(S)]
                    jaccards += [len(sets[q_] & sets[q_ + 1]) / max(1, len(sets[q_] | sets[q_ + 1]))
                                 for q_ in range(S - 1)]
        res[name] = {"n_kv_blocks": S // (8 if name == "DRRA_8_4" else 4),
                     "window": 16 if name == "DRRA_8_4" else 32,
                     "unique_valid_mean": statistics.mean(per_q_counts),
                     "unique_valid_min": min(per_q_counts), "unique_valid_max": max(per_q_counts),
                     "raw_topk_unique_mean": statistics.mean(raw_topk_unique),
                     "adjacent_jaccard_mean": statistics.mean(jaccards)}
    return res


def main():
    env = {"python": sys.version.split()[0], "torch": torch.__version__}
    gate = equality_gate()
    ok = all(r["pass"] for r in gate)
    result = {"env": env, "tol": TOL, "equality_gate": gate, "gate_pass": ok}
    if not ok:
        result["verdict"] = "STOP — replication mismatch, debug before timing."
    else:
        result["latency"] = canonical_latency()
        result["unique_blocks"] = unique_blocks()
        result["verdict"] = "PASS"
    OUT_JSON.write_text(json.dumps(result, indent=2))
    L = ["# A-2 canonical latency + B1-2 unique blocks", "",
         f"Env: `{env}` | gate: **{'PASS' if ok else 'FAIL'}**", "",
         "| config | seed | maxdiff LASTvsFULL | pass | sel(a)==sel(b) |",
         "|---|---|---|---|---|"]
    L += [f"| {r['config']} | {r['seed']} | {r['maxdiff']:.2e} | {r['pass']} | {r['sel_match_ab']} |"
          for r in gate]
    if ok:
        L += ["", "## Canonical latency (25 rounds x 30, B=32, round-robin alternating)", ""]
        for k, v in result["latency"].items():
            L.append(f"- {k}: `{v}`")
        L += ["", "## B1-2 realized unique blocks/query (synthetic batch; mechanics data-independent)", ""]
        for k, v in result["unique_blocks"].items():
            L.append(f"- {k}: `{v}`")
    OUT_MD.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\nwrote {OUT_JSON} {OUT_MD}")


if __name__ == "__main__":
    main()
