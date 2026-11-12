# Paper's Method (GelSLAM)

## Key Contribution

GelSLAM turns local tactile tracking into tactile SLAM. It treats GelSight images as differential representations: normal maps (first order) and curvature maps (second order), rather than nearly flat point clouds. Three modules run on them: tracking with failure detection and keyframes, loop closure with a two-stage detector, and pose-graph optimisation. (Reconstruction is a fourth module that this benchmark does not score.)

## Computational Steps (as implemented in `method/gelslam_sim/`)

1. **Geometry per frame** (Section III-C): normals N from the gradients; curvature L = divergence of the gradient field, Gaussian filtered (5x5 at this half resolution, i.e. the paper's 7x7 at 320x240), zeroed outside the eroded contact mask and clipped; height H and contact mask C as given.
2. **NormalFlow registration** (IV-A1, Eq. 1): Gauss-Newton on the normal-alignment objective over the 3000 highest-|curvature| reference pixels (rotation and in-plane translation), then z translation from the mean height difference. Ported from the released NormalFlow code.
3. **Failure detection** (IV-A2): Curvature Cosine Similarity and Shared Curvature Ratio; a registration fails if CCS < 0.85 or SCR < 0.3 (the paper's tracking setting).
4. **Tracking and keyframes** (IV-A3): each frame is registered to the latest keyframe, initialised from the previous frame's estimate. On failure the previous frame becomes a keyframe; if the previous frame already is the keyframe, tracking is lost and a new tracking session starts.
5. **Coverage set** (IV-B1): greedy set of keyframes that each contribute more than 0.2 mm^2 of boundary-weighted contact area not covered by their neighbours; redundant ones are pruned.
6. **Loop detection** (IV-B2): for each new keyframe and each active coverage keyframe (except its immediate predecessor), SIFT features of the curvature maps are matched (cross-check), a planar similarity transform is fitted with RANSAC, pairs with more than 8 inliers become candidates, and NormalFlow initialised from that transform verifies them with the same CCS/SCR test.
7. **Pose graph** (IV-B3): Levenberg-Marquardt over SE(3) keyframe poses with a fixed covariance (0.01 rad, 0.1 mm) on all tracking and loop constraints; each tracking session is anchored by an identity prior (as in the release) until a loop merges it with an older session. Frame poses follow from their keyframe.

The stream is processed synchronously, so no keyframe is skipped by the loop module (GS-Offline schedule; the paper's Table IV shows GS-Online within 0.1 deg of it).

## Main Claims

- GelSLAM reduces long-horizon tracking error relative to frame-to-frame NormalFlow by 46% (rotation) and 17.5% (translation) on 140 real episodes (Table IV).
- Loop closures are verified so that false loops are rejected; none were false in the reconstruction study (Section VI-B). SIFT-only loop acceptance is worse than no loops (GS-OnlySIFT); NormalFlow-only loop search is slower and misses loops (GS-OnlyNF).
- After simulated contact loss the method relocalises and tracks nearly as well as on the full episodes (Fig. 11), though relocalisation can be delayed when contact resumes far from earlier contacts; low-texture objects yield few loops (Discussion).

## Scaled Reproduction Scope

Data: synthetic GelSight-Mini-style observations at half resolution instead of the real dataset; the paper's photometric-stereo calibration is replaced by simulated noisy gradients and Poisson-integrated heights. Episodes are 400 frames. The algorithm and its thresholds follow the paper and the released code. Reconstruction is not scored.
