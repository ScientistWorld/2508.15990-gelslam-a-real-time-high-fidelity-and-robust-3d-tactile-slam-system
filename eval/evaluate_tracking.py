#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

GELSIGHT_MM_PER_PIXEL = 20.0 / 320.0


def as_se3(pose: np.ndarray) -> np.ndarray:
    pose = np.asarray(pose, dtype=np.float64)
    if pose.shape == (6,):
        return pose.copy()
    if pose.shape == (3,):
        return np.array([pose[0], pose[1], 0.0, 0.0, 0.0, pose[2]], dtype=np.float64)
    raise ValueError(f"Expected pose vector with 3 or 6 entries, got {pose.shape}")


def matrix_from_pose(pose: np.ndarray) -> np.ndarray:
    pose = as_se3(pose)
    mat = np.eye(4, dtype=np.float64)
    mat[:3, :3] = Rotation.from_rotvec(pose[3:]).as_matrix()
    mat[:3, 3] = pose[:3]
    return mat


def pose_from_matrix(mat: np.ndarray) -> np.ndarray:
    return np.concatenate([mat[:3, 3], Rotation.from_matrix(mat[:3, :3]).as_rotvec()]).astype(np.float64)


def compose(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return pose_from_matrix(matrix_from_pose(a) @ matrix_from_pose(b))


def invert(a: np.ndarray) -> np.ndarray:
    return pose_from_matrix(np.linalg.inv(matrix_from_pose(a)))


def origin_relative(poses: np.ndarray) -> np.ndarray:
    poses = np.asarray([as_se3(p) for p in poses], dtype=np.float64)
    inv0 = invert(poses[0])
    return np.asarray([compose(inv0, p) for p in poses])


def relative_error(pred: np.ndarray, gt: np.ndarray) -> np.ndarray:
    return pose_from_matrix(np.linalg.inv(matrix_from_pose(gt)) @ matrix_from_pose(pred))


def load_ground_truth(dataset: Path) -> np.ndarray:
    data = np.load(dataset)
    if "poses" not in data:
        raise KeyError(f"{dataset} does not contain required 'poses' ground-truth array")
    return np.asarray([as_se3(p) for p in data["poses"]], dtype=np.float64)


def metrics(run_dir: Path, gt: np.ndarray) -> dict[str, float]:
    """Evaluate one method run.

    Required artifact:
    - pred_poses.npy: one 3- or 6-vector pose per frame.

    Optional artifacts:
    - summary.json with loop_edges and keyframe_indices for loop metrics.
    - keyframe_poses.npy can be present for diagnostics, but raw keyframe
      counts are not scored because the packaged benchmark is shorter than the
      paper's real episodes.
    """
    pred = np.load(run_dir / "pred_poses.npy")
    if len(pred) != len(gt):
        raise ValueError(f"{run_dir} has {len(pred)} predictions but dataset has {len(gt)} ground-truth poses")
    pred = origin_relative(pred)
    gt = origin_relative(gt)
    errors = np.asarray([relative_error(p, g) for p, g in zip(pred, gt)], dtype=np.float64)
    pos_err = np.linalg.norm(errors[:, :3], axis=1)
    rot_err = np.linalg.norm(errors[:, 3:], axis=1)
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    loop_edges = summary.get("loop_edges", [])
    accepted = len(loop_edges)
    false_loops = 0
    keyframe_indices = summary.get("keyframe_indices", [])
    for edge in loop_edges:
        if len(edge) < 3 or not keyframe_indices:
            false_loops += 1
            continue
        key_i, key_j, measurement = int(edge[0]), int(edge[1]), as_se3(np.asarray(edge[2], dtype=float))
        if key_i >= len(keyframe_indices) or key_j >= len(keyframe_indices):
            false_loops += 1
            continue
        true_rel = compose(invert(gt[int(keyframe_indices[key_i])]), gt[int(keyframe_indices[key_j])])
        loop_err = relative_error(measurement, true_rel)
        terr = float(np.linalg.norm(loop_err[:3]))
        rerr = float(np.linalg.norm(loop_err[3:]))
        if terr > 10.0 or np.degrees(rerr) > 20.0:
            false_loops += 1
    return {
        "rotation_mae_deg": float(np.degrees(rot_err).mean()),
        "translation_mae_mm": float(pos_err.mean() * GELSIGHT_MM_PER_PIXEL),
        "accepted_loops": accepted,
        "false_loop_rate": float(false_loops / max(accepted, 1)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method-run", action="append", nargs=2, metavar=("NAME", "DIR"), required=True)
    parser.add_argument("--dataset", default="data/synthetic_tracking/loop_patch.npz")
    parser.add_argument("--output", default="scoring/scores.json")
    args = parser.parse_args()
    gt = load_ground_truth(Path(args.dataset))
    flat_results = {}
    for name, directory in args.method_run:
        flat_results[name] = metrics(Path(directory), gt)
    scores = {
        "experiments": {
            "synthetic_long_horizon_tracking": {
                "results": {
                    name: {
                        "rotation_mae_deg": vals["rotation_mae_deg"],
                        "translation_mae_mm": vals["translation_mae_mm"],
                    }
                    for name, vals in flat_results.items()
                }
            },
            "loop_closure_quality": {
                "results": {
                    name: {
                        "accepted_loops": vals["accepted_loops"],
                        "false_loop_rate": vals["false_loop_rate"],
                    }
                    for name, vals in flat_results.items()
                }
            },
        }
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scores, indent=2) + "\n")


if __name__ == "__main__":
    main()
