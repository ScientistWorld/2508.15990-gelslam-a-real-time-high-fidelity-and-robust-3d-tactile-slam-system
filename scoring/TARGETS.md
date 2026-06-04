# Evaluation Targets

Every target below corresponds to an experiment and metric in `scoring/reference.json`. The benchmark is a scaled 144-frame synthetic substitute for the paper's real tactile tracking dataset, but it is designed to preserve the same long-horizon tracking question and loop-closure constraints.

The reference values are derived from the paper's reported tracking and revisit tables. The reproduced scores are generated on the scaled substitute, so absolute numerical comparison is approximate; the core target is reducing long-horizon drift relative to the packaged frame-to-frame baseline while maintaining safe revisit behavior.

## Primary: synthetic_long_horizon_tracking

Tests whether the method reduces long-horizon tactile tracking drift on generated tactile sequences with repeated contacts.

- **Metric:** `rotation_mae_deg` (lower is better)
- **Metric:** `translation_mae_mm` (lower is better)
- **Metric:** `rotation_p95_deg` (lower is better)
- **Metric:** `translation_p95_mm` (lower is better)
- **Metric:** `terminal_rotation_error_deg` (lower is better)
- **Metric:** `terminal_translation_error_mm` (lower is better)
- **How to run:** Evaluate the candidate method and the fixed frame-to-frame baseline on the fixed closed-loop synthetic tracking sequence with identical input streams and preprocessing. The train/test slice files are diagnostics for partitioned error analysis; `scoring/scores.json` is the primary benchmark contract.

## Constraint: loop_closure_quality

Tests whether drift reduction is accompanied by valid revisit behavior rather than accepting arbitrary pose constraints.

- **Metric:** `accepted_loops` (higher is better)
- **Metric:** `valid_loops` (higher is better)
- **Metric:** `valid_loop_rate` (higher is better)
- **Metric:** `false_loop_rate` (lower is better)
- **Metric:** `loop_span_rotation_mae_deg` (lower is better)
- **Metric:** `loop_span_translation_mae_mm` (lower is better)
- **Metric:** `loop_rotation_error_deg` (lower is better)
- **Metric:** `loop_translation_error_mm` (lower is better)
- **How to run:** Count accepted revisit links and compare each one against the ground-truth revisit relation for the same synthetic tracking episodes.
