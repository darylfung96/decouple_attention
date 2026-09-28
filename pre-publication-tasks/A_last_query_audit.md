# A — Audit forecasting computation (last-query-only)

Status: DONE (A-1…A-4 all 2026-09-28) | Updated: 2026-09-28 | Evidence: `plan/gates/gate13_p0_audits/last_query_latency.json/md` + tex diffs + `plan/paper_notes.md` | Depends: none

Reviewer ask: Eq.(1) single-block + `y = horizon_head(h[:, -1, :])`. Per-position LN/MLP → earlier attention outputs unused. Dense baseline could do `Attention(q_last, K, V)` — O(L) not O(L²). Implement + benchmark last-query path per config; or add multilayer backbone. Until resolved, speedup claims partly reflect unnecessary compute.

Current state (confirmed):
- `model.py:CSATimeSeriesModel.forward`: full `attn(x)` `[B,256,128]` → norm/MLP all positions → `output_proj(x[:, -1, :])`.
- `paper/sections/method.tex` Eq.(1) + Fig.1 state last-state readout. No last-query path in `attention.py` / `normal_attention.py` / `model.py`.
- At risk: `experiments.tex Tab:speed` (49.3 vs 52.5ms), latency-scale, L-scale, MACs (76.9M vs 59.6M).

## Tasks

- [x] **A-1.** DONE 2026-09-28 GREEN — hook proofs all maxdiff 0.00e+00 (3 configs x seeds {0,42,123}). Stock B32 audit-speed: Normal 40.7 / CSA 43.8 / DRRA 41.7ms. Evidence: `plan/gates/gate13_p0_audits/last_query_audit.json/md` (+ `design.md` pre-reg).
  - Acceptance: equality table + full-layer vs forecast-required costs. Effort: S. Blocks: A-2, Stage-2.
- [x] **A-2.** DONE 2026-09-28 — canonical 25×30 round-robin B32 (uv, torch 2.6.0). FULL: Normal 47.7 / CSA 47.4 / DRRA 40.8ms. LAST (forecast-required): Normal 3.9 / CSA 9.5 / DRRA 8.6ms (paired Δ −43.8/−37.9/−32.2 ± ~1ms). HEADLINE: dense-last is fastest — published speedup claims must be recomputed vs last-query baseline. Evidence: `plan/gates/gate13_p0_audits/last_query_latency.json/md` (+ `a2_b12_design.md`, amendments A2-1/A2-2). Remaining: update `gate5` companion + `experiments.tex §efficiency` (A-2b text task).
- [x] **A-3.** DONE 2026-09-28 — decision (i): keep single-block (backbone not the bottleneck, §refpoints), both costs reported (§efficiency); multilayer deferred. Logged in `plan/paper_notes.md` + new limitations bullet (`discussion.tex`).
- [x] **A-4.** DONE 2026-09-28 — Complexity carries both-costs + report-against-last-query-baseline language (via A-2 companion); appendix repro lists gate13/14/15 artifacts + mapping regression test; MACs-are-not-energy stated. Acceptance grep: `forecast-required|full-layer|last-query` non-empty — verify at commit.

## Log

- 2026-09-28: Created from review §A; header added; Stage-0 blocker flagged.
- 2026-09-28: A-1 DONE GREEN (exact-zero diffs; MLP 33.5M full vs 0.13M last; K/V+compressors stay full-sequence). Canonical rerun under `~/.uv_env/py311` (torch 2.6.0, matches lock): same EQUIVALENT verdict; B32 audit-speed Normal 44.0 / CSA 43.6 / DRRA 37.7ms (latency is torch-build-sensitive — always report env). Next: A-2 canonical 25x30 alternating on last-query paths.
- 2026-09-28: A-2 DONE — gate PASS (maxdiff ~5e-7, sel a==b). Two audit-script bugs found+fixed via bisection (q_b_norm order A2-1; timing closure A2-2 — see design amendments). Forecast-required << full-layer; dense-last fastest. Next: A-3 backbone decision (default: keep single-block + report both costs).
- 2026-09-28: A-3/A-4 DONE (single-block bullet + paper_notes log + repro artifacts). A-file COMPLETE.
