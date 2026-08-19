# Gate 1 — Frozen Forecasting-Task Specification (DIRECT-96)

**Status: FROZEN. All models, all experiments, all future runs — including every Gate 2 run — use exactly this task definition. Any deviation must be a separate, explicitly labeled experiment.**

Source grounding: `dataset.py`, `model.py`, `main.py`, `compare.py`, `train_surrogate.py`, `WRITEUP.md` §2. Where those conflict with this document, this document wins (§9).

---

## 1. Task Form — DIRECT 96-step Long-Horizon Forecasting

Direct multi-horizon forecasting: the model receives a past window of `L = 256` consecutive hourly timesteps for 7 features and, in **one forward pass** (no teacher forcing, no autoregressive feedback, no iterative decoding), outputs the next `H = 96` future steps.

**This replaces the old paradigm** — per-token next-step regression (`WRITEUP.md` §2.2–2.3; `dataset.py` `__getitem__` with `y = data[idx+1 : idx+lookback+1]`; `model(x)[:, -HORIZON:, :]` losses in `compare.py`/`main.py`), where the model output `[B, 256, 7]` was scored only on the last 96 positions.

**Why the old paradigm is rejected:** it was **not a long-horizon forecast** — the model only ever predicted the *next single step*, and only **1 of the 96 scored target positions** (`idx+256`) was out-of-window; the other 95 were in-sample reconstructions, so a model could score well by recopying input. No input position had to predict more than one step ahead, so attention faced no genuine long-range forecast pressure. Reviewers would reject on this alone.

**Contract (machine-precise):**

```python
x = data[idx : idx + L]          # [L, 7]  past window  data[idx .. idx+255]
y = data[idx + L : idx + L + H]  # [H, 7]  next H steps data[idx+256 .. idx+351]
out = model(x)                   # [H, 7]  direct forecast, ONE forward pass
loss = MSELoss(out, y)           # scalar, mean over all B*H*7 elements (§6)
```

`out` is produced without access to any element of `y` (no teacher forcing), without feeding `out` back into the model (no autoregression), and in a single forward call (no iterative/rollout decoding).

---

## 2. Tensors (Exact)

| Tensor | Shape | Meaning |
|---|---|---|
| `x` (input) | `[B, 256, 7]` | past window: rows `data[t-255 .. t]` |
| `y` (target) | `[B, 96, 7]` | future: rows `data[t+1 .. t+96]` |
| `out` (output) | `[B, 96, 7]` | model forecast, same layout as `y` |
| `loss` | `[]` scalar | `MSELoss(out, y)` |

- `B` = batch size = 32 (default; training-time parameter, §7). `L = 256`, `H = 96`, 7 features (HUFL, HULL, MUFL, MULL, LUFL, LULL, OT).
- **Disjoint in time**: `y` starts strictly after the last input token (`index(y[0]) = index(x[-1]) + 1`); input and target windows never overlap.
- Output must be exactly `[B, H, 7]`; any `[B, L, 7]` intermediate must be pooled/projected to `[B, H, 7]` before the loss. `loss = MSELoss(out, y)` with **no slicing of `out`**.

---

## 3. Windowing / Stride / Overlap

- **Sliding windows with `STRIDE = 1` within each split** (consecutive indices); window `idx` and `idx+1` differ by exactly one row. Adjacent windows overlap by `(L-1)/L = 255/256` steps — **heavy dependence**.
- **Explicit warning: samples are NOT IID** — I.i.d. assumptions (random splits, per-sample permutation tests) do not apply; do not claim sample independence.
- **No window ever spans a split boundary**: windowing is applied after splitting, separately within each split's rows. Valid window starts in a split: `idx ∈ [0, len(split) − L − H]`, stride 1; windows are dropped, never padded across splits.

---

## 4. Split (Chronological, Disjoint)

Computed on the **raw-row axis** of the full series (`N` timesteps, chronological order): train = `[0, floor(0.6·N))`, val = `[floor(0.6·N), floor(0.8·N))`, test = `[floor(0.8·N), N)`. Disjoint, non-overlapping, ordered (val after train, test after val).

- **No shuffling across time for val/test**: always evaluated with `shuffle=False` over every valid window. Train loader may shuffle *within* train only (batch order; the window set and its timesteps never change).

---

## 5. Normalization

Per-feature z-score `z = (x − mean) / std` per column, with `mean`/`std` computed **on the TRAIN split only**; the **same train-fitted stats are applied** to val and test — val/test are never re-centered or re-scaled by their own statistics.

```python
train_rows = full_data[:int(n*0.6)]
mean, std  = train_rows.mean(axis=0), train_rows.std(axis=0)   # [7] each
normalize(split) = (split - mean) / std                        # same stats for all splits
```

- **Leak fix (explicit)**: the OLD code (`dataset.py` `download_and_preprocess_etth1`) computed mean/std over the **entire series including val/test** before splitting — a **future-stats leak** (test statistics inform training data and vice versa). Now fixed.
- **All pre-freeze numbers in `RESULTS.md` / `WRITEUP.md` were produced in the leaky-normalization regime** — see §9.

---

## 6. Metric

- **Pooled MSE**: `torch.mean((out - y) ** 2)` — mean over **all** `(B, 96, 7)` elements, single scalar, identical to `nn.MSELoss(out, y)`. **No slicing** of `out`: the full 96-step horizon and all 7 features are scored.
- **Units**: predictions/metrics stay in **standardized (z-score) units**. **No un-normalization to raw units** currently — a documented future repro item, but **NOT** a requirement of this frozen spec. Every model reports standardized-unit MSE.

---

## 7. Determinism & Config Invariants

**IN (frozen — invariant across all models/experiments):** direct 96-step single-pass task form; `L = 256`; `H = 96`; 7 features (ETTh1); stride-1 per-split windowing, no cross-split windows; chronological 60/20/20 split; per-feature z-score, train-only stats; pooled `(B, 96, 7)` MSE; val/test on all windows, `shuffle=False`; strictly causal attention (§8).

**OUT (free to vary — NOT part of the task definition):** seeds (set per run; affects run-to-run variance only), training budget (epochs/steps/early stopping), optimizer/LR schedules, batch size, architecture, parameter count, compute budget. Changing an OUT parameter changes the *experiment*, never the *task*. Changing an IN parameter requires a new task definition.

---

## 8. Causality Contract

A model is **task-valid** iff its forecast never depends on input positions it should not:

- Output position `p` of `out` (future step `t+p`, `p ∈ [1, 96]`) may depend only on input rows `t-255 .. t`; no output may depend, directly or transitively, on any row `> t`. Perturbing any input row `data[j]`, `j > t` (or any target row) must leave every output unchanged.
- **Attention masking must be strictly causal at all stages**, including compressed/indexed attention: a query at position `q` may attend only to keys for positions `≤ q` — at every granularity (raw tokens, sliding window, compressed KV blocks, index/router tokens, sinks). Future-spanning blocks are masked or sentineled (cf. `expert_plus_plus_attention.py` block-end future-safety).
- Compliance is **documented by companion tests** (future-perturbation: perturb future inputs, verify earlier predictions unchanged; gradient-mask: no gradient path from future inputs to earlier outputs). A model failing these tests is not task-valid; its numbers are void.

---

## 9. Supersession Note

Every number in `RESULTS.md` / `WRITEUP.md` (all Val/Test MSE, speed, and Perf/Spd numbers in `RESULTS.md` / `WRITEUP.md`, including surrogate rows, are superseded) **predates this freeze** — produced under the old per-token next-step task (§1) and leaky full-series normalization (§5). Those numbers are **superseded** and must not be cited as results of this task; valid numbers come only from **Gate 2 runs** under this protocol (direct-96, train-only normalization, pooled `[B,96,7]` MSE, strictly causal attention). This document is the sole authority on task definition; conflicting descriptions in the codebase/`WRITEUP.md` yield until updated.

---

## 10. Decision Record

| Decision | Choice | Rationale |
|---|---|---|
| Task form | **Direct 96-step** (one pass, no feedback) | Every output position is a genuine out-of-window prediction; matches the long-horizon claim; single-shot evaluation; reviewer-safe. |
| Rejected — rolling one-step | ✗ | Scores `t+1` only; 95/96 scored positions are in-sample reconstructions; not a long-horizon forecast. |
| Rejected — iterative decoding | ✗ | Error accumulation, more compute, harder causality auditing; direct-96 isolates raw horizon skill. |
| Normalization fix | **Train-only per-feature z-score** | OLD full-series stats leaked future (test) information; fixed, with all pre-freeze numbers flagged as leaky-regime. |

---

*Freeze date: 2026-08-11. Companion artifacts: causality tests (future-perturbation + gradient-mask) — see Gate 1 checklist in `plan/next_step.md`.*