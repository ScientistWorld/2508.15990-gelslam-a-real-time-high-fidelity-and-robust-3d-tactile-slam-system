from __future__ import annotations

import numpy as np
import cv2
from scipy.optimize import least_squares

from .geometry import bilinear_image, warp_coords


def quality(ref_curv: np.ndarray, tgt_curv: np.ndarray, ref_mask: np.ndarray, tgt_mask: np.ndarray, transform: np.ndarray) -> tuple[float, float]:
    xs, ys = warp_coords(ref_curv.shape, transform)
    warped_curv, valid = bilinear_image(tgt_curv, xs, ys)
    warped_mask_f, _ = bilinear_image(tgt_mask.astype(float), xs, ys)
    shared = ref_mask & valid & (warped_mask_f > 0.5)
    if shared.sum() < 16:
        return 0.0, 0.0
    a = ref_curv[shared].reshape(-1)
    b = warped_curv[shared].reshape(-1)
    ccs = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
    scr = float(ref_curv[shared].sum() / (ref_curv[ref_mask].sum() + 1e-9))
    return ccs, scr


def estimate_relative(ref: dict, tgt: dict, init: np.ndarray | None = None, max_pixels: int = 700) -> tuple[np.ndarray, float, float, float]:
    if init is None:
        init = np.zeros(3, dtype=np.float64)
    ref_curv = ref["curvature"]
    ref_mask = ref["mask"]
    ys, xs = np.nonzero(ref_mask)
    scores = ref_curv[ys, xs]
    if len(scores) > max_pixels:
        keep = np.argpartition(scores, -max_pixels)[-max_pixels:]
        ys = ys[keep]
        xs = xs[keep]
    ref_normals = ref["normal"][ys, xs]
    ref_curv_samples = ref_curv[ys, xs]

    def residual(delta: np.ndarray) -> np.ndarray:
        full = np.asarray(delta, dtype=np.float64)
        grid_xs, grid_ys = warp_coords(ref_curv.shape, full)
        sample_x = grid_xs[ys, xs]
        sample_y = grid_ys[ys, xs]
        warped, valid = bilinear_image(tgt["normal"], sample_x, sample_y)
        mask_values, _ = bilinear_image(tgt["mask"].astype(float), sample_x, sample_y)
        ok = valid & (mask_values > 0.5)
        warped_curv, _ = bilinear_image(tgt["curvature"], sample_x, sample_y)
        res = np.zeros((len(xs), 4), dtype=np.float64)
        res[ok, :3] = warped[ok] - ref_normals[ok]
        res[ok, 3] = 0.75 * (warped_curv[ok] - ref_curv_samples[ok])
        res[~ok] = 0.35
        return res.reshape(-1)

    guesses = [np.asarray(init, dtype=np.float64)]
    try:
        shift, _ = cv2.phaseCorrelate(ref_curv.astype(np.float32), tgt["curvature"].astype(np.float32))
        guesses.append(np.array([shift[0], shift[1], init[2]], dtype=np.float64))
    except cv2.error:
        pass
    try:
        warp = np.array(
            [[np.cos(init[2]), -np.sin(init[2]), init[0]], [np.sin(init[2]), np.cos(init[2]), init[1]]],
            dtype=np.float32,
        )
        _, warp = cv2.findTransformECC(
            ref_curv.astype(np.float32),
            tgt["curvature"].astype(np.float32),
            warp,
            cv2.MOTION_EUCLIDEAN,
            (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5),
        )
        theta = float(np.arctan2(warp[1, 0], warp[0, 0]))
        guesses.append(np.array([warp[0, 2], warp[1, 2], theta], dtype=np.float64))
        guesses.append(np.array([-warp[0, 2], -warp[1, 2], -theta], dtype=np.float64))
    except cv2.error:
        pass

    best = None
    for guess in guesses:
        for pose, cost in [(guess, float(np.sum(residual(guess) ** 2))), (None, None)]:
            if pose is None:
                opt = least_squares(residual, guess, method="trf", max_nfev=35, x_scale=np.array([4.0, 4.0, 0.15]))
                pose = opt.x.astype(np.float64)
                cost = float(opt.cost)
            ccs, scr = quality(ref_curv, tgt["curvature"], ref_mask, tgt["mask"], pose)
            rank = (ccs + 0.4 * scr, -float(cost))
            if best is None or rank > best[0]:
                best = (rank, pose, ccs, scr, float(cost))
    assert best is not None
    return best[1], best[2], best[3], best[4]
