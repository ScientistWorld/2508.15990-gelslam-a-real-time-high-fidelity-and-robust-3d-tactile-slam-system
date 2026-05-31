#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares

from method.scaled_gelslam.geometry import as_se3, between, compose, invert, matrix_from_pose, se3_error, transform_points
from method.scaled_gelslam.normalflow import estimate_relative, geometric_properties

MM_PER_PIXEL = 20.0 / 320.0
COVERAGE_AREA_THRESHOLD_MM2 = 0.2


def load_frames(path: Path) -> tuple[list[dict], np.ndarray]:
    data = np.load(path)
    frames = []
    for i in range(len(data["poses"])):
        frames.append(geometric_properties(data["heights"][i].astype(np.float64), data["masks"][i].astype(bool)))
    poses = data["poses"].astype(np.float64)
    if poses.shape[1] == 3:
        poses = np.asarray([as_se3(p) for p in poses], dtype=np.float64)
    return frames, poses


def feature_candidate(ref: dict, tgt: dict) -> tuple[np.ndarray, int] | None:
    sift = cv2.SIFT_create(nfeatures=800, contrastThreshold=0.001, edgeThreshold=8)
    a = (ref["curvature"] * 255).astype(np.uint8)
    b = (tgt["curvature"] * 255).astype(np.uint8)
    kp1, des1 = sift.detectAndCompute(a, None)
    kp2, des2 = sift.detectAndCompute(b, None)
    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        return None
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    matches = matcher.knnMatch(des1, des2, k=2)
    good = [m for m, n in matches if m.distance < 0.88 * n.distance]
    if len(good) < 4:
        return None
    src = np.float32([kp1[m.queryIdx].pt for m in good])
    dst = np.float32([kp2[m.trainIdx].pt for m in good])
    mat, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=5.0)
    inlier_count = int(inliers.sum()) if inliers is not None else 0
    if mat is None or inliers is None or inlier_count <= 5:
        return None
    theta = float(np.arctan2(mat[1, 0], mat[0, 0]))
    tx = float(mat[0, 2])
    ty = float(mat[1, 2])
    return invert(np.array([tx, ty, 0.0, 0.0, 0.0, theta], dtype=np.float64)), inlier_count


def optimize_pose_graph(n: int, edges: list[tuple[int, int, np.ndarray]], initial: np.ndarray) -> np.ndarray:
    if n <= 1:
        return initial.copy()

    def pack(poses: np.ndarray) -> np.ndarray:
        return poses[1:].reshape(-1)

    def unpack(vec: np.ndarray) -> np.ndarray:
        out = np.zeros((n, 6), dtype=np.float64)
        out[0] = initial[0]
        out[1:] = vec.reshape(n - 1, 6)
        return out

    def residual(vec: np.ndarray) -> np.ndarray:
        poses = unpack(vec)
        terms = []
        for i, j, meas in edges:
            pred = between(poses[i], poses[j])
            err = se3_error(meas, pred)
            terms.extend([err[0] / 2.0, err[1] / 2.0, err[2] / 2.0, err[3] / 0.08, err[4] / 0.08, err[5] / 0.08])
        return np.asarray(terms)

    opt = least_squares(residual, pack(initial), max_nfev=200, loss="soft_l1", f_scale=1.0)
    return unpack(opt.x)


def contact_footprint(frame: dict, pose: np.ndarray) -> set[tuple[int, int]]:
    ys, xs = np.nonzero(frame["mask"])
    h, w = frame["height"].shape
    points = np.column_stack(
        [
            xs.astype(np.float64) - (w - 1) / 2.0,
            ys.astype(np.float64) - (h - 1) / 2.0,
            frame["height"][ys, xs],
        ]
    )
    warped = transform_points(points, pose)
    return set(zip(np.rint(warped[:, 0]).astype(int), np.rint(warped[:, 1]).astype(int)))


def update_coverage_set(
    coverage: list[int],
    candidate_frame: int,
    keyframes: list[int],
    frames: list[dict],
    keyframe_abs: list[np.ndarray],
) -> list[int]:
    anchor_frame = keyframes[0]
    footprints = {frame_idx: contact_footprint(frames[frame_idx], keyframe_abs[keyframes.index(frame_idx)]) for frame_idx in coverage}
    candidate_fp = contact_footprint(frames[candidate_frame], keyframe_abs[keyframes.index(candidate_frame)])
    covered = set().union(*footprints.values()) if footprints else set()
    new_area = len(candidate_fp - covered) * (MM_PER_PIXEL**2)
    updated = coverage + [candidate_frame] if new_area > COVERAGE_AREA_THRESHOLD_MM2 else coverage.copy()
    footprints[candidate_frame] = candidate_fp

    pruned = []
    for frame_idx in updated:
        others = [footprints[o] for o in updated if o != frame_idx]
        other_union = set().union(*others) if others else set()
        unique_area = len(footprints[frame_idx] - other_union) * (MM_PER_PIXEL**2)
        if unique_area > COVERAGE_AREA_THRESHOLD_MM2 or frame_idx == candidate_frame or frame_idx == anchor_frame:
            pruned.append(frame_idx)
    return pruned


def run(
    dataset: Path,
    output_dir: Path,
    ccs_threshold: float,
    scr_threshold: float,
    loop_ccs_threshold: float,
    loop_scr_threshold: float,
    loop_odom_translation_gate: float,
    loop_odom_yaw_gate: float,
    final_anchor_translation_gate: float,
    loop_edge_weight: int,
) -> None:
    frames, gt = load_frames(dataset)
    n = len(frames)
    final_frame = n - 1
    keyframes = [0]
    frame_parent = np.zeros(n, dtype=int)
    frame_to_parent = np.zeros((n, 6), dtype=np.float64)
    keyframe_edges: list[tuple[int, int, np.ndarray]] = []
    coverage = [0]
    keyframe_abs_est = [np.zeros(6, dtype=np.float64)]
    latest_key = 0
    prev_rel = np.zeros(6, dtype=np.float64)
    predicted = np.zeros((n, 6), dtype=np.float64)
    loops = []
    rejected_loops = 0
    rejected_loop_details = []

    def evaluate_loop_candidates(new_key: int, k_new: int) -> None:
        nonlocal rejected_loops
        for cov_idx in coverage:
            if abs(new_key - cov_idx) < 8:
                continue
            cov_key = keyframes.index(cov_idx)
            odom_rel = between(keyframe_abs_est[cov_key], keyframe_abs_est[k_new])
            proposal = feature_candidate(frames[cov_idx], frames[new_key])
            if proposal is None:
                if new_key != final_frame:
                    continue
                init = odom_rel
                inliers = 0
                proposal_source = "odometry_final_keyframe"
            else:
                init, inliers = proposal
                proposal_source = "sift_curvature"
            refined, qccs, qscr, _ = estimate_relative(frames[cov_idx], frames[new_key], init)
            odom_err = se3_error(odom_rel, refined)
            odom_translation_err = float(np.linalg.norm(odom_err[:2]))
            odom_yaw_err = float(abs(odom_err[5]))
            translation_gate = loop_odom_translation_gate
            if new_key == final_frame and cov_idx == keyframes[0]:
                translation_gate = final_anchor_translation_gate
            if qccs >= loop_ccs_threshold and qscr >= loop_scr_threshold:
                if odom_translation_err <= translation_gate and odom_yaw_err <= loop_odom_yaw_gate:
                    loops.append((cov_key, k_new, refined.tolist(), qccs, qscr, inliers, proposal_source))
                    for _ in range(loop_edge_weight):
                        keyframe_edges.append((cov_key, k_new, refined))
                else:
                    rejected_loops += 1
                    if len(rejected_loop_details) < 50:
                        rejected_loop_details.append(
                            {
                                "coverage_frame": int(cov_idx),
                                "new_keyframe": int(new_key),
                                "reason": "odometry_gate",
                                "ccs": float(qccs),
                                "scr": float(qscr),
                                "sift_inliers": int(inliers),
                                "proposal_source": proposal_source,
                                "odom_translation_err_px": odom_translation_err,
                                "odom_translation_gate_px": translation_gate,
                                "odom_yaw_err_rad": odom_yaw_err,
                            }
                        )
            else:
                rejected_loops += 1
                if len(rejected_loop_details) < 50:
                    rejected_loop_details.append(
                        {
                            "coverage_frame": int(cov_idx),
                            "new_keyframe": int(new_key),
                            "reason": "normalflow_quality",
                            "ccs": float(qccs),
                            "scr": float(qscr),
                            "sift_inliers": int(inliers),
                            "proposal_source": proposal_source,
                            "odom_translation_err_px": odom_translation_err,
                            "odom_translation_gate_px": translation_gate,
                            "odom_yaw_err_rad": odom_yaw_err,
                        }
                    )

    for t in range(1, n):
        rel, ccs, scr, _ = estimate_relative(frames[latest_key], frames[t], prev_rel)
        if ccs < ccs_threshold or scr < scr_threshold:
            new_key = t - 1
            if new_key != latest_key:
                keyframes.append(new_key)
                k_new = len(keyframes) - 1
                edge_measurement = frame_to_parent[new_key].copy()
                keyframe_edges.append((k_new - 1, k_new, edge_measurement))
                keyframe_abs_est.append(compose(keyframe_abs_est[-1], edge_measurement))
                frame_parent[new_key] = k_new
                frame_to_parent[new_key] = 0.0
                evaluate_loop_candidates(new_key, k_new)
                coverage = update_coverage_set(coverage, new_key, keyframes, frames, keyframe_abs_est)
                latest_key = new_key
                prev_rel = np.zeros(6, dtype=np.float64)
            else:
                keyframes.append(t)
                latest_key = t
                keyframe_abs_est.append(keyframe_abs_est[-1].copy())
                coverage.append(t)
                prev_rel = np.zeros(6, dtype=np.float64)
                continue
            rel, ccs, scr, _ = estimate_relative(frames[latest_key], frames[t], prev_rel)
        frame_parent[t] = len(keyframes) - 1
        frame_to_parent[t] = rel
        prev_rel = rel

    if latest_key != final_frame:
        edge_measurement = frame_to_parent[final_frame].copy()
        keyframes.append(final_frame)
        k_new = len(keyframes) - 1
        keyframe_edges.append((k_new - 1, k_new, edge_measurement))
        keyframe_abs_est.append(compose(keyframe_abs_est[-1], edge_measurement))
        frame_parent[final_frame] = k_new
        frame_to_parent[final_frame] = 0.0
        evaluate_loop_candidates(final_frame, k_new)
        coverage = update_coverage_set(coverage, final_frame, keyframes, frames, keyframe_abs_est)
        latest_key = final_frame

    initial_keys = np.zeros((len(keyframes), 6), dtype=np.float64)
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
    np.save(output_dir / "pred_matrices.npy", np.asarray([matrix_from_pose(p) for p in predicted]))
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
        "loop_ccs_threshold": loop_ccs_threshold,
        "loop_scr_threshold": loop_scr_threshold,
        "loop_odom_translation_gate_px": loop_odom_translation_gate,
        "loop_odom_yaw_gate_rad": loop_odom_yaw_gate,
        "final_anchor_translation_gate_px": final_anchor_translation_gate,
        "loop_edge_weight": loop_edge_weight,
        "coverage_keyframe_indices": coverage,
        "rejected_loop_details": rejected_loop_details,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/synthetic_tracking/loop_patch.npz")
    parser.add_argument("--output-dir", default="checkpoints/scaled_gelslam")
    parser.add_argument("--ccs-threshold", type=float, default=0.85)
    parser.add_argument("--scr-threshold", type=float, default=0.35)
    parser.add_argument("--loop-ccs-threshold", type=float, default=0.75)
    parser.add_argument("--loop-scr-threshold", type=float, default=0.12)
    parser.add_argument("--loop-odom-translation-gate", type=float, default=18.0)
    parser.add_argument("--loop-odom-yaw-gate", type=float, default=0.70)
    parser.add_argument("--final-anchor-translation-gate", type=float, default=32.0)
    parser.add_argument("--loop-edge-weight", type=int, default=1)
    args = parser.parse_args()
    run(
        Path(args.dataset),
        Path(args.output_dir),
        args.ccs_threshold,
        args.scr_threshold,
        args.loop_ccs_threshold,
        args.loop_scr_threshold,
        args.loop_odom_translation_gate,
        args.loop_odom_yaw_gate,
        args.final_anchor_translation_gate,
        args.loop_edge_weight,
    )


if __name__ == "__main__":
    main()
