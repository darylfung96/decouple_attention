#!/usr/bin/env python3
"""Gate 5 — systems benchmark (frozen protocol; Apple M2 development machine).

Complements gate3_latency.py / gate3_latency_scale.py (mean latency + CI,
throughput, batch scaling) with the remaining Gate-5 items (next_step.md §10):

  (1) full hardware details (macOS, chip, cores, RAM, torch, BLAS backend)
  (2) theoretical/empirical MACs per model (from torch.profiler shapes,
      aggregated over linear/mm/bmm/einsum ops; record_shapes=True)
  (3) peak resident memory (max RSS growth over a warm forward burst, batch 32)
  (4) training time per variant on ETTh1 (parsed from gate3_sweep.log elapsed)
  (5) sequence-length scaling L in {128, 256, 512, 1024, 2048, 4096} at batch
      {1, 32}: mean ms/batch + 95% bootstrap CI + empirical log-log slope
      alpha (t ~ L^alpha) per model — the §11 complexity evidence
  (6) top-CPU-ops profile at L=256, batch 32 (stage-level attribution by op)

Honesty: single machine; cross-hardware and depth/width sweeps are out of
scope here (documented); the router's dense L x M comparison makes total cost
O(L^2 / c_R) + O(L) — NOT subquadratic — which the slopes will confirm.

Output: plan/gates/gate5/gate5_results.json + printed summary.
"""
import argparse
import json
import os
import platform
import resource
import statistics as st
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import torch  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import NormalTimeSeriesModel  # noqa: E402
from plan.gates.gate2.gate2_factorial import EPPTimeSeriesModel  # noqa: E402
# gate3_harness uses flat sibling imports (gate3_datasets), so its own
# directory must be importable:
GATE3_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gate3")
sys.path.insert(0, GATE3_DIR)
from gate3_harness import VARIANT_CELLS, RANKS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "gate5_results.json")

LOOKBACK = 256
HORIZON = 96
FEATURES = 7
THREADS = 8
SEED = 42
LS = [128, 256, 512, 1024, 2048, 4096]
BATCHES = [1, 32]
ROUNDS_SMALL = 12   # L <= 1024
ROUNDS_LARGE = 8    # L >= 2048
PASSES = 8
WARMUP = 4
BOOT_N = 10000


def percentile(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def bootstrap_ci(samples, n=BOOT_N):
    import random
    rng = random.Random(2026)
    est = st.mean(samples)
    if not samples:
        return est, est
    res = sorted(st.mean(rng.choices(samples, k=len(samples))) for _ in range(n))
    return res[int(n * 0.025)], res[int(n * 0.975) - 1]


def machine_info():
    info = {"platform": platform.platform(),
            "mac_ver": list(platform.mac_ver()),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "threads": torch.get_num_threads(),
            "interop_threads": torch.get_num_interop_threads(),
            "blas": torch.__config__.show().splitlines()[0:3]}
    for key, cmd in (("chip", ["sysctl", "-n", "machdep.cpu.brand_string"]),
                     ("cores", ["sysctl", "-n", "hw.ncpu"]),
                     ("mem_bytes", ["sysctl", "-n", "hw.memsize"]),
                     ("model", ["sysctl", "-n", "hw.model"])):
        try:
            info[key] = subprocess.run(cmd, capture_output=True,
                                       text=True).stdout.strip()
        except Exception as e:  # pragma: no cover
            info[key] = f"n/a ({e})"
    return info


def build_models(L=LOOKBACK, seed=SEED):
    """Build the three variants at lookback L (pos_embedding is L-sized)."""
    models = {}
    for variant in sorted(VARIANT_CELLS):
        torch.manual_seed(seed)
        if variant == "Normal":
            m = NormalTimeSeriesModel(num_features=FEATURES, hidden_size=128,
                                      lookback=L, horizon=HORIZON)
        else:
            ckv, c_r = VARIANT_CELLS[variant]
            m = EPPTimeSeriesModel(FEATURES, ckv, c_r, q_lora_rank=RANKS[0],
                                   o_lora_rank=RANKS[1], hidden_size=128,
                                   lookback=L, horizon=HORIZON)
        m.eval()
        models[variant] = m
    return models


def count_macs_with_profiler(models, B=1, L=LOOKBACK):
    """Analytic per-sequence forward MACs from module geometry (documented
    formulas; small ops — norms, RoPE, masks, compression weighted sums —
    excluded). torch.profiler input_shapes proved unreliable on this build
    (empty), so the analytic route is used.

    Components (per sequence, L tokens, heads=4, d_head=32, d=128):
      wrapper : input_proj L*F*d + MLP 2*L*d*4d + head d*(H*F)
      q_lora  : L*d*64 (q_a) + L*64*(heads*d_head) (q_b)
      kv      : L*d*d_head            (tied K=V, single head)
      attn    : 2*heads*L*cols*d_head (scores + values)
                cols = L/c_KV + window + 1  (compressed cells)
                cols = L                     (Normal)
      router  : L*(L/c_R)*d_head      (EPP only: shared-Q scores vs M=L/c_R)
      o_proj  : Normal o_lora=128: L*(heads*d_head/4)*(4*128) + L*(4*128)*d
                EPP     o_lora=64 : L*(heads*d_head/4)*(4*64)  + L*(4*64)*d
      compress(EPP): gates 2*L*d*64 + kv projs 2*L*d*d_head
    """
    heads, d_head, d = 4, 32, 128
    F, H = FEATURES, HORIZON
    mlp = 2 * L * d * (4 * d)
    wrapper = L * F * d + mlp + d * (H * F)
    q_lora = L * d * 64 + L * 64 * (heads * d_head)
    kv = L * d * d_head
    o_normal = L * (heads * d_head // 4) * (4 * 128) + L * (4 * 128) * d
    o_epp = L * (heads * d_head // 4) * (4 * 64) + L * (4 * 64) * d
    attn_normal = 2 * heads * L * L * d_head
    cols_epp = L // 8 + 16 + 1
    attn_epp = 2 * heads * L * cols_epp * d_head
    router_epp = L * (L // 4) * d_head
    compress_epp = 2 * (L * d * 64) + 2 * (L * d * d_head)
    out = {
        "Normal": {"wrapper": wrapper, "q_lora": q_lora, "kv": kv,
                   "attn": attn_normal, "o_proj": o_normal,
                   "total": wrapper + q_lora + kv + attn_normal + o_normal,
                   "note": "analytic dominant terms; norms/RoPE/masks excluded"},
        "Flat": {"wrapper": wrapper, "q_lora": q_lora, "kv": kv,
                 "attn": 2 * heads * L * (L // 4 + 16 + 1) * d_head,
                 "router": L * (L // 4) * d_head,
                 "o_proj": o_epp,
                 "compress": 2 * (L * d * 64) + 2 * (L * d * d_head),
                 "total": (wrapper + q_lora + kv +
                           2 * heads * L * (L // 4 + 16 + 1) * d_head +
                           L * (L // 4) * d_head + o_epp +
                           2 * (L * d * 64) + 2 * (L * d * d_head)),
                 "note": "Flat=(4,4): same formulas with c_KV=4, c_R=4"},
        "DRRA": {"wrapper": wrapper, "q_lora": q_lora, "kv": kv,
                 "attn": attn_epp, "router": router_epp, "o_proj": o_epp,
                 "compress": compress_epp,
                 "total": (wrapper + q_lora + kv + attn_epp + router_epp +
                           o_epp + compress_epp),
                 "note": "analytic dominant terms; norms/RoPE/masks excluded"},
    }
    return {v: {"total_macs_per_batch": int(m["total"]),
                "macs_per_seq": int(m["total"]),
                "components": {k: int(val) for k, val in m.items()
                               if k != "note"},
                "note": m["note"]}
            for v, m in out.items()}


def measure_peak_rss(models, B=32):
    """Peak RSS growth over a warm batch-32 forward burst. NOTE: on macOS
    ru_maxrss is in BYTES. Must be measured BEFORE any large allocations from
    other benchmark stages (the max is cumulative for the process)."""
    x = torch.randn(B, LOOKBACK, FEATURES)
    base = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    out = {}
    for variant, m in models.items():
        with torch.no_grad():
            for _ in range(10):
                m(x)
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        out[variant] = {"peak_rss_bytes": peak,
                        "rss_growth_bytes": peak - base,
                        "units": "bytes (macOS ru_maxrss)",
                        "params": sum(p.numel() for p in m.parameters()),
                        "param_bytes": sum(p.numel() for p in m.parameters()) * 4}
        base = max(base, peak)   # monotonic max: attribute growth cumulatively
    return out


def l_scale(out_path, heads=4):
    """L-scaling: mean ms/batch + CI + slope, per model per batch size.
    Models are rebuilt per L (pos_embedding is L-sized). Writes partial
    results to out_path after every batch size (sleep/crash-proof).
    Memory guard: the dense score tensor is B*heads*L*L*4 bytes; combos whose
    scores exceed ~4 GB are skipped and recorded (they would swap-thrash on
    a 16 GB machine). Existing batch sizes in out_path are resumed, not
    re-measured."""
    out = {}
    if os.path.exists(out_path):
        try:
            out = json.load(open(out_path)).get("l_scale", {})
        except (json.JSONDecodeError, OSError):
            out = {}
    skipped = {}
    for B in BATCHES:
        if str(B) in out and "loglog_slope" in out[str(B)]:
            print(f"  [l_scale] B={B}: already complete — resuming")
            continue
        per_batch = {}
        for L in LS:
            # Memory guard: dense score tensor is B*heads*L*L*4 bytes.
            score_bytes = B * 4 * L * L * 4
            if score_bytes > 4 * 1024**3:
                per_batch[str(L)] = {"skipped": True,
                                     "reason": (f"dense score tensor ~"
                                                f"{score_bytes / 1024**3:.1f} GB "
                                                f"exceeds practical RAM; would "
                                                f"swap-thrash")}
                print(f"  [l_scale] B={B} L={L}: SKIPPED ({per_batch[str(L)]['reason']})")
                continue
            models = build_models(L=L)
            torch.manual_seed(0)
            x = torch.randn(B, L, FEATURES)
            rounds = ROUNDS_LARGE if L >= 2048 else ROUNDS_SMALL
            samples = {v: [] for v in models}
            for v, m in models.items():
                with torch.no_grad():
                    for _ in range(WARMUP):
                        m(x)
            for _ in range(rounds):
                for v, m in models.items():
                    ts = []
                    with torch.no_grad():
                        for _ in range(PASSES):
                            t0 = time.perf_counter()
                            m(x)
                            ts.append(time.perf_counter() - t0)
                    samples[v].append(st.median(ts))
            per_batch[str(L)] = {}
            for v in models:
                ms = [t * 1e3 for t in samples[v]]
                mean = st.mean(ms)
                lo, hi = bootstrap_ci(ms)
                per_batch[str(L)][v] = {
                    "mean_ms_per_batch": round(mean, 2),
                    "mean_ms_per_seq": round(mean / B, 4),
                    "ci95_ms": [round(lo, 2), round(hi, 2)],
                }
            print(f"  [l_scale] B={B} L={L}: " + "  ".join(
                f"{v} {per_batch[str(L)][v]['mean_ms_per_batch']:.1f} ms"
                for v in models))
        # save measurements BEFORE slopes (never lose data to a fit error);
        # slopes: fit log(t) = a + alpha*log(L) on L >= 512 (asymptotic regime);
        # skipped memory-infeasible combos are excluded from the fit
        out[str(B)] = {"latency": per_batch}
        with open(out_path, "w") as f:
            json.dump({"l_scale": out}, f, indent=2, sort_keys=True)
        import numpy as np
        slopes = {}
        for v in models:
            xs = [L for L in LS if L >= 512 and str(L) in per_batch
                  and v in per_batch[str(L)]
                  and "mean_ms_per_batch" in per_batch[str(L)][v]]
            ys = [per_batch[str(L)][v]["mean_ms_per_batch"] for L in xs]
            logx = np.log(np.array(xs, dtype=float))
            logy = np.log(np.array(ys, dtype=float))
            alpha = float(np.polyfit(logx, logy, 1)[0])
            slopes[v] = round(alpha, 3)
        out[str(B)]["loglog_slope"] = slopes
        with open(out_path, "w") as f:
            json.dump({"l_scale": out}, f, indent=2, sort_keys=True)
        del models
    return out


def top_ops_profile(models, L=LOOKBACK, B=32):
    x = torch.randn(B, L, FEATURES)
    out = {}
    for v, m in models.items():
        with torch.no_grad():
            for _ in range(2):
                m(x)
            with torch.profiler.profile(
                    activities=[torch.profiler.ProfilerActivity.CPU]) as prof:
                m(x)
        rows = [(e.key, e.self_cpu_time_total / 1e3) for e in prof.key_averages()]
        rows.sort(key=lambda r: -r[1])
        out[v] = [{"op": k, "self_cpu_ms": round(t, 3)} for k, t in rows[:12]]
    return out


def training_time_from_sweep():
    """Mean elapsed (s) per variant on ETTh1 from the Gate-3 sweep log."""
    log = os.path.join(REPO_ROOT, "plan", "gates", "gate3", "gate3_sweep.log")
    import re
    per = {v: [] for v in VARIANT_CELLS}
    cur = None
    with open(log) as f:
        for line in f:
            m = re.search(r"=== etth1 (\w+) seed=(\d+) START", line)
            if m:
                cur = m.group(1)
            m = re.search(r"FINAL test_mse=.*\(elapsed (\d+)s\)", line)
            if m and cur and cur in per:
                per[cur].append(int(m.group(1)))
            if "DONE" in line:
                cur = None
    return {v: {"runs": len(per[v]),
                "mean_seconds": round(st.mean(per[v]), 1) if per[v] else None,
                "seconds": per[v]} for v in per}


def main():
    torch.set_num_threads(THREADS)
    models = build_models(L=LOOKBACK)
    result = {
        "machine": machine_info(),
        "task": {"L": LOOKBACK, "H": HORIZON, "F": FEATURES, "threads": THREADS},
        # peak RSS must come FIRST: ru_maxrss is a cumulative process max, so
        # later stages (profiler, L-scaling) would contaminate the baseline
        "peak_rss": measure_peak_rss(models),
        "macs": count_macs_with_profiler(models),
        "training_time_etth1": training_time_from_sweep(),
        "l_scale": l_scale(OUT_PATH),
        "top_ops": top_ops_profile(models),
    }
    with open(OUT_PATH, "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)

    print("== machine ==")
    for k in ("model", "chip", "cores", "mem_bytes", "mac_ver", "torch", "threads"):
        print(f"  {k}: {result['machine'].get(k)}")
    print("  blas:", result["machine"].get("blas"))
    print("\n== MACs (L=256, B=1) ==")
    for v in models:
        m = result["macs"][v]
        print(f"  {v}: {m['total_macs_per_batch']/1e6:.2f} M/batch  {m['macs_per_seq']/1e3:.1f} k/seq")
    print("\n== peak RSS (batch 32) ==")
    for v in models:
        r = result["peak_rss"][v]
        print(f"  {v}: +{r['rss_growth_bytes']/1e6:.1f} MB growth, params {r['params']:,} ({r['param_bytes']/1e6:.1f} MB)")
    print("\n== training time (ETTh1, 10 epochs, from sweep) ==")
    for v, t in result["training_time_etth1"].items():
        print(f"  {v}: mean {t['mean_seconds']} s over {t['runs']} runs")
    print("\n== L-scaling slopes (log-log, L>=512) ==")
    for B in BATCHES:
        print(f"  batch {B}: " + "  ".join(f"{v} alpha={s}" for v, s in
              result["l_scale"][str(B)]["loglog_slope"].items()))
    print("\n== top ops (L=256, B=32) ==")
    for v in models:
        tops = ", ".join(f"{r['op'].split('.')[-1]} {r['self_cpu_ms']:.1f}ms"
                         for r in result["top_ops"][v][:5])
        print(f"  {v}: {tops}")
    print(f"\nwrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
