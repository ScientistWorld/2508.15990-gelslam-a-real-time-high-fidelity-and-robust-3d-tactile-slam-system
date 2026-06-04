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

train = json.loads(Path("scoring/scores_train.json").read_text())
test = json.loads(Path("scoring/scores_test.json").read_text())
reference = json.loads(Path("scoring/reference.json").read_text())

train_exps = set(train["experiments"])
test_exps = set(test["experiments"])
if train_exps != test_exps:
    raise SystemExit(f"experiment mismatch: train={sorted(train_exps)} test={sorted(test_exps)}")
reference_exps = set(reference["experiments"])
if train_exps != reference_exps:
    raise SystemExit(f"reference experiment mismatch: scores={sorted(train_exps)} reference={sorted(reference_exps)}")

for exp in sorted(train_exps):
    train_methods = set(train["experiments"][exp]["results"])
    test_methods = set(test["experiments"][exp]["results"])
    if train_methods != test_methods:
        raise SystemExit(
            f"method mismatch for {exp}: train={sorted(train_methods)} test={sorted(test_methods)}"
        )
    required_metrics = set(reference["experiments"][exp]["metrics"])
    for slice_name, scores in [("train", train), ("test", test)]:
        for method, values in scores["experiments"][exp]["results"].items():
            missing = sorted(required_metrics - set(values))
            nulls = sorted(key for key in required_metrics if values.get(key) is None)
            if missing or nulls:
                raise SystemExit(
                    f"{slice_name} {exp}/{method}: missing={missing} nulls={nulls}"
                )
    print(f"{exp}: {len(train_methods)} methods scored on train and test")
PY
