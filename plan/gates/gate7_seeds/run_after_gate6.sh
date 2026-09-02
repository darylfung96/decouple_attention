#!/usr/bin/env bash
# Wait for the Gate-6 baselines sweep to finish, then run Gate-7 seeds (4 threads).
set -u
cd "$(dirname "$0")"
PY=/Users/darylfung/Documents/Work/Nicosia/new_attention/.venv-gate6/bin/python
echo "[chain] waiting for gate6 sweep to finish..."
while pgrep -f "gate6_sweep.sh" > /dev/null || pgrep -f "gate6_baselines.py --full" > /dev/null; do
  sleep 60
done
echo "[chain] gate6 done at $(date -u +%FT%TZ); starting gate7 with 4 threads"
"$PY" gate7_seeds.py --full --threads 4 > gate7_run.log 2>&1
echo "[chain] gate7 finished at $(date -u +%FT%TZ)"
