#!/usr/bin/env python3
"""Gate 2 — strict 2x2 factorial harness (c_KV x c_R) on the ExpertPlusPlus family.

Frozen task: plan/gates/gate1/gate1_task.md (direct-96, L=256, H=96, 7 features, train-only
z-score, pooled [B,96,7] MSE, strictly causal attention). Repo: CPU PyTorch, no
git. NEW FILE ONLY — no existing repo file is modified; attention modules are
untouched (ExpertPlusPlusAttention reused verbatim).

Design (aux IDENTICAL across all cells):
  sliding_window=16, index_topk=16, num_heads=4, head_dim=32, hidden=128,
  o_groups=4, shared-Q routing, horizon head Linear(128->672), AdamW
  lr=1e-4 wd=1e-5, clip 10.0, batch 32, 10 epochs, L=256, H=96,
  train-only z-score (download_and_preprocess_etth1(return_stats=True) +
  ETTForecastDataset from dataset.py).

Cells (c_KV = compress_rate, c_R = index_compress_rate):
  (4,4), (8,4), (4,8), (8,8). Reference cell (8,4) == ExpertPlusPlusTimeSeriesModel
  config (model.py:138-149: q_lora_rank=64, compress_rate=8,
  index_compress_rate=4, index_topk=16, sliding_window=16, o_groups=4,
  o_lora_rank=64).

Equalization: target = attention-param count of cell (8,4) with ranks (64,64).
Each other cell searches q_lora_rank x o_lora_rank over 32..128 step 16 to
minimize |attn_params - target|. compress_rate, index_compress_rate,
sliding_window, index_topk, o_groups, hidden, heads are NEVER touched (they
define the cell or the aux contract). Tolerance: |Δ|/target <= 0.5% enforced
(preferred <= 0.2%); verified by instantiating and summing p.numel().

Final equalized per-cell configs (verified at runtime by --dry-run):
  cell   c_kv c_r  q_lora_rank  o_lora_rank  attn_params  full_params    Δ%
  (4,4)    4   4       64           64          95,396      348,100   -0.268
  (8,4)    8   4       64           64          95,652      348,356    0.000  <- target (champion)
  (4,8)    4   8       64           64          95,652      348,356    0.000
  (8,8)    8   8       64           64          95,908      348,612   +0.268
  Tolerance check: |Δ|/target = 0.268% <= 0.5% for ALL cells (preferred 0.2%
  is NOT reachable: the rank lattice is discrete — a single q/o rank step moves
  params by >= 4,112 (4.3%) — so 0.268% is the global minimum; the champion
  ranks (64,64) are argmin for every cell and are kept unchanged).
  Note: Δ comes solely from the per-cell position-bias sizes
  (compress_rate x 64 + index_compress_rate x 64), which are part of the cell
  definition, not the aux contract.

CLI modes:
  --dry-run : build all 4 cells with chosen ranks; print per-cell table. No training.
  --smoke   : dry-run table + 1 epoch on bounded subsets (first 40*32 train
              windows, 10*32 val); prints train/val MSE; asserts [B,96,7]; saves nothing.
  --full --seed N : 10 epochs, full train split (shuffle=True), val each epoch,
              final test eval; APPENDS one JSON line to plan/gates/gate2/gate2_results.jsonl.
              Idempotent: a completed (cell, seed) line is skipped on rerun.

Exit codes: 0 on success; non-zero (with traceback/message) on failure.
"""
import argparse
import datetime
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset

from expert_plus_plus_attention import ExpertPlusPlusAttention
from dataset import download_and_preprocess_etth1, ETTForecastDataset

# ── Frozen task constants (plan/gates/gate1/gate1_task.md) ───────────────────────────────
NUM_FEATURES = 7
LOOKBACK = 256
HORIZON = 96
BATCH_SIZE = 32

# ── Aux contract (IDENTICAL across all cells) ────────────────────────────────
HIDDEN_SIZE = 128
NUM_HEADS = 4
HEAD_DIM = 32
SLIDING_WINDOW = 16
INDEX_TOPK = 16
O_GROUPS = 4
LR = 1e-4
WEIGHT_DECAY = 1e-5
CLIP = 10.0
EPOCHS = 10
CHAMPION_Q_RANK = 64   # model.py:141 (ExpertPlusPlusTimeSeriesModel)
CHAMPION_O_RANK = 64   # model.py:148

# ── Factorial cells (c_KV, c_R) ──────────────────────────────────────────────
CELLS = [(4, 4), (8, 4), (4, 8), (8, 8)]
TARGET_CELL = (8, 4)

# ── Equalization lattice + tolerance ─────────────────────────────────────────
RANK_GRID = list(range(32, 129, 16))          # 32..128 step 16
WIDEN_RANK_GRID = list(range(32, 161, 8))     # fallback: step 8, cap 160
TOLERANCE_PCT = 0.5                           # hard: |Δ|/target <= 0.5%

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "gate2_results.jsonl")

SMOKE_TRAIN_BATCHES = 40
SMOKE_VAL_BATCHES = 10


# ── 1) Model builder: EPP-family wrapper, configurable rates + ranks ─────────
class EPPTimeSeriesModel(nn.Module):
    """Mirror of model.py ExpertPlusPlusTimeSeriesModel (byte-identical aux) with
    configurable compress_rate, index_compress_rate, q_lora_rank, o_lora_rank.
    Encoder stack (input_proj, pos_embedding, norm1, mlp, norm2) and the frozen
    horizon head (output_proj Linear(128 -> 672), last hidden state -> [B,96,7])
    are identical to the champion wrapper (model.py:14-67)."""

    def __init__(self, num_features, compress_rate, index_compress_rate,
                 q_lora_rank=CHAMPION_Q_RANK, o_lora_rank=CHAMPION_O_RANK,
                 hidden_size=HIDDEN_SIZE, lookback=LOOKBACK, horizon=HORIZON):
        super().__init__()
        self.num_features = num_features
        self.hidden_size = hidden_size
        self.lookback = lookback
        self.horizon = horizon

        self.input_proj = nn.Linear(num_features, hidden_size)
        self.pos_embedding = nn.Parameter(torch.randn(1, lookback, hidden_size))

        self.attn = ExpertPlusPlusAttention(
            hidden_size=hidden_size,
            num_heads=NUM_HEADS,
            head_dim=HEAD_DIM,
            q_lora_rank=q_lora_rank,
            compress_rate=compress_rate,
            index_compress_rate=index_compress_rate,
            index_topk=INDEX_TOPK,
            sliding_window=SLIDING_WINDOW,
            o_groups=O_GROUPS,
            o_lora_rank=o_lora_rank,
        )
        self.norm1 = nn.LayerNorm(hidden_size)

        self.mlp = nn.Sequential(
            nn.Linear(hidden_size, hidden_size * 4),
            nn.GELU(),
            nn.Linear(hidden_size * 4, hidden_size),
        )
        self.norm2 = nn.LayerNorm(hidden_size)

        # Frozen horizon head: last hidden state -> all H*F future values.
        self.output_proj = nn.Linear(hidden_size, horizon * num_features)

    def forward(self, x):
        # x: [B, L, F]
        x = self.input_proj(x) + self.pos_embedding
        attn_out = self.attn(x)
        x = self.norm1(x + attn_out)
        mlp_out = self.mlp(x)
        x = self.norm2(x + mlp_out)
        out = self.output_proj(x[:, -1, :])                  # [B, H*F]
        return out.view(-1, self.horizon, self.num_features)  # [B, H, F]


def count_attn_params(model):
    return sum(p.numel() for p in model.attn.parameters())


def count_full_params(model):
    return sum(p.numel() for p in model.parameters())


# ── 2) Param equalization: search q/o ranks, verify by instantiation ────────
def search_ranks(ckv, c_r, target_attn):
    """Minimize |attn_params - target_attn| over q_lora_rank x o_lora_rank.

    Tie-break: prefer ranks closest to the champion (64, 64). Never touches
    compress_rate/index_compress_rate/sliding_window/index_topk/o_groups/
    hidden/heads. Widens the lattice (step 8, cap 160) if the 0.5% hard
    tolerance is not met; raises otherwise.
    """
    grid = RANK_GRID
    best = None  # (delta, rank_distance, qr, o_rank, attn_p)
    for _ in range(2):  # at most one widening pass
        for qr in grid:
            for o_rank in grid:
                model = EPPTimeSeriesModel(NUM_FEATURES, ckv, c_r,
                                           q_lora_rank=qr, o_lora_rank=o_rank)
                attn_p = count_attn_params(model)
                delta = abs(attn_p - target_attn)
                rank_dist = abs(qr - CHAMPION_Q_RANK) + abs(o_rank - CHAMPION_O_RANK)
                key = (delta, rank_dist, qr, o_rank, attn_p)
                if best is None or key[:2] < best[:2]:
                    best = key
        if best[0] / target_attn * 100.0 <= TOLERANCE_PCT:
            break
        grid = WIDEN_RANK_GRID
    delta, _, qr, o_rank, attn_p = best
    delta_pct = delta / target_attn * 100.0
    if delta_pct > TOLERANCE_PCT:
        raise RuntimeError(
            f"cell ({ckv},{c_r}): cannot equalize to <= {TOLERANCE_PCT}% "
            f"(best |Δ|/target = {delta_pct:.3f}% with q={qr}, o={o_rank})")
    return qr, o_rank, attn_p, delta_pct


def build_all_cells():
    """Instantiate every cell with its equalized ranks; return target + configs.

    target_attn = attention params of reference cell (8,4) at champion ranks.
    target_full = full-model params of (8,4) at champion ranks.
    """
    target_model = EPPTimeSeriesModel(NUM_FEATURES, TARGET_CELL[0], TARGET_CELL[1])
    target_attn = count_attn_params(target_model)
    target_full = count_full_params(target_model)

    configs = {}
    for ckv, c_r in CELLS:
        qr, o_rank, attn_p, delta_pct = search_ranks(ckv, c_r, target_attn)
        model = EPPTimeSeriesModel(NUM_FEATURES, ckv, c_r,
                                   q_lora_rank=qr, o_lora_rank=o_rank)
        full_p = count_full_params(model)
        configs[(ckv, c_r)] = {
            "q_lora_rank": qr, "o_lora_rank": o_rank,
            "attn_params": attn_p, "full_params": full_p,
            "delta_pct": delta_pct,
            "model": model,
        }
    return target_attn, target_full, configs


# ── 3) Data (reused from dataset.py — zero duplication) ─────────────────────
def load_datasets():
    train_raw, val_raw, test_raw, _stats = download_and_preprocess_etth1(return_stats=True)
    return (ETTForecastDataset(train_raw),
            ETTForecastDataset(val_raw),
            ETTForecastDataset(test_raw))


def make_loaders(seed, smoke):
    """Seed BEFORE data loading (shuffle order comes from torch RNG)."""
    torch.manual_seed(seed)
    train_ds, val_ds, test_ds = load_datasets()
    if smoke:
        train_ds = Subset(train_ds, range(SMOKE_TRAIN_BATCHES * BATCH_SIZE))
        val_ds = Subset(val_ds, range(SMOKE_VAL_BATCHES * BATCH_SIZE))
        return (
            DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True),
            DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False),
            None,
        )
    return (
        DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True),
        DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False),
        DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False),
    )


# ── 4) Training / evaluation ─────────────────────────────────────────────────
@torch.no_grad()
def evaluate(model, loader):
    model.eval()
    total, n = 0.0, 0
    for x, y in loader:
        out = model(x)
        assert out.shape == (x.shape[0], HORIZON, NUM_FEATURES), \
            f"bad output shape {tuple(out.shape)}"
        total += F.mse_loss(out, y).item() * x.shape[0]
        n += x.shape[0]
    return total / n if n else float("nan")


def train_and_eval(model, train_loader, val_loader, test_loader, epochs):
    """AdamW lr=1e-4 wd=1e-5, grad clip 10.0. Returns (train, val, test) MSE."""
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    final_train, final_val = None, None
    for epoch in range(1, epochs + 1):
        model.train()
        total, n = 0.0, 0
        for x, y in train_loader:
            optimizer.zero_grad()
            out = model(x)
            assert out.shape == (x.shape[0], HORIZON, NUM_FEATURES), \
                f"bad output shape {tuple(out.shape)}"
            loss = F.mse_loss(out, y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            optimizer.step()
            total += loss.item() * x.shape[0]
            n += x.shape[0]
        final_train = total / n
        final_val = evaluate(model, val_loader)
        print(f"      epoch {epoch:2d}/{epochs}  train_mse={final_train:.6f}  "
              f"val_mse={final_val:.6f}")
    test_mse = evaluate(model, test_loader) if test_loader is not None else None
    return final_train, final_val, test_mse


# ── 5) Reporting / results persistence ───────────────────────────────────────
def print_table(target_attn, target_full, configs):
    header = (f"{'cell':>6} {'c_kv':>4} {'c_r':>4} {'q_lora_rank':>11} "
              f"{'o_lora_rank':>11} {'attn_params':>11} {'full_params':>11} "
              f"{'delta_pct':>9}")
    print(header)
    print("-" * len(header))
    for ckv, c_r in CELLS:
        cfg = configs[(ckv, c_r)]
        delta = cfg["delta_pct"]
        tag = "  <- target (champion)" if (ckv, c_r) == TARGET_CELL else ""
        print(f"({ckv},{c_r})  {ckv:>4} {c_r:>4} {cfg['q_lora_rank']:>11} "
              f"{cfg['o_lora_rank']:>11} {cfg['attn_params']:>11} "
              f"{cfg['full_params']:>11} {delta:>8.3f}%{tag}")
    print("-" * len(header))
    print(f"  target: attn={target_attn} full={target_full} "
          f"(cell {TARGET_CELL} at q=64, o=64; full-model tolerance check)")
    for ckv, c_r in CELLS:
        d = configs[(ckv, c_r)]["delta_pct"]
        status = "OK" if d <= TOLERANCE_PCT else "FAIL"
        print(f"  ({ckv},{c_r}) |Δ|/target = {d:.3f}% <= {TOLERANCE_PCT}%  "
              f"[{status}]")


def load_completed(results_path):
    done = set()
    if os.path.exists(results_path):
        with open(results_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    done.add((tuple(rec["cell"]), int(rec["seed"])))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    return done


def append_result(results_path, rec):
    with open(results_path, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ── 6) Modes ─────────────────────────────────────────────────────────────────
def run_dry_run(configs, target_attn, target_full):
    print_table(target_attn, target_full, configs)
    return 0


def run_smoke(seed, cells, configs, target_attn, target_full):
    print_table(target_attn, target_full, configs)
    print(f"\n[smoke] seed={seed}, 1 epoch, train={SMOKE_TRAIN_BATCHES}x{BATCH_SIZE} "
          f"windows, val={SMOKE_VAL_BATCHES}x{BATCH_SIZE} windows")
    train_loader, val_loader, _ = make_loaders(seed, smoke=True)
    print(f"[smoke] train batches={len(train_loader)} val batches={len(val_loader)}")
    for ckv, c_r in cells:
        print(f"  cell ({ckv},{c_r}):")
        torch.manual_seed(seed)          # determinism: seed before model init
        model = EPPTimeSeriesModel(NUM_FEATURES, ckv, c_r,
                                   q_lora_rank=configs[(ckv, c_r)]["q_lora_rank"],
                                   o_lora_rank=configs[(ckv, c_r)]["o_lora_rank"])
        train_mse, val_mse, _ = train_and_eval(model, train_loader, val_loader,
                                               None, epochs=1)
        print(f"      smoke train_mse={train_mse:.6f} val_mse={val_mse:.6f}")
    print("[smoke] done — nothing saved")
    return 0


def run_full(seed, cells, configs, target_attn, target_full):
    print_table(target_attn, target_full, configs)
    done = load_completed(RESULTS_PATH)
    todo = [(ckv, c_r) for (ckv, c_r) in cells if ((ckv, c_r), seed) in done]
    pending = [(ckv, c_r) for (ckv, c_r) in cells if ((ckv, c_r), seed) not in done]
    if todo:
        print(f"[full] already completed (skipping, idempotent): "
              f"{[f'{ckv},{c_r}' for ckv, c_r in todo]}")
    if not pending:
        print("[full] nothing to run for this (cell, seed) set")
        return 0
    print(f"\n[full] seed={seed}, {EPOCHS} epochs, full train split (shuffle=True), "
          f"val each epoch, final test eval. Results -> {RESULTS_PATH}")
    train_loader, val_loader, test_loader = make_loaders(seed, smoke=False)
    print(f"[full] train batches={len(train_loader)} val batches={len(val_loader)} "
          f"test batches={len(test_loader)}")
    for ckv, c_r in pending:
        cell_start = time.time()
        print(f"  cell ({ckv},{c_r}):")
        torch.manual_seed(seed)          # determinism: seed before model init
        model = EPPTimeSeriesModel(NUM_FEATURES, ckv, c_r,
                                   q_lora_rank=configs[(ckv, c_r)]["q_lora_rank"],
                                   o_lora_rank=configs[(ckv, c_r)]["o_lora_rank"])
        final_train, final_val, test_mse = train_and_eval(
            model, train_loader, val_loader, test_loader, epochs=EPOCHS)
        attn_p = count_attn_params(model)
        full_p = count_full_params(model)
        rec = {
            "cell": [ckv, c_r],
            "seed": seed,
            "val_mse": round(final_val, 8),
            "test_mse": round(test_mse, 8),
            "final_train_mse": round(final_train, 8),
            "attn_params": attn_p,
            "full_params": full_p,
            "c_kv": ckv,
            "c_r": c_r,
            "completed_utc": datetime.datetime.now(datetime.timezone.utc)
                             .strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        append_result(RESULTS_PATH, rec)
        print(f"      FINAL test_mse={test_mse:.6f} train_mse={final_train:.6f} "
              f"attn_params={attn_p} full_params={full_p} "
              f"(elapsed {time.time() - cell_start:.0f}s)")
        print(f"      appended: {json.dumps(rec)}")
    return 0


# ── 7) CLI ───────────────────────────────────────────────────────────────────
def parse_cells(raw):
    cells = []
    for tok in raw:
        try:
            ckv, c_r = (int(x) for x in tok.split(","))
        except ValueError:
            raise SystemExit(f"error: --cell must be 'c_kv,c_r' (e.g. '4,4'), got {tok!r}")
        if (ckv, c_r) not in CELLS:
            raise SystemExit(f"error: cell ({ckv},{c_r}) not in factorial set {CELLS}")
        if (ckv, c_r) not in cells:
            cells.append((ckv, c_r))
    return cells


def main():
    parser = argparse.ArgumentParser(
        description="Gate 2 factorial harness: strict 2x2 (c_KV x c_R) on "
                    "ExpertPlusPlus family (frozen direct-96 task).")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="build all cells with equalized ranks; print table only")
    mode.add_argument("--smoke", action="store_true",
                      help="dry-run table + 1 epoch on bounded subsets; saves nothing")
    mode.add_argument("--full", action="store_true",
                      help="full 10-epoch training, val each epoch, final test; "
                           "appends to plan/gates/gate2/gate2_results.jsonl (idempotent)")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed for model init + data loading (default 42)")
    parser.add_argument("--cell", action="append", default=None,
                        help="cell to run as 'c_kv,c_r'; repeatable; "
                             "default: all 4 cells (4,4) (8,4) (4,8) (8,8)")
    parser.add_argument("--threads", type=int, default=8,
                        help="torch.set_num_threads (default 8)")
    args = parser.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)          # seed before ANY model init / data loading

    cells = parse_cells(args.cell) if args.cell else list(CELLS)

    # Equalization (instantiates every cell; same for all modes)
    print(f"== Gate 2 factorial harness (CPU PyTorch, threads={args.threads}, "
          f"seed={args.seed}) ==")
    target_attn, target_full, configs = build_all_cells()

    if args.full:
        return run_full(args.seed, cells, configs, target_attn, target_full)
    if args.smoke:
        return run_smoke(args.seed, cells, configs, target_attn, target_full)
    return run_dry_run(configs, target_attn, target_full)


if __name__ == "__main__":
    sys.exit(main())
