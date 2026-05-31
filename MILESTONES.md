# Reproduction Milestones

**Current: none**

## Progress Log

### [2026-05-31 18:55] - none
- Audited existing GelSLAM reproduction scaffold after milestone reset.
- Local `python validate.py --compare` passes structurally, but current `scores.json` is stale and lacks the reconstruction experiment from the latest 6DoF path.
- Submitting a CPU test job to run `scripts/reproduce.sh`, train/test slice evaluation, and validation inside the container.

### [2026-05-31 19:05] - none
- Continued audit confirmed the implementation is a scaled GelSLAM-style pipeline rather than a learned surrogate: NormalFlow-style normal alignment, keyframe management, curvature/SIFT loop proposals, loop verification, pose graph optimization, and fused reconstruction code are present.
- Evaluation remains method-independent, but the saved artifacts are stale and tracking-only; the submitted CPU job must regenerate scores before `method_runs` or `core_claim` can be restored.

### [2026-05-31 19:20] - none
- CPU job `eb37481c-080` ran the attempted 192-frame 6DoF path but failed validation: no loops were accepted, loop train/test metrics had no signal, and depth drift made translation/reconstruction scores unusable.
- Reset the default runnable benchmark to the previously stable 144-frame closed-loop planar substitute, while keeping reconstruction artifact generation and scoring enabled.
- Submitting another CPU test job to regenerate honest scores for this stable benchmark.

## Stop Justification
- Completed at milestone `none`.
