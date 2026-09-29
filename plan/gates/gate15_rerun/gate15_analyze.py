# Gate15 v2 analysis (pre-registered in v2_refresh_plan.md section A).

# Merges old-kept rows ((8,4)/Normal) + gate15-new rows (fixed (4,4)/(4,8)/(8,8),
# suite Flat). Old manifests never modified.
# Outputs: plan/gates/gate15_rerun/gate15_analysis.json + .md
# Run: ~/.uv_env/py311/bin/python plan/gates/gate15_rerun/gate15_analyze.py
import json
import numpy as np
from pathlib import Path
from scipy import stats
from collections import Counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # HERE is the gate15_rerun dir (unlike file-based scripts)
OUT_JSON = HERE / "gate15_analysis.json"
OUT_MD = HERE / "gate15_analysis.md"

G2 = ROOT / "plan/gates/gate2/gate2_results.jsonl"
G7 = ROOT / "plan/gates/gate7_seeds/results/gate7.jsonl"
BASE = ROOT / "plan/gates/baseline/baseline_normal_results.jsonl"
G15F = HERE / "results" / "factorial.jsonl"
G3DIR = ROOT / "plan/gates/gate3/results"
G15S = HERE / "results" / "suite_flat"

CELLMAP = {(4, 4): "CSA", (8, 4): "DRRA", (4, 8): "C48", (8, 8): "C88"}
G7MAP = {"CSA(4,4)": "CSA", "DRRA(8,4)": "DRRA", "(4,8)": "C48", "(8,8)": "C88",
         "Normal": "Normal"}
SUITE_DS = ["etth1", "etth2", "ettm1", "ettm2", "electricity", "traffic", "weather",
            "exchange", "solar", "syn_sinusoids", "syn_changepoints", "syn_delayedcopy"]


def est(x):
    x = np.asarray(x, float)
    m = float(x.mean())
    ci = stats.t.interval(0.95, len(x) - 1, loc=m, scale=stats.sem(x))
    try:
        wp = float(stats.wilcoxon(x).pvalue)
    except Exception as e:
        wp = f"n/a ({e})"
    tp = float(stats.ttest_rel(x, np.zeros_like(x)).pvalue)
    return {"mean": m, "ci95": [float(ci[0]), float(ci[1])], "wilcoxon_p": wp,
            "ttest_p": tp, "n": len(x),
            "sign_consistent": int((np.sign(x) == np.sign(m)).sum())}


def load_factorial():
    """v2: NEW fixed rows for CSA/C48/C88; KEPT rows for DRRA/Normal."""
    new, old = {}, {}
    for line in G15F.read_text().splitlines():
        r = json.loads(line)
        new[(CELLMAP[tuple(r["cell"])], r["seed"])] = (r["val_mse"], r["test_mse"])
    for line in G2.read_text().splitlines():
        r = json.loads(line)
        old[(CELLMAP[tuple(r["cell"])], r["seed"])] = (r["val_mse"], r["test_mse"])
    for line in G7.read_text().splitlines():
        r = json.loads(line)
        old[(G7MAP[r["cell_name"]], r["seed"])] = (r["val_mse"], r["test_mse"])
    for line in BASE.read_text().splitlines():
        r = json.loads(line)
        old[("Normal", r["seed"])] = (r["val_mse"], r["test_mse"])
    seeds = sorted(set(s for _, s in new))
    assert len(seeds) == 25, len(seeds)
    for c in ["CSA", "C48", "C88"]:
        assert sum((c, s) in new for s in seeds) == 25, c
    for c in ["DRRA", "Normal"]:
        assert sum((c, s) in old for s in seeds) == 25, c
    Y = {c: np.array([new[(c, s)][0] for s in seeds]) for c in ["CSA", "C48", "C88"]}
    Y.update({c: np.array([old[(c, s)][0] for s in seeds]) for c in ["DRRA", "Normal"]})
    T = {c: np.array([new[(c, s)][1] for s in seeds]) for c in ["CSA", "C48", "C88"]}
    T.update({c: np.array([old[(c, s)][1] for s in seeds]) for c in ["DRRA", "Normal"]})
    return seeds, Y, T


def load_suite():
    """v2: NEW fixed Flat rows; KEPT DRRA/Normal rows from gate3."""
    flat, ref = {}, {}
    for ds in SUITE_DS:
        for line in (G15S / f"{ds}.jsonl").read_text().splitlines():
            r = json.loads(line)
            flat[(ds, r["seed"])] = (r["val_mse"], r["test_mse"])
    for ds in SUITE_DS:
        for line in (G3DIR / f"{ds}.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r["variant"] in ("DRRA", "Normal"):
                ref[(ds, r["variant"], r["seed"])] = (r["val_mse"], r["test_mse"])
    for ds in SUITE_DS:
        assert sum((ds, s) in flat for s in [42, 123, 2024, 7, 99]) == 5, ds
    return flat, ref


def main():
    res = {"provenance": "v2: gate15-new (fixed mapping) + kept (8,4)/Normal; old manifests untouched"}
    seeds, Y, T = load_factorial()
    res["n_seeds"] = 25
    res["cell_means_val"] = {c: {"mean": float(Y[c].mean()), "std": float(Y[c].std(ddof=1))}
                             for c in ["CSA", "DRRA", "C48", "C88", "Normal"]}
    res["cell_means_test"] = {c: float(T[c].mean()) for c in ["CSA", "DRRA", "C48", "C88", "Normal"]}
    kv = (Y["DRRA"] + Y["C88"]) / 2 - (Y["CSA"] + Y["C48"]) / 2
    rt = (Y["C48"] + Y["C88"]) / 2 - (Y["CSA"] + Y["DRRA"]) / 2
    res["KV_main"] = est(kv)
    res["routing_main"] = est(rt)
    res["interaction"] = est((Y["C88"] - Y["DRRA"]) - (Y["C48"] - Y["CSA"]))
    res["H1"] = est(rt - kv)
    res["DRRA_minus_CSA_val"] = est(Y["DRRA"] - Y["CSA"])
    res["DRRA_minus_CSA_test"] = est(T["DRRA"] - T["CSA"])
    for c in ["CSA", "DRRA", "C48", "C88"]:
        res[f"{c}_minus_Normal"] = est(Y[c] - Y["Normal"])
    cells4 = ["CSA", "DRRA", "C48", "C88"]
    res["best_of_four_val"] = dict(Counter(
        [cells4[int(np.argmin([Y[c][i] for c in cells4]))] for i in range(25)]))
    res["best_of_four_test"] = dict(Counter(
        [cells4[int(np.argmin([T[c][i] for c in cells4]))] for i in range(25)]))
    res["beats_CSA_val"] = {c: int((Y[c] < Y["CSA"]).sum()) for c in ["DRRA", "C48", "C88"]}
    res["beats_CSA_test"] = {c: int((T[c] < T["CSA"]).sum()) for c in ["DRRA", "C48", "C88"]}
    res["beats_Normal"] = {c: int((Y[c] < Y["Normal"]).sum()) for c in cells4}
    # suite v2
    flat, ref = load_suite()
    fmeans, dmeans = {}, {}
    for ds in SUITE_DS:
        fv = np.array([flat[(ds, s)][0] for s in [42, 123, 2024, 7, 99]])
        dv = np.array([ref[(ds, "DRRA", s)][0] for s in [42, 123, 2024, 7, 99]])
        nv = np.array([ref[(ds, "Normal", s)][0] for s in [42, 123, 2024, 7, 99]])
        fmeans[ds] = float(fv.mean())
        dmeans[ds] = float(dv.mean())
        res.setdefault("suite", {})[ds] = {
            "flat_mean": float(fv.mean()), "drra_mean": float(dv.mean()),
            "normal_mean": float(nv.mean()),
            "flat_minus_normal": est(fv - nv),
            "drra_minus_flat": est(dv - fv)}
    res["suite_flat_best_count"] = sum(1 for ds in SUITE_DS
                                       if fmeans[ds] < min(dmeans[ds], res["suite"][ds]["normal_mean"]))
    OUT_JSON.write_text(json.dumps(res, indent=2))
    L = ["# Gate15 v2 analysis (fixed mapping)", "",
         "## Factorial (25 seeds; new CSA/C48/C88 + kept DRRA/Normal)", ""]
    for c in cells4 + ["Normal"]:
        m = res["cell_means_val"][c]
        L.append(f"- {c}: val {m['mean']:.4f}±{m['std']:.4f} test {res['cell_means_test'][c]:.4f}")
    for k in ["KV_main", "routing_main", "interaction", "H1", "DRRA_minus_CSA_val",
              "DRRA_minus_CSA_test"]:
        e = res[k]
        L.append(f"- {k}: {e['mean']:+.4f} [{e['ci95'][0]:+.4f},{e['ci95'][1]:+.4f}] "
                 f"wilcoxon {e['wilcoxon_p']} t {e['ttest_p']:.4f} sign {e['sign_consistent']}/25")
    L += ["", f"best-of-four val: `{res['best_of_four_val']}` test: `{res['best_of_four_test']}`",
          f"beats-CSA val: `{res['beats_CSA_val']}` test: `{res['beats_CSA_test']}`",
          f"beats-Normal: `{res['beats_Normal']}`", "", "## Suite Flat v2 (5 seeds)", ""]
    for ds in SUITE_DS:
        s = res["suite"][ds]
        L.append(f"- {ds}: flat {s['flat_mean']:.4f} drra {s['drra_mean']:.4f} "
                 f"normal {s['normal_mean']:.4f} | flat-vs-normal p={s['flat_minus_normal']['wilcoxon_p']}")
    L.append(f"Flat best-mean count: {res['suite_flat_best_count']}/12")
    OUT_MD.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\nwrote {OUT_JSON} {OUT_MD}")


if __name__ == "__main__":
    main()
