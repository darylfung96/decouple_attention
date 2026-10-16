# Execution plan — when to start, what to start, step by step

Written 2026-10-16. This file answers one question: **what do I run next, and what must be true before
each thing starts.** It is the operational companion to the README dashboard (what exists) and
`N_necessity_audit.md` (what to keep and what to discard).

Reading order for any new session:

1. `BASELINE.md` — what is already done in the paper.
2. `README.md` dashboard — current status of every item.
3. This file — the phase you are in and the next unchecked step.
4. The item file for the task you are starting, then `RUNBOOK.md` for the exact commands.

---

## The eight ground rules

Violating any of these is how a re-run turns into a rewrite. They are the reason the earlier pass went
smoothly.

1. **Freeze before you run.** Any rule that decides interpretation (a filling rule, a margin, a
   lookback) is written down, dated, and committed to a design file *before* the run begins. A rule
   chosen after seeing results is not admissible.
2. **One variable per run.** A new run changes exactly one thing against a named reference row. If two
   things change, the result answers neither question.
3. **The seed set is fixed.** New experiments reuse the 25 paired seeds:
   `42, 123, 2024, 7, 99, 1–6, 8–21`. Paired comparisons only work on the same seeds as the reference.
4. **Historical artifacts are append-only.** Never rewrite a `*.jsonl` manifest, never edit a gate
   result file, never re-run an old gate script into its old output path. New run, new directory,
   new manifest.
5. **Every run ships its analysis.** A gate directory is not finished with a raw JSONL; it needs the
   analysis script and a short `.md` that states the result and its interval.
6. **Evidence or it is not done.** A checkbox closes only against a path: a JSON, an `.md`, a paper
   file and line, a figure. Checkboxes without a path reopen at the next audit.
7. **The paper stays clean.** No gate numbers, task IDs, stage names or plan paths inside `paper/`.
   `verify_manuscript.py` enforces this and must pass before any manuscript-visible change is called
   done.
8. **Numbers move owner-first.** Change the paper section that owns the number, then the derived
   echoes (tables, captions, abstract, conclusion, reading guide). Superseded values never stay in
   `paper/` — if a number is replaced, the old one exists only in the audit log.

---

## Dependency map

```
Phase 1  S1 (submission packaging) ............ author time, no compute, parallel to everything
Phase 2  R5 probes ── R6 figure ── R4 probe ── C4 MoBA paragraph ......  3–4 h, no dependencies
Phase 3  R2 matched dense retrain ............  needs nothing; feeds R6's frontier if done first
Phase 4  C1 all-block control ................ needs D5 frozen; benefits from R2's matched row
Phase 5  R3 matched information budget ....... only if D1 = high-aim; needs D2 frozen
Phase 6  R7 handling (free narrowing) ........ one decision, about 30 minutes of writing
Gate M2 ── submit the narrowed paper ───────── the minimum path
```

Milestones, in order: **M1** submission-ready (S1 done) → **M2** headline confounds closed (Phases 2–3)
→ **M3** story checked (Phase 4) → **M4** high-aim package (Phase 5) → **M5** submission.

---

## Phase 0 — Freeze the decisions (start now, about 1 hour, no compute)

**Start when:** now. Nothing else waits on it except the phases that name a specific decision.

**Steps**

1. Open `DECISIONS.md` and answer D1 (venue). This is the only decision that changes the phase list.
2. Answer D5 (margin) if Phase 4 will run — it must be frozen before C1 starts.
3. Answer D6 (R7) and D7 (MAE). Both have zero cost and settle a paragraph each.
4. Answer D2 (filling rule) only if Phase 5 will run, and D4 (title) only after Phase 4 reports.

**Exit criteria:** every open decision in `DECISIONS.md` has a date and a one-line rationale, or is
recorded as "default applies".

**Owner:** Daryl. **Blocks:** Phase 4 (D5), Phase 5 (D2), Phase 6 (D6).

---

## Phase 1 — Submission packaging (S1): start now, in parallel

**Start when:** now. This is the only mandatory block, it needs no machine time, and it can proceed while
any other phase runs.

**Steps**

1. Fill the author block in `paper/main.tex` (names, affiliations, corresponding author, emails).
2. Write Highlights: 3–5 bullets, at most 85 characters each, one per finding.
3. Trim the abstract from 386 words to roughly 250 without losing the matched-versus-as-run pair.
4. Write the CRediT author statement.
5. Write the Data Availability Statement, naming the repository and the license.
6. Write the declaration of interest.
7. Add the generative-AI disclosure if AI tools assisted the writing (they did — a tracker and an
   audit assistant; declare it in the journal's neutral wording).
8. Draft the cover letter and a suggested-reviewer list.
9. Confirm in the current Guide for Authors: the review model (single or double anonymized), the
   figure and length limits, and whether Highlights are submitted as a separate file.

**Exit criteria:** every checkbox in `S1_submission_packaging.md` is ticked against a file and line, and
`verify_manuscript.py` passes with the author block in place.

**Cost:** 3–5 h of author time. **Owner:** the submitting author. **Blocks:** nothing, but nothing can be
submitted without it. Milestone M1.

---

## Phase 2 — The cheap claim closers (3–4 h, start after Phase 0)

**Start when:** Phase 0 is answered. No dependency on S1 or on any run.

**Order inside the phase matters**, because R5 can change a number that R6's figure and R4's probe
report beside.

1. **R5 — regenerate the two probes** (about 30 min). They predate the mapping fix, so every mechanism
   number in §4.3 must come from the current implementation.
2. **R6 — rebuild the efficiency frontier** (about 1 h) so the forecast-required path leads, with the
   full-layer view retained as a labelled comparison.
3. **R4 — route-stability probe** (about 30 min): instrument one cell's training run, log the selected
   sets per epoch, report the overlap between the first and last epoch.
4. **C4 — the MoBA paragraph** (about 30 min): add the nearest-neighbour comparison to related work.
   Leave the rest of C4 parked.

**Exit criteria:** §4.3 numbers come from the current implementation; the frontier figure answers "what
does one forecast cost"; the route claim is a measurement; the related-work gap is closed. Each with a
log line and an artifact path.

**Cost:** 3–4 h, mostly machine time on CPU. **Milestone:** contributes to M2.

---

## Phase 3 — Close the accounting confound (R2, 3–4 h)

**Start when:** Phase 2 is running or done. Nothing depends on it, and it is the last confound on the
main efficiency headline.

**Steps**

1. Add a `Normal-r64` variant to the harness: identical to the as-run Normal except the output
   projection uses the compressed cells' rank, with the same normalization, positional treatment and
   sink handling.
2. `--dry-run` first and confirm the parameter table shows the projection matched; then `--smoke`;
   only then the full 25-seed run into a new manifest under a new gate directory.
3. Analyze paired per-seed differences against Normal and each factorial cell, with intervals.
4. Update §4.6, the tables and the conclusion so every headline improvement names its source
   (compression, routing, projection rank, or head).
5. If R6 has landed, put the matched baseline on the frontier figure.

**Exit criteria:** a projection-matched dense row sits beside Normal in the tables and the figure, and
no efficiency sentence is left unattributed. **Milestone M2 complete.**

---

## Phase 4 — The decisive control (C1 all-block, about 7 h)

**Start when:** **D5 is frozen** and Phase 3 has landed. This is the experiment that can change the
paper's story, so its interpretation rule must be written down before its first run.

**Steps**

1. Write `plan/gates/<new>/design.md`: the control is "compression without routing" — every index token
   is selected, so the model keeps the compressors and the projection ranks and loses only the
   selection. State the reference rows, the seeds, and the interpretation rule with the D5 margin.
2. Implement the variant behind a flag, and assert in the dry run that the selected-block count equals
   all safe blocks for every position.
3. Smoke, then run the 25 paired seeds into a new manifest.
4. Analyze against the four factorial cells and Normal with paired intervals.
5. Branch on the predeclared rule:
   - Control is **worse** by more than the margin → the routing axis is doing work; the paper's story
     survives, and R3 becomes the natural next purchase.
   - Control is **within** the margin → the finding is a boundary result; update the title, abstract and
     conclusion per D4: routing is unnecessary in this regime, and compression is sufficient.
   - Control is **better** → the router is actively harmful; report it plainly.

**Exit criteria:** the control row exists with intervals, the branch taken is the one predeclared, and
the manuscript reflects the branch. **Milestone M3.**

---

## Phase 5 — Conditional: matched information budget (R3, 10–15 h)

**Start when:** D1 = high-aim **and** D2 is frozen. Do not start it otherwise; it is the only item on
the borderline list.

**Steps**

1. Write the filling rule into a design file (D2) and implement the budget clamp.
2. Verify in the dry run that realized unique valid blocks are equal across cells at the same length —
   this assertion is the whole point of the item.
3. Run the affected cells on the 25 seeds into a new manifest.
4. Re-estimate the KV main effect under matched budgets and report what survives.
5. Update the KV claims to either the matched result or an explicit "budget-unmatched configuration
   effect" if the effect moves.

**Exit criteria:** the KV main effect is either measured under a matched budget or the paper states the
configuration reading with the matching attempt documented. **Milestone M4.**

---

## Phase 6 — R7 handling (about 30 minutes, no compute)

**Start when:** Phase 0 answers D6.

- **Default (free):** delete the transfer claim and keep the geometry statement as a limitation. About
  30 minutes of writing, then verify.
- **Alternative (10–15 h):** re-run the transfer at a longer patch count so the coarse-router cells
  actually discriminate. Buy this only if D1 = the full package.

---

## Parked work and its re-entry triggers

Parked means "no compute now", not "forgotten". Each item reopens only against a named trigger, and
that trigger is usually a referee or a manager, never a mood.

| Parked item | Reopens when | Cheapest admissible response |
|---|---|---|
| C2 generalization matrix | a referee asks for a longer lookback or a second horizon | one lookback (for example 512) on two datasets, not the matrix |
| C3 systems and energy | a referee asks for wall-clock or energy evidence | wall-clock on the existing machine under the same protocol; energy only with real instrumentation |
| C4 selection guide | a referee asks for practical guidance | one paragraph pointing at the existing figure and tables; the validated guide stays a future-work item |
| C5 mechanistic program | a referee says the mechanism is asserted rather than shown | point at the explicit unverified-mechanism statement; offer the controlled families as future work |
| C6 temporal and equivalence program | a referee disputes the intervals | state the estimand in one sentence: paired mean differences over 25 seeds, no equivalence test |
| R4 trained indexer | C1 shows the router matters and D3 changes | one trained-selector control at the same budget |
| R7 transfer re-run | D6 chooses the paid path | the longer-patch re-run at 25 seeds |

---

## Session ritual (five minutes, prevents most mistakes)

**Start of session:** read the dashboard for status, read this file for the current phase, open the item
file, then run the phase's dry run or smoke before touching anything real.

**End of session:** one line in the item file's log, one line in `../pre-publication-tasks/STATUS.md`,
update the dashboard status if it changed, and leave every new artifact inside its gate directory.

**Never running two experiment phases at once** is deliberate: the machine is CPU-only and the runs are
20–25 minutes each, so interleaving them makes failures ambiguous.
