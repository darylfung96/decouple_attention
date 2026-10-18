#!/usr/bin/env python3
"""Gate 28 — C1 all-block compression control.

Design (frozen pre-run): plan/gates/gate28_c1control/design.md.
Two control cells, one variable per cell vs its routed reference:
index_topk 16 -> n_idx (64), i.e. every index token is selected and
_postprocess_topk maps it to every safe KV block. No new parameters, no new
code path: the control is the reference cell's EPPTimeSeriesModel with one
attribute changed after construction.

Usage (from repo root, uv env):
  ~/.uv_env/py311/bin/python plan/gates/gate28_c1control/run.py --dry-run
  ~/.uv_env/py311/bin/python plan/gates/gate28_c1control/run.py --smoke
  ~/.uv_env/py311/bin/python plan/gates/gate28_c1control/run.py --full

Writes ONLY to plan/gates/gate28_c1control/results/allblock.jsonl (append-only,
idempotent). No historical file is touched.
"""
import argparse
import datetime
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for p in (REPO_ROOT,
          os.path.join(REPO_ROOT, "plan", "gates", "gate2"),
          os.path.join(REPO_ROOT, "plan", "gates", "gate3")):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch

from plan.gates.gate2.gate2_factorial import (
    make_loaders as g2_loaders, EPOCHS, NUM_FEATURES, LOOKBACK,
    INDEX_TOPK, build_all_cells, EPPTimeSeriesModel,
)
from gate3_harness import train_and_eval

PROVENANCE = "gate28/uv-torch2.6.0/c1-allblock"
RESULTS_PATH = os.path.join(HERE, "results", "allblock.jsonl")

SEEDS = [42, 123, 2024, 7, 99, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12,
         13, 14, 15, 16, 17, 18, 19, 20, 21]

# control name -> (c_KV, c_R, routed reference cell name in the factorial manifest)
CONTROLS = {"C1(4,4)": (4, 4, "Flat"), "C1(8,4)": (8, 4, "DRRA")}

_CFGS = None


def cfgs():
    """Reference-cell ranks, from the same equalization search gate2 used."""
    global _CFGS
    if _CFGS is None:
        _CFGS = build_all_cells()[2]
    return _CFGS


def n_idx_for(ck, cr, L=LOOKBACK):
    """Index-token count exactly as ExpertPlusPlusAttention._compress_idx builds it."""
    usable = (L // ck) * ck
    usable_idx = (usable // cr) * cr
    return usable_idx // cr


def build_pair(ck, cr, seed=0):
    """(reference, control) at identical init; the control differs only in index_topk."""
    cfg = cfgs()[(ck, cr)]
    qr, orank = cfg["q_lora_rank"], cfg["o_lora_rank"]
    torch.manual_seed(seed)
    ref = EPPTimeSeriesModel(NUM_FEATURES, ck, cr, q_lora_rank=qr, o_lora_rank=orank)
    torch.manual_seed(seed)
    ctrl = EPPTimeSeriesModel(NUM_FEATURES, ck, cr, q_lora_rank=qr, o_lora_rank=orank)
    ctrl.attn.index_topk = n_idx_for(ck, cr)
    return ref, ctrl


def count_params(module):
    return sum(p.numel() for p in module.parameters())


def _capture(model, tag, caps):
    """Record the postprocessed block indices of one forward."""
    orig = model.attn._postprocess_topk

    def wrapped(top_k_indices, index_scores, n_idx, S, device):
        blocks, n_kv = orig(top_k_indices, index_scores, n_idx, S, device)
        caps[tag] = (blocks.detach().clone(), n_kv,
                     top_k_indices.detach().clone())
        return blocks, n_kv

    model.attn._postprocess_topk = wrapped


def dry_run():
    print("== Gate28 dry-run: C1 all-block control ==")
    ok = True
    train_loader, val_loader, _ = g2_loaders(0, smoke=True)
    x, _y = next(iter(val_loader))
    S = x.shape[1]

    for name, (ck, cr, ref_name) in CONTROLS.items():
        n_idx = n_idx_for(ck, cr)
        ref, ctrl = build_pair(ck, cr, seed=0)

        ref_attn, ref_full = count_params(ref.attn), count_params(ref)
        c_attn, c_full = count_params(ctrl.attn), count_params(ctrl)
        sd_ref = {k: v for k, v in ref.state_dict().items()}
        sd_ctrl = {k: v for k, v in ctrl.state_dict().items()}
        bitwise = (sd_ref.keys() == sd_ctrl.keys()
                   and all(torch.equal(sd_ref[k], sd_ctrl[k]) for k in sd_ref))

        print(f"\n[{name}] reference '{ref_name}': attn={ref_attn} full={ref_full} "
              f"k={ref.attn.index_topk}")
        print(f"[{name}] control            : attn={c_attn} full={c_full} "
              f"k={ctrl.attn.index_topk} (n_idx={n_idx})")
        ok &= (ref_attn, ref_full) == (c_attn, c_full)
        ok &= bitwise
        ok &= ref.attn.index_topk == INDEX_TOPK
        ok &= ctrl.attn.index_topk == n_idx and n_idx == S // cr
        if not bitwise:
            print(f"[{name}] FAIL: state_dict differs — more than one variable changed")

        # Realized selection sets on a real validation batch.
        caps = {}
        _capture(ref, "ref", caps)
        _capture(ctrl, "ctrl", caps)
        with torch.no_grad():
            ref(x)
            ctrl(x)

        blocks_c, n_kv, tok_c = caps["ctrl"]
        blocks_r, _n_kv_r, tok_r = caps["ref"]
        ok &= int(tok_c.shape[-1]) == n_idx and int(tok_r.shape[-1]) == INDEX_TOPK
        ok &= n_kv == S // ck

        q = torch.arange(S)
        safe_counts = ((q.view(-1, 1) >= torch.arange(n_kv).view(1, -1) * ck + (ck - 1))
                       .sum(dim=1))
        bad = 0
        strict = 0
        for qi in range(S):
            safe = {b for b in range(n_kv) if b * ck + (ck - 1) <= qi}
            got = {int(v) for v in blocks_c[0, qi].tolist() if v < n_kv}
            got_r = {int(v) for v in blocks_r[0, qi].tolist() if v < n_kv}
            if got != safe:
                bad += 1
            if not got_r <= safe:
                bad += 1
            if got_r != safe:
                strict += 1
        ctrl_mean = float(blocks_c[0].clamp(max=n_kv - 1).lt(n_kv).sum(-1)
                          .float().mean())
        # duplicates legitimately repeat a block, so count distinct for the report
        ctrl_distinct = float(torch.tensor(
            [len({int(v) for v in row.tolist() if v < n_kv}) for row in blocks_c[0]]).float().mean())
        ref_distinct = float(torch.tensor(
            [len({int(v) for v in row.tolist() if v < n_kv}) for row in blocks_r[0]]).float().mean())
        print(f"[{name}] positions with wrong/uncontained set: {bad} of {S}")
        print(f"[{name}] realized distinct blocks per query: control {ctrl_distinct:.2f} "
              f"of {n_kv}, routed {ref_distinct:.2f} of {n_kv} "
              f"(analytic all-safe mean {safe_counts.float().mean():.2f}); "
              f"strict-superset positions {strict}/{S}")
        ok &= bad == 0
        ok &= ctrl_distinct > ref_distinct
        ok &= abs(ctrl_distinct - float(safe_counts.float().mean())) < 1e-6

    if not ok:
        raise SystemExit("dry-run FAILED: control deviates from the frozen design")
    print("\ndry-run OK — single variable is the selection set size (k = n_idx)")
    return 0


def smoke(threads):
    torch.set_num_threads(threads)
    print("== Gate28 smoke: 1 epoch, bounded subsets, saves nothing ==")
    seed = 42
    train_loader, val_loader, _ = g2_loaders(seed, smoke=True)
    print(f"  train batches={len(train_loader)} val batches={len(val_loader)}")
    for name, (ck, cr, _ref) in CONTROLS.items():
        _ref_model, model = build_pair(ck, cr, seed=seed)
        t0 = time.time()
        train_mse, val_mse, _ = train_and_eval(model, train_loader, val_loader,
                                               None, epochs=1)
        finite = torch.isfinite(torch.tensor([train_mse, val_mse])).all().item()
        print(f"  [{name}] train_mse={train_mse:.6f} val_mse={val_mse:.6f} "
              f"finite={finite} ({time.time() - t0:.0f}s)")
        if not finite:
            raise SystemExit("smoke FAILED: non-finite loss")
    print("[smoke] done — nothing saved")
    return 0


def load_completed():
    done = set()
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    done.add((r["cell_name"], int(r["seed"])))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    return done


def append(rec):
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


def realized_blocks_mean(ck):
    """Mean over query positions of the safe-block count (exact, no sampling)."""
    S, n_kv = LOOKBACK, LOOKBACK // ck
    q = torch.arange(S)
    safe = (q.view(-1, 1) >= torch.arange(n_kv).view(1, -1) * ck + (ck - 1))
    return float(safe.sum(dim=1).float().mean())


def run_full(threads):
    torch.set_num_threads(threads)
    done = load_completed()
    todo = [(name, seed) for name in CONTROLS for seed in SEEDS
            if (name, seed) not in done]
    print(f"=== Gate28 C1 all-block: {len(todo)} pending of "
          f"{len(CONTROLS) * len(SEEDS)} runs ===", flush=True)
    t_start = time.time()
    for i, (name, seed) in enumerate(todo, 1):
        ck, cr, _ref = CONTROLS[name]
        n_idx = n_idx_for(ck, cr)
        t0 = time.time()
        print(f"--- [{i}/{len(todo)}] {name} seed={seed} START "
              f"{datetime.datetime.now(datetime.timezone.utc).strftime('%FT%TZ')} ---",
              flush=True)
        train_loader, val_loader, test_loader = g2_loaders(seed, smoke=False)
        _ref_model, model = build_pair(ck, cr, seed=seed)
        final_train, final_val, test_mse = train_and_eval(
            model, train_loader, val_loader, test_loader, epochs=EPOCHS)
        rec = {
            "cell_name": name,
            "control": "all-block",
            "reference_cell": _ref,
            "seed": seed,
            "val_mse": round(final_val, 8),
            "test_mse": round(test_mse, 8),
            "final_train_mse": round(final_train, 8),
            "attn_params": count_params(model.attn),
            "full_params": count_params(model),
            "ckv": ck,
            "cr": cr,
            "index_topk": model.attn.index_topk,
            "n_idx": n_idx,
            "realized_blocks_mean": realized_blocks_mean(ck),
            "n_blocks": LOOKBACK // ck,
            "provenance": PROVENANCE,
            "completed_utc": datetime.datetime.now(datetime.timezone.utc)
                             .strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        append(rec)
        rate = (time.time() - t_start) / i
        print(f"      FINAL val_mse={final_val:.6f} test_mse={test_mse:.6f} "
              f"train_mse={final_train:.6f} (elapsed {time.time() - t0:.0f}s, "
              f"eta {(len(todo) - i) * rate / 3600:.1f}h)")
        print(f"      appended: {json.dumps(rec)}", flush=True)
    print(f"=== done in {(time.time() - t_start) / 3600:.2f}h ===")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--threads", type=int, default=8)
    args = ap.parse_args()
    if args.dry_run:
        return dry_run()
    if args.smoke:
        return smoke(args.threads)
    if args.full:
        return run_full(args.threads)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
