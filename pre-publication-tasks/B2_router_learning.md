# B2 — Router learning signal

Status: DONE (Q-2 = disclose-fixed, 2026-09-29) | Updated: 2026-09-29 | Evidence: `method.tex` Router trainability note + limitations bullet + `router_grad_audit.json` | Depends: none

Reviewer ask: scores → hard top-k + mask only → no ordinary differentiable path to indexer-exclusive params (arXiv:2002.06504). State how indexer trains; report grad norms/param changes; disclose aux loss / relaxation / STE / continuous-score use.

Current state:
- `attention.py:BaseCSAAttention.forward`: `index_scores → topk → block_bias.scatter(0/-inf) → _attend`. Scores unused elsewhere. Same in EPP (shared-Q returns main `q`, but `idx_kv_proj/idx_gate_proj/idx_position_bias/idx_norm/idx_weights_proj` only feed dead-end scores).
- No grad logging, aux loss, STE. `test_expert_plus_plus.py` checks shapes/overfit, not indexer grads.

## Tasks

- [x] **B2-1.** DONE 2026-09-28 RED — one training step (seed 42, synthetic standardized [2,256,7]→[2,96,7]): ALL indexer-exclusive grads exactly 0.000e+00, both CSA (incl. `idx_q_proj`) and DRRA; compressor + shared all nonzero. Verdict: DOES-NOT-LEARN via task loss. Evidence: `plan/gates/gate13_p0_audits/router_grad_audit.json/md` (+ `design.md` pre-reg). Env: `/opt/homebrew/bin/python3.13`, torch 2.12.1.
  - Acceptance: LEARNS / DOES-NOT-LEARN verdict per param. Blocks: B2-2, Stage-2.
- [x] **B2-2.** DONE 2026-09-29 — Q-2 = (a) disclose-fixed. Paper: Router trainability note (`method.tex`: hard top-k → zero task gradient, fixed-at-init, granularity = architecture effects) + `idx_weights_proj` 'learned weight' → fixed-in-practice + limitations bullet. No learning claims existed to rename (grep verified). Logged here + `plan/paper_notes.md` (see log line).
- [x] **B2-3.** DONE 2026-09-29 — appendix repro lists the grad audit (`router_grad_audit.json/md` with per-param norms + rerun command in design pre-reg).
- [x] **B2-4.** DONE 2026-09-29 — contrast in method note: CSA's dedicated `idx_q_proj` and DRRA's shared-Q both receive zero task gradient (B2-1 rows for both configs).

## Log

- 2026-09-28: Created from review §B2; header added; Stage-0 blocker flagged.
- 2026-09-28: B2-1 DONE RED — hard-topk dead-end confirmed (even `idx_weights_proj` = 0). Canonical rerun under `~/.uv_env/py311` (torch 2.6.0): identical DOES-NOT-LEARN both configs. Next: B2-2 decision Q-2 ((a) disclose fixed router vs (b) redesign + re-train) — needs manager input before any Stage-2.
- 2026-09-29: Q-2 = (a) disclose-fixed. B2-2/B2-3/B2-4 DONE (method note + limitations bullet + appendix coverage). B-file COMPLETE.
