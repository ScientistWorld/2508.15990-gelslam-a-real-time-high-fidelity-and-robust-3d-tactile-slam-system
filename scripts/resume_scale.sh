#!/bin/bash
# Finish the same combined audit after scheduler preemption, preserving raw
# inference and completed phases. The scientific protocol is unchanged.
set -euo pipefail
cd /home/user
export PYTHONPATH=/home/user
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export OPENCV_FOR_THREADS_NUM=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1
unset TACTILE_EVAL_CACHE TACTILE_EVAL_SCRATCH
RES=eval/test/hardening_results
fingerprint=$(python - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, 'eval/test')
import harness
print(harness.resume_fingerprint(Path.cwd(), 'test'))
PY
)
PHASES="$RES/scale_phases/$fingerprint"
mkdir -p "$PHASES"
if [ ! -f "$PHASES/contracts" ]; then
    python eval/test/check_contracts.py
    touch "$PHASES/contracts"
fi
if [ ! -f "$PHASES/cohort" ]; then
    rm -rf checkpoints/*
    python - <<'PY'
import json
from pathlib import Path
variants=['hybrid_dense_loops','nf_kf','only_nf_exhaustive','exhaustive_two_stage']
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
    python eval/test/resume_previous_audit.py --namespace cohort
    python eval/test/evaluate_test.py --output "$RES/after_cohort_test.json" --audit-dir eval/test/audit_raw/cohort --resume-dir eval/test/resume/cohort
    python - <<'PY'
import json
from pathlib import Path
s=json.loads(Path('eval/test/hardening_results/after_cohort_test.json').read_text())
assert len(s['_metadata']['episodes'])==384
assert s['_diagnostics']['gelslam_online']['status']=='scored'
assert s['_diagnostics']['normalflow']['status']=='scored'
assert all(d['status'] in ('scored','failed') for d in s['_diagnostics'].values())
expected=set(s['_metadata']['methods_discovered'])|{'normalflow'}
assert all(set(e['results'])==expected for e in s['experiments'].values())
PY
    touch "$PHASES/cohort"
fi
# Restore only the reference registration, with the same bytes used by the
# prior independent run. Clearing all variants keeps official files clean.
rm -rf checkpoints/*
mkdir -p checkpoints/gelslam_online
cat > checkpoints/gelslam_online/predict.json <<'JSON'
{
  "name": "gelslam_online",
  "command": ["python", "-m", "method.gelslam_sim.run", "--input", "{input}", "--output", "{output}"]
}
JSON
if [ ! -f "$PHASES/train" ]; then
    bash scripts/method.sh --resume-dir eval/train/resume/reference
    bash scripts/evaluate_train.sh --resume-dir eval/train/resume/reference
    cp scoring/scores_train.json eval/train/hardening_results/after_reference_train.json
    touch "$PHASES/train"
fi
if [ ! -f "$PHASES/reference" ]; then
    python eval/test/resume_previous_audit.py --namespace reference
    bash scripts/evaluate_test.sh --resume-dir eval/test/resume/reference
    cp scoring/scores_test.json "$RES/after_reference_test.json"
    touch "$PHASES/reference"
fi
python - <<'PY'
import importlib.metadata, json
from pathlib import Path
Path('eval/test/hardening_results/package_versions.json').write_text(json.dumps({
    p:importlib.metadata.version(p) for p in ['numpy','scipy','opencv-python-headless']},indent=2)+'\n')
PY
python redteam/hardening/summarize_review.py
python validate.py
