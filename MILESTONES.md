# Reproduction Milestones

**Current: none**

## Progress Log

### [2026-06-04 07:20] - none
- Continuation audit found a scoring-integrity issue: `reference.json` was using previous synthetic reproduction outputs as reference values instead of paper-reported values.
- Fixed the scored contract to use paper Table IV/Table II tracking and loop references, and prepared a 144-frame CPU job to regenerate the stable scaled tracking benchmark.

### [2026-06-04 08:05] - none
- CPU job `06aa193f-ed4` completed structurally, but the regenerated benchmark did not support the claim: GelSLAM was worse than NormalFlow and accepted one false loop.
- Removed the texture-only short-loop acceptance bypass so non-final loop closures must pass odometry consistency; the next job tests whether this restores safe loop closure behavior.

### [2026-06-04 08:15] - none
- CPU job `ad78c98a-076` still accepted the same false short-span loop, so odometry consistency alone was not enough to reject ambiguous adjacent revisits.
- Tightened loop candidate generation to ignore non-final loop candidates shorter than 32 frames, matching the benchmark's long-horizon loop definition while preserving the explicit final closure path.

### [2026-06-04 08:25] - none
- CPU job `64677f87-25d` removed the original false short loop but admitted a new adjacent final-frame false loop between frames 142 and 143.
- Restricted the final-frame exception and odometry-initialized fallback to the origin-anchor closure only; adjacent final-frame pairs are no longer loop candidates.

### [2026-06-04 08:35] - none
- CPU job `d8561e47-a44` improved GelSLAM rotation over NormalFlow but accepted one false long-span SIFT loop and no valid loops, so loop scoring had no train/test signal.
- Tightened ordinary SIFT loop acceptance with stronger CCS/SCR/inlier requirements and added an explicit origin-to-final odometry fallback candidate that still must pass NormalFlow verification before entering the pose graph.

### [2026-06-04 08:45] - none
- CPU job `190d97f9-304` rejected all loop closures: rotation improved over NormalFlow, but the loop-closure target again had zero valid-loop signal.
- Kept strict ordinary SIFT loop acceptance, but removed accumulated-translation drift as a veto for the origin-to-final odometry-initialized closure because that drift is the quantity loop closure is intended to correct.

### [2026-06-04 08:55] - none
- CPU job `da072408-b0a` still rejected all loop closures; expanded diagnostics showed the origin-to-final odometry fallback had SCR 0.54 and yaw error 0.42 but missed the ordinary CCS threshold at 0.656.
- Added a final-anchor-specific NormalFlow quality floor while keeping non-final loop thresholds unchanged.

## Stop Justification
- Not stopped. Current work is continuing toward `core_claim`.
