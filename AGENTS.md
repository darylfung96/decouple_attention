# Project instructions — new_attention

Written 2026-10-16. Keep this file short: it is loaded into every session, so it points at owners
instead of restating them.

## Session resume ritual (do this first, in order)

1. Read `pre-publication-tasks/STATUS.md` — the live resume point: what was last done, what is blocked.
2. For the review program, read `pre-publication_v2_tasks/README.md` (dashboard), then
   `EXECUTION_PLAN.md` (the phase to work in), then the task file, then `RUNBOOK.md` for the exact
   commands. Take the first unchecked step of the earliest incomplete phase.
3. Before starting any run, check `pre-publication_v2_tasks/DECISIONS.md`. A decision that shapes a run
   must be frozen there first, and D5 (the non-inferiority margin) has no safe default.

## Two workstreams, do not confuse them

- **Bounded paper** — submittable today: `paper/`, tracked in `pre-publication-tasks/`.
- **Review program** — the R/C/S items: `pre-publication_v2_tasks/`. Nothing in it blocks the bounded
  submission except S1 (submission packaging).
- `HANDOVER.md`, `PUBLICATION.md`, `RESULTS.md` and `WRITEUP.md` are dated history or pre-freeze
  material, not status. Status lives in the two tracker folders.

## Hard rules

- **Environment:** always `~/.uv_env/py311/bin/python`. Never system python.
- **Paper hygiene:** no gate numbers, plan paths, stage names or task IDs inside `paper/`.
- **Numbers:** superseded values never stay in `paper/`; update the owning section first, then the
  derived echoes (tables, captions, abstract, reading guide). Run
  `~/.uv_env/py311/bin/python paper/scripts/verify_manuscript.py` before calling any manuscript change
  done, and rebuild with `cd paper && ../tectonic -X compile main.tex`.
- **Experiments:** reuse the fixed 25 paired seeds; one new variable per run; new run gets a new
  `plan/gates/<NN>_<slug>/` directory with a pre-written `design.md`; historical manifests and gate
  outputs are append-only and are never overwritten; every run ships its analysis script and a short
  `.md` stating the result and its interval.
- **Evidence or it is not done:** every closed checkbox needs an artifact path.
- **One task, one file:** log one dated line in the task file and one in `pre-publication-tasks/STATUS.md`
  when a session ends.
- **Facts and settled choices** go to durable memory (owner file first, then re-index), not into this
  file.

## Current pointer (update when a phase closes)

- **Next actions:** Phase 1 (S1 submission packaging — no-input drafts are in the S1 file; needs author
  names/affiliations, code license, release tag, CRediT roles) and Phase 3 (R2 projection-matched dense,
  ~3–4 h). **Phase 2 is complete**: R5 probes regenerated + causality suite, R6 figure, R4 route probe,
  C4 MoBA all landed and verified.
- **Then:** Phase 4 (C1 all-block control, needs D5 frozen) → Phase 5 (R3, only if D1 turns high-aim) →
  Phase 6 (R7 narrowing).
- **Open decisions:** D5 margin (no safe default; before Phase 4), D6 R7 handling, D7 MAE. D1 = Option A
  is closed. Venue call (Q-6) still open; D1's stop rule after M2 is to stop after Phase 3 and submit
  the narrowed paper.
- Last updated: 2026-10-16.
