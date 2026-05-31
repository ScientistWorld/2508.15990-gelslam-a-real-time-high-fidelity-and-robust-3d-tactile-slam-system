#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"

DATASET="${1:-data/synthetic_tracking/loop_patch.npz}"
OUT="${2:-checkpoints/scaled_gelslam}"

python method/scaled_gelslam/run_gelslam.py --dataset "$DATASET" --output-dir "$OUT"
bash scripts/evaluate.sh
