#!/bin/bash
# One serialized job: final protocol, paired variants/shortcuts, then reference alone.
set -euo pipefail
cd /home/user
export PYTHONPATH=/home/user
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export OPENCV_FOR_THREADS_NUM=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1
unset TACTILE_EVAL_CACHE TACTILE_EVAL_SCRATCH
RES=eval/test/hardening_results
mkdir -p "$RES" tmp
python - <<'PY'
import json, platform
from pathlib import Path
import numpy, scipy, cv2
Path('eval/test/hardening_results/runtime.json').write_text(json.dumps({
    'python':platform.python_version(), 'numpy':numpy.__version__,
    'scipy':scipy.__version__, 'opencv':cv2.__version__,
    'numerical_threads':1, 'cpu_affinity_cores':1, 'episode_cpu_budget_seconds':7200,
},indent=2)+'\n')
PY
python eval/test/check_contracts.py
# Remove just generated checkpoint registrations; they are never source files.
rm -rf checkpoints/*
bash scripts/download.sh
python - <<'PY'
import json
from pathlib import Path
variants=['reference_seed1','session_chain_dense','hybrid_local_loops','hybrid_dense_loops',
          'nf_kf','only_nf_exhaustive','exhaustive_two_stage']
shortcuts=['labels_copy','generator_replay','gt_replacement','duplicate_loops','nan_loops',
           'forged_scores','baseline_replacement','constant','empty_predictions','nan_predictions',
           'impossible_translation','read_hidden_test','metric_cache_forgery','false_constraint']
for name,module,extra in [('gelslam_online','method.gelslam_sim.run',[])]+[
        (v,'redteam.hardening.variants',['--variant',v]) for v in variants]+[
        ('sc_'+v,'redteam.hardening.shortcuts',['--kind',v]) for v in shortcuts]:
    path=Path('checkpoints')/name; path.mkdir(parents=True)
    command=['python','-m',module]+extra+['--input','{input}','--output','{output}']
    (path/'predict.json').write_text(json.dumps({'name':name,'command':command}))
p=Path('checkpoints/sc_orphan');p.mkdir();(p/'poses.npy').touch()
p=Path('checkpoints/sc_invalid');p.mkdir();(p/'predict.json').write_text('{}')
PY
# Every candidate sees the exact same rendered observations. Methods run sequentially.
python eval/test/evaluate_test.py --output "$RES/after_cohort_test.json" --audit-dir eval/test/audit_raw/cohort --resume-dir eval/test/resume/cohort
# Training needs only honest variants; unchanged shortcuts need no training replay.
find checkpoints -maxdepth 1 -type d -name 'sc_*' -exec rm -rf {} +
python eval/train/evaluate_train.py --output eval/train/hardening_results/after_cohort_train.json --audit-dir eval/train/audit_raw/cohort --resume-dir eval/train/resume/cohort
# Reference and baseline rerun end to end with no other candidate registered or running.
rm -rf checkpoints/*
bash scripts/method.sh --resume-dir eval/train/resume/reference
# method.sh already writes scores.json on the public episodes. The new train score is
# produced by its official entry point too, never copied from an audit cohort.
bash scripts/evaluate_train.sh --resume-dir eval/train/resume/reference
bash scripts/evaluate_test.sh --resume-dir eval/test/resume/reference
cp scoring/scores_test.json "$RES/after_reference_test.json"
cp scoring/scores_train.json eval/train/hardening_results/after_reference_train.json
python redteam/hardening/summarize_review.py
python validate.py
