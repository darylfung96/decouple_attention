"""C-1: factorial recompute from unrounded merged seeds (gate2 5-seed + gate7 20-seed).

Design: plan/gates/gate14_c1/c1_design.md (pre-registered).
Run: ~/.uv_env/py311/bin/python plan/gates/gate14_c1/c1_recompute.py
"""
import json
import numpy as np
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]
G2 = ROOT / "plan/gates/gate2/gate2_results.jsonl"
G7 = ROOT / "plan/gates/gate7_seeds/results/gate7.jsonl"
OUT_JSON = Path(__file__).with_name("c1_recompute.json")
OUT_MD = Path(__file__).with_name("c1_recompute.md")

CELLMAP = {(4, 4): "CSA", (8, 4): "DRRA", (4, 8): "C48", (8, 8): "C88"}
G7MAP = {"CSA(4,4)": "CSA", "DRRA(8,4)": "DRRA", "(4,8)": "C48", "(8,8)": "C88",
         "Normal": "Normal"}


def load():
    data = {}  # (cfg, seed) -> val
    test = {}  # (cfg, seed) -> test
    for line in G2.read_text().splitlines():
        r = json.loads(line)
        data[(CELLMAP[tuple(r["cell"])], r["seed"])] = r["val_mse"]
        test[(CELLMAP[tuple(r["cell"])], r["seed"])] = r["test_mse"]
    for line in (ROOT / "plan/gates/baseline/baseline_normal_results.jsonl").read_text().splitlines():
        r = json.loads(line)
        assert r["cell"] == "Normal"
        data[("Normal", r["seed"])] = r["val_mse"]
        test[("Normal", r["seed"])] = r["test_mse"]
    for line in G7.read_text().splitlines():
        r = json.loads(line)
        key = (G7MAP[r["cell_name"]], r["seed"])
        assert key not in data, f"duplicate {key}"
        data[key] = r["val_mse"]
        test[key] = r["test_mse"]
    return data, test


def est(x):
    x = np.asarray(x, float)
    m = float(x.mean())
    ci = stats.t.interval(0.95, len(x) - 1, loc=m, scale=stats.sem(x))
    try:
        w = stats.wilcoxon(x)
        wp = float(w.pvalue)
    except Exception as e:
        wp = f"n/a ({e})"
    tp = float(stats.ttest_rel(x, np.zeros_like(x)).pvalue)
    return {"mean": m, "ci95": [float(ci[0]), float(ci[1])], "wilcoxon_p": wp,
            "ttest_p": tp, "n": len(x),
            "sign_consistent": int((np.sign(x) == np.sign(m)).sum())}


def main():
    data, test = load()
    seeds = sorted(set(s for _, s in data))
    cfgs = ["CSA", "DRRA", "C48", "C88", "Normal"]
    assert len(seeds) == 25, seeds
    for c in cfgs:
        assert sum((c, s) in data for s in seeds) == 25, c
    Y = {c: np.array([data[(c, s)] for s in seeds]) for c in cfgs}
    kv = (Y["DRRA"] + Y["C88"]) / 2 - (Y["CSA"] + Y["C48"]) / 2
    rt = (Y["C48"] + Y["C88"]) / 2 - (Y["CSA"] + Y["DRRA"]) / 2
    inter = (Y["C88"] - Y["DRRA"]) - (Y["C48"] - Y["CSA"])
    h1 = rt - kv
    offdiag = Y["C48"] - Y["DRRA"]
    res = {"n_seeds": 25, "seeds": seeds,
           "cell_means": {c: {"mean": float(Y[c].mean()), "std": float(Y[c].std(ddof=1))} for c in cfgs},
           "KV_main": est(kv), "routing_main": est(rt), "interaction": est(inter),
           "H1_routing_minus_KV": est(h1),
           "offdiag_y48_minus_y84": est(offdiag),
           "H1_identity_maxdiff": float(np.abs(h1 - offdiag).max()),
           "DRRA_minus_CSA": est(Y["DRRA"] - Y["CSA"])}
    for c in ["CSA", "DRRA", "C48", "C88"]:
        res[f"{c}_minus_Normal"] = est(Y[c] - Y["Normal"])
    # counts
    cells4 = ["CSA", "DRRA", "C48", "C88"]
    best = [cells4[int(np.argmin([Y[c][i] for c in cells4]))] for i in range(25)]
    from collections import Counter
    res["best_of_four_counts"] = dict(Counter(best))
    res["beats_CSA"] = {c: int((Y[c] < Y["CSA"]).sum()) for c in ["DRRA", "C48", "C88", "Normal"]}
    res["beats_Normal"] = {c: int((Y[c] < Y["Normal"]).sum()) for c in cells4}
    res["compressed_beats_Normal_total"] = sum(res["beats_Normal"].values())
    # D-2: test-side DRRA-vs-CSA (unrounded test MSE)
    from collections import Counter as _C
    T = {c: np.array([test[(c, s)] for s in seeds]) for c in cfgs}
    res["test_DRRA_minus_CSA"] = est(T["DRRA"] - T["CSA"])
    res["test_cell_means"] = {c: float(T[c].mean()) for c in cfgs}
    tb = [["CSA", "DRRA", "C48", "C88"][int(np.argmin([T[c][i] for c in ["CSA", "DRRA", "C48", "C88"]]))] for i in range(25)]
    res["test_best_of_four_counts"] = dict(_C(tb))
    res["test_beats_CSA"] = {c: int((T[c] < T["CSA"]).sum()) for c in ["DRRA", "C48", "C88"]}
    # verification vs paper (rounded values quoted in experiments.tex)
    paper = {"DRRA_mean": 0.6190, "DRRA_std": 0.0827, "CSA_mean": 0.6575, "CSA_std": 0.0686,
             "C48_mean": 0.6994, "C88_mean": 0.6347, "Normal_mean": 0.8389,
             "KV": -0.0516, "RT": 0.0288, "H1": 0.080, "H1_wilcox": 0.0032, "H1_t": 0.0013}
    chk = {
        "DRRA_mean": res["cell_means"]["DRRA"]["mean"], "DRRA_std": res["cell_means"]["DRRA"]["std"],
        "CSA_mean": res["cell_means"]["CSA"]["mean"], "CSA_std": res["cell_means"]["CSA"]["std"],
        "C48_mean": res["cell_means"]["C48"]["mean"], "C88_mean": res["cell_means"]["C88"]["mean"],
        "Normal_mean": res["cell_means"]["Normal"]["mean"],
        "KV": res["KV_main"]["mean"], "RT": res["routing_main"]["mean"],
        "H1": res["H1_routing_minus_KV"]["mean"],
        "H1_wilcox": res["H1_routing_minus_KV"]["wilcoxon_p"],
        "H1_t": res["H1_routing_minus_KV"]["ttest_p"]}
    res["paper_verification"] = {k: {"paper": paper[k], "recomputed": v,
                                     "match": bool(abs(v - paper[k]) < 5e-5)} for k, v in chk.items()}
    OUT_JSON.write_text(json.dumps(res, indent=2))
    L = ["# C-1 factorial recompute (25 unrounded seeds)", "",
         f"Design: `c1_design.md` | rows: {len(data)} (25 seeds x 5 configs, no duplicates)", "",
         "## Estimates (validation MSE)", "",
         "| estimate | mean | 95% CI | Wilcoxon p | t p | sign x/25 |",
         "|---|---|---|---|---|---|"]
    for k in ["KV_main", "routing_main", "interaction", "H1_routing_minus_KV",
              "DRRA_minus_CSA", "CSA_minus_Normal", "DRRA_minus_Normal"]:
        e = res[k]
        L.append(f"| {k} | {e['mean']:+.4f} | [{e['ci95'][0]:+.4f},{e['ci95'][1]:+.4f}] | {e['wilcoxon_p']} | {e['ttest_p']:.4f} | {e['sign_consistent']}/25 |")
    L += ["", f"H1 ≡ off-diagonal identity maxdiff: {res['H1_identity_maxdiff']:.2e}", "",
          "## Counts", "",
          f"best-of-four: `{res['best_of_four_counts']}` | beats-CSA: `{res['beats_CSA']}` | "
          f"beats-Normal: `{res['beats_Normal']}` (total {res['compressed_beats_Normal_total']}/100)", "",
          "## D-2 test side (unrounded test MSE)", "",
          f"test means: `{res['test_cell_means']}`",
          f"DRRA-CSA test: mean {res['test_DRRA_minus_CSA']['mean']:+.4f} CI [{res['test_DRRA_minus_CSA']['ci95'][0]:+.4f},{res['test_DRRA_minus_CSA']['ci95'][1]:+.4f}] "
          f"Wilcoxon {res['test_DRRA_minus_CSA']['wilcoxon_p']:.4f} sign {res['test_DRRA_minus_CSA']['sign_consistent']}/25",
          f"test best-of-four: `{res['test_best_of_four_counts']}` | test beats-CSA: `{res['test_beats_CSA']}`", "",
          "## Paper verification", ""]
    for k, v in res["paper_verification"].items():
        L.append(f"- {k}: paper {v['paper']} vs recomputed {v['recomputed']:.6f} → {'MATCH' if v['match'] else 'MISMATCH'}")
    OUT_MD.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\nwrote {OUT_JSON} {OUT_MD}")


if __name__ == "__main__":
    main()
