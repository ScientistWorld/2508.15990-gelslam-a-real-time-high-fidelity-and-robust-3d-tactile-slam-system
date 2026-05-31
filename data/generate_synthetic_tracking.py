#!/usr/bin/env python3
"""Generate a small tactile tracking benchmark with known ground truth.

The generated frames are local GelSight-like contact patches sampled from a
larger textured height field. The benchmark keeps the paper's problem shape:
long-horizon tactile-only pose tracking with revisits that make loop closure
useful. It is intentionally small enough for repeated CPU jobs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _bilinear(image: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    h, w = image.shape
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    x1 = x0 + 1
    y1 = y0 + 1
    valid = (x0 >= 0) & (y0 >= 0) & (x1 < w) & (y1 < h)
    out = np.zeros_like(x, dtype=np.float64)
    x0c = np.clip(x0, 0, w - 1)
    x1c = np.clip(x1, 0, w - 1)
    y0c = np.clip(y0, 0, h - 1)
    y1c = np.clip(y1, 0, h - 1)
    wa = (x1 - x) * (y1 - y)
    wb = (x1 - x) * (y - y0)
    wc = (x - x0) * (y1 - y)
    wd = (x - x0) * (y - y0)
    out[valid] = (
        wa[valid] * image[y0c[valid], x0c[valid]]
        + wb[valid] * image[y1c[valid], x0c[valid]]
        + wc[valid] * image[y0c[valid], x1c[valid]]
        + wd[valid] * image[y1c[valid], x1c[valid]]
    )
    return out


def make_surface(seed: int, size: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size]
    surface = np.zeros((size, size), dtype=np.float64)
    for scale, amp in [(18.0, 0.9), (36.0, 1.3), (75.0, 1.6)]:
        for _ in range(10):
            cx, cy = rng.uniform(0, size, 2)
            width = rng.uniform(0.6, 1.4) * scale
            height = rng.normal(0.0, amp)
            surface += height * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * width**2))
    # Add repeatable fine tactile texture: ridges plus local bumps.
    surface += 0.45 * np.sin(xx / 4.5 + 0.7 * np.sin(yy / 23.0))
    surface += 0.25 * np.sin((0.8 * xx + 1.7 * yy) / 7.0)
    for _ in range(260):
        cx, cy = rng.uniform(0, size, 2)
        width = rng.uniform(1.0, 3.2)
        height = rng.normal(0.0, 1.1)
        surface += height * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * width**2))
    surface -= surface.mean()
    surface /= surface.std()
    return surface


def make_trajectory(n: int, center: tuple[float, float], radius: float) -> np.ndarray:
    poses = []
    cx, cy = center
    for i in range(n):
        a = 2.0 * np.pi * i / (n - 1)
        wobble = 0.35 * np.sin(3 * a)
        x = cx + radius * np.cos(a) + 10.0 * np.sin(2.2 * a)
        y = cy + (radius * 0.72) * np.sin(a) + 8.0 * np.cos(1.6 * a)
        theta = 0.42 * np.sin(a + 0.3) + wobble
        poses.append((x, y, theta))
    return np.asarray(poses, dtype=np.float64)


def patch_from_surface(surface: np.ndarray, pose: np.ndarray, patch: int, noise: float, rng: np.random.Generator) -> np.ndarray:
    half = (patch - 1) / 2.0
    yy, xx = np.mgrid[0:patch, 0:patch].astype(np.float64)
    xx -= half
    yy -= half
    c, s = np.cos(pose[2]), np.sin(pose[2])
    wx = pose[0] + c * xx - s * yy
    wy = pose[1] + s * xx + c * yy
    height = _bilinear(surface, wx, wy)
    height += rng.normal(0.0, noise, size=height.shape)
    gy, gx = np.gradient(height)
    norm = np.sqrt(gx * gx + gy * gy + 1.0)
    normals = np.stack([-gx / norm, -gy / norm, np.ones_like(gx) / norm], axis=-1)
    curvature = np.abs(np.gradient(gx, axis=1) + np.gradient(gy, axis=0))
    curvature = curvature / (np.percentile(curvature, 98) + 1e-8)
    mask = np.ones((patch, patch), dtype=bool)
    border = 3
    mask[:border] = False
    mask[-border:] = False
    mask[:, :border] = False
    mask[:, -border:] = False
    return height, normals, np.clip(curvature, 0.0, 1.0), mask


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/synthetic_tracking/loop_patch.npz")
    parser.add_argument("--frames", type=int, default=96)
    parser.add_argument("--patch-size", type=int, default=56)
    parser.add_argument("--surface-size", type=int, default=260)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    surface = make_surface(args.seed, args.surface_size)
    poses = make_trajectory(args.frames, (args.surface_size / 2, args.surface_size / 2), args.surface_size * 0.20)
    heights, normals, curvatures, masks = [], [], [], []
    for pose in poses:
        h, n, c, m = patch_from_surface(surface, pose, args.patch_size, 0.018, rng)
        heights.append(h)
        normals.append(n)
        curvatures.append(c)
        masks.append(m)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        poses=poses,
        heights=np.asarray(heights, dtype=np.float32),
        normals=np.asarray(normals, dtype=np.float32),
        curvatures=np.asarray(curvatures, dtype=np.float32),
        masks=np.asarray(masks, dtype=bool),
    )
    meta = {
        "frames": args.frames,
        "patch_size": args.patch_size,
        "seed": args.seed,
        "description": "Synthetic GelSight-like long-horizon loop trajectory.",
    }
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")


if __name__ == "__main__":
    main()
