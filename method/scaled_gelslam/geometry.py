from __future__ import annotations

import math

import numpy as np


def compose(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ca, sa = math.cos(a[2]), math.sin(a[2])
    x = a[0] + ca * b[0] - sa * b[1]
    y = a[1] + sa * b[0] + ca * b[1]
    return np.array([x, y, wrap(a[2] + b[2])], dtype=np.float64)


def invert(a: np.ndarray) -> np.ndarray:
    c, s = math.cos(a[2]), math.sin(a[2])
    return np.array([-c * a[0] - s * a[1], s * a[0] - c * a[1], wrap(-a[2])], dtype=np.float64)


def between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return compose(invert(a), b)


def wrap(theta: float) -> float:
    return (theta + math.pi) % (2.0 * math.pi) - math.pi


def warp_coords(shape: tuple[int, int], transform: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0
    x = xx - cx
    y = yy - cy
    c, s = np.cos(transform[2]), np.sin(transform[2])
    # Target sampled into reference coordinates. Positive transform means target
    # pose relative to reference; inverse warp samples target at corresponding px.
    xs = c * x + s * y - transform[0] + cx
    ys = -s * x + c * y - transform[1] + cy
    return xs, ys


def bilinear_image(image: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h, w = image.shape[:2]
    x0 = np.floor(xs).astype(np.int64)
    y0 = np.floor(ys).astype(np.int64)
    x1 = x0 + 1
    y1 = y0 + 1
    valid = (x0 >= 0) & (y0 >= 0) & (x1 < w) & (y1 < h)
    x0c = np.clip(x0, 0, w - 1)
    x1c = np.clip(x1, 0, w - 1)
    y0c = np.clip(y0, 0, h - 1)
    y1c = np.clip(y1, 0, h - 1)
    wa = (x1 - xs) * (y1 - ys)
    wb = (x1 - xs) * (ys - y0)
    wc = (xs - x0) * (y1 - ys)
    wd = (xs - x0) * (ys - y0)
    if image.ndim == 2:
        out = np.zeros(xs.shape, dtype=np.float64)
    else:
        out = np.zeros(xs.shape + (image.shape[-1],), dtype=np.float64)
        wa, wb, wc, wd = wa[..., None], wb[..., None], wc[..., None], wd[..., None]
    out[valid] = (
        wa[valid] * image[y0c[valid], x0c[valid]]
        + wb[valid] * image[y1c[valid], x0c[valid]]
        + wc[valid] * image[y0c[valid], x1c[valid]]
        + wd[valid] * image[y1c[valid], x1c[valid]]
    )
    return out, valid


def se2_to_matrix(pose: np.ndarray) -> np.ndarray:
    c, s = np.cos(pose[2]), np.sin(pose[2])
    mat = np.eye(4, dtype=float)
    mat[0, 0] = c
    mat[0, 1] = -s
    mat[1, 0] = s
    mat[1, 1] = c
    mat[0, 3] = pose[0]
    mat[1, 3] = pose[1]
    return mat
