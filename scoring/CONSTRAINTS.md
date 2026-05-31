# Scientist Constraints

These constraints define what future scientist agents must hold fixed when trying to improve this benchmark. The goal is to improve long-horizon tactile SLAM behavior, not to win by changing the task into a different perception problem.

## Data

Use only the provided synthetic long-horizon tactile tracking and reconstruction benchmark and its fixed train/test seeds. Do not add real GelSight data, external tactile datasets, rendered CAD assets, or hand-labeled loop annotations beyond what the benchmark generator provides. The benchmark is deliberately scaled down from the paper's real dataset, so adding richer data would change the reproduction target.

## Inputs

Use the same synthetic tactile observation stream available to all methods. Do not use hidden generator state, future frames unavailable at the current timestep for online tracking, ground-truth pose, ground-truth loop labels, or target reconstruction points as method inputs. Ground truth and target surfaces are for evaluation only.

## Baseline Comparison

Report the NormalFlow frame-to-frame baseline on the same test split whenever reporting GelSLAM or an improved method. The paper's central claim is relative to NormalFlow-style tracking drift, so results without that comparison are incomplete.

## Evaluation

Use the fixed metrics: `rotation_mae_deg`, `translation_mae_mm`, `accepted_loops`, `valid_loops`, `valid_loop_recall`, `valid_loop_rate`, `false_loop_rate`, `chamfer_distance_mm`, and `normal_cosine_distance`. Do not remove `false_loop_rate`; it is the constraint metric that prevents trivial improvements by accepting excessive or incorrect loops. Do not remove `valid_loop_recall` or `valid_loop_rate`; they prevent methods from satisfying the loop-closure target by abstaining from revisits or by accepting many low-quality candidates. Reconstruction must be scored from emitted artifacts, not regenerated inside the evaluator. Keyframe counts are recorded as diagnostics in method artifacts, but they are not scored because the scaled benchmark has a different episode length from the paper's real-data setting.

## Procedure

The submitted method must remain a tactile long-horizon tracking, SLAM, or reconstruction method. It may improve components such as local registration, keyframe selection, loop proposal, loop verification, pose graph optimization, robust outlier handling, or surface fusion. It must not replace the task with direct supervised trajectory regression from the whole sequence, offline smoothing using ground-truth-like future information, oracle reconstruction from the synthetic generator, or a non-tactile localization source.

## Compliance Checklist

- [ ] Uses only the provided synthetic tactile benchmark data and fixed seeds
- [ ] Does not use ground-truth pose or loop labels as method inputs
- [ ] Reports NormalFlow on the same test split
- [ ] Reports all required metrics
- [ ] Keeps `false_loop_rate` as a constraint metric
- [ ] Scores reconstruction only from method-emitted surface artifacts
- [ ] Stays within tactile tracking/SLAM rather than switching to an unrelated sequence regression or oracle-localization paradigm
