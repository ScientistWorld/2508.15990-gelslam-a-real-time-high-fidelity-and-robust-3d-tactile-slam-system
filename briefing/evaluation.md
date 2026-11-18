# Evaluation

The benchmark is a scaled synthetic substitute for the paper's real long-horizon tactile tracking data: a simulated GelSight-Mini-style sensor (160x120 pixels, 0.1268 mm per pixel) slides over textured convex objects from four texture families (dense bumps, near-periodic weave, low-texture grain, multi-scale roughness), with sensor-fixed calibration errors, per-frame gel distortion and per-pixel noise.

## Experiments

- **long_horizon_tracking** (weight 0.6): 400-frame episodes with continuous contact and frequent revisits.
- **relocalization_after_contact_loss** (weight 0.4): 400-frame episodes in which 25 frames are removed after every 100 kept frames (three contact breaks), as in the paper's relocalisation study.

## Metrics (per experiment)

- **rotation_mae_deg**, **translation_mae_mm**: mean absolute error of the sensor pose relative to the first frame, averaged over the three rotation (Euler theta_x, theta_y, theta_z) or translation (x, y, z) axes and over frames, then over episodes. This is the statistic of the paper's Table IV. Lower is better. Coefficient 1.0 each.
- **rotation_p95_deg**, **translation_p95_mm**: 95th percentile over all frames of the geodesic rotation error and of the translation-error norm. Lower is better. Coefficient 0.4 each.
- **false_loop_excess**: constraint. Fraction of the method's reported frame-pair relations (one record per frame pair) whose relative pose is off by more than 1 mm or 5 degrees from ground truth (each record must be well formed and finite), minus a 2% allowance for the verification tolerance, floored at 0. A method that reports no relations scores 0. Lower is better. Coefficient 0.5.

Per-frame errors are capped at 90 degrees and 30 mm. A run fails, and receives the worst value of every metric in both experiments (90 deg, 30 mm, false-loop excess 0.98), if the method crashes or consumes more than 7200 CPU seconds on an episode, writes poses of the wrong shape, non-finite or non-rigid poses, translations beyond 1 m, unreadable, malformed, non-finite, impossible or duplicate loop records, or more than 50,000 loop records, or if more than 10% of its reported relations are false within either experiment.

## Protocol

- `scripts/evaluate_train.sh` (and `scripts/evaluate.sh`) render the 24 public training episodes listed in `data/train_episodes.json` (12 per experiment) with `data/tactile_sim.py`, run every registered method, and write `scoring/scores_train.json` (`scoring/scores.json`).
- `scripts/evaluate_test.sh` takes no arguments. It renders 384 held-out episodes (192 continuous, 192 contact-loss; same families and parameter ranges, unpublished seeds) inside `eval/test/`, runs every registered method on them, and writes `scoring/scores_test.json`. Ground truth never leaves the evaluator process. This is the ranked score.
- Both evaluators also score the eval-owned NormalFlow frame-to-frame baseline under the name `normalflow`.
- Rendering and scoring are deterministic; every method sees identical inputs.

## Method Contract

Register a method by writing `checkpoints/<dir>/predict.json`:

```json
{"name": "my_method",
 "command": ["python", "-m", "my_pkg.run", "--input", "{input}", "--output", "{output}"]}
```

The command is run once per episode from the workspace root (PYTHONPATH includes the root), on one CPU core. `{input}` is an `.npz` with `gradients` (N x 120 x 160 x 2, surface gradients du, dv), `heights` (N x 120 x 160, height map in pixels integrated from the gradients), `contact_masks` (N x 120 x 160, bool) and `mm_per_pixel`. The method must write `{output}/poses.npy`: N x 4 x 4 rigid transforms, sensor pose of each frame in a common object-fixed frame, translations in mm (they are re-expressed relative to frame 0 before scoring). It may write `{output}/loops.json` = `{"loops": [{"i": int, "j": int, "T_ij": 4x4}]}` where `T_ij` is the pose of frame j expressed in frame i (mm); these are the frame-pair relations checked by `false_loop_excess`. Any other file is ignored. Every directory under `checkpoints/` that holds model or prediction artifacts but no `predict.json` is scored as a failed method. The test runs inference only; anything a method needs (trained weights, configs) must already be on disk.

## Reproducible execution and ranking

Numerical-library threads are fixed to one, and the evaluator and method have one-core CPU affinity. CPU consumption, including private child-process search, is budgeted; elapsed seconds are diagnostic only. No evaluator or reproduction script imposes a wall-clock deadline. The external job allocation may still preempt a job; incomplete runs retain complete worst-value score entries.

Method commands run with a Landlock filesystem policy: their own source, public data and stored models are readable; only their current output directory is writable. The input observation file is readable. Hidden evaluator files, repository history, other scratch files and scoring files are not readable. Temporary method files belong under `$TMPDIR` (inside the output directory). Landlock support is required; unsupported kernels fail closed. The same interface and policy apply on train and test.

Each metric contributes experiment weight times the magnitude of its coefficient times signed improvement over the reference, divided by its population standard deviation across all attempts being ranked (including failed runs). The sign comes solely from `higher_is_better`. A constant metric contributes zero. Failed methods receive every metric's worst value, so another metric cannot compensate for failure.
