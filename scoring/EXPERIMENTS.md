# Experiment Overview

## synthetic_long_horizon_tracking

Tests whether a tactile tracking system maintains accurate pose estimates over long synthetic tactile sequences. The experiment is designed so short-range frame-to-frame tracking is not enough: repeated contacts are present, drift can accumulate, and a successful method must recover global consistency.

## loop_closure_quality

Tests whether the system uses revisited contacts productively and safely. This experiment measures both how many loops are accepted and how often accepted loops are wrong, because accepting incorrect loop closures can make trajectory error look temporarily better on some sequences while breaking the scientific claim.

## Keyframe Diagnostics

Raw keyframe counts are kept in method artifacts for inspection, but they are not part of the automated score. The scaled benchmark contains 144 frames, whereas the paper reports keyframe statistics over substantially longer real episodes, so direct raw-count comparison is not a stable paper-to-reproduction metric.
