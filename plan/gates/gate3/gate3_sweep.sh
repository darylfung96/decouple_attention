#!/bin/bash
# Gate 3 sequential sweep — one process at a time, threads=8 (benchmark_protocol).
# Log: plan/gates/gate3/gate3_sweep.log ; results: plan/gates/gate3/results/*.jsonl
# Idempotent: completed (variant, seed) rows are skipped on rerun.
cd "$(dirname "$0")/../../.." || exit 9
PY="${PYTHON:-python3}"
HARNESS="plan/gates/gate3/gate3_harness.py"
DATASETS="etth1 etth2 ettm1 ettm2 electricity traffic weather exchange solar syn_sinusoids syn_changepoints syn_delayedcopy"
VARIANTS="Normal Flat DRRA"
SEEDS="42 123 2024 7 99"
for ds in $DATASETS; do
  for v in $VARIANTS; do
    for s in $SEEDS; do
      echo "=== $ds $v seed=$s START $(date -u +%FT%TZ) ==="
      $PY -u "$HARNESS" --full --dataset "$ds" --variant "$v" --seed "$s" --threads 8 \
        || echo "FAIL $ds $v $s rc=$?"
      echo "=== $ds $v seed=$s DONE $(date -u +%FT%TZ) ==="
    done
  done
done
echo "SWEEP_DONE $(date -u +%FT%TZ)"
