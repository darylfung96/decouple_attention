# Runbook — exact commands and close-out rules

Companion to `EXECUTION_PLAN.md`. The plan says what to do and when; this file says how to type it and
how to prove it worked. Nothing here is exploratory: every command either exercises code with no
consequence (`--dry-run`, `--smoke`) or writes only into new files.

## Environment

| Thing | Value |
|---|---|
| Repo root | `/Users/darylfung/Documents/Work/Nicosia/new_attention` |
| Python | `~/.uv_env/py311/bin/python` (uv env, torch 2.6.0, CPU-only for everything in this plan) |
| Paper build | `cd paper && ../tectonic -X compile main.tex` |
| Manuscript check | `~/.uv_env/py311/bin/python paper/scripts/verify_manuscript.py` (exit 0 required) |
| Training reference | ETTh1, lookback 256, horizon 96, 10 epochs, about 8–10 min per run on 8 threads |
| Seed set (fixed) | `42 123 2024 7 99 1 2 3 4 5 6 8 9 10 11 12 13 14 15 16 17 18 19 20 21` (25 paired) |

## Directory convention for any new run

```
plan/gates/<NN>_<slug>/
├── design.md        # written and dated BEFORE the first real run: question, config, seeds, decision rule
├── <script>.py      # the driver, importing existing harness code rather than copying it
├── results/*.jsonl  # raw per-run records, one JSON object per line, appended, never edited
├── analysis.py      # reads the raw JSONL and writes the summary
└── analysis.md      # the result, its interval, and the branch taken
```

Rules that make this worth following: new directory per run class, imports instead of copies, raw
records appended and never rewritten, analysis reproducible from the raw file alone.

---

## Phase 2 recipes

### R5 — regenerate the two mechanism probes (about 30 min)

The gate12 driver trains both synthetic families across three variants and writes
`plan/gates/gate12/gate12_results.json` plus checkpoints. **Do not run it in place** — that would
overwrite historical output.

```bash
# from repo root
mkdir -p plan/gates/gate26_r5probes/checkpoints
cp plan/gates/gate12/gate12_mechanistic.py plan/gates/gate26_r5probes/
# edit the copy: HERE/OUT_JSON/CKPT_DIR now resolve to gate26_r5probes
~/.uv_env/py311/bin/python plan/gates/gate26_r5probes/gate12_mechanistic.py
```

Then, in the manuscript: replace the two historical probe values in §4.3 with the regenerated ones, or
move the paragraph to the appendix as history with the current numbers in the main text. The causality
test extension (index-score masking, tie-breaking at each rate pair) is pytest-style code in
`test_expert_plus_plus.py`; run the whole file and keep the log:

```bash
~/.uv_env/py311/bin/python -m pytest test_expert_plus_plus.py -q 2>&1 | tee plan/gates/gate26_r5probes/tests.log
```

### R6 — rebuild the efficiency frontier (about 1 h, no runs)

Data already exists in `plan/gates/gate13_p0_audits/last_query_latency.json`.

```bash
cd paper && ~/.uv_env/py311/bin/python scripts/make_figures.py --v2   # same command that regenerates all figures
```

Change in `paper/scripts/make_figures.py`: the performance-versus-speed figure takes forecast-required
latency on the x-axis, with the full-layer frontier as a labelled second panel. Update the caption and
the §4.7 pointer, then rebuild the paper and run the manuscript check.

### R4 — route-stability probe (about 30 min)

No per-epoch route data exists for any run, and only the gate12 checkpoints are stored, so the probe
instruments one training run rather than reading history.

```bash
~/.uv_env/py311/bin/python plan/gates/gate15_rerun/gate15_run.py --dry-run   # confirms the harness still builds
```

Then add a hook in the training loop that, once per epoch on a fixed validation batch, records the
selected block set per query position for one cell (use (8,4); it is the paper's primary cell), and a
new driver that runs one seed (42) and writes `results/route_snapshots.jsonl`. Report: mean Jaccard
overlap between the epoch-1 and final-epoch selected sets, and the fraction of positions whose set is
unchanged. One run ≈ 8–10 min plus code.

### C4 — MoBA paragraph (about 30 min, writing only)

Add one paragraph to related work comparing the study's fixed-rate selection against mixture-of-block
attention, citing the MoBA paper. Nothing else in C4; the selection guide stays parked.

---

## Phase 3 recipe — R2 projection-matched dense

The harness already builds cells through `build_all_cells()` in `plan/gates/gate2/gate2_factorial.py`,
where each cell carries `q_lora_rank` and `o_lora_rank` (the compressed cells use rank 64 for the output
projection; the as-run Normal uses 128). `EPPTimeSeriesModel(num_features, compress_rate, index_compress_rate, q_lora_rank, o_lora_rank)`
accepts both ranks directly.

```bash
# 1. add a Normal-r64 entry to the harness config (same handling as Normal, o_lora_rank=64)
# 2. prove the equalization before training anything:
~/.uv_env/py311/bin/python plan/gates/gate2/gate2_factorial.py --dry-run
#    expect: parameter table shows the projection matched against the compressed cells
# 3. bounded smoke test, saves nothing:
~/.uv_env/py311/bin/python plan/gates/gate2/gate2_factorial.py --smoke
# 4. real run: 25 seeds into a NEW manifest under gate27_r2matched/
```

Write the driver as a thin variant of `plan/gates/gate15_rerun/gate15_run.py` (it already imports the
gate2 model, loaders and training constants and writes only to new files, with a provenance string —
follow that pattern). Analysis: paired per-seed differences against Normal and each factorial cell with
paired 95% intervals; the interval helper precedent is `plan/gates/gate15_rerun/gate15_analyze.py`.

**Landing the result:** §4.6, the operation-count tables, the conclusion, and — if R6 is done — the
frontier figure. Every efficiency sentence must name its source.

---

## Phase 4 recipe — C1 all-block compression control

The control keeps the compressors and the projection ranks and removes only the selection, so it is a
flag on the selector, not a new architecture: select every index token (`k = n_idx`), which maps through
`_postprocess_topk` to all safe KV blocks.

```bash
# 1. write plan/gates/gate28_c1control/design.md FIRST: reference rows, seeds, and the D5 margin rule
# 2. implement the flag; dry run must assert selected-block count == all safe blocks for every position
~/.uv_env/py311/bin/python plan/gates/gate28_c1control/run.py --dry-run
~/.uv_env/py311/bin/python plan/gates/gate28_c1control/run.py --smoke
# 3. 25 paired seeds, new manifest
~/.uv_env/py311/bin/python plan/gates/gate28_c1control/run.py --full
```

Analysis and branch: compare against the four factorial cells and Normal with paired intervals, then take
the branch written in the design file (worse than margin / within margin / better). Update title,
abstract and conclusion only along the predeclared branch — see D4.

---

## Phase 5 recipe — R3 matched information budget (conditional)

Prerequisite: D2 frozen in `DECISIONS.md`. Steps mirror Phase 4: design file holds the filling rule and
the equality assertion; the dry run must print realized unique valid blocks per cell at equal length and
fail if they differ; only then run the 25 seeds into a new manifest (`gate29_r3budget/`), then re-estimate
the KV main effect with paired intervals and update the KV claims.

---

## Verification commands (run before calling anything done)

```bash
# manuscript hygiene: no internal names, no superseded numbers, refs and cites resolve
~/.uv_env/py311/bin/python paper/scripts/verify_manuscript.py

# paper builds
cd paper && ../tectonic -X compile main.tex

# a new number is everywhere it should be and nowhere else (replace VALUE)
grep -rn "VALUE" paper/sections paper/scripts | head
```

## Close-out checklist for every item

1. Artifact exists under a gate directory, with the analysis script beside the raw data.
2. The `.md` summary states the result and its interval, and names the branch or decision it triggers.
3. The item file's checkboxes are ticked with paths, and a dated log line is appended.
4. The dashboard row status changes in `README.md`, one line goes into
   `../pre-publication-tasks/STATUS.md`, and the **Current pointer** in the repo-root `AGENTS.md` moves if
   a phase opened or closed — that pointer is what a fresh session reads first.
5. If the manuscript changed: the check above passes, the paper rebuilds, and the reading guide is
   checked for echoes of any moved number.
