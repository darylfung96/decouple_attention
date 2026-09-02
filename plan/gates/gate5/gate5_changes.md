# Gate 5 — Changes / Audit Log (systems benchmarking on the development machine)

- **2026-08-25 · Scope + execution start (user: "continue on with gate 5").**
  - Partially pre-completed in earlier turns (Gate-3 companions): mean latency + bootstrap CIs + throughput at batch 32 (`gate3_latency.py`/`gate3_latency.json`), batch-size scaling B ∈ {1..256} (`gate3_latency_scale.py`/`gate3_latency_scale.json`), paper Table 5 + Figure 4.
  - New this pass (`plan/gates/gate5/gate5_bench.py` → `gate5_results.json`), all on the frozen protocol (L=256/H=96/F=7 unless noted, fp32, 8 threads):
    1. Full hardware details (macOS/chip/cores/RAM/torch/BLAS via `torch.__config__`, thread + interop settings).
    2. Empirical MACs per model at L=256/B=1 via torch.profiler `record_shapes` (aggregated over aten::linear/addmm/mm/matmul/bmm/einsum).
    3. Peak RSS growth over a warm batch-32 forward burst + param memory.
    4. Training time per variant on ETTh1 (parsed from `gate3_sweep.log` FINAL elapsed lines).
    5. Sequence-length scaling L ∈ {128, 256, 512, 1024, 2048, 4096} × batch {1, 32}: mean ms/batch + 95% CI + **empirical log-log slopes** (L ≥ 512) — the §11 complexity evidence.
    6. Top-CPU-ops profile at L=256/B=32 (stage attribution by op).
  - **Fixes during bring-up:** `gate3_harness` import (gate5 dir was on sys.path instead of gate3; harness's flat sibling imports require the gate3 dir on path); models rebuilt per L (`EPPTimeSeriesModel`/`NormalTimeSeriesModel` accept `lookback=`; pos_embedding is L-sized).
  - **Out of scope / unavailable:** cross-hardware (needs a second machine — Linux x86 / GPU not available on this setup; documented as limitation; scripts are portable), model depth/width sweep (deferred — separate ablation), time-to-quality beyond best-val epoch proxy.

- **2026-08-27 · Benchmark complete + docs/paper updated.**
  - `gate5_results.json` complete: machine block (Mac14,2 / Apple M2 / 8 cores / 16 GB / macOS 14.6 / torch 2.6.0 / 8 threads), analytic MACs (Normal 76.9M, (4,4) 61.7M, (8,4) 59.6M per sequence — component breakdown included), peak RSS (batch-32 watermark +299 MB; param memory 1.4 MB/model), training time medians (Normal 474 s / (4,4) 511 s / (8,4) 459 s; one 1417 s DRRA run excluded as machine-sleep-contaminated), L-scaling with log-log slopes (batch 1: 1.24/1.32/1.69; batch 32: 1.40/1.42/1.72 for (8,4)/(4,4)/Normal), top-ops profile (Normal: bmm+softmax = the dense attention dominates; (8,4): flatter). L=4096/B=32 skipped with recorded reason (~8 GB score tensor).
  - `gate5_summary.md` written (8 sections incl. complexity reading: all cells asymptotically quadratic via router O(L²/c_R); NO subquadratic claim).
  - Paper: Efficiency subsection extended ("Sequence-length scaling and complexity" + "Compute and memory accounting" + new Figure `fig:lscale`); method.tex Complexity paragraph rewritten (honest quadratic-in-L statement, pointer to measured evidence); discussion limitation updated ("Single-machine systems measurements"); experiments batch-scaling TODO removed (cross-hardware → roadmap); fig8 (L-scaling, B=1 + B=32) added to make_figures.py. Remaining Gate-5 TODOs scoped to cross-hardware + depth/width only.
  - plan/next_step.md §10 checkboxes updated (done/deferred with reasons) + ✅ blockquote; §11 all four checkboxes done (complexity derived, constant-reduction stated, subquadratic explicitly disclaimed, slopes reported). plan/paper_notes.md §5 H2/H3/H4 statuses updated with Gate-5/Gate-3 evidence.
  - Recompiled: exit 0, 13 pages, only pre-existing underfull-hbox; PDF verification passed.

- **2026-08-27 · Gate-5 remainder skipped by decision (user) — TODOs converted to future-work statements.**
  - User decision: skip cross-hardware (no Linux/GPU available) and depth/width (out of the single-block design-study scope). Both are now stated in the paper as conscious scope exclusions / future work, NOT as red TODO markers.
  - `paper/sections/method.tex` (Complexity ending) + `discussion.tex` (limitations item): `\todo{Gate 5 remainder ...}` → plain "conscious scope exclusions … left to future work" sentences. `appendix.tex` roadmap item 4 → "DONE on the development machine … remaining as future work". `paper/README.md` TODO inventory updated (also removed the duplicated stale Gate-4 line).
  - Recompiled: exit 0, 13 pages, only pre-existing underfull-hbox. Remaining TODOs in the paper are all non-Gate-5 pending items (Gate-1 citation, H1–H5 mechanistic status, H4 analysis, surrogate retention, freeze-clean package).
