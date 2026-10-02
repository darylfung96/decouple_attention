# Cell speed addendum (FULL vs LAST, 25x30 round-robin B32)

cols/query: `{'Normal': 256, 'DRRA_8_4': 48, 'EPP_16_4': 32, 'EPP_32_4': 16}` | gate: PASS

| path | mean ms | vs Normal FULL |
|---|---|---|
| Normal FULL | 45.59 | 1.00x |
| Normal LAST | 3.48 | 13.12x |
| DRRA_8_4 FULL | 38.63 | 1.18x |
| DRRA_8_4 LAST | 7.53 | 6.06x |
| EPP_16_4 FULL | 37.29 | 1.22x |
| EPP_16_4 LAST | 8.26 | 5.52x |
| EPP_32_4 FULL | 37.36 | 1.22x |
| EPP_32_4 LAST | 7.61 | 5.99x |
FULL speedup DRRA_8_4 vs Normal: 1.18x
FULL speedup EPP_16_4 vs Normal: 1.223x
FULL speedup EPP_32_4 vs Normal: 1.22x
