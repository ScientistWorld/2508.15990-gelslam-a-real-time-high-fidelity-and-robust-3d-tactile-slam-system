from __future__ import annotations

import cv2
import numpy as np
from scipy.optimize import least_squares

from .geometry import as_se3, bilinear_image, invert, rotate_vectors, transform_points


def geometric_properties(height: np.ndarray, mask: np.ndarray | None = None) -> dict:
    """Compute the tactile geometry tuple used by GelSLAM from a height map.

    The real system obtains normals from GelSight RGB images through
    photometric stereo and then integrates/derives the remaining fields. The
    scaled benchmark starts from synthetic height maps, so this function is the
    equivalent geometry stage for the available observations.
    """
    height = height.astype(np.float64)
    gy, gx = np.gradient(height)
    denom = np.sqrt(gx * gx + gy * gy + 1.0)
    normal = np.stack([-gx / denom, -gy / denom, np.ones_like(height) / denom], axis=-1)
    curvature = np.abs(np.gradient(gx, axis=1) + np.gradient(gy, axis=0))
    curvature = curvature / (np.percentile(curvature, 98) + 1e-8)
    if mask is None:
        mask = np.ones_like(height, dtype=bool)
    return {
        "height": height,
        "normal": normal,
        "curvature": np.clip(curvature, 0.0, 1.0),
        "mask": mask.astype(bool),
    }


def _surface_points(height: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    h, w = height.shape
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0
    z = height[ys, xs]
    return np.column_stack([xs.astype(np.float64) - cx, ys.astype(np.float64) - cy, z])


def _project(points: np.ndarray, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    h, w = shape
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0
    return points[:, 0] + cx, points[:, 1] + cy


def quality(
    ref_height: np.ndarray,
    ref_curv: np.ndarray,
    tgt_curv: np.ndarray,
    ref_mask: np.ndarray,
    tgt_mask: np.ndarray,
    transform: np.ndarray,
) -> tuple[float, float]:
    ys, xs = np.nonzero(ref_mask)
    points = _surface_points(ref_height, xs, ys)
    # The optimized measurement composes keyframe poses as T_target = T_ref * T.
    # Warping reference-frame samples into the target image needs the inverse
    # local-coordinate transform: p_target = T_target^-1 T_ref p_ref.
    warped = transform_points(points, invert(transform))
    sample_x, sample_y = _project(warped, ref_curv.shape)
    warped_curv, valid = bilinear_image(tgt_curv, sample_x, sample_y)
    warped_mask_f, _ = bilinear_image(tgt_mask.astype(float), sample_x, sample_y)
    shared = valid & (warped_mask_f > 0.5)
    if shared.sum() < 16:
        return 0.0, 0.0
    a = ref_curv[ys[shared], xs[shared]].reshape(-1)
    b = warped_curv[shared].reshape(-1)
    ccs = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
    scr = float(a.sum() / (ref_curv[ref_mask].sum() + 1e-9))
    return ccs, scr


def estimate_relative(ref: dict, tgt: dict, init: np.ndarray | None = None, max_pixels: int = 900) -> tuple[np.ndarray, float, float, float]:
    """Estimate the SE(3) transform from a reference tactile frame to a target.

    This is a scaled implementation of GelSLAM's NormalFlow objective: surface
    points q=[u,v,H(u,v)] from the reference contact are warped by an SE(3)
    candidate, projected into the target frame, and the target normal at the
    warped location is matched against the rotated reference normal.
    """
    if init is None:
        init = np.zeros(6, dtype=np.float64)
    init = as_se3(init)
    ref_curv = ref["curvature"]
    ref_mask = ref["mask"]
    ys, xs = np.nonzero(ref_mask)
    scores = ref_curv[ys, xs]
    if len(scores) > max_pixels:
        keep = np.argpartition(scores, -max_pixels)[-max_pixels:]
        ys = ys[keep]
        xs = xs[keep]

    ref_points = _surface_points(ref["height"], xs, ys)
    ref_normals = ref["normal"][ys, xs]

    def residual(delta: np.ndarray) -> np.ndarray:
        pose = as_se3(delta)
        warp_pose = invert(pose)
        warped_points = transform_points(ref_points, warp_pose)
        sample_x, sample_y = _project(warped_points, ref_curv.shape)
        target_normals, valid = bilinear_image(tgt["normal"], sample_x, sample_y)
        target_heights, height_valid = bilinear_image(tgt["height"], sample_x, sample_y)
        mask_values, _ = bilinear_image(tgt["mask"].astype(float), sample_x, sample_y)
        ok = valid & height_valid & (mask_values > 0.5)
        rotated_ref = rotate_vectors(ref_normals, warp_pose)
        normal_res = np.zeros((len(xs), 3), dtype=np.float64)
        normal_res[ok] = target_normals[ok] - rotated_ref[ok]
        normal_res[~ok] = 0.35
        height_res = np.zeros(len(xs), dtype=np.float64)
        # Keep the baseline objective matched to the method objective: the
        # warped reference surface should agree with both target normals and
        # target height values in the local tactile frame.
        height_res[ok] = (warped_points[ok, 2] - target_heights[ok]) / 0.5
        height_res[~ok] = 0.35
        return np.concatenate([normal_res.reshape(-1), height_res])

    guesses = [init]
    try:
        shift, _ = cv2.phaseCorrelate(ref_curv.astype(np.float32), tgt["curvature"].astype(np.float32))
        guesses.append(invert(np.array([shift[0], shift[1], init[2], init[3], init[4], init[5]], dtype=np.float64)))
    except cv2.error:
        pass
    try:
        warp = np.array(
            [[np.cos(init[5]), -np.sin(init[5]), init[0]], [np.sin(init[5]), np.cos(init[5]), init[1]]],
            dtype=np.float32,
        )
        _, warp = cv2.findTransformECC(
            ref_curv.astype(np.float32),
            tgt["curvature"].astype(np.float32),
            warp,
            cv2.MOTION_EUCLIDEAN,
            (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5),
        )
        rz = float(np.arctan2(warp[1, 0], warp[0, 0]))
        guesses.append(invert(np.array([warp[0, 2], warp[1, 2], init[2], init[3], init[4], rz], dtype=np.float64)))
    except cv2.error:
        pass

    best = None
    for guess in guesses:
        guess = as_se3(guess)
        for pose, cost in [(guess, float(np.sum(residual(guess) ** 2))), (None, None)]:
            if pose is None:
                opt = least_squares(
                    residual,
                    guess,
                    method="lm",
                    max_nfev=45,
                    x_scale=np.array([4.0, 4.0, 1.0, 0.08, 0.08, 0.15]),
                )
                pose = as_se3(opt.x)
                cost = float(opt.cost)
            ccs, scr = quality(ref["height"], ref_curv, tgt["curvature"], ref_mask, tgt["mask"], pose)
            rank = (ccs + 0.4 * scr, -float(cost))
            if best is None or rank > best[0]:
                best = (rank, pose, ccs, scr, float(cost))
    assert best is not None
    return best[1], best[2], best[3], best[4]
