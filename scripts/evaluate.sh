#!/bin/bash
# Standard evaluation entry point for development: scores every method
# registered under checkpoints/ on the public training episodes and writes
# scoring/scores.json (same computation as scripts/evaluate_train.sh).
#
# A method is registered by a checkpoints/<dir>/predict.json such as
#   {"name": "my_method",
#    "command": ["python", "-m", "my_pkg.run", "--input", "{input}", "--output", "{output}"]}
# The command must write {output}/poses.npy (N x 4 x 4, mm) and may write
# {output}/loops.json. See briefing/evaluation.md.

set -e

cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
mkdir -p scoring

python eval/train/evaluate_train.py --output scoring/scores.json
