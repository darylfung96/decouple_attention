# Pre-publication tasks — index (SINGLE SOURCE OF TRUTH)

Source review: https://chatgpt.com/s/t_6ab8df73ca3c81919e3cc733a559fd0a
Old master `plan/manager_review_revision_checklist.md` is a pointer — do not edit it.
Created: 2026-09-28

Reviewer verdict (gist): publishable idea (separate compression amount from routing granularity); do NOT submit yet; reframe as design study, fix method + stats first.

Status legend: `[x]` DONE · `[~]` PARTIAL · `[ ]` TODO · `[!]` BLOCKING

## Workflow (anti-confusion rules — follow every session)

1. **Resume here:** read `STATUS.md` first (it is the only "where left off").
2. **One task, one file:** edit ONLY the task file you're working + `STATUS.md`. Never copy content between files.
3. **Close the loop:** ticking `[ ]` → `[x]` requires an Evidence path (artifact JSON/md or paper file:line). No evidence = stays open.
4. **Log it:** append one line to `STATUS.md` Session log + the task file's `Log:` footer with date + what changed.
5. **Max 2 DOING:** move anything else back to TODO. Blocked items stay in BLOCKED with reason + dependency ID.
6. **IDs are stable:** `00`, `A`, `B1`, `B2`, `C`, `D`, `E`, `F`, `G`, `H`, `I`, `J`. Never rename; sub-tasks append `-N` (e.g. `A-1`).
7. **No silent scope growth:** new work gets a new sub-ID + acceptance line, never an untracked checkbox edit elsewhere.
8. **Manuscript hygiene:** no internal names in `paper/` — no Gate-N, Stage-N, `plan/` paths, Q-N, or tracking shorthands. Use the paper's convention (`released with the source`). Check before every paper commit:
   `grep -rni "gate-1[0-9]\\|stage-[01]\\|plan/\\|pre-publication\\|Q-[0-9]" paper/sections/ paper/main.tex` → must be empty.

## Dashboard

| ID | File | Status | Notes |
|---|---|---|---|
| 00 | `00_title.md` | `[x]` DONE | Locked: Decoupling Compression and Routing… |
| A | `A_last_query_audit.md` | `[~]` PARTIAL | A-1/A-2 DONE; A-3/A-4 QUEUED |
| B1 | `B1_operator_spec.md` | `[!]` BLOCKING-RED→FIXED | B1-5 fixed, Gate15 running; B1-1 QUEUED; B1-3 blocked on Q-2 |
| B2 | `B2_router_learning.md` | `[!]` BLOCKING | B2-1 RED; Q-2 decision open |
| C | `C_factorial_reanalysis.md` | `[x]` DONE | C-1…C-5; numbers flagged for v2 refresh post-Gate15 |
| D | `D_decoupling_vs_compression.md` | `[~]` PARTIAL | D-1/D-2/D-4 DONE; D-3 blocked |
| E | `E_backbone_controls.md` | `[ ]` TODO | Stage-2 |
| F | `F_validation_test_primary.md` | `[ ]` TODO | Stage-2 |
| G | `G_efficiency.md` | `[x]` DONE | G-1…G-4 |
| H | `H_citability.md` | `[ ]` TODO | Stage-2/3; gate12 Flat probes need post-fix rerun |
| I | `I_editorial.md` | `[x]` DONE | I-1…I-9 |
| J | `J_venue.md` | `[ ]` TODO | After Q-2 + Gate15 |

## Execution order (dependencies)

- **Stage 0 — audits:** A-1/A-2/B2-1/B1-2/B1-5 DONE (designs + JSONs in `gate13/`).
- **Stage 1 — analysis/text:** 00/C/D-terminology+test-side/G/I DONE (C-1 in `gate14/`).
- **Gate15 — option-(b) re-run (IN FLIGHT):** broken cells only (factorial 75 → suite-Flat 60), then v2 analysis + paper number refresh.
- **Stage 2 — targeted runs (needs Q-2 + Gate15 v2):** B1-3 control, D-3-cell factorial, E-controls, F-H/L, H-probes (+ gate12 Flat-probe reruns).
- **Stage 3 — venue-dependent:** E-backbone, H-sweep, repo release, J-lock.

Open decisions: **Q-2** router (disclose-fixed vs redesign) · **Q-5** DONE = option (b) fix+rerun.

## Provenance (read these, don't re-derive)

- Task: `plan/gates/gate1/gate1_task.md` · Params: `plan/gates/gate0/gate0_registry.json`
- Gate-2: `plan/gates/gate2/gate2_design.md`, `gate2_results.jsonl`, `gate2_summary.md`
- Gate-7 25-seed: `plan/gates/gate7_seeds/results/`, `paper/sections/experiments.tex` RQ1
- Baseline: `plan/gates/baseline/baseline_normal_results.jsonl`, `baseline_normal_summary.md`, `normal_sanity_check.md`
- Coverage: `plan/gates/gate3/results/*.jsonl`, `gate3_summary.md`
- Stats: `plan/gates/gate4/gate4_stats.py/.md/.json`
- Systems: `plan/gates/gate5/gate5_results.json`, `gate5_summary.md`, `plan/gates/gate3/gate3_latency*.json`
- Mechanistic: `plan/gates/gate12/gate12_results.json`, `gate12_summary.md`, `checkpoints/` (Flat checkpoints STALE post-fix — rerun flagged)
- Refpoints: `plan/gates/gate6_baselines/results/`, `gate6_summary.md`, `gate6_facts.json`
- Code: `model.py`, `attention.py`, `expert_plus_plus_attention.py` (mapping FIXED 2026-09-28 — see B1-5)
- Audits (this round): `plan/gates/gate13_p0_audits/` (design, A-1, B2-1, A-2+B1-2, B1-5 mapping)
- Recompute: `plan/gates/gate14_c1/c1_recompute.json/md` (as-run v1; v2 after Gate15)
- Re-run: `plan/gates/gate15_rerun/` (design + driver + results; old manifests NEVER modified)
- Paper: `paper/main.tex`, `paper/sections/{method,experiments,discussion,appendix}.tex`, `paper/scripts/make_figures.py`
