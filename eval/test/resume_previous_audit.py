"""Reuse private raw outputs across reviewed audit-only recovery changes.

The two source snapshots preserve the exact completed 96-input audit and the
partially completed 384-input audit. A manifest locks every changed file to
its reviewed current bytes; inference, baseline, full renderer, input settings
and metric calculations retain their scientific behavior. The combined job
checks full-render/truth-only equivalence before importing any raw outputs.
Normal evaluation never invokes this utility or reads its manifest.
"""
import argparse
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

import cv2
import harness

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / 'eval/test/hardening_results'
RECOVERY_FILES = {
    'eval/test/evaluate_test.py', 'eval/test/harness.py',
    'eval/test/hidden_world.py', 'eval/test/check_contracts.py',
    'eval/test/resume_previous_audit.py',
}


def episode_list(source):
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'HELDOUT_EPISODES' for t in n.targets))
    return ast.literal_eval(node.value)



def function_ast(source, name):
    return ast.dump(next(n for n in ast.parse(source).body
                         if isinstance(n, ast.FunctionDef) and n.name == name))


def assert_scientific_equivalence(old):
    # All original rendering steps remain byte-for-byte the same in the AST.
    current = ast.parse((ROOT / 'eval/test/hidden_world.py').read_text())
    current.body = [n for n in current.body if not
                    (isinstance(n, ast.FunctionDef) and n.name == 'render_ground_truth')]
    assert ast.dump(current) == ast.dump(ast.parse(old['eval/test/hidden_world.py']))
    # Recovery scheduling and I/O changed; mathematical scoring did not.
    source = (ROOT / 'eval/test/harness.py').read_text()
    for name in ['rigid_inverse', '_is_rigid', 'load_poses', '_euler_axes_deg',
                 'pose_errors', '_as_index', 'score_loops', 'aggregate', 'worst_results']:
        assert function_ast(source, name) == function_ast(old['eval/test/harness.py'], name), name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--namespace', choices=['cohort', 'reference'], required=True)
    args = parser.parse_args()
    runtime = json.loads((RES / 'runtime.json').read_text())
    assert platform.python_version() == runtime['python']
    assert cv2.__version__ == runtime['opencv']
    for package in ('numpy', 'scipy'):
        assert importlib.metadata.version(package) == runtime[package]
    manifest = json.loads((RES / 'resume_migrations.json').read_text())
    episodes_now = episode_list((ROOT / 'eval/test/evaluate_test.py').read_text())
    new_key = harness.resume_fingerprint(ROOT, 'test')
    namespace = ROOT / 'eval/test/resume' / args.namespace
    methods = [None] + harness.discover_methods(ROOT / 'checkpoints')
    count = 0
    for snapshot, expected_hashes in manifest.items():
        old = json.loads((RES / snapshot).read_text())
        assert set(old) == set(expected_hashes), 'incomplete source provenance'
        for name, source in old.items():
            current = (ROOT / name).read_bytes()
            assert hashlib.sha256(current).hexdigest() == expected_hashes[name], f'unreviewed edit: {name}'
            if name not in RECOVERY_FILES:
                assert current == source.encode(), f'inference/scientific source changed: {name}'
        assert_scientific_equivalence(old)
        episodes = episode_list(old['eval/test/evaluate_test.py'])
        assert episodes == episodes_now[:len(episodes)], 'previous episode inputs changed'
        digest = hashlib.sha256()
        for package in ('numpy', 'scipy', 'opencv-python-headless'):
            digest.update((package + importlib.metadata.version(package)).encode())
        digest.update(sys.version.encode())
        for name, source in sorted(old.items()):
            digest.update(name.encode())
            digest.update(source.encode())
        old_key = digest.hexdigest()
        for episode in episodes:
            for method in methods:
                if method is not None and method['error'] is not None:
                    continue
                source = harness.resume_location(namespace, old_key, method, episode)
                target = harness.resume_location(namespace, new_key, method, episode)
                if source.is_dir() and not target.exists():
                    poses = harness.load_poses(source, episode['frames'])
                    timing = json.loads((source / 'execution.json').read_text())
                    harness.save_resume_raw(target, poses, timing, source)
                    count += 1
    print(f'[audit] transferred {count} raw checkpoints; all metrics will be recomputed', flush=True)


if __name__ == '__main__':
    main()
