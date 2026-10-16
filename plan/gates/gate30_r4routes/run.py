#!/usr/bin/env python3
"""Gate 30 — R4 route-stability probe.

One training run of the (8,4) cell on ETTh1 under the frozen protocol (seed 42),
instrumented to snapshot the selected KV-block set per query position on a fixed
validation batch after every epoch. Writes results/route_snapshots.jsonl
(append-only, one line per epoch). Training is a line-for-line replica of
gate3_harness.train_and_eval; the only addition is the read-out forward.
See design.md for the frozen metric and interpretation rule.

Usage: ~/.uv_env/py311/bin/python plan/gates/gate30_r4routes/run.py [--smoke]
  --smoke : 1 epoch on bounded subsets, writes nothing.
"""
import argparse
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
# gate3_harness imports its sibling gate3_datasets by bare name
GATE3_DIR = os.path.join(REPO_ROOT, "plan", "gates", "gate3")
if GATE3_DIR not in sys.path:
    sys.path.insert(0, GATE3_DIR)

import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import torch.nn.functional as F  # noqa: E402

from plan.gates.gate3.gate3_harness import (  # noqa: E402
    BATCH_SIZE, CLIP, EPOCHS, LR, WEIGHT_DECAY, build_model, evaluate,
    make_loaders)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
OUT_JSONL = os.path.join(RESULTS_DIR, "route_snapshots.jsonl")

DATASET = "etth1"
VARIANT = "DRRA"          # (8,4): the paper's primary cell
SEED = 42
PROVENANCE = ("gate30 R4 route-stability; frozen gate3 protocol; cell=(8,4); "
              "snapshot on fixed first val batch after each epoch")


def instrument(attn, store):
    """Wrap _postprocess_topk on the instance; capture only when armed."""
    orig = attn._postprocess_topk

    def wrapped(top_k_indices, index_scores, n_idx, S_len, device):
        kv_blocks, nk = orig(top_k_indices, index_scores, n_idx, S_len, device)
        if store.get("armed"):
            store["blocks"] = kv_blocks.detach().cpu()
            store["nk"] = int(nk)
            if index_scores is not None:
                store["scores"] = index_scores.detach().float().cpu()
        return kv_blocks, nk

    attn._postprocess_topk = wrapped


def snapshot_sets(model, xb, store):
    """Forward the fixed batch and return per-row, per-position sorted unique
    valid block ids (sentinel dropped), plus route-score entropy stats."""
    store["armed"] = True
    with torch.no_grad():
        model.eval()
        model(xb)
    store["armed"] = False
    kv = store["blocks"]                        # [B, S, top_k]
    nk = store["nk"]
    sets = []
    for b in range(kv.shape[0]):
        rows = []
        for q in range(kv.shape[1]):
            vals = sorted({int(v) for v in kv[b, q].tolist() if int(v) < nk})
            rows.append(vals)
        sets.append(rows)

    # route-score entropy over finite (valid) candidates, predeclared in
    # design.md Amendment 1
    ent = {"score_entropy_mean": None, "score_entropy_std": None,
           "candidates_mean": None}
    sc = store.get("scores")
    if sc is not None:
        hs, cands = [], []
        for b in range(sc.shape[0]):
            for q in range(sc.shape[1]):
                s = sc[b, q]
                fin = torch.isfinite(s)
                k = int(fin.sum())
                cands.append(k)
                if k > 1:
                    p = torch.softmax(s[fin], dim=-1)
                    hs.append(float(-(p * p.log()).sum()))
                elif k == 1:
                    hs.append(0.0)
        if hs:
            m = sum(hs) / len(hs)
            var = sum((h - m) ** 2 for h in hs) / len(hs)
            ent = {"score_entropy_mean": round(m, 4),
                   "score_entropy_std": round(var ** 0.5, 4),
                   "candidates_mean": round(sum(cands) / len(cands), 3)}
    return sets, ent


def main(smoke=False):
    torch.set_num_threads(8)
    t0 = time.time()
    train_loader, val_loader, test_loader = make_loaders(DATASET, SEED, smoke=smoke)
    model = build_model(DATASET, VARIANT, SEED)
    store = {}
    instrument(model.attn, store)

    # fixed validation batch (val loader is shuffle=False; capture once)
    xb, _ = next(iter(val_loader))
    epochs = 1 if smoke else EPOCHS

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    records = []
    for epoch in range(1, epochs + 1):
        model.train()
        total, n = 0.0, 0
        for x, y in train_loader:
            optimizer.zero_grad()
            out = model(x)
            loss = F.mse_loss(out, y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            optimizer.step()
            total += loss.item() * x.shape[0]
            n += x.shape[0]
        train_mse = total / n
        val_mse = evaluate(model, val_loader)
        sets, ent = snapshot_sets(model, xb, store)
        rec = {"provenance": PROVENANCE, "dataset": DATASET, "cell": [8, 4],
               "seed": SEED, "epoch": epoch, "epochs_total": epochs,
               "train_mse": round(train_mse, 6), "val_mse": round(val_mse, 6),
               "fixed_batch_rows": int(xb.shape[0]),
               "positions": int(xb.shape[1]),
               "sets": sets, **ent}
        records.append(rec)
        print(f"epoch {epoch:2d}/{epochs}  train_mse={train_mse:.6f}  "
              f"val_mse={val_mse:.6f}  snapshot rows={len(sets)}  "
              f"route_H={ent['score_entropy_mean']}", flush=True)

    if smoke:
        print("[smoke] done — nothing saved")
        print(f"[smoke] elapsed {time.time()-t0:.0f}s")
        return 0

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUT_JSONL, "w") as f:               # new file (this gate's own)
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    print(f"wrote {OUT_JSONL} ({len(records)} epochs)")
    print(f"elapsed {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    sys.exit(main(smoke=args.smoke))
