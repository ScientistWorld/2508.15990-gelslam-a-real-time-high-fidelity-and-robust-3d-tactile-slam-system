# Reproduction Milestones

**Current: none**

## Progress Log

### [2026-05-31 17:20] - none
- Continuation audit found the previous scaled tracking implementation was too planar to support `core_claim`.
- Reworked the scaled method toward the paper's actual SE(3) computation: geometry is recomputed from height maps, NormalFlow now warps 3D tactile surface points and compares rotated normals, loop candidate gating requires more than 8 RANSAC inliers, and pose graph residuals use SE(3) errors.
- Removed stale scores pending a fresh compute-container run.

### [2026-05-31 17:35] - none
- The first CPU container smoke job failed at import time before method execution: direct script execution could not import the workspace `method` package.
- Updated all shell entrypoints to export `/home/user` on `PYTHONPATH` before running Python scripts.

- Documentation and scoring metadata were created for a scaled synthetic GelSLAM reproduction.
- The benchmark target is synthetic long-horizon tactile tracking with GelSLAM versus NormalFlow.
- Required metrics are `rotation_mae_deg`, `translation_mae_mm`, `accepted_loops`, `false_loop_rate`, and `keyframes`.
- Reference values are anchored to the paper's Table II tracking statistics, Table IV tracking MAE, and Table VI reconstruction quality context.

### [2026-05-31 16:08] - core_claim
- Implemented a scaled GelSLAM tracking reproduction with differential normal/curvature maps, NormalFlow-style alignment, CCS/SCR keyframes, SIFT-on-curvature loop proposals, NormalFlow loop verification, and pose graph optimization.
- Ran the fixed synthetic long-horizon tactile tracking benchmark against a frame-to-frame NormalFlow baseline.
- Full GelSLAM improved rotation MAE from 13.47 to 7.20 degrees and translation MAE from 1.23 to 0.78 mm, accepted 7 loop closures, and had 0.0 false accepted loop rate.

## Stop Justification

No stop condition. Higher milestones would require more objects/settings or the full released dataset.
