# Gate 20 — component-accounting recheck

Generated 2026-10-16T12:09:39Z · no training runs.

## Shape audit (executed module, L=256)

| cell | index tokens | cols scored (excl. sink) | router MACs/seq (measured) | corrected analytic | superseded charge |
|---|---|---|---|---|---|
| (4,4) | 64 | 80 | 2,097,152 | 2,097,152 | 524,288 |
| (8,4) | 64 | 48 | 2,097,152 | 2,097,152 | 524,288 |
| (4,8) | 32 | 80 | 1,048,576 | 1,048,576 | 262,144 |
| (8,8) | 32 | 48 | 1,048,576 | 1,048,576 | 262,144 |
| (16,4) | 64 | 32 | 2,097,152 | 2,097,152 | 524,288 |
| (32,4) | 64 | 24 | 2,097,152 | 2,097,152 | 524,288 |

## Corrected component accounts at L=256 (MACs/seq)

| component | Normal | CSA (4,4) | DRRA (8,4) |
|---|---|---|---|
| wrapper | 33,869,824 | 33,869,824 | 33,869,824 |
| q_lora | 4,194,304 | 4,194,304 | 4,194,304 |
| kv | 1,048,576 | 1,048,576 | 1,048,576 |
| attn | 16,777,216 | 5,308,416 | 3,211,264 |
| router | --- | 2,097,152 | 2,097,152 |
| compress | --- | 6,291,456 | 6,291,456 |
| o_proj | 20,971,520 | 10,485,760 | 10,485,760 |
| **total** | **76,861,440** | **63,295,488** | **61,198,336** |

Superseded totals: CSA 61,722,624, DRRA 59,625,472 (released gate5 values).

## Derived numbers

```
{
 "generated_utc": "2026-10-16T12:09:39Z",
 "why": "Q1 review R8: verify the router term against tensor shapes. Executed router = H*d_head = d MACs per (query, index-token) pair; the superseded charge counted one head.",
 "geometry": {
  "H": 4,
  "d_head": 32,
  "d": 128,
  "W": 16,
  "L0": 256
 },
 "attention_path_savings_pct": {
  "contexts": [
   256,
   1024,
   4096,
   8192,
   32768,
   131072
  ],
  "cells": {
   "(4,4)": [
    18.4,
    51.5,
    59.7,
    61.1,
    62.2,
    62.4
   ],
   "(8,4)": [
    30.9,
    64.0,
    72.2,
    73.6,
    74.7,
    74.9
   ],
   "(16,4)": [
    37.1,
    70.2,
    78.5,
    79.9,
    80.9,
    81.2
   ],
   "(32,4)": [
    40.2,
    73.3,
    81.6,
    83.0,
    84.0,
    84.3
   ]
  },
  "asymptote": {
   "(4,4)": 62.5,
   "(8,4)": 75.0,
   "(16,4)": 81.2,
   "(32,4)": 84.4
  }
 },
 "whole_layer_savings_pct_L32768": {
  "d128": {
   "DRRA": 72.9,
   "(32,4)": 82.1
  },
  "d512": {
   "DRRA": 68.3,
   "(32,4)": 76.8
  },
  "d1024": {
   "DRRA": 62.9,
   "(32,4)": 70.8
  },
  "d4096": {
   "DRRA": 42.7,
   "(32,4)": 48.0
  }
 },
 "whole_layer_savings_pct_d128": {
  "L2048": 50.5,
  "L4096": 60.8,
  "L32768": 72.9
 },
 "whole_layer_savings_pct_L2048_d128_CSA": 41.4,
 "sensitivity_L32768_DRRA_aux_weight": {
  "x0.5": 81.1,
  "x1.0": 74.7,
  "x2.0": 61.9
 },
 "sensitivity_single_head_indexer": {
  "as_executed_DRRA": 75.0,
  "single_head_indexer_DRRA": 84.0
 },
 "whole_model_saving_pct": {
  "DRRA_vs_Normal": 20.4,
  "CSA_vs_Normal": 17.6,
  "DRRA_projection_matched": 7.8,
  "projection_share_of_gap_pct": 66.9,
  "attention_path_DRRA_vs_Normal": 30.9,
  "attention_core_DRRA_vs_Normal": 80.9,
  "attention_path_frozen_split_DRRA": {
   "core": 3211264,
   "router": 2097152,
   "compressors": 6291456
  }
 },
 "energy_composition_L2048_pct_of_dense_per_token": {
  "dense_core": 72.7,
  "CSA": {
   "core": 18.8,
   "router_compress": 12.5
  },
  "DRRA": {
   "core": 9.7,
   "router_compress": 12.5
  },
  "fixed_block": 27.3,
  "attention_path_saving": {
   "CSA": 57.0,
   "DRRA": 69.5
  },
  "whole_model_saving": {
   "CSA": 41.4,
   "DRRA": 50.5
  }
 },
 "validation": {
  "batch1": {
   "spearman_latency_vs_work": 0.992,
   "n_points": 18,
   "pearson_work_ratio_vs_time_ratio": 0.891,
   "n_ratios": 6
  },
  "batch32": {
   "spearman_latency_vs_work": 1.0,
   "n_points": 15,
   "pearson_work_ratio_vs_time_ratio": 0.96,
   "n_ratios": 5
  }
 }
}
```
