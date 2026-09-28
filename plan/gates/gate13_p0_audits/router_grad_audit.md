# B2-1 router grad audit

Verdict: **CSA_4_4: indexer DOES-NOT-LEARN (all ~0) | DRRA_8_4: indexer DOES-NOT-LEARN (all ~0)**

Note: `idx_weights_proj` mixes continuously BEFORE topk — nonzero there alone is not proof routing learns; selection-path params (`idx_kv_proj/idx_gate_proj/idx_position_bias/idx_norm`, CSA `idx_q_proj`) are the test.

## CSA_4_4 (loss 1.2714)

| param | group | grad_norm | sgd_delta |
|---|---|---|---|
| pos_embedding | shared/other | 2.979e-02 | 2.979e-05 |
| input_proj.weight | shared/other | 8.511e-02 | 8.512e-05 |
| input_proj.bias | shared/other | 2.992e-02 | 2.992e-05 |
| attn.sinks | shared/other | 4.615e-05 | 4.615e-08 |
| attn.comp_position_bias | compressor | 1.019e-03 | 1.019e-06 |
| attn.idx_position_bias | indexer-exclusive | 0.000e+00 | 0.000e+00 |
| attn.q_a_proj.weight | shared/other | 4.630e-02 | 4.630e-05 |
| attn.q_a_norm.weight | shared/other | 2.325e-03 | 2.359e-06 |
| attn.q_b_proj.weight | shared/other | 3.161e-02 | 3.161e-05 |
| attn.kv_proj.weight | shared/other | 5.891e-02 | 5.891e-05 |
| attn.kv_norm.weight | shared/other | 3.824e-03 | 3.834e-06 |
| attn.o_a_proj.weight | shared/other | 3.066e-02 | 3.066e-05 |
| attn.o_b_proj.weight | shared/other | 1.225e-01 | 1.225e-04 |
| attn.comp_kv_proj.weight | compressor | 2.640e-02 | 2.640e-05 |
| attn.comp_norm.weight | compressor | 1.453e-03 | 1.449e-06 |
| attn.idx_kv_proj.weight | indexer-exclusive | 0.000e+00 | 0.000e+00 |
| attn.idx_norm.weight | indexer-exclusive | 0.000e+00 | 0.000e+00 |
| attn.idx_q_proj.weight | indexer-exclusive | 0.000e+00 | 0.000e+00 |
| attn.idx_weights_proj.weight | indexer-exclusive | 0.000e+00 | 0.000e+00 |
| attn.comp_gate_proj.weight | compressor | 1.380e-02 | 1.380e-05 |
| attn.idx_gate_proj.weight | indexer-exclusive | 0.000e+00 | 0.000e+00 |
| norm1.weight | shared/other | 3.160e-02 | 3.158e-05 |
| norm1.bias | shared/other | 3.300e-02 | 3.300e-05 |
| mlp.0.weight | shared/other | 1.373e-01 | 1.373e-04 |
| mlp.0.bias | shared/other | 1.213e-02 | 1.213e-05 |
| mlp.2.weight | shared/other | 2.538e-01 | 2.538e-04 |
| mlp.2.bias | shared/other | 3.245e-02 | 3.244e-05 |
| norm2.weight | shared/other | 8.889e-02 | 8.887e-05 |
| norm2.bias | shared/other | 5.821e-02 | 5.821e-05 |
| output_proj.weight | shared/other | 7.379e-01 | 7.379e-04 |
| output_proj.bias | shared/other | 6.645e-02 | 6.645e-05 |

## DRRA_8_4 (loss 1.3758)

| param | group | grad_norm | sgd_delta |
|---|---|---|---|
| pos_embedding | shared/other | 3.370e-02 | 3.368e-05 |
| input_proj.weight | shared/other | 7.900e-02 | 7.899e-05 |
| input_proj.bias | shared/other | 3.583e-02 | 3.583e-05 |
| attn.sinks | shared/other | 9.874e-05 | 9.874e-08 |
| attn.comp_position_bias | compressor | 1.702e-03 | 1.702e-06 |
| attn.idx_position_bias | indexer-exclusive | 0.000e+00 | 0.000e+00 |
| attn.q_a_proj.weight | shared/other | 4.374e-02 | 4.374e-05 |
| attn.q_a_norm.weight | shared/other | 2.686e-03 | 2.657e-06 |
| attn.q_b_proj.weight | shared/other | 4.253e-02 | 4.253e-05 |
| attn.kv_proj.weight | shared/other | 6.059e-02 | 6.059e-05 |
| attn.kv_norm.weight | shared/other | 2.722e-03 | 2.713e-06 |
| attn.o_a_proj.weight | shared/other | 3.888e-02 | 3.888e-05 |
| attn.o_b_proj.weight | shared/other | 1.150e-01 | 1.150e-04 |
| attn.comp_kv_proj.weight | compressor | 4.369e-02 | 4.369e-05 |
| attn.comp_norm.weight | compressor | 2.153e-03 | 2.172e-06 |
| attn.idx_kv_proj.weight | indexer-exclusive | 0.000e+00 | 0.000e+00 |
| attn.idx_norm.weight | indexer-exclusive | 0.000e+00 | 0.000e+00 |
| attn.idx_weights_proj.weight | indexer-exclusive | 0.000e+00 | 0.000e+00 |
| attn.comp_gate_proj.weight | compressor | 2.227e-02 | 2.228e-05 |
| attn.idx_gate_proj.weight | indexer-exclusive | 0.000e+00 | 0.000e+00 |
| norm1.weight | shared/other | 3.770e-02 | 3.768e-05 |
| norm1.bias | shared/other | 3.788e-02 | 3.788e-05 |
| mlp.0.weight | shared/other | 1.598e-01 | 1.598e-04 |
| mlp.0.bias | shared/other | 1.443e-02 | 1.443e-05 |
| mlp.2.weight | shared/other | 2.942e-01 | 2.942e-04 |
| mlp.2.bias | shared/other | 3.810e-02 | 3.810e-05 |
| norm2.weight | shared/other | 1.021e-01 | 1.021e-04 |
| norm2.bias | shared/other | 6.836e-02 | 6.836e-05 |
| output_proj.weight | shared/other | 7.459e-01 | 7.459e-04 |
| output_proj.bias | shared/other | 6.701e-02 | 6.701e-05 |
