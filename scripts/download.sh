#!/bin/bash
# Download all data and models needed for this environment.
#
# Run on a node with internet access BEFORE building the container
# or submitting compute jobs.
#
# This script should be idempotent — safe to run multiple times.
# It should skip files that already exist.
#
# Update the storage estimate below as you add downloads.
#
# Estimated total download size: 0 GB for the default scaled benchmark.
# Estimated disk usage after extraction: <20 MB.
#
# You do not need to run this script during reproduction — it exists
# for future portability. Write it to download to workspace-local
# paths (data/, checkpoints/) instead of the shared directories
# so a future user with just the workspace can run this script and get everything they need.

set -e

cd /home/user

python data/generate_synthetic_tracking.py \
  --output data/synthetic_tracking/loop_patch.npz \
  --frames 144 \
  --surface-size 300

# The full released dataset is hosted as one 73.1 GB archive:
# https://huggingface.co/datasets/joehjhuang/GelSLAM_dataset/blob/main/dataset.zip
# The scaled benchmark above is the default because the full archive is not
# needed for the CPU smoke/core experiment packaged here.
