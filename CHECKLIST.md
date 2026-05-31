# Reproduction Checklist

## Briefing

- [x] `briefing/problem.md` documents the method-agnostic task
- [x] `briefing/evaluation.md` documents metrics and protocol
- [x] `briefing/method.md` documents GelSLAM's actual computational procedure
- [x] `briefing/overview.md` summarizes the paper and scaled reproduction scope

## Scoring

- [x] `scoring/reference.json` records paper-anchored reference values
- [x] `scoring/TARGETS.md` lists primary and constraint targets
- [x] `scoring/CONSTRAINTS.md` lists benchmark constraints for future scientists
- [x] `scoring/DIRECTION.md` scopes future research directions
- [x] `scoring/EXPERIMENTS.md` explains experiment purpose without method details
- [x] `scoring/scores.json` records reproduced run outputs

## Code And Scripts

- [x] Method code implements GelSLAM-style tracking computational steps
- [x] Full 6DoF tracking and reconstruction path is implemented for the scaled benchmark
- [ ] Full 6DoF tracking and reconstruction path has been validated in the container
- [x] NormalFlow baseline is available for the same synthetic benchmark
- [x] Evaluation code reports all required metrics
- [x] `scripts/run.sh` regenerates the benchmark, baseline, method outputs, and scores before validation

## Documentation Integrity

- [x] Synthetic benchmark is explicitly described as scaled substitute data
- [x] Documentation states that the GelSLAM computational procedure must be preserved
- [x] Benefit metrics and constraint metrics are both represented
- [x] Paper Table II, Table IV, and Table VI values are captured where relevant
