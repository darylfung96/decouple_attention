# Cell speed addendum: FULL vs LAST latency for Normal / (8,4) / (16,4) / (32,4).
# (16,4) and (32,4) were never benchmarked; this answers that with data.
# Design: same protocol as last_query_latency.py (25 rounds x 30, B=32/L=256,
# round-robin alternating, uv python torch 2.6.0). Generic per-token mapping.
# Run: ~/.uv_env/py311/bin/python plan/gates/gate13_p0_audits/cell_speed.py
import json
import statistics
import sys
import time
import torch
import torch.nn.functional as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "plan" / "gates" / "gate2"))

from model import NormalTimeSeriesModel
from gate2_factorial import EPPTimeSeriesModel
from attention import apply_rotary_pos_emb
from last_query_latency import _embed, _single_q

OUT_JSON = Path(__file__).with_name("cell_speed.json")
OUT_MD = Path(__file__).with_name("cell_speed.md")
LAST_POS, TOL, ROUNDS, PASSES = 255, 1e-5, 25, 30


def make(name):
    if name == "Normal":
        return NormalTimeSeriesModel(num_features=7).eval()
    ck, cr = {"DRRA_8_4": (8, 4), "EPP_16_4": (16, 4), "EPP_32_4": (32, 4)}[name]
    return EPPTimeSeriesModel(7, ck, cr, q_lora_rank=64, o_lora_rank=64).eval()


def last_forward_epp(model, x):
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
    n_kv = S // attn.compress_rate
    h1 = h[:, LAST_POS:LAST_POS + 1, :]
    q_1, q_r1, cos_1, sin_1 = _single_q(attn, h1)
    q_idx_1 = attn._index_query(q_1, q_r1, cos_1, sin_1, B, 1)
    scores_1 = torch.matmul(q_idx_1.float(), compressed_idx.transpose(-1, -2).float())
    scores_1 = F.relu(scores_1) * (attn.index_head_dim ** -0.5)
    weights_1 = attn.idx_weights_proj(h1).float() * (attn.index_n_heads ** -0.5)
    iscores_1 = (scores_1.permute(0, 2, 1, 3) * weights_1.unsqueeze(-1)).sum(dim=2)
    top_k = min(attn.index_topk, n_idx)
    idx_pos, idx_scale = attn._build_idx_positions(S, h.device)
    assert bool(((idx_pos + idx_scale - 1) <= LAST_POS).all())
    topk_1 = iscores_1.topk(top_k, dim=-1).indices
    assert bool((topk_1 < n_idx).all())
    per = n_idx // n_kv
    if n_idx == n_kv:
        kv_idx_1 = topk_1
    elif n_idx > n_kv:
        kv_idx_1 = topk_1.clamp(0, n_idx - 1) // per
    else:
        kv_idx_1 = torch.cat([topk_1 * (n_kv // n_idx) + j for j in range(n_kv // n_idx)], dim=-1)
    assert bool((((kv_idx_1 * attn.compress_rate + attn.compress_rate - 1) <= LAST_POS)).all())
    actual_window = min(attn.sliding_window, S)
    total_k = torch.cat([kv[:, :, -actual_window:, :], compressed_kv], dim=2)
    block_bias = torch.full((B, 1, 1, n_kv + 1), float('-inf'), device=x.device)
    block_bias.scatter_(-1, kv_idx_1.unsqueeze(1), 0.0)
    block_bias = block_bias[..., :n_kv]
    block_bias = attn._postprocess_block_bias(block_bias, compressed_kv)
    final_mask = torch.cat([torch.zeros((B, 1, 1, actual_window), device=x.device),
                            block_bias], dim=-1)
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
    return model.output_proj(t[:, -1, :]).view(B, model.horizon, model.num_features)


def main():
    names = ["Normal", "DRRA_8_4", "EPP_16_4", "EPP_32_4"]
    models = {n: make(n) for n in names}
    cols = {"Normal": 256, "DRRA_8_4": 48, "EPP_16_4": 32, "EPP_32_4": 16}
    gate, paths = [], {}
    torch.manual_seed(0)
    xb_check = torch.randn(2, 256, 7)
    with torch.no_grad():
        for n in names:
            ref = models[n](xb_check)
            got = last_forward_epp(models[n], xb_check) if n != "Normal" else None
            if got is None:  # Normal single-query path validated in A-2; re-time stock only
                from last_query_latency import last_forward_normal
                got = last_forward_normal(models[n], xb_check)
            d = (ref - got).abs().max().item()
            gate.append({"config": n, "maxdiff": d, "pass": bool(d < TOL)})
            paths[(n, "FULL")] = lambda x, m=models[n]: m(x)
    assert all(r["pass"] for r in gate), gate
    torch.manual_seed(1)
    xb = torch.randn(32, 256, 7)
    fns = dict(paths)
    for n in names:
        m = models[n]
        if n != "Normal":
            fns[(n, "LAST")] = (lambda mm: (lambda x: last_forward_epp(mm, x)))(m)
        else:
            from last_query_latency import last_forward_normal as _lfn
            fns[(n, "LAST")] = (lambda mm: (lambda x: _lfn(mm, x)))(m)
    keys = [(n, p) for n in names for p in ("FULL", "LAST")]
    with torch.no_grad():
        for k in keys:
            for _ in range(5):
                fns[k](xb)
        rt = {k: [] for k in keys}
        for _ in range(ROUNDS):
            for k in keys:
                t0 = time.perf_counter()
                for _ in range(PASSES):
                    fns[k](xb)
                rt[k].append((time.perf_counter() - t0) / PASSES * 1000)
    res = {"gate": gate, "cols_per_query": cols, "latency": {},
           "env": {"python": sys.version.split()[0], "torch": torch.__version__}}
    for k in keys:
        ts = rt[k]
        res["latency"][f"{k[0]}_{k[1]}"] = {"mean_ms": statistics.mean(ts),
                                            "stdev_ms": statistics.stdev(ts)}
    base = statistics.mean(rt[("Normal", "FULL")])
    for n in names[1:]:
        f = statistics.mean(rt[(n, "FULL")])
        res["latency"][f"speedup_FULL_{n}_vs_Normal"] = round(base / f, 3)
    OUT_JSON.write_text(json.dumps(res, indent=2))
    L = ["# Cell speed addendum (FULL vs LAST, 25x30 round-robin B32)", "",
         f"cols/query: `{cols}` | gate: PASS", "",
         "| path | mean ms | vs Normal FULL |",
         "|---|---|---|"]
    for n in names:
        for p in ("FULL", "LAST"):
            m = res["latency"][f"{n}_{p}"]["mean_ms"]
            L.append(f"| {n} {p} | {m:.2f} | {base / m:.2f}x |")
    for n in names[1:]:
        L.append(f"FULL speedup {n} vs Normal: {res['latency'][f'speedup_FULL_{n}_vs_Normal']}x")
    OUT_MD.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\nwrote {OUT_JSON} {OUT_MD}")


if __name__ == "__main__":
    main()
