# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-04 08:24] - core_claim
- CPU job `8ba3d0e8-8c0` completed successfully with exit code 0.
- The packaged `scripts/run.sh` path regenerated the synthetic benchmark, ran the NormalFlow baseline, ran scaled GelSLAM, wrote full/train/test scores, and passed `python validate.py --compare`.
- Restored `core_claim`: scaled GelSLAM improved over NormalFlow on both tracking metrics, 5.71 deg vs 6.09 deg rotation MAE and 0.70 mm vs 0.95 mm translation MAE.
- Loop-closure constraint is satisfied in the regenerated artifacts: GelSLAM accepted one loop, it was valid, and false-loop rate was 0.0.

### [2026-06-04 08:21] - method_runs
- CPU job `4b493d0e-95c` regenerated the full benchmark successfully and reproduced the core full-score pattern: GelSLAM improved tracking over NormalFlow and accepted one valid loop with zero false-loop rate.
- The job failed validation because the train/test split counted the same single long-loop edge in both slices, making the loop primary metric identical between `scores_train.json` and `scores_test.json`.
- Updated split loop scoring to assign long-loop edges by their earlier anchor frame, so train/test loop metrics are distinct without changing full benchmark scoring or duplicating loop evidence.
- Submitting another CPU container validation job.

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
- Completed at milestone `core_claim`.
