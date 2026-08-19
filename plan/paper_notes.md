# Novelty & Paper-Prep Ledger (living doc — last updated 2026-08-13)

## 0. Status of this ledger

This is a **living pre-writing document**, not paper prose. It consolidates the novelty claims, evidence, warnings, and open items for writing the paper, so that nothing is over- or under-claimed at submission time. Every claim below is tagged **EVIDENCE-BACKED** / **DIRECTIONAL** / **OPEN** / **SUPERSEDED** and carries source pointers (file § or file:line). No number is invented: Gate-2 numbers are copied verbatim (4dp) from `plan/gates/gate2/gate2_summary.md` (source of truth); parameter counts come from `plan/gates/gate0/gate0_registry.json`; citation statuses are copied verbatim from `plan/lit_audit.md`. As the gates complete (Gate 3 datasets, Gate 4 statistics, Gate 5 hardware), this ledger must be updated and the statuses re-tagged.

## 1. Central framing

Two-axis design study of the **compressed-and-indexed attention family** along two independent axes — KV compression rate **c_KV** and routing resolution **c_R** — on the **frozen ETTh1 direct-96 task** (spec `plan/gates/gate1/gate1_task.md`). This is **not a novel sparse-attention mechanism**: every building block (two-series softmax-overlap compression, fine router over coarse blocks, shared-Q routing, slim O, dense masked attention over sparse selection) is a configuration of known ideas, and overlap with recent work (DeepSeek-V4 CSA, NSA, the routing-attention line) is acknowledged rather than elided. The contribution is the *study* (PUBLICATION.md §2). All pilot-era numbers are superseded by the Gate-1 freeze; valid numbers come only from Gate 2 runs (PUBLICATION.md freeze notice, line 5; RESULTS.md TASK FREEZE NOTICE, lines 3–7).

## 2. Novelty claims ledger

| Claim | Status | Evidence (numbers verbatim from `plan/gates/gate2/gate2_summary.md`; params from `plan/gates/gate0/gate0_registry.json`) | Source pointers | What would upgrade status |
|---|---|---|---|---|
| **C1 — Decoupling insight**: routing granularity carries accuracy, KV content density buys speed | **DIRECTIONAL** | Gate-2 champion (8,4) val **0.5967** ± **0.0710** vs (4,4) **0.6332** ± **0.0611**; (4,8) worst **0.6858** ± **0.0875**; main effects **c_KV −0.0427** / **c_R +0.0463**; both effects < seed std **0.0647** (per-cell std range 0.0393–0.0875); direction consistent in 7/10 seed-column comparisons per effect; **no significance test run** | `plan/gates/gate2/gate2_summary.md:17-20,36-37,41`; `PUBLICATION.md:58` (§2 item (b)); `WRITEUP.md:37,276-277` | Gate-4 statistics (mixed-effects β₂>β₁, TOST, block bootstrap) + Gate-3 multi-dataset confirmation |
| **C2 — "To our knowledge not stated this explicitly"** (the decoupling framing) | **VERIFIED 2026-08-16** (branch: KEEP chosen by user; phrasing in related\_work.tex stands, now with an explicit closest-works contrast) | Sweep log `plan/mini_tasks/c2/2026-08-16-c2-lit-sweep.md` + `plan/mini_tasks/c2/c2_sweep_log.md` (29 assessed rows, 0 COUNTERS, 742 papers swept); DS-V4 internals `plan/mini_tasks/c2/dsv4_csa_read.md`; NSA `plan/mini_tasks/c2/nsa_read.md`; decision brief `plan/mini_tasks/c2/c2_decision_brief.md` | `plan/lit_audit.md:11,22`; `PUBLICATION.md:58` | Re-run the sweep pre-submission once Gate 3 lands (fresh 12-month window) |
| **C3 — Parameter reduction** | **EVIDENCE-BACKED** (registry-verified); a param-count fact, **not** a speed claim | EPP: attn 95,652 / full 348,356 vs Flat: attn 144,548 / full 397,252 → attn **−33.8%** ((144,548−95,652)/144,548); full-model **−12.3%** ((397,252−348,356)/397,252); EPP attn 95,652 **< Normal attn 102,496** | `plan/gates/gate0/gate0_registry.json:18,32,88,89`; −33.8% attn headline: `WRITEUP.md:124` (§7.2), `PUBLICATION.md:30`, `RESULTS.md:38` | Keep as-is; re-state against the frozen-registry full counts (348,356 vs 397,252) once the Normal/Flat/DRRA 3-way merge lands |
| **C4 — Speed claim (pre-freeze 1.32× forward vs Flat)** | **SUPERSEDED** — figures removed from the earlier drafts 2026-08-18; original measurements preserved in `experiment-session-new-attention.md` | 22.42 ms vs 29.66 ms was a **pre-freeze pilot** figure (alternating head-to-head, old paradigm); removed from `RESULTS.md`, `WRITEUP.md`, `PUBLICATION.md` (removal notice added in each, 2026-08-18) | Removal notices: `RESULTS.md` "Speed Evidence (removed — superseded)", `WRITEUP.md` §2.2 + §7.3, `PUBLICATION.md:5`; original measurements: `experiment-session-new-attention.md` | Re-measure under Gate-5 hardware/latency protocol (p50/p90/p99, bootstrap CIs, scaling sweeps, cross-hardware) — `next_step.md` §10 |
| **C5 — Negative-results corpus + surrogate line** | **SEPARABLE / SECONDARY** | Six documented failed designs + surrogate (windowed + global-prototype student); neither is the paper's core claim | `PUBLICATION.md:61` (§2 item 5); `WRITEUP.md:355-363`; `RESULTS.md:170-201` | Optional separate paper; if retained, align surrogate epochs to 10 and add equal-budget small-transformer control (`PUBLICATION.md:114`) |

## 3. What we must NOT claim

From `next_step.md` ⚠️ KEY WARNINGS FROM THE STRATEGY DOCUMENT (lines 254–259) + PUBLICATION.md "What it is not" (line 63):

- **Not a novel sparse-attention mechanism** — framing is a two-axis design study (`PUBLICATION.md:55,63`).
- **No SOTA claim** — no external baselines exist in the repo; val 0.1099 is pre-freeze internal-family best-or-near-best and is superseded (`PUBLICATION.md:63`; `next_step.md:230`).
- **No "statistically identical"** from seed 42 and the informal ±0.002 band — equivalence needs predeclared margin + TOST/Bayesian ROPE (`next_step.md:255,259`; `PUBLICATION.md:59`).
- **No subquadratic claim** without the §11-style complexity analysis: only claim subquadratic if the candidate budget is sublinear AND routing avoids O(S×M_R) dense comparison (`next_step.md:142-143`).
- **No "CSA" novelty** — acknowledge the 2026 label overlap with DeepSeek-V4 and recent routing work (`next_step.md:257`; `plan/lit_audit.md:11`).
- No "Zero-accuracy-cost" language — absence of observed difference ≠ equivalence (`next_step.md:256`).
- No treating overlapping forecast windows as IID samples (`next_step.md:258`; `WRITEUP.md:50`).

## 4. Evidence ledger (numbers + where)

| Evidence | Pointer |
|---|---|
| Frozen task spec (sole authority on task definition): direct-96, L=256, H=96, 7 features, train-only z-score, pooled `[B,96,7]` MSE, strictly causal | `plan/gates/gate1/gate1_task.md` (§1, §5, §9) |
| **Gate-2 5-seed means table (verbatim from `plan/gates/gate2/gate2_summary.md:17-20`)** | Cell (4,4): val 0.6332 ± 0.0611 · test 0.9079 ± 0.0557 · train 0.2908 · (8,4): val **0.5967** ± 0.0710 · test **0.7988** ± 0.0506 · train 0.2880 · (4,8): val 0.6858 ± 0.0875 · test 0.8996 ± 0.0740 · train 0.2983 · (8,8): val 0.6368 ± 0.0393 · test 0.9159 ± 0.0317 · train 0.2844 — champion (8,4); attn 95,652 / full 348,356 | `plan/gates/gate2/gate2_summary.md:13-22,46-47` |
| Main effects: c_KV 4→8 = **−0.0427**; c_R 4→8 = **+0.0463**; pairwise seed deltas & consistency (7/10 each) | `plan/gates/gate2/gate2_summary.md:30-37,41` |
| Param registry (ground truth param counts) | `plan/gates/gate0/gate0_registry.json` (Normal attn 102,496 / full 355,200; Flat 144,548 / 397,252; ExpertPlusPlus 95,652 / 348,356) |
| **Normal baseline leg — completed 2026-08-14** (5 seeds, results in `plan/gates/baseline/baseline_normal_results.jsonl`; aggregated in `plan/gates/baseline/baseline_normal_summary.md`; merged into RESULTS.md "Baseline Comparison" section) | `plan/gates/baseline/baseline_normal_sweep.py` (docstring lines 2–35); `plan/gates/baseline/baseline_normal_results.jsonl`; `plan/gates/baseline/baseline_normal_summary.md`; `RESULTS.md` "Baseline Comparison" section |
| Pre-freeze pilot numbers (val 0.1083–0.1116, 1.32×, 22.42 ms, Perf/Spd, surrogate figures) = **superseded**; the speed/latency figures among them were removed from the pre-paper drafts 2026-08-18 (removal notices in `RESULTS.md` / `WRITEUP.md` / `PUBLICATION.md`; original measurements preserved in `experiment-session-new-attention.md`) | `RESULTS.md:3-7` (TASK FREEZE NOTICE), `WRITEUP.md:56`, `PUBLICATION.md:5` |
| Data-integrity checks for Gate 2 (param equalization < 0.5%: max attn delta 0.2676%, max full delta 0.0735%; training matched; 20/20 rows) | `plan/gates/gate2/gate2_summary.md:7-11` |

## 5. Hypothesis status (H1–H5 verbatim from `next_step.md` §9, lines 111–115)

| Hypothesis (verbatim) | Status |
|---|---|
| **H1**: Routing sensitivity — increasing c_R causes larger MSE deterioration than c_KV | **Tested DIRECTIONALLY**: c_R raises val MSE **+0.0463** while c_KV lowers it **−0.0427** — consistent with H1's directional claim but weak: n=5, no significance test; note `gate2_summary.md:41` verdict is "No" to the strict magnitude form (|c_R| ≈ |c_KV|), direction only |
| **H2**: Dual-rate Pareto advantage — (8,4) Pareto-dominates equal-rate at comparable latency | **Untested** (pre-registered; requires Gate-4 stats + Gate-5 latency) |
| **H3**: Hardware crossover — dense masked faster below candidate-width threshold | **Untested** (pre-registered; requires Gate-5 cross-hardware) |
| **H4**: Signal dependence — routing advantage larger for change points/sparse events | **Untested** (pre-registered; requires §12 mechanistic analyses) |
| **H5**: Surrogate noninferiority (if retained) | **Untested** (pre-registered; retention decision pending — `PUBLICATION.md:114`) |

## 6. Citation ledger (verification status copied verbatim from `plan/lit_audit.md`)

| Work | ID | Status (verbatim from lit_audit.md) |
|---|---|---|
| DeepSeek-V4 Compressed Sparse Attention (CSA) | arXiv:2606.19348 | **VERIFIED** — existence, hybrid CSA/HCA, 1M context, 27% FLOPs / 10% KV cache vs V3.2. **CSA/HCA internals read in depth 2026-08-16** (`plan/mini_tasks/c2/dsv4_csa_read.md`): CSA compresses every m tokens into one entry (two-series overlapped softmax) then selects top-k compressed entries via the lightning indexer (Flash m=4/k=512, Pro m=4/k=1024; HCA m'=128; window 128); knobs exposed but NEVER varied independently (no ablation in the report) |
| DeepSeek NSA (Native Sparse Attention) | arXiv:2502.11089 | **VERIFIED** (coarse-grained compression + fine-grained token selection; closest conceptual cousin) |
| Routing Transformer (Roy et al.) | arXiv:2003.05997 | **VERIFIED** (content-based routing sparse attention; TACL 2020) |
| RADLADS | arXiv:2505.03005 | **VERIFIED** (overlaps the surrogate/retired-attention secondary line, not the routing/compression core) |
| FAR | — | **[NEEDS VERIFICATION]** — acronym ambiguous; candidates arXiv:2505.21535 ("FAR: Function-preserving Attention Replacement") and arXiv:2203.10694 ("FAR: Fourier Aerial Video Recognition"); cannot confirm which the strategy doc meant |
| MLA (Multi-head Latent Attention) | — | Canonical citation **[NEEDS VERIFICATION]** (LoRA-style Q / grouped-O lineage of shared-Q + slim O; known from context, cited in PUBLICATION.md §3.3) |
| TS forecasting baselines (PatchTST, iTransformer, DLinear, Informer, TimesNet, ModernTCN) | — | Known from context; citations to be collected together with the Gate 3 baseline runs |

## 7. Open items before submission (checklist)

Each item is traceable to a `next_step.md` section (or `lit_audit.md`); none is invented.

- [x] **Lit re-audit — C2 portion DONE 2026-08-16** (sweep `plan/mini_tasks/c2/2026-08-16-c2-lit-sweep.md`; 0 counterexamples; DS-V4 decoupling question answered in `plan/mini_tasks/c2/dsv4_csa_read.md`). Remaining for the full pre-submission re-audit: resolve FAR identity; find MLA canonical citation; fresh 2024–2026 two-axis + TS-efficiency search once Gate 3 results exist (`lit_audit.md` §2/§4; `next_step.md` §3).
- [ ] **Gate 3 dataset expansion** — ETT family (ETTh1, ETTh2, ETTm1, ETTm2), large multivariate (Electricity, Traffic, Weather), different dynamics (Exchange, Solar-Energy, or PEMS), mechanistic synthetic; H ∈ {96, 192, 336, 720}, L ∈ {96, 256, 512, 720, 1024} (`next_step.md` §6). **Scoping pending user** (datasets/horizons/lookbacks not yet selected).
- [ ] **Gate 4 statistics** — 5–10 paired seeds; mean/std/95% CI + individual seed points; mixed-effects model `MSE = β₀ + β₁ log₂(c_KV) + β₂ log₂(c_R) + β₃ log₂(c_KV)log₂(c_R) + random effects` (main claim requires β₂ > β₁); TOST or Bayesian ROPE for equivalence; paired Wilcoxon/Friedman with Holm correction; block bootstrap or HAC-robust tests for temporal dependence (`next_step.md` §8).
- [ ] **Gate 5 hardware/latency re-measure (C4)** — full hardware details; p50/p90/p99 with bootstrap CIs; throughput; memory; FLOPs/MACs; scaling sweeps (seq 128→4096+, batch 1/8/32); cross-hardware (Apple Silicon + Linux x86 CPU, ideally GPU); stage-level profiling (`next_step.md` §10).
- [ ] **§7 baselines** — Normal/CSA/Flat vs DRRA 3-way DONE 2026-08-14 except NormalAttention wiring sanity re-verification (completed 2026-08-14 — plan/gates/baseline/normal_sanity_check.md) + end-to-end models (DLinear, PatchTST, iTransformer, TimesNet, ModernTCN, CATS or state-space/mixer) and same-backbone attention line (Linformer, Performer, Reformer/LSH, Informer/ProbSparse, BigBird/Longformer, Routing Transformer) (`next_step.md` §7; `PUBLICATION.md` §3.4 roadmap items 1–3).
- [ ] **Title decision** — 4 candidates in `lit_audit.md` §3 (decision rule: prefer 2 or 3 for "study, not mechanism"; fall back to 1 for method-name recognition); final choice at the pre-submission re-audit.
- [ ] **Freeze-clean submission package** — run manifest (run_id/timestamp/config hash/dataset checksum/split indices/model config/training/accuracy/efficiency/diagnostics), automated table regeneration, unit tests (causality masks, bias init, param counts, softmax equivalence), environment lockfile, data hashes (`next_step.md` §16).

## 8. Changelog

- 2026-08-13: created.
- 2026-08-16: C2 resolved (KEEP — user decision); DS-V4 CSA/HCA internals read in depth; 2024–2026 routing/compression-attention sweep logged (plan/mini_tasks/c2/2026-08-16-c2-lit-sweep.md + plan/mini_tasks/c2/c2_sweep_log.md, 0 counterexamples); 2 new verified citations added to the paper (SSA mao2026ssa, Sparse Frontier nawrot2025sparsefrontier).
- 2026-08-18: pre-freeze speed/latency claims (1.32×, ms figures, Perf/Spd, surrogate speed figures) removed from the earlier drafts `RESULTS.md`, `WRITEUP.md`, `PUBLICATION.md` (per §4 — superseded by the Gate-1 freeze); removal notice added in each doc; original measurements remain in `experiment-session-new-attention.md`; the introduction TODO ("remove pre-freeze speed claims from any earlier draft") removed from `paper/sections/introduction.tex`.
