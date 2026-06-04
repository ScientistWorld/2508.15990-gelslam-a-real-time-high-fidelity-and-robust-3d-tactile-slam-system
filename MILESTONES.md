# Reproduction Milestones

**Current: method_runs**

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

### [2026-06-04 09:00] - core_claim
- Hardened the full-sequence evaluator so `scoring/scores.json` emits every metric declared in `scoring/reference.json`, matching the train/test evaluator contract.
- Updated `scripts/run.sh` to regenerate the synthetic benchmark, NormalFlow baseline, scaled GelSLAM artifacts, full scores, train/test scores, and validator comparison in one CPU job.
- Local syntax compilation passed; evaluator execution requires the container NumPy/SciPy/OpenCV overlay, so a CPU test job is submitted for fresh end-to-end validation.

### [2026-06-04 09:13] - core_claim
- CPU verification job `b9542f1c-97a` completed with exit code 0.
- The job regenerated the benchmark and artifacts, emitted complete full/train/test scores, checked full metric coverage, and passed `python validate.py --compare`.
- Final verification report written; workspace judged ready for scaled gym use.

### [2026-06-04 09:20] - method_runs
- Independent method-fidelity audit found that the previous `core_claim` path depended on planarizing poses, special final-anchor loop handling, and non-paper odometry gates.
- Reset the milestone to `method_runs`: the implementation still runs recognizable GelSLAM components, but a higher milestone needs results from a more faithful scaled SE(3) procedure.
- Patched the runnable path to use full SE(3) pose graph variables, remove planar projection from method and baseline, remove final-anchor/odometry loop shortcuts, and generate the default synthetic benchmark in 6DoF mode.

### [2026-06-04 09:28] - method_runs
- Final verification found that the checked-in scores and checkpoint artifacts are stale relative to the current 6DoF runnable path.
- Local structural validation passes on the existing artifacts, and optional download URLs were verified, but `core_claim` cannot be restored without a fresh container run from the current code.
- Keeping `action: submit` for a CPU validation job to regenerate the benchmark, baseline, method outputs, full/train/test scores, and validator comparison.

### [2026-06-04 09:50] - method_runs
- CPU job `1d21151c-831` completed the current 6DoF path end to end and passed structural validation, confirming the packaged environment still runs.
- The regenerated scores do not support `core_claim`: GelSLAM reduced translation drift versus NormalFlow but had much worse rotation error and accepted three false loop closures.
- Patched the NormalFlow registration objective used by both the method and baseline with a target-height consistency residual so the scaled 6DoF renderer constrains z, roll, and pitch instead of relying on normal direction alone.

## Stop Justification
- Not stopped. A CPU retry job is being submitted for the depth-aware scaled SE(3) path before any higher milestone is claimed.
