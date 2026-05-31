#!/bin/bash
# Example job script submitted via the end-of-turn YAML block.
#
# This runs inside the compute container with:
#   - Your workspace mounted at /home/user
#   - GPU(s) available
#   - No internet access
#
# Make sure all data, code, and dependencies are already in the
# workspace or baked into the container before submitting.

set -e

cd /home/user

bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh

python - <<'PY'
import json
from pathlib import Path

from validate import validate_reference, validate_scores

reference = json.loads(Path("scoring/reference.json").read_text())
errors = validate_reference(reference)
for score_path in ("scoring/scores_train.json", "scoring/scores_test.json"):
    scores = json.loads(Path(score_path).read_text())
    errors.extend(f"{score_path}: {err}" for err in validate_scores(scores, reference))
if errors:
    raise SystemExit("\n".join(errors))
PY
