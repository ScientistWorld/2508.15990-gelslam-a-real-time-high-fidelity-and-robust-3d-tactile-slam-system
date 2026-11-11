#!/bin/bash
# Hardening job: final reference scores, then the audit cohort (variants,
# brute force, shortcuts) through the hidden test, then rank summaries.
# Reproducing only the reference: bash scripts/reproduce.sh
set -e
cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
RES=redteam/hardening/results
mkdir -p "$RES" tmp
rm -rf checkpoints/* tmp/hardening_cache

register() {  # name, module args...
  local name=$1; shift
  mkdir -p "checkpoints/$name"
  python - "$name" "$@" <<'PY'
import json, sys
name, args = sys.argv[1], sys.argv[2:]
cmd = ["python", "-m"] + args + ["--input", "{input}", "--output", "{output}"]
open(f"checkpoints/{name}/predict.json", "w").write(json.dumps({"name": name, "command": cmd}, indent=2) + "\n")
PY
}

echo "=== [1] final reference: scripts/reproduce.sh ($(date))"
rm -rf tmp/eval_scratch
timeout -k 60 3600 bash scripts/reproduce.sh || echo "reproduce exited non-zero"
cp scoring/scores_test.json "$RES/final_scores_test.json"
cp scoring/scores_train.json "$RES/final_scores_train.json"
cp scoring/scores.json "$RES/final_scores.json"

echo "=== [2] genuine variants and brute force on the hidden test ($(date))"
rm -rf tmp/gelslam_online_parked
mv checkpoints/gelslam_online tmp/gelslam_online_parked
for v in reference_seed1 nf_kf only_sift loop_ccs_070 session_chain session_chain_dense hybrid_local_loops exhaustive_two_stage only_nf_exhaustive; do
  register "$v" redteam.hardening.variants --variant "$v"
done
timeout -k 60 7200 python eval/test/evaluate_test.py --output "$RES/variants_test.json" || echo "variant test pass exited non-zero"

echo "=== [3] genuine variants on the training slice ($(date))"
rm -rf checkpoints/only_sift checkpoints/reference_seed1 checkpoints/loop_ccs_070 checkpoints/session_chain
timeout -k 60 2400 python eval/train/evaluate_train.py --output "$RES/variants_train.json" || echo "variant train pass exited non-zero"
rm -rf checkpoints/*

echo "=== [4] shortcuts on the hidden test ($(date))"
CACHE_TRAIN_EPISODES=1 bash scripts/download.sh
for k in labels_copy generator_replay gt_replacement duplicate_loops self_derived_loops nan_loops forged_scores baseline_replacement constant empty_predictions nan_predictions impossible_translation read_hidden_test; do
  register "sc_$k" redteam.hardening.shortcuts --kind "$k"
done
mkdir -p checkpoints/sc_orphan_artifacts
python -c "import numpy as np; np.save('checkpoints/sc_orphan_artifacts/pred_poses.npy', np.zeros((400, 6)))"
mkdir -p checkpoints/sc_invalid_spec
echo '{"name": "sc_invalid_spec", "command": ["python", "-c", "pass"]}' > checkpoints/sc_invalid_spec/predict.json
timeout -k 60 5400 python eval/test/evaluate_test.py --output "$RES/shortcuts_test.json" || echo "shortcut pass exited non-zero"
git checkout -- data/tactile_sim.py baseline/normalflow_baseline.py
rm -rf checkpoints/* data/downloads/train_episodes

echo "=== [5] restore final state and summarize ($(date))"
mv tmp/gelslam_online_parked checkpoints/gelslam_online
cp "$RES/final_scores_test.json" scoring/scores_test.json
cp "$RES/final_scores_train.json" scoring/scores_train.json
cp "$RES/final_scores.json" scoring/scores.json
rm -rf checkpoints/gelslam_online/train_outputs
python redteam/hardening/rank.py "$RES/rank_test" "$RES/final_scores_test.json" "$RES/variants_test.json" "$RES/shortcuts_test.json"
python redteam/hardening/rank.py "$RES/rank_test_genuine" "$RES/final_scores_test.json" "$RES/variants_test.json"
python redteam/hardening/rank.py "$RES/rank_train" "$RES/final_scores_train.json" "$RES/variants_train.json"
python validate.py || true
echo "=== done ($(date))"
