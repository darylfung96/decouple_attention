# Pre-publication tasks — index (SINGLE SOURCE OF TRUTH)

> **Scope note (2026-10-16).** This folder owns the **bounded paper** — the study as it stands.
> The manager's Q1 review of 2026-10-16 opened a second, larger program (the review's R1–R8 items plus
> the P1 controls, the generalization matrix, systems/energy evidence and positioning work). That
> program is tracked in **`../pre-publication_v2_tasks/`**, whose README is its dashboard and whose
> `BASELINE.md` records what the 2026-10-16 pass already fixed here. Nothing in the v2 folder blocks
> submitting the bounded paper.

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
6. **IDs are stable:** `00`, `A`, `B1`, `B2`, `C`, `D`, `E`, `F`, `G`, `H`, `I`, `J`, `K`. Never rename; sub-tasks append `-N` (e.g. `A-1`).
7. **No silent scope growth:** new work gets a new sub-ID + acceptance line, never an untracked checkbox edit elsewhere.
8. **Manuscript hygiene:** no internal names in `paper/` — no Gate-N, Stage-N, `plan/` paths, Q-N, or tracking shorthands. Use the paper's convention (`released with the source`). Check before every paper commit:
   `grep -rni "gate-1[0-9]\\|stage-[01]\\|plan/\\|pre-publication\\|Q-[0-9]" paper/sections/ paper/main.tex` → must be empty.

## Dashboard

| ID | File | Status | Notes |
|---|---|---|---|
| 00 | `00_title.md` | `[x]` DONE | Locked: Decoupling Compression and Routing… |
| A | `A_last_query_audit.md` | `[x]` DONE | A-1…A-4 in paper (both costs, single-block kept) |
| B1 | `B1_operator_spec.md` | `[x]` DONE-text (B1-3 runs deferred) | B1-1/B1-2/B1-5 in paper; B1-3 matched-budget Stage-2 |
| B2 | `B2_router_learning.md` | `[x]` DONE | Disclose-fixed (Q-2 closed) in method + limitations |
| C | `C_factorial_reanalysis.md` | `[x]` DONE | C-1…C-5 + v2 in paper (KV -0.0320, RT +0.0300, int -0.0724, H1 p=0.0074) |
| D | `D_decoupling_vs_compression.md` | `[x]` DONE (promotion deferred) | D-1…D-5 + Gate19 + D-3 (ETTh1-only) in paper; independent replication Stage-2 |
| E | `E_backbone_controls.md` | `[~]` PARTIAL | E-2 (40/40 + speed 1.11x/1.27x + figure) in appendix; E-3/E-4 Stage-2 |
| F | `F_validation_test_primary.md` | `[ ]` DEFERRED-BY-DESIGN | Val-headlined with test alongside; F-1/F-2/F-3 Stage-2; F-4/F-5 sentences in |
| G | `G_efficiency.md` | `[x]` DONE | G-1…G-4 |
| K | `K_scaling_energy.md` | `[x]` DONE | Scaling forecast + energy projection (main text §4.8 + App. D); manager request |
| H | `H_citability.md` | `[ ]` DEFERRED-BY-DESIGN | Descriptive stance + means-only disclosure in paper; H-1/H-2/H-4-bars Stage-2 |
| I | `I_editorial.md` | `[x]` DONE | I-1…I-9 |
| J | `J_venue.md` | `[ ]` TODO | Venue pick (J-1) + Q-1/Q-3/Q-6 open; bounded draft fits workshop/Sci Rep/NCA |
| K | `K_scaling_energy.md` | `[x]` DONE | Scaling forecast + energy projection (§4.8 + App. D) + K-7 accounting recheck (2026-10-16) |
| L | `L_q1_review_triage.md` | `[x]` DONE | 2026-10-16 Q1-review triage: 3 items already fixed, 3 wording/scope fixes, 2 numerical fixes; new-run program deferred to Q-6 |

## Execution order (dependencies)

- **Stage 0 — audits:** A-1/A-2/B2-1/B1-2/B1-5 DONE (designs + JSONs in `gate13/`).
- **Stage 1 — analysis/text:** 00/C/D-terminology+test-side/G/I DONE (C-1 in `gate14/`).
- **Gate15 — option-(b) re-run (COMPLETE):** factorial 75 + suite-Flat 60; v2 analysis + paper refresh committed.
- **D-3 (COMPLETE):** 4 cells x 3 datasets x 5 seeds = 60/60; H1 ETTh1-only; in RQ1.
- **E-2 (COMPLETE incl speed):** 40/40 + 25x30 speed (DRRA 1.11x, C88 1.27x) + Fig transfer-speed; in appendix.
- **D-5/Gate19 (COMPLETE):** (16,4) + (32,4) 25/25 exploratory; starred in Table 2/Fig 1; promotion replication deferred.
- **Stage 2 — deferred runs (needs Q-1 + J):** B1-3 control, E-controls, F-H/L + MAE, H-probes + bars, promotion replication (+ gate12 Flat-probe reruns).
- **Stage 3 — venue-dependent:** E-backbone, H-sweep, repo release, J-lock.

Open decisions: **Q-1** Stage-2 compute (~30-50h, only for Neurocomputing-track) · **Q-3** venue ambition · Q-2/Q-4/Q-5 CLOSED.

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
