# C3 — Systems evidence and release package

**Status:** TODO · **Cost:** days, hardware-dependent · **Depends:** R6 for the metric definitions

**Verdict:** PARKED — the paper claims neither GPU behaviour nor energy savings, so there is nothing here for a referee to check.
**Start when:** a referee asks for wall-clock or energy evidence; wall-clock under the same protocol is the cheap response, energy only with real instrumentation.

**Source:** Q1 review §7 "Strengthen the statistics and systems evidence" (PDF p. 8), "Benchmark optimized implementations, not only operation counts" (line 408) and "Treat energy as a measurement question" (line 421).

## What the review asked

Benchmark optimized implementations rather than only operation counts. Use the existing Apple CPU
measurements as one platform and add a representative GPU or a clearly justified second platform, and
compare against the strongest valid dense implementation including fused attention where compatible,
because FlashAttention shows why reduced memory traffic and reduced arithmetic must be distinguished.
Measure forecast-required latency at batch 1 and at a realistic batched setting, throughput, peak
allocated memory, forward-plus-backward time and end-to-end training time; report dtype, kernel,
compilation mode, thread count, synchronization, warm-up, device and software versions; alternate timed
configurations within rounds and report paired uncertainty; and include compression, index scoring,
top-k, masks, transfers and the prediction head in the timed path. State explicitly that the current
implementation pays the full compressed attention width despite sparse masks and profile where time is
spent. On energy: move the arithmetic-to-energy projections to a qualified appendix or replace them with
sustained instrumented measurements, and if joules per forecast are reported, state whether the boundary
is device-only or whole-system, report idle treatment, integrate power over a timed workload, and
quantify measurement resolution. Finally, release a tagged code archive, dataset hashes, configuration
files, raw paired results, profiler traces, corrected tests and one-command table and figure
regeneration, and archive the exact version used for submission.

## What already holds

- Single-machine (Apple M2, fp32, 8 threads) latency with bootstrap intervals, p90/p99 tails, batch
  scaling 1–256 and lookback scaling 128–4096; analytic MACs, peak process watermark, training time;
  alternating head-to-head rounds; both full-layer and forecast-required paths (the latter from R6's
  measurements).
- The energy work is already scoped as a first-order projection in the appendix, with sensitivity and
  an explicit non-claim, and the paper states that MACs are not energy and that the dense-masked
  implementation pays the full compressed width.
- The repository carries manifests, dataset hashes, environment locks and regeneration scripts.

## What is left

- [ ] **Second platform.** Port the timing harness to a GPU (or an x86 CPU with a stated justification)
      and report the same metric set, with fused attention for the dense baseline where compatible. Note
      in the paper that the memory advantage measured here is implementation-relative because the
      materializing dense path is the comparison.
- [ ] **Profiling.** Add a profiler trace of the timed path and report where time goes (compressor,
      indexer, mask construction, GEMM), which substantiates the "dense masking pays full width" claim.
- [ ] **Metric coverage.** Add throughput, peak allocated memory, forward-plus-backward time and
      end-to-end training time to the released tables, with the environment block the review lists.
- [ ] **Energy, if it is claimed.** Either keep the projection in the appendix as a model-based estimate
      (current stance) or instrument: decide the boundary (device-only versus whole system), record idle
      power, integrate power over a timed workload and state the measurement resolution.
- [ ] **Release.** Tag a version, archive it, and check that one command regenerates every table and
      figure. The review's phrasing matters: the paper currently says the artifacts exist on the
      repository, not that an independently verified tagged release exists.

## Acceptance

Every efficiency claim in the paper names its platform, its path (full-layer or forecast-required) and
its uncertainty; the energy claim is either instrumented or explicitly model-based in an appendix; and a
tagged release reproduces the tables and figures in one command.

## Evidence pointers

- `plan/gates/gate5/gate5_bench.py`, `plan/gates/gate3/gate3_latency*` (current systems measurements)
- `plan/gates/gate13_p0_audits/last_query_latency.{json,md}` (forecast-required path, R6)
- `paper/sections/experiments.tex` §4.7, `paper/sections/appendix.tex` energy appendix and reproducibility section
- `plan/environment-lock.txt`, `plan/REPRO.md` (current release scaffolding)

## Log

- 2026-10-16: created from the review's "strengthen the statistics and systems evidence".
