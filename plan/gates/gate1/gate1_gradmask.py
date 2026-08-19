"""Gate 1 causality audit — gradient mask, no future gradient flow (plan/gates/gate1/gate1_task.md §8).

For each of the 6 model variants (num_features=7, eval mode, fresh instance):
  - x = seeded randn [2, 256, 7] with requires_grad=True; forward in grad mode.
  - h = post-norm2 encoder output [B, 256, 128] via norm2 hook.
  - Probe p in {64, 192}:
      scalar = (h[:, p, :] * probe_w).sum()     # fixed random projection
      grad   = autograd.grad(scalar, x, retain_graph=True)[0]
      - FUTURE MASK: grad[:, p+1:, :] must be EXACTLY zero
        (count_nonzero == 0) — causal masks give exactly 0 gradients.
      - POWER: grad[:, :p+1, :] must contain nonzeros (count_nonzero > 0).

TEST-NOTE (fix applied): the task's literal `h_p.sum()` functional is DEGENERATE:
every model here ends in a LayerNorm (norm2), and LayerNorm's Jacobian rows sum to
~0 for fresh models (weight init = 1, mean-centering cancels the unweighted sum).
Measured: grad(LN(z)[:, p].sum(), z) ~ 1.19e-7 = float32 epsilon — the power check
then reports ~0 gradient for every variant regardless of causality. The scalar is
therefore the fixed seeded random projection (h[:, p, :] * probe_w).sum(), which
probes every component: it is O(1) whenever h_p depends on the input at all, and
still exactly 0 in the future region (causal-mask zeros are exact). This only fixes
the probe functional; model.py / attention modules are untouched.

Exit 0 iff all checks pass; exit 1 otherwise (failing variant + counts printed).

Run from repo root:  python3 plan/gates/gate1/gate1_gradmask.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch

from _gate1_common import (
    VARIANT_CLASSES,
    build_variant,
    make_norm2_hook,
    make_x,
    SEQ,
    HIDDEN,
)

PROBES = [64, 192]
PROBE_SEED = 1234


def make_probe_weights(seq=SEQ, hidden=HIDDEN):
    """Fixed random projection over the hidden dim, shared across batch/seq.

    Same vector for every variant so all results are directly comparable.
    """
    torch.manual_seed(PROBE_SEED)
    return torch.randn(1, 1, hidden)


def run_variant_gradmask(name, probe_w):
    model = build_variant(name)
    x = make_x()
    x.requires_grad_(True)

    storage = []
    handle = make_norm2_hook(model, storage)

    _out = model(x)          # grad mode ON (eval, no dropout)
    h = storage[-1]          # [B, SEQ, HIDDEN]
    handle.remove()

    rows = []
    ok = True
    for p in PROBES:
        scalar = (h[:, p, :] * probe_w).sum()
        grad = torch.autograd.grad(scalar, x, retain_graph=True)[0]
        nz_future = int(torch.count_nonzero(grad[:, p + 1:, :]))
        nz_past = int(torch.count_nonzero(grad[:, :p + 1, :]))
        fpass = (nz_future == 0)
        ppass = (nz_past > 0)
        rows.append((name, p, fpass, ppass, nz_future, nz_past))
        ok = ok and fpass and ppass

    return rows, ok


def main():
    probe_w = make_probe_weights()
    print("=" * 82)
    print("gate1_gradmask.py — gradient mask: no gradient path from future inputs to earlier encoder states")
    print(f"L={SEQ}  F=7  H=128  |  probes p in {PROBES}")
    print("scalar = (h_p * probe_w).sum()  with fixed random probe_w (seed 1234)")
    print("NOTE: literal h_p.sum() is degenerate under LayerNorm (rows sum ~0 at fresh init); fixed via random projection.")
    print("future-mask: count_nonzero(grad[:, p+1:, :]) == 0   |   power: count_nonzero(grad[:, :p+1, :]) > 0")
    print("=" * 82)
    header = f"{'variant':<14}{'p':<6}{'future-mask(exact-zero)':<24}{'power':<8}{'nz_future':<11}{'nz_past':<10}"
    print(header)
    print("-" * len(header))

    failures = []
    for name, _cls in VARIANT_CLASSES:
        rows, ok = run_variant_gradmask(name, probe_w)
        for r_name, p, fpass, ppass, nz_f, nz_p in rows:
            print(f"{r_name:<14}{p:<6}{str(fpass):<24}{str(ppass):<8}{nz_f:<11}{nz_p:<10}")
        if not ok:
            failures.append(name)

    print("-" * len(header))
    if failures:
        print(f"FAILED variants (gradmask): {', '.join(failures)}")
        print("FAIL — future inputs have a non-zero gradient path to an earlier encoder state; task-validity contract violated.")
        sys.exit(1)
    print("ALL PASS — grad[:, p+1:, :] is exactly zero at every probe for every variant; power checks confirm nonzero past gradients.")
    sys.exit(0)


if __name__ == "__main__":
    main()
