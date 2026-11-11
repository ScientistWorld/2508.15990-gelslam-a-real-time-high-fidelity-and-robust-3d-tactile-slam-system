#!/bin/bash
set -euo pipefail
cd /home/user
for trial in \
  ref_seed_0 ref_seed_1 ref_seed_2 \
  stronger_more_compute stronger_observed_normals stronger_residual_fix weaker_no_loops \
  brute_force_all_keyframes \
  labels_copy_shortcut generator_replay_shortcut duplicate_loops_shortcut \
  ground_truth_replacement_shortcut baseline_replacement_shortcut \
  omit_reconstruction_shortcut forged_scores_fields_shortcut \
  unlisted_method_shortcut empty_predictions_shortcut empty_entry_shortcut \
  constant_shortcut impossible_translation_shortcut nan_predictions_shortcut \
  nan_loops_shortcut failed_tracking_loop_spam_shortcut false_constraint_shortcut
do
  if [ -f "redteam/$trial/outcome.json" ]; then
    echo "[audit] preserved completed trial $trial"
    continue
  fi
  echo "[audit] $trial"
  bash "redteam/$trial/run.sh"
done
python redteam/summarize.py
