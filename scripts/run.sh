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

bash scripts/reproduce.sh
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh

python - <<'PY'
import json
from pathlib import Path

full = json.loads(Path("scoring/scores.json").read_text())
train = json.loads(Path("scoring/scores_train.json").read_text())
test = json.loads(Path("scoring/scores_test.json").read_text())
reference = json.loads(Path("scoring/reference.json").read_text())

reference_exps = set(reference["experiments"])
score_sets = {"full": full, "train": train, "test": test}
for slice_name, scores in score_sets.items():
    score_exps = set(scores["experiments"])
    if score_exps != reference_exps:
        raise SystemExit(
            f"{slice_name} experiment mismatch: scores={sorted(score_exps)} reference={sorted(reference_exps)}"
        )

for exp in sorted(reference_exps):
    method_sets = {
        slice_name: set(scores["experiments"][exp]["results"])
        for slice_name, scores in score_sets.items()
    }
    if len({tuple(sorted(methods)) for methods in method_sets.values()}) != 1:
        raise SystemExit(f"method mismatch for {exp}: {method_sets}")
    required_metrics = set(reference["experiments"][exp]["metrics"])
    for slice_name, scores in score_sets.items():
        for method, values in scores["experiments"][exp]["results"].items():
            missing = sorted(required_metrics - set(values))
            nulls = sorted(key for key in required_metrics if values.get(key) is None)
            if missing or nulls:
                raise SystemExit(
                    f"{slice_name} {exp}/{method}: missing={missing} nulls={nulls}"
                )
    print(f"{exp}: {len(next(iter(method_sets.values())))} methods scored on full/train/test")
PY

python validate.py --compare
