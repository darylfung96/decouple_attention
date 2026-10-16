# Gate19 manifest note — `cell` label in the shipped rows

The 25 shipped rows in `results/etth1.jsonl` carry `"cell": [16, 4]` in the
`cell` field while the module was constructed with `compress_rate=32`
(`EPPTimeSeriesModel(NUM_FEATURES, 32, 4, ...)`, `gate19_run.py`). The label is
a copy/paste error in the driver; the *values* belong to $(32,4)$. Three
independent checks:

1. `attn_params = 97,188` in every row, which is the $(32,4)$ row of the paper's
   configuration table (the $(16,4)$ cell of `gate18_d5` carries `96,164`).
2. `full_params = 349,892` likewise matches the $(32,4)$ row.
3. `provenance = "gate19/uv-torch2.6.0/exploratory"` and the directory the rows
   live in identify the probe unambiguously.

Consumers read these rows **by directory plus parameter count**, never by the
`cell` field (`paper/scripts/make_figures.py` `_exp = {"(32,4)*": "gate19_324"}`;
`plan/gates/gate15_rerun/gate15_analyze.py` reads only the factorial manifest), so
no analysis in this project is affected.

Rules followed: old manifests are never modified. The driver now writes the
correct `[32, 4]` label, so any future run of the same script in a fresh results
file is self-describing. If the results JSONL is ever regenerated for a release,
it will carry the corrected label; until then this note is the correction of
record.

Logged 2026-10-16 (Q1-review pass, item "rebuild the evidential chain": audit
each manifest field a reader could check against the paper).
