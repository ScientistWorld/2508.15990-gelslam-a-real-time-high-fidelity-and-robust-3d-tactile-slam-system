# Scientist Constraints

## Data

Use only the tactile observations the evaluator passes to your command. The public simulator (`data/tactile_sim.py`) and training episodes (`data/train_episodes.json`) may be used freely for development, tuning and training; the held-out episodes are rendered only inside `eval/test/` at test time. Do not read, import or modify anything under `eval/` from method code, and do not modify the evaluators, the simulator copy they use, or the scoring files.

## Inputs and outputs

Per episode the method receives surface gradients, heights, contact masks and the pixel size, and must return one rigid 6DoF pose per frame (and optionally frame-pair relations). It may use all frames of the episode (the paper's offline schedule is allowed). It must not use ground-truth poses, simulator seeds or generator state at inference.

## Baseline comparison

The evaluator always scores its own frozen NormalFlow frame-to-frame baseline as `normalflow`; report it alongside any improvement.

## Compute

Each episode is processed by one invocation on one CPU core and must finish within 15 minutes. The test runs inference only; train beforehand and store weights on disk.

## Evaluation

The metrics are fixed: per-axis rotation and translation MAE, 95th-percentile rotation and translation error, and the false-relation rate, for both experiments. Do not drop `false_loop_rate`: reporting relations is optional, but any relation you report must be geometrically correct.

## Compliance checklist

- [ ] Method registered with `checkpoints/<dir>/predict.json`; no stray artifact directories under `checkpoints/`
- [ ] No access to `eval/`, ground truth or simulator seeds at inference
- [ ] Runs on the public training episodes before submitting
- [ ] All reported frame-pair relations are real estimates, not derived to inflate counts
