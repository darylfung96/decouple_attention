"""Gate 1 causality audit — future-perturbation invariance (plan/gates/gate1/gate1_task.md §8).

For each of the 6 model variants (num_features=7, eval mode):
  - Encoder state h = post-norm2 output [B, 256, 128], captured by a forward
    hook on model.norm2 (NOT through the horizon head, which legitimately
    reads only the last hidden state).
  - Probe p in {32, 128, 224}:
      (a) FUTURE-INVARIANCE: x[:, p+1:, :] += 3*randn -> h at position p must
          be BITWISE identical (torch.equal True). Causal masks make masked
          contributions exactly 0.
      (b) POWER (test has teeth):  x[:, :p+1, :] += 3*randn -> h at position p
          must CHANGE (torch.equal False).
  - E2E sanity (fresh model, no hooks): x[:, -16:, :] += 3*randn -> full model
    output [B, 96, 7] must CHANGE (head reads position 255, which legitimately
    depends on those rows).

Exit 0 iff ALL assertions hold; exit 1 otherwise (failing variant printed).

Run from repo root:  python3 plan/gates/gate1/gate1_causality.py
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
)

PROBES = [32, 128, 224]
FUTURE_SEED_BASE = 1000  # + p  -> one fixed noise draw per probe
POWER_SEED_BASE = 2000   # + p  -> one fixed noise draw per probe
E2E_SEED = 3000
PERTURB_AMP = 3.0


def perturb_future(x, p, seed):
    xp = x.clone()
    torch.manual_seed(seed)
    xp[:, p + 1:, :] += PERTURB_AMP * torch.randn_like(xp[:, p + 1:, :])
    return xp


def perturb_past(x, p, seed):
    xp = x.clone()
    torch.manual_seed(seed)
    xp[:, :p + 1, :] += PERTURB_AMP * torch.randn_like(xp[:, :p + 1, :])
    return xp


def perturb_tail(x, n_rows, seed):
    xp = x.clone()
    torch.manual_seed(seed)
    xp[:, -n_rows:, :] += PERTURB_AMP * torch.randn_like(xp[:, -n_rows:, :])
    return xp


def run_variant_causality(name):
    """Returns (rows, e2e_ok, all_ok). rows: (variant, p, fi, power)."""
    model = build_variant(name)
    x = make_x()

    storage = []
    handle = make_norm2_hook(model, storage)

    with torch.no_grad():
        model(x)
    h_ref = storage[-1]  # [B, SEQ, HIDDEN]

    rows = []
    ok = True
    for p in PROBES:
        # (a) future-invariance: perturb strictly-future rows only.
        xf = perturb_future(x, p, FUTURE_SEED_BASE + p)
        with torch.no_grad():
            model(xf)
        h_pert = storage[-1]
        fi = torch.equal(h_ref[:, p, :], h_pert[:, p, :])

        # (b) power: perturb past incl. position p itself -> must change.
        xp = perturb_past(x, p, POWER_SEED_BASE + p)
        with torch.no_grad():
            model(xp)
        h_pow = storage[-1]
        pw = not torch.equal(h_ref[:, p, :], h_pow[:, p, :])

        rows.append((name, p, fi, pw))
        ok = ok and fi and pw

    handle.remove()

    # e2e sanity: fresh model WITHOUT hooks; last-16-row perturbation must
    # change the full [B, 96, 7] output.
    m2 = build_variant(name)
    x2 = make_x()
    x3 = perturb_tail(x2, 16, E2E_SEED)
    with torch.no_grad():
        y_ref = m2(x2)
        y_e2e = m2(x3)
    e2e = not torch.equal(y_ref, y_e2e)
    ok = ok and e2e

    return rows, e2e, ok


def main():
    print("=" * 78)
    print("gate1_causality.py — future-perturbation invariance (post-norm2 encoder state)")
    print(f"B={make_x().shape[0]}  L={SEQ}  F=7  H=128  |  probes p in {PROBES}")
    print("future-invariance: perturb x[:, p+1:, :] -> h_p bitwise unchanged (exact zeros via causal mask)")
    print("power:             perturb x[:, :p+1, :] -> h_p changes   |   e2e: perturb last 16 rows -> out[96,7] changes")
    print("=" * 78)
    header = f"{'variant':<14}{'p':<6}{'future-invariant(bitwise)':<26}{'power':<8}{'e2e-sanity':<12}"
    print(header)
    print("-" * len(header))

    failures = []
    for name, _cls in VARIANT_CLASSES:
        rows, e2e, ok = run_variant_causality(name)
        for r_name, p, fi, pw in rows:
            print(f"{r_name:<14}{p:<6}{str(fi):<26}{str(pw):<8}{str(e2e):<12}")
        if not ok:
            failures.append(name)

    print("-" * len(header))
    if failures:
        print(f"FAILED variants (causality): {', '.join(failures)}")
        print("FAIL — task-validity contract NOT satisfied by the failing variant(s).")
        sys.exit(1)
    print("ALL PASS — every variant is future-perturbation-invariant at all probes; power + e2e checks confirm the test has teeth.")
    sys.exit(0)


if __name__ == "__main__":
    main()
