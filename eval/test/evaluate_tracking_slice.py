#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

SLICE_NAME = "test"
SLICE_BLOCK_PARITY = 1
BLOCK_SIZE = 8
LONG_LOOP_SPAN_FRAMES = 32
GELSIGHT_MM_PER_PIXEL = 20.0 / 320.0
NO_LOOP_TRANSLATION_PENALTY_MM = 10.0 * GELSIGHT_MM_PER_PIXEL
NO_LOOP_ROTATION_PENALTY_DEG = 20.0
LEGACY_SCORE_NAMES = {
    "normalflow_baseline": "normalflow",
    "scaled_gelslam": "gelslam_online",
}


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


def tracking_indices(n_frames: int) -> np.ndarray:
    return np.asarray([idx for idx in range(n_frames) if (idx // BLOCK_SIZE) % 2 == SLICE_BLOCK_PARITY], dtype=np.int64)


def long_loop_edges(loop_edges: list, keyframe_indices: list) -> list:
    selected = []
    for edge in loop_edges:
        keep = False
        if len(edge) >= 2 and keyframe_indices:
            key_i, key_j = int(edge[0]), int(edge[1])
            if key_i < len(keyframe_indices) and key_j < len(keyframe_indices):
                frame_i = int(keyframe_indices[key_i])
                frame_j = int(keyframe_indices[key_j])
                span = abs(frame_j - frame_i)
                keep = span >= LONG_LOOP_SPAN_FRAMES
        if keep:
            selected.append(edge)
    return selected


def read_summary(run_dir: Path) -> dict:
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        return {}
    return json.loads(summary_path.read_text())


def score_name_for_run(run_dir: Path) -> str:
    summary = read_summary(run_dir)
    explicit = summary.get("score_name")
    if isinstance(explicit, str) and explicit:
        return explicit
    if run_dir.name in LEGACY_SCORE_NAMES:
        return LEGACY_SCORE_NAMES[run_dir.name]
    method = summary.get("method")
    if isinstance(method, str) and method:
        return LEGACY_SCORE_NAMES.get(method, method)
    return run_dir.name


def discover_method_runs(root: Path, expected_methods: set[str] | None) -> list[tuple[str, Path]]:
    runs = []
    for pred_path in sorted(root.rglob("pred_poses.npy")):
        run_dir = pred_path.parent
        name = score_name_for_run(run_dir)
        if expected_methods is not None and name not in expected_methods:
            continue
        runs.append((name, run_dir))
    seen = {}
    for name, run_dir in runs:
        if name in seen:
            raise ValueError(f"Duplicate method name {name!r}: {seen[name]} and {run_dir}")
        seen[name] = run_dir
    if expected_methods is not None:
        missing = sorted(expected_methods - set(seen))
        if missing:
            raise FileNotFoundError(f"Could not find prediction artifacts for expected methods: {missing}")
    return sorted(runs, key=lambda item: item[0])


def expected_methods_from_scores(path: Path) -> set[str]:
    data = json.loads(path.read_text())
    experiments = data.get("experiments", data)
    methods: set[str] = set()
    for exp_data in experiments.values():
        if not isinstance(exp_data, dict):
            continue
        results = exp_data.get("results", exp_data)
        if isinstance(results, dict):
            methods.update(name for name in results if not str(name).startswith("_"))
    return methods


def metrics(run_dir: Path, gt: np.ndarray) -> dict[str, float]:
    pred = np.load(run_dir / "pred_poses.npy")
    if len(pred) != len(gt):
        raise ValueError(f"{run_dir} has {len(pred)} predictions but dataset has {len(gt)} ground-truth poses")
    indices = tracking_indices(len(gt))
    pred = origin_relative(pred)
    gt = origin_relative(gt)
    errors = np.asarray([relative_error(p, g) for p, g in zip(pred, gt)], dtype=np.float64)
    full_pos_err_mm = np.linalg.norm(errors[:, :3], axis=1) * GELSIGHT_MM_PER_PIXEL
    full_rot_err_deg = np.degrees(np.linalg.norm(errors[:, 3:], axis=1))
    pos_err_mm = full_pos_err_mm[indices]
    rot_err_deg = full_rot_err_deg[indices]

    summary = read_summary(run_dir)
    keyframe_indices = summary.get("keyframe_indices", [])
    loop_edges = long_loop_edges(summary.get("loop_edges", []), keyframe_indices)
    accepted = len(loop_edges)
    false_loops = 0
    loop_translation_errors_mm = []
    loop_rotation_errors_deg = []
    loop_span_mask = np.zeros(len(gt), dtype=bool)
    for edge in loop_edges:
        if len(edge) >= 2 and keyframe_indices:
            key_i, key_j = int(edge[0]), int(edge[1])
            if key_i < len(keyframe_indices) and key_j < len(keyframe_indices):
                frame_i = int(keyframe_indices[key_i])
                frame_j = int(keyframe_indices[key_j])
                lo, hi = sorted((frame_i, frame_j))
                loop_span_mask[lo : hi + 1] = True
        if len(edge) < 3 or not keyframe_indices:
            false_loops += 1
            loop_translation_errors_mm.append(NO_LOOP_TRANSLATION_PENALTY_MM)
            loop_rotation_errors_deg.append(NO_LOOP_ROTATION_PENALTY_DEG)
            continue
        key_i, key_j, measurement = int(edge[0]), int(edge[1]), as_se3(np.asarray(edge[2], dtype=float))
        if key_i >= len(keyframe_indices) or key_j >= len(keyframe_indices):
            false_loops += 1
            loop_translation_errors_mm.append(NO_LOOP_TRANSLATION_PENALTY_MM)
            loop_rotation_errors_deg.append(NO_LOOP_ROTATION_PENALTY_DEG)
            continue
        true_rel = compose(invert(gt[int(keyframe_indices[key_i])]), gt[int(keyframe_indices[key_j])])
        loop_err = relative_error(measurement, true_rel)
        terr = float(np.linalg.norm(loop_err[:3]))
        rerr = float(np.linalg.norm(loop_err[3:]))
        loop_translation_errors_mm.append(terr * GELSIGHT_MM_PER_PIXEL)
        loop_rotation_errors_deg.append(np.degrees(rerr))
        if terr > 10.0 or np.degrees(rerr) > 20.0:
            false_loops += 1
    valid_loops = accepted - false_loops
    if not loop_translation_errors_mm:
        loop_translation_errors_mm.append(NO_LOOP_TRANSLATION_PENALTY_MM)
        loop_rotation_errors_deg.append(NO_LOOP_ROTATION_PENALTY_DEG)
    loop_span_indices = indices[loop_span_mask[indices]]
    if len(loop_span_indices) == 0:
        loop_span_indices = indices
    return {
        "rotation_mae_deg": float(rot_err_deg.mean()),
        "translation_mae_mm": float(pos_err_mm.mean()),
        "rotation_p95_deg": float(np.percentile(rot_err_deg, 95)),
        "translation_p95_mm": float(np.percentile(pos_err_mm, 95)),
        "terminal_rotation_error_deg": float(rot_err_deg[-1]),
        "terminal_translation_error_mm": float(pos_err_mm[-1]),
        "accepted_loops": accepted,
        "valid_loops": valid_loops,
        "valid_loop_rate": float(valid_loops / max(accepted, 1)),
        "false_loop_rate": float(false_loops / max(accepted, 1)),
        "loop_translation_error_mm": float(np.mean(loop_translation_errors_mm)),
        "loop_rotation_error_deg": float(np.mean(loop_rotation_errors_deg)),
        "loop_span_translation_mae_mm": float(np.mean(full_pos_err_mm[loop_span_indices])),
        "loop_span_rotation_mae_deg": float(np.mean(full_rot_err_deg[loop_span_indices])),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method-run", action="append", nargs=2, metavar=("NAME", "DIR"))
    parser.add_argument("--discover-root", default=None)
    parser.add_argument("--expected-methods-from", default=None)
    parser.add_argument("--dataset", default="data/synthetic_tracking/loop_patch.npz")
    parser.add_argument("--output", default="scoring/scores_test.json")
    args = parser.parse_args()

    expected = expected_methods_from_scores(Path(args.expected_methods_from)) if args.expected_methods_from else None
    if args.method_run:
        method_runs = [(name, Path(directory)) for name, directory in args.method_run]
        if expected is not None:
            found = {name for name, _ in method_runs}
            missing = sorted(expected - found)
            if missing:
                raise ValueError(f"Explicit method runs are missing expected methods: {missing}")
    elif args.discover_root:
        method_runs = discover_method_runs(Path(args.discover_root), expected)
    else:
        raise SystemExit("Provide METHOD_NAME RUN_DIR pairs or --discover-root")
    if not method_runs:
        raise SystemExit("No prediction artifacts found.")

    gt = load_ground_truth(Path(args.dataset))
    flat_results = {name: metrics(run_dir, gt) for name, run_dir in method_runs}
    scores = {
        "_metadata": {
            "slice": SLICE_NAME,
            "split": f"block_interleaved_{BLOCK_SIZE}_frame_tracking_with_global_long_loop_constraint_ge_{LONG_LOOP_SPAN_FRAMES}_frames",
        },
        "experiments": {
            "synthetic_long_horizon_tracking": {
                "results": {
                    name: {
                        "rotation_mae_deg": vals["rotation_mae_deg"],
                        "translation_mae_mm": vals["translation_mae_mm"],
                        "rotation_p95_deg": vals["rotation_p95_deg"],
                        "translation_p95_mm": vals["translation_p95_mm"],
                        "terminal_rotation_error_deg": vals["terminal_rotation_error_deg"],
                        "terminal_translation_error_mm": vals["terminal_translation_error_mm"],
                    }
                    for name, vals in flat_results.items()
                }
            },
            "loop_closure_quality": {
                "results": {
                    name: {
                        "accepted_loops": vals["accepted_loops"],
                        "valid_loops": vals["valid_loops"],
                        "valid_loop_rate": vals["valid_loop_rate"],
                        "false_loop_rate": vals["false_loop_rate"],
                        "loop_translation_error_mm": vals["loop_translation_error_mm"],
                        "loop_rotation_error_deg": vals["loop_rotation_error_deg"],
                        "loop_span_translation_mae_mm": vals["loop_span_translation_mae_mm"],
                        "loop_span_rotation_mae_deg": vals["loop_span_rotation_mae_deg"],
                    }
                    for name, vals in flat_results.items()
                }
            },
        },
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scores, indent=2) + "\n")


if __name__ == "__main__":
    main()
