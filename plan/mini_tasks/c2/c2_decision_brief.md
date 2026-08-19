# C2 Decision Brief — may the "to our knowledge" phrasing stand?

**Date:** 2026-08-16 · **Status:** FINAL — evidence complete, recommendation ready, awaiting user sign-off

**Claim under test** (paper `related_work.tex:23-30`): *"none of these works, to our knowledge, systematically varies the content-compression rate and the routing resolution independently and reports their separate main effects on a fixed task."*

**Rubric:** COUNTER iff (1) both knobs exist, (2) varied independently, (3) separate main effects on a fixed task.

## 1. Verdict counts (sweep log: 29 assessed rows; screen stats)

**COUNTER = 0 · RELATED = 26 · IRRELEVANT = 3**

Coverage: 10 arXiv keyword sweeps (742 unique papers, 2024-01-01..2026-08-31) → 189 screened → 15 methods-level first-hand reads; 7 seed papers; 300 citation-chase rows; 4 targeted web searches. Full evidence in `c2_sweep_log.md`, `dsv4_csa_read.md`, `nsa_read.md`, `c2_sweep_cache/citation_chase.md`.

## 2. The four closest works (all RELATED, with the precise contrast)

| Work | Both knobs? | Why it does NOT counter C2 |
|---|---|---|
| **SSA / Gist Tokens** (2604.20920) | yes (chunk size L, top-k k) | k derived from L: k = ⌊n_kv/(L_eff·G·L)⌋+1 (Eq. A.1) — "ensuring that the total number of unfolded tokens remains approximately proportional to n_kv regardless of the compression ratio". Knobs coupled by construction; routing axis never isolated. |
| **The Sparse Frontier** (2504.17768) | no — selection only | 7065 configurations but ALL vary one axis (selection budget 0–0.95) across 6 training-free methods; no content-compression knob exists (block size fixed 16×16). |
| **DeepSeek-V4 CSA/HCA** (2606.19348) | yes, structurally | m=4, k=512/1024, m'=128 are fixed per-model hyperparameters (§4.2.1); the word "ablation" never occurs in the report; all 14 tables are model/mode comparisons. |
| **NSA** (2502.11089) | yes, structurally | one fixed configuration (l=32, d=16, l'=64, n=16, w=512); baselines sparsity-equalized instead of knob sweeps. |

## 3. Structural observation (shapes wording regardless of branch)

DS-V4's CSA is **the same two-axis family as ours** (compression rate × top-k over compressed entries, two-series overlapped softmax, sliding window, attention sink — see `dsv4_csa_read.md`). The claim is safe only because DS-V4 *sets* rather than *varies* its knobs; any reviewer aware of CSA will see the family resemblance, so the KEEP-branch wording must state the DS-V4 contrast explicitly (it does, below).

## 4. Recommendation: KEEP, with the closest-works contrast + 2 new citations

The phrasing is supported by the sweep. Recommended replacement for `related_work.tex` lines 22–30 (draft — final wording at sign-off):

```latex
Crucially for our claim (b), none of these works, to our knowledge,
\emph{systematically varies the content-compression rate and the routing
resolution independently and reports their separate main effects} on a
fixed task. The closest are Simplified Sparse Attention
\citep{mao2026ssa}, which compresses context into gist tokens and
selectively unfolds top-$k$ chunks but derives $k$ from the chunk size to
hold the total budget constant (Eq.~A.1), coupling the two axes; and The
Sparse Frontier \citep{nawrot2025sparsefrontier}, which sweeps selection
budgets across six methods with no content-compression knob.
DeepSeek-V4 \citep{deepseekv4_2026} and NSA \citep{yuan2025nsa} expose
both mechanisms as fixed hyperparameters without varying them
independently. We confirmed this on a systematic sweep of the 2024--2026
routing/compression-attention literature (August 2026).
```

Plus: `references.bib` gains `mao2026ssa` (2604.20920, verified) and `nawrot2025sparsefrontier` (2504.17768, verified); the `deepseekv4_2026` note drops "not read in depth" and records the read.

## 5. Fallback branches (available if you prefer a narrower posture)

- **NARROW:** restrict the claim to TS forecasting ("none of these works, to our knowledge, does so on a fixed time-series forecasting task") — defensible but weaker, and the sweep found no TS-domain counterexample either, so it buys nothing.
- **DROP:** remove the epistemic clause entirely and let the measured factorial speak — the most conservative posture; loses a legitimate (now evidence-backed) contribution element.

## 6. User decision

Branch: **KEEP (recommended)** — decided 2026-08-16 by user (ask_user_question). Applied to `related_work.tex`, `references.bib`, `README.md`; ledgers updated in `paper_notes.md` and `lit_audit.md`.
