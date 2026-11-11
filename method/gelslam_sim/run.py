#!/usr/bin/env python3
"""Run GelSLAM on one tactile episode (the gym's method entry point).

Usage: python -m method.gelslam_sim.run --input EPISODE.npz --output OUT_DIR

Writes OUT_DIR/poses.npy (N x 4 x 4 sensor poses relative to frame 0, mm),
OUT_DIR/loops.json (accepted loop constraints) and OUT_DIR/summary.json.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from method.gelslam_sim.gelslam import GelSLAM, run_gelslam


def load_episode(path: Path):
    with np.load(path) as data:
        return (
            data["gradients"],
            data["heights"],
            data["contact_masks"],
            float(data["mm_per_pixel"]),
        )


def write_outputs(out_dir: Path, poses: np.ndarray, loops: list, stats: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "poses.npy", np.asarray(poses, dtype=np.float64))
    (out_dir / "loops.json").write_text(json.dumps({"loops": loops}))
    (out_dir / "summary.json").write_text(json.dumps(stats, indent=2) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--loop-mode", default="two_stage", choices=["two_stage", "only_sift", "only_nf", "none"])
    parser.add_argument("--no-coverage", action="store_true", help="compare against every keyframe (no coverage set)")
    parser.add_argument("--track-ccs", type=float, default=0.85)
    parser.add_argument("--track-scr", type=float, default=0.3)
    parser.add_argument("--loop-ccs", type=float, default=0.85)
    parser.add_argument("--loop-scr", type=float, default=0.3)
    parser.add_argument("--n-samples", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    gradients, heights, contacts, mm_per_pixel = load_episode(Path(args.input))
    start = time.process_time()
    slam = GelSLAM(
        mm_per_pixel,
        track_ccs=args.track_ccs,
        track_scr=args.track_scr,
        loop_ccs=args.loop_ccs,
        loop_scr=args.loop_scr,
        n_samples=args.n_samples,
        loop_mode=args.loop_mode,
        use_coverage=not args.no_coverage,
        seed=args.seed,
    )
    poses, loops, stats = run_gelslam(gradients, heights, contacts, mm_per_pixel, slam=slam)
    stats["frames"] = int(len(poses))
    stats["cpu_seconds"] = round(time.process_time() - start, 3)
    write_outputs(Path(args.output), poses, loops, stats)


if __name__ == "__main__":
    main()
