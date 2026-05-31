#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from method.scaled_gelslam.geometry import compose, se2_to_matrix
from method.scaled_gelslam.normalflow import estimate_relative
from method.scaled_gelslam.run_gelslam import load_frames


def run(dataset: Path, output_dir: Path) -> None:
    frames, gt = load_frames(dataset)
    pred = np.zeros((len(frames), 3), dtype=np.float64)
    prev_rel = np.zeros(3, dtype=np.float64)
    for i in range(1, len(frames)):
        rel, _, _, _ = estimate_relative(frames[i - 1], frames[i], prev_rel)
        pred[i] = compose(pred[i - 1], rel)
        prev_rel = rel
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "pred_poses.npy", pred)
    np.save(output_dir / "gt_poses.npy", gt)
    np.save(output_dir / "pred_matrices.npy", np.asarray([se2_to_matrix(p) for p in pred]))
    (output_dir / "summary.json").write_text(
        json.dumps({"method": "normalflow_baseline", "frames": len(frames), "keyframes": len(frames), "accepted_loops": 0}, indent=2)
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/synthetic_tracking/loop_patch.npz")
    parser.add_argument("--output-dir", default="checkpoints/normalflow_baseline")
    args = parser.parse_args()
    run(Path(args.dataset), Path(args.output_dir))


if __name__ == "__main__":
    main()
