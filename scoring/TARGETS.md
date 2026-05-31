# Evaluation Targets

Every target below corresponds to an experiment and metric in `scoring/reference.json`. The benchmark is a scaled synthetic substitute for the paper's real tactile tracking dataset, but it is designed to preserve the same long-horizon tracking question and loop-closure constraints.

## Primary: synthetic_long_horizon_tracking

Tests whether the method reduces long-horizon tactile tracking drift on generated tactile sequences with repeated contacts.

- **Metric:** `rotation_mae_deg` (lower is better)
- **Metric:** `translation_mae_px` (lower is better)
- **How to run:** Evaluate GelSLAM and NormalFlow on the fixed synthetic tracking test split with identical input streams and preprocessing.

## Constraint: loop_closure_quality

Tests whether drift reduction comes from valid loop closure behavior rather than accepting arbitrary pose constraints.

- **Metric:** `accepted_loops` (higher is better)
- **Metric:** `false_loop_rate` (lower is better)
- **How to run:** Count accepted loop closures and compare each accepted loop against the ground-truth revisit relation for the same synthetic tracking episodes.

## Constraint: keyframe_budget

Tests whether the method keeps the tactile SLAM state bounded while solving the tracking problem.

- **Metric:** `keyframes` (lower is better, after maintaining tracking and loop correctness)
- **How to run:** Count retained keyframes over the same fixed synthetic tracking episodes used for the main benchmark.
