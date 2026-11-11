#!/bin/bash
# Hidden test: renders the held-out tactile episodes (defined only in eval/test/),
# runs every method registered under checkpoints/ (any directory with a
# predict.json; artifact directories without one are scored as failed), scores
# each method together with the eval-owned NormalFlow baseline, and writes
# scoring/scores_test.json. Takes no arguments.

set -e

cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
mkdir -p scoring

python eval/test/evaluate_test.py --output scoring/scores_test.json
