"""Light integrity checks; executed with the full scientific audit in its CPU job."""
import json
import os
from pathlib import Path
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import harness
import hidden_world
from runner import run_isolated

ROOT = HERE.parents[1]


def main():
    scratch = HERE / 'scratch'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as td:
        work = Path(td)
        inp = work / 'input.npz'; inp.touch()
        def invoke(code, budget=5):
            out = work / str(len(list(work.iterdir())))
            out.mkdir()
            return run_isolated([sys.executable, '-c', code], inp, out, ROOT, work/'log.txt', budget)
        # A suspended/scheduled-out process consumes no budget; no elapsed deadline exists.
        result = invoke('import time; time.sleep(2)', 1)
        assert result['seconds'] >= 2 and result['cpu_seconds'] < 1
        # Real CPU search, including a privately spawned child, is counted.
        try:
            invoke('import subprocess,sys; subprocess.run([sys.executable,"-c",'
                   '"import signal; signal.signal(signal.SIGXCPU,signal.SIG_IGN)\\nwhile True: pass"])', 1)
            raise AssertionError('private child CPU search escaped budget')
        except RuntimeError as exc:
            assert 'CPU budget exceeded' in str(exc)
        code = '''from pathlib import Path
for name in ["eval/test/evaluate_test.py", "eval/test/hidden_world.py", ".git/HEAD"]:
    try:
        Path(name).read_bytes()
    except PermissionError:
        continue
    raise AssertionError("private file readable: " + name)
try:
    Path("scoring/scores_test.json").write_text("{}")
except PermissionError:
    pass
else:
    raise AssertionError("scoring writable")
import importlib
importlib.import_module("method.gelslam_sim.run")
'''
        invoke(code)
        out = work / 'poses'; out.mkdir()
        poses = np.tile(np.eye(4), (3,1,1))
        for bad in [np.zeros((0,4,4)), poses*np.nan, poses.copy()]:
            if np.isfinite(bad).all() and bad.shape == poses.shape:
                bad[2,0,3] = 1e6
            np.save(out/'poses.npy', bad)
            try:
                harness.load_poses(out, 3)
                raise AssertionError('invalid pose accepted')
            except harness.MethodFailure:
                pass
        relation = {'i':0,'j':2,'T_ij':np.eye(4).tolist()}
        (out/'loops.json').write_text(json.dumps({'loops':[relation]*1000}))
        try:
            harness.score_loops(out, poses)
            raise AssertionError('duplicate loop spam accepted')
        except harness.MethodFailure:
            pass
        relation['T_ij'][0][0] = float('nan')
        (out/'loops.json').write_text(json.dumps({'loops':[relation]}))
        try:
            harness.score_loops(out, poses)
            raise AssertionError('non-finite loop accepted')
        except harness.MethodFailure:
            pass
        episodes=[dict(name='a',contact_loss=False),dict(name='b',contact_loss=True)]
        failure=harness.worst_results(episodes)
        assert set(failure)==set(harness.EXPERIMENTS)
        assert all(set(m)==set(harness.METRICS) and m==harness.WORST for m in failure.values())
        # The old untrusted scalar cache has no read path.
        assert not hasattr(harness,'_cache_load')

        # Recovery must avoid rerunning a completed command while recomputing
        # every metric from raw predictions against the current private truth.
        fixture = work / "recovery_fixture"
        registration = fixture / "checkpoints" / "candidate"
        registration.mkdir(parents=True)
        (registration / "predict.json").write_text(json.dumps({"command": ["dummy", "{input}", "{output}"]}))
        truth = np.tile(np.eye(4), (3, 1, 1))
        calls = []
        renders = []
        writes = []
        def render(ep):
            renders.append(ep["name"])
            return {"poses_mm": truth, "gradients": None, "heights": None,
                    "contact_masks": None, "mm_per_pixel": 1.0}
        def save_observations(data, path):
            writes.append(path.name)
            path.touch()
        def command(method, inp, out, root, log):
            calls.append(method["name"])
            np.save(out / "poses.npy", np.tile(np.eye(4), (3, 1, 1)))
            return {"seconds": 0.0, "cpu_seconds": 0.0}
        original = harness.run_command
        harness.run_command = command
        truth_calls = []
        def render_truth(ep):
            truth_calls.append(ep["name"])
            return truth.copy()
        def recovery(cache=False):
            return harness.evaluate("test", [{"name": "tiny", "frames": 3, "contact_loss": False}],
                render, save_observations, lambda *args: np.tile(np.eye(4), (3, 1, 1)),
                fixture / "scores.json", fixture, resume_dir=fixture / "eval/test/resume/unit",
                render_ground_truth=render_truth, cache_ground_truth=cache)
        try:
            first = recovery()
            truth[1:, 0, 3] = 0.3
            second = recovery()
            assert calls == ["candidate"], "completed raw prediction was executed twice"
            assert len(renders) == len(writes) == 1, "recovery regenerated observations"
            exp = "long_horizon_tracking"
            assert first["results"]["candidate"][exp]["translation_mae_mm"] == 0.0
            assert second["results"]["candidate"][exp]["translation_mae_mm"] > 0.0, "cached scalar trusted"
            source = fixture / "method"
            source.mkdir()
            (source / "algorithm.py").write_text("changed = True\n")
            recovery()
            assert calls == ["candidate", "candidate"], "changed source restored stale predictions"
            assert len(renders) == len(writes) == 2
            fourth = recovery(cache=True)
            count = len(truth_calls)
            fifth = recovery(cache=True)
            assert len(truth_calls) == count, "private truth checkpoint was not reused"
            assert fourth["results"] == fifth["results"]
            assert calls == ["candidate", "candidate"]
        finally:
            harness.run_command = original
    # Exact equivalence, including the contact-loss jump and every texture.
    # This runs only in the submitted CPU job, never on the login node.
    for family_index, family in enumerate(hidden_world.FAMILIES):
        for contact_loss, frames in [(False, 16), (True, 126)]:
            seed = 100003 + family_index
            full = hidden_world.render_episode(family, seed, frames, contact_loss)["poses_mm"]
            truth_only = hidden_world.render_ground_truth(family, seed, frames, contact_loss)
            assert np.array_equal(full, truth_only), f"ground-truth fast path changed {family}/{contact_loss}"
    print('Evaluation integrity contracts passed; truth-only poses exactly match full rendering', flush=True)


if __name__ == '__main__':
    main()
