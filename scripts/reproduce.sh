#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# This script runs inside the compute container and should call
# scripts/baseline.sh and scripts/method.sh to run baselines and
# the paper's method, each of which calls scripts/evaluate.sh.
#
# Assumes:
#   - Container is built (environment/container.sif)
#   - Data and models are downloaded (via scripts/download.sh)
#   - Working directory is /home/user
#
# This is the "gold standard" reproduction — 
# You do not need to run this, but keep this in good shape
# so other agents can easily run a full loop of reproduction and get the paper's numbers.

set -e

cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"

echo "[reproduce] generating synthetic tactile benchmark"
python data/generate_synthetic_tracking.py \
  --output data/synthetic_tracking/loop_patch.npz \
  --frames 192 \
  --surface-size 340 \
  --trajectory planar
echo "[reproduce] running NormalFlow baseline"
python baseline/normalflow_baseline.py --dataset data/synthetic_tracking/loop_patch.npz --output-dir checkpoints/normalflow_baseline
echo "[reproduce] running scaled GelSLAM"
python method/scaled_gelslam/run_gelslam.py --dataset data/synthetic_tracking/loop_patch.npz --output-dir checkpoints/scaled_gelslam
echo "[reproduce] evaluating full benchmark"
bash scripts/evaluate.sh
