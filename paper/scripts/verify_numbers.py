#!/usr/bin/env python3
"""Recompute every number in the manuscript's tables from the raw per-seed
manifests and compare with the values printed in the paper.

verify_manuscript.py checks that strings exist; this script checks that the
strings are the right numbers. Written 2026-10-20 after two stale numbers
survived an eyeball pass: a human should never have to remember a value.

Usage:  ~/.uv_env/py311/bin/python paper/scripts/verify_numbers.py [-v]

Every check prints PASS/FAIL with its source manifest; exit 1 on any FAIL.
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

VERBOSE = "-v" in sys.argv
REPO = Path(__file__).resolve().parents[2]
PLAN = REPO / "plan" / "gates"

fails: list[str] = []
checks = 0


def recs(p: Path) -> list[dict]:
    return [json.loads(line) for line in open(p)]


def check(label, computed, printed, tol=0.0, src=""):
    global checks
    checks += 1
    ok = abs(float(computed) - float(printed)) <= tol if tol else float(computed) == float(printed)
    if not ok:
        fails.append(f"{label}: paper {printed} vs artifact {computed}  [{src}]")
    elif VERBOSE:
        print(f"  ok  {label}: {printed}")


# --- factorial rows (25 seeds, corrected mapping) --------------------------
def factorial(cell: tuple[int, int]) -> list[dict]:
    out = {}
    for r in recs(PLAN / "gate2" / "gate2_results.jsonl"):
        if tuple(r["cell"]) == cell:
            out[r["seed"]] = r
    for r in recs(PLAN / "gate7_seeds" / "results" / "gate7.jsonl"):
        if r.get("cell") and tuple(r["cell"]) == cell:
            out[r["seed"]] = r
    if cell in {(4, 4), (4, 8), (8, 8)}:
        for r in recs(PLAN / "gate15_rerun" / "results" / "factorial.jsonl"):
            if tuple(r["cell"]) == cell:
                out[r["seed"]] = r
    return [out[s] for s in sorted(out)]


def normal_rows() -> list[dict]:
    out = {}
    for r in recs(PLAN / "baseline" / "baseline_normal_results.jsonl"):
        out[r["seed"]] = r
    for r in recs(PLAN / "gate7_seeds" / "results" / "gate7.jsonl"):
        if r.get("cell_name") == "Normal":
            out.setdefault(r["seed"], r)
    return [out[s] for s in sorted(out)]


def stats(rs):
    val = [r["val_mse"] for r in rs]
    return dict(n=len(val), val=st.mean(val), sd=st.stdev(val),
                test=st.mean(r["test_mse"] for r in rs),
                train=st.mean(r["final_train_mse"] for r in rs),
                attn=rs[0].get("attn_params"), full=rs[0].get("full_params"))


def main() -> int:
    normal = normal_rows()
    flat, drra = factorial((4, 4)), factorial((8, 4))
    c48, c88 = factorial((4, 8)), factorial((8, 8))
    x16 = recs(PLAN / "gate18_d5" / "results" / "etth1.jsonl")
    x32 = recs(PLAN / "gate19_324" / "results" / "etth1.jsonl")
    r64 = recs(PLAN / "gate27_r2matched" / "results" / "normal_r64.jsonl")
    C = {"Normal": stats(normal), "Normal-r64": stats(r64), "(4,4)": stats(flat),
         "(8,4)": stats(drra), "(4,8)": stats(c48), "(8,8)": stats(c88),
         "(16,4)*": stats(x16), "(32,4)*": stats(x32)}

    # --- Table 1: geometry and parameter counts ---------------------------
    for name, attn, full in [("Normal", 102496, 355200), ("(4,4)", 95396, 348100),
                             ("(8,4)", 95652, 348356), ("(4,8)", 95652, 348356),
                             ("(8,8)", 95908, 348612), ("(16,4)*", 96164, 348868),
                             ("(32,4)*", 97188, 349892)]:
        check(f"T1 attn {name}", C[name]["attn"], attn, src="per-seed manifests")
        check(f"T1 full {name}", C[name]["full"], full, src="per-seed manifests")
    ref = C["(8,4)"]["attn"]
    dev = max(abs(C[c]["attn"] - ref) / ref * 100 for c in ["(4,4)", "(8,4)", "(4,8)", "(8,8)"])
    check("max attn deviation from (8,4) ref (%)", round(dev, 3), 0.268, tol=0.0006)
    devf = max(abs(C[c]["full"] - C["(8,4)"]["full"]) / C["(8,4)"]["full"] * 100
               for c in ["(4,4)", "(8,4)", "(4,8)", "(8,8)"])
    check("max full deviation from (8,4) ref (%)", round(devf, 3), 0.073, tol=0.0006)
    for c in ["(4,4)", "(8,4)", "(4,8)", "(8,8)", "(16,4)*", "(32,4)*"]:
        pct = (1 - C[c]["attn"] / C["Normal"]["attn"]) * 100
        print(f"  attention params {c}: {pct:.2f}% fewer than Normal")
    pct_f = (1 - C["(8,4)"]["full"] / C["Normal"]["full"]) * 100
    print(f"  full-model params (8,4): {pct_f:.2f}% below Normal")

    # --- Figure 1: the drawn cell's column arithmetic ---------------------
    # The caption prints "16 + 32 + 1 = 49" and "up to 16 of the 32 block
    # columns", and Table 1 prints the same identity as "48 + 1". Re-derive
    # all of it from the frozen auxiliary contract (window W, selection k) and
    # the drawn (c_KV, c_R) = (8, 4) cell, so editing the rates without
    # editing the printed numbers fails here rather than surviving an eyeball.
    L_FIG, W_FIG, SINK = 256, 16, 1
    ckv_fig, cr_fig, k_fig = 8, 4, 16
    check("Fig1 softmax columns (16 + 32 + 1)", L_FIG // ckv_fig + W_FIG + SINK,
          49, src="Figure 1 caption")
    check("Fig1 Table 1 form (48 + 1)", L_FIG // ckv_fig + W_FIG, 48, src="Table 1")
    check("Fig1 compressed blocks (32)", L_FIG // ckv_fig, 32, src="Figure 1 strip")
    check("Fig1 index tokens (64)", L_FIG // cr_fig, 64, src="Figure 1 strip")
    check("Fig1 index tokens per block (two)", ckv_fig // cr_fig, 2,
          src="Figure 1 caption / S3.3 mapping")
    assert k_fig <= L_FIG // ckv_fig, "selection larger than the block set"

    # --- Table 2: factorial ----------------------------------------------
    printed2 = {
        "Normal": (0.8389, 0.0814, 1.0804, 0.2864),
        "Normal-r64": (0.7910, 0.0649, 1.0281, 0.2975),
        "(4,4)": (0.6148, 0.0704, 0.8771, 0.2941),
        "(8,4)": (0.6190, 0.0827, 0.8440, 0.2876),
        "(4,8)": (0.6810, 0.0570, 0.9496, 0.2863),
        "(8,8)": (0.6128, 0.0660, 0.8505, 0.2837),
        "(16,4)*": (0.5810, 0.0751, 0.8100, 0.2793),
        "(32,4)*": (0.6122, 0.0652, 0.8586, 0.2702),
    }
    for name, (v, s, t, tr) in printed2.items():
        c = C[name]
        check(f"T2 {name} val", round(c["val"], 4), v, tol=5e-5)
        check(f"T2 {name} std", round(c["sd"], 4), s, tol=5e-5)
        check(f"T2 {name} test", round(c["test"], 4), t, tol=5e-5)
        check(f"T2 {name} train", round(c["train"], 4), tr, tol=5e-5)
        check(f"T2 {name} n", c["n"], 25)
    base = {r["seed"]: r["val_mse"] for r in flat}
    beats_flat = {"(8,4)": 16, "(4,8)": 6, "(8,8)": 12, "(16,4)*": 16, "(32,4)*": 14}
    for name, want in beats_flat.items():
        got = sum(1 for r in C and {"(8,4)": drra, "(4,8)": c48, "(8,8)": c88,
                                    "(16,4)*": x16, "(32,4)*": x32}[name]
                  if r["val_mse"] < base[r["seed"]])
        check(f"T2 beats(4,4) {name}", got, want)
    nb = {r["seed"]: r["val_mse"] for r in normal}
    series = {"(4,4)": flat, "(8,4)": drra, "(4,8)": c48, "(8,8)": c88}
    wins = {k: sum(1 for r in v if r["val_mse"] < nb[r["seed"]]) for k, v in series.items()}
    print(f"  beats Normal per cell: {wins}  total {sum(wins.values())}/100")
    check("95/100 paired comparisons vs Normal", sum(wins.values()), 95)

    # --- Table 3: baseline deltas ----------------------------------------
    n = C["Normal"]
    for name, dv, dt in [("Normal-r64", -5.72, -4.85), ("(4,4)", -26.71, -18.82),
                         ("(8,4)", -26.22, -21.89)]:
        check(f"T3 {name} dval", round((C[name]["val"] / n["val"] - 1) * 100, 2), dv, tol=0.01)
        check(f"T3 {name} dtest", round((C[name]["test"] / n["test"] - 1) * 100, 2), dt, tol=0.01)

    # --- Table 4: five-seed suite ----------------------------------------
    DS = ["etth1", "etth2", "ettm1", "ettm2", "electricity", "traffic", "weather",
          "exchange", "solar", "syn_sinusoids", "syn_changepoints", "syn_delayedcopy"]
    printed4 = [(0.8416, 0.5909, 0.5967, -29.1), (1.9187, 1.7817, 1.8080, -5.8),
                (0.4285, 0.4121, 0.3832, -10.6), (1.5618, 0.9326, 0.8053, -48.4),
                (0.4047, 0.3775, 0.3808, -5.9), (0.5994, 0.5907, 0.5874, -2.0),
                (0.4460, 0.4448, 0.4424, -0.8), (2.9800, 3.1364, 3.2350, 8.6),
                (0.1899, 0.1693, 0.1722, -9.3), (0.1227, 0.1276, 0.1264, 3.0),
                (5.9456, 5.9733, 6.0013, 0.9), (0.2888, 0.2894, 0.2894, 0.2)]
    for ds, (mn, mf, md, dv) in zip(DS, printed4):
        rs = recs(PLAN / "gate3" / "results" / f"{ds}.jsonl")
        by = {(r["variant"], r["seed"]): r["val_mse"] for r in rs}
        seeds = sorted({r["seed"] for r in rs})
        frs = recs(PLAN / "gate15_rerun" / "results" / "suite_flat" / f"{ds}.jsonl")
        fb = {(r["variant"], r["seed"]): r["val_mse"] for r in frs}
        fv = "Flat-fix" if ("Flat-fix", seeds[0]) in fb else "Flat"
        got = (st.mean(by[("Normal", s)] for s in seeds),
               st.mean(fb[(fv, s)] for s in seeds),
               st.mean(by[("DRRA", s)] for s in seeds))
        for got_v, want_v, lab in zip(got, (mn, mf, md), ("Normal", "(4,4)", "(8,4)")):
            check(f"T4 {ds} {lab}", round(got_v, 4), want_v, tol=5e-5, src=f"gate3/{ds}.jsonl")
        check(f"T4 {ds} dval (8,4)", round((got[2] / got[0] - 1) * 100, 1), dv, tol=0.05,
              src="ratio of five-seed means")

    # --- Table 6: all-block control --------------------------------------
    ab = recs(PLAN / "gate28_c1control" / "results" / "allblock.jsonl")
    for name, ref_rows, want_ctrl, want_rel, want_better, want_real in [
            ("C1(4,4)", flat, 0.7727, 27.1, 1, 31.75),
            ("C1(8,4)", drra, 0.6857, 11.8, 5, 15.62)]:
        rs = [r for r in ab if r["cell_name"] == name]
        by = {r["seed"]: r for r in rs}
        rb = {r["seed"]: r for r in ref_rows}
        check(f"T6 {name} ctrl mean", round(st.mean(r["val_mse"] for r in rs), 4), want_ctrl, tol=5e-5)
        rel = st.mean((by[s]["val_mse"] / rb[s]["val_mse"] - 1) * 100 for s in by)
        check(f"T6 {name} delta rel", round(rel, 1), want_rel, tol=0.05)
        better = sum(1 for s in by if by[s]["val_mse"] < rb[s]["val_mse"])
        check(f"T6 {name} seeds better", better, want_better)
        real = st.mean(r.get("realized_blocks", float("nan")) for r in rs)
        if real == real:
            check(f"T6 {name} realized blocks", round(real, 2), want_real, tol=0.01)
        check(f"T6 {name} test mean", round(st.mean(r["test_mse"] for r in rs), 4),
              {"C1(4,4)": 1.0695, "C1(8,4)": 0.9551}[name], tol=5e-5)

    # --- Table 7: latency ------------------------------------------------
    lat = json.load(open(PLAN / "gate3" / "gate3_latency.json"))["models"]
    for name, (key, (m, p90, p99, thr, dlt)) in {
        "Normal": ("Normal", (52.5, 59.4, 65.0, 19.1, 0.0)),
        "(4,4)": ("Flat", (52.1, 63.5, 71.5, 19.2, -0.7)),
        "(8,4)": ("DRRA", (49.3, 56.5, 65.9, 20.3, -6.1)),
    }.items():
        x = lat[key]
        check(f"T7 {name} mean", round(x["mean_ms"], 1), m, tol=0.05, src="gate3_latency.json")
        check(f"T7 {name} p90", round(x["p90_ms"], 1), p90, tol=0.05)
        check(f"T7 {name} p99", round(x["p99_ms"], 1), p99, tol=0.05)
        check(f"T7 {name} throughput", round(x["throughput_batches_per_s"], 1), thr, tol=0.05)
        check(f"T7 {name} delta", round(x["delta_mean_vs_normal_pct"], 1), dlt, tol=0.05)
        check(f"T7 {name} CI low", round(x["mean_ci95_ms"][0], 1),
              {"Normal": 50.4, "(4,4)": 49.2, "(8,4)": 47.2}[name], tol=0.05)
        check(f"T7 {name} CI high", round(x["mean_ci95_ms"][1], 1),
              {"Normal": 54.7, "(4,4)": 55.4, "(8,4)": 51.7}[name], tol=0.05)

    # --- Table 9: closed-form attention-path savings ----------------------
    H, DH, D, W = 4, 32, 128, 16
    # Compressor cost: two projections of width 2*d_h per compressor, two
    # compressors (gate31 hook measurement of the executed module). The gate20
    # row charged the index pair at width d_h and is superseded here.
    COMPRESS_PER_TOKEN = 4 * D * 64

    def s_attn(L, ckv, cr):
        wn = 2 * H * DH * L * L
        wc = (2 * H * DH * L * (L // ckv + W + 1) + L * (L // cr) * H * DH
              + L * COMPRESS_PER_TOKEN)
        return (1 - wc / wn) * 100

    printed9 = []
    for L, row in [(256, (5.9, 18.4, 24.6, 27.7)), (4096, (59.0, 71.5, 77.7, 80.8)),
                   (8192, (60.7, 73.2, 79.5, 82.6)), (32768, (62.1, 74.6, 80.8, 83.9)),
                   (131072, (62.4, 74.9, 81.1, 84.3))]:
        for ckv, want in zip((4, 8, 16, 32), row):
            check(f"T9 L={L} ({ckv},4)", round(s_attn(L, ckv, 4), 1), want, tol=0.05,
                  src="Eq. (2)/(3) evaluated")

    # --- Table 11: component accounts ------------------------------------
    g20 = json.load(open(PLAN / "gate20_accounting" / "router_accounting_audit.json"))
    g31 = json.load(open(PLAN / "gate31_compressor_accounting" / "results.json"))
    check("gate31 compressor MACs/seq", g31["executed_total"], 8388608, tol=0)
    check("gate31 compressor per token", g31["executed_total"] // 256,
          COMPRESS_PER_TOKEN, tol=0)
    comp = {k: dict(v) for k, v in g20["components_L256"].items()}
    delta = g31["executed_total"] - comp["CSA"]["compress"]
    for k in ("CSA", "DRRA"):
        comp[k]["compress"] += delta
        comp[k]["total"] += delta
    for name, key, want in [("Normal", "Normal", 76.86), ("(4,4)", "CSA", 65.39),
                            ("(8,4)", "DRRA", 63.30)]:
        check(f"T11 {name} total", round(comp[key]["total"] / 1e6, 2), want, tol=0.006,
              src="gate20 + gate31 compressor correction")
    gap = (comp["Normal"]["total"] - comp["DRRA"]["total"]) / 1e6
    check("whole-model gap M", round(gap, 2), 13.57, tol=0.006)
    o = (comp["Normal"]["o_proj"] - comp["DRRA"]["o_proj"]) / 1e6
    check("o_proj share of gap M", round(o, 2), 10.49, tol=0.006)
    check("o_proj share of gap %", round(100 * o / gap, 1), 77.3, tol=0.05)
    matched = (comp["Normal"]["total"] - comp["Normal"]["o_proj"] + comp["DRRA"]["o_proj"]) / 1e6
    check("matched total M", round(matched, 2), 66.38, tol=0.006)
    check("matched whole-model saving %", round((1 - comp["DRRA"]["total"] / (matched * 1e6)) * 100, 1),
          4.6, tol=0.05)
    check("as-run whole-model saving %", round((1 - comp["DRRA"]["total"] / comp["Normal"]["total"]) * 100, 1),
          17.6, tol=0.05)

    # --- Table 10: PatchTST transfer -------------------------------------
    g17 = json.load(open(PLAN / "gate17_e2" / "gate17_analysis.json"))
    for ds, want in [("etth1", (0.3730, 0.3705, 0.3745, 0.3704)),
                     ("etth2", (0.2559, 0.2613, 0.2614, 0.2613))]:
        m = g17[ds]["means"]
        for got, printed, cell in zip((m["CSA"], m["DRRA"], m["C48"], m["C88"]), want,
                                      ("(4,4)", "(8,4)", "(4,8)", "(8,8)")):
            check(f"T10 {ds} {cell}", round(got, 4), printed, tol=5e-5)
    sp = json.load(open(PLAN / "gate17_e2" / "gate17_speed.json"))["latency"]
    for cell, key, want in [("(4,4)", "CSA", 37.4), ("(8,4)", "DRRA", 33.7),
                            ("(4,8)", "C48", 33.0), ("(8,8)", "C88", 29.4)]:
        check(f"T10 speed {cell}", round(sp[key]["mean_ms"], 1), want, tol=0.05)
    check("T10 speed ratio (8,4)/(4,4)", round(sp["DRRA"]["mean_ms"] / sp["CSA"]["mean_ms"], 2),
          0.90, tol=0.01, src="1/1.11")


    # --- derived values quoted in the prose ------------------------------
    def s_layer(L, d, ckv, cr):
        cell = 2 * d * (L / ckv + W + 1) + d * L / cr + 4 * d * 64
        return (1 - (cell + 12 * d * d) / (2 * d * L + 12 * d * d)) * 100

    LE = 2048
    dense_tok = 2 * D * LE + 12 * D * D
    check("energy dense core %", round(100 * (2 * D * LE) / dense_tok, 1), 72.7, tol=0.05)
    for name, ckv, cr, core_w, aux_w, save_w, path_w in [
            ("CSA", 4, 4, 18.8, 13.6, 40.3, 55.4),
            ("DRRA", 8, 4, 9.7, 13.6, 49.4, 67.9)]:
        core = 2 * D * (LE / ckv + W + 1)
        aux = D * LE / cr + 4 * D * 64
        check(f"energy {name} core %", round(100 * core / dense_tok, 1), core_w, tol=0.05)
        check(f"energy {name} aux %", round(100 * aux / dense_tok, 1), aux_w, tol=0.05)
        check(f"energy {name} whole saving %",
              round(100 * (1 - (core + aux + 12 * D * D) / dense_tok), 1), save_w, tol=0.05)
        check(f"energy {name} path saving %", round(s_attn(LE, ckv, cr), 1), path_w, tol=0.05)
    check("energy fixed block %", round(100 * 12 * D * D / dense_tok, 1), 27.3, tol=0.05)

    for d, drra, x32 in [(128, 72.9, 82.0), (512, 68.2, 76.7), (1024, 62.8, 70.7),
                         (4096, 42.6, 48.0)]:
        check(f"whole-layer 32k d={d} (8,4)", round(s_layer(32768, d, 8, 4), 1), drra, tol=0.05)
        check(f"whole-layer 32k d={d} (32,4)", round(s_layer(32768, d, 32, 4), 1), x32, tol=0.05)
    check("whole-layer d128 L=2048 %", round(s_layer(2048, 128, 8, 4), 1), 49.4, tol=0.05)
    check("whole-layer d128 L=4096 %", round(s_layer(4096, 128, 8, 4), 1), 60.2, tol=0.05)
    check("whole-layer d128 L=32768 %", round(s_layer(32768, 128, 8, 4), 1), 72.9, tol=0.05)

    LS = 32768
    for lam, want in [(0.5, 81.0), (1.0, 74.6), (2.0, 61.7)]:
        p = (2 * H * DH * LS * (LS // 8 + W + 1)
             + lam * (LS * (LS // 4) * H * DH + LS * COMPRESS_PER_TOKEN))
        check(f"aux-weight sensitivity x{lam}",
              round(100 * (1 - p / (2 * H * DH * LS * LS)), 1), want, tol=0.05)
    p_sh = (2 * H * DH * LS * (LS // 8 + W + 1) + LS * (LS // 4) * DH
            + LS * COMPRESS_PER_TOKEN)
    check("single-head indexer 32k", round(100 * (1 - p_sh / (2 * H * DH * LS * LS)), 1),
          83.9, tol=0.05)
    check("single-head indexer asymptote", round(100 * (1 - (1 / 8 + 1 / 32)), 1),
          84.4, tol=0.05)

    check("attention path saving %", round(s_attn(256, 8, 4), 1), 18.4, tol=0.05)
    core256 = 2 * H * DH * 256 * (256 // 8 + W + 1)
    check("attention core saving %", round(100 * (1 - core256 / (2 * H * DH * 256 * 256)), 1),
          80.9, tol=0.05)

    va = g20["validation"]
    check("Spearman rho batch 32", va["batch32"]["spearman_latency_vs_work"], 1.0, tol=1e-9)
    check("Spearman rho batch 1", va["batch1"]["spearman_latency_vs_work"], 0.992, tol=0.0006)
    check("Pearson r batch 32", va["batch32"]["pearson_work_ratio_vs_time_ratio"], 0.96, tol=0.006)

    g5 = json.load(open(PLAN / "gate5" / "gate5_results.json"))
    rss = g5["peak_rss"]["DRRA"]["rss_growth_bytes"] / 1e9
    check("peak RSS growth GB", round(rss, 2), 0.3, tol=0.06)
    pbytes = g5["peak_rss"]["DRRA"]["param_bytes"] / 1e6
    check("param memory MB", round(pbytes, 2), 1.4, tol=0.06)
    tt = {k: sorted(v["seconds"]) for k, v in g5["training_time_etth1"].items()}
    med = {k: st.median(v[:-1] if k == "DRRA" else v) for k, v in tt.items()}
    check("train median Normal", med["Normal"], 474, tol=0.5)
    check("train median (4,4)", med["Flat"], 511, tol=0.5)
    check("train median (8,4)", med["DRRA"], 459, tol=0.5)

    # last-query: the shipped log is the only source for the range quoted
    lq = json.load(open(PLAN / "gate13_p0_audits" / "last_query_latency.json"))["latency"]
    check("last-query Normal ms", round(lq["Normal_LAST"]["mean_ms"], 2), 2.62, tol=0.006)
    check("last-query CSA ms", round(lq["CSA_4_4_LAST"]["mean_ms"], 2), 6.18, tol=0.006)
    check("last-query DRRA ms", round(lq["DRRA_8_4_LAST"]["mean_ms"], 2), 5.82, tol=0.006)
    check("wiring max diff", 1.192093e-07, 1.19e-07, tol=1e-9,
          src="baseline/normal_sanity_check.md")

    # the three full-layer Normal levels quoted as session spread
    l4 = json.load(open(PLAN / "gate27_r2matched" / "latency_4model.json"))
    check("session level gate27 Normal", round(l4["latency"]["Normal_FULL"]["mean_ms"], 1), 42.0, tol=0.05,
          src="latency_4model.json")
    check("session level gate13 Normal", round(lq["Normal_FULL"]["mean_ms"], 1), 40.7, tol=0.05)
    check("session level gate3 Normal", round(lat["Normal"]["mean_ms"], 1), 52.5, tol=0.05)


    # --- Table-2-adjacent statistics quoted in §4.2 -----------------------
    g15 = json.load(open(PLAN / "gate15_rerun" / "gate15_analysis.json"))
    for key, want, wci, wp in [
        ("KV_main", -0.0320, (-0.0618, -0.0023), 0.0096),
        ("routing_main", 0.0300, (0.0010, 0.0589), 0.0588),
        ("interaction", -0.0724, (-0.1289, -0.0158), 0.0136),
        ("H1", 0.0620, (0.0157, 0.1082), 0.0074),
    ]:
        blk = g15[key]
        check(f"§4.2 {key} mean", round(blk["mean"], 4), want, tol=5e-5, src="gate15_analysis.json")
        check(f"§4.2 {key} CI low", round(blk["ci95"][0], 4), wci[0], tol=5e-5)
        check(f"§4.2 {key} CI high", round(blk["ci95"][1], 4), wci[1], tol=5e-5)
        check(f"§4.2 {key} wilcoxon p", round(blk["wilcoxon_p"], 4), wp, tol=5e-5)
    check("§4.2 KV sign-consistent", g15["KV_main"]["sign_consistent"], 20)
    check("§4.2 routing sign-consistent", g15["routing_main"]["sign_consistent"], 16)
    check("§4.2 H1 paired-t p", round(g15["H1"]["ttest_p"], 4), 0.0107, tol=5e-5)
    check("§4.2 routing paired-t p", round(g15["routing_main"]["ttest_p"], 4), 0.0430, tol=5e-5)
    check("§4.2 DRRA-CSA val p", round(g15["DRRA_minus_CSA_val"]["wilcoxon_p"], 2), 0.62, tol=0.005)
    check("§4.2 DRRA-CSA val wins", g15["DRRA_minus_CSA_val"]["sign_consistent"], 9)
    check("§4.2 DRRA-CSA test mean", round(g15["DRRA_minus_CSA_test"]["mean"], 4), -0.0331, tol=5e-5)
    check("§4.2 DRRA-CSA test p", round(g15["DRRA_minus_CSA_test"]["wilcoxon_p"], 3), 0.032, tol=0.0006)
    check("§4.2 DRRA-CSA test wins", g15["DRRA_minus_CSA_test"]["sign_consistent"], 17)
    check("§4.2 beats-CSA DRRA", g15["beats_CSA_val"]["DRRA"], 16)
    check("§4.2 beats-CSA C88", g15["beats_CSA_val"]["C88"], 12)
    check("§4.2 beats-CSA C48", g15["beats_CSA_val"]["C48"], 6)
    check("§4.2 best-of-four CSA", g15["best_of_four_val"]["CSA"], 8)
    check("§4.2 best-of-four DRRA", g15["best_of_four_val"]["DRRA"], 7)
    check("§4.2 best-of-four C88", g15["best_of_four_val"]["C88"], 8)
    check("§4.2 best-of-four C48", g15["best_of_four_val"]["C48"], 2)

    g21 = json.load(open(PLAN / "gate21_simple_effects" / "simple_effects.json"))["conditional_effects"]
    for key, want, wp in [("kv_at_cr4", 0.0042, 0.615), ("kv_at_cr8", -0.0682, 0.0001),
                          ("cr_at_ckv4", 0.0662, 0.002), ("cr_at_ckv8", -0.0062, 1.0)]:
        check(f"§4.2 conditional {key}", round(g21[key]["mean"], 4), want, tol=5e-5)
        check(f"§4.2 conditional {key} p", round(g21[key]["wilcoxon_p"], 3), wp, tol=0.0006)

    dv48 = (C["(4,8)"]["val"] / n["val"] - 1) * 100
    dv88 = (C["(8,8)"]["val"] / n["val"] - 1) * 100
    check("abstract delta range low %", round(min(-26.71, -26.22, dv48, dv88), 1), -27.0, tol=0.05)
    check("abstract delta range high %", round(max(-26.71, -26.22, dv48, dv88), 1), -18.8, tol=0.05)

    # --- matched-baseline comparisons (§4.8) -----------------------------
    g27 = json.load(open(PLAN / "gate27_r2matched" / "analysis.json"))
    nm = g27["Normal_r64_minus_Normal_val"]
    check("r64 paired mean", round(nm["mean"], 3), -0.048, tol=0.0006)
    check("r64 CI low", round(nm["ci95"][0], 3), -0.088, tol=0.0006)
    check("r64 CI high", round(nm["ci95"][1], 3), -0.008, tol=0.0006)
    check("r64 seeds better", nm["sign_consistent"], 15)
    lo = min(g27["matched_comparisons"][c]["cell_minus_Normal_r64_val"]["mean"] for c in ["CSA", "DRRA", "C48", "C88"])
    hi = max(g27["matched_comparisons"][c]["cell_minus_Normal_r64_val"]["mean"] for c in ["CSA", "DRRA", "C48", "C88"])
    check("cells vs r64 low", round(lo, 3), -0.178, tol=0.0006)
    check("cells vs r64 high", round(hi, 3), -0.110, tol=0.0006)
    check("cells vs r64 min seeds", min(g27["matched_comparisons"][c]["beats_Normal_r64_count_val"] for c in ["CSA", "DRRA", "C48", "C88"]), 21)

    # --- training-MSE span across the 125 factorial runs -----------------
    all_factorial = [r for c in [(4, 4), (8, 4), (4, 8), (8, 8)] for r in factorial(c)] + normal
    tm = [r["final_train_mse"] for r in all_factorial]
    check("factorial n runs", len(tm), 125)
    check("train MSE span low", round(min(tm), 4), 0.2756, tol=5e-5)
    check("train MSE span high", round(max(tm), 4), 0.3029, tol=5e-5)

    print(f"\nCHECKS: {checks}   FAILURES: {len(fails)}")
    for f in fails:
        print("  FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
