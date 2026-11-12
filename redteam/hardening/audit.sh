#!/bin/bash
# Hardening audit (run from the workspace root: bash redteam/hardening/audit.sh). Resumable: the audit passes cache every scored
# (method, episode) in tmp/eval_cache (TACTILE_EVAL_CACHE), and finished passes
# are skipped, so a preempted job can simply be resubmitted.
#
# Passes: [A] variants and brute force on the hidden test, [B] shortcuts on the
# hidden test, [C] final reference from the final code (scripts/reproduce.sh,
# no cache), [D] variants on the training slice, [E] rank/paired summaries.
#
# To reproduce only the reference: bash scripts/reproduce.sh
set -e
cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
RES=redteam/hardening/results
mkdir -p "$RES" tmp
git checkout -- data/tactile_sim.py baseline/normalflow_baseline.py

complete() {
  python - "$1" <<'PY'
import json, sys
try:
    diag = json.load(open(sys.argv[1])).get("_diagnostics")
    ok = isinstance(diag, dict) and bool(diag) and all(
        isinstance(v, dict) and v.get("status") in ("scored", "failed") for v in diag.values())
except Exception:
    ok = False
sys.exit(0 if ok else 1)
PY
}

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

export TACTILE_EVAL_CACHE=/home/user/tmp/eval_cache

if ! complete "$RES/variants_test.json"; then
  echo "=== [A] variants and brute force on the hidden test ($(date))"
  rm -rf checkpoints/*
  for v in reference_seed1 nf_kf only_sift loop_ccs_070 session_chain session_chain_dense hybrid_local_loops exhaustive_two_stage only_nf_exhaustive; do
    register "$v" redteam.hardening.variants --variant "$v"
  done
  timeout -k 60 9000 python eval/test/evaluate_test.py --output "$RES/variants_test.json" || echo "variant test pass exited non-zero"
fi

if ! complete "$RES/shortcuts_test.json"; then
  echo "=== [B] shortcuts on the hidden test ($(date))"
  rm -rf checkpoints/*
  CACHE_TRAIN_EPISODES=1 bash scripts/download.sh
  for k in labels_copy generator_replay gt_replacement duplicate_loops self_derived_loops nan_loops forged_scores baseline_replacement constant empty_predictions nan_predictions impossible_translation read_hidden_test; do
    register "sc_$k" redteam.hardening.shortcuts --kind "$k"
  done
  mkdir -p checkpoints/sc_orphan_artifacts
  python -c "import numpy as np; np.save('checkpoints/sc_orphan_artifacts/pred_poses.npy', np.zeros((400, 6)))"
  mkdir -p checkpoints/sc_invalid_spec
  echo '{"name": "sc_invalid_spec", "command": ["python", "-c", "pass"]}' > checkpoints/sc_invalid_spec/predict.json
  timeout -k 60 7200 python eval/test/evaluate_test.py --output "$RES/shortcuts_test.json" || echo "shortcut pass exited non-zero"
  git checkout -- data/tactile_sim.py baseline/normalflow_baseline.py
  rm -rf data/downloads/train_episodes
fi

if [ ! -f "$RES/final_rerun_complete.txt" ]; then
  echo "=== [C] final reference from the final code: scripts/reproduce.sh, no cache ($(date))"
  rm -rf checkpoints/*
  ( unset TACTILE_EVAL_CACHE; timeout -k 60 5400 bash scripts/reproduce.sh ) || echo "reproduce exited non-zero"
  if complete scoring/scores_test.json && complete scoring/scores_train.json && complete scoring/scores.json; then
    cp scoring/scores_test.json "$RES/final_scores_test.json"
    cp scoring/scores_train.json "$RES/final_scores_train.json"
    cp scoring/scores.json "$RES/final_scores.json"
    date > "$RES/final_rerun_complete.txt"
  fi
fi

if ! complete "$RES/variants_train.json"; then
  echo "=== [D] variants on the training slice ($(date))"
  rm -rf tmp/gelslam_online_parked
  [ -d checkpoints/gelslam_online ] && mv checkpoints/gelslam_online tmp/gelslam_online_parked
  rm -rf checkpoints/*
  for v in nf_kf session_chain_dense hybrid_local_loops exhaustive_two_stage only_nf_exhaustive; do
    register "$v" redteam.hardening.variants --variant "$v"
  done
  timeout -k 60 3600 python eval/train/evaluate_train.py --output "$RES/variants_train.json" || echo "variant train pass exited non-zero"
fi

echo "=== [E] restore the reference-only state and summarize ($(date))"
rm -rf checkpoints/*
mkdir -p checkpoints/gelslam_online
cat > checkpoints/gelslam_online/predict.json <<'JSON'
{
  "name": "gelslam_online",
  "command": ["python", "-m", "method.gelslam_sim.run", "--input", "{input}", "--output", "{output}"]
}
JSON
rm -rf tmp/gelslam_online_parked
cp "$RES/final_scores_test.json" scoring/scores_test.json
cp "$RES/final_scores_train.json" scoring/scores_train.json
cp "$RES/final_scores.json" scoring/scores.json
python redteam/hardening/rank.py "$RES/rank_test" "$RES/final_scores_test.json" "$RES/variants_test.json" "$RES/shortcuts_test.json" || true
python redteam/hardening/rank.py "$RES/rank_test_genuine" "$RES/final_scores_test.json" "$RES/variants_test.json" || true
python redteam/hardening/rank.py "$RES/rank_train" "$RES/final_scores_train.json" "$RES/variants_train.json" || true
python validate.py || true
echo "=== done ($(date))"
