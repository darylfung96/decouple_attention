# Gate 1 Audit Log — Task Freeze: Direct 96-Step Forecasting

Date: 2026-08-11 · Contract: `gate1_task.md` (sole authority on task definition)
Scope: convert pipeline from old per-token next-step regression to frozen direct-96 task.

---

## dataset.py

| Aspect | OLD | NEW |
|--------|-----|-----|
| Target window | `y = data[idx+1 : idx+lookback+1]` → `[B, 256, 7]` (window shifted by 1 step) | `y = data[idx+L : idx+L+H]` = `data[idx+256 : idx+352]` → `[B, 96, 7]` (next 96 steps, disjoint from input) |
| Window length | `len = len(data) - L - H + 1` | unchanged formula (still correct: `len - 256 - 96 + 1`) |
| Normalization | Per-feature z-score over **entire series** (incl. val/test) before split — future-stats leak | Split on raw rows first (60/20/20 chronological), then per-feature z-score fit on **train rows only**; same stats applied to val/test via `_standardize(x, mean, std)` |
| API | `return train, val, test` | `return train, val, test` (+ optional `return_stats=True` → dict `{"mean", "std"}`) |

## model.py

| Aspect | OLD | NEW |
|--------|-----|-----|
| Output head | `output_proj = Linear(hidden → num_features)`, applied per-token → `[B, 256, 7]` | `output_proj = Linear(hidden → horizon*num_features)` = `Linear(128 → 672)`, applied to **last hidden state only** → `[B, 96, 7]` |
| Loss pairing | `criterion(out[:, -96:, :], y[:, -96:, :])` | `criterion(out, y)` — full horizon, no slicing |
| Encoder stack | — | **Untouched** (all attention variants, positional embedding, norms, MLP identical) |
| Head params | `Linear(128→7)` = 903 | `Linear(128→672)` = 86,688 → **+85,785 params** in every variant |

## main.py / compare.py / train_surrogate.py

| Aspect | OLD | NEW |
|--------|-----|-----|
| Eval/loss slice | `out[:, -horizon:, :]` vs `y[:, -horizon:, :]` | `criterion(out, y)` full `[B,96,7]` vs `[B,96,7]` |
| Hyperparameters | L=256, H=96, batch 32, AdamW 1e-4 wd 1e-5, clip 10.0, seed 42, 10 epochs (compare) / 5 (main) | **Unchanged** |
| Surrogate distill path | teacher/student per-token `[B,256,7]` | both `[B,96,7]`; `task = criterion(out, y)`, `distill = F.mse_loss(student_out, teacher_out.detach())` |

## plan/gates/gate0/gate0_registry.json (regenerated via `python3 plan/gates/gate0/gen_registry.py`)

Attention params unchanged (encoder untouched). Full-model params shifted by exactly +85,785 (head swap 903 → 86,688):

| Model | attn (unchanged) | full OLD | full NEW |
|-------|------------------|----------|----------|
| Normal | 102,496 | 269,415 | 355,200 |
| Flat | 144,548 | 311,467 | 397,252 |
| Modified | 144,552 | 311,471 | 397,256 |
| FlatPlus | 152,492 | 319,411 | 405,196 |
| ExpertFlat | 145,060 | 311,979 | 397,764 |
| ExpertPlusPlus | 95,652 | 262,571 | 348,356 |
| Stacked | N/A (no source) | N/A | N/A |

## RESULTS.md

- Added `⛔ TASK FREEZE NOTICE (Gate 1, 2026-08-11)` block at top: all numbers predate the frozen direct-96 task AND the leaky full-series normalization; every number superseded; valid numbers only from Gate 2 runs under the frozen protocol.
- No table numbers modified (supersession, not correction).

## Files NOT touched

`benchmark_speed.py`, `benchmark_alternating.py` (timing harnesses feed random tensors to attention modules — task-form agnostic; may retain old slicing, expected), `test_expert_plus_plus.py`, `attention.py`, all attention variants, `surrogate_attention.py`, `plan/gates/gate0/gate0_*` (except regenerated registry), `plan/REPRO.md`.

---

## Gate 1 docs freeze (Step 4)

Docs-only pass (no code changes, no existing `.py` modified in this pass (new Gate-1 test scripts were created earlier in Gate 1 and run separately — see `gate1_causality_report.md`), python3 not run). Touched: `WRITEUP.md`, `plan/next_step.md`, `gate1_changes.md` (this file).

- **`WRITEUP.md` §2 rewritten OLD→NEW**:
  - per-token next-step `[B,256,7]` scored on last 96 (`out[:, -96:, :]`) → **direct 96-step** `[B,96,7]` in one forward pass via horizon head `Linear(hidden→672)` from last hidden state (encoder untouched; no teacher forcing/autoregression);
  - full-series z-score "simplification" note → **train-only stats, leak-fixed** statement (same stats to val/test);
  - causality tests referenced (`gate1_causality.py` + `gate1_gradmask.py`, all 6 variants PASS);
  - freeze note: all previously reported numbers superseded (see `RESULTS.md` TASK FREEZE NOTICE); §2.4 hyperparams and all later sections untouched.
- **`plan/next_step.md`** — Gate 1 checkboxes now `[x]` (direct-96 chosen incl. inner bullets; future-perturbation causality tests; gradient mask tests; tensor/stride/overlap/normalization documented) + `✅ Gate 1 DONE (2026-08-11)` blockquote after the checklist.
- **New files created in Gate 1** — `gate1_task.md` (frozen spec, sole authority), `gate1_causality.py`, `gate1_gradmask.py`, `_gate1_common.py`, `gate1_causality_report.md`, `gate1_changes.md` (itself).

Bounded-subset smoke accepted as verification (full 5-epoch CPU run impractical).
