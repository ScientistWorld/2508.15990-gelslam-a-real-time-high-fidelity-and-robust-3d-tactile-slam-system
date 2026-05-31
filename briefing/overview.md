# Overview

- **Paper ID:** arXiv:2508.15990
- **Title:** GelSLAM: A Real-time, High-Fidelity, and Robust 3D Tactile SLAM System
- **Domain:** Robotics / Tactile Perception / SLAM
- **TL;DR:** GelSLAM is a tactile-only SLAM system that tracks long-horizon object motion and builds globally consistent tactile reconstructions by combining local tactile registration, dense keyframes, loop closure, and pose graph optimization.

## Short Summary

The paper addresses long-horizon tactile object tracking and reconstruction from vision-based tactile sensor streams. Frame-to-frame tactile tracking drifts over time because each tactile image covers only a small local patch; GelSLAM extends tactile tracking into a SLAM pipeline with keyframes, loop detection, loop verification, and global pose graph correction. The reported real-world experiments use GelSight Mini tactile videos for tracking and object scanning, with NormalFlow as the strongest frame-to-frame tracking baseline.

This workspace is a scaled synthetic substitute for the paper's full real-data reproduction. It preserves the paper's computational procedure for the tracking benchmark while replacing the large real GelSLAM dataset and physical sensor calibration with generated long-horizon tactile sequences that expose the same failure mode: drift under local frame-to-frame registration and recovery through valid loop closures.

## Key Results From Paper

- **Tracking accuracy, Table IV:** GelSLAM Online reports average axis-wise tracking MAE of 4.06, 4.38, and 3.57 degrees, and 1.00, 0.96, and 0.72 mm translation, versus NormalFlow at 7.11, 7.53, and 7.63 degrees, and 1.13, 1.21, and 0.92 mm translation.
- **Tracking statistics, Table II:** GelSLAM averages 523 frames, 68 keyframes, 21 coverage keyframes, 65 loop candidates, and 34 accepted loops over 140 long-horizon tracking episodes.
- **Reconstruction quality, Table VI:** On ten 3D-printed objects with CAD ground truth, GelSLAM reports average Chamfer Distance of 0.60 mm and average Normal Cosine Distance of 0.962.
