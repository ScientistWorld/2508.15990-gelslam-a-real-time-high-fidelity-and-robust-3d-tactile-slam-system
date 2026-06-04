# Evaluation

This file describes the benchmark task and metrics without exposing implementation details that future methods must not rely on. The benchmark is a scaled synthetic substitute for the paper's real GelSight long-horizon tracking and reconstruction dataset.

## Metrics

- **rotation_mae_deg:** Mean absolute rotation error in degrees over the evaluated trajectory. Lower is better.
- **translation_mae_mm:** Mean absolute translation error in millimeters. The synthetic image-grid error is converted with the GelSight Mini pitch implied by the paper's resized 320x240 frames over a 20mm x 15mm sensing area. Lower is better.
- **accepted_loops:** Number of loop closures accepted during the trajectory. Higher is generally better when false loops remain controlled, because the benchmark is designed to require revisiting earlier contacts to correct drift.
- **false_loop_rate:** Fraction of accepted loops that are inconsistent with ground truth revisits. Lower is better. This is a constraint metric because a method can artificially increase accepted loops by accepting outliers.
Fused-surface artifacts may be inspected as diagnostics, but they are not part of the default scoring contract because the packaged touched-surface metric is not directly comparable to the paper's full CAD/object-scan reconstruction benchmark.

## Baselines and Targets

The required tracking comparison is between a candidate long-horizon tactile tracking system and the fixed frame-to-frame tactile registration baseline shipped in `baseline/`. The paper's Table IV reports the baseline at about 7.42 degrees average rotation MAE and 1.09 mm average translation MAE, while the proposed system reports about 4.00 degrees and 0.89 mm. The synthetic benchmark should preserve the same qualitative target: a successful long-horizon tracker should reduce drift relative to the frame-to-frame baseline.

For loop behavior, Table II reports an average of 34 accepted revisits per real tracking episode. The scaled benchmark should not require matching this count exactly, but it should measure whether revisits are actually used and whether false loops remain rare. Table II also reports retained-state counts; those are retained as diagnostics only because raw counts are not directly comparable between the paper's 523-frame average real episodes and this scaled benchmark.

For reconstruction, Table VI reports average Chamfer Distance of 0.60 mm and average Normal Cosine Distance of 0.962 on physical objects with CAD ground truth. The scaled benchmark can emit fused touched-surface artifacts, but reconstruction is documented as a diagnostic rather than a scored target until a CAD-comparable protocol is added.

## Evaluation Protocol

Evaluate all methods on the same generated long-horizon tactile sequences, with fixed seeds and identical preprocessing. Each sequence should include local contact observations, ground-truth pose over time, known touched surface geometry, and repeated contacts that make loop closure meaningful. Continuous contact and long enough horizons are important: the benchmark must not collapse into a short-range registration task where the frame-to-frame baseline already solves the problem.

Report the tracking and loop metrics for both the candidate method and the fixed frame-to-frame baseline on the same test split. The baseline should be evaluated without global revisit correction. A long-horizon method may use revisits and global consistency mechanisms, but the comparison is valid only if all methods consume the same synthetic tactile stream and the same pose ground truth.

## Method Output Contract

`scripts/evaluate.sh` scores saved run artifacts rather than rerunning any method. A method run must write `pred_poses.npy` with one pose vector per frame. To score loop-closure constraints, it should also write `summary.json` with `loop_edges` and `keyframe_indices`. `reconstructed_points.npy` and `reconstructed_normals.npy` are optional diagnostic artifacts. `keyframe_poses.npy` is optional diagnostic output. Malformed loop records are counted as false loops.
