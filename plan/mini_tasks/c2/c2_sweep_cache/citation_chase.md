# Citation chase + web search — C2 sweep

**Date:** 2026-08-16 · **By:** main agent (assembled from subagent data + own searches)

## 1. Citation counts per seed (Semantic Scholar Graph API, limit 100 each)

| Seed | Citing rows returned | 2024+ attention-titled |
|---|---|---|
| NSA (2502.11089) | 100 | 41 |
| DeepSeek-V4 (2606.19348) | 100 | 2 (paper too new) |
| Routing Transformer (2003.05997) | 100 | 39 |

S2 data is incomplete for the newest papers (DS-V4 has only 2 attention-titled citing rows). Kept candidates from citations are merged into `c2_sweep_cache/candidates_web.json` (98 entries total: 82 citations + 16 web).

## 2. Notable candidates surfaced by the citation chase (all assessed in the sweep log)

- 2607.21752 gzip-guided sparse attention (cited by both NSA and Routing-T lines) → RELATED (row 12)
- 2606.13392 MiniMax MSA → RELATED (row 13)
- 2606.22874 SpotAttention → RELATED (row 14)
- 2608.01665 Macer → IRRELEVANT (row 15)
- 2606.07703 "How Much Dense Attention is Necessary?" — layer-level GQA/FULL allocation; not checked at methods level (layer allocation, not compression × routing) → noted, not a counter candidate
- 2606.18056 ConSA "Controllable Sparsity in Hybrid Attention via Learnable Allocation" — noted; hybrid-attention layer allocation, same reasoning → not a counter candidate

## 3. Web search findings (4 queries, run by subagent + main agent)

1. "attention compression rate routing resolution varied independently main effects" → SLA2 (2602.12675, sparse-linear attention with routing; linear-attention hybrid, no content-compression knob → RELATED, not in log), plus a scirate listing of conditional-computation work.
2. "decoupling content compression from routing granularity sparse attention" → Gist/Forget-Then-Recall (2604.20920, row 27, RELATED — knobs coupled by Eq. A.1), TriRoute (2607.06601, row 25), NSA explainer blog (non-archival).
3. "sparse attention compression and selection ablation factorial fixed task" → The Sparse Frontier (2504.17768, row 26, RELATED — single-axis selection sweep), Fasa (frequency-aware sparse attention, routing-only), 2607.21752 (row 12).
4. "efficient attention time series forecasting compression routing design study 2025" → GateTS (2508.17515, routed MoE for TS — no compression knob), BiTST (bi-level routing TS — routing-only), WaveRoRA (2410.22649, row 23), "Dynamic Routing Sparse Attention" TS paper (routing-only), MoE-Transformer (routing-only). **No TS-domain work surfaced that varies content compression × routing independently.**

## 4. Bottom line

The web/citation channels surfaced no COUNTER candidate; every two-mechanism paper found couples its knobs (SSA Eq. A.1, MiniMax matched-budget), lacks a content-compression knob (Sparse Frontier, SpotAttention, TwinFormer, gzip-guided), or lacks a routing knob (TokenDecouple, AB-Sparse). All assessed rows: see `c2_sweep_log.md`.
