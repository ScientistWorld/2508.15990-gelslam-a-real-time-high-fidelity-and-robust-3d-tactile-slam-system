# Paper's Method

## Key Contribution

GelSLAM turns local tactile tracking into full tactile SLAM. The core contribution is not a generic learned pose regressor; it is a geometric pipeline that estimates relative motion from tactile-derived differential surface signals, selects keyframes, detects revisited tactile contacts, verifies loop closures, and optimizes a pose graph to remove long-horizon drift.

## Approach

The method operates on a stream of GelSight tactile images. Each frame is converted into geometric representations used by the tracking and loop modules, including contact-relevant image information, surface normals, curvature, and masks. Consecutive or selected tactile frames are registered using NormalFlow-style normal-map alignment to estimate relative sensor/object motion.

Because tactile sensing is local, GelSLAM inserts keyframes frequently. A subset of keyframes represents unique surface coverage, while candidate loop pairs are proposed when the current contact resembles an earlier contact. Loop detection uses curvature-based local feature matching to find plausible revisits and then refines or rejects each candidate with tactile registration and overlap/consistency checks. Accepted odometry and loop constraints are added to a pose graph, which is optimized to correct accumulated drift.

For reconstruction, the optimized poses are used to fuse tactile surface observations into a global object mesh. This workspace focuses on the scaled synthetic long-horizon tracking benchmark, but the briefing keeps the reconstruction numbers as context for the paper's broader claims.

## Main Claims

- **Primary claim:** GelSLAM improves long-horizon tactile tracking over frame-to-frame NormalFlow by correcting drift through valid loop closures while remaining online-capable.
- **Constraint claim:** The improvement depends on accepting correct loops and rejecting false loops; false loop closures can corrupt the global trajectory and reconstruction.
- **Resource/behavior claim:** Dense keyframe insertion is expected for tactile SLAM because adjacent contacts can have limited overlap, but the number of keyframes and loop candidates must remain bounded enough for real-time or near-real-time operation.
- **Secondary claim:** The same optimized tactile pose graph supports high-fidelity 3D reconstruction, with the paper reporting submillimeter average Chamfer Distance and high normal-map agreement on 3D-printed objects.

## Scaled Reproduction Scope

This reproduction evaluates a synthetic long-horizon tactile tracking substitute rather than the full physical GelSight dataset. The benchmark should still implement the paper's computational steps: tactile geometry extraction, NormalFlow baseline tracking, GelSLAM keyframe management, loop proposal, loop verification, pose graph optimization, and trajectory evaluation. Scaling down data source and sequence size is acceptable; replacing the algorithm with a learned end-to-end pose predictor or unrelated tracker is not.
