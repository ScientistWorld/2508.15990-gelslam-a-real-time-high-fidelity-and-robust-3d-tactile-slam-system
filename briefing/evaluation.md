# Evaluation

This file describes the benchmark task and metrics without exposing implementation details that future methods must not rely on. The benchmark is a scaled synthetic substitute for the paper's real long-horizon tactile tracking and reconstruction dataset.

## Metrics

- **rotation_mae_deg** and **translation_mae_mm:** Mean pose error over the evaluated trajectory. Lower is better.
- **rotation_p95_deg** and **translation_p95_mm:** 95th percentile pose error, measuring tail failures. Lower is better.
- **terminal_rotation_error_deg** and **terminal_translation_error_mm:** Final-frame accumulated drift. Lower is better.
- **accepted_loops:** Number of long-range revisit links accepted during the trajectory. Higher is useful only when false links remain controlled.
- **valid_loops** and **valid_loop_rate:** Count and fraction of accepted revisit links that are geometrically consistent. Higher is better.
- **false_loop_rate:** Fraction of accepted revisit links that are inconsistent with ground truth revisits. Lower is better. This is a constraint metric because a method can artificially increase accepted links by accepting outliers.
- **loop_span_rotation_mae_deg** and **loop_span_translation_mae_mm:** Pose error on frames far enough apart for revisit reasoning to matter. Lower is better.
- **loop_rotation_error_deg** and **loop_translation_error_mm:** Pose disagreement for accepted revisits, with a conservative penalty when no revisit is accepted. Lower is better.
Fused-surface artifacts may be inspected as diagnostics, but they are not part of the default scoring contract because the packaged touched-surface metric is not directly comparable to the paper's full CAD/object-scan reconstruction benchmark.

## Baselines and Targets

The required tracking comparison is between a candidate long-horizon tactile tracking system and the fixed frame-to-frame tactile registration baseline shipped in `baseline/`. The paper's full-scale tables provide context in `scoring/reference.json`; reproduced numbers in `scoring/scores.json` come only from running the packaged benchmark. The synthetic benchmark should preserve the same qualitative target: a successful long-horizon tracker should reduce drift relative to the frame-to-frame baseline while keeping revisit acceptance reliable.

For revisit behavior, the scaled benchmark should not require matching full-scale raw counts exactly, but it should measure whether revisits are actually used and whether false links remain rare.

For reconstruction, Table VI reports average Chamfer Distance of 0.60 mm and average Normal Cosine Distance of 0.962 on physical objects with CAD ground truth. The scaled benchmark can emit fused touched-surface artifacts, but reconstruction is documented as a diagnostic rather than a scored target until a CAD-comparable protocol is added.

## Evaluation Protocol

Evaluate all methods on the same generated long-horizon tactile sequences, with fixed seeds and identical preprocessing. Each sequence should include local contact observations, ground-truth pose over time, known touched surface geometry, and repeated contacts that make revisit handling meaningful. Continuous contact and long enough horizons are important: the benchmark must not collapse into a short-range registration task where the frame-to-frame baseline already solves the problem.

Report the tracking and revisit metrics for both the candidate method and the fixed frame-to-frame baseline on the same test split. The comparison is valid only if all methods consume the same synthetic tactile stream and are evaluated against the same withheld pose ground truth.

## Method Output Contract

`scripts/evaluate.sh` scores saved run artifacts rather than rerunning any method. A method run must write `pred_poses.npy` with one pose vector per frame. To score revisit constraints, it should also write `summary.json` with accepted revisit records and the frame/state indices they connect. `reconstructed_points.npy` and `reconstructed_normals.npy` are optional diagnostic artifacts. Malformed revisit records are counted as false links.
