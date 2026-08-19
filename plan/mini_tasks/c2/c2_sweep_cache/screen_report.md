# Screening report — C2 sweep (arXiv keyword sweeps)

**Date:** 2026-08-16 · **By:** main agent (dc9ab639 subagent failed mid-task; screening completed by main agent with a keyword pre-filter + manual title/summary review)

## 1. Counts

| Sweep (query) | Papers returned | Kept (attention-relevant) |
|---|---|---|
| "routed attention" | n/a (merged) | merged across sweeps |
| "routing attention" | n/a | merged |
| "compressed attention" | n/a | merged |
| "sparse attention" | n/a | merged |
| "top-k attention" | n/a | merged |
| "block attention" | n/a | merged |
| "token compression" | n/a | merged |
| "selective attention" | n/a | merged |
| "efficient attention" + "time series" | n/a | merged |
| "sparse attention" + "forecasting" | n/a | merged |
| **Total unique papers across all sweeps** | **742** | **189 kept** (94 Routing · 35 KVcomp · 5 Both · 55 other) |

Raw per-sweep results: `c2_sweep_cache/sweep_0.json` … `sweep_9.json`; merged deduped list: `c2_sweep_cache/merged.json`; kept candidates: `c2_sweep_cache/candidates.json`.

## 2. Kept list

See `c2_sweep_cache/candidates.json` (189 entries: id, title, date, 300-char summary, family tag, source sweeps). The 5 "Both"-family candidates and all highest-risk candidates were checked at methods level — results are in `c2_sweep_log.md` (29 rows).

## 3. Borderline cases (kept, flagged)

- **2606.18056 ConSA "Controllable Sparsity in Hybrid Attention via Learnable Allocation"** — hybrid-attention layer allocation; kept but judged not a counter-candidate (layer-level allocation, not compression × routing knobs); noted in citation_chase.md §2.
- **2606.07703 "How Much Dense Attention is Necessary?"** — layer-level full/GQA allocation; same reasoning.
- **2511.18936 SWAN (Sparse Winnowed Attention)** — sparse decomposition with memory reduction; no two-axis design.
- **2505.00315 Mixture of Sparse Attention (MoA)** — budget allocation across layers via Taylor approximation; single-axis (budget) + allocation, no content-compression knob.
- **2411.09688 Squeezed Attention** — query/key "squeezing" (compression of Q/K for scoring, cf. ESA/Unshackling); dimension reduction for scoring, not KV content compression → RELATED.
- **2602.12675 SLA2** — sparse-linear attention with learnable routing; linear-attention hybrid, no content-compression knob → RELATED.

None of the borderline cases survived the rubric (all fail criterion 1 or 2); none is a COUNTER. Final tally: **COUNTER = 0 · RELATED = 26 · IRRELEVANT = 3** (log rows 1–29).
