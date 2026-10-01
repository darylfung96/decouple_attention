# STATUS — where we left off (edit this every session)

Updated: 2026-09-29 (Q-2 closed; Gate15 suite in flight)
Current stage: **Gate15 suite-Flat running; v2 + paper pass next**
Source review: https://chatgpt.com/s/t_6ab8df73ca3c81919e3cc733a559fd0a
Canonical env: `~/.uv_env/py311/bin/python` (uv, torch 2.6.0) — always use uv, any project.

## DOING (max 2 at a time)

- [ ] Q-1 (partially answered: PatchTST approved + E-2 done) — remaining: approve ~30-50h Stage-2 compute.
- [x] D-5 DONE 2026-10-01 — (16,4) best-mean 0.5810, paper updated (exploratory only).

## QUEUED (unblocked, text-only, do after DOING frees up)

- (empty — v2 paper refresh committed; next text work is the D-3 analysis write-up on 60/60)

## BLOCKED (with reason + dependency)

- E-2/E-3, F-3, H-1/H-2 (Stage-2 runs; need Q-1 + venue steer in J).
- Paper v2 numbers are IN (`cb2bae5`); Q-2/Q-5 closed; B2/B1-1/A/C/G/I complete.

## DONE (with evidence — link artifact, not prose)

- [x] Stage-1 text batch: 00-1 title, C-1…C-5, D-1/D-2/D-4, G-1…G-4, I-1…I-9. Evidence: `plan/gates/gate14_c1/c1_recompute.json/md` + paper tex diffs (git-committed).
- [x] B1-5 mapping audit + fix (Q-5=(b)): `t//2` unconditional → geometry dispatch; (8,4) bitwise-identical 0.0 vs snapshot; regression test §5 passes. Evidence: `plan/gates/gate13_p0_audits/mapping_audit.json/md`, `expert_plus_plus_attention.py`, `test_expert_plus_plus.py`.
- [x] A-1 last-query equivalence — EQUIVALENT (maxdiff 0.00e+00). Evidence: `plan/gates/gate13_p0_audits/last_query_audit.json/md` + `design.md`.
- [x] A-2 canonical latency — gate PASS (~5e-7); paired + forecast-required deltas; dense-last fastest. Evidence: `plan/gates/gate13_p0_audits/last_query_latency.json/md` + `a2_b12_design.md`.
- [x] B1-2 unique blocks — effective ≈47/27 vs dense 96/48. Evidence: same `last_query_latency.json/md`.
- [x] B2-1 router grad audit — DOES-NOT-LEARN both configs (indexer grads 0.000e+00). Evidence: `plan/gates/gate13_p0_audits/router_grad_audit.json/md` + `design.md`.
- (prior gates live in `plan/gates/` — see `README.md` Provenance)

## Session log (newest first)

- 2026-10-01: Gate18 D-5 25/25 COMPLETE + paper updated. Remaining human items: Q-1 compute, J-1 venue.

- 2026-09-30: D-5 APPROVED + LAUNCHED as Gate18 (generalized mapping branch, (8,4)-identical, regression extended, ranks kept +0.535% disclosed). 25 seeds ETTh1.

- 2026-09-30: Gate17 E-2 40/40 COMPLETE + analyzed (all tied within noise; backbone-relative reading) + paper bullet. Committed.

- 2026-09-30: D-3 60/60 COMPLETE + analyzed (H1 not replicated off-ETTh1) + RQ1 paragraph written. Only Q-1/D-5 human-held; Stage-2 awaits Q-1.

- 2026-09-29: Suite 60/60 COMPLETE → v2 analysis + full paper number refresh (B-1…B-18, fig1/2/6/9 `--v2`) committed. Story: top-three tie, H1 p=0.0074, DRRA−CSA p=0.62, Flat/DRRA 4/12 best-means each.

- 2026-09-28: Q-5=(b) reviewed (essential-code-review) → fixed mapping → verified (8,4)-identical + tests pass → Gate15 launched (factorial 75 in flight; suite-Flat 60 queued). Q-2 still open.
- 2026-09-28: B1-1/A-3/A-4 DONE (algorithm box + single-block decision + repro artifacts; committed f1cf38d). A-file COMPLETE. Remaining: Gate15 monitor, Q-2, v2 number pass.
- 2026-09-28: Stage-1 text batch DONE (00/C/D/G/I). B1-5 RED found during B1-1 prep (mapping bug) — halted B1-1/A-3/A-4, decided Q-5 after report.
- 2026-09-28: A-2 DONE + B1-2 DONE (canonical 25×30 uv/torch2.6.0); two audit-script bugs fixed (A2-1/A2-2). Repo `.venv` REMOVED; always-uv rule in memory.
- 2026-09-28: A-1 GREEN + B2-1 RED (indexer grads exactly 0). First runs used homebrew python3.13/torch2.12.1; canonicalized to uv env after.
- 2026-09-28: Restructured to single-source `pre-publication-tasks/`; pointer set; headers/logs added.
