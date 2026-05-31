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
# Optional full dataset download: 68.1 GiB compressed / 73.1 GB reported.
# Estimated disk usage after default generation: <20 MB.
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

mkdir -p method/gelslam/src/gelslam/resources/example_calibration/model
if [ ! -e method/gelslam/src/gelslam/resources/example_calibration/model/nnmodel.pth ]; then
  wget -O method/gelslam/src/gelslam/resources/example_calibration/model/nnmodel.pth \
    https://raw.githubusercontent.com/rpl-cmu/gelslam/main/src/gelslam/resources/example_calibration/model/nnmodel.pth
fi

# The full released GelSLAM dataset is not required for the packaged CPU core
# experiment, but this verified optional path lets a future agent fetch it for
# higher-milestone real-data work without guessing a URL.
if [ "${DOWNLOAD_FULL_GELSLAM_DATASET:-0}" = "1" ]; then
  mkdir -p data/downloads/gelslam_dataset
  if [ ! -e data/downloads/gelslam_dataset/dataset.zip ]; then
    wget -O data/downloads/gelslam_dataset/dataset.zip \
      https://huggingface.co/datasets/joehjhuang/GelSLAM_dataset/resolve/main/dataset.zip
  fi
fi
