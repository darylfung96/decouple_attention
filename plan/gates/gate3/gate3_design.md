# Gate 3 — Dataset-Coverage Expansion: Pre-Registered Design

**Status: PRE-REGISTERED 2026-08-18.** Results land in `results/<dataset>.jsonl` + `gate3_summary.md`. This document freezes the design; deviations after launch must be logged in `gate3_changes.md`.

---

## 1. Task

The frozen task (`plan/gates/gate1/gate1_task.md`) applies **verbatim** to every dataset, with one explicit extension:

- **F = dataset channels** (ETT 7 · electricity 321 · traffic 862 · weather 21 · exchange 8 · solar 137 · synthetic 7). The wrapper adapts `input_proj Linear(F→128)` and the horizon head `Linear(128→H·F)`; all attention modules are F-independent and identical to Gate 2.
- All other IN invariants unchanged: direct-96 single-pass, L=256, H=96, stride-1 per-split windows, no cross-split windows, chronological **60/20/20** split on the raw-row axis, per-feature z-score with **train-only** stats, pooled `[B,H,F]` MSE, strictly causal attention, standardized units.
- TSL's 70/10/20 convention is deliberately **NOT** used — task-consistency across datasets matters more than convention compatibility (we do not compare against TSL-published numbers).

## 2. Normalization guard

Features whose train std < 1e-8 are normalized with std = 1.0 instead (degenerate/constant channels, e.g. some Traffic sensors). The guard is applied to the normalization only; the channel's values still contribute to the loss unchanged in shape. Audit records how many channels per dataset hit the guard.

## 3. Datasets

| Dataset | Role | Source | Expected shape |
|---|---|---|---|
| etth1, etth2 | ETT family | zhouhaoyi/ETDataset (GitHub raw) | 17,420 × 7 |
| ettm1, ettm2 | ETT family | zhouhaoyi/ETDataset (GitHub raw) | 69,680 × 7 |
| electricity | large multivariate | thuml HF mirror `Time-Series-Library` | 26,304 × 321 |
| traffic | large multivariate | thuml HF mirror `Time-Series-Library` | 17,544 × 862 |
| weather | large multivariate | thuml HF mirror `Time-Series-Library` | 52,696 × 21 |
| exchange | different dynamics (daily) | thuml HF mirror `Time-Series-Library` | 7,588 × 8 |
| solar | different dynamics (10-min) | laiguokun/multivariate-time-series-data `solar_AL.txt.gz` | 52,560 × 137 |
| syn_sinusoids | mechanistic synthetic | generated (`gate3_synthetic.py`, seed 0) | 20,000 × 7 |
| syn_changepoints | mechanistic synthetic | generated (`gate3_synthetic.py`, seed 0) | 20,000 × 7 |
| syn_delayedcopy | mechanistic synthetic | generated (`gate3_synthetic.py`, seed 0) | 20,000 × 7 |

Selected 2026-08-18 (user decision): dynamics = **Exchange + Solar-Energy** (PEMS08 dropped — third-party provenance only). If a measured shape differs from expected, the measured value is frozen into the registry and the delta logged.

## 4. Synthetic generators (deterministic, seed 0, N=20,000, 7 channels)

1. **sinusoids**: `x_c(t) = A_c sin(2πt/T_c + φ_c) + ε`, ε~N(0, 0.1²); T = [24, 48, 96, 168, 336, 720, 1440], A = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2], φ = [0, .5, 1, 1.5, 2, 2.5, 3]. Known-period forecastability probe.
2. **changepoints**: piecewise-constant mean; boundaries at t = 2000, 4000, …, 18000; each channel's level shifts by N(0,1) at each boundary; noise σ = 0.1. Post-change adaptation probe.
3. **delayedcopy**: 5 channels periodic with period = lag ∈ [96, 128, 168, 224, 256] + 2 pure-noise channels. Property: `y[t+1..t+96] = x[t+1−L..t+96−L]` fully in-window for L ∈ [96, 256] — exact-offset content recall probe at block-routing granularity. (Note: a period-L sinusoid is also phase-extrapolable; the probe measures whether compression/routing reproduces exact in-window offsets, not whether the task is solvable.)

## 5. Variants + protocol

| Variant | Model | Cell |
|---|---|---|
| Normal | `model.NormalTimeSeriesModel` (model.py verbatim, as run in the baseline gate) | full causal attention |
| Flat | `EPPTimeSeriesModel(F, 4, 4)` (verbatim from `plan/gates/gate2/gate2_factorial.py`), ranks (64,64) | (4,4) |
| DRRA | `EPPTimeSeriesModel(F, 8, 4)`, ranks (64,64) | (8,4) champion |

Protocol identical to `plan/benchmark_protocol.md`: AdamW lr=1e-4 wd=1e-5 · clip 10.0 · batch 32 · **10 epochs fixed** · no scheduler/warm-up/mixed-precision · `torch.set_num_threads(8)` · seed before data load AND model init · paired seeds {42, 123, 2024, 7, 99} · val each epoch, test from epoch-10 weights · standardized-unit pooled MSE.

**Params are NOT re-equalized across variants** — same stance as the baseline gate (~2% attn-param spread on F=7; the spread is F-independent since attention params don't depend on F). Recorded per run for audit.

## 6. Analysis plan (pre-registered)

- Per-dataset 3-way table: val mean±std, test mean±std, Δ% vs Normal (val and test).
- Paired per-seed val deltas vs Normal (negative = variant beats Normal), beats-count per variant.
- Integrity audit per dataset: 15/15 rows; all seeds present; no duplicates; attn/full params match recomputed expectations; final-train MSE within [0.5×, 2×] dataset median; no non-finite values.
- Cross-dataset counts: # datasets where DRRA mean val < Normal; # where Flat mean val < Normal.
- **Descriptive statistics only.** No significance tests (Gate 4), no equivalence claims, no margins. Synthetic-family rows get the same treatment (mechanistic diagnostics beyond MSE are §12 work, deferred).
- ETTh1 is re-run inside this sweep (uniform harness table); Gate-2/baseline rows remain the ETTh1 source for the factorial and 3-way baseline tables.

## 7. Decision record

| Decision | Choice | Rationale |
|---|---|---|
| Dynamics datasets | Exchange + Solar-Energy | User decision 2026-08-18; PEMS08 excluded (third-party provenance) |
| Compute mode | One process, threads=8, sequential | Matches `benchmark_protocol.md`; Gate-2 log shows the fast regime |
| H/L grid (H∈{192,336,720}, L∈{512,720,1024}) | Deferred to follow-on task | Scope decision 2026-08-18 |
| Splits | 60/20/20 all datasets | Task consistency (gate1_task §4); TSL 70/10/20 not used |
| Zero-std channels | std → 1.0 | Degenerate-channel guard, logged |
| Synthetic N / seed | 20,000 / 0 | Deterministic, comparable length to ETTh1 |
