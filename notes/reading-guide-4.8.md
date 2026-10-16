# Reading §4.8 from zero — every symbol, with context

Companion explainer for `paper/sections/experiments.tex` §4.8 and `paper/sections/appendix.tex` App. D.
Not part of the paper; written 2026-10-15. Assumes no background. Numbers are the paper's frozen-task
numbers, checked against the released accounts (`plan/gates/gate5/gate5_results.json`).

## The single idea behind every symbol

Every symbol in §4.8 is either (a) a count of how much arithmetic some part of attention performs,
or (b) a rate that sets that count, and the whole section works because those counts can be written
down from the design without running the model. Energy enters through one extra assumption: energy is
proportional to those counts, so a percentage of arithmetic removed becomes a percentage of energy
removed.

## 1. What the model does

The model reads the last **256 time steps** of a signal (for example, ~10 days of hourly readings) and
predicts the next **96**. That is the whole job. The paper compares attention designs inside this
model; attention is the only part that changes between the compared variants.

## 2. What attention is, in one picture

Picture attention as a table. Each time step owns a **row** (the paper calls its owner a **query**,
because it asks a question about the past); in that picture, what a past step advertises for matching
is its **key**, and what it hands over when matched is its **value**. Every time step a query is
allowed to look at is a **column**.

For each column in its row, a query does two things: it compares its own 32 numbers against the
column's 32 numbers to get a match score (a dot product), then adds the column's content into its
answer in proportion to that score (a weighted average). The weights are normalized to sum to 1 —
that normalization is the **softmax** — so "one softmax column" simply means "one thing a query
reads". Reading one column costs **2 × 32 multiply-and-adds**: 32 to score it, 32 to read it.

The model runs **4 independent copies** of this reader in parallel; the paper calls them **heads**.
Each head compares 32 numbers, so the model is 4 × 32 = **128 numbers wide** at every time step.

One **multiply-and-add** is one multiplication plus one addition (a single "dot-product step"). It is
the paper's unit of currency, written **MAC** in the tables, because it is the dominant arithmetic in
attention and it can be counted exactly from the design.

## 3. Why dense attention is expensive

Dense attention lets every query read every column: 256 queries × 256 columns. Each query–column pair
costs 2 × 32 multiply-and-adds per head, and there are 4 heads:

    2 × 4 × 32 × 256 × 256 = 16,777,216        (16.78M: the paper's dense baseline)

The cost grows with the **square** of the context: at 32,768 time steps the same formula gives 274.9
billion. That square is the problem the paper attacks.

## 4. The change the paper studies

The compressed design changes what a query may read and adds a cheap first pass:

- **Blocks.** Every 8 time steps are summarized into one key/value block (one summary card for 8
  steps): 256 / 8 = **32 blocks**. The rate 8 is **c_KV**, the "KV compression rate".
- **Window.** The **16** most recent positions are kept uncompressed in a sliding window, because
  recent detail matters most. This length is **W**.
- **Index tokens and the router.** Separately, every 4 time steps are summarized into a routing
  **index token**: 256 / 4 = **64 index tokens**. Before reading, each query compares itself against
  all 64 index tokens (a cheap 32-number comparison each) and opens the blocks whose index tokens
  scored best; the unopened blocks are masked (given zero weight). The rate 4 is **c_R**, the
  "routing resolution". Two summaries of the same past at two different granularities — that is the
  paper's "decoupling" idea.
- **Sink.** One extra column that means "none of the above", so the weights have somewhere harmless
  to go instead of being forced onto something irrelevant. It is the **+1** in the formulas.

So a query's menu becomes 32 blocks + 16 window positions + 1 sink = **49 columns**, instead of 256.

## 5. Every symbol, one line each

- **L** — context length: how many past time steps the model reads. 256 in the study; up to 131,072
  in the forecast.
- **c_KV** — how many past positions are folded into one key/value block (8 means 8 positions → 1
  block).
- **c_R** — how many past positions one routing index token summarizes (4 means 4 positions → 1
  index token).
- **W** — sliding-window length: recent positions kept uncompressed (16).
- **+1** — the single sink column.
- **h** — number of attention heads = parallel readers (4).
- **d_h** — how many numbers one head compares per position (32).
- **d** — how many numbers per time step in the model (128 = h × d_h).
- **64** — the fixed width the compressor's internal projection uses; a design constant, not a
  variable.
- **2** (leading every cost term) — the two operations per column: score, then read.
- **W_N(L)** — what dense attention costs: a count of multiply-and-adds.
- **W_C(L; c_KV, c_R)** — what the compressed attention path costs, including the router and the
  compressors.
- **S(L)** — the fraction of attention-path work removed, relative to dense.
- **S_∞** — what that fraction becomes as the context becomes enormous ("the limit").
- **S_layer(L; d)** — the fraction removed when the rest of the model layer is also counted.
- **12 d², 4 d², 8 d²** — the per-token cost of the parts that are not attention: 4 d² for the four
  projections, 8 d² for the feed-forward network (MLP).
- **E(θ)** — energy under the paper's model; **θ** is the configuration being evaluated (which
  variant, at which context length); **Σ** means "sum over"; **k** is the bucket index over
  operation types; **n_k(θ)** is how many operations of type k the configuration performs (the counts
  above); **ε_k** is the energy of one such operation — a property of the chip, not the model.
- **O(1), O(L), O(L²)** — shorthand for "grows like a constant / like L / like L squared" as L grows.

Watch out for two different k's: in the energy sum `Σ_k`, k counts operation types; elsewhere the
paper writes "top-k" for how many index tokens the router keeps (16). Same letter, unrelated jobs.

## 6. The formulas, read aloud

**Dense work.** `W_N(L) = 2 × h × d_h × L²` — every one of the L queries reads every one of the L
columns, 2 × 32 multiply-and-adds per column per head, 4 heads. At L = 256: 16.78M.

**Compressed work.** `W_C = term 1 + term 2 + term 3`.

- Term 1: `2 × h × d_h × L × (L/c_KV + W + 1)` — the same read, but each query's menu is now the
  32 blocks + 16 window + 1 sink = 49 columns. At L = 256: 2 × 4 × 32 × 256 × 49 = **3.21M**.
- Term 2: `d × L² / c_R` — the router: each of the 256 queries scores all 64 index tokens, and the
  score runs with every head of the shared query, i.e. `h × d_h = d = 128` multiply-and-adds per
  comparison (a single-head indexer would pay 32). At L = 256: 128 × 256 × 64 = **2.10M**. It still
  grows with L² (queries × index tokens both grow), just with the smaller factor 1/c_R.
- Term 3: `2 × L × d × (64 + d_h)` — building the two summaries (blocks and index tokens). Every
  time step pays a fixed 24,576 multiply-and-adds no matter how long the sequence is: at L = 256,
  **6.29M**. This is the only term that does not grow with the square of context.

Attention path total at L = 256: 3.21 + 2.10 + 6.29 = **11.60M** against dense 16.78M.

**Saving (Equation 3, left half).** `S(L) = 1 − W_C(L) / W_N(L)`, read symbol by symbol:

- `S(L)` — the fraction of attention-path work removed at context length L.
- `1 −` — "whole minus spent": S is a share of dense work, so start from 100% and subtract the
  share still spent.
- `W_C(L)` — the compressed path at the same L: the sum of the three terms above.
- `W_N(L)` — the dense cost at the same L: 2 × h × d_h × L².
- the ratio — the share of dense work the compressed path still spends.

At L = 256: W_C = 11.60M, W_N = 16.78M, ratio = 0.691, so S = 1 − 0.691 = 0.309 → **30.9%**. It looks
modest because the summaries (term 3) are 6.29M of the 11.60M: most of the compressed cost at this
length is bookkeeping (the summaries plus the router), not attention.

**The limit (Equation 3, right half).** `S_∞ = lim as L→∞ of S(L) = 1 − (1/c_KV + 1/(2 c_R))`, read
symbol by symbol:

- `S_∞` — the value S(L) approaches as the context grows without bound.
- `lim as L→∞` — "the value as L grows arbitrarily large"; the curve approaches it and does not
  pass it, rather than necessarily reaching it at any real length.
- `1/c_KV` — the leftover column share: compressed attention reads one column per c_KV dense
  columns, so 1/8 = 12.5% of dense attention work remains.
- `1/(2 c_R)` — the router's added share, unchanged by the head count: 1/(2 × 4) = 1/8 = 12.5%.
- `1 − (…)` — saved = 100% minus those two leftovers = 100 − 12.5 − 12.5 = **75.0%**.

Only those two terms survive because the window offset and the compressor cost fade as L grows (one
is constant in L, the other grows only linearly, while the attention terms grow with L²). The
forecast table shows the climb: 30.9% at L = 256, 74.7% at 32,768, 75.0% at the limit.

A useful rearrangement (one line of algebra, in App. D): with d = h × d_h, the compressed-to-dense
ratio is four shares of dense work,

    1/c_KV  +  (W+1)/L  +  1/(2 c_R)  +  (64 + d_h)/L

At L = 256: 12.5% + 6.6% + 12.5% + 37.5% = 69.1% (saving 30.9%). At L = 32,768 the two 1/L shares
shrink to 0.05% and 0.29%, leaving 25.0% (saving 74.7%). Read it as: of every 100 multiply-and-adds
dense attention does, the compressed design pays 12.5 for the retained columns, a per-length share
for the window and sink, 12.5 for routing, and a per-length share for the summaries.

**Whole layer.** `S_layer` puts the rest of the layer in the denominator. Every time step pays
`12 d² = 12 × 128² = 196,608` multiply-and-adds for the non-attention parts (projections and MLP),
unchanged by the attention design, while dense attention costs `2 × d × L` per token (65,536 at
L = 256). Numerator: attention work removed. Denominator: dense attention + the fixed 196,608. The
same formula gives 7.7% at the frozen L = 256, 50.5% at L = 2,048, and — for a much wider model
(d = 4,096) at 32k context — only 42.7%, because the fixed part grows with the square of the model
width while attention grows linearly with width.

**Energy.** `E(θ) = Σ_k ε_k n_k(θ)` is a shopping bill: for each operation type k, multiply "how many
operations" (n_k) by "energy per operation" (ε_k), and add up. θ is the configuration (which design,
at which context). If all operations cost the same ε, then dense costs ε × 16.78M and compressed
costs ε × 11.60M, and the saved fraction is 1 − 11.60/16.78 = 30.9% — the same number as S, because
the ε appears on both sides and cancels. That is why the paper says the projection is
"coefficient-free": no chip, clock, or process node enters the headline percentages.

## 7. What the paper does and does not claim

The percentages are **projected** from counted arithmetic, not measured joules: the paper runs the
model only at L = 256 and evaluates the formulas for longer contexts (that is the "forecast" — no
retraining, no re-runs). Real hardware also spends energy moving data and idling, so realized savings
will be smaller than these numbers. Two checks show the direction is right: measured run time ranks
with the counted attention work (rank correlation 1.000 and 0.992), and where the comparison is fair
the whole-layer projection lands near the measured end-to-end saving (50.5% projected vs 56.2%
measured at one operating point, 60.8% vs 63.3% at the longer one; the measured saving is
slightly *larger*, which happens because the dense baseline is memory-bound there and spends time
beyond its arithmetic count).

## 8. The chain in one sentence

Count the multiply-and-adds from the design (three terms), take the ratio against dense to get the
work saving, and because energy is assumed proportional to those counts with the same constant on
both sides, the work saving is also the energy saving — under the stated model, and only under it.
