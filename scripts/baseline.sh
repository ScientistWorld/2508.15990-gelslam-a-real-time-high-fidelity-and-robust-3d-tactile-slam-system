#!/bin/bash
# The NormalFlow frame-to-frame baseline (paper Table IV "NF") is scored by
# every evaluator run under the name "normalflow" from an eval-owned frozen copy
# (eval/*/frozen_normalflow.py). This script runs the public copy in baseline/
# on the training episodes for inspection; outputs go to tmp/baseline_outputs/.
#
# Usage: bash scripts/baseline.sh

set -e

cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"

python data/tactile_sim.py --configs data/train_episodes.json --output-dir data/downloads/train_episodes
for ep in data/downloads/train_episodes/*.npz; do
  name=$(basename "$ep" .npz)
  python -m baseline.normalflow_baseline --input "$ep" --output "tmp/baseline_outputs/$name"
  echo "[baseline] wrote tmp/baseline_outputs/$name"
done
