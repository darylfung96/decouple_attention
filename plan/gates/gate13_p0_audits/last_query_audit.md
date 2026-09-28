# A-1 last-query audit

Verdict: **EQUIVALENT — earlier attention/MLP outputs unused; report full-layer vs forecast-required costs separately.**

| config | seed | attn_zero | attn_randx10 | mlp_zero | equiv |
|---|---|---|---|---|---|
| Normal | 0 | 0.00e+00 | 0.00e+00 | 0.00e+00 | True |
| Normal | 42 | 0.00e+00 | 0.00e+00 | 0.00e+00 | True |
| Normal | 123 | 0.00e+00 | 0.00e+00 | 0.00e+00 | True |
| CSA_4_4 | 0 | 0.00e+00 | 0.00e+00 | 0.00e+00 | True |
| CSA_4_4 | 42 | 0.00e+00 | 0.00e+00 | 0.00e+00 | True |
| CSA_4_4 | 123 | 0.00e+00 | 0.00e+00 | 0.00e+00 | True |
| DRRA_8_4 | 0 | 0.00e+00 | 0.00e+00 | 0.00e+00 | True |
| DRRA_8_4 | 42 | 0.00e+00 | 0.00e+00 | 0.00e+00 | True |
| DRRA_8_4 | 123 | 0.00e+00 | 0.00e+00 | 0.00e+00 | True |

## Analytic cost split (per forward, B=1)

- Normal: `{'scores_full': 8388608, 'scores_last': 32768, 'mlp_full': 33554432, 'mlp_last': 131072, 'note': 'Q-last still needs full K/V; scores 256x -> 1x (65,536 -> 256 per head per D).'}`
- CSA_4_4: `{'dense_cols': 96, 'scores_full_per_head': 24576, 'scores_last_per_head': 96, 'mlp_full': 33554432, 'mlp_last': 131072, 'note': 'window32 + 64 blocks + sink; K/V+compressors full-sequence regardless.'}`
- DRRA_8_4: `{'dense_cols': 48, 'scores_full_per_head': 12288, 'scores_last_per_head': 48, 'mlp_full': 33554432, 'mlp_last': 131072, 'note': 'window16 + 32 blocks + sink; K/V+compressors full-sequence regardless.'}`

## Stock full-forward latency (audit-speed protocol, B=32 — see note)

- Normal: `{'mean_ms': 43.988854169729166, 'stdev_ms': 1.744335922837725, 'rounds': 10, 'passes': 20, 'note': 'audit-speed protocol; A-2 uses full 25x30 alternating'}`
- CSA_4_4: `{'mean_ms': 43.62404458981473, 'stdev_ms': 0.338697710237258, 'rounds': 10, 'passes': 20, 'note': 'audit-speed protocol; A-2 uses full 25x30 alternating'}`
- DRRA_8_4: `{'mean_ms': 37.679874584428035, 'stdev_ms': 0.8898866206964833, 'rounds': 10, 'passes': 20, 'note': 'audit-speed protocol; A-2 uses full 25x30 alternating'}`
