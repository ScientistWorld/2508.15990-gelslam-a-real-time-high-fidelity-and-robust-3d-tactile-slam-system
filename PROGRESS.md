# Progress

## What Works

Documentation, scoring metadata, and a runnable scaled GelSLAM reproduction are in place. The benchmark is long-horizon tactile tracking with GelSLAM compared against a NormalFlow frame-to-frame baseline.

## Results

`scoring/scores.json` contains measured results from `bash scripts/reproduce.sh`:

- NormalFlow baseline: 13.47 deg rotation MAE, 19.75 px translation MAE.
- Scaled GelSLAM: 7.20 deg rotation MAE, 12.55 px translation MAE.
- Scaled GelSLAM accepted 7 loop closures with 0.0 false accepted loop rate and used 50 keyframes.

`scoring/reference.json` contains paper-anchored reference values:

- Table IV tracking MAE averages: NormalFlow 7.42 deg / 1.09 translation units, GelSLAM Online 4.00 deg / 0.89 translation units before synthetic benchmark scaling.
- Table II tracking statistics: 523 frames, 68 keyframes, 21 coverage keyframes, 65 loop candidates, and 34 accepted loops on average.
- Table VI reconstruction context: average CD 0.60 mm and average NCD 0.962 over ten 3D-printed objects.

## Remaining

- Submit the packaged reproduction as a CPU job to verify the container/job path.
- Higher milestones would require expanding to more synthetic objects or downloading the full 73 GB released dataset and running the official ROS2/GTSAM reconstruction code.

## Issues

The current reproduction intentionally uses a synthetic benchmark because the full real GelSLAM dataset is a 73 GB archive and the official release depends on ROS2/GTSAM reconstruction infrastructure. This is a data/scale substitution, not an algorithm substitution.

## Deviations From Paper

The reproduction target is a scaled synthetic substitute for the real GelSight long-horizon tracking dataset. The paper used physical GelSight Mini tactile videos with MoCap ground truth; this workspace evaluates generated tactile sequences with known synthetic ground truth and reports translation in pixels rather than millimeters. The method is still expected to follow GelSLAM's computational procedure: tactile geometry extraction, NormalFlow tracking, keyframe selection, loop proposal, loop verification, and pose graph optimization.
