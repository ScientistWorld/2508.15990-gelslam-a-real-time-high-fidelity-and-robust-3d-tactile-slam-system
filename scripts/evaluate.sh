#!/bin/bash
# Evaluation script — the standard way to evaluate work in this environment.
#
# This script must be SELF-CONTAINED using only code in eval/.
# Do NOT import from method/ — evaluate.sh must work even when the
# paper's method code is hidden from a scientist agent.
#
# Design it so that anyone following the same output format can run
# this script to evaluate their results.
#
# OUTPUT CONTRACT: This script MUST write scoring/scores.json containing
# a JSON dict nested by experiment, e.g.:
#   {"imagenet_classification": {"top1_accuracy": 82.1, "top5_accuracy": 94.8}}
# Experiment and metric names must match the keys in scoring/reference.json.
# This file is read by the system for automated comparison.
#
# Example usage:
#   ./evaluate.sh <method_and_run_name>                             # evaluate with defaults
#   ./evaluate.sh <method_and_run_name> checkpoints/epoch_10.pt     # evaluate a specific checkpoint
#
# Called from run.sh after training, or independently.

set -e

cd /home/user

mkdir -p scoring

ARGS=()
if [ "$#" -gt 0 ]; then
  if [ $(( $# % 2 )) -ne 0 ]; then
    echo "Usage: scripts/evaluate.sh [METHOD_NAME RUN_DIR]..." >&2
    exit 2
  fi
  while [ "$#" -gt 0 ]; do
    ARGS+=(--method-run "$1" "$2")
    shift 2
  done
else
  if [ -f checkpoints/normalflow_baseline/pred_poses.npy ]; then
    ARGS+=(--method-run normalflow checkpoints/normalflow_baseline)
  fi
  if [ -f checkpoints/scaled_gelslam/pred_poses.npy ]; then
    ARGS+=(--method-run gelslam_online checkpoints/scaled_gelslam)
  fi
fi

if [ ${#ARGS[@]} -eq 0 ]; then
  echo "No prediction artifacts found under checkpoints/." >&2
  exit 1
fi

python eval/evaluate_tracking.py "${ARGS[@]}" --output scoring/scores.json
