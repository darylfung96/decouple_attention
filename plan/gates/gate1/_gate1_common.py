"""Shared Gate-1 causality-test helpers (plan/gates/gate1/gate1_task.md §8).

Provides: the 6 model-variant list, fresh eval-mode builders, the norm2
encoder-output hook, and a seeded input maker. Used by:
  - gate1_causality.py  (future-perturbation invariance)
  - gate1_gradmask.py   (gradient-mask / no-future-gradient-flow)
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import torch

from model import (
    CSATimeSeriesModel,
    ModifiedCSATimeSeriesModel,
    NormalTimeSeriesModel,
    FlatPlusTimeSeriesModel,
    ExpertFlatTimeSeriesModel,
    ExpertPlusPlusTimeSeriesModel,
)

NUM_FEATURES = 7
BATCH = 2
SEQ = 256
HIDDEN = 128
SEED = 42

# (display name, class) — the single source of truth for both scripts.
VARIANT_CLASSES = [
    ("CSA", CSATimeSeriesModel),
    ("ModifiedCSA", ModifiedCSATimeSeriesModel),
    ("Normal", NormalTimeSeriesModel),
    ("FlatPlus", FlatPlusTimeSeriesModel),
    ("ExpertFlat", ExpertFlatTimeSeriesModel),
    ("ExpertPlusPlus", ExpertPlusPlusTimeSeriesModel),
]


def build_variant(name):
    """Fresh eval-mode model instance for the given variant name."""
    for n, cls in VARIANT_CLASSES:
        if n == name:
            m = cls(num_features=NUM_FEATURES)
            m.eval()
            return m
    raise ValueError(f"unknown variant: {name}")


def make_norm2_hook(model, storage):
    """Register a forward hook on model.norm2 that appends its output to storage.

    The post-norm2 encoder output has shape [B, SEQ, HIDDEN]; storage[-1] is
    the output of the most recent forward pass.
    """
    def _hook(module, inp, out):
        storage.append(out)
    return model.norm2.register_forward_hook(_hook)


def make_x(seed=SEED, batch=BATCH, seq=SEQ, features=NUM_FEATURES):
    """Seeded input [B, SEQ, F], identical across variants (seed reset here)."""
    torch.manual_seed(seed)
    return torch.randn(batch, seq, features)
