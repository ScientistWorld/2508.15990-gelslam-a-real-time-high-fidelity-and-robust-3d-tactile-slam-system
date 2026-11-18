#!/bin/bash
# Training/development slice: renders the public episodes in
# data/train_episodes.json, runs every method registered under checkpoints/
# (predict.json), scores them with the eval-owned NormalFlow baseline, and
# writes scoring/scores_train.json. Method outputs are kept under
# checkpoints/<method>/train_outputs/. Takes no arguments.

set -e

cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
mkdir -p scoring

python eval/train/evaluate_train.py --output scoring/scores_train.json "$@"
