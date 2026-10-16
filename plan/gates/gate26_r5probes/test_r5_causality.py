"""R5 — causality-suite extension (gate26).

Extends the future-invariance coverage of `test_expert_plus_plus.py` §5–6 with
the probes the Q1 review asks for, at EVERY tested rate pair:

  A. Index-score masking, adversarial: the future half of the input is replaced
     by large-magnitude noise (so future index tokens dominate the raw scores
     by construction). Assertions for every query position q in the past half:
       - output[:, :q0+1, :] is bitwise identical to the clean run;
       - the selected index-token set and the mapped KV-block tensor are
         bitwise identical to the clean run;
       - no selected token/block violates the safety predicate
         (span ends <= q), i.e. no future dependence through the selector.
  B. Ties: a past hidden state is duplicated into the immediately-following
     position (equal features across a past/future pair). Assert the same
     invariance + no-future-selection properties: the tie-break cannot promote
     the future token.
  C. Block boundaries and padding at a non-divisible length (S=31, patch
     regime): per-cell forward runs, safety predicate holds per block, and for
     the fan-out cell (4,8) the emitted blocks come in (2t, 2t+1) pairs with
     per-block safety; coverage of the KV-block set is reported as a diagnostic.

All six tested rate pairs: (4,4) (8,4) (4,8) (8,8) (16,4) (32,4).
No training; seconds of CPU. Usage:
  ~/.uv_env/py311/bin/python plan/gates/gate26_r5probes/test_r5_causality.py
Exit code 0 = all assertions passed.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import torch  # noqa: E402
from expert_plus_plus_attention import ExpertPlusPlusAttention  # noqa: E402

CELLS = [(4, 4), (8, 4), (4, 8), (8, 8), (16, 4), (32, 4)]
S = 256
Q0 = S // 2                      # split: everything after Q0 is "future" noise
FAILURES = []


def build(ck, ci, S_len=S, seed=0, beta_hidden=128):
    torch.manual_seed(seed)
    return ExpertPlusPlusAttention(
        hidden_size=beta_hidden, num_heads=4, head_dim=32, q_lora_rank=64,
        compress_rate=ck, index_compress_rate=ci, index_topk=16,
        index_n_heads=4, index_head_dim=32, sliding_window=16, o_groups=4,
        o_lora_rank=64).eval()


def instrument(model):
    """Record the selector's final output by wrapping _postprocess_topk
    (the real pipeline; nothing is re-implemented here)."""
    rec = {}
    orig = model._postprocess_topk

    def wrapped(top_k_indices, index_scores, n_idx, S_len, device):
        rec["top_k"] = top_k_indices.detach().clone()
        kv_blocks, nk = orig(top_k_indices, index_scores, n_idx, S_len, device)
        rec["kv_blocks"] = kv_blocks.detach().clone()
        rec["nk"] = nk
        rec["n_idx"] = n_idx
        return kv_blocks, nk

    model._postprocess_topk = wrapped
    return rec


def safety_checks(model, rec, S_len, ck, ci, q_max, tag):
    """No selected token/block may extend past its query position."""
    idx_pos, idx_scale = model._build_idx_positions(S_len, torch.device("cpu"))
    n_idx, nk = rec["n_idx"], rec["nk"]
    top_k, kv_blocks = rec["top_k"], rec["kv_blocks"]
    for q in range(0, q_max + 1):
        for t in top_k[0, q].tolist():
            if t >= n_idx:
                continue                      # sentinel: masked, never read
            end = int(idx_pos[t] + idx_scale[t] - 1)
            assert end <= q, f"{tag}: future index token {t} (end {end}) at q={q}"
        seen = set()
        for b in kv_blocks[0, q].tolist():
            if b >= nk:
                continue
            end = b * ck + (ck - 1)
            assert end <= q, f"{tag}: future block {b} (end {end}) at q={q}"
            seen.add(b)
        assert len(seen) <= kv_blocks.shape[-1]


def run_cell(ck, ci):
    model = build(ck, ci)
    rec = instrument(model)
    torch.manual_seed(1)
    x = torch.randn(1, S, 128)

    with torch.no_grad():
        out1 = model(x)
        sel1, kv1 = rec["top_k"].clone(), rec["kv_blocks"].clone()

        # A. adversarial future: extreme noise after Q0
        x_adv = x.clone()
        x_adv[:, Q0 + 1:, :] = 1e3 * torch.randn(1, S - Q0 - 1, 128)
        out2 = model(x_adv)
        sel2, kv2 = rec["top_k"].clone(), rec["kv_blocks"].clone()

        ok_out = torch.equal(out1[:, :Q0 + 1, :], out2[:, :Q0 + 1, :])
        ok_sel = torch.equal(sel1[:, :Q0 + 1, :], sel2[:, :Q0 + 1, :])
        ok_kv = torch.equal(kv1[:, :Q0 + 1, :], kv2[:, :Q0 + 1, :])
        print(f"  [{ck},{ci}] A: past output bitwise {ok_out}, token set {ok_sel}, "
              f"block tensor {ok_kv}")
        if not (ok_out and ok_sel and ok_kv):
            FAILURES.append(f"[{ck},{ci}] A: future noise changed past output/selection")
        safety_checks(model, rec, S, ck, ci, Q0, f"[{ck},{ci}] A",

                      )

        # future positions must differ (the perturbation is real, probe has teeth)
        assert not torch.equal(out1[:, Q0 + 1:, :], out2[:, Q0 + 1:, :]), \
            f"[{ck},{ci}] perturbation had no effect at all"
        rec_future = rec["top_k"].clone()

        # B. tie probe: duplicate a past state into the next position
        x_tie = x.clone()
        x_tie[:, Q0 + 1, :] = x[:, Q0 - 1, :]
        out3 = model(x_tie)
        sel3, kv3 = rec["top_k"].clone(), rec["kv_blocks"].clone()
        ok_out3 = torch.equal(out1[:, :Q0 + 1, :], out3[:, :Q0 + 1, :])
        ok_sel3 = torch.equal(sel1[:, :Q0 + 1, :], sel3[:, :Q0 + 1, :])
        ok_kv3 = torch.equal(kv1[:, :Q0 + 1, :], kv3[:, :Q0 + 1, :])
        print(f"  [{ck},{ci}] B: tie-duplicate past output bitwise {ok_out3}, "
              f"token set {ok_sel3}, block tensor {ok_kv3}")
        if not (ok_out3 and ok_sel3 and ok_kv3):
            FAILURES.append(f"[{ck},{ci}] B: tie-duplicated future changed past result")
        safety_checks(model, rec, S, ck, ci, Q0, f"[{ck},{ci}] B")

    return rec


def run_patch_regime():
    """C. non-divisible length S=31: forward runs, per-block safety, fan-out pairs."""
    S_len = 31
    for ck, ci in [(4, 4), (8, 4), (4, 8), (8, 8)]:
        torch.manual_seed(0)
        m = ExpertPlusPlusAttention(
            hidden_size=16, num_heads=4, head_dim=4, q_lora_rank=8,
            compress_rate=ck, index_compress_rate=ci, index_topk=4,
            index_n_heads=4, index_head_dim=4, sliding_window=8, o_groups=4,
            o_lora_rank=8).eval()
        rec = instrument(m)
        h = torch.randn(1, S_len, 16)
        with torch.no_grad():
            o = m(h)
        assert tuple(o.shape) == (1, S_len, 16), (ck, ci, tuple(o.shape))
        safety_checks(m, rec, S_len, ck, ci, S_len - 1, f"[{ck},{ci}] C")
        nk = rec["nk"]
        kv = rec["kv_blocks"]
        seen = set()
        for q in range(S_len):
            for b in kv[0, q].tolist():
                if b < nk:
                    seen.add(b)
        # fan-out pairing for (4,8): columns are two halves
        # [2t_0..2t_{k-1} | 2t_0+1..2t_{k-1}+1], width 2 * min(topk, n_idx)
        # (at S=31, n_idx=3 < topk=4, so 6 columns).
        if (ck, ci) == (4, 8):
            expected = 2 * min(4, rec["n_idx"])
            assert kv.shape[-1] == expected, (kv.shape, expected)
            k = len(kv[0, 0]) // 2
            for q in range(S_len):
                pair = kv[0, q].tolist()
                for i in range(k):
                    a, b_ = pair[i], pair[i + k]
                    if a < nk and b_ < nk:
                        assert b_ == a + 1 and a % 2 == 0, \
                            f"[{ck},{ci}] C: fan-out pair broken at q={q}: {a},{b_}"
        print(f"  [{ck},{ci}] C: S=31 forward OK; blocks reachable={sorted(seen)} "
              f"of nk={nk}")


def main():
    print("R5 causality extension — index-score masking, ties, boundaries/padding")
    print(f"cells: {CELLS}, S={S}, adversarial split Q0={Q0}")
    for ck, ci in CELLS:
        run_cell(ck, ci)
    print("C. non-divisible length (patch regime)")
    run_patch_regime()
    print()
    if FAILURES:
        print("FAILURES:")
        for f in FAILURES:
            print(" -", f)
        return 1
    print("ALL R5 CAUSALITY CHECKS PASSED "
          f"({len(CELLS)} cells at S={S}; 4 cells at S=31)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
