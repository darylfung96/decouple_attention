# Gate 5 — Systems Benchmark Summary (development machine, 2026-08-27)

**Scope:** everything measurable on the single available machine (Apple M2).
Cross-hardware (Linux x86 / GPU) and model depth/width sweeps are **out of
scope here** (no second machine; separate ablation). All measurements are
from `gate5_bench.py` → `gate5_results.json`, `gate3_latency.json`,
`gate3_latency_scale.json`, plus training times parsed from `gate3_sweep.log`.
Frozen protocol unless noted: L=256, H=96, F=7, batch 32, fp32, 8 threads.

## 1. Machine

Apple M2 (Mac14,2), 8 cores (4P+4E), 16 GB RAM, macOS 14.6, arm64;
PyTorch 2.6.0 (CPU build), 8 intra-op threads.

## 2. Latency (forward, batch 32; Table 5 in the paper)

| Model | Mean (ms) | 95% CI | p90 | p99 | Throughput |
|---|---|---|---|---|---|
| Normal | 52.5 | [50.4, 54.7] | 59.4 | 65.0 | 19.1 b/s |
| (4,4) | 52.1 | [49.2, 55.4] | 63.5 | 71.5 | 19.2 b/s |
| (8,4) | 49.3 | [47.2, 51.7] | 56.5 | 65.9 | 20.3 b/s |

Alternating head-to-head protocol (25 rounds × 30 passes). CIs overlap;
ordering replicated across runs → directional only.

## 3. Batch scaling (B = 1…256; Figure 4)

Batch 1: Normal fastest (2.5 ms/seq; DRRA +30.8% — fixed overheads).
Batch ≥ 8: (8,4) at or below Normal; at B=256: (8,4) −21.1% vs Normal
(3.49 vs 4.42 ms/seq). Mid-range (16–32): within run-to-run noise.

## 4. Sequence-length scaling (L = 128…4096; batch 1 and 32)

Mean ms/batch (batch 32): L=128: 25.3/27.4/22.3 (N/F/D — Normal fastest);
L=512: 197.3/171.6/148.6; L=2048: 2151.8/1270.3/986.5 — i.e., at L=2048
(8,4) is **2.2× faster than Normal**. Batch 1, L=4096: 235.1/107.0/86.2 ms
(2.7× vs Normal). (8,4) at B=32/L=4096 is skipped: the dense score tensor
(~8 GB) exceeds practical RAM — reported as a finding (full attention's
memory wall; the compressed cells would fit but are skipped for a fair
same-shape comparison).

**Empirical log-log slopes** (L ≥ 512): batch 1 — Normal 1.69, (4,4) 1.33,
(8,4) 1.24; batch 32 — Normal 1.72, (4,4) 1.42, (8,4) 1.40. Consistent with
the complexity analysis: asymptotically all cells are O(L²) with a reduced
constant (router O(L²/c_R)); Normal approaches the quadratic slope fastest.
**No subquadratic claim is made.**

## 5. Analytic MACs (forward, per sequence, L=256; dominant terms)

| Component | Normal | (4,4) | (8,4) |
|---|---|---|---|
| Wrapper (input proj + MLP + head) | 33.87M | 33.87M | 33.87M |
| Q (LoRA a+b) | 4.19M | 4.19M | 4.19M |
| KV proj (tied) | 1.05M | 1.05M | 1.05M |
| Attention (scores+values) | 16.78M | 4.42M | 3.21M |
| Router | — | 0.52M | 0.52M |
| Compressors | — | 6.29M | 6.29M |
| O projection | 20.97M | 10.49M | 10.49M |
| **Total** | **76.86M** | **61.72M** | **59.63M** |

(8,4) needs 22% fewer forward MACs than Normal. Note the wrapper MLP
(33.87M) is the single largest block for every model — attention is not the
dominant compute at this scale, which is why the 5.3× column reduction does
not translate into proportional latency gains. (norms/RoPE/masks excluded;
documented formulas in gate5_bench.py.)

## 6. Memory (batch 32 forward burst)

Cumulative peak-RSS watermark: +299 MB (process max; per-model attribution
is limited by the monotonic max — Normal's burst added the largest
increment, +67 MB after (8,4)'s +299 MB watermark was set). Parameter
memory ≈ 1.4 MB per model. Activation memory at batch 32 is tens of MB;
at L=4096/B=32 the full-attention score tensor alone would be ~8 GB
(Section 4) — the practical memory wall for dense attention.

## 7. Training time (ETTh1, 10 epochs, from the Gate-3 sweep)

| Model | Median | Mean | Runs |
|---|---|---|---|
| Normal | 474 s | 491.2 s | 5 |
| (4,4) | 511 s | 480.8 s | 5 |
| (8,4) | 459 s | 651.6 s | 5 |

DRRA's mean includes one contaminated run (1417 s — machine-sleep window);
medians are the robust statistic and are within ~11% of each other.
Time-to-quality: all variants reach their best validation MSE by epoch ~7
(fixed 10-epoch budget; no early stopping used).

## 8. Reading (H2 relevance)

The latency leg of H2 (dual-rate Pareto advantage at comparable latency) is
now supported directionally: (8,4) has fewer MACs (−22% vs Normal), lower
or equal mean latency from batch 8 / L ≥ 512 onward, and the gap widens
with batch and sequence length — while matching the equal-rate cell's
routing granularity. Per-dataset accuracy wins remain descriptive
(Gate 4: nothing survives correction at n=5). Combined score (Table 6):
(8,4) 1.099 / 1.199 (B=32 / B=256) vs (4,4) 1.064 / 1.043.
