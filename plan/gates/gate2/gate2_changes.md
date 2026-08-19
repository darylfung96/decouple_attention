# Gate 2 Audit Log — Strict Factorial Confirmation + Docs Freeze

Date: 2026-08-13 · Contract: `plan/gates/gate1/gate1_task.md` (frozen direct-96 task — sole authority on task definition)
Scope: docs-only freeze of Gate 2 results (no `.py` touched, no runs executed, no numbers recomputed — all numbers copied verbatim from `gate2_summary.md`).

---

## Gate 2 docs freeze (Step 5)

Docs-only pass (no code changes; python3 not run). Touched: `RESULTS.md`, `plan/next_step.md`, `gate2_changes.md` (this file).

### RESULTS.md

- Added `## Gate 2 — Post-Freeze Factorial Results (2026-08-13)` section at end of file (after all pre-freeze EPP/related sections; the `⛔ TASK FREEZE NOTICE (Gate 1, 2026-08-11)` block at top untouched; no pre-freeze number relabeled as current):
  - one-line method pointer (5 paired seeds, 10 epochs, param-equalized ≤0.5%, direct 96-step frozen task; details in `gate2_design.md`);
  - 4-cell aggregate table (cell | val mean±std | test mean | train mean) — numbers copied verbatim from `gate2_summary.md`;
  - main effects c_KV = −0.0427 (coarser KV compression lowers val MSE) and c_R = +0.0463 (coarser routing raises val MSE), with sign meaning;
  - champion (8,4) — mean val 0.5967 / mean test 0.7988, attn 95,652 / full 348,356, matching the EPP champion corner (coarse-KV `compress_rate=8` / fine-routing `index_compress_rate=4`);
  - H1 verdict copied verbatim from `gate2_summary.md`, incl. the explicit hedge (effects ~0.04 < seed-to-seed std 0.0647; consistent but not unanimous; directional only; no formal significance test run).
- No speculative prose or recommendations beyond the verdict.

### plan/next_step.md

- §4 (Gate 2) — all 4 checkboxes marked `[x]` + `✅ Gate 2 DONE (2026-08-13)` blockquote appended after the checklist, in the same style as §§1–3. §5+ untouched.

## Files touched

- `RESULTS.md` (edited — new Gate 2 section appended at end)
- `plan/next_step.md` (edited — §4 marked done)
- `gate2_changes.md` (this file, created)

(SHA-256 manifest: `plan/gates/gate0/gate0_manifest.json` covers Gate-0 registry files only; no manifest exists for Gate-2 artifacts — paths recorded only, no hashes computed.)

## Reference

- Frozen task: `plan/gates/gate1/gate1_task.md` (sole authority on task definition)
- E4 audit: aggregation in `gate2_summary.md` §Data integrity — all checks **PASS** (param equalization vs (8,4) ref: max attn delta 0.2676%, max full delta 0.0735%, all < 0.5%; training matched: final train MSE span 0.0181 ≤ 0.02; all 20/20 rows present, no duplicates)
