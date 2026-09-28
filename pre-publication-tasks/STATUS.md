# STATUS — where we left off (edit this every session)

Updated: 2026-09-28 (option-b fix verified; Gate15 re-run in flight)
Current stage: **Gate15 re-run (option b) + Q-2 open**
Source review: https://chatgpt.com/s/t_6ab8df73ca3c81919e3cc733a559fd0a
Canonical env: `~/.uv_env/py311/bin/python` (uv, torch 2.6.0) — always use uv, any project.

## DOING (max 2 at a time)

- [ ] Gate15 re-run in flight: factorial 75 (`plan/gates/gate15_rerun/gate15_run.log`, pid 23972, 7/75 at last check) — monitor + resume if dies; then suite-Flat 60 via `--suite-flat`.
- [ ] Q-2 / B2-2 router decision: disclose-fixed vs redesign (`B2_router_learning.md`) — NEEDS MANAGER INPUT (blocks Stage-2 text pass + D-3).

## QUEUED (unblocked, text-only, do after DOING frees up)

- (empty — B1-1/A-3/A-4 completed 2026-09-28; next text work is the v2 number pass after Gate15 + Q-2)

## BLOCKED (with reason + dependency)

- B2-3/B2-4 (need Q-2 decision) · D-3 60-run factorial (needs Q-2 AND gate15 v2) · E-2/E-3, F-3, H-1/H-2 (Stage-2 runs; need Q-2 + venue steer in J).
- Paper RQ1/H1/D-2 number updates (need gate15 v2 analysis — current tex numbers are as-run under the old mapping; flagged, not silently kept).
- v2 refresh execution (plan: `plan/gates/gate15_rerun/v2_refresh_plan.md` — A-1…A-4 outputs, B-1…B-18 paper/figure updates, C figs, D no-change list, E decision checkpoint; runs after Gate15 completes + Q-2).

## DONE (with evidence — link artifact, not prose)

- [x] Stage-1 text batch: 00-1 title, C-1…C-5, D-1/D-2/D-4, G-1…G-4, I-1…I-9. Evidence: `plan/gates/gate14_c1/c1_recompute.json/md` + paper tex diffs (git-committed).
- [x] B1-5 mapping audit + fix (Q-3=(b)): `t//2` unconditional → geometry dispatch; (8,4) bitwise-identical 0.0 vs snapshot; regression test §5 passes. Evidence: `plan/gates/gate13_p0_audits/mapping_audit.json/md`, `expert_plus_plus_attention.py`, `test_expert_plus_plus.py`.
- [x] A-1 last-query equivalence — EQUIVALENT (maxdiff 0.00e+00). Evidence: `plan/gates/gate13_p0_audits/last_query_audit.json/md` + `design.md`.
- [x] A-2 canonical latency — gate PASS (~5e-7); paired + forecast-required deltas; dense-last fastest. Evidence: `plan/gates/gate13_p0_audits/last_query_latency.json/md` + `a2_b12_design.md`.
- [x] B1-2 unique blocks — effective ≈47/27 vs dense 96/48. Evidence: same `last_query_latency.json/md`.
- [x] B2-1 router grad audit — DOES-NOT-LEARN both configs (indexer grads 0.000e+00). Evidence: `plan/gates/gate13_p0_audits/router_grad_audit.json/md` + `design.md`.
- (prior gates live in `plan/gates/` — see `README.md` Provenance)

## Session log (newest first)

- 2026-09-28: Q-3=(b) reviewed (essential-code-review) → fixed mapping → verified (8,4)-identical + tests pass → Gate15 launched (factorial 75 in flight; suite-Flat 60 queued). Q-2 still open.
- 2026-09-28: B1-1/A-3/A-4 DONE (algorithm box + single-block decision + repro artifacts; committed f1cf38d). A-file COMPLETE. Remaining: Gate15 monitor, Q-2, v2 number pass.
- 2026-09-28: Stage-1 text batch DONE (00/C/D/G/I). B1-5 RED found during B1-1 prep (mapping bug) — halted B1-1/A-3/A-4, decided Q-3 after report.
- 2026-09-28: A-2 DONE + B1-2 DONE (canonical 25×30 uv/torch2.6.0); two audit-script bugs fixed (A2-1/A2-2). Repo `.venv` REMOVED; always-uv rule in memory.
- 2026-09-28: A-1 GREEN + B2-1 RED (indexer grads exactly 0). First runs used homebrew python3.13/torch2.12.1; canonicalized to uv env after.
- 2026-09-28: Restructured to single-source `pre-publication-tasks/`; pointer set; headers/logs added.
