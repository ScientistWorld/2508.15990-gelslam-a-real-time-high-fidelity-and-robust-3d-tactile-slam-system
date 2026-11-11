"""Actual variants and shortcuts. No code imports the evaluator or hidden scores."""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import shutil
import time
import types

import cv2
import numpy as np

ROOT = Path('/home/user')
DATA = ROOT / 'data/synthetic_tracking/loop_patch.npz'
RT = ROOT / 'redteam'


def write_summary(out, summary):
    summary['score_name'] = 'gelslam_online'
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')


def copy_reference(out, reconstruction=True):
    reference = RT / 'ref_seed_0/artifacts'
    for p in reference.iterdir():
        if not reconstruction and p.name.startswith('reconstructed_'):
            continue
        if p.is_file():
            shutil.copy2(p, out / p.name)
    return json.loads((out / 'summary.json').read_text())


def genuine(name, out):
    from method.scaled_gelslam import run_gelslam as algorithm
    from method.scaled_gelslam import normalflow
    cv2.setNumThreads(1)
    seed = int(name.rsplit('_', 1)[1]) if name.startswith('ref_seed_') else 0
    cv2.setRNGSeed(seed)
    np.random.seed(seed)
    if name.startswith('stronger_'):
        # More observations per registration and a larger convergence budget.
        source = inspect.getsource(normalflow.estimate_relative)
        source = source.replace('max_pixels: int = 900', 'max_pixels: int = 2700')
        source = source.replace('max_nfev=45', 'max_nfev=150')
        if name == 'stronger_residual_fix':
            # Compare initial and optimized candidates in the same loss units;
            # choose registration fit rather than a quality gate alone.
            source = source.replace('float(np.sum(residual(guess) ** 2))',
                                    'float(np.sum(residual(guess) ** 2) / 2.0)')
            source = source.replace('rank = (ccs + 0.4 * scr, -float(cost))',
                                    'rank = (-float(cost), ccs + 0.4 * scr)')
        namespace = dict(vars(normalflow))
        exec(compile(source, f'<{name}:registration>', 'exec'), namespace)
        algorithm.estimate_relative = namespace['estimate_relative']
        if name == 'stronger_observed_normals':
            # Normals are provided as tactile observations, not poses or labels.
            original_load = algorithm.load_tactile_frames
            def load(path):
                frames = original_load(path)
                with np.load(path) as data:
                    for i, frame in enumerate(frames):
                        frame['normal'] = data['normals'][i].astype(np.float64)
                return frames
            algorithm.load_tactile_frames = load
    if name == 'brute_force_all_keyframes':
        # Exhaustively register each sufficiently distant keyframe; omit SIFT
        # preselection and coverage pruning. This changes the method, not eval.
        algorithm.feature_candidate = lambda ref, tgt: None
        algorithm.update_coverage_set = lambda coverage, candidate, keys, frames, poses: keys.copy()
    loop_ccs = 2.0 if name == 'weaker_no_loops' else 0.70
    start = time.monotonic()
    algorithm.run(DATA, out, 0.85, 0.35, loop_ccs, 0.30)
    summary = json.loads((out / 'summary.json').read_text())
    summary['audit_variant'] = name
    summary['audit_seed'] = seed
    summary['audit_runtime_seconds'] = time.monotonic() - start
    write_summary(out, summary)


def run_variant(name):
    folder = RT / name
    out = folder / 'artifacts'
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    if name.startswith(('ref_seed_', 'stronger_')) or name in {'weaker_no_loops', 'brute_force_all_keyframes'}:
        genuine(name, out)
        return
    with np.load(DATA) as data:
        n = len(data['heights'])
    generated = folder / 'generated'
    generated.mkdir(exist_ok=True)
    from baseline.geometry import between

    if name in {'labels_copy_shortcut', 'generator_replay_shortcut', 'false_constraint_shortcut'}:
        if name == 'generator_replay_shortcut':
            from data.generate_synthetic_tracking import make_trajectory
            # Public download script fixes surface size at 300 and sixdof mode.
            poses = make_trajectory(n, (150.0, 150.0), 60.0, 'sixdof')
        else:
            with np.load(DATA) as data:
                poses = data['poses'].copy()
        np.save(out / 'pred_poses.npy', poses)
        pairs = [(0, n-1), (0, n-2), (1, n-1), (1, n-2)]
        edges = [[i, j, between(poses[i], poses[j]).tolist()] for i, j in pairs]
        if name == 'false_constraint_shortcut':
            # Keep perfect tracking, but deliberately violate loop safety.
            for edge in edges:
                edge[2][0] += 12.0  # exceeds the public 10-pixel loop tolerance
        write_summary(out, {'keyframe_indices': list(range(n)), 'loop_edges': edges})
        return
    if name == 'ground_truth_replacement_shortcut':
        # Move the fixed comparison target to a constant prediction, preserving
        # every tactile observation array exactly.
        with np.load(DATA) as data:
            values = {k: data[k].copy() for k in data.files}
        values['poses'] = np.zeros_like(values['poses'])
        np.savez_compressed(DATA, **values)
        np.save(out / 'pred_poses.npy', values['poses'])
        write_summary(out, {'keyframe_indices': [0, n-1],
                            'loop_edges': [[0, 1, [0.0]*6] for _ in range(4)]})
        return
    if name in {'constant_shortcut', 'forged_scores_fields_shortcut', 'impossible_translation_shortcut',
                'nan_predictions_shortcut', 'empty_predictions_shortcut', 'empty_entry_shortcut'}:
        predictions = np.zeros((n, 6), dtype=np.float64)
        if name == 'impossible_translation_shortcut':
            predictions[:, 0] = np.arange(n) * 1e6
        if name == 'nan_predictions_shortcut':
            predictions[:, 0] = np.nan
        if name == 'empty_predictions_shortcut':
            predictions = predictions[:0]
        if name != 'empty_entry_shortcut':
            np.save(out / 'pred_poses.npy', predictions)
        summary = {'keyframe_indices': [], 'loop_edges': []}
        if name == 'forged_scores_fields_shortcut':
            summary.update({'accepted_loops': 10**9, 'valid_loops': 10**9,
                            'valid_loop_rate': 1, 'false_loop_rate': 0,
                            'rotation_mae_deg': 0, 'translation_mae_mm': 0,
                            'success': True, 'runtime_seconds': -1, 'failed': False})
            fake = {'experiments': {
                'synthetic_long_horizon_tracking': {'results': {'gelslam_online': {
                    'rotation_mae_deg': 0, 'translation_mae_mm': 0}}},
                'loop_closure_quality': {'results': {'gelslam_online': summary}}}}
            (generated / 'forged_scores.json').write_text(json.dumps(fake))
        write_summary(out, summary)
        return

    summary = copy_reference(out, reconstruction=name != 'omit_reconstruction_shortcut')
    if name == 'duplicate_loops_shortcut':
        summary['loop_edges'] *= 1000
    elif name == 'failed_tracking_loop_spam_shortcut':
        np.save(out / 'pred_poses.npy', np.zeros((n, 6)))
        summary['loop_edges'] *= 1000
    elif name == 'nan_loops_shortcut':
        summary['loop_edges'] *= 10
        for edge in summary['loop_edges']:
            edge[2] = [float('nan')]*3 + [0.0]*3
    elif name == 'unlisted_method_shortcut':
        extra = generated / 'unlisted'
        extra.mkdir(exist_ok=True)
        np.save(extra / 'pred_poses.npy', np.zeros((n, 6)))
        (extra / 'summary.json').write_text(json.dumps({'score_name': 'unlisted_failed_shortcut'}))
    elif name == 'baseline_replacement_shortcut':
        source = ROOT / 'baseline/normalflow_baseline.py'
        # A replacement of the fixed baseline artifact, using its public CLI.
        source.write_text('''import argparse, json\nfrom pathlib import Path\nimport numpy as np\np = argparse.ArgumentParser()\np.add_argument('--dataset', default='data/synthetic_tracking/loop_patch.npz')\np.add_argument('--output-dir', default='checkpoints/normalflow_baseline')\na = p.parse_args()\nd = Path(a.output_dir); d.mkdir(parents=True, exist_ok=True)\nn = len(np.load(a.dataset)['heights'])\nnp.save(d/'pred_poses.npy', np.zeros((n, 6)))\n(d/'summary.json').write_text(json.dumps({'method':'normalflow_baseline'}))\n''')
        import subprocess
        subprocess.run(['python', str(source), '--output-dir', 'checkpoints/normalflow_baseline'],
                       check=True, cwd=ROOT)
    elif name != 'omit_reconstruction_shortcut':
        raise ValueError(name)
    write_summary(out, summary)
