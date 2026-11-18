#!/usr/bin/env python3
"""Shortcut attempts replayed through the hardened hidden test.

Same entry-point contract as a method:
    python -m redteam.hardening.shortcuts --kind KIND --input EP.npz --output DIR

Kinds:
  labels_copy          copy any ground-truth pose file visible in the workspace
  generator_replay     identify the episode among the public simulator configs and replay its ground truth
  gt_replacement       rewrite the public simulator so its ground truth is "no motion", predict no motion
  duplicate_loops      reference trajectory, every loop record repeated 100 times
  self_derived_loops   reference trajectory plus loop records derived from that trajectory
  nan_loops            reference trajectory plus 500 loop records with NaN translations
  forged_scores        constant poses, prewritten perfect score files and summary claims
  baseline_replacement replace the public baseline with constant poses, report the reference trajectory
  constant             identity pose for every frame
  empty_predictions    empty pose array
  nan_predictions      NaN translations
  impossible_translation  translations of one million millimetres per frame
  read_hidden_test     (filesystem access attempt) import the hidden evaluator and replay its ground truth
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def _identity(n: int) -> np.ndarray:
    return np.tile(np.eye(4), (n, 1, 1))


def _load(path: Path):
    from method.gelslam_sim.run import load_episode
    return load_episode(path)


def _reference(path: Path):
    """Recompute genuine reference outputs from this input; no trusted cache."""
    from method.gelslam_sim.gelslam import run_gelslam
    gradients, heights, contacts, mmpp = _load(path)
    poses, loops, _ = run_gelslam(gradients, heights, contacts, mmpp)
    return poses, loops



def _write(out: Path, poses: np.ndarray, loops: list | None = None, extra: dict | None = None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "poses.npy", poses)
    (out / "loops.json").write_text(json.dumps({"loops": loops or []}))
    if extra:
        (out / "summary.json").write_text(json.dumps(extra))


def _match_first_frame(gradients: np.ndarray, configs: list[dict], sim) -> dict | None:
    """Return the config whose rendered first frame equals the input's first frame."""
    for cfg in configs:
        obj = sim.TactileObject(cfg["family"], int(cfg["seed"]))
        kept = sim.kept_frame_indices(int(cfg["frames"]), bool(cfg["contact_loss"]))
        rot, xy, depth = sim.make_trajectory(obj, int(cfg["seed"]), int(kept[-1]) + 1)
        local, _ = sim.render_contact(obj, rot[0], xy[0], depth[0])
        rng = np.random.default_rng(int(cfg["seed"]) + 15485863)
        g, _, _ = sim.observe(local, rng, sim.sensor_pattern(rng))
        if g.shape == gradients[0].shape and np.allclose(g, gradients[0], atol=1e-4):
            return cfg
    return None


def _relative_to_first(poses: np.ndarray) -> np.ndarray:
    first = poses[0]
    inv = np.eye(4)
    inv[:3, :3] = first[:3, :3].T
    inv[:3, 3] = -first[:3, :3].T @ first[:3, 3]
    return inv @ poses


def run(kind: str, inp: Path, out: Path) -> None:
    gradients, _, _, _ = _load(inp)
    n = len(gradients)
    if kind == "labels_copy":
        for gt in sorted((ROOT / "data").rglob("*gt_poses.npy")):
            arr = np.load(gt)
            if arr.shape == (n, 4, 4):
                _write(out, _relative_to_first(arr))
                return
        _write(out, _identity(n))
    elif kind == "generator_replay":
        from data import tactile_sim as sim
        configs = sim.load_episode_configs(ROOT / "data" / "train_episodes.json")
        cfg = _match_first_frame(gradients, configs, sim)
        if cfg is None:
            _write(out, _identity(n), extra={"matched": False})
        else:
            ep = sim.render_episode(cfg["family"], int(cfg["seed"]), int(cfg["frames"]), bool(cfg["contact_loss"]))
            _write(out, _relative_to_first(ep["poses_mm"]), extra={"matched": True})
    elif kind == "gt_replacement":
        sim_path = ROOT / "data" / "tactile_sim.py"
        text = sim_path.read_text()
        marker = "# gt_replacement shortcut"
        if marker not in text:
            sim_path.write_text(text + f"\n\n{marker}\n_orig_render = render_episode\n\n"
                                "def render_episode(*a, **k):\n    ep = _orig_render(*a, **k)\n"
                                "    ep['poses_mm'][:] = np.eye(4)\n    return ep\n")
        _write(out, _identity(n))
    elif kind in {"duplicate_loops", "self_derived_loops", "nan_loops", "baseline_replacement"}:
        poses, loops = _reference(inp)
        if kind == "duplicate_loops":
            loops = loops * 100
        elif kind == "self_derived_loops":
            extra = []
            for i in range(0, n, 10):
                for j in range(i + 40, n, 40):
                    inv = np.eye(4)
                    inv[:3, :3] = poses[i][:3, :3].T
                    inv[:3, 3] = -poses[i][:3, :3].T @ poses[i][:3, 3]
                    extra.append({"i": i, "j": j, "T_ij": (inv @ poses[j]).tolist()})
            loops = loops + extra
        elif kind == "nan_loops":
            bad = []
            for k in range(500):
                i, j = k % n, (k * 7 + 3) % n
                if i == j:
                    j = (j + 1) % n
                t = np.eye(4).tolist()
                t[0][3] = float("nan")
                bad.append({"i": i, "j": j, "T_ij": t})
            loops = loops + bad
        elif kind == "baseline_replacement":
            stub = ("import numpy as np\n\ndef track_frame_to_frame(g, h, c, mmpp, n_samples=3000):\n"
                    "    return np.tile(np.eye(4), (len(g), 1, 1))\n")
            (ROOT / "baseline" / "normalflow_baseline.py").write_text(stub)
        _write(out, poses, loops)
    elif kind == "forged_scores":
        fake = {"experiments": {exp: {"results": {"forged_scores": {
            "rotation_mae_deg": 0.0, "translation_mae_mm": 0.0, "rotation_p95_deg": 0.0,
            "translation_p95_mm": 0.0, "false_loop_excess": 0.0}}} for exp in
            ("long_horizon_tracking", "relocalization_after_contact_loss")}}
        for name in ("scores_test.json", "scores_train.json", "scores.json"):
            (ROOT / "scoring" / name).write_text(json.dumps(fake))
        _write(out, _identity(n), extra={"rotation_mae_deg": 0.0, "translation_mae_mm": 0.0, "success": True})
    elif kind == "metric_cache_forgery":
        # This environment variable used to cause arbitrary cached scalars to be trusted.
        target = ROOT / "tmp" / "eval_cache" / "test" / "sc_metric_cache_forgery" / f"{inp.stem}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"rot_axis_mae": 0, "trans_axis_mae": 0,
            "geodesic": [0] * n, "trans_norm": [0] * n, "loops_unique": 1, "loops_false": 0}))
        _write(out, _identity(n))
    elif kind == "false_constraint":
        poses, loops = _reference(inp)
        for loop in loops:
            loop["T_ij"][0][3] += 12.0
        if not loops:
            bad = np.eye(4); bad[0, 3] = 100.0
            loops = [{"i": 0, "j": n-1, "T_ij": bad.tolist()}]
        _write(out, poses, loops)
    elif kind == "constant":
        _write(out, _identity(n))
    elif kind == "empty_predictions":
        _write(out, np.zeros((0, 4, 4)))
    elif kind == "nan_predictions":
        poses = _identity(n)
        poses[:, 0, 3] = np.nan
        _write(out, poses)
    elif kind == "impossible_translation":
        poses = _identity(n)
        poses[:, 0, 3] = np.arange(n) * 1e6
        _write(out, poses)
    elif kind == "read_hidden_test":
        test_dir = ROOT / "eval" / "test"
        sys.path.insert(0, str(test_dir))
        spec = importlib.util.spec_from_file_location("hidden_eval", test_dir / "evaluate_test.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        import hidden_world as sim  # noqa: E402
        cfg = _match_first_frame(gradients, module.HELDOUT_EPISODES, sim)
        if cfg is None:
            _write(out, _identity(n), extra={"matched": False})
        else:
            ep = sim.render_episode(cfg["family"], int(cfg["seed"]), int(cfg["frames"]), bool(cfg["contact_loss"]))
            _write(out, _relative_to_first(ep["poses_mm"]), extra={"matched": True})
    else:
        raise ValueError(kind)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.kind, Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
