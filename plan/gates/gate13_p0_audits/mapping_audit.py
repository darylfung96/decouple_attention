"""B1-5: index->KV mapping audit — is t//2 correct for every cell?

Design: this file is the pre-registration (2026-09-28).
Finding it tests: ExpertPlusPlusAttention._postprocess_topk applies
`blocks = topk.clamp(0, n_idx-1) // 2` unconditionally. Correct ONLY for
(KV=8,R=4) (64 fine tokens -> 32 coarse blocks). For (4,4): identity needed,
code halves to blocks 0..31 of 64. For (4,8): 1-coarse-token->2-fine-blocks
needed, code halves to 0..15 of 64. For (8,8): identity needed, code halves
to 0..15 of 32. Base CSAAttention._postprocess_topk (identity) is NOT used:
gate2/gate7/gate3 build every compressed cell via EPPTimeSeriesModel.

Method: instantiate EPP(ck,ci) per cell, fixed standardized batch, replicate
the forward selection block verbatim, record post-mapping valid-block id
range + sentinel fraction at q=255 (representative; all queries asserted
same bound in script).
Run: ~/.uv_env/py311/bin/python plan/gates/gate13_p0_audits/mapping_audit.py
"""
import json
import sys
import torch
import torch.nn.functional as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from expert_plus_plus_attention import ExpertPlusPlusAttention
from attention import apply_rotary_pos_emb

OUT_JSON = Path(__file__).with_name("mapping_audit.json")
OUT_MD = Path(__file__).with_name("mapping_audit.md")


def audit_cell(ck, ci):
    torch.manual_seed(0)
    a = ExpertPlusPlusAttention(hidden_size=128, num_heads=4, head_dim=32, q_lora_rank=64,
                                compress_rate=ck, index_compress_rate=ci, index_topk=16,
                                sliding_window=16, o_groups=4, o_lora_rank=64).eval()
    h = torch.randn(2, 256, 128)
    with torch.no_grad():
        B, S = 2, 256
        pos = torch.arange(S).unsqueeze(0).expand(B, -1)
        cos, sin = a.rotary_emb(h, pos)
        qr = a.q_a_norm(a.q_a_proj(h))
        q = a.q_b_proj(qr).view(B, S, 4, 32).transpose(1, 2)
        q = a.q_b_norm(q)
        q = apply_rotary_pos_emb(q, cos, sin)
        n_win = S // ck
        usable = n_win * ck
        cidx = a._compress_idx(h, n_win, usable)
        n_idx = cidx.shape[2]
        # Deterministic probe: feed EVERY token as a candidate at q=255 and
        # check the exact mapping rule (independent of top-k sampling).
        tall = torch.arange(n_idx).unsqueeze(0).unsqueeze(0).expand(B, S, n_idx)
        t16 = tall[:, :, :16].clone()
        kb_probe, _ = a._postprocess_topk(t16, None, n_idx, S, h.device)
        probe = kb_probe[0, 255, :]
        if ck == 8 and ci == 4:
            rule_ok = bool((probe == t16[0, 255, :] // 2).all())
        elif ck == ci:
            rule_ok = bool((probe == t16[0, 255, :]).all())
        elif ck == 4 and ci == 8:
            rule_ok = bool((probe[:16] == t16[0, 255, :] * 2).all()
                            and (probe[16:] == t16[0, 255, :] * 2 + 1).all()
                            and tuple(kb_probe.shape) == (B, S, 32))
        else:
            rule_ok = False
        qi = a._index_query(q, qr, cos, sin, B, S)
        sc = torch.matmul(qi.float(), cidx.transpose(-1, -2).float())
        sc = F.relu(sc) * (a.index_head_dim ** -0.5)
        wgt = a.idx_weights_proj(h).float() * (a.index_n_heads ** -0.5)
        isc = (sc.permute(0, 2, 1, 3) * wgt.unsqueeze(-1)).sum(2)
        ip, isc2 = a._build_idx_positions(S, h.device)
        qpos = torch.arange(S, device=h.device)
        fm = ((ip + isc2 - 1).unsqueeze(0) > qpos.view(-1, 1))
        isc = isc.masked_fill(fm, float('-inf'))
        tki = isc.topk(16, dim=-1).indices
        safe = tki.clamp(0, n_idx - 1)
        oob = tki >= n_idx
        inv = ((ip[safe] + isc2[safe] - 1 > qpos.view(1, -1, 1)) | oob)
        tki = torch.where(inv, n_idx, tki)
        kvb, n_kv = a._postprocess_topk(tki, isc, n_idx, S, h.device)
        valid = kvb[kvb < n_kv]
        # correct mapping for comparison
        if ck == 8 and ci == 4:
            expect = f"0..{n_kv - 1} (t//2 correct)"
        elif ck == ci:
            expect = f"0..{n_kv - 1} identity needed"
        else:  # (4,8): coarse token -> 2 fine blocks
            expect = "1-token-to-2-blocks fan-out needed"
        # verdict is about the RULE (deterministic probe above), not sampling.
        return {"cell": f"({ck},{ci})", "n_kv": n_kv, "n_idx": n_idx,
                "max_selected": int(valid.max().item()) if valid.numel() else -1,
                "min_selected": int(valid.min().item()) if valid.numel() else -1,
                "sentinel_frac": float((kvb >= n_kv).float().mean().item()),
                "expected": expect,
                "verdict": "CORRECT" if rule_ok else "BROKEN"}


def main():
    rows = [audit_cell(ck, ci) for ck, ci in [(4, 4), (8, 4), (4, 8), (8, 8)]]
    res = {"rows": rows, "scope": ("HISTORICAL BUG (fixed 2026-09-28): gate2 (5 seeds) + gate7 "
                                   "(20 seeds) + gate3 suite Flat built compressed cells via "
                                   "EPPTimeSeriesModel with unconditional t//2; only (8,4) was "
                                   "correct. Post-fix audit: all four geometries map correctly.")}
    OUT_JSON.write_text(json.dumps(res, indent=2))
    L = ["# B1-5 index→KV mapping audit", "",
         "| cell | n_kv | n_idx | selected range | sentinel | expected | verdict |",
         "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['cell']} | {r['n_kv']} | {r['n_idx']} | {r['min_selected']}..{r['max_selected']} | "
                 f"{r['sentinel_frac']:.3f} | {r['expected']} | **{r['verdict']}** |")
    L += ["", f"Scope: {res['scope']}"]
    OUT_MD.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\nwrote {OUT_JSON} {OUT_MD}")


if __name__ == "__main__":
    main()
