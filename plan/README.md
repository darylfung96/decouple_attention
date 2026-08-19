# plan/ — project planning & paper-prep notes

**Main file: [`paper_notes.md`](paper_notes.md)** — the living novelty & paper-prep ledger
(statuses, evidence pointers, checklist, changelog). Start here; everything else below supports it.

## Supporting ledgers

| File | What it is |
|---|---|
| `paper_notes.md` | **MAIN.** Novelty-claims ledger (C1–C5), open items, changelog |
| `lit_audit.md` | Citation/literature audit status (§1 citation ledger, §2 claims, §4 re-audit checklist) |
| `next_step.md` | What to do next, in order (gates, pre-submission tasks) |
| `REPRO.md` | How to reproduce the experiments |
| `benchmark_protocol.md` | Benchmark / speed-measurement protocol |

## Gate & baseline records (`gates/`)

- `gates/gate0/` — registry & change records (parameter counts, manifest; `build_manifest.py`, `gen_registry.py`, `rename_changes.md`)
- `gates/gate1/` — task freeze + causality checks (`gate1_task.md`, `gate1_causality.py`, `gate1_gradmask.py`, `_gate1_common.py`, reports)
- `gates/gate2/` — factorial sweep: design, results (`gate2_summary.md`, `gate2_results.jsonl`, learning curves), `gate2_factorial.py`, `run_gate2_sweep.sh`
- `gates/baseline/` — Normal-attention baseline runs (`baseline_normal_*`) + sanity checks (`normal_sanity_check.md`, `check_normal_wiring.py`)

## Archived mini-tasks

- [`mini_tasks/c2/`](mini_tasks/c2/) — **C2 claim verification** (2024–2026 routing/compression-attention literature sweep):
  `2026-08-16-c2-lit-sweep.md` (plan), `c2_sweep_log.md` (evidence log, 29 rows),
  `dsv4_csa_read.md` / `nsa_read.md` (full-text reads), `c2_decision_brief.md` (rubric + KEEP decision),
  `c2_sweep_cache/` (raw sweep data), plus the `_c2_*.py` tooling.
