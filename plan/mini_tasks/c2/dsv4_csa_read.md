# DeepSeek-V4 CSA/HCA deep read — evidence file

Purpose: feeds the novelty-claim verification — "does any paper vary content-compression rate × routing resolution independently and report separate main effects on a fixed task?"

Source: arXiv HTML of arXiv:2606.19348, extracted to `/tmp/dsv4.txt` (fetched via `https://arxiv.org/html/2606.19348`, ~915 KB HTML). All quotes below are VERBATIM from that extraction. Extraction note: math symbols appear interleaved with their LaTeX source (e.g., "mm" = italic *m*, "m′m^{\prime}" = *m′*, "kk" = italic *k*, "1m\frac{1}{m}" = 1/*m*, "nwinn_{\text{win}}" = *n*<sub>win</sub>). Section numbers refer to the paper's own numbering.

## 1. Metadata (Q8)

| Field | Value | Pointer / verbatim |
|---|---|---|
| arXiv id | 2606.19348 (v1) | first-page stamp: "arXiv:2606.19348v1 [cs.CL] 26 Apr 2026" |
| Exact title | DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence | title on first page (and HTML `<title>`) |
| Authors | DeepSeek-AI (single collective byline; no individual names listed in accessible text) | byline line immediately under the title on the first page: "DeepSeek-AI" |
| Submission / update dates | 26 Apr 2026 (v1; no later version present in accessible text) | same first-page stamp |
| Page count | NOT FOUND in accessible HTML text — PDF check pending (see note below) | — |

Note: page count to be confirmed from the PDF; not verifiable from the HTML text alone.

## 2. CSA structure (Q1–Q2)

### Q1 — what is compressed, at what granularity, what rate(s)

What is compressed: the KV cache (keys and values share the same entry — "Shared Key-Value MQA"), along the sequence dimension, in blocks of *m* consecutive tokens.

- Section 2.3 (intro to hybrid attention): "CSA integrates both compression and sparse attention strategies: it first compresses the Key-Value (KV) cache of every mm tokens into one entry, and then applies DeepSeek Sparse Attention (DSA) (26) where each query token attends to only kk compressed KV entries."
- Section 2.3.1: "The core architecture of CSA is illustrated in Figure 3, which first compresses the KV cache of each mm tokens into one entry, and then applies DeepSeek Sparse Attention for further acceleration."
- Overlap detail (each compressed entry is built from 2*m* source entries, overlapping with the neighboring entry's window): "Note that each CiCompC^{\text{Comp}}_{i}\in\mathbb{R}^{c} is derived from 2m2m KV entries, but the indexes of CbC^{b} used for CiCompC^{\text{Comp}}_{i} and the indexes of CaC^{a} used for Ci−1CompC^{\text{Comp}}_{i-1} are overlapped." (Section 2.3.1)
- Effective rate: "Therefore, CSA in fact compresses the sequence length to 1m\frac{1}{m} times." (Section 2.3.1)
- Sliding-window complement (uncompressed, runs in parallel with the compressed entries): "we introduce a supplementary attention branch to both CSA and HCA in a sliding window manner, for better modeling of local dependencies. To be specific, for each query token, we additionally produce nwinn_{\text{win}} uncompressed KV entries corresponding to the recent nwinn_{\text{win}} tokens." (Section 2.3.3, "Additional Branch of Sliding Window Attention")

One rate or several: ONE global compression rate per model variant (no per-layer or per-head rate is stated anywhere in the accessible text):

- Flash (Section 4.2.1, "DeepSeek-V4-Flash"): "For CSA, we set the compression rate mm to 4, the number of indexer query heads nhIn_{h}^{I} to 64, the indexer head dimension cIc^{I} to 128, and the number of KV entries selected for sparse attention (i.e., attention top-k) to 512."
- Pro (Section 4.2.1, "DeepSeek-V4-Pro"): "For CSA, we set the compression rate mm to 4, the number of indexer query heads nhIn_{h}^{I} to 64, the indexer head dimension cIc^{I} to 128, and the number of KV entries selected for sparse attention (i.e., attention top-k) to 1024."
- Window size (both models, Section 4.2.1): "For the additional branch of sliding window attention, the window size nwinn_{\text{win}} is set to 128."

So: compression = block of *m* tokens → 1 entry; *m* = 4 for both Flash and Pro; plus an uncompressed 128-token sliding window per query.

### Q2 — routing / selection mechanism and resolution

Selection is BLOCK-LEVEL (each candidate is one compressed block of *m* tokens), TOP-K, PER QUERY TOKEN. The score for (query token *t*, compressed block *s*) is computed by the "Lightning Indexer" and aggregated over the *n*<sub>*h*</sub><sup>I</sup> indexer heads into a single scalar:

- Section 2.3.1 ("Lightning Indexer for Sparse Selection"): "After obtaining the compressed KV entries CCompC^{\text{Comp}}, CSA applies the DSA strategy to select top-k compressed KV entries for core attention."
- Score (Eq. 16): "Next, the index score It,s∈ℝI_{t,s}\in\mathbb{R} between the query token tt and a preceding compressed block ss (ss < Floor⁡(tm)\operatorname{Floor}(\frac{t}{m})) is computed by ... It,s\displaystyle I_{t,s} =∑h=1nhIwt,hI⋅ReLU​(𝐪t,hI⋅KsIComp),\displaystyle=\sum_{h=1}^{n_{h}^{I}}w_{t,h}^{I}\cdot\text{ReLU}\left(\mathbf{q}^{I}_{t,h}\cdot K^{\text{IComp}}_{s}\right),"
- Selection (Eq. 17): "For a query token tt, given its index scores It,:I_{t,:}, we employ a top-k selector to selectively retain a subset of compressed KV entries 𝒞tSprsComp\mathcal{C}^{\text{SprsComp}}_{t} for subsequent core attention: ... 𝒞tSprsComp={CsComp|It,s∈Top−k(It,:)}.\mathcal{C}^{\text{SprsComp}}_{t}=\left\{C^{\text{Comp}}_{s}\penalty\ \Big|\penalty\ I_{t,s}\in\operatorname{Top-k}(I_{t,:})\right\}."

Resolution (k): 512 selected compressed entries for Flash, 1024 for Pro (Section 4.2.1 quotes above). The top-k set is per query token (all query heads of the token attend to the same selected set — consistent with "where each query token attends to only kk compressed KV entries", Section 2.3).

## 3. HCA structure (Q4)

- Section 2.3.2: "The core architecture of HCA is illustrated in Figure 4, which compresses the KV cache in a heavier manner, but does not employ sparse attention."
- Section 2.3.2: "By and large, the compression strategy of HCA is similar to that of CSA, but employs a larger compression rate m′m^{\prime} (≫m\gg m) and does not perform overlapped compression."
- Section 2.3.2: "Through this compression operation, HCA compresses the sequence length to 1m′\frac{1}{m^{\prime}} times."
- Rate value (Section 4.2.1, identical in Flash and Pro blocks): "For HCA, we set the compression rate m′m^{\prime} to 128."
- No routing at all: no indexer, no top-k; dense attention over all n/m′ compressed entries (Section 2.3.2, "does not employ sparse attention"; Eq. 26 applies CoreAttn to the full CCompC^{\text{Comp}}).

Differences from CSA:

| Axis | CSA | HCA |
|---|---|---|
| Compression rate | 1/4 (m=4) | 1/128 (m′=128) |
| Compression scheme | two overlapped streams (2m source entries per compressed entry) | single stream, non-overlapped ("does not perform overlapped compression", Section 2.3.2) |
| Routing / selection | per-token top-k (k=512/1024) sparse selection via Lightning Indexer | none — dense attention over all compressed entries |
| Layer placement | interleaved with HCA after the first two layers (both models, Section 4.2.1) | Pro: "For the first two layers, we use HCA." / Flash: "For the first two layers, we use pure sliding window attention." (Section 4.2.1) |

## 4. The decoupling question (Q3)

DECOUPLING: PARTIAL

Evidence: the design exposes two SEPARATE named knobs — a content-compression rate (*m* for CSA, *m′* for HCA) and a routing/selection budget (*k*, "attention top-k") — and the model configs set them independently (Flash: m=4, k=512; Pro: m=4, k=1024; both: m′=128; Section 4.2.1). Architecturally the knobs are decoupled. However, NO experiment in the accessible text varies either knob independently: there is no table, figure, or paragraph reporting a sweep of *m* with *k* fixed, a sweep of *k* with *m* fixed, or any factorial grid. The word "ablation" does not occur in the accessible text (verified by search). The only places *m* or *k* appear in an experimental context are: (a) the training schedule — "we first warmup the model with dense attention for the first 1T tokens, and introduce sparse attention at the sequence length of 64K and keep sparse attention during the rest of the training." (Section 4.2.2, Flash training setup); (b) the difference between the two model variants (Flash top-k=512 vs Pro top-k=1024, Section 4.2.1) — different model scales with different benchmark tables, not a controlled ablation on a fixed task; (c) "Third, relative to DeepSeek-V3.2, a smaller attention top-k is chosen in DeepSeek-V4 series, thereby improving model efficiency on short- and medium-length texts." (Section 2.3.4) — a between-model claim, with no measured numbers in the accessible text. Hence: both knobs exposed (YES), independent experimental variation (NOT FOUND).

## 5. Ablation inventory (Q3/Q5)

The accessible text contains exactly 14 numbered tables. NONE of them varies compression ratio or selection count; all are model-vs-model or mode-vs-mode comparisons. Captions / descriptions verbatim:

| Table # | What is varied | Values | Benchmark | Isolates which axis? |
|---|---|---|---|---|
| 1 | Base-model comparison DeepSeek-V3.2 / V4-Flash / V4-Pro ("In Table 1, we provide a detailed comparison of the base models ...") | — | "all evaluated under a unified internal framework with strictly consistent settings" | None — whole models |
| 2 | "Comparison of three reasoning modes" | — | (per Table 2 caption) | None |
| 3 | "Instruction injected into the system prompt for the \"Think Max\" mode." | — | — | None |
| 4 | "Tool-call schema for DeepSeek-V4 series." | — | — | None |
| 5 | "Quick Instruction special tokens for auxiliary tasks." | — | — | None |
| 6 | Model comparison: "The comparison of DeepSeek-V4-Pro-Max and other closed/open source models is presented in Table 6." | — | public benchmarks | None — whole models |
| 7 | Reasoning modes: "we evaluate different modes of DeepSeek-V4-Flash and DeepSeek-V4-Pro and show the results in Table 7." | — | public benchmarks | None |
| 8 | "Comparison on R&D Coding Benchmark (external models included strictly for evaluation purposes)." | — | R&D Coding Benchmark | None |
| 9 | "Agentic Search vs. Retrieval Augmented Search for DeepSeek-V4-Pro." | — | search tasks | None |
| 10 | "Cost Comparison:Agentic Search vs. Retrieval Augmented Search (Mean) for DeepSeek-V4-Pro. Most of the tool calls are parallel for Agentic Search." | — | search tasks | None |
| 11 | "Comparative Evaluation of DeepSeek-V4-Pro and DeepSeek-V3.2 on Search Q&A Tasks." | — | search Q&A | None |
| 12 | "Comparative Analysis of DeepSeek-V4-Pro and Gemini-3.1-Pro in Chinese Functional Writing." | — | functional writing | None |
| 13 | Creative writing comparison: "Table 13 presents the creative writing comparison, which is evaluated along two axes: instruction following and writing quality." | — | creative writing | None |
| 14 | "DeepSeek-V4-Pro vs. Claude-Opus-4.5 on Complex Instruction Following and Multi-Turn Writing." | — | instruction following / writing | None |

Q5 — separate main effects: NOT FOUND in accessible text. No table reports the effect of varying ONLY the compression rate, or ONLY the selection budget, on the same benchmark. There is no single-axis or factorial ablation of *m* × *k* anywhere in the accessible text.

## 6. Abstract-claims verification (Q6)

Abstract claim (Abstract): "In the one-million-token context setting, DeepSeek-V4-Pro requires only 27% of single-token inference FLOPs and 10% of KV cache compared with DeepSeek-V3.2."

VERIFIED in the body (not just the abstract): Section 2.1 "Designs Inherited from DeepSeek-V3" (the right-panel-of-Figure-1 discussion):

- "The right part of Figure 1 demonstrates the estimated single-token inference FLOPs and accumulated KV cache size of DeepSeek-V3.2 and DeepSeek-V4 series."
- "In the scenario of 1M-token context, even DeepSeek-V4-Pro, which has a larger number of activated parameters, attains only 27% of the single-token FLOPs (measured in equivalent FP8 FLOPs) and 10% of the KV cache size relative to DeepSeek-V3.2."
- Companion figure: "Right: inference FLOPs and KV cache size of DeepSeek-V4 series and DeepSeek-V3.2." (Figure 1 caption)

Configuration: 1M-token context, DeepSeek-V4-Pro vs DeepSeek-V3.2, FLOPs "measured in equivalent FP8 FLOPs". The underlying data is a figure (Figure 1, right) — the numbers are "estimated" (per the body wording above), not a measured table. Companion claim for the smaller model (same section): "Furthermore, DeepSeek-V4-Flash, with its smaller number of activated parameters, pushes efficiency even further: in the 1M-token context setting, it achieves only 10% of the single-token FLOPs and 7% of the KV cache size compared with DeepSeek-V3.2."

## 7. Framing language (Q7)

- Section 2.3: "For DeepSeek-V4, we design two efficient attention architectures — Compressed Sparse Attention (CSA) and Heavily Compressed Attention (HCA) — and employ their interleaved hybrid configuration, which substantially reduces the computational cost of attention in long-text scenarios."
- Section 2.3: "CSA integrates both compression and sparse attention strategies: it first compresses the Key-Value (KV) cache of every mm tokens into one entry, and then applies DeepSeek Sparse Attention (DSA) (26) where each query token attends to only kk compressed KV entries."
- Section 2.3.4 ("Efficiency Discussion"): "Due to the employment of hybrid CSA and HCA, together with low-precision computation and storage, the attention module of DeepSeek-V4 series achieves remarkable efficiency in both attention FLOPs and KV cache size, especially in long-context scenarios."
- Section 2.3.4: "Finally, and most importantly, compressed attention and hybrid attention techniques substantially reduce both the KV cache size and the computational FLOPs."
- Section 2.3.4: "Taking BF16 GQA8 (5) with a head dimension of 128 as the baseline — one of the common configurations of LLM attention — the KV cache size of DeepSeek-V4 series can be dramatically reduced to approximately 2%2\% times of that baseline in the 1M-context setting."
- Explicit "design space" / "trade-off" / "compression × routing" framing: NOT FOUND in accessible text (searched the extraction for "trade-off", "tradeoff", "design space": no hits). The paper frames CSA/HCA as efficiency techniques, not as points in an explored design space.

## 8. C2 verdict

C2: RELATED — both mechanisms are present (content-compression rate *m*/*m′* and routing resolution top-*k* *k* as separate named hyperparameters, Section 4.2.1), but the paper never varies them independently: no ablation changes *m* with *k* fixed or *k* with *m* fixed, and no table reports a separate main effect of either knob on a fixed task (all 14 tables are model/mode comparisons).
