#!/usr/bin/env bash
# Chain: when gate6 reaches its first HEAVY dataset (solar), pause it (SIGSTOP),
# run gate7 to completion, then resume gate6 (SIGCONT). Sequential CPU usage.
set -u
cd "$(dirname "$0")"
PY=/Users/darylfung/Documents/Work/Nicosia/new_attention/.venv-gate6/bin/python
LOG=../gate6_baselines/gate6_sweep.log

echo "[chain] waiting for gate6 to reach the heavy tail (solar START marker)..."
until grep -q -- "--- solar DLinear seed=42 START" "$LOG" 2>/dev/null; do sleep 60; done
G6PID=""
until [ -n "$G6PID" ]; do G6PID=$(pgrep -f "gate6_baselines.py --full" | head -1); sleep 2; done
echo "[chain] pausing gate6 (pid $G6PID) at $(date -u +%FT%TZ)"
kill -STOP "$G6PID" && sleep 2
# verify it's actually stopped before starting gate7
if ps -o stat= -p "$G6PID" | grep -q T; then
  echo "[chain] gate6 confirmed paused; starting gate7 (8 threads)"
  "$PY" gate7_seeds.py --full --threads 8 > gate7_run.log 2>&1
  echo "[chain] gate7 finished at $(date -u +%FT%TZ); resuming gate6"
  kill -CONT "$G6PID"
else
  echo "[chain] WARN: could not confirm pause; running gate7 anyway (some contention possible)"
  "$PY" gate7_seeds.py --full --threads 8 > gate7_run.log 2>&1
fi
echo "[chain] done"
