# Decision register

Every decision below is owned by a person, has a deadline, and has a **default** so the plan never
stalls waiting on it. A decision is closed when it has a date and a one-line rationale in the freeze log
at the bottom — not when it has been discussed.

Two rules make this file worth keeping:

1. **A decision that shapes interpretation must be closed before the run it shapes.** A rule chosen
   after seeing results is not admissible, and saying so afterwards will not repair it.
2. **The default applies silently if the deadline passes.** That is deliberate: it converts an unmade
   decision into a known, conservative choice rather than into a stalled phase.

## Register

| ID | Question | Options | Default if undecided | Deadline | Owner | Blocks |
|---|---|---|---|---|---|---|
| **D1** | Where does this paper go? | (a) submit the bounded paper now with S1 only; (b) Option A — sound + decisive control, 15–20 h; (c) Option B — defensible at a Neurocomputing review, 30–45 h; (d) the review's full package, 75–110 h | **Option A.** It closes every confound on the primary claims and adds the one control that can change the story. If unanswered by M2, stop after Phase 3 and submit the narrowed paper instead | before Phase 4 | Daryl + manager | the entire phase list |
| **D2** | R3 filling rule: how is a matched budget filled when a cell has fewer safe blocks than the budget? | (a) take blocks in score order until the budget is full, then stop; (b) take the most recent blocks; (c) random within the safe set | **(a) score order.** It is the rule the router already implies and the only one that needs no new mechanism | before Phase 5 | Daryl | Phase 5 (R3) |
| **D3** | Keep the non-learned indexer, or train it? | (a) keep it — the paper's identity is a parameter-free selection rule; (b) add one trained-selector control with an auxiliary loss | **closed 2026-10-19: (a) keep** (default applied when C1 confirmed routing matters; the indexer receives no task gradient, so (b) is a design change) | only if C1 branches to "routing matters" | Daryl | R4's second half |
| **D4** | Title | (a) keep the current title, locked in `../pre-publication-tasks/00_title.md`; (b) adopt the review's conditional framing, *When Does Compressed Attention Help Time-Series Forecasting? Separating Compression, Routing, and Computational Cost* | **closed 2026-10-19: (a) keep** — C1 reported `routing_confirmed`, not a boundary, so the unconditional title stands | after Phase 4 | Daryl | abstract, title, conclusion |
| **D5** | Non-inferiority margin: what difference counts as "no meaningful difference"? | a relative validation-MSE margin chosen for forecast usefulness, not from these results. Suggested anchor: 2% relative | **frozen 2026-10-18: 2% relative for the label, with a bound as the primary output** (see freeze log). No binary non-inferiority verdict is manufactured at n=25 | before Phase 4 | Daryl | C1 interpretation, any equivalence wording in C6 |
| **D6** | R7 transfer claim: narrow it for free, or re-run at 10–15 h? | (a) delete the transfer claim, keep the geometry as a stated limitation; (b) re-run with more patch tokens | **(a) narrow.** The claim is not worth 10–15 h of compute when the honest version is one sentence | before Phase 6 | Daryl | §4 transfer paragraph |
| **D7** | MAE: report it or not? | (a) re-run the 25-seed suite with MAE recorded; (b) state the omission in the limitations | **(b) state the omission.** Re-running 25 seeds to record a second metric is not a good use of the machine; a stated omission is honest | before any re-run | Daryl | the metrics paragraph |

## Freeze log

Append one line per decision when it is closed: date, ID, choice, one-line rationale, who closed it.
Anything not in this log has not been decided, whatever was said in conversation.

| Date | ID | Choice | Rationale | By |
|---|---|---|---|---|
| 2026-10-16 | — | folder created | review triaged; keep/discard split recorded in `N_necessity_audit.md` | assistant |
| 2026-10-16 | D1 | **(b) Option A** — S1 + R2 + R6 + R5-probes + R4-probe + C1 all-block, 15–20 h | smallest package that closes every confound on the paper's primary claims and runs the one control that can change the story; R3/R7/C2/C5 remain narrowed as stated limits | Daryl |
| 2026-10-18 | D5 | **2% relative validation MSE for the label, with the bound as the primary output** — the label applies per cell to (MSE_ctrl − MSE_ref)/MSE_ref; non-inferiority is declared only on interval containment, and the 95% upper limit U on the relative cost of removing routing is reported as the headline whatever the label says | the anchor is decision-relevant (~1/10 of the 19–27% headline) and strict relative to the paper's own reading of the 5.72% matched-dense difference; the pre-run precision check shows n=25 resolves ~6% (paired half-widths 5.3–7.7%, a 2% test would need seed-correlation ≥ 0.91), so a binary verdict at 2% is pre-declared unavailable rather than manufactured | Daryl (delegated; investigated recommendation) |
| 2026-10-19 | D3 | **(a) keep the non-learned indexer** (default) | C1 confirmed routing matters, which triggers D3; but the router-gradient audit shows the indexer receives exactly zero task gradient, so a trained selector is a new architecture rather than a control, and the parameter-free identity is accurate | Daryl (default applied) |
| 2026-10-19 | D4 | **(a) keep the title** | C1's branch is `routing_confirmed` (selection loses 12-27% relative accuracy when removed), not a boundary, so the conditional retitle is not triggered | Daryl (branch rule) |
| | | | | |
