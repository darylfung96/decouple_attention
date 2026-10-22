# Decoupling Compression and Routing in Attention for Time-Series Forecasting

This repository holds the code, the machine-readable results, and the manuscript
source for a controlled design study of **compressed-and-indexed attention** on
long-horizon time-series forecasting.
<!-- prose-ok: one-sentence repository abstract; expanded below -->

The family shrinks the attention matrix by compressing the key/value stream into
blocks and routing each query to a few of them, and two rates parameterize it:
the **KV compression rate** `c_KV` and the **routing resolution** `c_R`. This
repository fixes the backbone, the task, and the training protocol, varies only
those two rates, and asks which axis carries accuracy and which only buys
efficiency.
<!-- prose-ok: definition paragraph; the design and its results follow -->

**Manuscript:** [`paper/main.pdf`](paper/main.pdf) (33 pp) — LaTeX source in
[`paper/`](paper/).

## Findings in brief

- On ETTh1, every compressed configuration beats full causal attention
  (mean validation-MSE deltas −18.8% to −27.0%; 95/100 paired seeds;
  Holm-adjusted *p* ≤ 3.3×10⁻⁶), and the advantage survives a dense retrain
  whose output projection is matched to the compressed cells' rank.
- Coarsening the router (+0.030 validation MSE) costs accuracy while coarsening
  KV compression (−0.032) is mildly beneficial; the pre-registered decoupling
  hypothesis is supported (exact Wilcoxon *p* = 0.0074) and localizes to the
  fine-content / coarse-router `(4,8)` cell.
- The dual-rate corner `(8,4)` attends to 48 (+1 sink) columns instead of 256
  (5.22×) at 17.6% fewer whole-model MACs on the frozen task; removing the
  routing selection costs 12–27% relative accuracy at identical parameters, so
  the router is load-bearing.
- Across twelve datasets the advantage is signal-dependent (8/12 each), not
  universal: it concentrates on smooth, redundant real series.

## Repository layout

| Path | What it is |
|---|---|
| `attention.py` | Base compressed-and-indexed attention: shared-Q router, two-series compressor, dense masked attention over the sparse selection, causal guards |
| `expert_plus_plus_attention.py` | The dual-rate cell `(8,4)` studied as DRRA |
| `expert_flat_attention.py`, `flat_plus_attention.py`, `modified_attention.py`, `normal_attention.py` | The other configurations, including the full causal baseline |
| `surrogate_attention.py`, `train_surrogate.py` | Separate distillation line of work, not part of the paper's claims |
| `model.py`, `dataset.py` | Shared transformer wrapper and the frozen data pipeline |
| `plan/gates/` | One directory per experiment: frozen `design.md`, runner, `results/*.jsonl` manifests, analysis, log |
| `plan/benchmark_protocol.md`, `plan/environment-lock.txt` | Systems protocol and environment |
| `paper/` | LaTeX source, figures, and the scripts that regenerate and verify them |
| `paper/scripts/verify_numbers.py` | Recomputes the paper's tables and statistics from the manifests (289 checks) |
| `paper/scripts/verify_manuscript.py` | Checks the source for stale values, unresolved references, and internal names |

`pre-publication-tasks/`, `pre-publication_v2_tasks/`, `notes/`, and the dated
`HANDOVER.md` / `RESULTS.md` / `WRITEUP.md` / `PUBLICATION.md` files are the
project's working record. They are kept for provenance and are not part of the
manuscript; `RESULTS.md` and `WRITEUP.md` predate the frozen task and say so at
the top.

## Quick start

Python 3.11, CPU only. The paper's runs used PyTorch 2.6.0 on an 8-thread Apple
M2 (see `requirements.txt`).

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python test_expert_plus_plus.py          # wiring and regression checks
```

## Reproducing the paper

Everything runs on CPU; one 10-epoch run takes ≈ 8 min on the machine above, so
the 125-run factorial is ≈ 17 h.

```bash
# 1. Inspect the factorial design without training (alignment table, no writes)
python plan/gates/gate2/gate2_factorial.py --dry-run

# 2. One cell, one seed
python plan/gates/gate2/gate2_factorial.py --full --cell 8,4 --seed 42

# 3. The factorial: 4 cells x 5 pre-registered seeds (the 20-seed power
#    extension lives in plan/gates/gate7_seeds/). Per-seed appends are restart-safe.
for s in 42 123 2024 7 99; do
  for c in 4,4 8,4 4,8 8,8; do
    python plan/gates/gate2/gate2_factorial.py --full --cell $c --seed $s
  done
done

# 4. Cross-dataset suite: one dataset x one variant x one seed
python plan/gates/gate3/gate3_harness.py --dataset etth1 --variant DRRA --seed 42 --full

# 5. Regenerate every figure from the released manifests
python paper/scripts/make_figures.py --v2

# 6. Verify the manuscript against the manifests, then source hygiene
python paper/scripts/verify_numbers.py     # 289 checks, 0 failures
python paper/scripts/verify_manuscript.py  # 0 failures

# 7. Build the PDF
cd paper && tectonic -X compile main.tex     # or pdflatex -> bibtex -> pdflatex x2
```

Pass `--cell` as `c_kv,c_r`, repeated to run several cells in one invocation.
Gate 3 takes `--variant` from `Normal`, `Flat` (4,4) and `DRRA` (8,4), and
`--dataset` from the twelve names defined in
`plan/gates/gate3/gate3_datasets.py`.
<!-- prose-ok: CLI usage note, not an argument -->

## Data

All twelve datasets are public and fetched by the scripts on first use; no raw
series are committed. The downloader writes a SHA-256 manifest
(`plan/gates/gate3/data/data_manifest.json`) so a run can be checked against the
exact bytes the paper used. Sources: ETT (Zhou et al., 2021),
Electricity/Traffic/Weather/Exchange (Wu et al., 2021; Time-Series Library),
Solar-Energy (Lai et al., 2018). The three synthetic families (sinusoids,
change points, delayed copy) are generated deterministically from fixed seeds,
so a rerun reproduces the same series byte for byte.

## Verification model

Every number in the paper traces to a manifest under `plan/gates/`.
`verify_numbers.py` re-derives 289 of them from those files and fails on any
mismatch; `verify_manuscript.py` fails on stale values, unresolved
`\ref`/`\cite`, missing figures, or internal paths leaking into the manuscript.
The figure scripts re-read the same manifests and assert exact equality with the
released component accounts before drawing, so a figure cannot drift from the
number it illustrates.

## Citation

If you use this code or the released results, please cite the manuscript:

```bibtex
@article{decouple_attention_2026,
  title  = {Decoupling Compression and Routing in Attention for Time-Series Forecasting},
  author = {{decouple_attention authors}},
  year   = {2026},
  note   = {Manuscript; code and results at https://github.com/darylfung96/decouple_attention}
}
```

The author field is a placeholder because the manuscript's author block is not
final yet; update it when it is.

## License

The MIT License (see [`LICENSE`](LICENSE)) covers the code only; manuscript text
and figures remain © the authors, and the public benchmark datasets retain their
original licenses and terms.

## Contact

Open an issue for questions about the code or the released results.
