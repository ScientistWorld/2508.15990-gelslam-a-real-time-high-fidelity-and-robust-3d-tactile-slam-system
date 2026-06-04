# Train/Test Evaluation Design Notes

## What I Checked

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side.
- Confirmed train invokes `eval/train/` and writes `scoring/scores_train.json`; test invokes `eval/test/` and writes `scoring/scores_test.json`.
- Checked that both split scripts enumerate prediction artifacts under `checkpoints/` unless explicit `METHOD_NAME RUN_DIR` pairs are supplied; there is no hardcoded default method.
- Grepped for train/test cross-import leakage and found none.
- Checked `scoring/reference.json` for paper-agreement metrics and did not find any metric whose floor is matching a published value.
- Confirmed `scoring/scores_train.json` and `scoring/scores_test.json` are absent.
- Ran static-only validation: `bash -n` on both split entry scripts and Python bytecode compilation for both split evaluators.

## What Changed

- Fixed a scoring coverage bug: both split evaluators already computed p95 and terminal drift metrics, but did not emit them in the score files and `reference.json` did not define them. Both train and test now emit:
  - `rotation_p95_deg`
  - `translation_p95_mm`
  - `terminal_rotation_error_deg`
  - `terminal_translation_error_mm`
- Added the same four metrics to `scoring/reference.json` with nonzero coefficients. These make the visible metric harder to game by improving mean pose error while allowing spikes or end-of-sequence drift.
- Fixed a train/test leakage weakness in `loop_closure_quality`: previously both slices scored the same set of long-loop edges, so loop-closure metrics had no held-out pressure. Long-loop edges are now assigned to train or test by the temporal midpoint block parity, matching the interleaved block split used for frame-level tracking.
- Kept loop scoring artifact-based: evaluation reads `pred_poses.npy` and optional `summary.json`; it does not import from `method/` or rerun the method.

## Runtime Concerns For The Runner Iteration

- The new metrics are still lightweight rescoring of existing artifacts. No retraining or expensive inference should be needed.
- `terminal_*` metrics use the final evaluated frame within each slice. The existing length check should catch incomplete trajectories instead of silently padding them.
- Methods that only output poses and no loop summary will score zero accepted and valid loops. That is acceptable for the loop-closure constraint, but from-scratch agents should know the loop metrics require an optional `summary.json` artifact.
- I did not run evaluators or generate scores in this pass, per the edit-files-only instruction.

## Runner Iteration Findings

- First split run completed on CPU and produced train/test scores for both `normalflow` and `gelslam_online`.
- The frame-tracking metrics behaved as intended: train and test were close but not byte-identical, and the proposed method improved mean translation/rotation on both slices while exposing a terminal/p95 tradeoff.
- The loop midpoint-parity split failed on the frozen method artifact because `gelslam_online` records only one accepted long loop. That assigned the only loop to train and left the held-out loop experiment saturated at zero loops for both methods.
- To keep the loop-closure experiment meaningful, long-loop acceptance is now scored as a global safety constraint on both slices while frame-level tracking remains block-interleaved. The evaluator also emits continuous `loop_translation_error_mm` and `loop_rotation_error_deg` residuals so loop scoring is not just a saturated pass/fail count. Methods with no accepted long loop receive the loop-validity threshold as a finite abstention penalty for those residual metrics.
- `scripts/run.sh` now checks every metric declared in `scoring/reference.json` is present and non-null in both split score files.
