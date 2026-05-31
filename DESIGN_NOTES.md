# Train/Test Evaluation Design Notes

## What I Checked

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side.
- Confirmed the train entry point invokes `eval/train/` and writes `scoring/scores_train.json`.
- Confirmed the test entry point invokes `eval/test/` and writes `scoring/scores_test.json`.
- Checked for hardcoded method defaults in the split scripts; both enumerate `checkpoints/` unless explicit `METHOD_NAME RUN_DIR` pairs are passed.
- Checked for train/test cross-import leakage by grepping both slice folders and scripts.
- Checked `scoring/reference.json` for paper-agreement metric names.
- Confirmed `scoring/scores_train.json` and `scoring/scores_test.json` are absent.
- Ran `bash -n` on both split entry scripts.

## What Changed

- Added harder-to-game trajectory metrics to both train and test slice evaluators:
  - `rotation_p95_deg`
  - `translation_p95_mm`
  - `terminal_rotation_error_deg`
  - `terminal_translation_error_mm`
- Added `valid_loops` to both slice evaluators so loop-closure scoring rewards correct accepted loops, not only the raw number of accepted loops.
- Added required metric descriptions in `scoring/reference.json`.
- Reduced the coefficient on raw `accepted_loops`, added a stronger positive coefficient for `valid_loops`, and made `false_loop_rate` an explicit negative constraint. This fixes the shortcut where a method could inflate loop count while relying on a separate false-rate metric to absorb the damage.

## Runtime Concerns For The Runner Iteration

- The new slice metrics are computed from the same lightweight artifacts as before: `pred_poses.npy` and optional `summary.json`. No method rerun or retraining should be needed.
- The split remains a single synthetic sequence partitioned by interleaved frame blocks. The added p95 and terminal metrics improve triangulation, but the runner should still watch for saturation if both methods score near-zero on all tracking metrics.
- `terminal_*` metrics use the final evaluated frame in each slice. If a future method emits incomplete or padded trajectories, the existing length check should fail rather than silently masking the problem.
- `valid_loops` depends on `summary.json` containing loop measurements and keyframe indices. Methods that only output poses will score zero accepted and valid loops, which is acceptable for the loop-closure constraint but should be noted when interpreting from-scratch methods.
- I did not run evaluators or generate scores in this pass, per the write-files-only instruction.
