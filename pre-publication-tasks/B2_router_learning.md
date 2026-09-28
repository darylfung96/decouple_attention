# B2 — Router learning signal

Status: BLOCKING RED — B2-1 DONE (indexer DOES-NOT-LEARN) → B2-2 decision needed | Updated: 2026-09-28 | Evidence: `plan/gates/gate13_p0_audits/router_grad_audit.json/md` | Depends: none (blocks Stage-2)

Reviewer ask: scores → hard top-k + mask only → no ordinary differentiable path to indexer-exclusive params (arXiv:2002.06504). State how indexer trains; report grad norms/param changes; disclose aux loss / relaxation / STE / continuous-score use.

Current state:
- `attention.py:BaseCSAAttention.forward`: `index_scores → topk → block_bias.scatter(0/-inf) → _attend`. Scores unused elsewhere. Same in EPP (shared-Q returns main `q`, but `idx_kv_proj/idx_gate_proj/idx_position_bias/idx_norm/idx_weights_proj` only feed dead-end scores).
- No grad logging, aux loss, STE. `test_expert_plus_plus.py` checks shapes/overfit, not indexer grads.

## Tasks

- [x] **B2-1.** DONE 2026-09-28 RED — one training step (seed 42, synthetic standardized [2,256,7]→[2,96,7]): ALL indexer-exclusive grads exactly 0.000e+00, both CSA (incl. `idx_q_proj`) and DRRA; compressor + shared all nonzero. Verdict: DOES-NOT-LEARN via task loss. Evidence: `plan/gates/gate13_p0_audits/router_grad_audit.json/md` (+ `design.md` pre-reg). Env: `/opt/homebrew/bin/python3.13`, torch 2.12.1.
  - Acceptance: LEARNS / DOES-NOT-LEARN verdict per param. Blocks: B2-2, Stage-2.
- [ ] **B2-2.** If zero: (a) disclose fixed/random router + rename claims, or (b) add aux loss / relaxation / STE / continuous mixing + re-train Gate-2. Log decision in `plan/paper_notes.md`. Effort: S for (a); L for (b).
- [ ] **B2-3.** Method exact-training statement + grad norms in appendix (reproducible command).
- [ ] **B2-4.** Shared-Q vs own-`idx_q_proj` contrast (DRRA vs CSA rows).

## Log

- 2026-09-28: Created from review §B2; header added; Stage-0 blocker flagged.
- 2026-09-28: B2-1 DONE RED — hard-topk dead-end confirmed (even `idx_weights_proj` = 0). Canonical rerun under `~/.uv_env/py311` (torch 2.6.0): identical DOES-NOT-LEARN both configs. Next: B2-2 decision Q-2 ((a) disclose fixed router vs (b) redesign + re-train) — needs manager input before any Stage-2.
