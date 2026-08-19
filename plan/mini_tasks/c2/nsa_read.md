# NSA (Native Sparse Attention) — knob inventory & C2 verdict

**Read by:** main agent, full text (arXiv HTML), 2026-08-16. Quotes verbatim from the extracted text.

## 1. Metadata
- arXiv:2502.11089 (v2), "Native Sparse Attention: Hardware-Aligned and Natively Trainable Sparse Attention", Yuan et al., published 2025-02-16, DeepSeek-AI.

## 2. Compression module (content-compression knob)
- NSA compresses keys/values into temporal blocks: block size `l`, sliding stride `d` (overlapped compression across adjacent blocks).
- Fixed configuration: "we set compression block size l = 32, sliding stride d = 16, selected block size l' = 64, selected block count n = 16 (including fixed activating the 1 initial block and 2 local blocks), and sliding window size w = 512" (§4, repeated verbatim in §5).
- The compression rate (block size l) is a **structural parameter with a single reported setting**; no experiment varies it.

## 3. Selection module (routing knob)
- Fine-grained token selection: selects `n = 16` blocks of size `l' = 64` per query via attention-score-based block selection; fixed first block + 2 local blocks always active.
- Routing cost per query is O(n) after a block-level prefilter (top-n over block scores).
- Single reported configuration; no knob sweep.

## 4. Ablation inventory
| What is varied | Where | Values | Benchmark | Isolates which axis? |
|---|---|---|---|---|
| NSA vs Full Attention | Table 1 (pretrain), Table 2 (LongBench), Table 3 (AIME after SFT) | whole-architecture | general benchmarks / LongBench / AIME | neither (architecture comparison) |
| NSA vs sparse-attention baselines (StreamingLLM, H2O, Quest, etc.) | Table 2 | matched sparsity | LongBench | neither — baselines sparsity-equalized: "the sparsity of all sparse attention methods set to the same to ensure a fair comparison" (§4); "we set the token activated by each query in all sparse attention baselines to 2560 tokens" (§4) |
| Memory-access analysis | Table 4 | — | decoding cost model | neither |
| **Compression block size l or selection budget n varied independently** | **NOT FOUND in accessible text** | — | — | — |

## 5. Decoupling verdict
`NSA DECOUPLING: NO` — NSA implements both coarse compression and fine selection, but reports exactly one configuration (l=32, d=16, l'=64, n=16, w=512) in every experiment; there is no ablation that varies the compression granularity or the selection budget, let alone a factorial varying them independently with separate main effects on a fixed task.

## 6. C2 verdict
**RELATED** — both mechanisms present (compression + selection), one fixed configuration, no independent variation, no per-axis main effects. Cannot counter C2.
