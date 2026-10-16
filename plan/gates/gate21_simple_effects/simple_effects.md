# Gate 21 — per-seed conditional effects (Q1 review R1)

25 paired seeds, validation MSE, merged v2 matrix.

| conditional effect | mean | 95% paired CI | Wilcoxon p | sign |
|---|---|---|---|---|
| c_KV 4->8 at c_R=4 | +0.0042 | [-0.0437, +0.0521] | 0.6150 | 9/25 |
| c_KV 4->8 at c_R=8 | -0.0682 | [-0.1009, -0.0355] | 0.0001 | 21/25 |
| c_R 4->8 at c_KV=4 | +0.0662 | [+0.0265, +0.1059] | 0.0020 | 19/25 |
| c_R 4->8 at c_KV=8 | -0.0062 | [-0.0475, +0.0350] | 1.0000 | 13/25 |

Cross-checks (must reproduce the published values):

- kv_main_mean: -0.0320
- cr_main_mean: +0.0300
- interaction_mean: -0.0724
- kv_main_est: -0.0320 [-0.0618, -0.0023], Wilcoxon p = 0.0096
- cr_main_est: +0.0300 [+0.0010, +0.0589], Wilcoxon p = 0.0588
- interaction_est: -0.0724 [-0.1289, -0.0158], Wilcoxon p = 0.0136
