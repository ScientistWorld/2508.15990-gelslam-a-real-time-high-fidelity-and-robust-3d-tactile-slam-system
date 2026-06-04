# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-06-04 08:16] - method_runs
- Continued from a reset milestone and audited the existing scaled GelSLAM reproduction.
- Confirmed the main method path implements GelSLAM-style tactile geometry extraction, NormalFlow tracking, loop verification, pose-graph optimization, and reconstruction diagnostics rather than a surrogate.
- Found a scoring-contract issue in train/test split evaluators: they computed loop-closure metrics but would serialize only tracking metrics.
- Patched both split evaluators to write the loop-closure constraint experiment and submitted CPU container validation to regenerate scores before restoring a higher milestone.

### [2026-06-04 08:30] - core_claim
- Packaged scaled GelSLAM benchmark reproduces the paper's core long-horizon tactile tracking claim on a 144-frame synthetic closed-loop sequence.
- The implemented method runs GelSLAM-style tactile geometry extraction, NormalFlow tracking, keyframe selection, loop verification, pose-graph optimization, and fused-surface diagnostics rather than a surrogate.
- Current reproduced scores improve over the NormalFlow baseline on both tracking benefit metrics: 5.71 deg vs 6.09 deg rotation MAE and 0.70 mm vs 0.95 mm translation MAE.
- Loop-closure constraint is measured directly from method artifacts: GelSLAM accepts one valid loop with 1.0 valid-loop rate and 0.0 false-loop rate, while NormalFlow accepts no loops.
- Scope limitation: this is a scaled synthetic planar tracking substitute, not the full physical GelSight dataset with complete 6DoF reconstruction.

## Stop Justification
