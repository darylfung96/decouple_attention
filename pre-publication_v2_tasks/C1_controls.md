# C1 — Decisive controls: is the router needed at all?

**Status:** DONE 2026-10-19 (all-block control only) · **Verdict:** routing is load-bearing; compression alone also beats full attention · **Cost:** 25–40 h including implementation · **Depends:** R2 for the matched row
**Source:** Q1 review §4 "Establish whether the router is needed at all" (PDF p. 5; `source/q1_review_text.txt` lines 203–267), the control table at lines 208–249; the external comparators also come from the manager's email.

**Verdict:** PARTIAL KEEP — only the all-block compression control is kept; the other seven controls in the review's table are parked (see `N_necessity_audit.md`).
**Start when:** Phase 4, after D5 (margin) is frozen and R2 has landed. This is the experiment that can change the paper's story, so its interpretation rule is written before its first run.
**Branch rule:** worse than margin → routing works; within margin → boundary result, retitle per D4; better → the router is harmful, report it plainly.

## Why this is the highest-value block

The current implementation computes attention densely over every compressed column even when most are
masked, so removing the router does not widen the attention core; it only removes the indexer and the
selector. That makes "compression without routing" a cheap and decisive control: if all-block compressed
attention matches or beats the routed cells on both accuracy and optimized latency, then routing is not
paying for itself in this regime, and the paper's honest contribution becomes "here is when routing is
unnecessary", which the review explicitly calls a stronger result than a favorable configuration.

## The controls, in the review's suggested order

| Control | Question it answers | Matching and reporting requirements | Cost |
|---|---|---|---|
| Projection-matched dense | Do the gains survive removal of the projection confound? | Match ranks, width, normalization, readout; disclose sink and positional differences | see R2 (3–4 h) |
| All-block compressed, no router | Is compression alone sufficient? | Test `c_KV = 4` and 8; keep the compressor, local window and head; report the realized column count | ≈7 h (2 × 25 seeds) |
| Window-only (no historical branch) | Does forecasting need the compressed history at all? | Same backbone and head; report the window size | 3–4 h |
| Random, recent and evenly-spaced selection | Does content-based selection beat inexpensive rules? | Match unique valid blocks; compare lag and coverage distributions | ≈20 h (3 rules × 2 `c_KV` × 25 seeds) |
| Mean or filtered pooling compressor | Is the learned overlapping compressor better than simple smoothing? | Match output block count; separate filter width from routing resolution | ≈7 h plus implementation |
| Trained indexer | Does learning block importance change the factorial result? | Report training loss, optimization budget, added parameters and inference overhead | see R4 (3–4 h per variant) |
| Original dense forecasting backbone | Is the modified model useful beyond the minimal testbed? | A competent temporal-token architecture plus its unmodified version | see C2 |

## What is left

- [ ] Run the first three controls on ETTh1 and one contrasting dataset before anything else: projection
      matching (R2), all-block compression, and the four factorial cells under the same protocol.
- [ ] Then the inexpensive selection rules (random, recent, evenly spaced) to see whether remote content
      and content-dependent selection contribute anything.
- [ ] Only after that, the learned-indexer and broader transfer experiments.
- [ ] Decide the paper's response if all-block compression matches routed compression. The review's
      instruction is explicit: do not preserve the router merely to preserve the name DRRA.
- [ ] External comparators (manager's email): MEAformer and, where a faithful implementation exists,
      PMformer, as complete-system comparisons kept separate from the same-backbone ablations. This needs
      third-party code under the frozen protocol plus a per-model tuning budget, and the review warns
      that an identical optimizer for unlike architectures is not a fair best-achievable comparison.
      Estimate: days of engineering plus GPU time.

## Acceptance

At least one control resolves the review's question against the preferred design, and the paper states
the result whichever way it goes, including the possibility that routing is unnecessary in this regime.

## Evidence pointers

- `expert_plus_plus_attention.py` (`_attend` computes over the full compressed column set; the mask
  selects), which is why the all-block control is cheap
- `paper/sections/appendix.tex` future-work item 5 (the deferred controls, already listed)
- `README.md` in this folder, recommended order

## Log

- 2026-10-16: created from the review's P1 table and the manager's email.

- 2026-10-17 (Phase 4 start): design frozen pre-run at `plan/gates/gate28_c1control/design.md` — two control cells (c_KV = 4 and 8, c_R = 4), single variable `index_topk` 16 -> 64 (= n_idx); no new parameters (state_dicts bitwise equal at a fixed seed) and no new compute path (selection enters only as a mask). `--dry-run` passes: 0 of 256 positions deviate from the brute-force safe set, realized distinct blocks 31.75 of 64 (4,4) vs routed 13.94, and 15.62 of 32 (8,4) vs routed 9.91. `--smoke` finite. `--full` launched 2026-10-18T05:07Z into `results/allblock.jsonl` (50 runs). `analysis.py` refuses to run while D5 is unfrozen — D5 (2% relative, the plan's anchor) is the one input this phase is waiting on. Branch rule: `design.md` §"D5 margin and branch rule".

- 2026-10-18 (D5 frozen + run incident): D5 frozen at 2% relative for the label, with the *bound* as the
  primary output (`DECISIONS.md` freeze log). Rationale from a pre-run precision check on the six existing
  cell pairs: paired relative half-widths are 5.3--7.7% at n=25 (paired SD 0.079--0.116), so a 2% containment
  test needs seed-correlation >= 0.91 while the study's same-family pairs measure 0.11--0.18; a 6% margin
  would sit at the resolution limit *and* contradict the paper's reading of the 5.72% matched-dense gap, so
  it was rejected. `analysis.py` now reports U (95% upper limit on the relative cost of removing routing),
  the pre-registered all-block-vs-Normal test, and a five-way label including "within margin but not
  resolvable". Synthetic end-to-end test done before real data (0%, +15%, -15% cases behave correctly).
- 2026-10-18 (incident): seed 123's wall clock (30,575 s vs 409 s for seed 42) was ~8.4 h of macOS system
  sleep, not compute; `caffeinate -dimsu -w <pid>` attached, and the ETA is now a median of completed runs.
  Manifests are unaffected: rows carry trained numbers, no timing field.

- 2026-10-19 (CLOSED, branch `routing_confirmed`): 50 runs complete. Removing the selection at
  identical parameters and MACs costs +27.1% [(4,4), CI 18.9-35.3] and +11.8% [(8,4), CI 4.6-19.1]
  paired relative validation MSE (1/25 and 5/25 seeds favour the control; exact Wilcoxon p = 1.2e-7 and
  0.0015; test MSE same direction). Pre-registered secondary test: the selection-free cells still beat
  Normal (-0.066 [-0.112,-0.020], 18/25; -0.153 [-0.203,-0.103], 24/25), so compression alone reproduces
  the headline and the router adds a separate gain. Paper: §4.6 paragraph + Table 6, intro (c),
  conclusion, audit-table row. D4 stays (a) keep the title (no boundary); D3 default (a) applies — the
  indexer receives no task gradient (B2-1), so a trained selector is a design change, not a control.
  Evidence: `plan/gates/gate28_c1control/{design.md,run.py,analysis.py,results/allblock.jsonl,analysis.json,analysis.md,run.log}`.

