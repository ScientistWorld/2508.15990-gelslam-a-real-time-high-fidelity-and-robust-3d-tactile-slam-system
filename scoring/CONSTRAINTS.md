# Scientist Constraints

These constraints define what future scientist agents must hold fixed when trying to improve this benchmark. The goal is to improve long-horizon tactile SLAM behavior, not to win by changing the task into a different perception problem.

## Data

Use only the provided synthetic long-horizon tactile tracking benchmark and its fixed train/test seeds. Do not add real GelSight data, external tactile datasets, rendered CAD assets, or hand-labeled loop annotations beyond what the benchmark generator provides. The benchmark is deliberately scaled down from the paper's real dataset, so adding richer data would change the reproduction target.

## Inputs

Use the same synthetic tactile observation stream available to all methods. Do not use hidden generator state, future frames unavailable at the current timestep for online tracking, ground-truth pose, or ground-truth loop labels as method inputs. Ground truth is for evaluation only.

## Baseline Comparison

Report the NormalFlow frame-to-frame baseline on the same test split whenever reporting GelSLAM or an improved method. The paper's central claim is relative to NormalFlow-style tracking drift, so results without that comparison are incomplete.

## Evaluation

Use the fixed metrics: `rotation_mae_deg`, `translation_mae_mm`, `accepted_loops`, `false_loop_rate`, and `keyframes`. Do not remove `false_loop_rate` or `keyframes`; they are constraint metrics that prevent trivial improvements by accepting excessive loops or retaining unbounded state.

## Procedure

The submitted method must remain a tactile long-horizon tracking or SLAM method. It may improve components such as local registration, keyframe selection, loop proposal, loop verification, pose graph optimization, or robust outlier handling. It must not replace the task with direct supervised trajectory regression from the whole sequence, offline smoothing using ground-truth-like future information, or a non-tactile localization source.

## Compliance Checklist

- [ ] Uses only the provided synthetic tactile benchmark data and fixed seeds
- [ ] Does not use ground-truth pose or loop labels as method inputs
- [ ] Reports NormalFlow on the same test split
- [ ] Reports all five required metrics
- [ ] Keeps `false_loop_rate` and `keyframes` as constraint metrics
- [ ] Stays within tactile tracking/SLAM rather than switching to an unrelated sequence regression or oracle-localization paradigm
