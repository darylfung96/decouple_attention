# B1-5 index→KV mapping audit

| cell | n_kv | n_idx | selected range | sentinel | expected | verdict |
|---|---|---|---|---|---|---|
| (4,4) | 64 | 64 | 0..62 | 0.129 | 0..63 identity needed | **CORRECT** |
| (8,4) | 32 | 64 | 0..30 | 0.147 | 0..31 (t//2 correct) | **CORRECT** |
| (4,8) | 64 | 32 | 0..63 | 0.324 | 1-token-to-2-blocks fan-out needed | **CORRECT** |
| (8,8) | 32 | 32 | 0..31 | 0.262 | 0..31 identity needed | **CORRECT** |

Scope: HISTORICAL BUG (fixed 2026-09-28): gate2 (5 seeds) + gate7 (20 seeds) + gate3 suite Flat built compressed cells via EPPTimeSeriesModel with unconditional t//2; only (8,4) was correct. Post-fix audit: all four geometries map correctly.
