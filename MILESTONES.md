# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-31 17:38] - core_claim
- Packaged a scaled synthetic long-horizon tactile tracking benchmark for GelSLAM.
- Implemented the recognizable GelSLAM tracking procedure: tactile geometry extraction, NormalFlow-style alignment, CCS/SCR checks, keyframe management, curvature-based loop proposal, loop verification, and pose graph optimization.
- Reproduced the core tracking claim on the packaged benchmark: GelSLAM Online improves over frame-to-frame NormalFlow on rotation and translation error while accepting valid loop closures with zero measured false-loop rate.

### [2026-05-31 17:43] - core_claim
- Continuation audit after milestone reset confirmed that the implementation is a scaled GelSLAM tracking reproduction rather than a surrogate.
- Local structural validation passed with `python validate.py --compare`; the final evaluator execution is submitted as a CPU container test because the login-node Python lacks NumPy/SciPy/OpenCV.

## Stop Justification
- Current result supports `core_claim` for the documented scaled synthetic tracking setting. The full physical GelSight 6DoF reconstruction benchmark remains out of scope for this package because it requires the 73 GB released dataset plus ROS2/GTSAM reconstruction infrastructure.
