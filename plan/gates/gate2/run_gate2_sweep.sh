#!/bin/zsh
# Gate 2 sweep runner — launched via launchctl to fully detach from shell.
# Log: plan/gates/gate2/gate2_sweep.log (unbuffered python), results: plan/gates/gate2/gate2_results.jsonl (idempotent).
cd /Users/darylfung/Documents/Work/Nicosia/new_attention || exit 9
exec > plan/gates/gate2/gate2_sweep.log 2>&1
for s in 42 123 2024 7 99; do
  echo "=== SWEEP SEED $s START $(date -u +%FT%TZ) ==="
  python3 -u plan/gates/gate2/gate2_factorial.py --full --seed "$s" --threads 8 || echo "SEED $s FAILED rc=$?"
  echo "=== SWEEP SEED $s DONE $(date -u +%FT%TZ) ==="
done
echo "SWEEP_DONE $(date -u +%FT%TZ)"
