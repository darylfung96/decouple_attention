# Literature & Title Audit — DRRA (two-axis design study framing)

**Date:** 2026-08-12 · **Status:** living process — this is the current-state audit; a **final pre-submission re-audit** is required (fresh search once Gate 3 results exist, before locking the title).

**Context:** contribution reframed as a **two-axis design study** (c_KV compression rate × c_R routing resolution) of the compressed-and-indexed attention family on ETTh1 (frozen direct-96 task). Overlap claims below were checked on 2026-08-12 where marked; items not verifiable from the repo or a quick check are flagged **[NEEDS VERIFICATION]** — nothing here is fabricated, no citation is invented.

## 1. Known overlap landscape (strategy doc + repo + quick check)

| Work | Relation to DRRA | Status |
|---|---|---|
| **DeepSeek-V4 Compressed Sparse Attention (CSA)** | Compression-based sparse attention; the label collision that forced our rename. DeepSeek-V4 hybrid attention = CSA + Heavily Compressed Attention (HCA), for million-token LLM context | **VERIFIED** (arXiv:2606.19348, "DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence", DeepSeek-AI, 2026-04-26). Verified: existence, hybrid CSA/HCA, 1M context, 27% FLOPs / 10% KV cache vs V3.2. **CSA/HCA internals read in depth 2026-08-16** (`plan/mini_tasks/c2/dsv4_csa_read.md`): CSA compresses every m tokens into one entry (two-series overlapped softmax) then selects top-k compressed entries via the lightning indexer (Flash m=4/k=512, Pro m=4/k=1024; HCA m'=128; window 128); knobs exposed but never varied independently (no ablation in the report) |
| **DeepSeek NSA (Native Sparse Attention)** | Coarse-grained compression + fine-grained token selection (hierarchical routing) — closest conceptual cousin; already flagged in PUBLICATION.md §3.3 | **VERIFIED** (arXiv:2502.11089, Yuan et al., Feb 2025) |
| **Routing Transformer (Roy et al.)** | Content-based routing (online k-means) sparse attention — the general routing-attention line | **VERIFIED** (arXiv:2003.05997, "Efficient Content-Based Sparse Attention with Routing Transformers", TACL 2020) |
| **RADLADS** | Attention→linear-attention distillation at scale (RWKV-variant decoders, Qwen2.5 conversions, 350–700M tokens) | **VERIFIED** (arXiv:2505.03005, "RADLADS: Rapid Attention Distillation to Linear Attention Decoders at Scale", May 2025). NOTE: overlaps our **surrogate/retired-attention** secondary line, not the routing/compression core |
| **FAR** | Named in strategy doc alongside RADLADS/routing work; acronym ambiguous | **[NEEDS VERIFICATION]** — candidates found: "FAR: Function-preserving Attention Replacement" (arXiv:2505.21535, attention-replacement/distillation — matches the strategy-doc grouping with RADLADS) and "FAR: Fourier Aerial Video Recognition" (arXiv:2203.10694). Cannot confirm which the strategy doc meant |
| **MLA (Multi-head Latent Attention)** | LoRA-style Q / grouped-O lineage of our shared-Q + slim-O projections | Known from context (DeepSeek-V2/V3; cited in PUBLICATION.md §3.3) — canonical citation **[NEEDS VERIFICATION]** |
| **TS forecasting baselines** | PatchTST, iTransformer, DLinear, Informer, TimesNet, ModernTCN (Gate 3 list) | Known from context; citations to be collected together with the Gate 3 baseline runs |

## 2. Honesty split: verified now vs needs a real pre-submission search

- **Verified by quick check (2026-08-12):** DeepSeek-V4 CSA/HCA existence + arXiv id; NSA; Routing Transformer; RADLADS. Citable on the strength of the arXiv abstracts.
- **[NEEDS VERIFICATION] before any citation:** FAR identity; MLA canonical citation; any fresh routing/compression-attention work from the last ~12 months at pre-submission time.
- **C2 sweep DONE 2026-08-16** (`plan/mini_tasks/c2/2026-08-16-c2-lit-sweep.md` + `plan/mini_tasks/c2/c2_sweep_log.md`): DeepSeek-V4 CSA internals read in depth (`plan/mini_tasks/c2/dsv4_csa_read.md`) — DS-V4/NSA do NOT decouple content-compression from routing granularity (knobs fixed or coupled); no 2024–2026 work frames the two-axis space with independent variation and separate main effects (0 counterexamples, 29 rows assessed). C2 phrasing KEEPed in the paper (user decision 2026-08-16).

## 3. Title candidates (design-study framing)

1. **Dual-Rate Routed Attention for Efficient Long-Horizon Time-Series Forecasting** (from plan §14 — method-led; keep only if the design-study framing reads clearly in the abstract)
2. **How Much to Compress, How Fine to Route: A Two-Axis Design Study of Compressed-and-Indexed Attention for Time-Series Forecasting** (design-study lead)
3. **Compression Rate × Routing Resolution: Mapping the Accuracy–Efficiency Trade-off of Routed Attention on ETTh1** (empirical-map lead)
4. **Decoupling Content Compression from Routing Granularity in Time-Series Attention: A Controlled 2×2 Design Study** (finding-led; foregrounds contribution (b))

**Decision 2026-09-28 (Stage-1 revision):** locked to reviewer-preferred
**Decoupling Compression and Routing in Attention for Time-Series Forecasting**
(design-study framing; `paper/main.tex`). Candidates 1–4 above superseded; memorable
shorthand *Compress Coarsely, Route Finely* reserved pending multi-dataset proof of (8,4).

**Decision rule:** prefer 2 or 3 if reviewers should see "study, not mechanism"; fall back to 1 if the venue wants method-name recognition. Final choice at the pre-submission re-audit.

## 4. Pre-submission checklist (remaining)

- [x] Verify DeepSeek-V4 CSA internals in depth — especially whether it decouples content vs routing granularity (affects contribution (b) claim) — **DONE 2026-08-16** (`plan/mini_tasks/c2/dsv4_csa_read.md`; verdict: knobs exposed but never varied independently; no ablation in the report)
- [ ] Resolve FAR identity; add RADLADS citation to the surrogate/related-work paragraph
- [ ] Add missing baselines after Gate 3 (PatchTST, iTransformer, DLinear, Informer, linear/SSM line) and collect their citations with the runs
- [ ] Final title decision (candidates above) + keyword list (draft: time-series forecasting; sparse attention; compression; routing; efficiency; design study; ETTh1; DRRA)
- [x] Fresh search sweep (2024–2026 routing/compression-attention) — **C2 portion DONE 2026-08-16** (`plan/mini_tasks/c2/2026-08-16-c2-lit-sweep.md` + `plan/mini_tasks/c2/c2_sweep_log.md`, 0 counterexamples); remaining for the full re-audit: TS-efficiency search + fresh 12-month window at pre-submission
