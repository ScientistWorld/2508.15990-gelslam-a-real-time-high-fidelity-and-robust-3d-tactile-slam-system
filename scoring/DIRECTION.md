# Research Direction

## Research Problem

This benchmark asks how to perform long-horizon tactile object tracking and touched-surface reconstruction when each observation is a small local contact patch. The central difficulty is accumulated drift: local frame-to-frame registration can be accurate over short ranges but loses global consistency over long sequences unless revisits are detected and used safely. Reconstruction quality then depends on the same global consistency.

## Core Contribution

The paper's contribution is a tactile SLAM formulation for local tactile streams. Future improvements should target the same family of ideas: robust local tactile registration, keyframe management, loop proposal, loop verification, robust pose graph correction, surface fusion, and the interaction between these pieces.

## Approach Scope

Scientists may modify the local alignment objective, feature representation, keyframe policy, loop candidate search, loop acceptance criteria, pose graph optimizer, robust loss, surface fusion rule, or scheduling. They may also add ablations or diagnostics that clarify which part improves tracking or reconstruction, provided the method still operates on the same tactile observation stream and solves the same long-horizon task.

## Out of Bounds

- Replacing the SLAM problem with direct supervised full-trajectory prediction from the complete sequence.
- Using ground-truth poses, ground-truth loop labels, or hidden synthetic generator state at inference time.
- Changing the benchmark data, seeds, sequence distribution, or metric definitions to make the task easier.
- Omitting NormalFlow as the frame-to-frame baseline comparison.
- Optimizing only trajectory error while allowing high false loop rate or unbounded keyframe growth.
- Generating reconstruction outputs from hidden target surfaces or ground-truth poses rather than from the method's estimated poses and tactile observations.
