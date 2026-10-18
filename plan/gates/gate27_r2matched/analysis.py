# Gate 27 — R2 analysis (pre-registered in design.md).

# Matched dense baseline (Normal_r64, this gate) vs the kept legacy Normal rows and
# the four factorial cells. Merging of the legacy rows is imported from
# gate15_analyze.load_factorial so the paper's arrays are reproduced, not re-derived.
# Old manifests are only read.
#
# Run: ~/.uv_env/py311/bin/python plan/gates/gate27_r2matched/analysis.py
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

sys.path.insert(0, str(ROOT / "plan" / "gates" / "gate15_rerun"))
from gate15_analyze import est, load_factorial  # noqa: E402

MATCHED = HERE / "results" / "normal_r64.jsonl"
OUT_JSON = HERE / "analysis.json"
OUT_MD = HERE / "analysis.md"

CELLS4 = ["CSA", "DRRA", "C48", "C88"]

# ── MAC accounting (same formulas as paper/scripts/make_figures.py at L=256) ──
L, D, H, DH, F, W, HOR = 256, 128, 4, 32, 7, 16, 96


def attn_normal(L):
    return 2 * H * L * L * DH


def rest_exact(L, o_rank):
    wrapper = L * F * D + 2 * L * D * (4 * D) + D * (HOR * F)
    q_lora = L * D * 64 + L * 64 * (H * DH)
    kv = L * D * DH
    o_proj = L * (H * DH // 4) * (4 * o_rank) + L * (4 * o_rank) * D
    return wrapper + q_lora + kv + o_proj


def path_cell(L, ckv, cr):
    attn = 2 * H * L * (L // ckv + W + 1) * DH
    router = L * (L // cr) * H * DH
    compress = 2 * L * D * 64 + 2 * L * D * DH
    return attn + router + compress


def macs():
    total = {
        "Normal": attn_normal(L) + rest_exact(L, 128),
        "Normal_r64": attn_normal(L) + rest_exact(L, 64),
    }
    for ckv, cr in [(4, 4), (8, 4), (4, 8), (8, 8)]:
        total[f"({ckv},{cr})"] = path_cell(L, ckv, cr) + rest_exact(L, 64)
    # self-check against the published percentages
    whole = 1 - total["(8,4)"] / total["Normal"]
    matched = 1 - total["(8,4)"] / total["Normal_r64"]
    assert abs(whole - 0.204) < 0.001, whole
    assert abs(matched - 0.078) < 0.001, matched
    return total, whole, matched


def load_matched(seeds):
    rows = {}
    for line in MATCHED.read_text().splitlines():
        r = json.loads(line)
        rows[int(r["seed"])] = (r["val_mse"], r["test_mse"])
    assert len(rows) == len(seeds), f"matched rows {len(rows)} != seeds {len(seeds)}"
    assert set(rows) == set(seeds), set(rows) ^ set(seeds)
    return {s: rows[s][0] for s in seeds}, {s: rows[s][1] for s in seeds}


def main():
    seeds, Y, T = load_factorial()
    seeds = list(seeds)
    mY, mT = load_matched(seeds)
    Y64 = np.array([mY[s] for s in seeds])
    T64 = np.array([mT[s] for s in seeds])
    Y, T = dict(Y), dict(T)          # copies: register the matched arrays for the
    Y["Normal_r64"], T["Normal_r64"] = Y64, T64   # table loops below

    total_macs, whole_pct, matched_pct = macs()
    res = {
        "provenance": "gate27 matched rows (new) + gate15/kept legacy rows (read-only)",
        "n_seeds": len(seeds),
        "seeds": seeds,
        "cell_means_val": {c: float(Y[c].mean()) for c in CELLS4 + ["Normal", "Normal_r64"]},
        "cell_means_test": {c: float(T[c].mean()) for c in CELLS4 + ["Normal", "Normal_r64"]},
        "macs_per_seq_L256": {k: float(v) for k, v in total_macs.items()},
        "mac_saving_vs_Normal": float(whole_pct),
        "mac_saving_vs_Normal_r64": float(matched_pct),
    }

    # 1) the projection's own effect on the dense model
    res["Normal_r64_minus_Normal_val"] = est(Y64 - Y["Normal"])
    res["Normal_r64_minus_Normal_test"] = est(T64 - T["Normal"])
    res["Normal_r64_better_than_Normal_count"] = int((Y64 < Y["Normal"]).sum())

    # 2) each cell vs the matched baseline (primary comparisons)
    res["matched_comparisons"] = {}
    for c in CELLS4:
        e_val = est(Y[c] - Y64)
        e_test = est(T[c] - T64)
        res["matched_comparisons"][c] = {
            "cell_minus_Normal_r64_val": e_val,
            "cell_minus_Normal_r64_test": e_test,
            "beats_Normal_r64_count_val": int((Y[c] < Y64).sum()),
            "decision": ("KEEP: claim holds at matched projection"
                         if e_val["ci95"][1] < 0 else
                         "NARROW: claim narrows to the attention path"),
        }
        # 3) legacy reference (recomputed for a self-contained table)
        res["matched_comparisons"][c]["cell_minus_Normal_val"] = est(Y[c] - Y["Normal"])

    # decision summary
    res["decision"] = {
        "all_cells_keep": all(res["matched_comparisons"][c]["decision"].startswith("KEEP")
                              for c in CELLS4),
        "per_cell": {c: res["matched_comparisons"][c]["decision"] for c in CELLS4},
    }

    OUT_JSON.write_text(json.dumps(res, indent=2))

    def line(tag, e):
        return (f"| {tag} | {e['mean']:+.4f} | [{e['ci95'][0]:+.4f}, {e['ci95'][1]:+.4f}] | "
                f"{e['wilcoxon_p']:.4g} | {e['sign_consistent']}/{e['n']} |")

    L_ = ["# Gate 27 — R2 projection-matched dense baseline: analysis", "",
          f"Matched rows: `results/normal_r64.jsonl` ({len(seeds)} seeds) · legacy Normal and the four "
          "factorial cells: unchanged manifests, merged as in `gate15_analyze.load_factorial`.", "",
          "## Means (validation MSE)", ""]
    for c in CELLS4 + ["Normal_r64", "Normal"]:
        L_.append(f"- {c}: val {res['cell_means_val'][c]:.4f} · test {res['cell_means_test'][c]:.4f}")
    L_ += ["", "## Comparisons (paired per-seed, n=25)", "",
           "| comparison | mean delta | 95% interval | Wilcoxon p | sign |", "|---|---|---|---|---|",
           line("Normal_r64 − Normal (val)", res["Normal_r64_minus_Normal_val"]),
           line("Normal_r64 − Normal (test)", res["Normal_r64_minus_Normal_test"])]
    for c in CELLS4:
        mc = res["matched_comparisons"][c]
        L_.append(line(f"{c} − Normal_r64 (val)", mc["cell_minus_Normal_r64_val"]))
        L_.append(line(f"{c} − Normal_r64 (test)", mc["cell_minus_Normal_r64_test"]))
    L_ += ["", "## Predeclared decision rule", ""]
    for c in CELLS4:
        d = res["matched_comparisons"][c]
        L_.append(f"- {c}: **{d['decision']}** — interval "
                  f"[{d['cell_minus_Normal_r64_val']['ci95'][0]:+.4f}, "
                  f"{d['cell_minus_Normal_r64_val']['ci95'][1]:+.4f}], "
                  f"beats matched in {d['beats_Normal_r64_count_val']}/25 seeds")
    L_ += ["", "## MAC context (L=256, per sequence; same accounting as the paper)", "",
           f"- as-run Normal {total_macs['Normal']/1e6:.2f}M · Normal_r64 {total_macs['Normal_r64']/1e6:.2f}M "
           f"· (8,4) {total_macs['(8,4)']/1e6:.2f}M",
           f"- whole-model saving as published: {whole_pct*100:.1f}% (as-run) vs "
           f"{matched_pct*100:.1f}% (projection-matched, before accuracy) — asserted in `macs()`", ""]
    OUT_MD.write_text("\n".join(L_))
    print("\n".join(L_))
    print(f"\nwrote {OUT_JSON.name}, {OUT_MD.name}")


if __name__ == "__main__":
    main()
