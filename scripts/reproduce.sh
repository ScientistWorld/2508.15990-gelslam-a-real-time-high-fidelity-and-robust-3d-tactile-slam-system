#!/bin/bash
# Reproduce the paper's results end-to-end on the synthetic tactile benchmark:
# register GelSLAM, score it with the NormalFlow baseline on the public training
# episodes (scoring/scores.json, scoring/scores_train.json) and on the hidden
# held-out episodes (scoring/scores_test.json). CPU only.

set -e

cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"

echo "[reproduce] registering GelSLAM and scoring the training episodes"
bash scripts/method.sh
echo "[reproduce] training slice"
bash scripts/evaluate_train.sh
echo "[reproduce] hidden test slice"
bash scripts/evaluate_test.sh
