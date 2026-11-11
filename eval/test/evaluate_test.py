#!/usr/bin/env python3
"""Hidden test slice: render held-out tactile episodes, run every method, score.

The held-out episodes below (and the ground truth they generate) exist only in
this directory. Inputs are rendered into a temporary directory at test time,
each registered method is run on them, and the outputs are scored by
harness.py against ground truth that never leaves this process.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import frozen_normalflow  # noqa: E402
import harness  # noqa: E402
import hidden_world  # noqa: E402

HELDOUT_EPISODES = [
    {"name": "heldout_seed_continuous_0", "family": "seed", "seed": 566009, "frames": 400, "contact_loss": False},
    {"name": "heldout_seed_continuous_1", "family": "seed", "seed": 380885, "frames": 400, "contact_loss": False},
    {"name": "heldout_seed_continuous_2", "family": "seed", "seed": 462183, "frames": 400, "contact_loss": False},
    {"name": "heldout_fabric_continuous_0", "family": "fabric", "seed": 264152, "frames": 400, "contact_loss": False},
    {"name": "heldout_fabric_continuous_1", "family": "fabric", "seed": 580535, "frames": 400, "contact_loss": False},
    {"name": "heldout_fabric_continuous_2", "family": "fabric", "seed": 429169, "frames": 400, "contact_loss": False},
    {"name": "heldout_wood_continuous_0", "family": "wood", "seed": 940107, "frames": 400, "contact_loss": False},
    {"name": "heldout_wood_continuous_1", "family": "wood", "seed": 782668, "frames": 400, "contact_loss": False},
    {"name": "heldout_wood_continuous_2", "family": "wood", "seed": 711054, "frames": 400, "contact_loss": False},
    {"name": "heldout_rock_continuous_0", "family": "rock", "seed": 215906, "frames": 400, "contact_loss": False},
    {"name": "heldout_rock_continuous_1", "family": "rock", "seed": 290358, "frames": 400, "contact_loss": False},
    {"name": "heldout_rock_continuous_2", "family": "rock", "seed": 889897, "frames": 400, "contact_loss": False},
    {"name": "heldout_seed_contact_loss_0", "family": "seed", "seed": 177414, "frames": 400, "contact_loss": True},
    {"name": "heldout_seed_contact_loss_1", "family": "seed", "seed": 144941, "frames": 400, "contact_loss": True},
    {"name": "heldout_fabric_contact_loss_0", "family": "fabric", "seed": 597362, "frames": 400, "contact_loss": True},
    {"name": "heldout_fabric_contact_loss_1", "family": "fabric", "seed": 600848, "frames": 400, "contact_loss": True},
    {"name": "heldout_wood_contact_loss_0", "family": "wood", "seed": 362779, "frames": 400, "contact_loss": True},
    {"name": "heldout_wood_contact_loss_1", "family": "wood", "seed": 248371, "frames": 400, "contact_loss": True},
    {"name": "heldout_rock_contact_loss_0", "family": "rock", "seed": 401515, "frames": 400, "contact_loss": True},
    {"name": "heldout_rock_contact_loss_1", "family": "rock", "seed": 479919, "frames": 400, "contact_loss": True},
    {"name": "heldout_seed_continuous_3", "family": "seed", "seed": 402879, "frames": 400, "contact_loss": False},
    {"name": "heldout_seed_continuous_4", "family": "seed", "seed": 893652, "frames": 400, "contact_loss": False},
    {"name": "heldout_seed_continuous_5", "family": "seed", "seed": 320906, "frames": 400, "contact_loss": False},
    {"name": "heldout_fabric_continuous_3", "family": "fabric", "seed": 239816, "frames": 400, "contact_loss": False},
    {"name": "heldout_fabric_continuous_4", "family": "fabric", "seed": 706798, "frames": 400, "contact_loss": False},
    {"name": "heldout_fabric_continuous_5", "family": "fabric", "seed": 824366, "frames": 400, "contact_loss": False},
    {"name": "heldout_wood_continuous_3", "family": "wood", "seed": 489777, "frames": 400, "contact_loss": False},
    {"name": "heldout_wood_continuous_4", "family": "wood", "seed": 155714, "frames": 400, "contact_loss": False},
    {"name": "heldout_wood_continuous_5", "family": "wood", "seed": 380847, "frames": 400, "contact_loss": False},
    {"name": "heldout_rock_continuous_3", "family": "rock", "seed": 648167, "frames": 400, "contact_loss": False},
    {"name": "heldout_rock_continuous_4", "family": "rock", "seed": 305036, "frames": 400, "contact_loss": False},
    {"name": "heldout_rock_continuous_5", "family": "rock", "seed": 785515, "frames": 400, "contact_loss": False},
    {"name": "heldout_seed_contact_loss_2", "family": "seed", "seed": 583916, "frames": 400, "contact_loss": True},
    {"name": "heldout_seed_contact_loss_3", "family": "seed", "seed": 275753, "frames": 400, "contact_loss": True},
    {"name": "heldout_fabric_contact_loss_2", "family": "fabric", "seed": 805820, "frames": 400, "contact_loss": True},
    {"name": "heldout_fabric_contact_loss_3", "family": "fabric", "seed": 408601, "frames": 400, "contact_loss": True},
    {"name": "heldout_wood_contact_loss_2", "family": "wood", "seed": 579491, "frames": 400, "contact_loss": True},
    {"name": "heldout_wood_contact_loss_3", "family": "wood", "seed": 544059, "frames": 400, "contact_loss": True},
    {"name": "heldout_rock_contact_loss_2", "family": "rock", "seed": 657502, "frames": 400, "contact_loss": True},
    {"name": "heldout_rock_contact_loss_3", "family": "rock", "seed": 638784, "frames": 400, "contact_loss": True},
]


def render(episode: dict) -> dict:
    return hidden_world.render_episode(episode["family"], int(episode["seed"]), int(episode["frames"]),
                                       bool(episode["contact_loss"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(HERE.parents[1]))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output) if args.output else root / "scoring" / "scores_test.json"
    harness.evaluate(
        "test",
        HELDOUT_EPISODES,
        render,
        hidden_world.save_observations,
        frozen_normalflow.track_frame_to_frame,
        output,
        root,
        keep_outputs=False,
    )


if __name__ == "__main__":
    main()
