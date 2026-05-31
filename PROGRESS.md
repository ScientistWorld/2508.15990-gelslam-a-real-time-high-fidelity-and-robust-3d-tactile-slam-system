# Progress

## What Works

Documentation and scoring metadata have been prepared for a scaled synthetic GelSLAM reproduction. The benchmark is defined as long-horizon tactile tracking with GelSLAM compared against a NormalFlow frame-to-frame baseline.

## Results

No reproduced scores are recorded yet. `scoring/reference.json` contains paper-anchored reference values:

- Table IV tracking MAE averages: NormalFlow 7.42 deg / 1.09 translation units, GelSLAM Online 4.00 deg / 0.89 translation units before synthetic benchmark scaling.
- Table II tracking statistics: 523 frames, 68 keyframes, 21 coverage keyframes, 65 loop candidates, and 34 accepted loops on average.
- Table VI reconstruction context: average CD 0.60 mm and average NCD 0.962 over ten 3D-printed objects.

## Remaining

- Implement or verify the synthetic tactile tracking benchmark.
- Ensure GelSLAM preserves the paper's computational procedure rather than substituting a generic sequence model.
- Run NormalFlow and GelSLAM on the same fixed synthetic test split.
- Write `scoring/scores.json` after experiments produce measured outputs.

## Issues

The current metadata intentionally uses a synthetic benchmark because the full real GelSLAM dataset and sensor setup are too large for a lightweight reproduction environment. This is a data/scale substitution, not an algorithm substitution.

## Deviations From Paper

The reproduction target is a scaled synthetic substitute for the real GelSight long-horizon tracking dataset. The paper used physical GelSight Mini tactile videos with MoCap ground truth; this workspace evaluates generated tactile sequences with known synthetic ground truth and reports translation in pixels rather than millimeters. The method is still expected to follow GelSLAM's computational procedure: tactile geometry extraction, NormalFlow tracking, keyframe selection, loop proposal, loop verification, and pose graph optimization.
