# S1 — Submission packaging: the only mandatory items

**Status:** TODO · **Cost:** 3–5 h of author time · **Owner:** the submitting author
**These are the journal's hard requirements.** Everything in R1–R8 and C1–C6 is a research-evidence
standard, not a rule Neurocomputing enforces at submission.

**Verdict:** KEEP, REQUIRED — the only block the journal enforces.
**Start when:** now, in parallel with everything else. No compute, no dependency.
**Milestone:** M1. Nothing can be submitted until every checkbox here is ticked.

**Source:** not the review — Neurocomputing's Guide for Authors and Elsevier's data policy. The review's own submission-gate section §9 supplies the minimum-package context (PDF p. 10; `source/q1_review_text.txt` line 487, with the package quoted at line 525).

## What Neurocomputing requires at submission

Verified against the journal's Guide for Authors and Elsevier's research-data policy on 2026-10-16.
Neurocomputing follows "Your Paper Your Way", so the initial submission does not need the Elsevier
two-column template; Elsevier's format applies at revision. The following are required from the start:

| Item | Status in the manuscript |
|---|---|
| Author names, affiliations, corresponding author | **Placeholder** (`Author Name`, `email@example.com`) — must be filled |
| Highlights, 3–5 bullets with at most 85 characters each | **Missing** — not written |
| Abstract, typically around 250 words | **386 words** — trim |
| CRediT author statement | **Missing** |
| Data Availability Statement | **Missing** — the material exists (repository, manifests, dataset sources) but is not declared as a statement |
| Declaration of interest | **Missing** |
| Generative-AI disclosure (if AI tools assisted the writing) | **Missing** — state it if applicable |
| Ethics statement | Present (public data, no human subjects); keep |
| Review model (single or double anonymized) | **Unverified** — confirm in the current guide before uploading; if double-anonymized, strip names from the manuscript and upload them separately |
| Cover letter and suggested reviewers | **Missing** |

Code and data sharing are *encouraged* by Neurocomputing, and a Data Availability Statement is required;
code release is mandatory only in the journal's separate Software Track, which this paper is not
submitting to. So the repository release is a strength of the submission, not a precondition.

## Log

- 2026-10-16: created. Nothing applied to `paper/` yet; the author block is still a placeholder.
- 2026-10-16: no-input drafts prepared in-file (Highlights, 239-word abstract replacement, Data
  Availability, declaration of interest, AI disclosure, CRediT template, cover-letter skeleton).
  Author input needed: names/affiliations/corresponding author, code license, release tag and
  repository visibility, CRediT assignments, cover letter date and reviewer list. The trimmed abstract
  preserves the matched-versus-as-run content and every corrected number; it has NOT been applied.

## Drafts (prepared 2026-10-16; confirm or edit before use)

These are the no-input pieces of S1. They still need the submitting author's sign-off, plus the items
marked TODO (real names, license, tag). Nothing here has been placed in `paper/` yet — no manuscript
change is made until you approve, except that they carry no task IDs and can be pasted as-is.

### Highlights (5 bullets, each within the 85-character limit)

- Factorial design separates KV compression rate from routing resolution. *(71 chars)*
- Compression lowers error on smooth series, not uniformly across tasks. *(70)*
- Routing granularity, not compression, is the accuracy-sensitive axis on ETTh1. *(78)*
- Per forecast the dense baseline is fastest; full-layer gains do not transfer. *(77)*
- An audit corrects the router work term and downstream energy projections. *(73)*

### Trimmed abstract (239 words; replaces the current 386-word abstract on approval)

> Long-horizon time-series forecasting with Transformers is dominated by the cost of quadratic attention
> over long lookback windows. Compressed-and-indexed attention---compressing the key/value (KV) stream
> and routing each query to a few compressed blocks---reduces this cost, but its design space is rarely
> studied systematically. We treat the family as a two-axis design problem: the KV compression rate
> $c_{KV}$ and the routing resolution $c_R$. Under a frozen direct-96-step protocol with twenty-five
> paired seeds, we run a parameter-equalized $2\times2$ factorial on ETTh1 and a three-way
> comparison---full attention, the equal-rate $(4,4)$ configuration (DeepSeek-V4's Compressed Sparse
> Attention design point), and the dual-rate $(8,4)$ corner---across twelve datasets. Four findings.
> First, on ETTh1 every compressed configuration outperforms full causal attention (mean deltas $-18.8\%$
> to $-27.0\%$, 95/100 paired comparisons, Holm-adjusted $p \le 3.3\times10^{-6}$) at equal or smaller
> parameter count. Second, coarsening the router ($+0.030$ MSE) hurts while coarsening KV compression is
> mildly beneficial ($-0.032$), supporting the decoupling hypothesis (paired Wilcoxon $p = 0.0074$); a
> conditional reading localizes the effect to the fine-content/coarse-router cell, and a three-dataset
> replication did not reproduce the sign structure. Third, the dual-rate corner reduces the attention
> matrix to 48 (+1 sink) columns versus 256 ($5.22\times$) at matching parameters. Fourth, the advantage
> is signal-dependent: smoother, more redundant series benefit most. Routing uses a non-learned hard
> top-$k$ selector (no task gradient to the indexer). Factorial conclusions are statistically
> established at $n{=}25$ on ETTh1; the cross-dataset pattern is descriptive, and latency is reported
> for one development machine.

### Data Availability Statement (draft)

> The code and machine-readable artifacts that reproduce every result in this paper are archived at
> https://github.com/darylfung96/new_attention (release tag: TODO). The frozen task specification, the
> pre-registered factorial manifests, per-run JSONL records, the analysis and figure scripts, and the
> causality/wiring-audit suites are included. Public benchmark datasets are provided as download
> scripts and retain their original licenses and terms. TODO: choose the code license (for example
> MIT) and confirm the repository is public at submission.

### Declaration of interest (draft)

> The authors declare that they have no known competing financial interests or personal relationships
> that could have appeared to influence the work reported in this paper.

### Generative-AI disclosure (draft, neutral wording)

> During the preparation of this work the authors used an AI-based assistant to implement and audit
> analysis scripts and to check the manuscript for internal consistency. After using this tool, the
> authors reviewed and edited the content as needed and take full responsibility for the content of
> the publication.

### CRediT author statement (template — roles need assigning)

> TODO (initials): Conceptualization, Methodology, Software, Validation, Formal analysis,
> Investigation, Data curation, Writing --- original draft, Writing --- review \& editing,
> Visualization, Supervision, Project administration.

### Cover letter skeleton

> Dear Editor, we submit for consideration in <journal> the manuscript "<title>", a two-axis design
> study of compressed-and-indexed attention for long-horizon time-series forecasting (1 paragraph:
> question, frozen protocol, 25 paired seeds, the conditional finding). The manuscript is original,
> not under consideration elsewhere; all authors approved submission. Suggested reviewers: TODO
> (three names, no conflicts).

## What is left

- [ ] Fill the author block and remove the working-draft markers (`TODO:`, `NEEDS VERIFICATION`); the
      repository hygiene check covers the internal names.
- [ ] Write the Highlights (for example: the two-axis factorial design; compression lowers error on
      smooth series; routing granularity is the accuracy-sensitive axis on ETTh1; forecast-required cost
      reverses the full-layer ranking; the accounting audit corrects a fourfold router count).
- [ ] Trim the abstract to about 250 words without dropping the corrected numbers.
- [ ] Add CRediT roles, the Data Availability Statement, the declaration of interest, and the AI
      disclosure if it applies.
- [ ] Tag and archive the release, and link it from the Data Availability Statement.
- [ ] Confirm the review model and any length or figure limits in the current Guide for Authors, then
      write the cover letter and a reviewer list.
- [ ] Rebuild once in the journal's template at revision time (the current build is the preprint layout).

## Acceptance

A submission that satisfies every mandatory declaration, with a tagged release behind the Data
Availability Statement, and no placeholder text anywhere in the manuscript or metadata.

## Evidence pointers

- `paper/main.tex` (author block, statements), `paper/sections/abstract.tex` (word count)
- `paper/scripts/verify_manuscript.py` (hygiene checks, run before every submission)
- `plan/REPRO.md`, `plan/environment-lock.txt` (release scaffolding)

## Log

- 2026-10-16: created after verifying the journal's requirements; the manuscript currently satisfies none
  of the mandatory declarations except the ethics statement.
