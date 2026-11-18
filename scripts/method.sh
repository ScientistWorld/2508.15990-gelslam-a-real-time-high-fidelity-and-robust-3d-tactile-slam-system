#!/bin/bash
# Register the paper's method (GelSLAM, method/gelslam_sim/) so every evaluator
# runs it, then score it on the public training episodes.
#
# Usage: bash scripts/method.sh

set -e

cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"

mkdir -p checkpoints/gelslam_online
cat > checkpoints/gelslam_online/predict.json <<'JSON'
{
  "name": "gelslam_online",
  "command": ["python", "-m", "method.gelslam_sim.run", "--input", "{input}", "--output", "{output}"]
}
JSON
bash scripts/evaluate.sh "$@"
