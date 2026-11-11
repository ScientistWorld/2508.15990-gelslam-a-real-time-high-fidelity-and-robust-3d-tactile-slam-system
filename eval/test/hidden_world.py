#!/usr/bin/env python3
"""Synthetic GelSight-Mini-style tactile episodes with known 6DoF ground truth.

Scaled stand-in for the paper's long-horizon tracking dataset (Section V-A):
a sensor slides over a textured object surface, keeps continuous contact and
revisits previously touched regions. Each episode belongs to one of four
texture families ("objects"): seed (dense bumps), fabric (near-periodic
weave), wood (low-texture grain) and rock (multi-scale roughness). Contact-loss
episodes follow the paper's relocalisation study (Section V-E): after every
100 kept frames, 25 frames are removed from the stream.

Observation model (Section III-C): the gel is indented by the object surface,
the photometric-stereo stage returns noisy surface gradients (iid noise plus a
fixed per-sensor calibration bias), the height map is obtained by integrating
those gradients with a fast Poisson solver, and the contact mask is the region
where the indentation is visible. Gradient errors combine a sensor-fixed
smooth calibration bias, a sensor-fixed fine pattern, a per-frame smooth gel
distortion and per-pixel noise. Units: pixels on the 160x120 sensor grid
(0.1268 mm per pixel, i.e. a 20.3 x 15.2 mm GelSight Mini resized by 1/2);
ground-truth poses are returned in millimetres.

This file is the public (training-side) simulator. Episode configurations for
training are listed in data/train_episodes.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.fft import dstn, idstn
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation

SENSOR_H = 120
SENSOR_W = 160
MM_PER_PIXEL = 0.1268
WORLD_SIZE = 640
FAMILIES = ("seed", "fabric", "wood", "rock")
CONTACT_THRESHOLD_PX = 0.15
GEL_BLUR_SIGMA = 1.0
GRADIENT_NOISE = 0.02      # per-frame iid photometric-stereo noise
GRADIENT_BIAS = 0.010      # smooth sensor-fixed calibration error
FIXED_PATTERN = 0.03       # fine sensor-fixed pattern (gel texture, illumination residuals)
GEL_WARP = 0.02            # per-frame smooth gel distortion
KEEP_BLOCK = 100
DROP_BLOCK = 25


# --------------------------------------------------------------------------
# Object surfaces
# --------------------------------------------------------------------------

def _unit(field: np.ndarray) -> np.ndarray:
    field = field - field.mean()
    return field / (field.std() + 1e-12)


def _sparse_blobs(rng: np.random.Generator, n: int, density: float, sigma: float) -> np.ndarray:
    count = int(density * n * n)
    field = np.zeros((n, n))
    np.add.at(field, (rng.integers(0, n, count), rng.integers(0, n, count)), rng.normal(0.0, 1.0, count))
    return _unit(ndimage.gaussian_filter(field, sigma))


def make_texture(family: str, rng: np.random.Generator, n: int) -> np.ndarray:
    """Zero-mean surface texture in pixel units for one object family."""
    if family == "seed":
        white = rng.standard_normal((n, n))
        fine = _unit(ndimage.gaussian_filter(white, 1.5) - ndimage.gaussian_filter(white, 4.0))
        bumps = _sparse_blobs(rng, n, 0.004, 2.5)
        return 0.35 * fine + 0.45 * bumps
    if family == "fabric":
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
        angle = rng.uniform(0.0, np.pi)
        lam1 = rng.uniform(7.0, 10.0)
        lam2 = rng.uniform(9.0, 13.0)
        phase1 = 2.0 * _unit(ndimage.gaussian_filter(rng.standard_normal((n, n)), 25.0))
        phase2 = 2.0 * _unit(ndimage.gaussian_filter(rng.standard_normal((n, n)), 25.0))
        a = xx * np.cos(angle) + yy * np.sin(angle)
        b = -xx * np.sin(angle) + yy * np.cos(angle)
        weave = np.sin(2 * np.pi * a / lam1 + phase1) * (0.6 + 0.4 * np.sin(2 * np.pi * b / lam2 + phase2))
        noise = _unit(ndimage.gaussian_filter(rng.standard_normal((n, n)), 2.0))
        return 0.4 * weave + 0.12 * noise
    if family == "wood":
        grain = ndimage.gaussian_filter(rng.standard_normal((n, n)), (10.0, 1.6))
        grain = _unit(ndimage.rotate(grain, rng.uniform(0.0, 180.0), reshape=False, mode="reflect"))
        knots = _sparse_blobs(rng, n, 0.0004, 4.0)
        return 0.4 * grain + 0.2 * knots
    if family == "rock":
        total = np.zeros((n, n))
        for sigma in (1.5, 3.0, 6.0, 12.0):
            total += (sigma / 1.5) ** 0.6 * _unit(ndimage.gaussian_filter(rng.standard_normal((n, n)), sigma))
        return 0.55 * _unit(total)
    raise ValueError(f"unknown family {family!r}")


class TactileObject:
    """Height field S(x, y) of a convex textured object, in world pixels."""

    def __init__(self, family: str, seed: int, size: int = WORLD_SIZE):
        rng = np.random.default_rng(seed)
        self.family = family
        self.size = size
        self.center = np.array([size / 2.0, size / 2.0])
        self.radius = rng.uniform(180.0, 320.0)
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
        cap = -((xx - self.center[0]) ** 2 + (yy - self.center[1]) ** 2) / (2.0 * self.radius)
        bend = 2.5 * _unit(ndimage.gaussian_filter(rng.standard_normal((size, size)), 60.0))
        self.surface = cap + bend + make_texture(family, rng, size)
        smooth = ndimage.gaussian_filter(cap + bend, 20.0)
        self.smooth_gy, self.smooth_gx = np.gradient(smooth)

    def sample(self, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        """Bilinear interpolation of the height field (clamped at the border)."""
        x = np.clip(xs, 0.0, self.size - 1.001)
        y = np.clip(ys, 0.0, self.size - 1.001)
        x0 = x.astype(np.int64)
        y0 = y.astype(np.int64)
        fx = x - x0
        fy = y - y0
        s = self.surface
        return (s[y0, x0] * (1 - fx) * (1 - fy) + s[y0, x0 + 1] * fx * (1 - fy)
                + s[y0 + 1, x0] * (1 - fx) * fy + s[y0 + 1, x0 + 1] * fx * fy)

    def macro_normal(self, x: float, y: float) -> np.ndarray:
        gx = ndimage.map_coordinates(self.smooth_gx, [[y], [x]], order=1, mode="nearest")[0]
        gy = ndimage.map_coordinates(self.smooth_gy, [[y], [x]], order=1, mode="nearest")[0]
        normal = np.array([-gx, -gy, 1.0])
        return normal / np.linalg.norm(normal)


# --------------------------------------------------------------------------
# Trajectories
# --------------------------------------------------------------------------

def smooth_noise(rng: np.random.Generator, n: int, corr: float) -> np.ndarray:
    pad = int(4 * corr) + 1
    values = ndimage.gaussian_filter1d(rng.standard_normal(n + 2 * pad), corr)[pad:pad + n]
    return values / (values.std() + 1e-12)


def _align_z(normal: np.ndarray) -> Rotation:
    z = np.array([0.0, 0.0, 1.0])
    axis = np.cross(z, normal)
    s = np.linalg.norm(axis)
    if s < 1e-12:
        return Rotation.identity()
    angle = np.arctan2(s, float(z @ normal))
    return Rotation.from_rotvec(axis / s * angle)


def episode_parameters(seed: int) -> dict:
    rng = np.random.default_rng(seed + 7919)
    return {
        "speed_px": float(rng.uniform(1.5, 2.2)),
        "area_radius_px": float(rng.uniform(75.0, 105.0)),
        "yaw_amplitude_deg": float(rng.uniform(30.0, 50.0)),
        "depth_px": float(rng.uniform(5.0, 7.0)),
    }


def make_trajectory(obj: TactileObject, seed: int, n_frames: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return sensor rotations (n,3,3), in-plane positions (n,2) and press depths (n,)."""
    params = episode_parameters(seed)
    rng = np.random.default_rng(seed + 104729)
    speed = params["speed_px"]
    area = params["area_radius_px"]
    speeds = speed * np.clip(1.0 + 0.35 * smooth_noise(rng, n_frames, 30.0), 0.4, 1.8)
    arc_needed = float(np.sum(speeds)) + 10.0
    points = [obj.center.copy()]
    length = 0.0
    while length < 1.6 * arc_needed:
        for _ in range(50):
            rad = area * np.sqrt(rng.uniform())
            ang = rng.uniform(0.0, 2 * np.pi)
            cand = obj.center + rad * np.array([np.cos(ang), np.sin(ang)])
            if np.linalg.norm(cand - points[-1]) > 35.0:
                break
        length += float(np.linalg.norm(cand - points[-1]))
        points.append(cand)
    points = np.asarray(points)
    chord = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])
    spline = CubicSpline(chord, points, bc_type="natural")
    dense_s = np.linspace(0.0, chord[-1], 40000)
    dense = spline(dense_s)
    dense_arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))])
    arc = np.concatenate([[0.0], np.cumsum(speeds[1:])])
    s_at = np.interp(arc, dense_arc, dense_s)
    xy = spline(s_at)

    yaw = np.deg2rad(params["yaw_amplitude_deg"]) * smooth_noise(rng, n_frames, 45.0)
    tilt_x = np.deg2rad(1.0) * smooth_noise(rng, n_frames, 40.0)
    tilt_y = np.deg2rad(1.0) * smooth_noise(rng, n_frames, 40.0)
    depth = np.clip(params["depth_px"] * (1.0 + 0.15 * smooth_noise(rng, n_frames, 35.0)), 3.5, 8.5)
    rotations = np.zeros((n_frames, 3, 3))
    for i in range(n_frames):
        align = _align_z(obj.macro_normal(xy[i, 0], xy[i, 1]))
        local = Rotation.from_euler("zxy", [yaw[i], tilt_x[i], tilt_y[i]])
        rotations[i] = (align * local).as_matrix()
    return rotations, xy, depth


# --------------------------------------------------------------------------
# Sensor model
# --------------------------------------------------------------------------

def poisson_integrate(gx: np.ndarray, gy: np.ndarray) -> np.ndarray:
    """Fast Poisson solver (zero Dirichlet boundary) for heights from gradients."""
    h, w = gx.shape
    div = np.zeros((h, w))
    div[:, 1:] += gx[:, 1:] - gx[:, :-1]
    div[1:, :] += gy[1:, :] - gy[:-1, :]
    interior = div[1:-1, 1:-1]
    ky = np.arange(1, h - 1)
    kx = np.arange(1, w - 1)
    denom = (2 * np.cos(np.pi * ky / (h - 1)) - 2)[:, None] + (2 * np.cos(np.pi * kx / (w - 1)) - 2)[None, :]
    solution = idstn(dstn(interior, type=1) / denom, type=1)
    out = np.zeros((h, w))
    out[1:-1, 1:-1] = solution
    return out


def _local_grid() -> tuple[np.ndarray, np.ndarray]:
    rows, cols = np.mgrid[0:SENSOR_H, 0:SENSOR_W].astype(np.float64)
    return cols - (SENSOR_W - 1) / 2.0, rows - (SENSOR_H - 1) / 2.0


def render_contact(obj: TactileObject, rot: np.ndarray, xy: np.ndarray, depth: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (local surface height map in px, world_T_sensor translation in px)."""
    u, v = _local_grid()
    t = np.array([xy[0], xy[1], float(obj.sample(np.array([xy[0]]), np.array([xy[1]]))[0])])
    z = np.zeros_like(u)
    for _ in range(7):
        wx = t[0] + rot[0, 0] * u + rot[0, 1] * v + rot[0, 2] * z
        wy = t[1] + rot[1, 0] * u + rot[1, 1] * v + rot[1, 2] * z
        s = obj.sample(wx, wy)
        z = (s - t[2] - rot[2, 0] * u - rot[2, 1] * v) / rot[2, 2]
    shift = float(z.max()) - depth
    t = t + shift * rot[:, 2]
    return z - shift, t


def sensor_pattern(rng: np.random.Generator) -> np.ndarray:
    """Sensor-fixed gradient errors: smooth calibration bias plus a fine fixed pattern."""
    smooth = np.stack([_unit(ndimage.gaussian_filter(rng.standard_normal((SENSOR_H, SENSOR_W)), 20.0))
                       for _ in range(2)], axis=-1)
    fine = np.stack([_unit(ndimage.gaussian_filter(rng.standard_normal((SENSOR_H, SENSOR_W)), 2.0))
                     for _ in range(2)], axis=-1)
    return GRADIENT_BIAS * smooth + FIXED_PATTERN * fine


def observe(local_height: np.ndarray, rng: np.random.Generator, pattern: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    indentation = ndimage.gaussian_filter(np.maximum(local_height, 0.0), GEL_BLUR_SIGMA)
    contact = indentation > CONTACT_THRESHOLD_PX
    gy, gx = np.gradient(indentation)
    gradients = np.stack([gx, gy], axis=-1)
    warp = np.stack([_unit(ndimage.gaussian_filter(rng.standard_normal((SENSOR_H, SENSOR_W)), 6.0))
                     for _ in range(2)], axis=-1)
    gradients = gradients + pattern + GEL_WARP * warp + GRADIENT_NOISE * rng.standard_normal(gradients.shape)
    heights = poisson_integrate(gradients[:, :, 0], gradients[:, :, 1])
    return gradients.astype(np.float32), heights.astype(np.float32), contact


def kept_frame_indices(n_kept: int, contact_loss: bool) -> np.ndarray:
    if not contact_loss:
        return np.arange(n_kept)
    kept = []
    i = 0
    while len(kept) < n_kept:
        if (i % (KEEP_BLOCK + DROP_BLOCK)) < KEEP_BLOCK:
            kept.append(i)
        i += 1
    return np.asarray(kept)


def render_episode(family: str, seed: int, n_frames: int = 400, contact_loss: bool = False) -> dict:
    """Render one episode. Returns observations, ground truth (mm) and metadata."""
    obj = TactileObject(family, seed)
    kept = kept_frame_indices(n_frames, contact_loss)
    n_raw = int(kept[-1]) + 1
    rotations, xy, depth = make_trajectory(obj, seed, n_raw)
    noise_rng = np.random.default_rng(seed + 15485863)
    pattern = sensor_pattern(noise_rng)
    gradients = np.zeros((n_frames, SENSOR_H, SENSOR_W, 2), dtype=np.float32)
    heights = np.zeros((n_frames, SENSOR_H, SENSOR_W), dtype=np.float32)
    contacts = np.zeros((n_frames, SENSOR_H, SENSOR_W), dtype=bool)
    poses = np.zeros((n_frames, 4, 4))
    for out_idx, raw_idx in enumerate(kept):
        local, t = render_contact(obj, rotations[raw_idx], xy[raw_idx], depth[raw_idx])
        g, h, c = observe(local, noise_rng, pattern)
        gradients[out_idx], heights[out_idx], contacts[out_idx] = g, h, c
        poses[out_idx] = np.eye(4)
        poses[out_idx, :3, :3] = rotations[raw_idx]
        poses[out_idx, :3, 3] = t * MM_PER_PIXEL
    return {
        "gradients": gradients,
        "heights": heights,
        "contact_masks": contacts,
        "mm_per_pixel": MM_PER_PIXEL,
        "poses_mm": poses,
        "raw_frame_indices": kept,
    }


def save_observations(episode: dict, path: Path) -> None:
    """Write the method-visible observation file (no ground truth)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        path,
        gradients=episode["gradients"],
        heights=episode["heights"],
        contact_masks=episode["contact_masks"],
        mm_per_pixel=np.float64(episode["mm_per_pixel"]),
    )


def load_episode_configs(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text())["episodes"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Render public training episodes.")
    parser.add_argument("--configs", default="data/train_episodes.json")
    parser.add_argument("--output-dir", default="data/downloads/train_episodes")
    parser.add_argument("--only", default=None, help="render a single named episode")
    args = parser.parse_args()
    out = Path(args.output_dir)
    for cfg in load_episode_configs(Path(args.configs)):
        if args.only and cfg["name"] != args.only:
            continue
        episode = render_episode(cfg["family"], int(cfg["seed"]), int(cfg["frames"]), bool(cfg["contact_loss"]))
        save_observations(episode, out / f"{cfg['name']}.npz")
        np.save(out / f"{cfg['name']}_gt_poses.npy", episode["poses_mm"])
        print(f"[tactile_sim] wrote {cfg['name']}", flush=True)


if __name__ == "__main__":
    main()
