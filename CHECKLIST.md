# Reproduction Checklist

## Briefing
- [x] `briefing/problem.md`, `briefing/evaluation.md` describe the task, metrics and method contract without the paper's method
- [x] `briefing/method.md` documents GelSLAM's computational steps as implemented
- [x] `briefing/overview.md` summarises the paper and the scaled benchmark

## Scoring
- [x] `scoring/reference.json`: two experiments, paper Table IV values, `_paper_context` for unscaled numbers
- [x] `scoring/TARGETS.md`, `CONSTRAINTS.md`, `DIRECTION.md`, `EXPERIMENTS.md` match the hardened gym
- [x] `scoring/scores.json`, `scores_train.json`, `scores_test.json` regenerated from the final code (reference + frozen baseline)

## Code and scripts
- [x] `method/gelslam_sim/`: NormalFlow port, tracking/keyframes/sessions, coverage set, SIFT-curvature + NormalFlow loop detection, LM pose graph
- [x] Eval-owned frozen NormalFlow baseline in `eval/train/` and `eval/test/`; public copy in `baseline/`
- [x] `scripts/evaluate_test.sh` (no arguments) runs every registered method on hidden inputs
- [x] `scripts/run.sh` reproduces the reference end to end; `redteam/hardening/audit.sh` reruns the audit
- [x] `python validate.py` passes

## Integrity
- [x] Test inputs/ground truth only in `eval/test/`, produced at test time
- [x] Every scored number recomputed from raw outputs; failures get worst values
- [x] Benefit metrics and a constraint metric (false-loop excess + gate) in both experiments

## Remaining hardening requirement
- [ ] Scale individual scans until exhaustive two-stage search no longer outranks the reference. It still has a small positive gain on the final test; see `HARDENING.md`.
