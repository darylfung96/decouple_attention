# Cover letter — draft

Replace every `[bracketed]` field before uploading. The letter is not part of
the manuscript; it goes in the submission system's cover-letter field.
<!-- prose-ok: submission instruction, not an argument -->

---

[Date]

The Editor-in-Chief
[Journal name]

Dear Editor,

We submit for your consideration the manuscript **"Decoupling Compression and
Routing in Attention for Time-Series Forecasting"** by [author list], for
publication as a research article in *[Journal name]*.

**The question.** Compressed-and-indexed attention is now a standard way to cut
the quadratic cost of long-context attention: the key/value stream is compressed
into blocks, and each query is routed to a few of them. Two rates control the
family — the KV compression rate `c_KV` and the routing resolution `c_R` — yet
they are usually fixed together as one hyperparameter, so it is unknown which
axis carries accuracy and which only buys efficiency.

**What we did.** We fix the backbone, the task (direct 96-step forecasting,
ETTh1 and eleven further datasets), and the training protocol, and vary only the
two rates: a pre-registered, parameter-equalized 2×2 factorial over 25 paired
seeds, plus a three-way comparison against full causal attention, a
projection-matched dense control, and an all-block control that removes the
routing selection at identical parameters and arithmetic.

**What we found.** (i) Every compressed configuration beats full causal attention
on the frozen task (mean validation-MSE deltas −18.8% to −27.0%; 95 of 100 paired
seeds; Holm-adjusted *p* ≤ 3.3×10⁻⁶), and the advantage survives the matched
dense retrain. (ii) Coarsening the router costs accuracy while coarsening KV
compression is mildly beneficial (exact Wilcoxon *p* = 0.0074), a decoupling that
localizes to the fine-content/coarse-router cell. (iii) The dual-rate corner
attends to 5.2× fewer columns at equal parameters, and removing its selection
costs 12–27% relative accuracy at equal compute — the router is load-bearing.
(iv) Across twelve datasets the advantage is signal-dependent (8/12 each), which
we state as a boundary rather than a law.

**Why this journal.** The work is a measurement study of efficiency/accuracy
trade-offs in attention for forecasting, with every artifact released and every
number traceable to a manifest — the kind of reproducible systems-and-methods
contribution *[Journal name]* publishes.

**Declarations.** The manuscript is original, has not been published, and is not
under consideration elsewhere. All authors have approved the submission and
declare no competing interests. Code and machine-readable results are archived
at https://github.com/darylfung96/decouple_attention (MIT licence, tag `v1.0.0`).
<!-- prose-ok: required declaration formula -->

Suggested reviewers (no conflicts of interest): [Name, affiliation, email],
[Name, affiliation, email], [Name, affiliation, email].
<!-- prose-ok: list of names the author must supply -->

Thank you for your consideration.
<!-- prose-ok: conventional close of a cover letter -->

Sincerely,

[Corresponding author name]
[Affiliation]
[Email] · [ORCID, if available]
