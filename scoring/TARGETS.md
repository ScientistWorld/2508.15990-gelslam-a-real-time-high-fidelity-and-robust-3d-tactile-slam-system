# Evaluation Targets

Every target below corresponds to an experiment and metric in `scoring/reference.json`. The benchmark is a scaled synthetic substitute for the paper's real tactile tracking and reconstruction dataset, but it is designed to preserve the same long-horizon tracking question, loop-closure constraints, and touched-surface reconstruction goal.

## Primary: synthetic_long_horizon_tracking

Tests whether the method reduces long-horizon tactile tracking drift on generated tactile sequences with repeated contacts.

- **Metric:** `rotation_mae_deg` (lower is better)
- **Metric:** `translation_mae_mm` (lower is better)
- **How to run:** Evaluate the candidate method and the fixed frame-to-frame baseline on the fixed synthetic tracking test split with identical input streams and preprocessing.

## Constraint: loop_closure_quality

Tests whether drift reduction comes from valid loop closure behavior rather than accepting arbitrary pose constraints.

- **Metric:** `accepted_loops` (higher is better)
- **Metric:** `valid_loops` (higher is better)
- **Metric:** `valid_loop_recall` (higher is better)
- **Metric:** `valid_loop_rate` (higher is better)
- **Metric:** `false_loop_rate` (lower is better)
- **How to run:** Count accepted loop closures and compare each accepted loop against the ground-truth revisit relation for the same synthetic tracking episodes.

## Secondary: synthetic_reconstruction

Tests whether the pose estimates are accurate enough to fuse local tactile contacts into a coherent touched-surface reconstruction.

- **Metric:** `chamfer_distance_mm` (lower is better)
- **Metric:** `normal_cosine_distance` (higher is better)
- **How to run:** Score the fused surface artifacts emitted by the method against the fixed known target surface for the same generated tactile sequence.
