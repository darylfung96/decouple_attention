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
            check(f"{name}: manifest sha256 matches",
                  g3.sha256_file(os.path.join(g3.DATA_DIR, info["raw_file"])) == info["sha256"])
            check(f"{name}: manifest shape matches",
                  (info["rows"], info["features"]) == (g3.DATASETS[name][2], g3.DATASETS[name][3]))
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
