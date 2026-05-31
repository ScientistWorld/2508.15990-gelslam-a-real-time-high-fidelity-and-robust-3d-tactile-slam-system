# Evaluation

This file describes the benchmark task and metrics without exposing implementation details that future methods must not rely on. The benchmark is a scaled synthetic substitute for the paper's real GelSight long-horizon tracking dataset.

## Metrics

- **rotation_mae_deg:** Mean absolute rotation error in degrees over the evaluated trajectory. Lower is better.
- **translation_mae_mm:** Mean absolute translation error in millimeters. The synthetic image-grid error is converted with the GelSight Mini pitch implied by the paper's resized 320x240 frames over a 20mm x 15mm sensing area. Lower is better.
- **accepted_loops:** Number of loop closures accepted during the trajectory. Higher is generally better when false loops remain controlled, because the benchmark is designed to require revisiting earlier contacts to correct drift.
- **false_loop_rate:** Fraction of accepted loops that are inconsistent with ground truth revisits. Lower is better. This is a constraint metric because a method can artificially increase accepted loops by accepting outliers.
- **keyframes:** Number of keyframes retained for the episode. Lower is better as a resource metric only after tracking quality and loop correctness are preserved.

## Baselines and Targets

The required comparison is between the reproduced GelSLAM procedure and a NormalFlow frame-to-frame baseline. The paper's Table IV reports NormalFlow at about 7.42 degrees average rotation MAE and 1.09 mm average translation MAE, while GelSLAM Online reports about 4.00 degrees and 0.89 mm. The synthetic benchmark should preserve the same qualitative target: GelSLAM should reduce long-horizon drift relative to NormalFlow.

For loop and resource behavior, Table II reports GelSLAM tracking episodes with an average of 68 keyframes and 34 accepted loops. The scaled benchmark should not require matching these counts exactly, but it should measure whether loop closure is actually used and whether false loops remain rare.

## Evaluation Protocol

Evaluate all methods on the same generated long-horizon tactile sequences, with fixed seeds and identical preprocessing. Each sequence should include local contact observations, ground-truth pose over time, and repeated contacts that make loop closure meaningful. Continuous contact and long enough horizons are important: the benchmark must not collapse into a short-range registration task where NormalFlow already solves the problem.

Report the metrics for both GelSLAM and NormalFlow on the same test split. NormalFlow should be evaluated as a frame-to-frame baseline without global loop correction. GelSLAM should be evaluated with its full SLAM procedure enabled. The comparison is valid only if both methods consume the same synthetic tactile stream and the same pose ground truth.

## Method Output Contract

`scripts/evaluate.sh` scores saved run artifacts rather than rerunning any method. A method run must write `pred_poses.npy` with one pose vector per frame. To score loop-closure and keyframe constraints, it should also write `summary.json` with `loop_edges` and `keyframe_indices`, plus `keyframe_poses.npy` containing retained keyframe poses. Malformed loop records are counted as false loops.
