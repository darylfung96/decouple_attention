# K — Scaling forecast + energy projection (manager request)

Status: DONE (K-1…K-7, 2026-10-16) | Updated: 2026-10-16
Evidence: `paper/figures/fig12_scaling_forecast.{pdf,png}`; `paper/sections/experiments.tex` §4.8;
`paper/sections/appendix.tex` App. D; `paper/scripts/make_figures.py --scaling` stdout (verification +
anchor/sensitivity tables) | Depends: Gate 5 component/latency accounts; Gate 3 batch scaling

Manager ask (2026-10-09), three points:
1. A general diagram of attention token/size growth and how much compression + decoupling
   reduces, **forecast rather than re-run**, at realistic scales (up to ~4096 width /
   ~32768 context; extended here to 131072 contexts).
2. The simplest defensible correlation between energy usage/savings and token/attention size.
3. A formula linking model size → energy → savings, explained in detail in the paper, and placed
   in the main text (not appendix only).

## Decisions (user, 2026-10-09)

- Anchors 4k / 8k / 32k / 128k contexts; standard-width backbones d=512/1024/4096 plus the study's
  d=128; include the measured latency anchors on the width panel.
- Energy is **model-only**: no measured-energy run. `powermetrics` needs root and adds attack surface
  (single machine, no DRAM power on M2); the coefficient-free projection is the publishable route.

## Tasks

- [x] **K-1. Scaling forecast figure (`fig12_scaling_forecast`).** Four panels: (a) softmax columns
  per query vs L; (b) attention-path savings vs L with closed-form asymptotes; (c) whole-layer savings
  by width with measured DRRA/Normal time savings overlaid; (d) asymptotic savings map over
  (c_KV, c_R) with tested cells marked. Standalone mode: `python scripts/make_figures.py --scaling`.
  The script asserts **exact equality** with the released per-component MAC accounts at L=256
  (76.86 / 63.30 / 61.20 M per sequence after the K-7 recheck) before drawing.
- [x] **K-2. Main-text subsection + table (§4.8 "Scaling forecast and energy projection").**
  Three savings measures defined (matrix / attention path / whole layer); closed forms
  `W_C(L)` and `S∞ = 1 − (1/c_KV + 1/(2c_R))`; Table with savings at 256 / 4k / 8k / 32k / 128k /
  limit; whole-layer projection by width; energy model statement; sensitivities; explicit non-claims.
- [x] **K-3. Energy projection: derivation, sensitivity, audit (App. D).** Component table
  (Normal / CSA / DRRA at L=256), closed-form derivation, three perturbations (auxiliary weighting
  λ∈{0.5,1,2} → 81.1/74.7/61.9% at 32k; single-head-indexer analogue → 84.0% asymptote against
  75.0% as executed; memory-traffic argument), validation (exact match; ρ=1.000 batch 32 / 0.992
  batch 1; paired r=0.96, n=5; whole-layer 50.5% vs 56.2% measured at L=2048/B32),
  scope-of-claim paragraph.
- [x] **K-4. Repo/compile hygiene found while building.** (i) `\sslash` in method.tex was undefined
  under the current toolchain — added `\usepackage{stmaryrd}` (the package that defines it). (ii) Two
  `tab:audits` rows ended with a single `\` instead of `\\` (source added after the last PDF build;
  would not compile) — fixed. (iii) One literal em-dash in method.tex produced a missing-glyph warning
  under XeTeX + `times` — replaced with `---`. Post-fix build is clean: 26 pages, no overfull boxes,
  no undefined references, no missing characters.

- [x] **K-5. Follow-up clarity (user question, 2026-10-09).** Panel (c) now names all three cells
  (DRRA solid, (16,4) dashed, (32,4) dotted; colors = width) with a compact style legend; the
  measured-marker key moved to the caption. §4.8 gained the "why not coarser?" synthesis:
  diminishing returns at the studied scale (frozen-context attention-path saving 30.9% → 37.1% →
  40.2% for (8,4)/(16,4)/(32,4) vs asymptotes 75.0/81.2/84.4%; measured full-layer speedup 1.18× /
  1.22× / 1.22× vs Normal, flat from 16:1); accuracy is not monotone in c_KV ((16,4) best mean of
  the three on val 0.5810 and test 0.8100, 25 seeds; (32,4) 0.6122/0.8586; (8,4) 0.6190/0.8440);
  probes stay exploratory (post hoc), so (8,4) remains the named confirmatory corner. Numbers from
  Gate18/Gate19 raw JSONL and the cell-speed audit (gate13_p0_audits/cell_speed.md).
  Paired check (corrected cell-restricted merge): (16,4)−(8,4) val Δ=−0.0379, exact Wilcoxon p=0.080
  (16/25); test Δ=−0.0340, p=0.059 (16/25); (32,4)−(8,4) val p=0.51, test p=0.41. Neither probe is
  statistically separated from the named corner; the earlier apparent significance was an artifact of a
  contaminated merge (gate2 rows not filtered by cell). Added the non-separation sentence to App. C.

- [x] **K-6. Term-by-term reading of the §4.8 equations in the main text (user request, 2026-10-15).**
  The three work terms of the compressed-cell accounting, the four-share decomposition of the
  savings ratio, the per-token reading of the whole-layer ratio, and every symbol of the energy
  model `E(θ)=Σ_k ε_k n_k(θ)` (including why the coefficient cancels) are now explained in §4.8
  itself. (b) §4.8 also gained a plain-language notation table (L, c_KV, c_R, W, +1, h, d_h, d, 64,
  with this study's values) and a one-line MAC definition, so the equations read standalone; (c)
  Equation (3) is now read term by term in §4.8 ($S(L)$ and every term of the $S_\infty$ limit with
  its value); (d) the additions are restyled to publication register (notation block promoted to a
  numbered float, tutorial phrasing removed, $W_N(L)$ and $W_C(L)$ explicitly defined); (e) App. D's
  closed-form paragraph became a full derivation that explains why each equation takes its form
  (per-component pricing, each term's $L$-power, the limit's two survivors, the per-token
  whole-layer form, and the frozen constants $256 = 2hd_h$, $17 = W+1$, $128 = hd_h = d$,
  $24{,}576 = 2d(64+d_h)$); (f) the derivation now sits with the equations in §4.8 (factoring
  reason, the executed router's per-head scoring note, $L^2$-coefficient rationale for the limit, frozen-constant map, the
  $2dL$ origin, and the approach-from-below remark), and App. D's derivation paragraph is a pointer
  to §4.8, keeping counts/sensitivity/validation/scope; (g) the user asked whether the energy
  paragraph could carry a figure — it now does: printed Figure 9 (repo
  `fig13_energy_composition.*`, `make_fig13` in `paper/scripts/make_figures.py`) shows the
  work-to-energy composition at $L{=}2048$ for Normal / CSA $(4,4)$ / DRRA $(8,4)$ as stacked
  per-token work shares (% of dense: attention core, router+compressor, projections+MLP), so the
  coefficient-free model is visible without any absolute energy: the attention path saves
  57.0\%/69.5\% while the fixed $12d^2$ block caps the whole-model saving at 41.4\%/50.5\%. The
  figure re-asserts exact equality with the audited accounts at $L{=}256$ (same checks as the
  scaling figure), and the script's analytic model is now shared by both figures (figs 8 and 9).
  Rebuilt clean (27 pp after float repacking, no overfull boxes, no undefined references);
  (h) the energy paragraph now also walks through Figure 9 in the text itself (composition: core
  $72.7\% \to 18.8\%/9.7\%$, router+compressor $12.5\%$, fixed block $27.3\%$, whole-model vs
  attention-path saving $41.4/50.5\%$ vs $57.0/69.5\%$) rather than a bare parenthetical
  reference. Rebuilt clean (27 pp).
- [x] **K-7. Component-accounting recheck (2026-10-16, Q1-review item R8).** The released router
  term charged one head per index-token comparison; a tensor-shape audit of the executed module
  (`plan/gates/gate20_accounting/`) shows the score matmul runs at $[B,H,S,d_h] \times [B,1,d_h,M]$,
  i.e. $hd_h = d = 128$ MACs per pair, so the compressed totals move 61.72→63.30 M (CSA) and
  59.63→61.20 M (DRRA) and every derived number moves with them: `W_C` router term $d_h L^2/c_R \to
  d L^2/c_R$; $S_\infty = 1 - (1/c_{KV} + 1/(2c_R))$; frozen-context savings 18.4/30.9/37.1/40.2%;
  asymptotes 62.5/75.0/81.2/84.4%; whole-model saving 20.4% (projection-matched 7.8%); whole-layer
  d=128 50.5% at L=2048 and 60.8% at L=4096; single-head-indexer analogue 84.0%. Also fixed the
  (32,4) softmax-column cell (16+1 → 24+1, matching the code's $L/c_{KV} + W + 1$) and the gate19
  manifest's `cell` label (see `plan/gates/gate19_324/MANIFEST_NOTE.md`). Figures 12–13 and §4.8,
  §4.6, App. D, the conclusion and the abstract updated; rebuilt clean (29 pp).

## Key numbers (all printed by the script; use these, not hand arithmetic)

- Exact MAC audit at L=256 (corrected by K-7): Normal 76.86 M, Flat/CSA 63.30 M, DRRA 61.20 M per
  sequence; router 2.10 M (was 0.52 M), attention core 3.21 M, compressors 6.29 M for DRRA.
- Attention-path savings vs Normal (%): L=256 → 18.4 / 30.9 / 37.1 / 40.2; L=4096 → 59.7 / 72.2 /
  78.5 / 81.6; L=32768 → 62.2 / 74.7 / 80.9 / 84.0; L=131072 → 62.4 / 74.9 / 81.2 / 84.3;
  asymptote → 62.5 / 75.0 / 81.2 / 84.4 for (4,4) / (8,4) / (16,4) / (32,4).
- Whole-layer savings at L=32768 (DRRA; (32,4)): d=128 72.9 (82.1); d=512 68.3 (76.8);
  d=1024 62.9 (70.8); d=4096 42.7 (48.0). Study backbone d=128: 50.5% at L=2048, 60.8% at L=4096.
- Whole-model MAC saving at L=256: 20.4% (CSA 17.6%); projection-matched 7.8%; the rank-128 vs
  rank-64 output projection is 10.49 M of the 15.66 M gap (66.9%).
- Validation: Spearman ρ = 1.000 (batch 32, n=15) / 0.992 (batch 1, n=18); paired DRRA/Normal
  work-vs-time Pearson r = 0.960 (batch 32, n=5) / 0.891 (batch 1, n=6). Measured end-to-end saving
  now exceeds the arithmetic projection at both anchors (56.2% vs 50.5%; 63.3% vs 60.8%), which the
  memory-bound dense baseline explains and the paper states.

## Notes for future sessions

- **Never present the projection as a measurement.** It is a first-order arithmetic model with a
  coefficient-free core (`E ∝ W` under a uniform coefficient); say "projected", "model-based",
  "coefficient-free". No joules, no energy measurement claims. The paper's Ethics Statement and the
  discussion limitations were updated accordingly; keep them in sync if the wording changes.
- **Stale internal summary found (do not propagate).** `plan/gates/gate5/gate5_summary.md` §5 lists
  4.42 M for the equal-rate cell's attention core; the released JSON (`gate5_results.json`) records
  5.31 M, consistent with Table 1's 81 columns. The paper and App. D table use the JSON values.
  Summaries are normally never modified; if that file is ever revised, fix the row to 5.31.
- **Compile requirements:** `stmaryrd` is now required by `main.tex`; keep it (it defines `\sslash`).
  Build locally with `cd paper && ../tectonic -X compile main.tex` (tectonic is vendored in the repo).
- Float placement: the fig12 float is declared right after the first paragraph of §4.8 (moved from
  the end of the file to cut a 4-page drift to 1.5 pages). If the paper is recompiled with the
  official two-column style, re-check its placement and caption width.

## Log

- 2026-10-09 (b): K-5 follow-up — panel (c) cell labels + "why not (32,4)?" synthesis added to §4.8;
  paper rebuilt clean (26 pp, 0 warnings of interest).
- 2026-10-15: K-6 — §4.8 (main text) now explains each equation term by term at the user's
  request: the three work terms with the frozen-task split (6.29M of 10.03M), the four-share ratio
  decomposition `1/c_KV + (W+1)/L + 1/(2hc_R) + (64+d_h)/L`, the per-token whole-layer
  numerator/denominator, and the symbols of the energy model plus the cancellation argument; clean
  rebuild (27 pp, no overfull/undefined).
- 2026-10-15 (b): K-6b — plain-language notation table added to §4.8 (L, c_KV, c_R, W, +1, h, d_h,
  d, 64 with values; one-line MAC definition), plus `notes/reading-guide-4.8.md` as the from-zero
  companion explainer; rebuilt clean (27 pp).
- 2026-10-15 (c): K-6c — Equation (3) now read term by term in §4.8: what $S(L)$ is, what the
  $1 -$ and the $W_C/W_N$ ratio mean at the same $L$, and each surviving term of $S_\infty$
  ($1/c_{KV} = 12.5\%$ columns, $1/(2hc_R) = 3.1\%$ router → 84.4\% for DRRA at L=256/limit).
  Guide updated to match; rebuilt clean (28 pp).
- 2026-10-15 (d): K-6d — §4.8 additions restyled to publication register: the notation block is now
  a numbered float (`tab:notation`, Table 7) with caption, tutorial phrasing removed throughout,
  and $W_N(L)$ / $W_C(L)$ are explicitly defined (dense work; and $W_C(L)$ as shorthand for
  $W_C(L; c_{KV}, c_R)$ of Equation 2); rebuilt clean (28 pp, no overfull/undefined).
- 2026-10-15 (e): K-6e — App. D "Closed form" replaced by a "Derivation" paragraph that explains
  why Equations 2–4 are shaped as they are (each factor's origin, each term's $L$-power, the
  limit's two survivors, the per-token whole-layer form, and the frozen constants
  $256 = 2hd_h$, $17 = W+1$, $32 = d_h$, $24{,}576 = 2d(64+d_h)$); rebuilt clean (28 pp).
- 2026-10-15 (f): K-6f — user asked why the derivation sat in the appendix rather than around the
  equations; per that, the unique derivation clauses moved into §4.8 (why $L$ is factored, the
  router's no-$h$ note, the limit's survivors being the two $L^2$ coefficients, the frozen-constant
  map, the $2dL$ origin, approach-from-below), and App. D's "Derivation" paragraph became a
  one-paragraph pointer to §4.8 while keeping the operation counts, sensitivity, validation, and
  scope. Rebuilt clean (28 pp).
- 2026-10-15 (g)/(h): K-6g/K-6h — Figure 9 (work-to-energy composition at L=2048) added and the
  energy paragraph rewritten to walk through it; rebuilt clean (28 pp).
- 2026-10-16: K-7 — component-accounting recheck from the Q1 review (R8): tensor-shape audit of
  the executed router (see the K-7 task line above); every affected paper number, figure and the
  gate19 manifest note updated; rebuilt clean (29 pp).
