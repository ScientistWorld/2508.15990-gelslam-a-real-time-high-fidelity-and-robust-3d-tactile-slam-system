# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-04 08:30] - core_claim
- Packaged scaled GelSLAM benchmark reproduces the paper's core long-horizon tactile tracking claim on a 144-frame synthetic closed-loop sequence.
- The implemented method runs GelSLAM-style tactile geometry extraction, NormalFlow tracking, keyframe selection, loop verification, pose-graph optimization, and fused-surface diagnostics rather than a surrogate.
- Current reproduced scores improve over the NormalFlow baseline on both tracking benefit metrics: 5.71 deg vs 6.09 deg rotation MAE and 0.70 mm vs 0.95 mm translation MAE.
- Loop-closure constraint is measured directly from method artifacts: GelSLAM accepts one valid loop with 1.0 valid-loop rate and 0.0 false-loop rate, while NormalFlow accepts no loops.
- Scope limitation: this is a scaled synthetic planar tracking substitute, not the full physical GelSight dataset with complete 6DoF reconstruction.

## Stop Justification
