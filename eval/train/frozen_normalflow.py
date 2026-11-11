"""Frozen copy of the NormalFlow frame-to-frame baseline owned by the evaluator.

Identical computation to baseline/normalflow_baseline.py; kept here so that
edits outside eval/ cannot change the baseline scored by this slice.
"""

from __future__ import annotations

import cv2
import numpy as np
from scipy.linalg import lstsq
from scipy.ndimage import binary_erosion
from scipy.spatial.transform import Rotation


class LoseTrackError(Exception):
    """NormalFlow could not find enough shared contact to estimate a pose."""


def erode_contact_mask(contact: np.ndarray) -> np.ndarray:
    size = max(contact.shape[0] // 48, 1)
    return binary_erosion(contact, structure=np.ones((size, size)))


def gxy2normal(gradients: np.ndarray) -> np.ndarray:
    ones = np.ones_like(gradients[:, :, :1], dtype=np.float32)
    normals = np.dstack([-gradients.astype(np.float32), ones])
    return (normals / np.linalg.norm(normals, axis=-1, keepdims=True)).astype(np.float32)


def gxy2laplacian(gradients: np.ndarray, contact: np.ndarray, ksize: int = 5) -> np.ndarray:
    """Curvature map: divergence of the gradient field, Gaussian filtered."""
    gx = gradients[:, :, 0].astype(np.float32)
    gy = gradients[:, :, 1].astype(np.float32)
    lap = np.gradient(gx, axis=1) + np.gradient(gy, axis=0)
    lap = cv2.GaussianBlur(lap.astype(np.float32), (ksize, ksize), 0)
    lap[np.logical_not(contact)] = 0.0
    return np.clip(lap, -0.7, 0.7).astype(np.float32)


def height2pointcloud(height: np.ndarray, mask: np.ndarray, mm_per_pixel: float) -> np.ndarray:
    rows, cols = np.nonzero(mask)
    xx = cols - height.shape[1] / 2 + 0.5
    yy = rows - height.shape[0] / 2 + 0.5
    return (np.vstack((xx, yy, height[rows, cols])).T * mm_per_pixel).astype(np.float32)


def wide_remap(image: np.ndarray, xx: np.ndarray, yy: np.ndarray, mode: int = cv2.INTER_LINEAR) -> np.ndarray:
    """Sample image at float pixel coordinates; returns (n,) or (n, channels)."""
    xx = np.ascontiguousarray(xx, dtype=np.float32).reshape(-1, 1)
    yy = np.ascontiguousarray(yy, dtype=np.float32).reshape(-1, 1)
    image = np.ascontiguousarray(image, dtype=np.float32)
    chunks = []
    for start in range(0, len(xx), 30000):
        stop = min(len(xx), start + 30000)
        out = cv2.remap(image, xx[start:stop], yy[start:stop], mode,
                        borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        chunks.append(out.reshape(stop - start, -1))
    if not chunks:
        channels = 1 if image.ndim == 2 else image.shape[2]
        return np.zeros((0,) if channels == 1 else (0, channels), dtype=np.float32)
    out = np.concatenate(chunks, axis=0)
    return out[:, 0] if image.ndim == 2 else out


def get_J(normals: np.ndarray, mask: np.ndarray, pointcloud: np.ndarray, mm_per_pixel: float) -> np.ndarray:
    """Jacobian of the normal residual w.r.t. (3 rotation, 2 translation) parameters."""
    dndx = cv2.Sobel(normals, cv2.CV_32F, 1, 0, ksize=5, scale=2 ** (-7))
    dndy = cv2.Sobel(normals, cv2.CV_32F, 0, 1, ksize=5, scale=2 ** (-7))
    yy, xx = np.nonzero(mask)
    jxx = dndx[:, :, 0][yy, xx] / mm_per_pixel
    jyx = dndx[:, :, 1][yy, xx] / mm_per_pixel
    jzx = dndx[:, :, 2][yy, xx] / mm_per_pixel
    jxy = dndy[:, :, 0][yy, xx] / mm_per_pixel
    jyy = dndy[:, :, 1][yy, xx] / mm_per_pixel
    jzy = dndy[:, :, 2][yy, xx] / mm_per_pixel
    n = pointcloud.shape[0]
    jn = np.stack([jxx, jxy, jyx, jyy, jzx, jzy], axis=-1).T.reshape(3, 2, -1).astype(np.float32)
    jx = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    jy = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 0.0], [-1.0, 0.0, 0.0]], dtype=np.float32)
    jz = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float32)
    proj = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    jw = np.concatenate(
        [
            (proj @ jx @ pointcloud.T).reshape(2, 1, -1),
            (proj @ jy @ pointcloud.T).reshape(2, 1, -1),
            (proj @ jz @ pointcloud.T).reshape(2, 1, -1),
            np.tile(proj[:, :-1, np.newaxis], (1, 1, n)),
        ],
        axis=1,
    )
    jnw = np.matmul(jn.transpose(2, 0, 1), jw.transpose(2, 0, 1)).transpose(1, 2, 0)
    jr = np.zeros((3, 5, n), dtype=np.float32)
    jr[0, 1] = normals[yy, xx, 2]
    jr[0, 2] = -normals[yy, xx, 1]
    jr[1, 0] = -normals[yy, xx, 2]
    jr[1, 2] = normals[yy, xx, 0]
    jr[2, 0] = normals[yy, xx, 1]
    jr[2, 1] = -normals[yy, xx, 0]
    return jnw - jr


def _project(points: np.ndarray, shape: tuple[int, int], mm_per_pixel: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    h, w = shape
    xx = points[:, 0] / mm_per_pixel + w / 2 - 0.5
    yy = points[:, 1] / mm_per_pixel + h / 2 - 0.5
    inside = (xx >= 0) & (xx < w) & (yy >= 0) & (yy < h)
    return xx.astype(np.float32), yy.astype(np.float32), inside


def normalflow(
    n_ref: np.ndarray,
    c_ref: np.ndarray,
    h_ref: np.ndarray,
    l_ref: np.ndarray,
    n_tar: np.ndarray,
    c_tar: np.ndarray,
    h_tar: np.ndarray,
    l_tar: np.ndarray,
    tar_T_ref_init: np.ndarray,
    mm_per_pixel: float,
    n_samples: int = 3000,
    max_iters: int = 50,
) -> tuple[np.ndarray, float, float]:
    """Estimate tar_T_ref (4x4, mm). Returns (transform, ccs, scr).

    Raises LoseTrackError when fewer than 10 sampled pixels share contact.
    The caller applies the CCS/SCR thresholds (failure detection).
    """
    abs_l = np.abs(l_ref).ravel()
    n_pick = int(min(n_samples, abs_l.size))
    l_threshold = np.partition(abs_l, -n_pick)[-n_pick] + 1e-6
    m_ref = np.abs(l_ref) >= l_threshold
    if int(m_ref.sum()) < 10:
        raise LoseTrackError()
    pointcloud = height2pointcloud(h_ref, m_ref, mm_per_pixel)
    masked_n_ref = n_ref[m_ref]
    masked_c_ref = c_ref[m_ref]
    masked_l_ref = l_ref[m_ref]
    jac = np.transpose(get_J(n_ref, m_ref, pointcloud, mm_per_pixel), (2, 0, 1))
    c_tar_f = c_tar.astype(np.float32)
    shape = c_ref.shape

    tar_T_ref = np.asarray(tar_T_ref_init, dtype=np.float64).copy()
    for it in range(max_iters):
        remapped = pointcloud @ tar_T_ref[:3, :3].T + tar_T_ref[:3, 3]
        xx, yy, inside = _project(remapped, shape, mm_per_pixel)
        shared = (wide_remap(c_tar_f, xx, yy, cv2.INTER_NEAREST) > 0.5) & inside
        if int(shared.sum()) < 10:
            raise LoseTrackError()
        remapped_n_tar = wide_remap(n_tar, xx, yy)
        b = (remapped_n_tar @ np.linalg.inv(tar_T_ref[:3, :3]).T - masked_n_ref)[shared].reshape(-1)
        a = jac[shared].reshape(-1, 5)
        dp = lstsq(a, b, lapack_driver="gelsy")[0]
        d_t = np.eye(4)
        d_t[:3, :3] = Rotation.from_euler("xyz", dp[:3], degrees=False).as_matrix()
        d_t[:2, 3] = dp[3:]
        tar_T_ref = tar_T_ref @ np.linalg.inv(d_t)
        tar_T_ref[2, 3] = 0.0
        if np.linalg.norm(dp[:3]) < 1e-4 and np.linalg.norm(dp[3:]) < 1e-2 and it > 5:
            break

    # z translation from the mean height difference over the shared contact.
    remapped = pointcloud @ tar_T_ref[:3, :3].T + tar_T_ref[:3, 3]
    xx, yy, inside = _project(remapped, shape, mm_per_pixel)
    shared = (wide_remap(c_tar_f, xx, yy, cv2.INTER_NEAREST) > 0.5) & inside
    if int(shared.sum()) < 10:
        raise LoseTrackError()
    remapped_h_tar = wide_remap(h_tar, xx, yy)
    tar_T_ref[2, 3] = float(np.mean(remapped_h_tar[shared] * mm_per_pixel - remapped[shared, 2]))

    # Failure-detection scores (Section IV-A2).
    remapped = pointcloud @ tar_T_ref[:3, :3].T + tar_T_ref[:3, 3]
    xx, yy, inside = _project(remapped, shape, mm_per_pixel)
    l_tar_backproj = wide_remap(l_tar, xx, yy)
    c_tar_backproj = (wide_remap(c_tar_f, xx, yy) > 0.5) & inside
    c_shared = masked_c_ref & c_tar_backproj
    denom = float(np.sum(np.abs(masked_l_ref)))
    scr = float(np.sum(np.abs(masked_l_ref[c_shared])) / denom) if denom > 0 else 0.0
    a_vec = masked_l_ref[c_shared].astype(np.float64)
    b_vec = l_tar_backproj[c_shared].astype(np.float64)
    na = float(np.linalg.norm(a_vec))
    nb = float(np.linalg.norm(b_vec))
    ccs = float(a_vec @ b_vec / (na * nb)) if na > 0 and nb > 0 else -1.0
    if not np.isfinite(tar_T_ref).all():
        raise LoseTrackError()
    return tar_T_ref, ccs, scr


class TactileFrame:
    """Geometric properties {N, L, H, C} of one tactile observation."""

    def __init__(self, gradients: np.ndarray, height: np.ndarray, contact: np.ndarray,
                 mm_per_pixel: float, contact_threshold: int = 125, laplacian_ksize: int = 5):
        self.C = erode_contact_mask(contact.astype(bool))
        self.G = gradients.astype(np.float32)
        self.H = height.astype(np.float32)
        self.N = gxy2normal(self.G)
        self.L = gxy2laplacian(self.G, self.C, laplacian_ksize)
        self.mm_per_pixel = float(mm_per_pixel)
        self.in_contact = int(self.C.sum()) >= contact_threshold


def register(ref: TactileFrame, tar: TactileFrame, tar_T_ref_init: np.ndarray, n_samples: int = 3000) -> tuple[np.ndarray, float, float]:
    return normalflow(ref.N, ref.C, ref.H, ref.L, tar.N, tar.C, tar.H, tar.L,
                      tar_T_ref_init, ref.mm_per_pixel, n_samples=n_samples)


def _inverse(transform: np.ndarray) -> np.ndarray:
    out = np.eye(4)
    out[:3, :3] = transform[:3, :3].T
    out[:3, 3] = -transform[:3, :3].T @ transform[:3, 3]
    return out


def track_frame_to_frame(gradients: np.ndarray, heights: np.ndarray, contacts: np.ndarray,
                         mm_per_pixel: float, n_samples: int = 3000) -> np.ndarray:
    """NF baseline of Table IV: frame-to-frame NormalFlow, no keyframes, no loop closure.

    Each frame is registered to the previous frame (identity initialisation)
    and the relative motions are composed. There is no failure detection; if
    NormalFlow finds no shared contact the motion is taken as identity.
    """
    n = len(gradients)
    poses = np.zeros((n, 4, 4))
    poses[0] = np.eye(4)
    prev = TactileFrame(gradients[0], heights[0], contacts[0], mm_per_pixel)
    for i in range(1, n):
        cur = TactileFrame(gradients[i], heights[i], contacts[i], mm_per_pixel)
        try:
            cur_T_prev, _, _ = register(prev, cur, np.eye(4), n_samples)
        except LoseTrackError:
            cur_T_prev = np.eye(4)
        poses[i] = poses[i - 1] @ _inverse(cur_T_prev)
        prev = cur
    return poses
