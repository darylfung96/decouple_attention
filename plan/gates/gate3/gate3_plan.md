# Gate 3 — Dataset-Coverage Expansion: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the frozen direct-96 benchmark from ETTh1-only to 12 datasets (9 real + 3 mechanistic synthetic), run the headline 3-way comparison (Normal vs Flat=(4,4) vs DRRA=(8,4)) with 5 paired seeds per dataset, produce an E-audited summary, update `RESULTS.md` / `plan/paper_notes.md`, and check off §6 in `plan/next_step.md`.

**Architecture:** Reuse the frozen task pipeline (`plan/gates/gate1/gate1_task.md`) and benchmark protocol (`plan/benchmark_protocol.md`) unchanged; add a dataset registry layer (download → cache → parse → split → normalize → window) and a dataset-parameterized training harness that imports the model wrappers verbatim from `model.py` and `plan/gates/gate2/gate2_factorial.py`. Results land as per-dataset JSONL, summarized by a generator that emits integrity audits + comparison tables, mirroring `gate2_summary.md` / `baseline_normal_summary.md`.

**Tech Stack:** Python 3.11 (`/Users/darylfung/.uv_env/py311/bin/python3`; torch 2.6.0, pandas 2.3.3, numpy 1.26.4), CPU PyTorch, Apple M2 (8 cores, 16 GB). No git — file-level checkpoints + `gate3_changes.md` audit log.

**Scope locked (user decisions, 2026-08-18):**
- Dynamics datasets: **Exchange + Solar-Energy** (PEMS08 dropped — third-party provenance only).
- Compute: **one process at a time, `--threads 8`** (matches `benchmark_protocol.md`; Gate-2 log shows this is the fast regime: ~7–13 min/run on ETTh1).
- Horizons/lookbacks: **deferred** — this pass is frozen-task only (L=256, H=96). The H∈{192,336,720} / L∈{512,720,1024} grid becomes a follow-on task.

---

## Data sources (verified reachable 2026-08-18)

| Dataset | Source | Format | Expected shape |
|---|---|---|---|
| etth1 / etth2 | `raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh{1,2}.csv` | csv | 17,420 × 7 |
| ettm1 / ettm2 | `.../ETTm{1,2}.csv` | csv | 69,680 × 7 |
| electricity | `huggingface.co/datasets/thuml/Time-Series-Library/resolve/main/electricity/electricity.csv` | csv | 26,304 × 321 |
| traffic | `.../traffic/traffic.csv` | csv | 17,544 × 862 |
| weather | `.../weather/weather.csv` | csv | 52,696 × 21 |
| exchange | `.../exchange_rate/exchange_rate.csv` | csv | 7,588 × 8 |
| solar | `raw.githubusercontent.com/laiguokun/multivariate-time-series-data/master/solar-energy/solar_AL.txt.gz` | txt.gz (space-separated) | 52,560 × 137 |
| syn_sinusoids / syn_changepoints / syn_delayedcopy | generated deterministically (`gate3_synthetic.py`, seed 0) | csv (no header) | 20,000 × 7 |

If a downloaded shape differs from the expected value, freeze the *measured* value into `gate3_datasets.py` + `gate3_data_test.py` and record the delta in `gate3_changes.md` (expected shapes are provenance assertions, not assumptions to silently pass).

## Frozen task contract (applies verbatim to every dataset; `gate1_task.md`)

- Direct-96: `x [B,256,F]` → `out [B,96,F]`, one forward pass, `loss = MSELoss(out, y)`, pooled, no slicing.
- Chronological 60/20/20 split on the raw-row axis (`floor(0.6N)`, `floor(0.8N)`); no cross-split windows; stride-1 per split.
- Per-feature z-score with stats fit on **train only**; val/test never re-centered. **Zero-std guard:** features with train std < 1e-8 are divided by 1.0 instead (documented deviation for degenerate channels, e.g. some Traffic sensors; the guard only affects normalization of those channels).
- F = dataset channels; wrapper adapts `input_proj Linear(F→128)` and `output_proj Linear(128→H·F)`. Attention modules are F-independent and identical to Gate 2.
- Metrics in standardized units. Determinism: `torch.manual_seed(seed)` before data load and before model init.

## Variants (identical aux contract; params NOT re-equalized across datasets — same stance as the baseline gate, ~2% spread, documented)

| Variant | Model | Notes |
|---|---|---|
| Normal | `model.NormalTimeSeriesModel` (model.py verbatim) | full causal attention; sliding_window=32, o_lora_rank=128 (as-run in baseline gate) |
| Flat | `EPPTimeSeriesModel(F, 4, 4)` from `plan/gates/gate2/gate2_factorial.py`, ranks (64,64) | same object the Gate-2 (4,4) cell used |
| DRRA | `EPPTimeSeriesModel(F, 8, 4)`, ranks (64,64) | champion cell |

Seeds: **{42, 123, 2024, 7, 99}** (paired with Gate 2 / baseline).

## Protocol (identical to `plan/benchmark_protocol.md`)

AdamW lr=1e-4 wd=1e-5 · grad clip 10.0 · batch 32 · **10 epochs fixed** · no scheduler/warm-up/mixed-precision · `torch.set_num_threads(8)` · seed before data load AND model init · val each epoch, final test from epoch-10 weights.

## File map

```
plan/gates/gate3/
├── gate3_plan.md            ← this plan
├── gate3_design.md          ← pre-registered design (Task 1)
├── gate3_datasets.py        ← registry: download/cache/parse/split/normalize + manifest (Task 2)
├── gate3_data_test.py       ← data integrity tests, assert-based, exit-code 0/1 (Task 2)
├── gate3_synthetic.py       ← 3 deterministic mechanistic generators (Task 3)
├── gate3_harness.py         ← dry-run / smoke / full training harness, per-dataset JSONL (Task 4)
├── gate3_sweep.sh           ← sequential sweep driver (Task 6)
├── gate3_summary.py         ← aggregate + audit → gate3_summary.md (Task 7)
├── gate3_changes.md         ← audit log (appended throughout)
├── data/                    ← raw caches + data_manifest.json + syn_*.csv
├── results/                 ← <dataset>.jsonl (180 rows total)
└── gate3_sweep.log          ← sweep log (Task 6)
```

---

## Task 1: Pre-registered design doc (`gate3_design.md`)

**Files:**
- Create: `plan/gates/gate3/gate3_design.md`
- Append: `plan/gates/gate3/gate3_changes.md`

- [ ] **Step 1: Write `gate3_design.md`**

Sections (frozen decisions only; no results):
1. **Status** — "PRE-REGISTERED 2026-08-18; results land in `results/*.jsonl` + `gate3_summary.md`."
2. **Task** — pointer to `gate1_task.md`; explicit extension note: "F is dataset channels (7/321/862/21/8/137/7); all other IN invariants unchanged; 60/20/20 and train-only z-score extend verbatim to every dataset; TSL's 70/10/20 convention is deliberately NOT used (task-consistency)."
3. **Normalization guard** — zero-std → std=1.0 rule.
4. **Datasets** — table from this plan (name, source, expected shape, role: ETT family / large multivariate / different dynamics / mechanistic synthetic).
5. **Synthetic generators** — formulas for the three families (from Task 3 code), N=20,000, seed 0, deterministic; delayed-copy property statement.
6. **Variants + protocol** — tables from this plan; statement that params are not re-equalized across datasets (~2% spread, same stance as baseline gate).
7. **Analysis plan (pre-registered)** — per-dataset 3-way table (val mean±std, test mean, Δ% vs Normal); paired per-seed deltas vs Normal; integrity audit checks (a–d); cross-dataset counts (how many datasets DRRA beats Normal paired, Flat beats Normal paired). Descriptive statistics only — no significance tests (Gate 4). No equivalence claims.
8. **Decisions** — record: dynamics = Exchange + Solar; sequential threads=8; H/L grid deferred; ETTh1 re-run in this sweep (uniform harness table) while Gate-2/baseline rows remain the ETTh1 source for factorial/baseline tables.

- [ ] **Step 2: Cross-check against `gate1_task.md` §7 and `benchmark_protocol.md`** — verify every IN invariant is either preserved or explicitly amended; fix discrepancies in the doc.

- [ ] **Step 3: Create `gate3_changes.md`** with header (gate name, date, scope) and first entry: "Task 1 — design doc pre-registered; file list + scope decisions."

---

## Task 2: Data layer (`gate3_datasets.py` + `gate3_data_test.py`)

**Files:**
- Create: `plan/gates/gate3/gate3_datasets.py`
- Create: `plan/gates/gate3/gate3_data_test.py`
- Create: `plan/gates/gate3/data/` (downloads land here)
- Append: `plan/gates/gate3/gate3_changes.md`

- [ ] **Step 1: Write `gate3_datasets.py`** (complete code):

```python
#!/usr/bin/env python3
"""Gate 3 — dataset registry: download -> cache -> parse -> split -> normalize.

Applies the frozen task pipeline (plan/gates/gate1/gate1_task.md §3-5) to every
dataset: chronological 60/20/20 split on the raw-row axis, per-feature z-score
with stats fit on the TRAIN split only (zero-std guard: train std < 1e-8 is
replaced by 1.0), stride-1 per-split windowing via dataset.ETTForecastDataset.
Raw files are cached under plan/gates/gate3/data/ with a SHA-256 manifest
(data_manifest.json) for provenance (Gate 6 input).

Sources verified reachable 2026-08-18 (see plan/gates/gate3/gate3_plan.md).
"""
import hashlib
import json
import os
import urllib.request

import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MANIFEST_PATH = os.path.join(DATA_DIR, "data_manifest.json")
LOOKBACK = 256
HORIZON = 96
ZERO_STD_EPS = 1e-8

# name -> (url, fmt, expected_rows, expected_features)
DATASETS = {
    "etth1": ("https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv",
              "csv", 17420, 7),
    "etth2": ("https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh2.csv",
              "csv", 17420, 7),
    "ettm1": ("https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTm1.csv",
              "csv", 69680, 7),
    "ettm2": ("https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTm2.csv",
              "csv", 69680, 7),
    "electricity": ("https://huggingface.co/datasets/thuml/Time-Series-Library/resolve/main/"
                    "electricity/electricity.csv", "csv", 26304, 321),
    "traffic": ("https://huggingface.co/datasets/thuml/Time-Series-Library/resolve/main/"
                "traffic/traffic.csv", "csv", 17544, 862),
    "weather": ("https://huggingface.co/datasets/thuml/Time-Series-Library/resolve/main/"
                "weather/weather.csv", "csv", 52696, 21),
    "exchange": ("https://huggingface.co/datasets/thuml/Time-Series-Library/resolve/main/"
                 "exchange_rate/exchange_rate.csv", "csv", 7588, 8),
    "solar": ("https://raw.githubusercontent.com/laiguokun/multivariate-time-series-data/"
              "master/solar-energy/solar_AL.txt.gz", "txt.gz", 52560, 137),
}


def download(name, force=False):
    """Cache the raw bytes at data/raw_<name>; return the local path."""
    url, fmt, exp_rows, exp_feats = DATASETS[name]
    path = os.path.join(DATA_DIR, "raw_" + name)
    if os.path.exists(path) and not force:
        return path
    os.makedirs(DATA_DIR, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 gate3-fetch"})
    with urllib.request.urlopen(req, timeout=180) as r, open(path, "wb") as f:
        f.write(r.read())
    return path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_raw(name):
    """Parse raw bytes -> float64 ndarray [N, F]; drop non-numeric columns with a log line."""
    url, fmt, exp_rows, exp_feats = DATASETS[name]
    path = download(name)
    if fmt == "txt.gz":
        df = pd.read_csv(path, sep=r"\s+", header=None, compression="gzip")
    else:
        df = pd.read_csv(path)
    num = df.select_dtypes(include=[np.number])
    dropped = [str(c) for c in df.columns if c not in num.columns]
    if dropped:
        print(f"[gate3_datasets] {name}: dropped non-numeric columns: {dropped}")
    data = num.values.astype(np.float64)
    if data.shape != (exp_rows, exp_feats):
        raise RuntimeError(f"{name}: expected shape {(exp_rows, exp_feats)}, got {data.shape}")
    if not np.isfinite(data).all():
        raise RuntimeError(f"{name}: non-finite values present")
    return data


def preprocess(name):
    """Split 60/20/20 on raw rows; train-only per-feature z-score (zero-std guard).

    Returns (train, val, test) float32 [n, F] arrays in standardized units + stats dict.
    """
    data = load_raw(name)
    n = len(data)
    s1, s2 = int(n * 0.6), int(n * 0.8)
    tr, va, te = data[:s1], data[s1:s2], data[s2:]
    mean, std = tr.mean(axis=0), tr.std(axis=0)
    std = np.where(std < ZERO_STD_EPS, 1.0, std)
    return ((tr - mean) / std).astype(np.float32), \
           ((va - mean) / std).astype(np.float32), \
           ((te - mean) / std).astype(np.float32), {"mean": mean, "std": std}


def window_counts(name):
    tr, va, te, _ = preprocess(name)
    return {k: max(0, len(d) - LOOKBACK - HORIZON + 1)
            for k, d in [("train", tr), ("val", va), ("test", te)]}


def build_manifest():
    """Download all datasets (cache-aware), record sha256/shape/source -> data_manifest.json."""
    os.makedirs(DATA_DIR, exist_ok=True)
    manifest = {}
    for name, (url, fmt, exp_rows, exp_feats) in DATASETS.items():
        path = download(name)
        sha = sha256_file(path)
        rows, feats = load_raw(name).shape
        manifest[name] = {"source": url, "raw_file": os.path.basename(path),
                          "sha256": sha, "rows": rows, "features": feats}
        print(f"  {name}: {rows}x{feats} sha256={sha[:16]}...")
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return manifest


def integrity(name):
    """Return dict of boolean checks (used by gate3_data_test.py)."""
    url, fmt, exp_rows, exp_feats = DATASETS[name]
    data = load_raw(name)
    tr, va, te, _ = preprocess(name)
    z_std = tr.std(axis=0)
    return {
        "shape": data.shape == (exp_rows, exp_feats),
        "finite": bool(np.isfinite(data).all()),
        "splits_positive": all(len(d) > LOOKBACK + HORIZON for d in (tr, va, te)),
        "splits_cover": len(tr) + len(va) + len(te) == len(data),
        "train_zmean": bool(np.abs(tr.mean(axis=0)).max() < 1e-4),
        "train_zstd": bool(np.all((z_std < ZERO_STD_EPS) | (np.abs(z_std - 1.0) < 1e-3))),
    }


def main():
    import argparse
    p = argparse.ArgumentParser(description="Gate 3 dataset registry CLI")
    p.add_argument("--fetch-all", action="store_true", help="download all + write manifest")
    p.add_argument("--check", nargs="*", default=None, help="integrity checks for names "
                   "(default: all)")
    args = p.parse_args()
    names = args.check if args.check is not None else list(DATASETS)
    if args.fetch_all:
        build_manifest()
    for n in names:
        ok = integrity(n)
        print(f"{n}: " + " ".join(f"{k}={v}" for k, v in ok.items()))
        if not all(ok.values()):
            raise SystemExit(f"integrity FAILED for {n}")
    print("ALL INTEGRITY CHECKS PASS")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `gate3_data_test.py`** (assert-based; exit 0 on pass):

```python
#!/usr/bin/env python3
"""Gate 3 data-layer tests — assert-based, prints PASS/FAIL, exit code reflects result."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import gate3_datasets as g3

FAILURES = []


def check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}" + (f"  ({detail})" if detail else ""))
    if not cond:
        FAILURES.append(label)


def test_shape_and_finite():
    for name in g3.DATASETS:
        data = g3.load_raw(name)
        check(f"{name}: shape", data.shape == (g3.DATASETS[name][2], g3.DATASETS[name][3]),
              f"got {data.shape}")
        check(f"{name}: finite", bool(np.isfinite(data).all()))


def test_preprocess_contract():
    for name in g3.DATASETS:
        tr, va, te, stats = g3.preprocess(name)
        n = len(g3.load_raw(name))
        check(f"{name}: split sizes", len(tr) == int(n * 0.6) and len(va) == int(n * 0.8) - int(n * 0.6)
              and len(te) == n - int(n * 0.8))
        check(f"{name}: disjoint+cover", len(tr) + len(va) + len(te) == n)
        z_std = tr.std(axis=0)
        check(f"{name}: train z-mean~0", float(np.abs(tr.mean(axis=0)).max()) < 1e-4)
        check(f"{name}: train z-std (1 or guarded)", bool(
            np.all((z_std < g3.ZERO_STD_EPS) | (np.abs(z_std - 1.0) < 1e-3))))
        check(f"{name}: window counts > 0", all(v > 0 for v in g3.window_counts(name).values()),
              str(g3.window_counts(name)))


def test_determinism():
    for name in g3.DATASETS:
        a = g3.preprocess(name)[:3]
        b = g3.preprocess(name)[:3]
        check(f"{name}: deterministic preprocess",
              all(np.array_equal(x, y) for x, y in zip(a, b)))


def test_manifest():
    if os.path.exists(g3.MANIFEST_PATH):
        import json
        with open(g3.MANIFEST_PATH) as f:
            m = json.load(f)
        for name, info in m.items():
            check(f"{name}: manifest sha256 matches", g3.sha256_file(os.path.join(g3.DATA_DIR, info["raw_file"])) == info["sha256"])
            check(f"{name}: manifest shape matches", (info["rows"], info["features"]) == (g3.DATASETS[name][2], g3.DATASETS[name][3]))
    else:
        print("[SKIP] manifest tests — data_manifest.json not present yet")


if __name__ == "__main__":
    test_shape_and_finite()
    test_preprocess_contract()
    test_determinism()
    test_manifest()
    if FAILURES:
        print(f"\n{len(FAILURES)} CHECK(S) FAILED")
        sys.exit(1)
    print("\nALL DATA TESTS PASS")
```

- [ ] **Step 3: Run the tests**

Run: `/Users/darylfung/.uv_env/py311/bin/python3 plan/gates/gate3/gate3_data_test.py`
Expected: all PASS (shape checks verify expected rows×features); if a shape mismatches, freeze the measured value into `DATASETS` and note the delta in `gate3_changes.md` before proceeding.

- [ ] **Step 4: Fetch all raw files and write the manifest**

Run: `/Users/darylfung/.uv_env/py311/bin/python3 plan/gates/gate3/gate3_datasets.py --fetch-all`
Expected: 9 lines `  <name>: <rows>x<feats> sha256=<16 hex>...` then nothing else; `data/data_manifest.json` created; re-run the tests → manifest checks PASS.

- [ ] **Step 5: Record task in `gate3_changes.md`** (dataset registry + manifest + tests; note any shape deltas).

---

## Task 3: Synthetic generators (`gate3_synthetic.py`)

**Files:**
- Create: `plan/gates/gate3/gate3_synthetic.py`
- Create: `plan/gates/gate3/data/syn_{sinusoids,changepoints,delayedcopy}.csv` (generated)
- Append: `plan/gates/gate3/gate3_changes.md`

- [ ] **Step 1: Write `gate3_synthetic.py`** (complete code):

```python
#!/usr/bin/env python3
"""Gate 3 — mechanistic synthetic datasets (deterministic, seed 0).

Three families, each N=20,000 rows x 7 channels, written as headerless numeric
CSVs to plan/gates/gate3/data/syn_<name>.csv and consumed by the SAME
gate3_datasets pipeline (60/20/20 split, train-only z-score, stride-1 windows).

1. syn_sinusoids    x_c(t) = A_c sin(2*pi*t/T_c + phi_c) + eps, eps~N(0, 0.1^2)
                     T = [24, 48, 96, 168, 336, 720, 1440]  (daily..2-month)
                     A = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]
                     phi = [0, .5, 1, 1.5, 2, 2.5, 3]
2. syn_changepoints piecewise-constant mean; change points at t = 2000, 4000,
                     ..., 18000; each channel's level shifts by N(0,1) at each
                     boundary; noise sigma 0.1. (Probes post-change adaptation.)
3. syn_delayedcopy  channels periodic with period = lag in [96, 128, 168, 224,
                     256] (5 channels) + 2 pure-noise channels. A period-L
                     channel satisfies y[t+1..t+96] = x[t+1-L .. t+96-L] for
                     L in [96, 256] (copy property, fully in-window) — probes
                     whether routed/compressed attention can reproduce
                     exact-offset in-window content at block granularity.

Determinism: same seed -> byte-identical CSV (SHA-256 recorded in the manifest
on --regenerate).
"""
import argparse
import hashlib
import os

import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
N = 20000
CHANNELS = 7
SEED = 0
NOISE_SIGMA = 0.1


def gen_sinusoids():
    rng = np.random.default_rng(SEED)
    t = np.arange(N, dtype=np.float64)[:, None]
    periods = np.array([24, 48, 96, 168, 336, 720, 1440], dtype=np.float64)
    amps = np.array([1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2])
    phases = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
    x = amps * np.sin(2.0 * np.pi * t / periods + phases)
    return x + NOISE_SIGMA * rng.standard_normal((N, CHANNELS))


def gen_changepoints():
    rng = np.random.default_rng(SEED)
    nseg = N // 2000 + 1
    seg_levels = np.cumsum(rng.standard_normal((nseg, CHANNELS)), axis=0)
    seg = np.minimum(np.arange(N) // 2000, nseg - 1)
    x = seg_levels[seg]
    return x + NOISE_SIGMA * rng.standard_normal((N, CHANNELS))


def gen_delayedcopy():
    rng = np.random.default_rng(SEED)
    t = np.arange(N, dtype=np.float64)[:, None]
    lags = np.array([96, 128, 168, 224, 256], dtype=np.float64)
    phases = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    copy = np.sin(2.0 * np.pi * t / lags + phases)   # period = lag => copy property
    x = np.zeros((N, CHANNELS))
    x[:, :5] = copy
    x[:, 5:] = NOISE_SIGMA * rng.standard_normal((N, 2))  # unpredictable channels
    return x


GENERATORS = {"sinusoids": gen_sinusoids, "changepoints": gen_changepoints,
              "delayedcopy": gen_delayedcopy}


def write_all():
    os.makedirs(DATA_DIR, exist_ok=True)
    hashes = {}
    for name, gen in GENERATORS.items():
        path = os.path.join(DATA_DIR, f"syn_{name}.csv")
        np.savetxt(path, gen(), fmt="%.8f", delimiter=",")
        hashes[name] = hashlib.sha256(open(path, "rb").read()).hexdigest()
        print(f"  syn_{name}: {N}x{CHANNELS} sha256={hashes[name][:16]}...")
    return hashes


def check_all():
    bad = []
    for name, gen in GENERATORS.items():
        path = os.path.join(DATA_DIR, f"syn_{name}.csv")
        if not os.path.exists(path):
            bad.append(f"syn_{name}: missing")
            continue
        x = np.loadtxt(path, delimiter=",")
        if x.shape != (N, CHANNELS):
            bad.append(f"syn_{name}: shape {x.shape}")
            continue
        if not np.array_equal(x, gen()):
            bad.append(f"syn_{name}: not deterministic (regeneration differs)")
    if bad:
        raise SystemExit("\n".join(bad))
    print("ALL SYNTHETIC CHECKS PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Gate 3 synthetic datasets")
    p.add_argument("--regenerate", action="store_true", help="(re)write the 3 CSVs")
    args = p.parse_args()
    if args.regenerate:
        write_all()
    check_all()
```

- [ ] **Step 2: Generate and verify**

Run: `/Users/darylfung/.uv_env/py311/bin/python3 plan/gates/gate3/gate3_synthetic.py --regenerate`
Expected: 3 lines `  syn_<name>: 20000x7 sha256=<16 hex>...` then `ALL SYNTHETIC CHECKS PASS`.
Re-run without `--regenerate` → `ALL SYNTHETIC CHECKS PASS` (determinism proof: byte-identical regeneration).

- [ ] **Step 3: Register synthetics in the pipeline** — add the 3 datasets to `gate3_datasets.DATASETS` (source = local file path, fmt "csv", 20000×7; `download()` copies them into the cache if missing — reuse the local file directly by returning its path when `raw_<name>` is absent). Simplest correct approach: `download()` special-cases `url.startswith("file://")`; entry: `("file://plan/gates/gate3/data/syn_sinusoids.csv", "csv", 20000, 7)`.

- [ ] **Step 4: Re-run `gate3_data_test.py`** → all PASS for the 3 synthetic names too; `--fetch-all` writes their manifest rows.

- [ ] **Step 5: Record in `gate3_changes.md`** (generator formulas, determinism proof, pipeline registration).

---

## Task 4: Training harness (`gate3_harness.py`)

**Files:**
- Create: `plan/gates/gate3/gate3_harness.py`
- Append: `plan/gates/gate3/gate3_changes.md`

- [ ] **Step 1: Write `gate3_harness.py`** (complete code):

```python
#!/usr/bin/env python3
"""Gate 3 — dataset-coverage training harness (frozen direct-96 task).

Variants (aux contract identical to Gate 2 / baseline gates):
  Normal : model.NormalTimeSeriesModel  (model.py verbatim, as run in baseline gate)
  Flat   : EPPTimeSeriesModel(F, 4, 4)  (imported verbatim from
           plan/gates/gate2/gate2_factorial.py; ranks (64,64))
  DRRA   : EPPTimeSeriesModel(F, 8, 4)  (champion cell; ranks (64,64))

Protocol (plan/benchmark_protocol.md, byte-identical to gate2_factorial.py):
  AdamW lr=1e-4 wd=1e-5, grad clip 10.0, batch 32, 10 epochs FIXED, no
  scheduler/warm-up/mixed-precision, threads=8, paired seeds {42,123,2024,7,99};
  torch.manual_seed(seed) before data load AND model init.
  Task: direct-96, L=256, H=96, F=dataset channels, pooled [B,H,F] MSE,
  standardized units (plan/gates/gate1/gate1_task.md).

CLI modes:
  --dry-run : print dataset/variant config + verified param counts. No training.
  --smoke   : 1 epoch on bounded subsets (first 40*32 train, 10*32 val); prints
              train/val MSE + estimated full-run time; saves nothing.
  --full    : 10 epochs, full train split (shuffle=True), val each epoch, final
              test; APPENDS one JSON line to plan/gates/gate3/results/<dataset>.jsonl
              (idempotent per (variant, seed)).

Exit codes: 0 on success; non-zero (traceback/message) on failure.
"""
import argparse
import datetime
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset

from model import NormalTimeSeriesModel
from dataset import ETTForecastDataset
import gate3_datasets as g3
from plan.gates.gate2.gate2_factorial import EPPTimeSeriesModel

# ── Frozen task constants (plan/gates/gate1/gate1_task.md) ─────────────────────
LOOKBACK = 256
HORIZON = 96
BATCH_SIZE = 32

# ── Protocol (plan/benchmark_protocol.md) ──────────────────────────────────────
HIDDEN_SIZE = 128
LR = 1e-4
WEIGHT_DECAY = 1e-5
CLIP = 10.0
EPOCHS = 10
SEEDS = [42, 123, 2024, 7, 99]
RANKS = (64, 64)                      # Gate-2 equalized q/o ranks for both cells

# ── Variants ───────────────────────────────────────────────────────────────────
VARIANT_CELLS = {"Normal": None, "Flat": (4, 4), "DRRA": (8, 4)}

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
SMOKE_TRAIN_BATCHES = 40
SMOKE_VAL_BATCHES = 10


def build_model(dataset_name, variant, seed):
    F = g3.DATASETS[dataset_name][3]
    torch.manual_seed(seed)           # determinism: seed before model init
    if variant == "Normal":
        return NormalTimeSeriesModel(num_features=F, hidden_size=HIDDEN_SIZE,
                                     lookback=LOOKBACK, horizon=HORIZON)
    ckv, c_r = VARIANT_CELLS[variant]
    return EPPTimeSeriesModel(F, ckv, c_r, q_lora_rank=RANKS[0], o_lora_rank=RANKS[1])


def count_attn_params(model):
    return sum(p.numel() for p in model.attn.parameters())


def count_full_params(model):
    return sum(p.numel() for p in model.parameters())


def make_loaders(dataset_name, seed, smoke):
    """Seed BEFORE data loading (shuffle order comes from torch RNG)."""
    torch.manual_seed(seed)
    tr, va, te, _ = g3.preprocess(dataset_name)
    mk = lambda d: ETTForecastDataset(d, lookback=LOOKBACK, horizon=HORIZON)
    train_ds, val_ds, test_ds = mk(tr), mk(va), mk(te)
    if smoke:
        train_ds = Subset(train_ds, range(SMOKE_TRAIN_BATCHES * BATCH_SIZE))
        val_ds = Subset(val_ds, range(SMOKE_VAL_BATCHES * BATCH_SIZE))
        return (DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True),
                DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False), None)
    return (DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True),
            DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False),
            DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False))


@torch.no_grad()
def evaluate(model, loader):
    model.eval()
    total, n = 0.0, 0
    for x, y in loader:
        out = model(x)
        assert out.shape == (x.shape[0], HORIZON, x.shape[2]), \
            f"bad output shape {tuple(out.shape)}"
        total += F.mse_loss(out, y).item() * x.shape[0]
        n += x.shape[0]
    return total / n if n else float("nan")


def train_and_eval(model, train_loader, val_loader, test_loader, epochs):
    """AdamW lr=1e-4 wd=1e-5, grad clip 10.0. Returns (train, val, test) MSE."""
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    final_train, final_val = None, None
    for epoch in range(1, epochs + 1):
        model.train()
        total, n = 0.0, 0
        for x, y in train_loader:
            optimizer.zero_grad()
            out = model(x)
            assert out.shape == (x.shape[0], HORIZON, x.shape[2]), \
                f"bad output shape {tuple(out.shape)}"
            loss = F.mse_loss(out, y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            optimizer.step()
            total += loss.item() * x.shape[0]
            n += x.shape[0]
        final_train = total / n
        final_val = evaluate(model, val_loader)
        print(f"      epoch {epoch:2d}/{epochs}  train_mse={final_train:.6f}  "
              f"val_mse={final_val:.6f}")
    test_mse = evaluate(model, test_loader) if test_loader is not None else None
    return final_train, final_val, test_mse


def load_completed(results_path):
    done = set()
    if os.path.exists(results_path):
        with open(results_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    done.add((rec["variant"], int(rec["seed"])))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    return done


def append_result(results_path, rec):
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def results_path(dataset_name):
    return os.path.join(RESULTS_DIR, f"{dataset_name}.jsonl")


def print_config(dataset_name, variant, seed, threads, smoke=False):
    F = g3.DATASETS[dataset_name][3]
    print(f"== Gate 3 harness (CPU PyTorch, threads={threads}, dataset={dataset_name}, "
          f"variant={variant}, seed={seed}, F={F}) ==")
    print(f"  task: frozen direct-96, L={LOOKBACK}, H={HORIZON}, batch={BATCH_SIZE}")
    print(f"  protocol: AdamW lr={LR} wd={WEIGHT_DECAY} clip={CLIP} epochs={EPOCHS} "
          f"(fixed), no scheduler/warm-up, fp32")
    wc = g3.window_counts(dataset_name)
    print(f"  windows: train={wc['train']} val={wc['val']} test={wc['test']} "
          f"(batches: {wc['train'] // BATCH_SIZE} / {wc['val'] // BATCH_SIZE} / "
          f"{wc['test'] // BATCH_SIZE})")


def run_dry_run(dataset_name, variant):
    print_config(dataset_name, variant, 42, 8)
    model = build_model(dataset_name, variant, seed=42)
    print(f"  params: attn={count_attn_params(model)} full={count_full_params(model)}")
    return 0


def run_smoke(dataset_name, variant, seed, threads):
    print_config(dataset_name, variant, seed, threads, smoke=True)
    t0 = time.time()
    train_loader, val_loader, _ = make_loaders(dataset_name, seed, smoke=True)
    print(f"[smoke] train batches={len(train_loader)} val batches={len(val_loader)}")
    model = build_model(dataset_name, variant, seed)
    print(f"  params: attn={count_attn_params(model)} full={count_full_params(model)}")
    train_mse, val_mse, _ = train_and_eval(model, train_loader, val_loader, None, epochs=1)
    dt = time.time() - t0
    per_batch = dt / len(train_loader)
    full_batches = g3.window_counts(dataset_name)["train"] // BATCH_SIZE
    est_min = per_batch * full_batches * EPOCHS / 60.0
    print(f"      smoke train_mse={train_mse:.6f} val_mse={val_mse:.6f}")
    print(f"      [estimate] {per_batch:.2f} s/batch -> full 10-epoch run ~{est_min:.0f} min")
    print("[smoke] done — nothing saved")
    return 0


def run_full(dataset_name, variant, seed, threads):
    print_config(dataset_name, variant, seed, threads)
    path = results_path(dataset_name)
    done = load_completed(path)
    if (variant, seed) in done:
        print(f"[full] ({variant}, seed={seed}) already completed — skipping (idempotent)")
        return 0
    train_loader, val_loader, test_loader = make_loaders(dataset_name, seed, smoke=False)
    print(f"[full] train batches={len(train_loader)} val batches={len(val_loader)} "
          f"test batches={len(test_loader)}")
    t0 = time.time()
    model = build_model(dataset_name, variant, seed)
    final_train, final_val, test_mse = train_and_eval(
        model, train_loader, val_loader, test_loader, epochs=EPOCHS)
    rec = {
        "dataset": dataset_name,
        "variant": variant,
        "cell": list(VARIANT_CELLS[variant]) if VARIANT_CELLS[variant] else None,
        "seed": seed,
        "val_mse": round(final_val, 8),
        "test_mse": round(test_mse, 8),
        "final_train_mse": round(final_train, 8),
        "attn_params": count_attn_params(model),
        "full_params": count_full_params(model),
        "n_train_batches": len(train_loader),
        "n_val_batches": len(val_loader),
        "n_test_batches": len(test_loader),
        "completed_utc": datetime.datetime.now(datetime.timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    append_result(path, rec)
    print(f"      FINAL test_mse={test_mse:.6f} train_mse={final_train:.6f} "
          f"(elapsed {time.time() - t0:.0f}s)")
    print(f"      appended: {json.dumps(rec)}")
    return 0


def main():
    p = argparse.ArgumentParser(description="Gate 3 dataset-coverage harness")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    p.add_argument("--dataset", required=True, choices=sorted(g3.DATASETS))
    p.add_argument("--variant", required=True, choices=sorted(VARIANT_CELLS))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--threads", type=int, default=8)
    args = p.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)

    if args.full:
        return run_full(args.dataset, args.variant, args.seed, args.threads)
    if args.smoke:
        return run_smoke(args.dataset, args.variant, args.seed, args.threads)
    return run_dry_run(args.dataset, args.variant)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Dry-run every dataset × variant** (param-count registry)

Run (loop): `for ds in etth1 etth2 ettm1 ettm2 electricity traffic weather exchange solar syn_sinusoids syn_changepoints syn_delayedcopy; do for v in Normal Flat DRRA; do python3 plan/gates/gate3/gate3_harness.py --dry-run --dataset $ds --variant $v; done; done`
Expected: 36 config blocks, each with `params: attn=... full=...`; no exceptions. Record the per-dataset param table in `gate3_changes.md` (Normal attn 102,496 on F=7; Flat/DRRA attn 95,652/95,652 — F-independent; full params scale with F).

- [ ] **Step 3: Smoke one dataset per family** — `--smoke --dataset etth1 --variant DRRA --seed 42` and `--smoke --dataset traffic --variant Normal --seed 42` and `--smoke --dataset solar --variant Flat --seed 42`. Expected: 1 epoch prints train/val MSE + `[estimate] ... min`; assert shapes pass (no assertion errors); smoke saves nothing. Use the estimates to sanity-check the runtime table below.

- [ ] **Step 4: Record in `gate3_changes.md`** (harness created; param table; smoke estimates).

---

## Task 5: Smoke all 12 datasets (full matrix, 1 epoch)

**Files:** (none new; log evidence into `gate3_changes.md`)

- [ ] **Step 1: Run smoke for all 36 (dataset, variant) combos at seed 42**

Run: `for ds in <all 12>; do for v in Normal Flat DRRA; do python3 -u plan/gates/gate3/gate3_harness.py --smoke --dataset $ds --variant $v --seed 42 --threads 8; done; done 2>&1 | tee plan/gates/gate3/gate3_smoke.log`
Expected: 36 blocks; every block ends with a finite `smoke train_mse` / `smoke val_mse` and an `[estimate]` line; no tracebacks. ~1–3 min per block → ~1 h total.

- [ ] **Step 2: Audit the smoke log** — no `FAIL`, no NaN, no assertion errors; per-family estimate column sanity (ETT hourly ≈ 7–15 min/run; ETTm ≈ 30–50; electricity/traffic/weather/solar within a factor ~2 of the budget table; exchange < 5 min; synthetic ≈ 10–15).

- [ ] **Step 3: Freeze the measured runtime table into `gate3_changes.md`** — this is the launch-time budget for the sweep (Task 6) and gets reported in `gate3_summary.md` for reproducibility.

---

## Task 6: Launch the sequential sweep (background)

**Files:**
- Create: `plan/gates/gate3/gate3_sweep.sh`
- Create: `plan/gates/gate3/gate3_sweep.log` (job output)

- [ ] **Step 1: Write `gate3_sweep.sh`** (complete code):

```bash
#!/bin/bash
# Gate 3 sequential sweep — one process at a time, threads=8 (benchmark_protocol).
# Log: plan/gates/gate3/gate3_sweep.log ; results: plan/gates/gate3/results/*.jsonl
# Idempotent: completed (variant, seed) rows are skipped on rerun.
cd "$(dirname "$0")/../../.." || exit 9
PY="${PYTHON:-python3}"
HARNESS="plan/gates/gate3/gate3_harness.py"
DATASETS="etth1 etth2 ettm1 ettm2 electricity traffic weather exchange solar syn_sinusoids syn_changepoints syn_delayedcopy"
VARIANTS="Normal Flat DRRA"
SEEDS="42 123 2024 7 99"
for ds in $DATASETS; do
  for v in $VARIANTS; do
    for s in $SEEDS; do
      echo "=== $ds $v seed=$s START $(date -u +%FT%TZ) ==="
      $PY -u "$HARNESS" --full --dataset "$ds" --variant "$v" --seed "$s" --threads 8 \
        || echo "FAIL $ds $v $s rc=$?"
      echo "=== $ds $v seed=$s DONE $(date -u +%FT%TZ) ==="
    done
  done
done
echo "SWEEP_DONE $(date -u +%FT%TZ)"
```

- [ ] **Step 2: Launch** — `bash plan/gates/gate3/gate3_sweep.sh` as a **background job** with output redirected to `plan/gates/gate3/gate3_sweep.log` (the script's own echo lines go to stdout; redirect at launch). Record the job id. Expected duration: **~45–60 h** (sequential, threads=8).

- [ ] **Step 3: First-hour checkpoint** — after ~1 h, verify: log shows `=== etth1 Normal seed=42 START` … `DONE` cycle advancing; no `FAIL` lines; `results/etth1.jsonl` growing; ETTh1 per-run time in the expected range (else kill + diagnose before 45 h burn).

---

## Task 7: Summary generator (`gate3_summary.py`) — written while the sweep runs

**Files:**
- Create: `plan/gates/gate3/gate3_summary.py`
- Append: `plan/gates/gate3/gate3_changes.md` (when complete)

- [ ] **Step 1: Write `gate3_summary.py`** (complete code):

```python
#!/usr/bin/env python3
"""Gate 3 summary generator — reads results/*.jsonl, emits gate3_summary.md.

Outputs per-dataset 3-way tables (val mean±std, test mean, Δ% vs Normal),
paired per-seed val deltas vs Normal, integrity audit (rows/seeds/dups/params/
train-range), and cross-dataset counts. Descriptive statistics only (Gate 4
does significance tests). Exit code 0 iff all integrity checks pass.
"""
import json
import os
import statistics as st

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
OUT_PATH = os.path.join(HERE, "gate3_summary.md")
SEEDS = [42, 123, 2024, 7, 99]
VARIANTS = ["Normal", "Flat", "DRRA"]
CELL_OF = {"Normal": None, "Flat": (4, 4), "DRRA": (8, 4)}
DATASET_ORDER = ["etth1", "etth2", "ettm1", "ettm2", "electricity", "traffic",
                 "weather", "exchange", "solar",
                 "syn_sinusoids", "syn_changepoints", "syn_delayedcopy"]

import gate3_datasets as g3
sys_path_ok = True


def load_rows(dataset):
    path = os.path.join(RESULTS_DIR, f"{dataset}.jsonl")
    rows = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def expected_params(dataset, variant):
    """Recompute attn/full params with seed 42 (harness build_model)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("g3h", os.path.join(HERE, "gate3_harness.py"))
    # simpler: reimplement the two counts via the same builders
    from model import NormalTimeSeriesModel
    from plan.gates.gate2.gate2_factorial import EPPTimeSeriesModel
    F = g3.DATASETS[dataset][3]
    torch.manual_seed(42)
    if variant == "Normal":
        m = NormalTimeSeriesModel(num_features=F, hidden_size=128, lookback=256, horizon=96)
    else:
        ckv, c_r = CELL_OF[variant]
        m = EPPTimeSeriesModel(F, ckv, c_r, q_lora_rank=64, o_lora_rank=64)
    return (sum(p.numel() for p in m.attn.parameters()),
            sum(p.numel() for p in m.parameters()))


def audit(dataset):
    rows = load_rows(dataset)
    issues = []
    by_key = {}
    for r in rows:
        by_key[(r["variant"], r["seed"])] = r
    for v in VARIANTS:
        for s in SEEDS:
            if (v, s) not in by_key:
                issues.append(f"missing ({v}, seed={s})")
    dups = len(rows) - len(by_key)
    if dups:
        issues.append(f"{dups} duplicate (variant, seed) rows")
    for v in VARIANTS:
        exp = expected_params(dataset, v)
        for s in SEEDS:
            r = by_key.get((v, s))
            if r and (r["attn_params"], r["full_params"]) != exp:
                issues.append(f"{v} seed={s} params {r['attn_params']}/{r['full_params']} "
                              f"!= expected {exp}")
    med = st.median([r["final_train_mse"] for r in rows]) if rows else float("nan")
    for r in rows:
        if not all(map(lambda x: x == x, [r["val_mse"], r["test_mse"], r["final_train_mse"]])):
            issues.append(f"{r['variant']} seed={r['seed']} non-finite MSE")
        elif med == med and not (0.5 * med <= r["final_train_mse"] <= 2.0 * med):
            issues.append(f"{r['variant']} seed={r['seed']} train_mse {r['final_train_mse']:.4f} "
                          f"outside [0.5,2.0]x median {med:.4f}")
    return issues, by_key


def agg(variant_rows):
    vals = [r["val_mse"] for r in variant_rows]
    tests = [r["test_mse"] for r in variant_rows]
    return (st.mean(vals), st.stdev(vals) if len(vals) > 1 else 0.0,
            st.mean(tests), st.stdev(tests) if len(tests) > 1 else 0.0)


def fmt_delta(pct):
    return f"{pct:+.2f}%" if pct == pct else "n/a"


def build_md():
    lines = ["# Gate 3 — Dataset-Coverage Summary", "",
             "3-way comparison (Normal / Flat=(4,4) / DRRA=(8,4)) × 5 paired seeds "
             "{42,123,2024,7,99} on 12 datasets under the frozen direct-96 task "
             "(L=256, H=96, train-only z-score, pooled MSE, standardized units). "
             "Descriptive statistics only; significance testing is Gate 4.",
             "", "## Integrity audit", ""]
    all_clean = True
    tables = []
    for ds in DATASET_ORDER:
        issues, by_key = audit(ds)
        rows = load_rows(ds)
        clean = not issues and len(rows) == 15
        all_clean &= clean
        lines.append(f"### {ds} — {'PASS' if clean else 'FAIL'}")
        if issues:
            lines += [f"- {i}" for i in issues]
        if len(rows) != 15:
            lines.append(f"- rows present: {len(rows)}/15")
        lines.append("")
        if not clean:
            continue
        n_agg = agg([by_key[("Normal", s)] for s in SEEDS])
        f_agg = agg([by_key[("Flat", s)] for s in SEEDS])
        d_agg = agg([by_key[("DRRA", s)] for s in SEEDS])
        lines += [
            "| Variant | Val mean±std | Test mean±std | Δval vs Normal | Δtest vs Normal |",
            "|---|---|---|---|---|",
            f"| Normal | {n_agg[0]:.4f} ± {n_agg[1]:.4f} | {n_agg[2]:.4f} ± {n_agg[3]:.4f} | — | — |",
            f"| Flat (4,4) | {f_agg[0]:.4f} ± {f_agg[1]:.4f} | {f_agg[2]:.4f} ± {f_agg[3]:.4f} | "
            f"{fmt_delta((f_agg[0] / n_agg[0] - 1) * 100)} | {fmt_delta((f_agg[2] / n_agg[2] - 1) * 100)} |",
            f"| DRRA (8,4) | {d_agg[0]:.4f} ± {d_agg[1]:.4f} | {d_agg[2]:.4f} ± {d_agg[3]:.4f} | "
            f"{fmt_delta((d_agg[0] / n_agg[0] - 1) * 100)} | {fmt_delta((d_agg[2] / n_agg[2] - 1) * 100)} |",
            "",
            "Paired per-seed val deltas vs Normal (negative = variant beats Normal):", "",
            "| Variant | Deltas by seed (42/123/2024/7/99) | Seeds beating Normal |", "|---|---|---|",
        ]
        for v in ("Flat", "DRRA"):
            deltas = [by_key[(v, s)]["val_mse"] - by_key[("Normal", s)]["val_mse"] for s in SEEDS]
            beat = sum(1 for d in deltas if d < 0)
            lines.append(f"| {v} | " + " / ".join(f"{d:+.4f}" for d in deltas) + f" | {beat}/5 |")
        lines.append("")
        tables.append((ds, n_agg, f_agg, d_agg))
    lines.append("## Cross-dataset headline", "")
    drra_beats = flat_beats = 0
    for ds, n_agg, f_agg, d_agg in tables:
        if d_agg[0] < n_agg[0]:
            drra_beats += 1
        if f_agg[0] < n_agg[0]:
            flat_beats += 1
    lines += [
        f"- Datasets where DRRA (8,4) mean val < Normal: **{drra_beats}/{len(tables)}**",
        f"- Datasets where Flat (4,4) mean val < Normal: **{flat_beats}/{len(tables)}**",
        f"- Datasets with a complete 15/15 row set: **{len(tables)}/12**",
    ]
    with open(OUT_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT_PATH}")
    return all_clean and len(tables) == 12


if __name__ == "__main__":
    import sys
    sys.exit(0 if build_md() else 1)
```

- [ ] **Step 2: Run on partial data** — while the sweep runs, run `python3 plan/gates/gate3/gate3_summary.py` on whatever rows exist; it must not crash on partial datasets (audit lists missing rows and skips tables). This is the smoke test for the generator itself.

- [ ] **Step 3: Record in `gate3_changes.md`.**

---

## Task 8: Report + docs (after sweep completes)

**Files:**
- Modify: `plan/gates/gate3/gate3_summary.md` (regenerated)
- Modify: `RESULTS.md` (new "Dataset Coverage (Gate 3)" section)
- Modify: `plan/paper_notes.md` (ledger row + changelog)
- Append: `plan/gates/gate3/gate3_changes.md`

- [ ] **Step 1: Regenerate the summary** — `python3 plan/gates/gate3/gate3_summary.py`; expected exit 0, 12/12 datasets PASS, 180 rows total.

- [ ] **Step 2: E-audit the summary** (as in Gate 2): spot-check 3 datasets by recomputing means from the JSONL by hand; verify Δ% math; verify per-seed delta signs; confirm no NaN rows. Fix generator bugs and regenerate.

- [ ] **Step 3: `RESULTS.md`** — add "## Dataset Coverage (Gate 3)" section: the per-dataset 3-way table (val mean±std, test mean, Δ% vs Normal), the cross-dataset counts line, the frozen-task/standardized-units caveat, and a pointer to `plan/gates/gate3/gate3_summary.md`. Keep the existing ETTh1 sections untouched (Gate-2/baseline remain the ETTh1 source for factorial/baseline tables).

- [ ] **Step 4: `plan/paper_notes.md`** — add Gate-3 ledger row (datasets, variants, seeds, artifacts, headline finding, caveats: descriptive-only, params ~2% spread, threads=8 sequential, H/L grid deferred) + changelog entry dated 2026-08-18.

- [ ] **Step 5: `gate3_changes.md`** — final entry: summary generator + docs updates.

---

## Task 9: Check off `plan/next_step.md` §6

**Files:**
- Modify: `plan/next_step.md` (§6 checkboxes + ✅ blockquote)

- [ ] **Step 1: Mark the four §6 dataset boxes `[x]`** (ETT family; large multivariate; different dynamics; mechanistic synthetic) **only if** Task 8 passed (12/12 datasets, audit clean).

- [ ] **Step 2: Add the ✅ blockquote under §6**, mirroring the Gate-2 style:

```markdown
> ✅ **Gate 3 — Dataset coverage DONE (2026-08-18).** Artifacts: `plan/gates/gate3/gate3_design.md` (pre-registered), `plan/gates/gate3/gate3_datasets.py` + `gate3_data_test.py` (data layer; raw caches + `data/data_manifest.json` SHA-256 provenance), `plan/gates/gate3/gate3_synthetic.py` (3 mechanistic families: sinusoids / change points / delayed-copy), `plan/gates/gate3/gate3_harness.py` (dataset-parameterized harness, frozen direct-96 protocol), `plan/gates/gate3/results/*.jsonl` (12 datasets × 3 variants × 5 seeds = 180 runs), `plan/gates/gate3/gate3_summary.md` (E-audited), `plan/gates/gate3/gate3_changes.md`. Headline: [1-line finding — filled at Task 8]. Caveats: descriptive statistics only (significance tests are Gate 4); params not re-equalized across datasets (~2% spread, same stance as the baseline gate); threads=8 sequential; standardized units. NOTE: the H∈{192,336,720} / L∈{512,720,1024} grid is deferred to a follow-on task.
```

- [ ] **Step 3: Record in `gate3_changes.md`** — next_step.md checkoffs applied.

---

## Runtime budget (pre-smoke estimates; Task 5 freezes measured values)

| Dataset | train windows | est. min/run | 15 runs |
|---|---|---|---|
| etth1 / etth2 | ~10,100 | 7–13 | 2–3 h each |
| ettm1 / ettm2 | ~41,456 | 30–50 | 8–13 h each |
| electricity | ~15,431 | 5–15 | 1–4 h |
| traffic | ~10,175 | 5–20 | 1–5 h |
| weather | ~31,267 | 10–20 | 2.5–5 h |
| exchange | ~4,324 | 2–5 | 0.5–1 h |
| solar | ~31,477 | 10–20 | 2.5–5 h |
| syn_* (×3) | ~11,648 | 8–15 | 2–4 h each |

**Total: ~45–60 h sequential.** All 180 runs are idempotent (per-dataset JSONL skips completed (variant, seed)) — a crash resumes cleanly.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Shape/provenance mismatch at download | Expected shapes are assertions; freeze measured values + log delta in `gate3_changes.md` |
| Traffic/Weather degenerate (constant) channels | Zero-std guard (std→1.0) + test asserts z-std ∈ {≈1, guarded}; audit documents guard count |
| Outlier-slow runs (Gate-2 saw 2–9 h outliers under contention) | Sequential single-process threads=8 = empirically fast regime; first-hour checkpoint; idempotent resume |
| HF/GitHub flakiness | Raw files cached once (`data/raw_*`); manifest hashes verify integrity; rerun fetch with `--fetch-all` reuses cache |
| Generator/summary bugs | Smoke generator on partial data (Task 7); E-audit by recomputation (Task 8) |
| Session interruption mid-sweep | Background job + idempotent JSONL; relaunch resumes where it stopped |
