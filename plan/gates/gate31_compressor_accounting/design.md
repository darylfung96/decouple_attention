# Gate 31 — compressor-term accounting recheck (executed tensor shapes)

**Written before the run.** 2026-10-21.

<!-- prose-ok: scope line in a design record, not an argument -->
This gate performs no training and launches no model runs.

## Why

The paper's attention-path accounting charges the two-series compressors
`2 * L * d * (64 + d_h)` MACs per sequence (paper Eq. 2, third term;
`compress_term()` in `plan/gates/gate20_accounting/router_accounting_audit.py`).
That term prices **one** projection of width `64` for the KV series and **one**
of width `d_h = 32` for the index series.

The module does not execute that. `_flat_two_series_compress()` (attention.py)
runs a `kv_proj` **and** a `gate_proj` per compressor, and both are
`Linear(hidden_size, 2 * dim)`:

- KV compressor: `comp_kv_proj`, `comp_gate_proj` — `d -> 2 * 32 = 64`
  (charged correctly: `2 * L * d * 64`).
- Index compressor: `idx_kv_proj`, `idx_gate_proj` — `d -> 2 * 32 = 64`
  (charged as `2 * L * d * d_h` = `2 * L * d * 32`, i.e. **half** the executed
  width, and one projection short).

Section 3.3 of the paper states the same compressor builds the index series
("the same compressor, with its own parameters"), so the index projection width
is `2 * d_h = 64`, not `d_h`. The router term was already corrected once for
exactly this class of slip (gate20: one head vs all heads); the compressor row
was carried forward from gate5 without a shape check.

## Question

Do the four executed compressor projections cost `2 * L * d * 64` MACs
(paper) or `4 * L * d * 64` (two projections of width `2 * d_h` per
compressor) per sequence at `L = 256`?

## Method

Instantiate `ExpertPlusPlusAttention` exactly as the factorial harness does
(`gate2_factorial.py` arguments: hidden 128, 4 heads, head dim 32, q rank 64,
o rank 64, window 16, top-k 16, `index_head_dim` 32), run one forward pass at
`B = 1, L = 256`, and record `tokens * in_features * out_features` for each of
`comp_kv_proj`, `comp_gate_proj`, `idx_kv_proj`, `idx_gate_proj` through
forward hooks.

<!-- prose-ok: method line, not a maxim -->
Both `c_KV` cells are measured.

## Prediction (falsifiable)

If the paper's term is right, `total == 6_291_456` for both cells.
If the index compressor is double-width, `total == 8_388_608`.

## Output

`results.json` + `summary.md`. Gate20's published JSON is **not** modified
(append-only history); this gate supersedes only the compressor row.
