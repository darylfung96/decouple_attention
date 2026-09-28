# I — Editorial contradictions + history removal

Status: DONE (I-1…I-9 all 2026-09-28, see notes) | Updated: 2026-09-28 | Evidence: tex diffs | Depends: none

| # | Location | Flag | Fix |
|---|---|---|---|
| I-1 | §5.1 / discussion | 7/10 + significance-as-future despite 25-seed | Update to 19/25, p=0.0032 Holm context, or mark historical |
| I-2 | §4.6 / stats | "5-seed can't reach p<0.05" vs "syn significant opposite" | State exact test per claim or remove |
| I-3 | §4.3 / RQ1–RQ2 | "Beats CSA 17" ≠ "best of four 17" | Verify latter from 25-seed raw (see D-1) |
| I-4 | §4.5 / RQ3 | syn reversal must exclude change-point (externals far better) | Exclude + restate bounds |
| I-5 | Intro + conclusion | "no latency" / "FLOPs planned" vs systems results | Reconcile: IS (single-machine latency + MACs) vs deferred (cross-hw, depth/width) |
| I-6 | Whole draft | DONE roadmap, bib notes, project-history | Remove to supplement/delete; one Limitations |
| I-7 | Whole draft | Surrogate inside manuscript | Move out (separate pub; appendix pointer; H5 deferred) |
| I-8 | Whole draft | Uninit-memory failure as anti-idea evidence | Bug-fix note only unless corrected rerun |
| I-9 | Whole draft | Repeated honest/frozen/not-a-claim | One limitations + repro; normal prose elsewhere |

## Tasks

- [x] **I-1…I-9.** DONE 2026-09-28 — I-1 (§5.1→19/25 + exact p + interaction); I-2 (syn opposite-direction now exact one-sided p=0.03125 for sSin/sDC, sCP ns — verified from gate3 per-seed 0/5s); I-3 (13 vs 17 fix); I-4 (sCP excluded from inversion); I-5 (scope paragraph reconciled: latency+MACs reported w/ stance); I-6 (Roadmap→Future work, refs kept); I-7 (surrogate→pointer, label kept); I-8 (already bug-fix note, kept); I-9 (`honest`→1 keeper in limitations; `frozen` kept as protocol terminology).
  - Acceptance: `grep TODO:/NEEDS VERIFICATION` → only pre-submission author boilerplate (`main.tex:35`); `honest` → 1.

## Log

- 2026-09-28: Created from review editorial table; header added.
- 2026-09-28: I-1…I-9 DONE (see above).
