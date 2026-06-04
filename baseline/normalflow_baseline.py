#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from baseline.geometry import compose, matrix_from_pose, rotate_vectors, transform_points
from baseline.normalflow import estimate_relative, geometric_properties


def load_tactile_frames(path: Path) -> list[dict]:
    data = np.load(path)
    return [
        geometric_properties(data["heights"][i].astype(np.float64), data["masks"][i].astype(bool))
        for i in range(len(data["heights"]))
    ]


def reconstruct_points(
    frames: list[dict],
    frame_indices: list[int],
    poses: np.ndarray,
    stride: int = 2,
    voxel_size: float = 0.8,
) -> tuple[np.ndarray, np.ndarray]:
    """Fuse baseline odometry frames for diagnostic artifacts.

    Evaluation does not score reconstruction by default, but the baseline emits
    the same artifact format as the proposed method so downstream users can
    inspect comparable outputs.
    """
    bins: dict[tuple[int, int, int], tuple[np.ndarray, np.ndarray, float]] = {}
    for frame_idx in frame_indices:
        frame = frames[frame_idx]
        mask = frame["mask"]
        if mask.sum() == 0:
            continue
        boundary_weight = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 3)
        ys, xs = np.nonzero(mask)
        keep = (xs % stride == 0) & (ys % stride == 0)
        ys = ys[keep]
        xs = xs[keep]
        if len(xs) == 0:
            continue
        h, w = frame["height"].shape
        local = np.column_stack(
            [
                xs.astype(np.float64) - (w - 1) / 2.0,
                ys.astype(np.float64) - (h - 1) / 2.0,
                frame["height"][ys, xs],
            ]
        )
        weights = 1.0 / (1.0 + np.exp(-(boundary_weight[ys, xs] - 3.0)))
        world = transform_points(local, poses[frame_idx])
        normals = rotate_vectors(frame["normal"][ys, xs], poses[frame_idx])
        keys = np.rint(world / voxel_size).astype(np.int64)
        for key_arr, point, normal, weight in zip(keys, world, normals, weights):
            key = tuple(int(v) for v in key_arr)
            if key not in bins:
                bins[key] = (point * weight, normal * weight, float(weight))
            else:
                psum, nsum, wsum = bins[key]
                bins[key] = (psum + point * weight, nsum + normal * weight, wsum + float(weight))

    if not bins:
        return np.zeros((0, 3), dtype=np.float64), np.zeros((0, 3), dtype=np.float64)
    points, normals = [], []
    for psum, nsum, wsum in bins.values():
        points.append(psum / max(wsum, 1e-9))
        normal = nsum / max(np.linalg.norm(nsum), 1e-9)
        normals.append(normal)
    return np.asarray(points, dtype=np.float64), np.asarray(normals, dtype=np.float64)


def run(dataset: Path, output_dir: Path) -> None:
    frames = load_tactile_frames(dataset)
    pred = np.zeros((len(frames), 6), dtype=np.float64)
    prev_rel = np.zeros(6, dtype=np.float64)
    for i in range(1, len(frames)):
        rel, _, _, _ = estimate_relative(frames[i - 1], frames[i], prev_rel)
        pred[i] = compose(pred[i - 1], rel)
        prev_rel = rel
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "pred_poses.npy", pred)
    np.save(output_dir / "pred_matrices.npy", np.asarray([matrix_from_pose(p) for p in pred]))
    recon_points, recon_normals = reconstruct_points(frames, list(range(len(frames))), pred)
    np.save(output_dir / "reconstructed_points.npy", recon_points)
    np.save(output_dir / "reconstructed_normals.npy", recon_normals)
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "method": "normalflow_baseline",
                "frames": len(frames),
                "keyframes": len(frames),
                "accepted_loops": 0,
                "reconstructed_points": int(len(recon_points)),
            },
            indent=2,
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/synthetic_tracking/loop_patch.npz")
    parser.add_argument("--output-dir", default="checkpoints/normalflow_baseline")
    args = parser.parse_args()
    run(Path(args.dataset), Path(args.output_dir))


if __name__ == "__main__":
    main()
