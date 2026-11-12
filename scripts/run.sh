#!/bin/bash
# Rescoring job after the false-loop metric change (evaluator-only change).
# Every variant/shortcut (method, episode) result is cached in tmp/eval_cache
# from the audit job, so the audit passes re-aggregate without rerunning any
# method. The reference is rerun from the final code through
# scripts/reproduce.sh (the eval-owned baseline is reused from the cache).
#
# To reproduce only the reference from scratch: bash scripts/reproduce.sh
set -e
cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
RES=redteam/hardening/results
mkdir -p "$RES" tmp
git checkout -- data/tactile_sim.py baseline/normalflow_baseline.py
export TACTILE_EVAL_CACHE=/home/user/tmp/eval_cache

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

echo "=== [1] reference: scripts/reproduce.sh ($(date))"
rm -rf checkpoints/*
timeout -k 60 5400 bash scripts/reproduce.sh
cp scoring/scores_test.json "$RES/final_scores_test.json"
cp scoring/scores_train.json "$RES/final_scores_train.json"
cp scoring/scores.json "$RES/final_scores.json"

echo "=== [2] re-aggregate audit passes from the cache ($(date))"
rm -rf checkpoints/*
for v in reference_seed1 nf_kf only_sift loop_ccs_070 session_chain session_chain_dense hybrid_local_loops exhaustive_two_stage only_nf_exhaustive; do
  register "$v" redteam.hardening.variants --variant "$v"
done
timeout -k 60 3600 python eval/test/evaluate_test.py --output "$RES/variants_test.json"
rm -rf checkpoints/*
for v in nf_kf session_chain_dense hybrid_local_loops exhaustive_two_stage only_nf_exhaustive; do
  register "$v" redteam.hardening.variants --variant "$v"
done
timeout -k 60 3600 python eval/train/evaluate_train.py --output "$RES/variants_train.json"
rm -rf checkpoints/*
for k in labels_copy generator_replay gt_replacement duplicate_loops self_derived_loops nan_loops forged_scores baseline_replacement constant empty_predictions nan_predictions impossible_translation read_hidden_test; do
  register "sc_$k" redteam.hardening.shortcuts --kind "$k"
done
mkdir -p checkpoints/sc_orphan_artifacts
python -c "import numpy as np; np.save('checkpoints/sc_orphan_artifacts/pred_poses.npy', np.zeros((400, 6)))"
mkdir -p checkpoints/sc_invalid_spec
echo '{"name": "sc_invalid_spec", "command": ["python", "-c", "pass"]}' > checkpoints/sc_invalid_spec/predict.json
timeout -k 60 3600 python eval/test/evaluate_test.py --output "$RES/shortcuts_test.json"
git checkout -- data/tactile_sim.py baseline/normalflow_baseline.py

echo "=== [3] reference-only final state and summaries ($(date))"
rm -rf checkpoints/*
mkdir -p checkpoints/gelslam_online
cat > checkpoints/gelslam_online/predict.json <<'JSON'
{
  "name": "gelslam_online",
  "command": ["python", "-m", "method.gelslam_sim.run", "--input", "{input}", "--output", "{output}"]
}
JSON
cp "$RES/final_scores_test.json" scoring/scores_test.json
cp "$RES/final_scores_train.json" scoring/scores_train.json
cp "$RES/final_scores.json" scoring/scores.json
python redteam/hardening/rank.py "$RES/rank_test" "$RES/final_scores_test.json" "$RES/variants_test.json" "$RES/shortcuts_test.json"
python redteam/hardening/rank.py "$RES/rank_test_genuine" "$RES/final_scores_test.json" "$RES/variants_test.json"
python redteam/hardening/rank.py "$RES/rank_train" "$RES/final_scores_train.json" "$RES/variants_train.json"
python validate.py
echo "=== done ($(date))"
