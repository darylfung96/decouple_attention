# Gate 2 Interpretation — Why (8,4) = (c_KV=8, c_R=4) Won

**Status: LIVING doc (created 2026-08-20).** Interprets the Gate-2 factorial
results (`plan/gates/gate2/gate2_summary.md`, ETTh1 only, 5 paired seeds). Update
this doc when Gate 3 (12-dataset sweep, running) confirms or refutes the
generalization, and when Gate 4 adds significance tests.

---

## 1. The result (recap — full detail in `gate2_summary.md`)

| Cell | Val mean±std | Test mean | Reading |
|---|---|---|---|
| (4,4) | 0.6332 ± 0.0611 | 0.9079 | equal-rate baseline |
| **(8,4)** | **0.5967 ± 0.0710** | **0.7988** | champion |
| (4,8) | 0.6858 ± 0.0875 | 0.8996 | worst |
| (8,8) | 0.6368 ± 0.0393 | 0.9159 | ≈ (4,4) |

Directional effects across the grid: **c_KV 4→8 improves** mean val (−0.0427);
**c_R 4→8 worsens** it (+0.0463). **Both effects are smaller than the seed-to-seed
std (0.0647); no significance test was run.** Everything below is a descriptive
reading, not an established mechanism. Significance testing is Gate 4.

## 2. The mechanism reading

The two axes are not symmetric in what they compress:

- **c_KV = content compression.** KV blocks of size 8 → 32 content blocks. This
  pools the value content the attention reads.
- **c_R = routing resolution.** Index blocks of size 4 → 64 candidates (topk 16
  selects among them). This sets the *granularity* at which the router can point
  at positions.

**(8,4) = aggressive content pooling + fine routing.** Why this corner wins:

1. **Content compression is cheap on this signal.** Hourly series are smooth and
   temporally redundant; 8:1 KV pooling discards little information, and the
   shared-Q / low-rank-O projection family can reconstruct the pooled content
   well (matches the design intuition in `gate2_design.md` and the EPP rationale
   in `model.py`).
2. **Routing precision is what the head actually consumes.** The frozen horizon
   head reads **only the last hidden state** (`output_proj(x[:, -1, :])`,
   `gate1_task.md` §1-2). Forecast quality is therefore bounded by how precisely
   the router retrieves the relevant recent context — and fine index blocks (4)
   keep candidate positions sharp. Coarsening the router ((4,8)) degrades
   retrieval precision while finer content blocks add little → the worst cell.
3. **Equal-rate pairs behave alike.** (8,8) ≈ (4,4): the two rates trade off
   against each other, consistent with a single effective "compression ×
   resolution" budget.

This asymmetry is exactly the pre-registered **H1** (`next_step.md` §9,
`paper_notes.md` §5): *"increasing c_R causes larger MSE deterioration than
c_KV"*. Gate 2 provides **directional support only** — the signs match H1, the
magnitudes do not clear seed noise.

## 3. Confirmation, not discovery

(8,4) is not a grid-search find: it is the **pre-registered champion corner** —
the original ExpertPlusPlus configuration (`model.py` `compress_rate=8`,
`index_compress_rate=4`) that Gate 2 was designed to test. Per-seed it beats the
(4,4) baseline in only **3/5 seeds** (deltas −0.1485 / −0.0540 / +0.0111 / −0.0730
/ +0.0821). The evidence base is a single dataset (ETTh1) at CPU scale. **Gate 3
is precisely the generalization test**: does (8,4) beat Normal and (4,4) on 12
datasets with paired seeds?

## 4. Why c_R=16 was not run (and is not needed for the current claim)

- The factorial grid was **pre-registered as {4,8}²** (`gate2_design.md`);
  c_R=16 was never part of the design.
- **c_R=16 is a degenerate endpoint, not "finer routing".** At
  `index_compress_rate=16` there are 256/16 = **16 index blocks**, and with
  `index_topk=16` the router selects **all of them** — routing collapses to
  "attend to everything at block level". A (·,16) cell would test the
  *no-routing endpoint* of the design axis, a different construct from higher
  routing resolution (which would require raising `index_topk` too, changing
  the aux contract).
- The 2×2 grid already brackets the c_R effect (4 vs 8), which is all H1 and
  the two-axis framing need. Extrapolating the directional trend, (8,16) and
  (4,16) should land ≤ (8,8) — **that is a prediction, not evidence**.
- If the paper ever wants the endpoint ablation: add (8,16) / (4,16) cells,
  idempotent per (cell, seed), ~2-3 h for 5 seeds on ETTh1; fold into the
  deferred follow-on work (H/L grid, `next_step.md` §6 note) or Gate 4.

## 5. What would strengthen or refute this reading

- **Gate 3** (running, `plan/gates/gate3/`): does (8,4) beat Normal and (4,4)
  on most of the 12 datasets (paired per-seed deltas)? A dataset where (4,4) or
  Normal wins would bound the story (e.g., high-dimensional channels where
  content compression is costlier — electricity/traffic).
- **Gate 4**: mixed-effects model (`MSE = β₀ + β₁ log₂(c_KV) + β₂ log₂(c_R) +
  β₃ log₂(c_KV)log₂(c_R) + random effects`); H1 requires β₂ > β₁ in the
  operating region; CIs on the effects.
- **Mechanistic diagnostics (§12, optional)**: routing recall (do fine routers
  select high-mass positions?), lag localisation on the synthetic delayed-copy
  task (Gate 3 includes it), content-distortion vs c_KV. These would test
  reading (2) directly rather than indirectly.

## Cross-references

- Results: `plan/gates/gate2/gate2_summary.md` (+ raw rows `gate2_results.jsonl`)
- Design/pre-registration: `plan/gates/gate2/gate2_design.md`
- Task contract: `plan/gates/gate1/gate1_task.md`
- Protocol: `plan/benchmark_protocol.md`
- Hypotheses: `next_step.md` §9 (H1-H5), `plan/paper_notes.md` §5
- Generalization test: `plan/gates/gate3/gate3_design.md` + `gate3_summary.md`
