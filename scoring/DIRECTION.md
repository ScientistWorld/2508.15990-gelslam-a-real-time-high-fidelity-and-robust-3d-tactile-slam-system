# Research Direction

## Research Problem

This benchmark asks how to perform long-horizon tactile object tracking and touched-surface reconstruction when each observation is a small local contact patch. The central difficulty is accumulated drift: short-range estimates can be accurate locally but lose global consistency over long sequences unless revisited regions are recognized and used safely. Reconstruction quality then depends on the same global consistency.

## Core Problem to Preserve

Future improvements should target the same problem family: tactile-only long-horizon tracking and touched-surface reconstruction from local contact streams, with explicit attention to drift, repeated contacts, and false-revisit risk.

## Approach Scope

Scientists may use alternative representations, uncertainty models, optimization strategies, temporal policies, or reconstruction procedures, provided the method still operates on the same tactile observation stream, satisfies the no-oracle constraints, and produces the standard output artifacts.

## Out of Bounds

- Replacing the tactile tracking problem with direct supervised full-trajectory prediction from the complete sequence.
- Using ground-truth poses, ground-truth loop labels, or hidden synthetic generator state at inference time.
- Changing the benchmark data, seeds, sequence distribution, or metric definitions to make the task easier.
- Omitting the packaged frame-to-frame baseline comparison.
- Optimizing only trajectory error while allowing high false-revisit rate or unbounded retained-state growth.
- Generating reconstruction outputs from hidden target surfaces or ground-truth poses rather than from the method's estimated poses and tactile observations.
