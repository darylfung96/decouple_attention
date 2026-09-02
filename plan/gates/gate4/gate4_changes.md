# Gate 4 — Changes / Audit Log (minimal statistical pass)

- **2026-08-25 · Scope decision (user).** Full pre-registered Gate 4 (next_step.md §8) reduced to a **minimal analysis-only pass** on the existing 180 Gate-3 runs. User question ("can we skip Gate 4?") answered with evidence: per-dataset significance is impossible at n=5 (two-sided floor p=0.0625) and the cross-dataset sign test is not significant (8/12 → p=0.39) — skipping entirely would leave reviewers to recompute these; the minimal pass reports them and pre-empts that.
  - Deferred with written justification (in `gate4_stats.md` and `next_step.md` §8): mixed-effects model (2×2 factorial exists only on ETTh1 at n=5; adds little until more cells×seeds), HAC/block bootstrap (analysis is at the seed level — 5 independent paired runs — so stride-1 window overlap does not invalidate paired tests), TOST/ROPE (no equivalence claims are made).
  - Optional strengthening noted: +5 seeds on headline cells (~8 h compute) lowers the floor to p=0.002.

- **2026-08-25 · Artifacts.**
  - `plan/gates/gate4/gate4_stats.py` — exact paired Wilcoxon (scipy, method="exact") per dataset × 3 comparisons on val MSE; Holm correction across 36 tests; cross-dataset binomial sign tests (mean val and mean test, 12 datasets); 10,000-resample bootstrap 95% CI on the mean of per-dataset Δval vs Normal; writes `gate4_stats.json` + `gate4_stats.md`.
  - **Fix:** REPO_ROOT off-by-one dirname (landed on `plan/`) — corrected to 4 levels.
  - Results: no test survives Holm (all corrected p = 1.0000); raw closest: etth1 0.0625, solar 0.0625 (DRRA better), syn_sinusoids/syn_delayedcopy 0.0625 (Normal better — wrong direction); cross-dataset sign tests DRRA vs Normal val 8/12 p=0.3877, test 8/12 p=0.3877, Flat val 7/12 p=0.7744; bootstrap mean Δval: Flat −8.93% [−16.79, −2.17], DRRA −8.26% [−17.50, −0.83] (both exclude 0).

- **2026-08-25 · Docs + paper.**
  - `plan/next_step.md` §8: 3 checkboxes done (seeds+CI reporting, Wilcoxon+Holm, multi-dataset tests), 2 deferred with justification, 1 dropped (TOST/ROPE); ✅ blockquote with artifacts + headline.
  - `plan/paper_notes.md`: §7 Gate-4 item done + changelog entry.
  - Paper: new "Statistical treatment" subsection (experiments.tex, label sec:stats) reporting the tests, the n=5 floor, p=0.39/0.77, and the CIs; RQ1's mixed-effects \todo reworded to a deferred-item sentence; discussion "Descriptive statistics" limitation updated; abstract updated ("per-dataset paired tests cannot reach significance — two-sided floor p=0.0625").
  - Recompiled: exit 0, 12 pages, only pre-existing underfull-hbox; PDF verified (sec:stats text, values).

- **2026-08-25 · Consistency fix (user-reported).** The "Non-IID samples" limitation item still carried `\todo{Gate 4: block bootstrap / HAC-robust tests}` — missed when the minimal Gate-4 pass rewrote the other Gate-4 markers. Converted to a deferred-work sentence consistent with Section sec:stats (seed-level paired tests are not invalidated by window overlap; HAC/block bootstrap deferred until per-window statistics). Verified: zero `\todo{Gate 3/4 ...}` markers remain in paper/sections/ (grep exit 1); remaining TODOs are legitimately pending (Gate 5 ×3, H1–H5, H4, retention, freeze-clean). Recompiled clean (exit 0, only pre-existing underfull-hbox); fix verified in main.pdf.
