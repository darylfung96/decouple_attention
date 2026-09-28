# Gate-0 Machine-Traceable Manifest — REPRO

`build_manifest.py` regenerates `plan/gates/gate0/gate0_manifest.json` from `gate0_registry.json` +
harmonized docs; no documented model number is typed by hand except the surrogate
*teacher* values (recorded-run snapshot; see `known_gaps`).

## Regenerate

```bash
cd /path/to/new_attention
~/.uv_env/py311/bin/python plan/gates/gate0/build_manifest.py   # canonical env (uv py311, torch 2.6.0); repo .venv removed 2026-09-28 (was empty, no torch)
~/.uv_env/py311/bin/python -m json.tool plan/gates/gate0/gate0_manifest.json > /dev/null && echo OK
```

Deterministic except `generated_utc` (generation time only); no historic run IDs
invented — `run_id = run-{config_hash[:8]}` (null for Stacked).

## Fields

- `manifest_version` / `generated_utc` — schema v1; generation timestamp (UTC, Z).
- `env` — python, torch, OS, device (cpu), fp_precision fp32, cuda_available.
- `protocol` — ETTh1, lookback 256, horizon 96, split 60/20/20, seed 42, batch 32, 10 epochs, AdamW 1e-4, wd 1e-5, clip 10.0.
- `files` — sha256 of repo-root *.py + RESULTS/WRITEUP/PUBLICATION.md + registry.
- `models.<name>` — run_id; registry_entry (verbatim registry row = link; key sliding_window = "window"); source_file (model.py; null for Stacked); file_sha256; val_mse / test_mse / fwd_ms_alternating / perf_spd (parsed from the RESULTS.md final table); provenance (RESULTS.md, alternating head-to-head, 10-epoch budget).
- `surrogate` — teacher ExpertPlusPlus; default_args parsed from train_surrogate.py argparse (epochs 5, finetune-epochs 1); teacher_run 0.1264/0.1868 recorded (runtime-printed; teacher_val_origin explains); v1 0.1424/0.1958; v2 0.1269/0.1817, params 16936 (computed from code).
- `known_gaps` — unresolved reproducibility items + recommended fixes.

## Known gaps → fixes

1. Stacked has no runnable source (registry LEGACY_NO_CURRENT_SOURCE; only a speed-harness wrapper in benchmark_speed.py) → re-implement or retire row.
2. Surrogate teacher val/test not code-reproducible (runtime-printed) → persist per-run logs (JSONL); seed-pinned check.
3. Sequential-benchmark exclusions not machine-encoded (prose only) → capture load avg + per-run stats; auto-filters.
4. compare.py prints no exact param ledger → add attention/full param print.
5. No git repo → git init next milestone; commit hashes not file sha256.
6. config_hash not model-unique (Flat/Modified/FlatPlus share one) → hash full config incl. class identity in gen_registry.py.
7. Normal fwd provenance differs across docs (RESULTS.md footnote: all rows alternating; WRITEUP: Normal 38.31 ms single sequential run) → mark per-row.

All doc-vs-registry values reconcile; future contradictions land in `known_gaps`
(doc value kept, never silently replaced).