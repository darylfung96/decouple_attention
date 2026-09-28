# A-2 canonical latency + B1-2 unique blocks

Env: `{'python': '3.11.12', 'torch': '2.6.0'}` | gate: **PASS**

| config | seed | maxdiff LASTvsFULL | pass | sel(a)==sel(b) |
|---|---|---|---|---|
| Normal | 0 | 5.96e-07 | True | n/a |
| Normal | 42 | 7.15e-07 | True | n/a |
| Normal | 123 | 5.96e-07 | True | n/a |
| CSA_4_4 | 0 | 3.87e-07 | True | True |
| CSA_4_4 | 42 | 4.77e-07 | True | True |
| CSA_4_4 | 123 | 4.77e-07 | True | True |
| DRRA_8_4 | 0 | 7.15e-07 | True | True |
| DRRA_8_4 | 42 | 4.77e-07 | True | True |
| DRRA_8_4 | 123 | 4.77e-07 | True | True |

## Canonical latency (25 rounds x 30, B=32, round-robin alternating)

- Normal_FULL: `{'mean_ms': 40.73177883354947, 'stdev_ms': 4.567668206016624, 'rounds': 25, 'passes': 30}`
- CSA_4_4_FULL: `{'mean_ms': 36.960139166253306, 'stdev_ms': 1.6881525790053449, 'rounds': 25, 'passes': 30}`
- DRRA_8_4_FULL: `{'mean_ms': 31.74136805254966, 'stdev_ms': 1.4547356277504206, 'rounds': 25, 'passes': 30}`
- Normal_LAST: `{'mean_ms': 2.62121399724856, 'stdev_ms': 0.19870098844339196, 'rounds': 25, 'passes': 30}`
- CSA_4_4_LAST: `{'mean_ms': 6.176206107717007, 'stdev_ms': 0.21474781164672782, 'rounds': 25, 'passes': 30}`
- DRRA_8_4_LAST: `{'mean_ms': 5.82336900010705, 'stdev_ms': 0.2493685580023224, 'rounds': 25, 'passes': 30}`
- Normal_paired_LAST_minus_FULL: `{'mean_ms': -38.11056483630091, 'stdev_ms': 4.5889003500536925, 'ci95': 1.7988489372210474}`
- CSA_4_4_paired_LAST_minus_FULL: `{'mean_ms': -30.783933058536302, 'stdev_ms': 1.6663043275189426, 'ci95': 0.6531912963874256}`
- DRRA_8_4_paired_LAST_minus_FULL: `{'mean_ms': -25.91799905244261, 'stdev_ms': 1.4878284624042448, 'ci95': 0.5832287572624639}`
- paired_FULL_DRRA_8_4_minus_Normal: `{'mean_ms': -8.99041078099981, 'stdev_ms': 4.384093801506386, 'ci95': 1.7185647701905034}`
- paired_FULL_CSA_4_4_minus_Normal: `{'mean_ms': -3.771639667296161, 'stdev_ms': 4.156894864027999, 'ci95': 1.6295027866989755}`
- paired_FULL_DRRA_8_4_minus_CSA_4_4: `{'mean_ms': -5.2187711137036485, 'stdev_ms': 2.15576798029017, 'ci95': 0.8450610482737465}`

## B1-2 realized unique blocks/query (synthetic batch; mechanics data-independent)

- CSA_4_4: `{'n_kv_blocks': 64, 'window': 32, 'unique_valid_mean': 13.9375, 'unique_valid_min': 0, 'unique_valid_max': 16, 'raw_topk_unique_mean': 14.18359375, 'adjacent_jaccard_mean': 0.47848840541099336}`
- DRRA_8_4: `{'n_kv_blocks': 32, 'window': 16, 'unique_valid_mean': 10.171875, 'unique_valid_min': 0, 'unique_valid_max': 16, 'raw_topk_unique_mean': 14.18359375, 'adjacent_jaccard_mean': 0.63537847053359}`
