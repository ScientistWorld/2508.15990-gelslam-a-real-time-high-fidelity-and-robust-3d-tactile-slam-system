# Verification Report

## Initial Assessment

The workspace contains a mostly complete scaled tactile tracking gym: problem
documentation, method code, baseline code, evaluators, train/test split
evaluators, environment scripts, reference scores, and reproduced score
artifacts are present. The structural validator passes on the checked-in
artifacts, the optional download URLs resolve, and the method-agnostic
documentation is generally suitable for from-scratch agents.

However, the current repository state is not the previously validated
`core_claim` state. The latest committed change reset `MILESTONES.md` and
`action.yaml` to `method_runs`, changed the runnable benchmark from planar to
6DoF, removed planar/final-anchor shortcut code, and submitted a CPU validation
job. That job has not yet produced checked-in scores in this workspace.

## Issues Found

- **Critical:** The checked-in `scoring/scores.json` and checkpoint artifacts are
  stale relative to the current runnable code. `data/synthetic_tracking/loop_patch.json`
  still records `trajectory: planar`, and `checkpoints/scaled_gelslam/summary.json`
  still contains an old `odometry_final_keyframe` loop source, while
  `scripts/reproduce.sh` and `scripts/download.sh` now generate `--trajectory sixdof`
  and the method code no longer has that loop path. A final `core_claim`
  judgment cannot be made until the container job regenerates scores from the
  current code.
- **Minor:** Generated Python `__pycache__` directories existed under root and
  source directories. These are ignored artifacts and were removed.
- **Residual:** The workspace has pre-existing unrelated dirty entries
  (`README.md`, `manifest.json`, and deleted ignored trajectory logs). They were
  not modified or reverted during this verification pass.

## Fixes Applied

- Removed generated Python cache directories from root, `baseline/`, `data/`,
  `eval/`, and `method/scaled_gelslam/`.
- Verified `scripts/download.sh` is self-contained for the default generated
  benchmark and has no `shared/` references.
- Verified both optional external URLs in `scripts/download.sh` using
  `curl -I -L --max-time 15`; the GitHub calibration file returned 200 and the
  Hugging Face dataset redirect resolved to a 200 response with the expected
  68.1 GiB archive size.
- Ran `python validate.py --compare`; it passes structurally on the existing
  artifacts, but those artifacts are stale for the current 6DoF code path.

## Final Judgment

The workspace is structurally close to gym-ready, but it is not ready to signal
final `done` at `core_claim` in the current state. The correct next action is to
run the already prepared CPU container validation job so `scores.json`,
`scores_train.json`, and `scores_test.json` are regenerated from the current
6DoF method and benchmark. If that job supports the claim, a later verifier can
restore `core_claim`; if it fails, the honest milestone remains `method_runs`.

- Milestone: method_runs
- Ready for gym use: partial
- Confidence: medium
- Key limitation: current checked-in scores are from the previous planar scaled
  benchmark, not from the current 6DoF runnable path
