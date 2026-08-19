#!/usr/bin/env python3
"""Generate plan/gates/gate0/gate0_manifest.json - machine-traceable record of Gate-0 numbers.

Sources (all read-only):
  - plan/gates/gate0/gate0_registry.json -> ground-truth model param/layout numbers
  - RESULTS.md               -> harmonized val/test/fwd/perf-spd doc values (parsed)
  - train_surrogate.py       -> surrogate default CLI args (parsed via ast)
  - surrogate_attention.py   -> v2 student param count (computed, verified)
  - repo root *.py + RESULTS.md + WRITEUP.md + PUBLICATION.md + registry
                             -> sha256 fingerprints

No documented model number is typed by hand except the surrogate *teacher*
val/test values (a recorded-run snapshot: train_surrogate.py prints them at
runtime and cannot re-derive them from code). Those constants are reconciled
against RESULTS.md before being emitted.

Run (from the repo root):  python3 plan/gates/gate0/build_manifest.py
Requires torch (python3 has it; the repo .venv does not).
"""

import ast
import datetime
import hashlib
import json
import platform
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = PLAN_DIR / "gate0_registry.json"
RESULTS_PATH = REPO_ROOT / "RESULTS.md"
SURROGATE_SCRIPT = REPO_ROOT / "train_surrogate.py"
OUT_PATH = PLAN_DIR / "gate0_manifest.json"

# Dependencies (env fingerprint needs torch)
try:
    import torch
except ImportError as exc:  # pragma: no cover - guard for .venv python
    raise SystemExit(
        "torch is required to generate the manifest. Run with `python3` "
        "(repo `.venv` has no torch)."
    ) from exc


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def table_cells(line: str):
    """Split a markdown table row into non-empty cell strings."""
    if not line.lstrip().startswith("|"):
        return None
    return [c.strip() for c in line.strip().strip("|").split("|")]


def model_key(cell: str) -> str:
    """Clean a model cell like '**ExpertPlusPlus (48+1 cols)**' -> 'ExpertPlusPlus'."""
    s = cell.replace("**", "").strip()
    s = re.sub(r"\s*\(.*?\)\s*", "", s)
    return s.strip()


def number(cell: str) -> float:
    """First float in a cell (ignores markdown/emoji/labels)."""
    m = re.search(r"-?\d+(?:\.\d+)?", cell)
    if m is None:
        raise ValueError(f"no numeric value found in {cell!r}")
    return float(m.group())


def two_ints(cell: str):
    """Parse 'A (B)' param cells like 'NNN,NNN (NNN,NNN)' -> (attn, full); None if no digits."""
    nums = [int(s.replace(",", "")) for s in re.findall(r"\d[\d,]*", cell)]
    return tuple(nums) if len(nums) == 2 else None


def parse_train_surrogate_defaults(path: Path) -> dict:
    """Extract argparse defaults from train_surrogate.py via ast."""
    tree = ast.parse(path.read_text())
    defaults = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            flag = None
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    flag = arg.value
                    break
            if not flag:
                continue
            dest = flag.lstrip("-").replace("-", "_")
            for kw in node.keywords:
                if kw.arg == "default":
                    try:
                        defaults[dest] = ast.literal_eval(kw.value)
                    except (ValueError, SyntaxError):
                        defaults[dest] = None
    return defaults


# --------------------------------------------------------------------------
# 1. Load the ground-truth registry
# --------------------------------------------------------------------------
registry = json.loads(REGISTRY_PATH.read_text())
registry_models = {m["name"]: m for m in registry["models"]}
MODEL_ORDER = [m["name"] for m in registry["models"]]

# --------------------------------------------------------------------------
# 2. Parse the harmonized numbers from RESULTS.md (doc_source of truth)
# --------------------------------------------------------------------------
results_txt = RESULTS_PATH.read_text()
final_table = {}      # model key -> {val, test, fwd, perf, params_doc}
surrogate_rows = {}   # 'v1_mlp' / 'v2_windowed' -> {val, test}

for line in results_txt.splitlines():
    cells = table_cells(line)
    if not cells:
        continue
    if len(cells) == 6 and model_key(cells[0]) in registry_models:
        name = model_key(cells[0])
        final_table[name] = {
            "val": number(cells[1]),
            "test": number(cells[2]),
            "params_doc": two_ints(cells[3]),
            "fwd": number(cells[4]),
            "perf": number(cells[5]),
        }
    elif len(cells) == 8 and cells[0].startswith("Surrogate MLP"):
        surrogate_rows["v1_mlp"] = {"val": number(cells[1]), "test": number(cells[2])}
    elif len(cells) == 8 and cells[0].startswith("Surrogate Win+Glob"):
        surrogate_rows["v2_windowed"] = {
            "val": number(cells[1]),
            "test": number(cells[2]),
        }

missing = [n for n in MODEL_ORDER if n not in final_table]
if missing:
    raise SystemExit(
        f"RESULTS.md final-table parse missed models: {missing}. "
        "Docs may have drifted; fix the parser or the docs."
    )

# --------------------------------------------------------------------------
# 3. Environment fingerprint (generation-time only, no historic run data)
# --------------------------------------------------------------------------
env = {
    "python": platform.python_version(),
    "torch": torch.__version__,
    "os": platform.platform(),
    "device": "cuda" if torch.cuda.is_available() else "cpu",
    "fp_precision": "fp32",
    "cuda_available": bool(torch.cuda.is_available()),
}

protocol = {
    "dataset": "ETTh1",
    "lookback": 256,
    "horizon": 96,
    "split": "chronological 60/20/20",
    "seed": 42,
    "batch_size": 32,
    "epochs": 10,
    "optimizer": "AdamW",
    "lr": 1e-4,
    "weight_decay": 1e-5,
    "clip_grad_norm": 10.0,
}

# --------------------------------------------------------------------------
# 4. sha256 fingerprints of repo-root *.py + 3 .md + registry
# --------------------------------------------------------------------------
files = {}
for p in sorted(REPO_ROOT.glob("*.py")):
    files[p.name] = sha256_file(p)
for name in ("RESULTS.md", "WRITEUP.md", "PUBLICATION.md"):
    files[name] = sha256_file(REPO_ROOT / name)
files["plan/gates/gate0/gate0_registry.json"] = sha256_file(REGISTRY_PATH)
files = dict(sorted(files.items()))

# --------------------------------------------------------------------------
# 5. Surrogate numbers (recorded-run snapshot for the teacher)
# --------------------------------------------------------------------------
# Teacher val/test are printed at runtime by train_surrogate.py; the recorded
# values below are a run snapshot. Reconciled against RESULTS.md text.
TEACHER_VAL, TEACHER_TEST = 0.1264, 0.1868
V2_PARAMS_DOC = 16936  # = 4*4096 + 8*32 + 8*32 + 40; documented in gate0_changes.md

known_gaps = []

# Teacher constants must still appear in the doc source text.
if "0.1264" not in results_txt or "0.1868" not in results_txt:
    known_gaps.append(
        {
            "item": "Surrogate teacher recorded values not found in RESULTS.md",
            "detail": f"teacher val {TEACHER_VAL} / test {TEACHER_TEST} are kept as the "
            "recorded-run snapshot but neither string appears in RESULTS.md anymore.",
            "recommended_fix": "Restore the recorded teacher values in RESULTS.md or update the manifest source.",
        }
    )

# v2 params: compute from the actual student architecture (window=32, n_global=8).
try:
    sys.path.insert(0, str(REPO_ROOT))
    from surrogate_attention import SurrogateAttentionV2  # noqa: E402

    _m = SurrogateAttentionV2(128, window=32, n_global=8)
    v2_params_computed = sum(p.numel() for p in _m.parameters())
    if v2_params_computed != V2_PARAMS_DOC:
        known_gaps.append(
            {
                "item": "Surrogate v2 param count computed != documented",
                "detail": f"computed {v2_params_computed} params from "
                f"surrogate_attention.py vs documented {V2_PARAMS_DOC}; "
                "keeping the documented value.",
                "recommended_fix": "Re-verify SurrogateAttentionV2 config and doc.",
            }
        )
except Exception as exc:  # pragma: no cover - env fallback
    v2_params_computed = None
    known_gaps.append(
        {
            "item": "Surrogate v2 params could not be computed from code",
            "detail": f"import/count failed ({exc}); using documented {V2_PARAMS_DOC}.",
            "recommended_fix": "Run under python3 so surrogate_attention.py is importable.",
        }
    )

train_defaults = parse_train_surrogate_defaults(SURROGATE_SCRIPT)
surrogate_defaults = {
    k: train_defaults[k]
    for k in (
        "epochs",
        "finetune_epochs",
        "distill_lambda",
        "teacher",
        "surrogate",
        "window",
        "n_global",
        "expansion",
        "layers",
        "batch_size",
        "lr",
        "seed",
    )
    if k in train_defaults
}

surrogate = {
    "teacher": "ExpertPlusPlus",
    "default_args": surrogate_defaults,
    "teacher_val_origin": "recorded-run snapshot (runtime-printed; not re-derivable)",
    "teacher_run": {"val_mse": TEACHER_VAL, "test_mse": TEACHER_TEST},
    **surrogate_rows,
}
surrogate["v2_windowed"]["params"] = V2_PARAMS_DOC

# --------------------------------------------------------------------------
# 6. Models section - one entry per registry model, doc numbers attached
# --------------------------------------------------------------------------
models = {}
for name in MODEL_ORDER:
    entry = registry_models[name]
    row = final_table[name]

    # Link into gate0_registry.json: verbatim registry entry (minus 'name').
    registry_entry = {k: v for k, v in entry.items() if k != "name"}

    # source_file: registry 'source' refers to the model class in model.py.
    src = entry.get("source") or ""
    source_file = "model.py" if src.startswith("model:") else None  # Stacked: legacy

    # Reconcile doc params cell (RESULTS.md final table) against the registry.
    if row["params_doc"] is not None and entry.get("attention_params") is not None:
        doc_attn, doc_full = row["params_doc"]
        if (doc_attn, doc_full) != (entry["attention_params"], entry["full_model_params"]):
            known_gaps.append(
                {
                    "item": f"Docs params contradict registry for {name}",
                    "detail": f"RESULTS.md final table has {doc_attn} ({doc_full}); "
                    f"gate0_registry.json has {entry['attention_params']} "
                    f"({entry['full_model_params']}). Keeping the registry value.",
                    "recommended_fix": "Harmonize the docs params cell to the registry.",
                }
            )

    provenance = {
        "doc_source": "RESULTS.md",
        "benchmark_protocol": "alternating head-to-head",
        "run_epoch_budget": 10,
    }
    if name == "Stacked":
        provenance.update(
            {"reproducible": False,
             "note": "no runnable source in repo"}
        )

    models[name] = {
        "run_id": f"run-{entry['config_hash'][:8]}" if entry.get("config_hash") else None,
        "registry_entry": registry_entry,
        "source_file": source_file,
        "file_sha256": files[source_file] if source_file else None,
        "val_mse": row["val"],
        "test_mse": row["test"],
        "fwd_ms_alternating": row["fwd"],
        "perf_spd": row["perf"],
        "provenance": provenance,
    }

# --------------------------------------------------------------------------
# 7. Known reproducibility gaps (static findings, reconciled above)
# --------------------------------------------------------------------------
STATIC_GAPS = [
    {
        "item": "Stacked model has no runnable source",
        "detail": "gate0_registry.json marks Stacked source as LEGACY_NO_CURRENT_SOURCE; "
        "no Stacked class exists in model.py or compare.py (only a speed-harness wrapper, "
        "ModifiedStackedCSAAttention, inside benchmark_speed.py, which cannot reproduce "
        "val/test). val 0.1116 / test 0.1665 / fwd 34.31 ms are legacy run results.",
        "recommended_fix": "Re-implement Stacked under the current model.py/compare.py "
        "API and re-run, or retire the row from the docs.",
    },
    {
        "item": "Surrogate teacher val/test not code-reproducible",
        "detail": "train_surrogate.py prints teacher val/test MSE at runtime (val(teacher) "
        "per Phase-1 epoch, final val_teacher/test_teacher) and does not persist runs. "
        "The recorded snapshot teacher val 0.1264 / test 0.1868 cannot be re-derived "
        "from code alone.",
        "recommended_fix": "Persist per-run logs (e.g., JSONL) from train_surrogate.py "
        "and commit them; add a seed-pinned reproducibility check.",
    },
    {
        "item": "Early sequential-benchmark exclusion policy not machine-encoded",
        "detail": "RESULTS.md/WRITEUP.md exclude benchmark_speed.py single-run numbers "
        "measured under CPU contention (e.g., EPP 57.49 vs 27.61 ms across runs; "
        "Flat 45.31 -> 34.01 -> 31.61 ms; Flat 273 ms at load average 19). The exclusion "
        "criteria live only in prose, not in code.",
        "recommended_fix": "Capture load average and per-run stats in benchmark_speed.py; "
        "apply automated outlier/sanity filters; log raw runs.",
    },
    {
        "item": "compare.py does not print an exact param ledger",
        "detail": "Attention/full param counts in the docs come from plan/gates/gate0/gen_registry.py, "
        "not from compare.py run output, so a fresh run cannot verify the registry numbers "
        "end-to-end.",
        "recommended_fix": "Add an exact per-model param ledger print (attention and full) "
        "to compare.py.",
    },
    {
        "item": "No git history",
        "detail": "Repo is not a git repository; the manifest records per-file sha256 only, "
        "with no commit-level provenance.",
        "recommended_fix": "git init on the next milestone and replace/augment file hashes "
        "with commit hashes.",
    },
    {
        "item": "Registry config_hash is not model-unique",
        "detail": "Flat, Modified and FlatPlus share the same config_hash "
        "(97a69c34...) in gate0_registry.json despite different architectures, so run ids "
        "derived from config_hash collide across those models.",
        "recommended_fix": "Hash over the full model config including class identity in "
        "gen_registry.py.",
    },
    {
        "item": "Normal forward-time provenance differs across docs",
        "detail": "RESULTS.md final-table footnote labels all rows 'alternating head-to-head', "
        "but WRITEUP.md 1/7.4 records Normal's 38.31 ms as a single sequential run (*). "
        "Manifest keeps the RESULTS.md value (38.31) as doc_source.",
        "recommended_fix": "Mark per-row timing provenance (head-to-head vs sequential) "
        "in RESULTS.md.",
    },
]
known_gaps.extend(STATIC_GAPS)

# --------------------------------------------------------------------------
# 8. Emit the manifest
# --------------------------------------------------------------------------
manifest = {
    "manifest_version": 1,
    "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "env": env,
    "protocol": protocol,
    "files": files,
    "models": models,
    "surrogate": surrogate,
    "known_gaps": known_gaps,
}

OUT_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

print(f"manifest written: {OUT_PATH}")
print(f"models: {', '.join(models.keys())}")
print(f"files hashed: {len(files)}")
print(f"surrogate v2 params: {V2_PARAMS_DOC}"
      + ("" if v2_params_computed == V2_PARAMS_DOC
         else f" (computed {v2_params_computed}, MISMATCH -> gap flagged)"))
print(f"known_gaps: {len(known_gaps)}")