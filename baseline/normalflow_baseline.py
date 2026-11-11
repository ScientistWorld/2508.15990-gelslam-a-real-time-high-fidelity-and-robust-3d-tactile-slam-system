#!/usr/bin/env python3
"""NormalFlow frame-to-frame baseline (paper Table IV "NF").

Each frame is registered to the previous one with NormalFlow (identity
initialisation) and the relative motions are composed; there are no keyframes,
no failure detection and no loop closure. Same entry-point contract as any
method: python -m baseline.normalflow_baseline --input EPISODE.npz --output DIR

The evaluators score their own frozen copy of this baseline (eval/*/frozen_normalflow.py)
under the name "normalflow"; this file is the readable public version.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from baseline.normalflow import LoseTrackError, TactileFrame, register


def _inverse(transform: np.ndarray) -> np.ndarray:
    out = np.eye(4)
    out[:3, :3] = transform[:3, :3].T
    out[:3, 3] = -transform[:3, :3].T @ transform[:3, 3]
    return out


def track_frame_to_frame(gradients, heights, contacts, mm_per_pixel, n_samples=3000):
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with np.load(args.input) as data:
        poses = track_frame_to_frame(data["gradients"], data["heights"], data["contact_masks"],
                                     float(data["mm_per_pixel"]))
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "poses.npy", poses)
    (out / "loops.json").write_text(json.dumps({"loops": []}))


if __name__ == "__main__":
    main()
