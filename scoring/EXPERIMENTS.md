# Experiment Overview

## synthetic_long_horizon_tracking

Tests whether a tactile tracking system maintains accurate pose estimates over a 192-frame synthetic tactile sequence. The experiment is designed so short-range frame-to-frame tracking is not enough: repeated contacts are present, drift can accumulate, and a successful method must recover global consistency.

## loop_closure_quality

Tests whether the system uses revisited contacts productively and safely on the scaled 192-frame sequence. This experiment measures both how many loops are accepted and how often accepted loops are wrong, because accepting incorrect loop closures can make trajectory error look temporarily better on some sequences while breaking the scientific claim.

## synthetic_reconstruction

Tests whether estimated poses support coherent touched-surface reconstruction. The experiment compares fused surface points and normals against the known target surface sampled by the tactile sequence, so improvements require both accurate alignment and consistent surface fusion.
