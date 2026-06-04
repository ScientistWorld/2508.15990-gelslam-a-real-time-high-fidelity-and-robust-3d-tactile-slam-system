# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-31 18:25] - method_runs
- Packaged a scaled GelSLAM implementation with tactile geometry extraction, NormalFlow-style registration, keyframe selection, loop verification, pose graph optimization, and fused reconstruction diagnostics.
- Verified that the baseline, method, evaluator, and structural validation run end-to-end in the container on the synthetic tactile benchmark.

### [2026-06-04 08:28] - core_claim
- Reproduced the core tracking claim on the 144-frame scaled tactile benchmark: scaled GelSLAM improves both rotation and translation MAE over the NormalFlow baseline.
- Reproduced the loop-closure safety constraint on the same benchmark: the accepted GelSLAM loop is valid and the false-loop rate is 0.0.
- `python validate.py --compare` passes, including train/test split checks and method/evaluation import separation.

### [2026-06-04 08:33] - method_runs
- Continuation audit reset the milestone to `method_runs` and rechecked method fidelity, evaluator independence, and scoring completeness.
- Fixed the scoring-contract wording so the primary target matches `scripts/evaluate.sh`: the full fixed closed-loop synthetic sequence, with train/test slice scores treated as diagnostics.
- Submitting a CPU container job to regenerate artifacts, run the evaluator, and determine whether `core_claim` can be restored from fresh results.

### [2026-06-04 08:37] - core_claim
- CPU container job `6a7582cb-f64` completed with exit code 0 and regenerated the full reproduction path from `scripts/run.sh`.
- Restored the core tracking claim on the 144-frame scaled tactile benchmark: GelSLAM scored 5.713 deg / 0.703 mm versus NormalFlow at 6.086 deg / 0.948 mm.
- Restored the loop-closure safety constraint: GelSLAM accepted one loop, the loop was valid, and the false-loop rate was 0.0.
- `python validate.py --compare` passed in the container and locally after the job.

## Stop Justification
- Completed at milestone `core_claim` for the packaged scaled benchmark. Higher milestones would require a broader multi-object or real-dataset reproduction beyond the current validated substitute.
