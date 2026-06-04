# Verification Report

## Initial Assessment

The workspace contains a mostly complete scaled tactile tracking gym: problem
documentation, method code, baseline code, evaluators, train/test split
evaluators, environment scripts, reference scores, and reproduced score
artifacts are present. The structural validator passes on the checked-in
artifacts, the optional download URLs resolve, and the method-agnostic
documentation is generally suitable for from-scratch agents.

However, the current repository state is not the previously validated
`core_claim` state. The latest faithful 6DoF runnable path has now been tested
in CPU jobs `1d21151c-831`, `bf082aab-738`, and `27442669-8d0`; all executed
successfully and passed structural validation, but their scores do not yet
support the core claim.

## Issues Found

- **Critical:** CPU job `1d21151c-831` regenerated the current 6DoF benchmark and
  artifacts, but the reproduced method failed the scientific claim: it improved
  translation drift relative to NormalFlow but had much worse rotation error and
  accepted three false loop closures. This justifies `method_runs`, not
  `core_claim`.
- **Critical:** CPU job `bf082aab-738` reran after the depth-residual patch. The
  extreme translation drift was fixed, but the reproduced method still trailed
  NormalFlow on both tracked benefit metrics and accepted one false loop. This
  still justifies only `method_runs`.
- **Critical:** CPU job `27442669-8d0` reran after stricter loop insertion. The
  method improved rotation and terminal drift over NormalFlow, but translation
  MAE remained slightly worse and no loop closures were accepted. This removes
  the false-loop failure but leaves the loop-closure constraint unproven.
- **Critical:** The failed 6DoF result exposed an observability gap in the
  registration objective. The existing residual matched target normal
  directions but did not penalize disagreement with target height, leaving depth
  motion and coupled SE(3) rotation weakly constrained in the scaled renderer.
- **Critical:** The latest 6DoF result exposes a loop-verification gap: a
  low-support SIFT-curvature proposal can pass CCS/SCR checks but be false under
  ground-truth SE(3) loop error.
- **Critical:** The latest stricter verifier also exposes a loop-proposal gap:
  sparse curvature features can miss the endpoint revisit entirely, leaving no
  candidate for NormalFlow verification.
- **Minor:** Generated Python `__pycache__` directories existed under root and
  source directories. These are ignored artifacts and were removed.
- **Residual:** The workspace has pre-existing unrelated dirty entries
  (`README.md`, `manifest.json`, and deleted ignored trajectory logs). They were
  not modified or reverted during this verification pass.

## Fixes Applied

- Removed generated Python cache directories from root, `baseline/`, `data/`,
  `eval/`, and `method/scaled_gelslam/`.
- Added a height-consistency residual to the NormalFlow registration objective
  in both the method and baseline implementations. The evaluator remains
  unchanged; the next CPU job must regenerate scores from method artifacts.
- Tightened method-side loop insertion: SIFT loop proposals now require at
  least 12 inliers and must be consistent with accumulated odometry before
  entering the pose graph. Rejected-loop diagnostics record inlier and odometry
  gates for future debugging.
- Added an odometry-initialized NormalFlow fallback candidate path for
  long-span coverage pairs when SIFT fails or is rejected. This fallback is not
  an automatic closure: it still must pass stricter CCS/SCR thresholds and the
  SE(3) odometry-consistency gate before adding a pose-graph edge.
- Verified `scripts/download.sh` is self-contained for the default generated
  benchmark and has no `shared/` references.
- Verified both optional external URLs in `scripts/download.sh` using
  `curl -I -L --max-time 15`; the GitHub calibration file returned 200 and the
  Hugging Face dataset redirect resolved to a 200 response with the expected
  68.1 GiB archive size.
- CPU job `1d21151c-831` ran `python validate.py --compare` in the container;
  it passed structurally on regenerated 6DoF artifacts, but the scores were
  scientifically insufficient.
- CPU job `bf082aab-738` ran `python validate.py --compare` in the container;
  it passed structurally on regenerated depth-aware 6DoF artifacts, but the
  scores were scientifically insufficient.
- CPU job `27442669-8d0` ran `python validate.py --compare` in the container;
  it passed structurally after stricter loop insertion, but the scores were
  scientifically insufficient because no valid loops were accepted.

## Final Judgment

The workspace is structurally close to gym-ready, but it is not ready to signal
final `done` at `core_claim` in the current state. The correct next action is to
rerun the CPU container validation job after the NormalFlow fallback loop
candidate patch so `scores.json`, `scores_train.json`, and `scores_test.json`
are regenerated from the current 6DoF method and benchmark. If that job supports
the claim, a later verifier can restore `core_claim`; if it fails, the honest
milestone remains `method_runs`.

- Milestone: method_runs
- Ready for gym use: partial
- Confidence: medium
- Key limitation: current 6DoF runnable path executes, but the latest completed
  scores failed the tracking-plus-loop-closure claim because no loop closures
  were accepted
