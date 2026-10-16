# Pre-publication v2 tasks — the Q1-review program (single source of truth)

Created 2026-10-16. Source: `Q1_Journal_Technical_Review_and_Revision_Plan.pdf` (12 pp, 2026-10-16, stored
at the repo root) plus the manager's email proposing Information Sciences as an alternative target. A
plain-text extraction lives at `source/q1_review_text.txt` so every citation below survives a move of the
PDF; `source/README.md` records the provenance and the one caveat that matters:

> The review's own page references ("Manuscript, p. 8, §4.2") identify **the 27-page draft it was given**,
> not the current 31-page paper. Page numbers in this folder always mean the PDF's own pages.
This folder owns everything that the review asks for but the current bounded paper does not yet
contain. The finished bounded paper is tracked in `../pre-publication-tasks/`; nothing here blocks
submitting it.

## Decision summary (2026-10-16)

The one-line version of the whole folder. "Discard" means do not run the experiment — every claim in
`paper/` is already corrected and disclosed, so nothing on the discard list leaves an untrue sentence.

| Group | Items | Cost |
|---|---|---|
| **Already done** — in the paper, no action | R1, R8, and the paper-side half of R2–R7 | 0 |
| **Keep** — run these | S1, C1 all-block control, R2 matched dense, R4 probe, R5 probe re-runs, R6 figure, C4 MoBA paragraph | 10–15 h |
| **Borderline** — buy only if aiming high | R3 matched information budget | 10–15 h |
| **Discard** — reviewer's ambition, not the paper's claims | C2 full matrix, C3 systems and energy, C4 selection guide, C5 mechanism program, C6 temporal and equivalence program, R4 trained indexer, R7 transfer re-run | 0 |

Details and reasoning: `N_necessity_audit.md`.

## Folder map

Four files run the program; the rest are one file per task. Read them in this order.

| File | What it is |
|---|---|
| `EXECUTION_PLAN.md` | **Start here to work.** Phases 0–6 in order, each with a start trigger, numbered steps, exit criteria and milestone. Also the ground rules and the parked-work re-entry table. |
| `DECISIONS.md` | The decision register, D1–D7, each with an owner, a deadline, a default if undecided, and a freeze log. A decision that shapes a run must be closed here before that run starts. |
| `RUNBOOK.md` | Exact commands per phase, the directory convention for new runs, the verification commands, and the close-out checklist. |
| `N_necessity_audit.md` | Why each item is kept or discarded, written after the manager confirmed the review is AI-generated rather than referee correspondence. |
| `source/` | The review PDF's plain-text extraction and its provenance. Every task file cites the review by section, page and line into this extraction. |
| `BASELINE.md` | The record of what the earlier pass already fixed in the manuscript. |
| `R1`–`R8`, `C1`–`C6`, `S1` | One file per task, each opening with a verdict and a start trigger. |

## How to use this folder

1. **Resume here.** `STATUS.md` in `../pre-publication-tasks/` remains the session resume point and
   points at this folder; this README is the program's dashboard. A new session also loads the repo-root
   `AGENTS.md`, which routes to the resume ritual so nothing has to be remembered by hand.
2. **Work from the phase list.** `EXECUTION_PLAN.md` numbers the phases and the steps inside each one;
   you take the first unchecked step of the current phase. `RUNBOOK.md` has the exact commands.
3. **Freeze decisions before the runs they shape.** `DECISIONS.md` holds D1–D7 with defaults, so an
   unmade decision never stalls a phase — it just applies the conservative choice.
4. **One task, one file.** Edit only the task file you are working on, then log a line in it and a
   one-line entry in `../pre-publication-tasks/STATUS.md`.
5. **Evidence or it is not done.** Every closed checkbox needs a path to an artifact (a JSON/MD under
   `plan/gates/`, a paper file and line, a figure). No evidence means the task stays open. The full
   close-out checklist is at the end of `RUNBOOK.md`.
6. **Keep the paper free of internal names.** If a task changes the manuscript, follow the v1 hygiene
   rule: no gate numbers, stage numbers, plan paths or task IDs inside `paper/`.
7. **Numbers move only with evidence.** When a task changes a number, update the owner (the paper
   section), then the derived echoes (captions, tables, the reading guide).

## Dashboard

Statuses: `DONE` = finished and in the paper · `PARTIAL` = the claim is corrected and disclosed, the
experiment is missing · `TODO` = not started.

| ID | Task | Status | Verdict | Cost | Why it matters |
|---|---|---|---|---|---|
| R1 | Interaction effects: conditional reading + interaction figure + per-seed intervals | `DONE` | KEEP-closed | 0 (done) | Removes the misreading that fine routing is generally better; the figure and the intervals now carry the conditional result. |
| R2 | Mechanism-matched dense baseline (same projection ranks) | `PARTIAL` | **KEEP** | 3–4 h | The 20.4% MAC headline is two-thirds projection rank; only a matched retrain can say how much is the attention design. |
| R3 | Realized information budget: match unique valid blocks across cells | `PARTIAL` | **BORDERLINE** | 10–15 h + D2 | Fixed top-k changes how much history each cell actually reads, so the KV main effect is currently a configuration effect. Buy only if D1 aims high. |
| R4 | Route stability: does the selected set drift during training? | `DONE` | KEEP-closed | 0 (done) | Measured: sets drift (Jaccard 0.83) while the routed amount is flat (≈10/32, entropy 3.13); the caveat is now a number. |
| R5 | Evidential chain: regenerate pre-fix probes; extend causality coverage | `DONE` | KEEP-closed | 0 (done) | Probes regenerated ((4,4) moved; (8,4)/Normal bit-identical); causality suite passes at all six rate pairs; §4.3 + appendix updated. |
| R6 | Forecast-required cost as the headline efficiency view | `DONE` | KEEP-closed | 0 (done) | Figure 6 now leads with the forecast-required path (R2 matched row lands with Phase 3). |
| R7 | Transfer routing: the PatchTST test barely exercises routing | `PARTIAL` | **PARKED** | 0 h to narrow, 10–15 h to re-run | At 31 patch tokens the coarse-router cells select every candidate, so the tie cannot show that routing washes out. D6 decides: delete the claim or re-run. |
| R8 | Accounting: router term, (32,4) columns, recomputed totals | `DONE` | KEEP-closed | 0 (done) | Two real arithmetic defects; the review caught one, the same audit caught the other. |
| C1 | Controls: all-block compression kept; the other seven parked | `TODO` | **KEEP** (all-block only) | 7 h | Answers "is the router needed at all?" — the one control that can change the paper's story. |
| C2 | Generalization matrix: datasets, horizons, lookbacks, backbones | `TODO` | **PARKED** | 0 | Scope, not a defect: the paper already has 12 datasets, 25 paired seeds and a cross-dataset replication. |
| C3 | Systems and release: second platform, energy, archived artifacts | `TODO` | **PARKED** | 0 | The paper claims neither GPU behaviour nor energy savings. |
| C4 | Positioning: MoBA paragraph kept; selection guide parked | `DONE` (MoBA only) | KEEP-closed (MoBA) | 0 (done) | A nearest-neighbour citation gap is the one thing a related-work referee reliably notices. |
| C5 | Mechanistic and signal-controlled tests | `TODO` | **PARKED** | 0 | The paper never claims a mechanism and says so explicitly; this is a different paper's work. |
| C6 | Inference: temporal validation, MAE, non-inferiority margin | `TODO` | **PARKED** | 0–30 min | The fixed-split 25-seed protocol is standard here and the paper makes no equivalence claim, so the margin has nothing to protect. Keep one sentence stating the estimand. |
| S1 | Submission packaging: authors, highlights, CRediT, data availability, declarations | `TODO` | **KEEP, REQUIRED** | 3–5 h | The only items the journal actually enforces; the manuscript satisfies none of them yet except the ethics statement. |

## Where each task ID comes from (mapping to the source PDF)

The review PDF only numbers its P0 items (R1–R8). The rest of its sections have no IDs, so this folder
invented C1–C6 for them; S1 and N are additions of mine that are not in the document at all. Use this
table when quoting the review back to the manager, because "C1" means nothing to him. Line numbers refer
to `source/q1_review_text.txt`.

| Folder ID | Source PDF | The document's own heading | Its page | Text lines | Item anchor |
|---|---|---|---|---|---|
| R1 | section 1 | "P0 / Corrections required before new headline results — 1. Correct the statistical interpretation and baseline attribution" | p. 2 | 58–108 | "R1. Interpret the interaction using simple effects" (60) |
| R2 | section 1 | same section | p. 2 | 58–108 | "R2. Separate attention savings from projection savings" (92) |
| R3 | section 2 | "2. Isolate routing resolution and verify what actually changes" | p. 3 | 115–152 | "R3. Fixed top-k is not a fixed information budget" (117) |
| R4 | section 2 | same section | p. 3 | 115–152 | "R4. An untrained indexer is not necessarily a fixed route" (131) |
| R5 | section 2 | same section | p. 3 | 115–152 | "R5. Rebuild the evidential chain after the mapping correction" (143) |
| R6 | section 3 | "3. Use the forecast-required path and nondegenerate routing" | p. 4 | 159–196 | "R6. Make optimized forecasting cost the primary comparison" (161) |
| R7 | section 3 | same section | p. 4 | 159–196 | "R7. Check whether the PatchTST experiment actually routes" (175) |
| R8 | section 3 | same section | p. 4 | 159–196 | "R8. Reconcile the remaining accounting before extrapolation" (188) |
| C1 | section 4 | "P1 / Experiments with the highest diagnostic value — 4. Establish whether the router is needed at all" (the control table: projection-matched dense, all-block compressed, window-only, random/recent/evenly spaced, mean or filtered pooling, trained indexer, original dense backbone) | p. 5 | 203–267 | control table 208–249; "Run the controls in a diagnostic sequence" (251) |
| C2 | section 5 | "5. Expand along dimensions that can change the conclusion" (dataset, horizon, lookback and backbone table) | p. 6 | 274–326 | dimension table 286–311; "Keep token axes and data protocols explicit" (317) |
| C5 | section 6 | "6. Build a mechanism-level contribution that others can reuse" (controlled synthetic families, the filter comparison, the analytical starting point) | p. 7 | 333–385 | signal-family table 339–360; "A useful analytical starting point" (366) |
| C6 | section 7, first half | "7. Strengthen the statistics and systems evidence": "Separate three sources of uncertainty" | p. 8 | 392–430 | 393 |
| C3 | section 7, second half | same section 7: "Benchmark optimized implementations, not only operation counts", "Treat energy as a measurement question", "Release a tagged code archive" | p. 8 | 392–430 | 408, 421 |
| C4 | section 8 | "8. Reframe the manuscript around a useful conditional finding" (title, MoBA and closest-work updates, the five-figure plan, the selection guide) | p. 9 | 437–480 | 439, 446, 456 |
| (quoted minimum) | section 9 | "Team delivery plan / priorities and submission gates — Minimum package I recommend for Neurocomputing" | p. 10 | 487–549 | 525 |
| S1 | **not in the document** | Journal mechanics, taken from Neurocomputing's Guide for Authors and Elsevier's data policy | — | — | — |
| N | **not in the document** | This folder's necessity audit (the assistant's own assessment that the document is an AI-generated auditor rather than a referee) | — | — | — |

## Are these needed to publish at Neurocomputing?

> **Read `N_necessity_audit.md` first if the decision is about scope.** The source document is an
> AI-generated review, not referee correspondence. It found two real arithmetic defects and four
> overclaims (genuine value), but its "minimum package" mixes required truth-preserving items with scope
> expansions. The audit file separates them item by item and ends with a 10–15 hour defensible path
> against the 75–110 hour programme below.

Short answer: **the S1 items are required; the R and C items are not rules but they are the reviewer's
minimum package, and that package is what decides survival in review.**

- **Journal requirements (S1 only).** Neurocomputing follows "Your Paper Your Way", so the first
  submission needs no strict formatting, but it does require an author block, Highlights of 3–5 bullets
  at 85 characters each, an abstract of roughly 250 words, a CRediT statement, a Data Availability
  Statement (code sharing is encouraged, and required only in the separate Software Track), a declaration
  of interest, and a generative-AI disclosure if AI tools assisted the writing. None of these is an
  experiment, and none of the R or C work is mentioned in the Guide for Authors.
- **The reviewer's minimum for Neurocomputing** (verbatim from the review): resolve all P0 issues;
  include projection-matched dense and compression-only controls; demonstrate active routing in a
  competent backbone; add targeted multi-horizon and longer-lookback work plus temporal validation; and
  make the main computational claims survive optimized forecast-required accounting. A trained-router
  control and the mechanistic tests should support the explanation rather than remain future-work
  promises. He adds that the submission should establish at least one meaningful conclusion — a genuine
  routed advantage in a regime, a useful compression-only trade-off, or a boundary showing when routing
  is unnecessary — and that unresolved confounds cannot be compensated by more datasets or cautious
  wording.
- **What that maps to here:** R2 and C1 (the two controls), R7 (active routing in a competent backbone),
  C2 (horizons, lookback, temporal validation), R6 (forecast-required accounting), R3 and R4 and R5
  (the remaining P0 audits), and C5 (the mechanistic tests). C3 and C4 are not in his minimum list; they
  are ambition items.
- **Cost of that minimum package:** roughly 75–110 CPU hours plus author time, which is larger than the
  30–50 h figure recorded earlier as Q-1, because the review's package is bigger than the original
  Stage-2 list. The honest floor is therefore: the bounded paper is submittable today with S1 only, but
  it carries the confounds the review names, and it is not the package he would recommend sending to
  Neurocomputing.

## Recommended order

The authoritative version is the phase list in `EXECUTION_PLAN.md`; this is the one-line summary.

**Phase 1** S1 (parallel from now) → **Phase 2** R5, R6, R4-probe, MoBA paragraph → **Phase 3** R2 →
**Phase 4** C1 all-block → **Phase 5** R3, only if aiming high → **Phase 6** R7 narrowing. Milestones:
M1 submission-ready, M2 headline confounds closed, M3 story checked, M4 high-aim package, M5 submission.

## Two analysed budget options (2026-10-16)

Option A was checked item by item against the reviewer's minimum package, so the gap is explicit.

| Option | Contents | Cost | What it buys, and what it leaves open |
|---|---|---|---|
| **A. Sound + decisive control** | S1, R2, R6, R5-probes, R4-probe, C1 all-block | 15–20 h | Closes every confound on the paper's primary claims and adds the control that can change the story. Leaves open, against the reviewer's minimum: R3 (budget), R7 (active routing in a competent backbone), C2 and C6 (horizons, longer lookback, temporal validation), C5 (mechanistic tests), and the trained-router control. Those must be narrowed in the text, and the reviewer's objections to them stand. |
| **B. Defensible at a Neurocomputing review** | Option A + R3 + the trained-router control | 30–45 h | Closes every confound on every claim the paper makes. Only generalization (C2) and mechanism (C5) remain as openly declared limits, so a referee may still request them, but no claim rests on an unresolved confound. |

R3 decides between the options, because it sits under the paper's title claim: the study exists to compare
the two axes, and fixed top-k means the KV cells read different amounts of history. R7 has a free
alternative — delete the transfer claim — but then no competent-backbone routing is demonstrated at all.

## Minimum path if the target is only "submit somewhere sound"

S1 alone, plus the four cheap items (R6, R5-probes, R4-probe, R2) at about 10 hours. That closes every
headline-confounding item except the information-budget one (R3) and the transfer saturation (R7), both
of which are already disclosed as limits. The claims that remain must stay narrow: no transfer
conclusion, and the KV effect stated as a configuration effect.

## Open decisions

Owned by `DECISIONS.md` — the register there carries the options, the deadlines and the default that
applies if a decision is not made in time. The summary below is a pointer, not the owner:

- **D1 — venue.** Submit the bounded paper now, or hold for Neurocomputing / Information Sciences.
  Default after M2: stop after Phase 3 and submit the narrowed paper.
- **D2 — R3 filling rule**, needed only before Phase 5.
- **D3 — trained indexer**, needed only if C1 shows the router matters.
- **D4 — title**, decided after Phase 4 reports.
- **D5 — non-inferiority margin.** No harmless default exists; it must be frozen before Phase 4 or the
  control's null result cannot be interpreted.
- **D6 — R7 handling**, default is to narrow the claim rather than re-run.
- **D7 — MAE**, default is to state the omission rather than re-run for a second metric.
