# Gate 3 — Dataset-Coverage Summary

3-way comparison (Normal / Flat=(4,4) / DRRA=(8,4)) × 5 paired seeds {42,123,2024,7,99} on 12 datasets under the frozen direct-96 task (L=256, H=96, train-only z-score, pooled MSE, standardized units). Descriptive statistics only; significance testing is Gate 4.

## Overview — models × datasets (transposed)

Validation MSE per dataset, mean ± std over 5 paired seeds (lower is better). Bold: best value in its dataset column (val rows among val rows, test rows among test rows).

| Model | ETTh1 | ETTh2 | ETTm1 | ETTm2 | Electricity | Traffic | Weather | Exchange | Solar | syn-sinusoids | syn-changepts | syn-delayedcopy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Normal val | 0.8416 ± 0.0799 | 1.9187 ± 0.6246 | 0.4285 ± 0.0187 | 1.5618 ± 0.6006 | 0.4047 ± 0.0310 | 0.5994 ± 0.0090 | 0.4460 ± 0.0121 | **2.9800 ± 0.1417** | 0.1899 ± 0.0054 | **0.1227 ± 0.0008** | **5.9456 ± 0.0706** | **0.2888 ± 0.0001** |
| Flat val | 0.6332 ± 0.0611 | **1.3624 ± 0.3341** | 0.3965 ± 0.0110 | 0.9964 ± 0.0753 | **0.3798 ± 0.0097** | **0.5838 ± 0.0097** | 0.4469 ± 0.0094 | 3.1166 ± 0.2802 | **0.1721 ± 0.0052** | 0.1264 ± 0.0008 | 5.9677 ± 0.0844 | 0.2894 ± 0.0002 |
| DRRA val | **0.5967 ± 0.0710** | 1.8080 ± 0.6832 | **0.3832 ± 0.0236** | **0.8053 ± 0.1929** | 0.3808 ± 0.0130 | 0.5874 ± 0.0098 | **0.4424 ± 0.0063** | 3.2350 ± 0.5234 | 0.1722 ± 0.0110 | 0.1264 ± 0.0015 | 6.0013 ± 0.0848 | 0.2894 ± 0.0003 |
| Δval (4,4) vs Normal | -24.77% | -28.99% | -7.46% | -36.20% | -6.17% | -2.61% | +0.20% | +4.58% | -9.35% | +3.04% | +0.37% | +0.20% |
| Δval (8,4) vs Normal | -29.10% | -5.77% | -10.58% | -48.44% | -5.92% | -2.01% | -0.80% | +8.56% | -9.29% | +3.05% | +0.94% | +0.21% |
| Normal test | 1.0814 ± 0.1106 | 0.4783 ± 0.1128 | 0.6853 ± 0.0401 | 0.3114 ± 0.0634 | 0.4048 ± 0.0098 | 0.8287 ± 0.0076 | **0.1683 ± 0.0038** | 2.1510 ± 0.0674 | 0.2160 ± 0.0048 | **0.1239 ± 0.0007** | **11.9788 ± 0.1556** | **0.3005 ± 0.0001** |
| Flat test | 0.9079 ± 0.0557 | **0.3607 ± 0.0872** | 0.6112 ± 0.0123 | 0.2969 ± 0.0452 | **0.3813 ± 0.0098** | 0.8119 ± 0.0073 | 0.1923 ± 0.0054 | 2.0490 ± 0.1050 | 0.2199 ± 0.0088 | 0.1276 ± 0.0008 | 12.0199 ± 0.1009 | 0.3011 ± 0.0002 |
| DRRA test | **0.7988 ± 0.0506** | 0.3900 ± 0.0991 | **0.6002 ± 0.0382** | **0.2591 ± 0.0103** | 0.3887 ± 0.0095 | **0.8074 ± 0.0111** | 0.1783 ± 0.0035 | **1.9900 ± 0.1273** | **0.1951 ± 0.0121** | 0.1277 ± 0.0014 | 12.0560 ± 0.1162 | 0.3011 ± 0.0002 |
| Δtest (4,4) vs Normal | -16.04% | -24.59% | -10.81% | -4.65% | -5.81% | -2.04% | +14.21% | -4.74% | +1.82% | +2.95% | +0.34% | +0.19% |
| Δtest (8,4) vs Normal | -26.13% | -18.46% | -12.41% | -16.78% | -3.98% | -2.57% | +5.89% | -7.48% | -9.65% | +3.01% | +0.64% | +0.19% |

## Integrity audit

### etth1 — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 0.8416 ± 0.0799 | 1.0814 ± 0.1106 | — | — |
| Flat (4,4) | 0.6332 ± 0.0611 | 0.9079 ± 0.0557 | -24.77% | -16.04% |
| DRRA (8,4) | 0.5967 ± 0.0710 | 0.7988 ± 0.0506 | -29.10% | -26.13% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | -0.2623 / -0.1835 / -0.2555 / -0.1745 / -0.1664 | 5/5 |
| DRRA | -0.4108 / -0.2375 / -0.2444 / -0.2476 / -0.0843 | 5/5 |

### etth2 — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 1.9187 ± 0.6246 | 0.4783 ± 0.1128 | — | — |
| Flat (4,4) | 1.3624 ± 0.3341 | 0.3607 ± 0.0872 | -28.99% | -24.59% |
| DRRA (8,4) | 1.8080 ± 0.6832 | 0.3900 ± 0.0991 | -5.77% | -18.46% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | -0.6133 / -0.8239 / +0.3152 / -1.5135 / -0.1460 | 4/5 |
| DRRA | -0.1540 / +0.0882 / +0.4871 / -0.1525 / -0.8220 | 3/5 |

### ettm1 — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 0.4285 ± 0.0187 | 0.6853 ± 0.0401 | — | — |
| Flat (4,4) | 0.3965 ± 0.0110 | 0.6112 ± 0.0123 | -7.46% | -10.81% |
| DRRA (8,4) | 0.3832 ± 0.0236 | 0.6002 ± 0.0382 | -10.58% | -12.41% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | -0.0120 / -0.0317 / -0.0529 / -0.0583 / -0.0048 | 5/5 |
| DRRA | -0.0303 / -0.0823 / -0.0430 / -0.0767 / +0.0058 | 4/5 |

### ettm2 — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 1.5618 ± 0.6006 | 0.3114 ± 0.0634 | — | — |
| Flat (4,4) | 0.9964 ± 0.0753 | 0.2969 ± 0.0452 | -36.20% | -4.65% |
| DRRA (8,4) | 0.8053 ± 0.1929 | 0.2591 ± 0.0103 | -48.44% | -16.78% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | -1.0909 / -1.0630 / +0.3581 / -0.8755 / -0.1558 | 4/5 |
| DRRA | -1.0407 / -1.1714 / +0.1517 / -1.3046 / -0.4177 | 4/5 |

### electricity — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 0.4047 ± 0.0310 | 0.4048 ± 0.0098 | — | — |
| Flat (4,4) | 0.3798 ± 0.0097 | 0.3813 ± 0.0098 | -6.17% | -5.81% |
| DRRA (8,4) | 0.3808 ± 0.0130 | 0.3887 ± 0.0095 | -5.92% | -3.98% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | -0.0030 / -0.0204 / -0.0063 / -0.0692 / -0.0260 | 5/5 |
| DRRA | +0.0048 / -0.0340 / -0.0040 / -0.0658 / -0.0209 | 4/5 |

### traffic — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 0.5994 ± 0.0090 | 0.8287 ± 0.0076 | — | — |
| Flat (4,4) | 0.5838 ± 0.0097 | 0.8119 ± 0.0073 | -2.61% | -2.04% |
| DRRA (8,4) | 0.5874 ± 0.0098 | 0.8074 ± 0.0111 | -2.01% | -2.57% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | -0.0308 / -0.0217 / -0.0213 / +0.0082 / -0.0126 | 4/5 |
| DRRA | -0.0289 / +0.0070 / -0.0114 / -0.0139 / -0.0132 | 4/5 |

### weather — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 0.4460 ± 0.0121 | 0.1683 ± 0.0038 | — | — |
| Flat (4,4) | 0.4469 ± 0.0094 | 0.1923 ± 0.0054 | +0.20% | +14.21% |
| DRRA (8,4) | 0.4424 ± 0.0063 | 0.1783 ± 0.0035 | -0.80% | +5.89% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | +0.0072 / +0.0061 / -0.0340 / +0.0211 / +0.0042 | 1/5 |
| DRRA | -0.0066 / +0.0040 / -0.0263 / +0.0179 / -0.0069 | 3/5 |

### exchange — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 2.9800 ± 0.1417 | 2.1510 ± 0.0674 | — | — |
| Flat (4,4) | 3.1166 ± 0.2802 | 2.0490 ± 0.1050 | +4.58% | -4.74% |
| DRRA (8,4) | 3.2350 ± 0.5234 | 1.9900 ± 0.1273 | +8.56% | -7.48% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | +0.5611 / +0.0641 / +0.3499 / +0.2523 / -0.5445 | 1/5 |
| DRRA | +0.8893 / -0.0341 / +0.9407 / +0.0699 / -0.5907 | 2/5 |

### solar — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 0.1899 ± 0.0054 | 0.2160 ± 0.0048 | — | — |
| Flat (4,4) | 0.1721 ± 0.0052 | 0.2199 ± 0.0088 | -9.35% | +1.82% |
| DRRA (8,4) | 0.1722 ± 0.0110 | 0.1951 ± 0.0121 | -9.29% | -9.65% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | -0.0140 / -0.0296 / -0.0022 / -0.0180 / -0.0249 | 5/5 |
| DRRA | -0.0168 / -0.0126 / -0.0259 / -0.0207 / -0.0122 | 5/5 |

### syn_sinusoids — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 0.1227 ± 0.0008 | 0.1239 ± 0.0007 | — | — |
| Flat (4,4) | 0.1264 ± 0.0008 | 0.1276 ± 0.0008 | +3.04% | +2.95% |
| DRRA (8,4) | 0.1264 ± 0.0015 | 0.1277 ± 0.0014 | +3.05% | +3.01% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | +0.0040 / +0.0035 / +0.0040 / +0.0036 / +0.0036 | 0/5 |
| DRRA | +0.0050 / +0.0021 / +0.0041 / +0.0028 / +0.0046 | 0/5 |

### syn_changepoints — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 5.9456 ± 0.0706 | 11.9788 ± 0.1556 | — | — |
| Flat (4,4) | 5.9677 ± 0.0844 | 12.0199 ± 0.1009 | +0.37% | +0.34% |
| DRRA (8,4) | 6.0013 ± 0.0848 | 12.0560 ± 0.1162 | +0.94% | +0.64% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | -0.0056 / +0.0467 / -0.0054 / +0.0374 / +0.0370 | 2/5 |
| DRRA | -0.0238 / +0.0131 / +0.0371 / +0.1185 / +0.1333 | 1/5 |

### syn_delayedcopy — PASS

| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |
|---|---|---|---|---|
| Normal | 0.2888 ± 0.0001 | 0.3005 ± 0.0001 | — | — |
| Flat (4,4) | 0.2894 ± 0.0002 | 0.3011 ± 0.0002 | +0.20% | +0.19% |
| DRRA (8,4) | 0.2894 ± 0.0003 | 0.3011 ± 0.0002 | +0.21% | +0.19% |

Paired per-seed val deltas vs Normal (negative = variant beats Normal):

| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |
|---|---|---|
| Flat | +0.0010 / +0.0007 / +0.0005 / +0.0003 / +0.0004 | 0/5 |
| DRRA | +0.0009 / +0.0006 / +0.0008 / +0.0003 / +0.0003 | 0/5 |

## Cross-dataset headline

- Datasets where DRRA (8,4) mean val < Normal: **8/12**
- Datasets where Flat (4,4) mean val < Normal: **7/12**
- Datasets with a complete 15/15 row set: **12/12**
