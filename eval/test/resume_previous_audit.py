"""One-time raw-output reuse when extending the already completed paired audit.

Only the hidden episode list changed. Verify all previous inference, renderer,
baseline, runner and scoring source bytes before moving their raw checkpoints
to the new fingerprint. Normal evaluation never calls this audit utility.
"""
import argparse
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

import evaluate_test
import harness

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / 'eval/test/hardening_results'


def episode_list(source):
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'HELDOUT_EPISODES' for t in n.targets))
    episodes = ast.literal_eval(node.value)
    node.value = ast.Constant(None)
    return episodes, ast.dump(tree)


def without_fingerprint_walk(source):
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'resume_fingerprint')
    node.body = [ast.Pass()]
    return ast.dump(tree)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--namespace', choices=['cohort', 'reference'], required=True)
    args = parser.parse_args()
    old = json.loads((RES / 'resume_sources_before_scale.json').read_text())
    runtime = json.loads((RES / 'runtime.json').read_text())
    assert platform.python_version() == runtime['python']
    for package, key in [('numpy', 'numpy'), ('scipy', 'scipy')]:
        assert importlib.metadata.version(package) == runtime[key]
    episodes, old_driver = episode_list(old['eval/test/evaluate_test.py'])
    new_episodes, new_driver = episode_list((ROOT / 'eval/test/evaluate_test.py').read_text())
    assert old_driver == new_driver, 'test driver changed beyond its episode list'
    assert episodes == new_episodes[:len(episodes)], 'old episode inputs changed'
    for name, source in old.items():
        if name == 'eval/test/harness.py':
            assert without_fingerprint_walk(source) == without_fingerprint_walk((ROOT / name).read_text())
        elif name != 'eval/test/evaluate_test.py':
            assert (ROOT / name).read_text() == source, f'inference/scoring source changed: {name}'
    # Reconstruct the exact old source/runtime key; all inputs to the old key
    # were preserved inside this private audit directory, never by the method.
    digest = hashlib.sha256()
    for package in ('numpy', 'scipy', 'opencv-python-headless'):
        digest.update((package + importlib.metadata.version(package)).encode())
    digest.update(sys.version.encode())
    for name, source in sorted(old.items()):
        digest.update(name.encode()); digest.update(source.encode())
    old_key = digest.hexdigest()
    new_key = harness.resume_fingerprint(ROOT, 'test')
    namespace = ROOT / 'eval/test/resume' / args.namespace
    methods = [None] + harness.discover_methods(ROOT / 'checkpoints')
    count = 0
    for episode in episodes:
        for method in methods:
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
