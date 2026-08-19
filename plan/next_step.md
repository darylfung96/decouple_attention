# Next Steps for Paper A: Dual-Rate Routed Attention

Based on the comprehensive development strategy document, here are the **priority next steps** for Paper A, organized in order of execution:

---

## 🚨 IMMEDIATE PRIORITY: Fix Foundational Issues

### 1. **Resolve All Numerical Inconsistencies** (Gate 0)
- [x] Reconcile the 52 KV tokens claim vs. 32 blocks + 16 window = 48
- [x] Document exact parameter counts for every model (not "approximately 0.1M")
- [x] Clarify the 34% parameter reduction denominator
- [x] Explain surrogate teacher MSE discrepancy (0.1264 vs. Flat 0.1085)
- [x] Correct the "fastest-but-least-accurate" claim about ExpertFlat vs. ExpertPlusPlus
- [x] Generate a machine-readable results manifest linking every number to a run ID, commit, seed, and split

> ✅ **Gate 0 DONE (2026-08-11).** Artifacts: `plan/gates/gate0/gate0_registry.json` + `gen_registry.py` (ground truth), `plan/gates/gate0/gate0_changes.md` (edit audit log), `plan/gates/gate0/gate0_manifest.json` + `build_manifest.py` + `REPRO.md` (reproducibility). NOTE: repo has no git → manifest links file SHA-256 instead of commit (recorded in `known_gaps`); Stacked has no runnable source (legacy, flagged). Regenerate manifest: `python3 plan/gates/gate0/build_manifest.py`.

### 2. **Define the Forecasting Task Unambiguously** (Gate 1)
- [x] Determine if you're doing:
  - [x] **Direct 96-step long-horizon forecasting** (recommended): Input L→256, predict L+1...L+96 without seeing ground truth
  - [x] **Rolling one-step prediction**: Keep but rename clearly
- [x] Implement future-perturbation causality tests:
  ```python
  # Perturb future inputs and verify earlier predictions unchanged
  ```
- [x] Run gradient mask tests to ensure no future information leakage
- [x] Document exact input tensor, target tensor, stride, overlap, and normalization

> ✅ **Gate 1 DONE (2026-08-11).** Artifacts: `plan/gates/gate1/gate1_task.md` (frozen spec — sole authority on task definition), dataset/model/script conversion to direct-96 (train-only z-score, horizon head `Linear(128→672)`, +85,785 params — logged in `plan/gates/gate1/gate1_changes.md`), causality suite `plan/gates/gate1/gate1_causality.py` + `plan/gates/gate1/gate1_gradmask.py` (all 6 variants PASS; bitwise future-invariance + exact-zero future gradients, power-checked), `RESULTS.md` freeze notice (all old numbers superseded). NOTE: bounded-subset smoke accepted as verification (full 5-epoch CPU run impractical).

### 3. **Rename and Reframe**
- [x] Retire "CSA" label (DeepSeek-V4 already uses Compressed Sparse Attention)
- [x] Adopt "Dual-Rate Routed Attention (DRRA)" as working name
- [x] Complete final literature/title audit before submission
- [x] Reframe contribution as a **two-axis design study**, not a novel sparse-attention mechanism

> ✅ **Rename & Reframe DONE (2026-08-12).** CSA label retired and DRRA adopted (audit: `plan/gates/gate0/rename_changes.md`); contribution reframed as a **two-axis design study** (c_KV compression rate × c_R routing resolution) of the compressed-and-indexed attention family — PUBLICATION.md §1.2/§2 and WRITEUP.md §1 repositioned with no numbers changed, and freeze-supersession pointers kept intact (PUBLICATION.md gained the same freeze note as WRITEUP/RESULTS so its pilot numbers are not read as current). The literature/title audit is a **living process**: the current-state audit doc lives at `plan/lit_audit.md` (overlap landscape with honest [NEEDS VERIFICATION] flags + 4 title candidates), and a **final pre-submission re-audit remains** — a fresh search once Gate 3 results exist, before the title decision is locked. This step's deliverable (audit doc + title shortlist + reframed docs) is complete.

---

## 🔬 CORE EXPERIMENTAL PROGRAM

### 4. **Run the Strict Factorial Confirmation** (Gate 2)
This is the **critical go/no-go test** for the central hypothesis:

- [x] Implement strict 2×2 controls with **identical auxiliary design**:
  - (c_KV=4, c_R=4) — baseline equal compression
  - (c_KV=8, c_R=4) — aggressive content compression, fine routing
  - (c_KV=4, c_R=8) — fine content, coarse routing
  - (c_KV=8, c_R=8) — aggressive both
- [x] Ensure **identical**:
  - Shared-Q setting
  - Output projection rank
  - Window size W
  - Parameter count (adjust to match)
  - Training schedule and budget
- [x] Run **5-10 paired seeds** (identical seeds across variants)
- [x] Document if the routing-resolution effect is reproducible

> ✅ **Gate 2 DONE (2026-08-13).** Artifacts: `plan/gates/gate2/gate2_factorial.py` (2×2 sweep script), `plan/gates/gate2/gate2_design.md` (pre-registered design), `plan/gates/gate2/gate2_results.jsonl` (20-run results, 5 paired seeds), `plan/gates/gate2/gate2_summary.md` (aggregate summary — E4 audit PASS, source of truth), `plan/gates/gate2/gate2_changes.md` (docs-freeze audit log). Sweep: ~30 h wall. Result: (8,4) champion, matches the EPP champion corner; effects directional only (c_KV −0.0427 / c_R +0.0463, both < seed-to-seed std 0.0647; no significance test run).

### 5. **Correct the Benchmark Protocol**
- [x] Replace 10-epoch cap with **convergence-based stopping** or justified fixed budget
- [x] Plot validation learning curves for all variants
- [x] Use early stopping with pre-specified patience, or justify fixed compute
- [x] Document: optimiser, scheduler, warm-up, gradient clipping, weight decay, batch size, initialisation, mixed precision, thread settings, deterministic flags

> ✅ **§5 DONE (2026-08-13).** Artifacts: `plan/gates/gate2/gate2_learning_curves.md` + `plan/gates/gate2/gate2_learning_curves.png` (per-cell mean validation curves + per-run/per-cell convergence diagnostics; log coverage verified 20/20 runs, 200/200 epoch lines), `plan/benchmark_protocol.md` (authoritative training protocol — optimiser/scheduler/warm-up/clipping/wd/batch/init/mixed-precision/threads/seeding/data, plus elements flagged as undocumented). Verdict: **fixed 10-epoch budget justified** — no cell shows a sustained improvement after epoch 4 (worst-case dip 0.011–0.015 in the (4,4) mean, within seed noise); mean last-3-epoch drift +0.0009; best-val epoch mean 6.5; 3 plateaued / 5 still-improving / 12 oscillating of 20 runs; no evidence of under-training.

### 6. **Expand Dataset Coverage** (Gate 3)
Minimum for journal submission:
- [ ] **ETT family**: ETTh1, ETTh2, ETTm1, ETTm2
- [ ] **Large multivariate**: Electricity, Traffic, Weather
- [ ] **Different dynamics**: Exchange, Solar-Energy, or PEMS
- [ ] **Mechanistic synthetic**: Controlled sinusoids, change points, delayed-copy tasks

Horizons: H ∈ {96, 192, 336, 720}
Lookbacks: L ∈ {96, 256, 512, 720, 1024}

### 7. **Add Strong Baselines**
- [ ] **Same-backbone attention**:
  - [x] Full causal attention
  - Sliding window
  - Linformer, Performer, Reformer/LSH
  - Informer/ProbSparse
  - Block-sparse (BigBird/Longformer)
  - Routing Transformer
- [ ] **End-to-end forecasting models**:
  - DLinear, PatchTST, iTransformer
  - TimesNet, ModernTCN
  - CATS or recent state-space/mixer baseline

> ✅ **§7 partial — Full causal attention baseline DONE (2026-08-14).** 5 paired seeds {42,123,2024,7,99}, frozen task (L=256, H=96, 10 epochs, `plan/benchmark_protocol.md`). Harness `plan/gates/baseline/baseline_normal_sweep.py`, results `plan/gates/baseline/baseline_normal_results.jsonl`, summary `plan/gates/baseline/baseline_normal_summary.md` (E-audited). NormalAttention wiring sanity-verified (bit-identical to naive causal reference; `plan/gates/baseline/check_normal_wiring.py` + `plan/gates/baseline/normal_sanity_check.md`). 3-way result — Normal val 0.8416±0.0799 / test 1.0814; CSA/Flat (4,4) 0.6332±0.0611 / 0.9079 (−24.76% val); DRRA (8,4) 0.5967±0.0710 / 0.7988 (−29.10% val). Compressed variants beat Normal in 5/5 seeds (paired). Caveats: single dataset (ETTh1), params not equalized across rows (~2%), descriptive only (no significance test). Formalized in RESULTS.md "Baseline Comparison" section; novelty/prep ledger `plan/paper_notes.md`. Remaining §7 items (other same-backbone + end-to-end baselines) pending.

---

## 📊 STATISTICAL RIGOR

### 8. **Implement Proper Statistics** (Gate 4)
- [ ] Run **5-10 paired seeds** for headline comparisons
- [ ] Report mean, standard deviation, 95% confidence intervals, individual seed points
- [ ] Fit mixed-effects model:
  ```
  MSE = β₀ + β₁ log₂(c_KV) + β₂ log₂(c_R) + β₃ log₂(c_KV)log₂(c_R) + random effects
  ```
  - Main claim requires β₂ > β₁ in relevant operating region
- [ ] For equivalence claims: Predeclare margin and use **TOST** or Bayesian ROPE
- [ ] For multi-dataset comparisons: Use paired Wilcoxon/Friedman with Holm correction
- [ ] Respect temporal dependence: block bootstrap or HAC-robust tests

### 9. **Pre-register Testable Hypotheses**
- [ ] H1: Routing sensitivity — increasing c_R causes larger MSE deterioration than c_KV
- [ ] H2: Dual-rate Pareto advantage — (8,4) Pareto-dominates equal-rate at comparable latency
- [ ] H3: Hardware crossover — dense masked faster below candidate-width threshold
- [ ] H4: Signal dependence — routing advantage larger for change points/sparse events
- [ ] H5: Surrogate noninferiority (if retained)

---

## ⚙️ SYSTEMS & HARDWARE VALIDATION

### 10. **Complete Systems Benchmarking** (Gate 5)
- [ ] Report full hardware details:
  - Apple chip, core counts, RAM, macOS version
  - PyTorch, BLAS/Accelerate backend, compiler settings
  - Thread and inter-op settings
- [ ] Measure **beyond forward latency**:
  - p50/p90/p99 latency (bootstrap CIs)
  - Throughput
  - Peak resident memory, activation memory
  - Theoretical FLOPs/MACs
  - Training time and time-to-quality
- [ ] Scaling sweeps:
  - Sequence length: 128 → 4096+
  - Batch sizes: 1, 8, 32
  - Model depth and width
- [ ] **Cross-hardware**: At least Apple Silicon + Linux x86 CPU (ideally GPU)
- [ ] Stage-level profiling: compression, routing/index construction, score calc, masking/softmax, aggregation, output projection

### 11. **Establish True Computational Complexity**
- [ ] Derive explicit complexity for routing and retrieval
- [ ] If O(S²/c_KV) with constant-factor reduction → state clearly
- [ ] Only claim subquadratic if candidate budget is sublinear AND routing avoids O(S×M_R) dense comparison
- [ ] Report empirical log-log scaling slopes

---

## 🔬 MECHANISTIC DEPTH

### 12. **Add Explanatory Analyses** (would elevate paper quality)
- [ ] **Routing recall**: Compare selected candidates with full-attention high-mass positions
- [ ] **Lag localisation**: Measure distance between selected and true causal lag on synthetic tasks
- [ ] **Content distortion**: Report compressed KV reconstruction error, block variance, spectral energy retention
- [ ] **Event-conditioned error**: Stratify error around peaks, change points, transients
- [ ] **Attention entropy**: Report route stability and diversity
- [ ] **Mediation analysis**: Test if c_R effect on error is mediated by routing recall

### 13. **Error Decomposition Framework**
- [ ] Introduce oracle-routed compressed output
- [ ] Bound total error:
  ```
  ||y_full - y_hat|| ≤ ||y_full - y_content-oracle|| + ||y_content-oracle - y_routed||
  ```
- [ ] Estimate each term's change with c_KV and c_R

---

## 📝 MANUSCRIPT PREPARATION

### 14. **Restructure Paper**
- [ ] **Title**: "Dual-Rate Routed Attention for Efficient Long-Horizon Time-Series Forecasting"
- [ ] **Introduction**: Problem → Domain tension → Gap → Approach → Result & limitation
- [ ] **Related Work**: Position carefully vs. DeepSeek-V4, RADLADS, FAR, routing work
- [ ] **Method**: Formalise c_KV and c_R; explicit complexity derivation; causality proof
- [ ] **Experimental Design**: Datasets, horizons, baselines, tuning, seeds, statistics
- [ ] **Results**: Test hypotheses (not leaderboard)
- [ ] **Ablations**: 2×2 controls; shared-Q; output rank; W/K; negative results
- [ ] **Discussion**: Mechanism, failure regimes, hardware dependence, limitations

### 15. **Figures and Tables to Create**
- [ ] Figure 1: Architecture diagram (routing + content pathways)
- [ ] Figure 2: 2-D heatmaps MSE and latency over c_KV × c_R
- [ ] Figure 3: Accuracy-latency Pareto fronts by dataset/hardware
- [ ] Figure 4: Scaling curves with empirical slopes
- [ ] Figure 5: Routing recall/content distortion diagnostics
- [ ] Table 1: Notation and complexity
- [ ] Table 2: Datasets and splits
- [ ] Table 3: Main results
- [ ] Table 4: Equivalence tests
- [ ] Table 5: Ablations
- [ ] Table 6: Negative results

---

## 📦 REPRODUCIBILITY

### 16. **Prepare Reproducibility Package** (Gate 6)
- [ ] Machine-generated run manifest with:
  - run_id, timestamp, git commit, config hash
  - Dataset version/checksum, split indices
  - Model: c_KV, c_R, W, K, indexer, param count
  - Training: seed, schedule, epochs
  - Accuracy: validation/test MSE
  - Efficiency: raw timings, memory, FLOPs
  - Diagnostics: routing recall, content distortion
- [ ] Automated table regeneration from manifest
- [ ] Unit tests: causality masks, bias initialisation, param counts, softmax equivalence
- [ ] Environment lockfile, data hashes
- [ ] Command to reproduce headline table

---

## 🎯 DECISION POINTS

### 17. **Evaluate After Gate 2 Factorial Confirmation**

**If routing-resolution effect is reproducible:**
- Proceed with full breadth expansion (Gates 3-6)
- Target: TMLR (methodological) or JCS (systems-focused)

**If effect is confined to ETTh1/small subset:**
- Reframe as dataset-characterised phenomenon
- Identify signal properties that predict the effect
- Target: MLWA or Neurocomputing

**If accuracy gains disappear but systems result stable:**
- Pivot to computational-science paper about hardware-aware sparse attention
- Target: Journal of Computational Science

**If DRRA doesn't beat modern baselines but improves Transformer backbone:**
- Publish controlled architectural result without SOTA claim
- Still publishable as design study

---

## ⏱️ RECOMMENDED TIMELINE

| Phase | Duration | Activities |
|-------|----------|------------|
| **Week 1-2** | Fix foundational issues, run causality tests, rename method | Gates 0-1 |
| **Week 3-4** | Factorial confirmation with 5-10 seeds | Gate 2 |
| **Week 5-6** | Evaluate results; decide on pivot vs. proceed | Decision point |
| **Week 7-10** | Expand to 6-8 datasets + baselines | Gate 3 |
| **Week 11-12** | Statistical analysis + equivalence tests | Gate 4 |
| **Week 13-15** | Complete systems benchmarking | Gate 5 |
| **Week 16-17** | Add mechanistic analyses | Optional (strongly recommended) |
| **Week 18-20** | Write paper + prepare reproducibility package | Gate 6 |

**Total: ~4-5 months** for strong journal submission

---

## ⚠️ KEY WARNINGS FROM THE STRATEGY DOCUMENT

- **Do not** submit the present pilot to a top journal — desk rejection risk is high
- **Do not** claim "statistically identical" from seed 42 and informal ±0.002 band
- **Do not** use "Zero-accuracy-cost" language — absence of observed difference ≠ equivalence
- **Do not** claim "CSA" novelty — acknowledge 2026 overlap with DeepSeek-V4 and recent routing work
- **Do not** treat overlapping forecast windows as IID samples
- **Do not** select equivalence margin after inspecting results

---

**Bottom line**: The next immediate step is to **freeze the task definition** and run the **strict factorial confirmation (Gate 2)**. This will determine whether the core hypothesis survives controlled testing and whether to proceed with the full experimental program or pivot to a more limited scope.