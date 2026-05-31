# Reproduction Milestones

**Current: core_claim**

## Progress Log

- Documentation and scoring metadata were created for a scaled synthetic GelSLAM reproduction.
- The benchmark target is synthetic long-horizon tactile tracking with GelSLAM versus NormalFlow.
- Required metrics are `rotation_mae_deg`, `translation_mae_px`, `accepted_loops`, `false_loop_rate`, and `keyframes`.
- Reference values are anchored to the paper's Table II tracking statistics, Table IV tracking MAE, and Table VI reconstruction quality context.

### [2026-05-31 16:08] - core_claim
- Implemented a scaled GelSLAM tracking reproduction with differential normal/curvature maps, NormalFlow-style alignment, CCS/SCR keyframes, SIFT-on-curvature loop proposals, NormalFlow loop verification, and pose graph optimization.
- Ran the fixed synthetic long-horizon tactile tracking benchmark against a frame-to-frame NormalFlow baseline.
- Full GelSLAM improved rotation MAE from 13.47 to 7.20 degrees and translation MAE from 19.75 to 12.55 pixels, accepted 7 loop closures, and had 0.0 false accepted loop rate.

## Stop Justification

No stop condition. Higher milestones would require more objects/settings or the full released dataset.
