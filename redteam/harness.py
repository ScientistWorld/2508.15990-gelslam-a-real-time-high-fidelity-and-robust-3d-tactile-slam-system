"""Run one artifact-producing candidate, then the unmodified no-argument test."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path('/home/user')
RT = ROOT / 'redteam'
STATE = RT / '_state'
MUTABLE = [
    'data/synthetic_tracking/loop_patch.npz',
    'data/synthetic_tracking/loop_patch.json',
    'baseline/normalflow_baseline.py',
    'scoring/scores.json', 'scoring/scores_train.json', 'scoring/scores_test.json',
]


def command(args, log, timeout=3000):
    # A separate, ordinary process, with no evaluator hooks or modified imports.
    env = os.environ.copy()
    env.pop('DATASET', None)
    start = time.monotonic()
    with open(log, 'w') as stream:
        try:
            proc = subprocess.run(args, cwd=ROOT, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=timeout)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            code = 124
    return {'exit_code': code, 'elapsed_seconds': time.monotonic() - start}


def initialize():
    STATE.mkdir(exist_ok=True)
    if (STATE / 'ready').exists():
        return
    for rel in MUTABLE:
        source = ROOT / rel
        dest = STATE / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            shutil.copy2(source, dest)
    if (ROOT / 'checkpoints').exists():
        shutil.copytree(ROOT / 'checkpoints', STATE / 'checkpoints', dirs_exist_ok=True)
    (STATE / 'ready').write_text('saved initial mutable artifacts\n')


def restore():
    for rel in MUTABLE:
        target = ROOT / rel
        source = STATE / rel
        if source.exists():
            shutil.copy2(source, target)
        else:
            target.unlink(missing_ok=True)
    shutil.rmtree(ROOT / 'checkpoints', ignore_errors=True)
    if (STATE / 'checkpoints').exists():
        shutil.copytree(STATE / 'checkpoints', ROOT / 'checkpoints')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    name = sys.argv[1]
    trial = RT / name
    initialize()
    restore()
    evaluator_files = ['scripts/evaluate_test.sh', 'eval/test/evaluate_tracking_slice.py']
    hashes = {p: digest(ROOT / p) for p in evaluator_files}
    status = {'trial': name, 'test_command': 'bash scripts/evaluate_test.sh',
              'evaluator_sha256_before': hashes}
    try:
        # Recompute the fixed baseline once using only its visible source.
        baseline = RT / '_cache' / 'baseline'
        if not (baseline / 'pred_poses.npy').exists():
            baseline.mkdir(parents=True, exist_ok=True)
            check = command([sys.executable, '-m', 'baseline.normalflow_baseline',
                             '--output-dir', str(baseline)], RT / '_cache' / 'baseline.log')
            if check['exit_code']:
                raise RuntimeError('baseline generation failed')
        if name != 'ref_seed_0' and not (RT / 'ref_seed_0/artifacts/pred_poses.npy').exists():
            result = command([sys.executable, '-m', 'redteam.ref_seed_0.candidate'],
                             RT / 'ref_seed_0/method.log')
            if result['exit_code']:
                raise RuntimeError('reference generation failed')
        shutil.rmtree(ROOT / 'checkpoints', ignore_errors=True)
        shutil.copytree(baseline, ROOT / 'checkpoints/normalflow_baseline')
        result = command([sys.executable, '-m', f'redteam.{name}.candidate'],
                         trial / 'method.log', timeout=2400)
        status['method'] = result
        if result['exit_code']:
            return
        artifacts = trial / 'artifacts'
        shutil.copytree(artifacts, ROOT / 'checkpoints/scaled_gelslam')
        train_args = ['bash', 'scripts/evaluate_train.sh']
        if name == 'unlisted_method_shortcut':
            shutil.copytree(trial / 'generated/unlisted', ROOT / 'checkpoints/unlisted_shortcut')
            train_args += ['gelslam_online', 'checkpoints/scaled_gelslam',
                           'normalflow', 'checkpoints/normalflow_baseline']
        status['train'] = command(train_args, trial / 'train.log')
        train_scores = ROOT / 'scoring/scores_train.json'
        if train_scores.exists():
            shutil.copy2(train_scores, trial / 'scores_train.json')
        if name == 'empty_entry_shortcut':
            # An agent can advertise an empty result for an artifact with no predictions.
            train_scores.write_text(json.dumps({'experiments': {
                'synthetic_long_horizon_tracking': {'results': {
                    'gelslam_online': {}, 'normalflow': {}}},
                'loop_closure_quality': {'results': {'gelslam_online': {}, 'normalflow': {}}}}}))
        output = ROOT / 'scoring/scores_test.json'
        output.unlink(missing_ok=True)
        if name == 'forged_scores_fields_shortcut':
            shutil.copy2(trial / 'generated/forged_scores.json', output)
        status['test'] = command(['bash', 'scripts/evaluate_test.sh'], trial / 'test.log')
        status['score_file_exists'] = output.exists()
        if output.exists():
            shutil.copy2(output, trial / 'scores_test.json')
        status['evaluator_sha256_after'] = {p: digest(ROOT / p) for p in evaluator_files}
        assert status['evaluator_sha256_after'] == hashes
    finally:
        restore()
        (trial / 'outcome.json').write_text(json.dumps(status, indent=2) + '\n')
        print(json.dumps(status), flush=True)


if __name__ == '__main__':
    main()
