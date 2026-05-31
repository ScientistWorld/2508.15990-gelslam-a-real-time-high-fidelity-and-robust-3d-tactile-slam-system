#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def wrap(theta: np.ndarray) -> np.ndarray:
    return (theta + np.pi) % (2 * np.pi) - np.pi


def compose(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    c, s = np.cos(a[2]), np.sin(a[2])
    return np.array([a[0] + c * b[0] - s * b[1], a[1] + s * b[0] + c * b[1], float(wrap(a[2] + b[2]))])


def invert(a: np.ndarray) -> np.ndarray:
    c, s = np.cos(a[2]), np.sin(a[2])
    return np.array([-c * a[0] - s * a[1], s * a[0] - c * a[1], float(wrap(-a[2]))])


def origin_relative(poses: np.ndarray) -> np.ndarray:
    inv0 = invert(poses[0])
    return np.asarray([compose(inv0, p) for p in poses])


def metrics(run_dir: Path) -> dict[str, float]:
    pred = np.load(run_dir / "pred_poses.npy")
    gt = np.load(run_dir / "gt_poses.npy")
    pred = origin_relative(pred)
    gt = origin_relative(gt)
    pos_err = np.linalg.norm(pred[:, :2] - gt[:, :2], axis=1)
    rot_err = np.abs(wrap(pred[:, 2] - gt[:, 2]))
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    accepted = int(summary.get("accepted_loops", 0))
    false_loops = 0
    keyframe_indices = summary.get("keyframe_indices", [])
    for edge in summary.get("loop_edges", []):
        if len(edge) < 3 or not keyframe_indices:
            continue
        key_i, key_j, measurement = int(edge[0]), int(edge[1]), np.asarray(edge[2], dtype=float)
        if key_i >= len(keyframe_indices) or key_j >= len(keyframe_indices):
            continue
        true_rel = compose(invert(gt[int(keyframe_indices[key_i])]), gt[int(keyframe_indices[key_j])])
        terr = float(np.linalg.norm(true_rel[:2] - measurement[:2]))
        rerr = float(abs(wrap(true_rel[2] - measurement[2])))
        if terr > 10.0 or np.degrees(rerr) > 20.0:
            false_loops += 1
    return {
        "rotation_mae_deg": float(np.degrees(rot_err).mean()),
        "translation_mae_px": float(pos_err.mean()),
        "accepted_loops": accepted,
        "false_loop_rate": float(false_loops / max(accepted, 1)),
        "keyframes": int(summary.get("keyframes", len(pred))),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method-run", action="append", nargs=2, metavar=("NAME", "DIR"), required=True)
    parser.add_argument("--output", default="scoring/scores.json")
    args = parser.parse_args()
    flat_results = {}
    for name, directory in args.method_run:
        flat_results[name] = metrics(Path(directory))
    scores = {
        "experiments": {
            "synthetic_long_horizon_tracking": {
                "results": {
                    name: {
                        "rotation_mae_deg": vals["rotation_mae_deg"],
                        "translation_mae_px": vals["translation_mae_px"],
                    }
                    for name, vals in flat_results.items()
                }
            },
            "loop_closure_quality": {
                "results": {
                    name: {
                        "accepted_loops": vals["accepted_loops"],
                        "false_loop_rate": vals["false_loop_rate"],
                    }
                    for name, vals in flat_results.items()
                }
            },
            "keyframe_budget": {
                "results": {name: {"keyframes": vals["keyframes"]} for name, vals in flat_results.items()}
            },
        }
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scores, indent=2) + "\n")


if __name__ == "__main__":
    main()
