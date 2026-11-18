# Overview

- **Paper ID:** arXiv:2508.15990
- **Title:** GelSLAM: A Real-time, High-Fidelity, and Robust 3D Tactile SLAM System
- **Domain:** Robotics / Tactile Perception / SLAM
- **TL;DR:** Tactile-only SLAM: NormalFlow tracking with curvature-based failure detection and keyframes, two-stage (SIFT on curvature + NormalFlow) loop detection over a coverage set, and pose-graph optimisation for long-horizon 6DoF tracking and reconstruction.

## This Workspace

A scaled synthetic substitute for the paper's tracking experiments. A simulated GelSight-Mini-style sensor slides over textured convex objects from four texture families. Two experiments are scored on 384 held-out episodes that exist only inside `eval/test/`: long-horizon tracking with continuous contact (paper Table IV) and tracking with periodic contact loss (paper Fig. 11). The frame-to-frame NormalFlow baseline is owned by the evaluator. Methods are run by the evaluator through a `predict.json` command, so the held-out inputs and ground truth never appear on disk before the test.

## Key Results From the Paper

- **Table IV (tracking MAE, per axis):** GS-Online 4.06/4.38/3.57 deg and 1.00/0.96/0.72 mm; NormalFlow 7.11/7.53/7.63 deg and 1.13/1.21/0.92 mm.
- **Table II:** 523 frames, 68 keyframes, 21 coverage keyframes, 65 loop candidates and 34 loops per episode on average.
- **Fig. 11:** after removing 25 frames every 100 frames, tracking error is nearly identical to the full episodes.
- **Table VI (reconstruction, not scored here):** average Chamfer Distance 0.60 mm, normal cosine similarity 0.962.

## Reproduced Results (held-out test, 384 episodes)

See `scoring/scores_test.json` and `HARDENING.md`. GelSLAM reduces the continuous-contact rotation/translation MAE of the NormalFlow baseline by more than half, relocalises after contact loss where the baseline cannot, and reports no false loops.
