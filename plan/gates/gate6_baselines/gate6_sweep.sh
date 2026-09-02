#!/usr/bin/env bash
# Gate 6 — external-baselines sweep driver (protocol/order mirrors gate3_sweep.sh).
# Idempotent: the harness skips any (variant, seed) already recorded in the
# dataset's results JSONL, so this driver is safe to re-run after interruption.
set -u
cd "$(dirname "$0")/../gate3"   # run from gate3 dir so dataset caches resolve identically

PY="${PY:-/Users/darylfung/Documents/Work/Nicosia/new_attention/.venv-gate6/bin/python}"
SEEDS="42 123 2024 7 99"
THREADS=8

echo "=== Gate 6 baselines sweep started $(date -u +%FT%TZ) ==="
echo "python: $PY"
$PY -c "import torch, pandas, numpy; print('env: torch', torch.__version__, '| pandas', pandas.__version__, '| numpy', numpy.__version__, '| threads', $THREADS)"

for ds in etth1 etth2 ettm1 ettm2 exchange syn_sinusoids syn_changepoints syn_delayedcopy solar electricity weather traffic; do
  for var in DLinear PatchTST; do
    for seed in $SEEDS; do
      echo "--- $ds $var seed=$seed START $(date -u +%FT%TZ) ---"
      "$PY" ../gate6_baselines/gate6_baselines.py --full --dataset "$ds" \
        --variant "$var" --seed "$seed" --threads $THREADS
      rc=$?
      echo "--- $ds $var seed=$seed EXIT=$rc $(date -u +%FT%TZ) ---"
    done
  done
done
echo "=== Gate 6 baselines sweep finished $(date -u +%FT%TZ) ==="
