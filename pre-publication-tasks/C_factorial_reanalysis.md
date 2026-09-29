# C — Factorial reanalysis

Status: DONE (C-1…C-5 all 2026-09-28) | Updated: 2026-09-28 | Evidence: `plan/gates/gate14_c1/c1_recompute.json/md` + tex diffs | Depends: none

Reviewer ask: `ΔR − ΔKV = y4,8 − y8,4` exactly — decisive test uses only off-diagonals. Report KV main + routing main + interaction + direct DRRA-vs-equal-rate with CIs. Recompute interaction from unrounded seeds (reviewer's −0.0262 was 5-seed rounded). 2×2 replicated suffices for mixed-effects + seed blocking. Replace slogan with bounded version.

Current state: `experiments.tex RQ1` reports KV −0.0516 / routing +0.0288 + H1 +0.080, p=0.0032/0.0013 as "decisive"; `discussion.tex` has old slogan + `7/10` (stale vs `19/25`). Data: `gate2_results.jsonl` + Gate-7 25-seed + baseline.

## Tasks

- [x] **C-1.** DONE — recomputed from 25 unrounded seeds (gate2 + baseline-Normal + gate7 merge, `c1_recompute.json`): KV −0.0516 [−0.081,−0.022], routing +0.0288 [+0.006,+0.052], interaction −0.0262 [−0.071,+0.019] p=0.31 ns, H1 +0.0804 exact p=0.0023 (supersedes approx 0.0032), DRRA−CSA −0.0385 p=0.096. All paper headline values MATCH; H1≡off-diagonal identity verified (2e-16).
- [x] **C-2.** DONE — Main-effects + H1 rewritten with CIs, interaction, exact p-values; off-diagonal demoted to one of four estimates with identity stated.
- [x] **C-3.** DONE — mixed-effects deferral reason corrected (2×2 already identifies all three fixed effects; deferred as robustness re-expression) in RQ1 + appendix future-work list.
- [x] **C-4.** DONE — slogan bounded to ETTh1-range (`discussion §5.1`, abstract); intro keeps question-form only.
- [x] **C-5.** DONE — `7/10` → 19/25 with provenance (25-seed recompute); stale directional-future text rewritten.

## Log

- 2026-09-28: Created from review §C; header added.
- 2026-09-28: C-1…C-5 DONE. Note: paper's 0.0032/0.093 came from Wilcoxon approx (`gate7_stats.py:97,124`); exact values 0.0023/0.096 now quoted with method. Same conclusions.
- 2026-09-29: v2 refresh (Gate15): KV −0.0320 p=0.0096 / RT +0.0300 p=0.059 / interaction −0.0724 p=0.014 (now significant) / H1 +0.0620 p=0.0074 / DRRA−CSA +0.0042 p=0.62. Paper + fig1/2 updated; old as-run values superseded (kept in git history + `gate14_c1/`).
