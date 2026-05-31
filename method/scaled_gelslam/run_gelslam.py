#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares

from method.scaled_gelslam.geometry import between, compose, se2_to_matrix, wrap
from method.scaled_gelslam.normalflow import estimate_relative, quality


def load_frames(path: Path) -> tuple[list[dict], np.ndarray]:
    data = np.load(path)
    frames = []
    for i in range(len(data["poses"])):
        frames.append(
            {
                "normal": data["normals"][i].astype(np.float64),
                "curvature": data["curvatures"][i].astype(np.float64),
                "mask": data["masks"][i].astype(bool),
                "height": data["heights"][i].astype(np.float64),
            }
        )
    return frames, data["poses"].astype(np.float64)


def feature_candidate(ref: dict, tgt: dict) -> np.ndarray | None:
    sift = cv2.SIFT_create(nfeatures=300, contrastThreshold=0.005, edgeThreshold=4)
    a = (ref["curvature"] * 255).astype(np.uint8)
    b = (tgt["curvature"] * 255).astype(np.uint8)
    kp1, des1 = sift.detectAndCompute(a, None)
    kp2, des2 = sift.detectAndCompute(b, None)
    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        return None
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    matches = matcher.knnMatch(des1, des2, k=2)
    good = [m for m, n in matches if m.distance < 0.78 * n.distance]
    if len(good) < 4:
        return None
    src = np.float32([kp1[m.queryIdx].pt for m in good])
    dst = np.float32([kp2[m.trainIdx].pt for m in good])
    mat, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0)
    if mat is None or inliers is None or int(inliers.sum()) < 4:
        return None
    theta = float(np.arctan2(mat[1, 0], mat[0, 0]))
    tx = float(mat[0, 2])
    ty = float(mat[1, 2])
    return np.array([tx, ty, theta], dtype=np.float64)


def optimize_pose_graph(n: int, edges: list[tuple[int, int, np.ndarray]], initial: np.ndarray) -> np.ndarray:
    if n <= 1:
        return initial.copy()

    def pack(poses: np.ndarray) -> np.ndarray:
        return poses[1:].reshape(-1)

    def unpack(vec: np.ndarray) -> np.ndarray:
        out = np.zeros((n, 3), dtype=np.float64)
        out[0] = initial[0]
        out[1:] = vec.reshape(n - 1, 3)
        return out

    def residual(vec: np.ndarray) -> np.ndarray:
        poses = unpack(vec)
        terms = []
        for i, j, meas in edges:
            pred = between(poses[i], poses[j])
            err = pred - meas
            err[2] = wrap(err[2])
            terms.extend([err[0] / 2.0, err[1] / 2.0, err[2] / 0.08])
        return np.asarray(terms)

    opt = least_squares(residual, pack(initial), max_nfev=200, loss="soft_l1", f_scale=1.0)
    poses = unpack(opt.x)
    poses[:, 2] = np.vectorize(wrap)(poses[:, 2])
    return poses


def run(dataset: Path, output_dir: Path, ccs_threshold: float, scr_threshold: float) -> None:
    frames, gt = load_frames(dataset)
    n = len(frames)
    keyframes = [0]
    frame_parent = np.zeros(n, dtype=int)
    frame_to_parent = np.zeros((n, 3), dtype=np.float64)
    keyframe_edges: list[tuple[int, int, np.ndarray]] = []
    coverage = [0]
    latest_key = 0
    prev_rel = np.zeros(3, dtype=np.float64)
    predicted = np.zeros((n, 3), dtype=np.float64)
    loops = []
    rejected_loops = 0

    for t in range(1, n):
        rel, ccs, scr, _ = estimate_relative(frames[latest_key], frames[t], prev_rel)
        if ccs < ccs_threshold or scr < scr_threshold:
            new_key = t - 1
            if new_key != latest_key:
                keyframes.append(new_key)
                k_new = len(keyframes) - 1
                edge_measurement = frame_to_parent[new_key].copy()
                keyframe_edges.append((k_new - 1, k_new, edge_measurement))
                frame_parent[new_key] = k_new
                frame_to_parent[new_key] = 0.0
                # Greedy coverage: add keyframe if it is not already well covered.
                best_scr = 0.0
                for cov_idx in coverage:
                    init = feature_candidate(frames[cov_idx], frames[new_key])
                    if init is None:
                        continue
                    refined, qccs, qscr, _ = estimate_relative(frames[cov_idx], frames[new_key], init)
                    best_scr = max(best_scr, qscr)
                    if qccs >= ccs_threshold and qscr >= scr_threshold:
                        loops.append((keyframes.index(cov_idx), k_new, refined.tolist(), qccs, qscr))
                        keyframe_edges.append((keyframes.index(cov_idx), k_new, refined))
                    else:
                        rejected_loops += 1
                if best_scr < 0.45:
                    coverage.append(new_key)
                latest_key = new_key
                prev_rel = np.zeros(3, dtype=np.float64)
            else:
                keyframes.append(t)
                latest_key = t
                coverage.append(t)
                prev_rel = np.zeros(3, dtype=np.float64)
                continue
            rel, ccs, scr, _ = estimate_relative(frames[latest_key], frames[t], prev_rel)
        frame_parent[t] = len(keyframes) - 1
        frame_to_parent[t] = rel
        prev_rel = rel

    initial_keys = np.zeros((len(keyframes), 3), dtype=np.float64)
    for i, j, meas in keyframe_edges:
        if j == i + 1:
            initial_keys[j] = compose(initial_keys[i], meas)
    optimized_keys = optimize_pose_graph(len(keyframes), keyframe_edges, initial_keys)
    for t in range(n):
        predicted[t] = compose(optimized_keys[frame_parent[t]], frame_to_parent[t])

    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "pred_poses.npy", predicted)
    np.save(output_dir / "gt_poses.npy", gt)
    np.save(output_dir / "keyframe_poses.npy", optimized_keys)
    np.save(output_dir / "pred_matrices.npy", np.asarray([se2_to_matrix(p) for p in predicted]))
    summary = {
        "method": "scaled_gelslam",
        "frames": n,
        "keyframes": len(keyframes),
        "keyframe_indices": keyframes,
        "coverage_keyframes": len(coverage),
        "accepted_loops": len(loops),
        "rejected_loop_candidates": rejected_loops,
        "loop_edges": loops,
        "ccs_threshold": ccs_threshold,
        "scr_threshold": scr_threshold,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/synthetic_tracking/loop_patch.npz")
    parser.add_argument("--output-dir", default="checkpoints/scaled_gelslam")
    parser.add_argument("--ccs-threshold", type=float, default=0.72)
    parser.add_argument("--scr-threshold", type=float, default=0.25)
    args = parser.parse_args()
    run(Path(args.dataset), Path(args.output_dir), args.ccs_threshold, args.scr_threshold)


if __name__ == "__main__":
    main()
