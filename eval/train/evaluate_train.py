#!/usr/bin/env python3
"""Training/development slice: render the public episodes, run every method, score.

Episodes come from data/train_episodes.json and the public simulator in
data/tactile_sim.py. Method outputs are kept under
checkpoints/<method>/train_outputs/<episode>/ for inspection.
"""

from __future__ import annotations

import argparse
import os

for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[_key] = "1"
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for p in (str(HERE), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import frozen_normalflow  # noqa: E402
import harness  # noqa: E402
from data import tactile_sim  # noqa: E402


def render(episode: dict) -> dict:
    return tactile_sim.render_episode(episode["family"], int(episode["seed"]), int(episode["frames"]),
                                      bool(episode["contact_loss"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--episodes", default=None, help="episode config JSON (default data/train_episodes.json)")
    parser.add_argument("--output", default=None)
    parser.add_argument("--only", nargs="*", default=None, help="restrict to these episode names")
    parser.add_argument("--audit-dir", default=None, help="private directory for evaluator-generated paired diagnostics")
    parser.add_argument("--resume-dir", default=None, help="private raw-output checkpoints for resuming preempted jobs; metrics are recomputed")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    episodes = tactile_sim.load_episode_configs(Path(args.episodes) if args.episodes else root / "data" / "train_episodes.json")
    if args.only:
        episodes = [e for e in episodes if e["name"] in set(args.only)]
    output = Path(args.output) if args.output else root / "scoring" / "scores_train.json"
    harness.evaluate(
        "train",
        episodes,
        render,
        tactile_sim.save_observations,
        frozen_normalflow.track_frame_to_frame,
        output,
        root,
        keep_outputs=True,
        audit_dir=Path(args.audit_dir) if args.audit_dir else None,
        resume_dir=Path(args.resume_dir) if args.resume_dir else None,
    )


if __name__ == "__main__":
    main()
