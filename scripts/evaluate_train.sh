#!/bin/bash
# Train-slice evaluation entry point.
#
# Mirrors scripts/evaluate.sh: pass METHOD_NAME RUN_DIR pairs explicitly, or
# omit arguments to enumerate every checkpoint directory with pred_poses.npy.

set -e

cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"

mkdir -p scoring
DATASET="${DATASET:-data/synthetic_tracking/loop_patch.npz}"

ARGS=()
if [ "$#" -gt 0 ]; then
  if [ $(( $# % 2 )) -ne 0 ]; then
    echo "Usage: scripts/evaluate_train.sh [METHOD_NAME RUN_DIR]..." >&2
    exit 2
  fi
  while [ "$#" -gt 0 ]; do
    ARGS+=(--method-run "$1" "$2")
    shift 2
  done
else
  ARGS+=(--discover-root checkpoints)
fi

python eval/train/evaluate_tracking_slice.py "${ARGS[@]}" --dataset "$DATASET" --output scoring/scores_train.json
