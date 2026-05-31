from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation


def as_se3(pose: np.ndarray) -> np.ndarray:
    pose = np.asarray(pose, dtype=np.float64)
    if pose.shape == (6,):
        return pose.copy()
    if pose.shape == (3,):
        return np.array([pose[0], pose[1], 0.0, 0.0, 0.0, pose[2]], dtype=np.float64)
    raise ValueError(f"Expected 3D SE(2) or 6D SE(3) vector, got shape {pose.shape}")


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


def between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return compose(invert(a), b)


def se3_error(measured: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    return pose_from_matrix(np.linalg.inv(matrix_from_pose(measured)) @ matrix_from_pose(predicted))


def transform_points(points: np.ndarray, pose: np.ndarray) -> np.ndarray:
    pose = as_se3(pose)
    rot = Rotation.from_rotvec(pose[3:]).as_matrix()
    return points @ rot.T + pose[:3]


def rotate_vectors(vectors: np.ndarray, pose: np.ndarray) -> np.ndarray:
    return Rotation.from_rotvec(as_se3(pose)[3:]).apply(vectors)


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
