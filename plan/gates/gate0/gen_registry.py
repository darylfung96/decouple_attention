#!/usr/bin/env python3
"""Generate plan/gates/gate0/gate0_registry.json - machine-readable ground truth of exact
attention-module numbers for the 7 CSA attention variants.

Reads the real module classes from the repo and counts parameters via
sum(p.numel()) on INSTANTIATED modules (no forward pass, no running the model,
CPU-only, fp32). Column math (kv_blocks / content_cols / sink_cols /
softmax_cols) mirrors the code in attention.BaseCSAAttention._attend.

Stacked has NO current source file/class: it is emitted as a
LEGACY_NO_CURRENT_SOURCE entry with all numeric fields null.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import torch  # noqa: E402

import model  # noqa: E402
from modified_attention import ModifiedCSAAttention  # noqa: E402

S = 256
NUM_FEATURES = 7
HIDDEN = 128
HORIZON = 96


def param_count(module):
    return sum(p.numel() for p in module.parameters())


def config_sha(d):
    blob = json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def build_entry(name, cls):
    torch.manual_seed(42)
    mdl = cls(num_features=NUM_FEATURES, hidden_size=HIDDEN,
              lookback=S, horizon=HORIZON)
    attn = mdl.attn

    attention_params = param_count(attn)
    full_model_params = param_count(mdl)
    entry = {"name": name}

    is_normal = name == "Normal"
    compress_rate = getattr(attn, "compress_rate", 0) if not is_normal else 0
    sliding_window = getattr(attn, "sliding_window", 0) if not is_normal else 0

    if is_normal:
        # Full O(S^2) attention: content == S, no compression/indexer/sink.
        kv_blocks = 0
        index_tokens = 0
        content_cols = S
        sink_cols = 0
        softmax_cols = content_cols
    else:
        # Compressed-KV column count = S // compress_rate, except the
        # Modified hierarchical compressor which always emits S//2 KV tokens.
        kv_blocks = S // compress_rate
        if isinstance(attn, ModifiedCSAAttention):
            kv_blocks = S // 2
        # Index-token count: default S//compress_rate; EPP uses its own
        # index_compress_rate (finer 4:1 router on top of 8:1 KV).
        index_tokens = S // compress_rate
        if hasattr(attn, "index_compress_rate"):
            index_tokens = S // getattr(attn, "index_compress_rate")
        window_cols = min(sliding_window, S)
        content_cols = kv_blocks + window_cols
        sink_cols = 1
        softmax_cols = content_cols + sink_cols

    # Hyperparameters captured from the instantiated attention module.
    config = {}
    for p_name in ("compress_rate", "index_compress_rate", "index_topk",
                   "index_n_heads", "index_head_dim", "sliding_window",
                   "o_groups", "o_lora_rank", "q_lora_rank"):
        if hasattr(attn, p_name):
            config[p_name] = getattr(attn, p_name)

    entry.update({
        "attention_params": attention_params,
        "full_model_params": full_model_params,
        "compress_rate": compress_rate,
        "kv_blocks": kv_blocks,
        "sliding_window": sliding_window,
        "index_tokens": index_tokens,
        "content_cols": content_cols,
        "sink_cols": sink_cols,
        "softmax_cols": softmax_cols,
        "config_hash": config_sha(config),
    })
    return entry


def main():
    model_classes = [
        ("Normal",        model.NormalTimeSeriesModel),
        ("Flat",          model.CSATimeSeriesModel),
        ("Modified",      model.ModifiedCSATimeSeriesModel),
        ("FlatPlus",      model.FlatPlusTimeSeriesModel),
        ("ExpertFlat",    model.ExpertFlatTimeSeriesModel),
        ("ExpertPlusPlus", model.ExpertPlusPlusTimeSeriesModel),
    ]

    registry = {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "shared_architecture": {
            "hidden_size": HIDDEN,
            "num_heads": 4,
            "head_dim": 32,
            "q_lora_rank": 64,
            "num_features": NUM_FEATURES,
            "lookback": S,
            "horizon": HORIZON,
            "S": S,
            "note": "CPU PyTorch, fp32. Params counted via sum(p.numel()); "
                    "no forward pass ever runs.",
        },
        "models": [],
    }

    for name, cls in model_classes:
        entry = build_entry(name, cls)
        # source string for runnable variants
        entry["source"] = "{}:{}".format(cls.__module__, cls.__name__)
        registry["models"].append(entry)

    # Stacked has no source file/class in the current tree.
    registry["models"].append({
        "name": "Stacked",
        "source": "LEGACY_NO_CURRENT_SOURCE",
        "attention_params": None,
        "full_model_params": None,
        "compress_rate": None,
        "kv_blocks": None,
        "sliding_window": None,
        "index_tokens": None,
        "content_cols": None,
        "sink_cols": None,
        "softmax_cols": None,
        "config_hash": None,
    })

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "gate0_registry.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(registry, fh, indent=2)
        fh.write("\n")

    print("wrote", out)
    for m in registry["models"]:
        print("{:<14} attn={!s:>9} full={!s:>9} kv={!s:>3} win={!s:>3} "
              "content={!s:>4} sink={!s} softmax={!s:>4} idx={!s:>3}".format(
                  m["name"],
                  m.get("attention_params"), m.get("full_model_params"),
                  m.get("kv_blocks"), m.get("sliding_window"),
                  m.get("content_cols"), m.get("sink_cols"),
                  m.get("softmax_cols"), m.get("index_tokens")))


if __name__ == "__main__":
    main()