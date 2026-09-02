# Gate 12 — Changes / Audit Log (mechanistic analyses)

- **2026-08-27 · Scope + execution start (user: "continue to finish the rest off").**
  - Goal: clear the last paper TODO — the H4/§12 mechanistic analysis (`experiments.tex`: "mechanistic analysis of what the router attends to; change-point/event-based analyses").
  - Feasibility note: the Gate-3 sweep did not save checkpoints, so router-internal analyses (routing recall vs full-attention mass, route entropy) would require instrumenting the untouched attention modules. Scope chosen instead — analyses that work from model outputs and existing runs, plus fresh checkpoint-saving retrains:
    1. **Lag-resolved per-channel error** on syn_delayedcopy (channels 0–4 = periodic lags {96,128,168,224,256} = exact-offset copy targets; channels 5–6 = noise floor) per model — tests exact in-window offset recall (H4/H2 mechanism).
    2. **Change-point distance stratification** on syn_changepoints — per-window test MSE bucketed by rows-since-last-level-change at forecast start (0–100/100–500/500–1000/1000–2000) — tests post-change adaptation by recency weighting.
    3. **Signal-dependence correlation (H4, cross-dataset)** — per-dataset lag-1 autocorrelation and roughness of the standardized train split vs per-dataset Δval% vs Normal (from the Gate-3 runs); Pearson + Spearman across 12 datasets.
  - Training: Normal/(4,4)/(8,4) × {syn_delayedcopy, syn_changepoints} × seed 42, frozen protocol (10 epochs), checkpoints saved to `plan/gates/gate12/checkpoints/`.
  - Deferred (needs attention-module instrumentation or out of scope): routing recall vs full-attention mass, route entropy/stability, compressed-KV content distortion, mediation analysis.

- **2026-08-28 · Analyses complete + paper updated.**
  - Results (corrected normalization — see bug note above): (1) delayed-copy per-channel: ALL models solve the exact-offset copy (copy MSE 0.0007 Normal / 0.0013–0.0026 (4,4) / 0.0013–0.0026 (8,4) vs noise floor ≈1.05; Normal ~2× more precise; mild lag gradient for compressed cells — larger lags slightly harder); (2) change-point distance: (8,4) lowest error in every bucket; bucket gradient confounded by generator random-walk drift (documented, not over-read); (3) H4 signal-dependence: compression advantage correlates with signal smoothness in the predicted direction (Pearson r = −0.29 (8,4) / −0.35 (4,4) vs lag-1 autocorr, p ≈ 0.3, n=12) — descriptive.
  - Paper: RQ2 mechanistic-probe paragraph replaces the H4 TODO (experiments.tex). next_step.md §12: 2 of 6 analyses done, 4 deferred (routing recall / content distortion / attention entropy / mediation need attention-module instrumentation — checkpoints now saved in gate12/checkpoints/ for that future work).
  - **The paper is now TODO-free** (all 8 markers resolved: Gate-1 citation → in-text statement; windows-overlap note → plain text; H1–H5 status → inline paragraph; H4 → mechanistic probes; surrogate retention → decision recorded; freeze-clean → package documented; Gate-5 remainders ×2 → scope exclusions).
  - Recompiled: exit 0, 15 pages, only pre-existing underfull-hbox; PDF verified.
