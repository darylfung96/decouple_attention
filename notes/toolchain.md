# Toolchain — new_attention environment (project notes)

## Python virtualenv (settled 2026-09-28)

- Global rule (all projects): ALWAYS use `uv` — never plain `python -m venv` / `.venv` / system python for runs. Canonical: `~/pi-memory/shared/toolchain.md`.
- This project (`new_attention`): canonical interpreter `~/.uv_env/py311/bin/python` (Python 3.11.12, torch 2.6.0 — matches `plan/environment-lock.txt` `torch==2.6.0`).
- Do NOT use `/opt/homebrew/bin/python3.13` (torch 2.12.1, wrong version) or system python3 for runs.
- Repo `.venv` (12MB, pip-only, no torch, nothing executed from it) REMOVED 2026-09-28. Kept: `.venv-gate6` (246MB, Gate-6 baselines env, still referenced by `gate6_sweep.sh` / `run_after_gate6.sh` / `gate6_audit.py` / `gate7_stats.py` — do not delete without migrating those scripts).
- Rationale: Gate-13 P0 audits (2026-09-28) initially ran under homebrew python3.13/torch-2.12.1 before this decision; canonical reruns use the uv env so numbers match the lock file.
- Repro commands:
  - `~/.uv_env/py311/bin/python plan/gates/gate13_p0_audits/last_query_audit.py`
  - `~/.uv_env/py311/bin/python plan/gates/gate13_p0_audits/router_grad_audit.py`
