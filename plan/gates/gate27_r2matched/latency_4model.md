# Gate 27 amendment — matched dense baseline latency

Instrument: gate13 `last_query_latency.py`, reused unmodified (4 models, 25x30 round-robin, B=32, L=256). Equality gate for Normal_r64: seed 0 7.2e-07, seed 42 6.0e-07, seed 123 6.0e-07

## Same-run reproduction of the released numbers

| config | path | same run (ms) | released (ms) | ratio |
|---|---|---|---|---|
| Normal_FULL | | 41.96 | 40.73 | 1.030 |
| Normal_LAST | | 3.05 | 2.62 | 1.163 |
| CSA_4_4_FULL | | 40.00 | 36.96 | 1.082 |
| CSA_4_4_LAST | | 7.25 | 6.18 | 1.174 |
| DRRA_8_4_FULL | | 34.54 | 31.74 | 1.088 |
| DRRA_8_4_LAST | | 6.81 | 5.82 | 1.169 |

Worst deviation vs released: 17.4% (OUTSIDE the 15% reproduction band)

## Matched model

| path | raw same-run (ms) | ratio vs same-run Normal | released-anchored (ms) |
|---|---|---|---|
| FULL | 39.91 | 0.951 | 38.74 |
| LAST | 3.15 | 1.034 | 2.71 |
