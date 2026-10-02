# HANDOVER — state of the pre-publication revision (2026-10-01)

## One-paragraph summary for the next owner

The review asked for a design-study reframing plus audits. All P0 audits are done,
two real bugs were found and fixed (unconditional `t//2` misrouting; zero-gradient
router, now disclosed), every affected run was redone (Gate15: 75 + 60 runs), and the
manuscript carries corrected numbers, redrawn figures, and honest limits. Two
exploratory probes ((16,4), (32,4)) and a 60-run cross-dataset replication plus a
40-run backbone transfer are also done and written up.

## Are the remaining runs necessary for publication?

No. The manuscript as committed is a complete, sound, bounded study:
single-dataset factorial + 12-dataset suite + reference anchors + disclosed limits.
That clears the bar for a soundness-first venue (Scientific Reports) or an
applications venue (NCA). The remaining runs (B1-3, E-3, F-3, H probes) buy
GENERALIZABILITY, not validity — they matter for Neurocomputing-level ambition
or if a reviewer demands them in round one. Recommendation: submit bounded now;
run Stage-2 only on reviewer request (all designs/harnesses are ready to launch).

## Open decisions (for the manager, not the code)

- Q-1 (remainder): approve ~30–50 CPU hours IF Stage-2 is wanted. Q-1's backbone
  half is done (PatchTST transfer complete, tied within noise).
- J-1: venue pick (Sci Rep bounded now vs Neurocomputing after Stage-2).

## How to resume (commands from repo root, uv env `~/.uv_env/py311/bin/python`)

- Check a run: `tail -n 3 plan/gates/<gate>/...run.log`, `pgrep -f <script>`.
- Resume any idempotent driver: rerun the same command (completed rows are skipped).
- v2 numbers: `plan/gates/gate15_rerun/gate15_analysis.json` (factorial + suite).
- D-3: `plan/gates/gate16_d3/gate16_analysis.json`. E-2: `plan/gates/gate17_e2/gate17_analysis.json`.
- Figures: `~/.uv_env/py311/bin/python paper/scripts/make_figures.py --v2` (default mode
  regenerates as-run figures — do NOT run bare unless intending that).
- Hygiene before every paper commit:
  `grep -rni "gate-1[0-9]\|stage-[01]\|plan/\|pre-publication\|Q-[0-9]" paper/sections/ paper/main.tex`
  must be empty. LaTeX balance check: `/tmp/bal.py`.
- Tracking: `pre-publication-tasks/STATUS.md` (resume point) + letter files (single source
  of truth); `pre-publication-tasks/progress.html` (manager-readable page).
- Git: 20+ commits, small and labeled; old manifests never modified (corrections live in
  gate15/16/17/18/19 dirs). Only uncommitted file should be `paper/main.pdf`
  (pre-existing local build artifact).

## Key facts the next owner must not re-derive

- Canonical env: `~/.uv_env/py311/bin/python` (torch 2.6.0). Repo `.venv` was removed.
- (8,4)/Normal old runs were kept (mapping fix verified bitwise-identical, diff 0.0).
- Router is disclosed fixed-at-init (zero task gradient); learning-to-route deferred.
- Forecast cost is reported both ways; dense-last is fastest (3.5 ms vs 6–9 ms).
- (16,4) best-mean 0.5810 and (32,4) 0.6122 are EXPLORATORY (out of confirmatory tables).
- H1 survives on ETTh1 (p=0.0074) but not off it (D-3) — the paper says ETTh1-only.
