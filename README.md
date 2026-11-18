# GelSLAM: A Real-time, High-Fidelity, and Robust 3D Tactile SLAM System

<!-- scope-note -->
> [!NOTE]
> **Not a full reproduction of the paper.** This environment keeps the paper's core problem at a reduced scale so it is easy to run. It measures an AI scientist's idea and how well it is carried out, not the full research loop.

<!-- hardening-note -->
> [!NOTE]
> **Red-teamed and hardened.** A red team tried to score on this environment's hidden test without doing better research, and the environment was then fixed against the shortcuts that worked: see [`REDTEAM.md`](REDTEAM.md) and [`HARDENING.md`](HARDENING.md). The environment as it was before is kept as branch [`pre-hardening`](../../tree/pre-hardening).

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2508.15990"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2508.15990-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| **Paper ID** | [2508.15990](https://arxiv.org/abs/2508.15990) |
|:---|:---|
| **Domain** | Robotics / Tactile Perception / SLAM |
| **TL;DR** | GelSLAM is a tactile-only SLAM system that tracks long-horizon object motion and builds globally consistent tactile reconstructions by combining local tactile registration, dense keyframes, loop closure, and pose graph optimization. |

## Summary

The paper addresses long-horizon tactile object tracking and reconstruction from vision-based tactile sensor streams. Frame-to-frame tactile tracking drifts over time because each tactile image covers only a small local patch; GelSLAM extends tactile tracking into a SLAM pipeline with keyframes, loop detection, loop verification, and global pose graph correction. The reported real-world experiments use GelSight Mini tactile videos for tracking and object scanning, with NormalFlow as the strongest frame-to-frame tracking baseline.

This workspace is a scaled synthetic substitute for the paper's full real-data reproduction. It preserves the paper's computational procedure for a CPU-sized tracking and reconstruction benchmark while replacing the large real GelSLAM dataset and physical sensor calibration with generated long-horizon tactile sequences that expose the same failure mode: drift under local frame-to-frame registration, recovery through valid revisits, and reconstruction quality that depends on globally consistent poses.

## Problem

How can a tactile-only perception system estimate object pose and reconstruct touched object surface geometry accurately over long horizons when each tactile observation covers only a small local patch and short-range tracking accumulates drift?

## The paper's method

GelSLAM turns local tactile tracking into full tactile SLAM. The core contribution is not a generic learned pose regressor; it is a geometric pipeline that estimates relative motion from tactile-derived differential surface signals, selects keyframes, detects revisited tactile contacts, verifies loop closures, and optimizes a pose graph to remove long-horizon drift.

## Run it

```bash
pip install sciworld
sw research 2508.15990 --mode innovate --agent claude-code
sw evaluate 2508.15990
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

