# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-05-31 17:20] - none
- Continuation audit found the previous scaled tracking implementation was too planar to support `core_claim`.
- Reworked the scaled method toward the paper's actual SE(3) computation: geometry is recomputed from height maps, NormalFlow now warps 3D tactile surface points and compares rotated normals, loop candidate gating requires more than 8 RANSAC inliers, and pose graph residuals use SE(3) errors.
- Removed stale scores pending a fresh compute-container run.

### [2026-05-31 17:35] - none
- The first CPU container smoke job failed at import time before method execution: direct script execution could not import the workspace `method` package.
- Updated all shell entrypoints to export `/home/user` on `PYTHONPATH` before running Python scripts.

### [2026-05-31 17:48] - none
- The next CPU job ran end-to-end but GelSLAM did not beat NormalFlow, so no milestone was advanced.
- Fixed a pose-convention bug: NormalFlow now uses the inverse of the optimized pose-graph measurement for tactile image/normal warping, and SIFT loop initializations are converted into the same measurement convention.

### [2026-05-31 18:00] - method_runs
- The SE(3) scaled GelSLAM pipeline ran end-to-end in the compute container and wrote `scoring/scores.json`.
- The run did not support the core claim yet: GelSLAM reduced xy drift only after a large unobservable z component inflated translation error, and rotation was worse than NormalFlow.
- Constrained the synthetic benchmark's unobservable z/roll/pitch axes inside the SE(3) NormalFlow solve and skipped adjacent keyframes as loop candidates.

### [2026-05-31 18:15] - method_runs
- The compute run after constraining unobservable axes fixed the extreme translation drift, but GelSLAM still did not beat the NormalFlow baseline.
- Latest scores: NormalFlow 4.93 deg / 0.45 mm, GelSLAM 5.29 deg / 0.74 mm, and zero accepted loops.
- Loosened curvature-feature loop proposals and separated loop-closure acceptance thresholds from keyframe-tracking thresholds for the next smoke job.

### [2026-05-31 18:30] - method_runs
- The loop-threshold smoke job accepted 13 loops, but all were false by the evaluator and degraded GelSLAM to 33.67 deg / 3.09 mm.
- Added an odometry-consistency gate for loop closures and retained rejected-candidate diagnostics in `summary.json`.

### [2026-05-31 18:45] - method_runs
- The odometry-gated run rejected all false loops but still accepted no valid loops, returning to the no-loop score.
- Diagnostics showed the origin keyframe was pruned from coverage, so the final revisit could not be proposed as a loop closure.
- Updated coverage pruning to retain the initial anchor keyframe as a loop target.

### [2026-05-31 19:00] - method_runs
- The origin anchor remained in coverage, but the final closed-loop frame was not itself promoted to a keyframe, so the true endpoint revisit was still not checked.
- Refactored loop evaluation into a shared helper and forced the final frame into the keyframe graph before pose-graph optimization.

- Documentation and scoring metadata were created for a scaled synthetic GelSLAM reproduction.
- The benchmark target is synthetic long-horizon tactile tracking with GelSLAM versus NormalFlow.
- Required metrics are `rotation_mae_deg`, `translation_mae_mm`, `accepted_loops`, `false_loop_rate`, and `keyframes`.
- Reference values are anchored to the paper's Table II tracking statistics, Table IV tracking MAE, and Table VI reconstruction quality context.

## Stop Justification

No stop condition. Higher milestones would require more objects/settings or the full released dataset.
