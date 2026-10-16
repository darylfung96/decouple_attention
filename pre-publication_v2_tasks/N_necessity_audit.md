# N — Necessity audit: my independent read of the AI-generated review

Written 2026-10-16 by the assistant (not by the review's author). Purpose: separate the items that
protect the paper's truth from the items that expand its scope, so the manager's list is not executed
wholesale.

## How I read the document

The document is an **auditor, not a referee**. Its checkable claims were mostly right, and it found two
genuine arithmetic defects plus four overclaims, which is real and unusual value. Its weakness is
calibration: it presents a full methodological ideal as the "minimum package", and roughly three
quarters of that package is generic best practice that a human referee for a controlled design study
would not demand. An AI review is optimized for completeness, so it always produces a longer list than
any referee; executing it wholesale means months of work and a paper that keeps receding.

Two concrete places where its premises were wrong or stale, which is why it should be read as a
checklist and not as an authority:

1. It assumed the PatchTST transfer used `k=16`. The transfer actually used `k=4`, so its saturation
   arithmetic was off even though the conclusion held for the coarse router. The paper now reports the
   real geometry (31 tokens, 6–7 versus 3 candidates).
2. It presented "demonstrate active routing in a competent backbone" and "temporal validation" as
   minimum items, but those are scope expansions that its own earlier pages classify as P1 ambition. It
   mixed the two tiers.

## Necessity audit, item by item

Verdicts: **Required** (protects a claim the paper makes) · **Do** (cheap and materially strengthens) ·
**Narrow instead** (replace the claim with an honest scope statement at zero cost) · **Skip** (scope
expansion, would not decide acceptance).

| Item | Is its premise a real defect? | Would a referee plausibly raise it? | Verdict |
|---|---|---|---|
| R1 interaction direction | Yes — the sentence contradicted the table | Yes, immediately | **Required** (done) |
| R8 accounting (router, columns, totals) | Yes — two real arithmetic errors, one found only because the review asked for a shape check | Yes, a referee reading the MAC table | **Required** (done) |
| S1 submission packaging | Not a research defect, but the journal enforces it | Yes, submission is blocked without it | **Required** |
| R2 projection confound | Yes, the attribution was wrong | Yes, it is the first thing a quantitative referee checks in an efficiency table | **Do** (3–4 h) *or* **Narrow instead**: drop the whole-model MAC claim and keep the attention-path number |
| C1 all-block compression | Not a defect, but it is the only control that can change the paper's conclusion | Maybe — a referee may ask "is routing needed at all?" | **Do** (7 h) · highest value per hour in the whole list |
| R4 route stability (probe) | Overclaim, already fixed in words | No — the wording fix suffices | **Do** (0.5 h, cheap insurance) |
| R5 probe re-runs | Yes, the probes predate a fix | No, the draft already labels them as history | **Do** (0.5 h) or leave the disclosure |
| R6 forecast-required figure | The reporting is right; only the figure's axis is stale | No — the text already states both paths | **Do** (1 h) or leave as is |
| C4 MoBA paragraph | Yes, a citation gap a related-work-literate referee may notice | Sometimes | **Do** (30 min of writing) |
| R3 budget matching | Yes — a real identification issue, and it sits under the paper's title claim | Only a methodologically deep referee; most will not compute realized coverage | **Do if aiming high** (10–15 h); otherwise **narrow instead**, which the paper already does by calling the KV effect a configuration effect |
| R7 transfer saturation | Yes, the interpretation was wrong | Only if the transfer is claimed as evidence | **Narrow instead** (delete the transfer claim) or 10–15 h to re-run |
| C6 rolling origins, moving-block bootstrap, non-inferiority margin | The current protocol is standard for this literature | Unlikely at an applied journal; this is econometrics-flavored boilerplate | **Skip**, except one cheap line: state that intervals are paired mean differences and that no equivalence test is run (already in the paper) |
| C6 MAE | No manifest records it | Occasionally requested in forecasting venues | **Do only if the paper is re-run anyway** — otherwise skip and state the omission |
| C2 horizons, longer lookback, full matrix | The paper has 12 datasets and a 25-seed factorial, which is more breadth than most accepted work here | A referee may ask for one longer lookback | **Skip the matrix**; add one longer lookback only if a referee asks |
| C5 mechanistic program (three controlled generators, filter comparison, discrepancy diagnostic) | The paper never claims a mechanism, and it says so | No — it explicitly marks the mechanism as unverified | **Skip** — this is a different paper |
| C3 GPU, second platform, instrumented energy | The paper claims neither GPU behaviour nor energy savings | No | **Skip** |
| C4 selection guide with held-out regret | Not a defect; it is a new contribution | No | **Skip** |
| C5/R4 trained-router control | Not a defect; the paper's identity is a non-learned indexer | No | **Skip** unless R3 runs and the story changes |

## What I would actually run

1. **S1** — days of author time, and nothing else matters until it exists.
2. **C1 all-block compression** — about 7 hours, the one experiment that can turn "a configuration wins
   on one dataset" into "routing is unnecessary in a defined regime", which is the sentence the review
   itself calls the stronger contribution.
3. **R2** — 3–4 hours, or a one-paragraph narrowing if the budget is tight.
4. **R4 probe, R5 probe re-runs, R6 figure, MoBA paragraph** — about 2.5 hours together.
5. Stop there and submit, unless a named referee asks for more.

That is roughly **10–15 hours** for a defensible submission, against the 75–110 hours the document
proposes as its minimum. The difference is entirely scope: a second platform, an energy measurement, a
mechanistic theory, a horizon and lookback matrix and a validated selection guide are things a *different*
paper is made of.

## The rule I used to decide

Keep an item if it points at a claim the paper makes that is false, unverifiable from the artifacts, or
confounded by something the paper itself discloses. Drop an item if it adds a new claim the paper does
not make, because that raises the bar without ever ending.

## Log

- 2026-10-16: created after the manager confirmed the review is AI-generated rather than referee
  correspondence. Conclusion: keep the eleven required and cheap items above; skip the six scope items.
