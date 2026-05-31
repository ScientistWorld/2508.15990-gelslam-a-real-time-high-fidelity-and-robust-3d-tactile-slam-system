# Experiment Overview

## synthetic_long_horizon_tracking

Tests whether a tactile tracking system maintains accurate pose estimates over long synthetic tactile sequences. The experiment is designed so short-range frame-to-frame tracking is not enough: repeated contacts are present, drift can accumulate, and a successful method must recover global consistency.

## loop_closure_quality

Tests whether the system uses revisited contacts productively and safely. This experiment measures both how many loops are accepted and how often accepted loops are wrong, because accepting incorrect loop closures can make trajectory error look temporarily better on some sequences while breaking the scientific claim.

## keyframe_budget

Tests whether the tracking system keeps a practical amount of state. Tactile SLAM naturally needs dense keyframes, but a method should not improve accuracy by retaining every frame without bound when the benchmark is meant to model scalable long-horizon tracking.
