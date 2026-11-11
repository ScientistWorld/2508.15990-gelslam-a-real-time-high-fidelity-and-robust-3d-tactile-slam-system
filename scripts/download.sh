#!/bin/bash
# Fetch/generate everything this environment needs. Idempotent.
#
# The benchmark is synthetic: the evaluators render every episode on the fly
# from code in data/ (training) and eval/test/ (held-out), so no external data
# or model weights are required. This script optionally caches the rendered
# public training episodes (about 100 MB each, 8 episodes) in
# data/downloads/train_episodes/ for inspection.
#
# Optional real-data resources from the paper's release (not used by the
# scored benchmark) can be fetched with the flags below.
#
# Estimated size: 0 GB required; ~0.8 GB with CACHE_TRAIN_EPISODES=1;
# 68 GB with DOWNLOAD_FULL_GELSLAM_DATASET=1.

set -e

cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"

if [ "${CACHE_TRAIN_EPISODES:-0}" = "1" ]; then
  mkdir -p data/downloads/train_episodes
  python data/tactile_sim.py --configs data/train_episodes.json --output-dir data/downloads/train_episodes
fi

if [ "${DOWNLOAD_OFFICIAL_GELSLAM_CALIBRATION:-0}" = "1" ]; then
  mkdir -p data/downloads/gelslam_example_calibration
  if [ ! -e data/downloads/gelslam_example_calibration/nnmodel.pth ]; then
    wget -O data/downloads/gelslam_example_calibration/nnmodel.pth \
      https://raw.githubusercontent.com/rpl-cmu/gelslam/main/src/gelslam/resources/example_calibration/model/nnmodel.pth
  fi
fi

if [ "${DOWNLOAD_FULL_GELSLAM_DATASET:-0}" = "1" ]; then
  mkdir -p data/downloads/gelslam_dataset
  if [ ! -e data/downloads/gelslam_dataset/dataset.zip ]; then
    wget -O data/downloads/gelslam_dataset/dataset.zip \
      https://huggingface.co/datasets/joehjhuang/GelSLAM_dataset/resolve/main/dataset.zip
  fi
fi
