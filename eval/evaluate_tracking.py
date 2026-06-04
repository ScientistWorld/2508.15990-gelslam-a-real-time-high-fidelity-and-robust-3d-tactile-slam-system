#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

GELSIGHT_MM_PER_PIXEL = 20.0 / 320.0
LOOP_OPPORTUNITY_BUDGET = 8.0


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


def transform_points(points: np.ndarray, pose: np.ndarray) -> np.ndarray:
    pose = as_se3(pose)
    rot = Rotation.from_rotvec(pose[3:]).as_matrix()
    return points @ rot.T + pose[:3]


def rotate_vectors(vectors: np.ndarray, pose: np.ndarray) -> np.ndarray:
    return Rotation.from_rotvec(as_se3(pose)[3:]).apply(vectors)


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


def target_reconstruction(dataset: Path, stride: int = 4) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(dataset)
    gt = np.asarray([as_se3(p) for p in data["poses"]], dtype=np.float64)
    heights = data["heights"]
    normals = data["normals"]
    masks = data["masks"]
    points_out, normals_out = [], []
    for pose, height, normal, mask in zip(gt, heights, normals, masks):
        ys, xs = np.nonzero(mask)
        keep = (xs % stride == 0) & (ys % stride == 0)
        ys = ys[keep]
        xs = xs[keep]
        if len(xs) == 0:
            continue
        h, w = height.shape
        local = np.column_stack(
            [
                xs.astype(np.float64) - (w - 1) / 2.0,
                ys.astype(np.float64) - (h - 1) / 2.0,
                height[ys, xs].astype(np.float64),
            ]
        )
        points_out.append(transform_points(local, pose))
        normals_out.append(rotate_vectors(normal[ys, xs].astype(np.float64), pose))
    points = np.concatenate(points_out, axis=0)
    nrms = np.concatenate(normals_out, axis=0)
    nrms /= np.linalg.norm(nrms, axis=1, keepdims=True) + 1e-9
    return points, nrms


def reconstruction_metrics(run_dir: Path, target_points: np.ndarray, target_normals: np.ndarray) -> dict[str, float]:
    points_path = run_dir / "reconstructed_points.npy"
    normals_path = run_dir / "reconstructed_normals.npy"
    if not points_path.exists() or not normals_path.exists():
        return {"chamfer_distance_mm": 1e6, "normal_cosine_distance": 0.0}
    pred_points = np.load(points_path).astype(np.float64)
    pred_normals = np.load(normals_path).astype(np.float64)
    if len(pred_points) == 0 or len(target_points) == 0:
        return {"chamfer_distance_mm": 1e6, "normal_cosine_distance": 0.0}
    pred_normals /= np.linalg.norm(pred_normals, axis=1, keepdims=True) + 1e-9
    target_tree = cKDTree(target_points)
    pred_tree = cKDTree(pred_points)
    d_pred_to_target, idx_target = target_tree.query(pred_points, k=1, workers=1)
    d_target_to_pred, idx_pred = pred_tree.query(target_points, k=1, workers=1)
    chamfer_px = 0.5 * (float(np.mean(d_pred_to_target)) + float(np.mean(d_target_to_pred)))
    pred_cos = np.sum(pred_normals * target_normals[idx_target], axis=1)
    target_cos = np.sum(target_normals * pred_normals[idx_pred], axis=1)
    ncd = 0.5 * (float(np.mean(np.clip(pred_cos, -1.0, 1.0))) + float(np.mean(np.clip(target_cos, -1.0, 1.0))))
    return {
        "chamfer_distance_mm": chamfer_px * GELSIGHT_MM_PER_PIXEL,
        "normal_cosine_distance": ncd,
    }


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
    valid_loops = accepted - false_loops
    return {
        "rotation_mae_deg": float(np.degrees(rot_err).mean()),
        "translation_mae_mm": float(pos_err.mean() * GELSIGHT_MM_PER_PIXEL),
        "accepted_loops": accepted,
        "valid_loops": valid_loops,
        "valid_loop_recall": float(min(valid_loops / LOOP_OPPORTUNITY_BUDGET, 1.0)),
        "valid_loop_rate": float(valid_loops / max(accepted, 1)),
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
        vals = metrics(Path(directory), gt)
        flat_results[name] = vals
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
                        "valid_loops": vals["valid_loops"],
                        "valid_loop_recall": vals["valid_loop_recall"],
                        "valid_loop_rate": vals["valid_loop_rate"],
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
