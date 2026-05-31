# Evaluation Targets

Every target below corresponds to an experiment and metric in `scoring/reference.json`. The benchmark is a scaled synthetic substitute for the paper's real tactile tracking dataset, but it is designed to preserve the same long-horizon tracking question and loop-closure constraints.

## Primary: synthetic_long_horizon_tracking

Tests whether the method reduces long-horizon tactile tracking drift on generated tactile sequences with repeated contacts.

- **Metric:** `rotation_mae_deg` (lower is better)
- **Metric:** `translation_mae_mm` (lower is better)
- **How to run:** Evaluate GelSLAM and NormalFlow on the fixed synthetic tracking test split with identical input streams and preprocessing.

## Constraint: loop_closure_quality

Tests whether drift reduction comes from valid loop closure behavior rather than accepting arbitrary pose constraints.

- **Metric:** `accepted_loops` (higher is better)
- **Metric:** `false_loop_rate` (lower is better)
- **How to run:** Count accepted loop closures and compare each accepted loop against the ground-truth revisit relation for the same synthetic tracking episodes.

## Context: keyframe counts

The method still writes keyframe diagnostics in `summary.json` and `keyframe_poses.npy`, but raw keyframe counts are not an automated target because the packaged 144-frame synthetic benchmark is intentionally much shorter than the paper's 523-frame average real episodes. Comparing those raw counts directly caused a scale mismatch rather than a meaningful scientific score.
