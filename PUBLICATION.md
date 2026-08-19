# Contribution & Publishability Assessment

> Companion to `RESULTS.md` and `WRITEUP.md`. This document describes **what was done**, classifies **what kind of contribution** the work is, and gives an honest **publishability assessment** with a concrete roadmap.

> **⚠️ Freeze notice (same supersession as `WRITEUP.md` §2.2 / `RESULTS.md` TASK FREEZE NOTICE):** all Val/Test MSE, speed, and Perf/Spd figures in this document predate the direct-96 task freeze and are **superseded** — they were produced under the old per-token next-step task and leaky full-series normalization. They describe the **pre-freeze pilot**, not results of the frozen task. Valid numbers come only from **Gate 2** runs under the frozen protocol (`plan/gates/gate1/gate1_task.md`). Attention-module parameter counts (e.g. EPP 95,652) carry over unchanged to Gate 2; legacy full-model counts predate the horizon head (+85,785 params, see `plan/gates/gate1/gate1_changes.md`).
>
> **Removal notice (2026-08-18):** the pre-freeze **speed/latency figures** (forward/training ms, speedups, Perf/Spd) have been removed from this document and from `RESULTS.md` / `WRITEUP.md` per `plan/paper_notes.md` §4. Original measurements are preserved in `experiment-session-new-attention.md`; re-measurement is planned under the Gate 5 hardware/latency protocol (`plan/next_step.md` §10).

---

## 1. What Was Done (summary of the work)

A focused empirical study of **Dual-Rate Routed Attention (DRRA) variants for long-sequence time-series forecasting**, on **ETTh1** (lookback 256, horizon 96; frozen task: direct 96-step forecasting — one forward pass `x = [B, 256, 7]` → `out = [B, 96, 7]` via a horizon head from the last hidden state, train-only z-score normalization; spec `plan/gates/gate1/gate1_task.md`). All models share one minimal Transformer block (hidden 128, 4 heads, head_dim 32, attention params 95,652–152,492 — full model 262,571–319,411 — CPU-only Apple Silicon, fp32, AdamW 1e-4, 10 epochs, seed 42). The *only* difference between variants is the attention module.

### 1.1 The variant family (all in-repo, all reproducible)

| Model | Attention | Content cols (KV + window; S=256) | Val MSE |
|---|---|---|---|
| **Normal** | Full O(S²) causal | 256 (no sink) | **0.1083** 🥇 |
| **Flat** | DRRA 4:1 (two-series compressor + flat indexer) | 96 (64 KV + 32 win) + 1 sink | 0.1085 🥈 |
| Modified | DRRA 4:1 + hierarchical indexer | 160 (128 KV + 32 win) + 1 sink | 0.1088 |
| FlatPlus | 4:1 + linear-pool indexer / gated residual KV | 96 (64 KV + 32 win) + 1 sink | 0.1098 |
| **ExpertPlusPlus** | DRRA **8:1 KV + 4:1 routing**, shared-Q, slim O, window 16 | 48 (32 KV + 16 win) + 1 sink | 0.1099 |
| ExpertFlat | DRRA 8:1 on **both** axes | 64 (32 KV + 32 win) + 1 sink | 0.1102 |
| Stacked (legacy) | 2:1→2:1 stacked compression | N/A (no source) | 0.1116 |

**Content cols = KV blocks + window; the "+1 sink" is a single softmax column of 4 scalar logits (one per head) — NOT a KV token (verified registry). Stacked: legacy numbers; no runnable source in repo (missing from model.py/compare.py) — parameter and column counts N/A (no source). Pre-freeze forward-latency figures for this table were removed 2026-08-18 (superseded; see removal notice above).**

### 1.2 The central finding and the design insight

**Central finding (pre-freeze pilot — superseded, see freeze notice above):** within the pilot variant family, the decoupled-rate cell **ExpertPlusPlus (EPP) — (c_KV=8, c_R=4)** — matched Flat's validation accuracy (0.1099 vs 0.1085, gap +0.0014 inside the ±0.002 run-to-run band) with **33.8% fewer parameters than Flat** ((144,548 − 95,652)/144,548; 95,652 attention params — full model 262,571 — *fewer than even the full-attention Normal model's 102,496 attention / 269,415 full*). The earlier "goal contract" framing (a speed target vs Flat) that produced this comparison is retired, along with all pre-freeze latency figures (removed 2026-08-18 — see removal notice above); this is reported as an observation from the pilot, not as a mechanism-level result.

**One-sentence design insight:** *routing granularity carries accuracy; KV content density only buys speed.* EPP decouples the two compression axes — 8:1 KV content (32 blocks, cheap dense attention over 48 columns) while keeping Flat's fine 4:1 router (64 index tokens). The control experiment supports the point: **ExpertFlat** (8:1 on *both* axes) — most aggressive compression of the variants predating EPP, but 2nd-worst accuracy (0.1102; the least accurate overall is Stacked at 0.1116 — legacy numbers) — showing that coarsening the router — not the content — is what costs accuracy.

Supporting engineering cuts (all verified zero-accuracy-cost):
- **Shared-Q routing** — the main per-head Q (already RoPE'd + normalized) doubles as the routing query, deleting `idx_q_proj` entirely (valid because `head_dim == index_head_dim`).
- **Slim O bottleneck** — `o_lora_rank` 128 → 64 (LoRA-style grouped O projection).
- **Sliding window 32 → 16** — free compute (same val, *better* test: 0.1665 → 0.1654).
- **Dense masked attention over sparse selection** — top-k selection implemented as dense GEMMs over 48 columns with −∞ masking (exact softmax, no approximation); on CPU this comfortably beat per-query sparse gather.

### 1.3 Secondary contribution: surrogate attention (inference-time attention replacement)

A separate pipeline (`train_surrogate.py`): jointly distill the attention block's output into a cheap student (λ·MSE with stop-gradient), then swap the student in at inference.

- **v1 (per-token MLP)**: +31% val (0.1424) — pointwise functions cannot replicate cross-token routing (expressivity limit, not a training failure).
- **v2 (windowed + global prototypes)**: causal window W=32 via `unfold` (O(S·W·d), not S²) + 8 input-independent global KV prototypes (sink-like) + relative-position bias. **0.017M params (~82% fewer than EPP)**, val 0.1269 vs teacher 0.1264 at the recorded 5+1-epoch run (~0.4% gap), test MSE actually beats the teacher. The teacher is **ExpertPlusPlus** (the code's default); its val is printed at runtime, so it is **not re-derivable from code** — the recorded value 0.1264 stands. These 5+1-epoch surrogate numbers are **not apples-to-apples with the 10-epoch main results**. Pre-freeze speed figures for the surrogates were removed 2026-08-18 (superseded; see removal notice above). 

### 1.4 Documented negative results (research value)

Sparse-gather routing (far slower on CPU) · hierarchical indexer (lost to flat) · multi-scale KV pyramid (overparameterized) · learnable block-bias offset (NaN instability ~50% of runs) · linear-pool indexer (loses per-head×per-dim routing flexibility) · stacked 2:1→2:1 (optimization harder at 10 epochs). Plus one methodology bug fix: `torch.empty` → `torch.zeros` for all bias parameters (uninitialized memory was the intermittent-NaN root cause on macOS).

---

## 2. What Kind of Contribution Is This?

**Framing: a two-axis design study, not a novel sparse-attention mechanism.** This work studies the **compressed-and-indexed attention family** along two independent axes — KV compression rate c_KV and routing resolution c_R — on one frozen task (ETTh1, direct-96). It does not claim a new mechanism: every building block (two-series softmax-overlap compression, fine router over coarse blocks, shared-Q routing, slim O, dense masked attention over sparse selection) is a configuration of known ideas, and overlap with recent work (DeepSeek-V4's Compressed Sparse Attention, NSA, the routing-attention line) is acknowledged rather than elided — see `plan/lit_audit.md`. The contribution is the *study*, decomposed as:

1. **(a) A controlled 2×2 factorial design (primary).** The c_KV × c_R grid (4:1 / 8:1 on each axis) under an aux-identical contract — shared-Q, fixed window/top-k/heads, near-equalized parameter count, paired seeds — is the experimental backbone (`plan/gates/gate2/gate2_design.md`, `plan/gates/gate2/gate2_factorial.py`). This is what makes the family's trade-off structure measurable rather than anecdotal.
2. **(b) A decoupled-rate finding (the publishable nugget).** *Routing granularity carries accuracy; KV content density only buys speed.* Concretely, the (c_KV=8, c_R=4) cell (EPP) matched the (4,4) baseline's accuracy while halving the attention matrix — and the ExpertFlat control (8:1 on *both* axes) shows that coarsening the router — not the content — is what costs accuracy. Falsifiable, demonstrated by the factorial controls, and (to our knowledge) not stated this explicitly in existing work — a claim to be checked against the literature before submission (see `plan/lit_audit.md`).
3. **(c) Honest efficiency/accuracy characterization, including limitations.** A verified per-module parameter ledger and an explicit limitations list: single dataset (ETTh1), single seed in the pilot, no external baselines, CPU-only tiny scale, dense-vs-sparse is explicitly a **CPU** finding (likely inverts on GPU). "Statistically identical" is a within-noise observation from one seed, not a statistical equivalence claim. Pre-freeze CPU latency claims were removed 2026-08-18 (superseded; see removal notice above); measured latency/FLOPs/hardware transfer is Gate 5 follow-up work.
4. **(d) Reproducibility artifacts.** Machine-readable results manifest (`plan/gates/gate0/gate0_manifest.json`), verified parameter registry (`plan/gates/gate0/gate0_registry.json`), frozen task spec (`plan/gates/gate1/gate1_task.md`), causal-validity suite (all variants PASS), sanity tests, and a self-contained codebase where every number traces to a file.
5. **(Secondary, separable.)** A negative-results corpus (six failed designs with failure modes documented) and the surrogate/retired-attention distillation line (windowed + global-prototype student, ~82% parameter reduction vs EPP) — useful, but neither is the paper's core claim.

**What it is not:** not a new SOTA forecasting model (val 0.1099 is internal-family best-or-near-best under the *pre-freeze* pilot, and nothing beats a proper external baseline comparison yet — none exists in the repo); not a novel sparse-attention mechanism; not a theory paper; not a GPU/HPC paper.

---

## 3. Can This Be Published?

### 3.1 Verdict (honest)

> **Not publishable as-is at a main-track conference. It is currently a strong, well-executed workshop-paper-level empirical study.** The core (decoupling insight + honest methodology + reproducible code) is publishable with modest additional work; a full conference paper needs substantially more.

### 3.2 Strengths a reviewer would credit

- **Clean, falsifiable insight** (routing granularity vs content density) with a direct control experiment (ExpertFlat).
- **Honest experimental methodology**: explicit variance handling, contention-robust timing, "dense-with-masking ≡ exact top-k softmax" argument.
- **Fully reproducible, tiny, self-contained codebase** — every number traces to a file; sanity tests included.
- **Negative results documented** — rare and valued by careful reviewers.
- **Parameter efficiency** — EPP (95,652 attention / 262,571 full) is smaller than even the full-attention baseline (Normal: 102,496 attention / 269,415 full), which is a clean headline.

### 3.3 Weaknesses — the "reviewer will ask" list (in rough severity order)

| # | Issue | Current state | Severity |
|---|---|---|---|
| 1 | **Single dataset** (ETTh1 — the *easiest* of the ETT family, 7 features) | No ETTh2/ETTm1/ETTm2, no Electricity/Traffic/Weather | 🔴 fatal as-is |
| 2 | **Single seed (42), one run per model** | ±0.002 band reported but no error bars / significance test | 🔴 fatal as-is |
| 3 | **No external baselines** | Only internal variant-vs-variant; needs PatchTST, iTransformer, DLinear, Informer under the *same* protocol | 🔴 fatal as-is |
| 4 | **Tiny scale + CPU-only** | 95,652–152,492 attention params (262,571–319,411 full model), hidden 128, fp32 CPU. Efficiency claims at deployment-relevant scale unverified; "dense beats sparse" is explicitly a **CPU** finding and likely inverts on GPU | 🔴 fatal as-is for a systems claim |
| 5 | **Central accuracy comparison is a null result** | EPP≈Flat within noise — fine for an efficiency/design-study paper, but needs stats to say "no significant loss" | 🟠 major |
| 6 | **Related-work positioning missing** | DeepSeek **NSA** already does coarse+fine granularity (hierarchical routing); the LoRA-style Q / grouped O projections descend from **MLA**; plus linear-attention/S4/Mamba and PatchTST/iTransformer families. Must position explicitly | 🟠 major |
| 7 | **"Goal contract" framing** | Retired 2026-08-18: the internal speed goal vs Flat and all pre-freeze latency figures were removed (paper_notes.md §4) | ✅ resolved (reframed) |
| 8 | **Surrogate section protocol mismatch** | 5+1-epoch distillation vs 10-epoch main results; v1 loses 31%; must answer *"why not just train a smaller model?"* | 🟠 major (for that section) |
| 9 | **Missing ablations reviewers expect** | top-k sensitivity, compress-rate sweep, window sweep (done for 32→16 only), head/head_dim sensitivity, scaling behavior (S, hidden), FLOPs & memory accounting, GPU transfer | 🟠 major |
| 10 | **Absolute numbers are small** | Pre-freeze latency figures removed 2026-08-18 (superseded); any future latency claim must be framed as *latency for CPU/edge forecasting*, not throughput at scale — re-examine under Gate 5 | ✅ resolved (claim removed) |

### 3.4 Realistic venue targets

| Tier | Venues | Required additions | Effort |
|---|---|---|---|
| **Workshop (reachable now-ish)** | ICML/NeurIPS/ICLR/IJCAI efficiency & time-series workshops; KDD/CIKM applied-AI workshops | 2–3 more datasets, 3–5 seeds, 1–2 external baselines, related-work positioning | ~2–3 weeks |
| **Applied domain conference** | ICDM, CIKM, PAKDD, Applied Intelligence, IEEE TNNLS brief | All of the above + 5–8 datasets + full baseline suite + ablations + GPU section | ~1–2 months |
| **Main-track ML conference** | NeurIPS/ICML/ICLR/AAAI main | Everything above + scaling study (hidden 128→1024, seq 256→4096), GPU + memory + FLOPs, stronger statistical rigor, and either a sharpened accuracy claim or a clearly-scoped efficiency-only framing | ~3–6 months |

### 3.5 Roadmap to publishable (concrete, prioritized)

1. **Multi-dataset** — ETTh2, ETTm1, ETTm2, Electricity, Traffic, Weather, Exchange (same normalization/protocol).
2. **Multi-seed statistics** — 3–5 seeds, report mean ± std; for any future latency claim (Gate 5), keep the alternating protocol and report the *ratio* distribution; paired test for "no significant accuracy loss".
3. **External baselines** — PatchTST, iTransformer, DLinear, and (for the efficiency angle) a vanilla small transformer and a linear-attention (Mamba/S4-lite) under identical protocol.
4. **GPU + accounting** — A100/L40S timings, FLOPs/param/memory table; revisit dense-vs-sparse on GPU (flash-attention-style masking may change the answer — either way it's a *stronger* result).
5. **Scaling study** — confirm accuracy-parity and any Gate-5-measured latency advantage survive at hidden 512–1024 and seq 1024–4096 (this is the single most convincing addition for reviewers).
6. **Ablation sweep** — top-k ∈ {8,16,32}, compress-rate ∈ {4,8,16}, window ∈ {8,16,32}, head count/dim; a heatmap of (content-ratio × routing-ratio) to map the whole design space — this would *strengthen the core insight into the paper's centerpiece figure*.
7. **Related work** — position vs NSA (coarse+fine routing), MLA (shared-Q/LoRA-Q lineage), FlashAttention/sparse-attention, linear attention & SSMs, PatchTST/iTransformer; state explicitly where the decoupling claim differs.
8. **Reframe** — replace "goal contract" language with a hypothesis-testing framing ("H1: routing granularity — not content density — determines compressed-attention accuracy").
9. **Surrogate section (optional separate paper)** — align epochs to 10, ablate window/global count, and include the *"equal-budget small transformer"* control; could stand alone as a short systems paper.

### 3.6 Bottom line

- **The decoupling insight + negative-results corpus + honest methodology is a legitimate, publishable workshop paper today** with ~2–3 weeks of dataset/seed/baseline/positioning work.
- **It is not a main-track paper yet**: single dataset, single seed, no baselines, CPU-only tiny-scale, and an accuracy claim that is currently within noise. All of these are *additive, mechanical work*, not scientific risk — the core idea does not appear to be broken by any evidence in the repo.
- **Highest-leverage single addition:** the (content-ratio × routing-ratio) design-space map (§roadmap-6) plus a GPU/scaling confirmation — together they would convert "a good internal comparison" into "a general design principle for compressed attention."
