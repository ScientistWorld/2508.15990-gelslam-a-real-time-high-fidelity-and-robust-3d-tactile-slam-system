# Experiment Overview

## long_horizon_tracking

Establishes whether a tactile-only system keeps an accurate global pose estimate over long continuous contact, where short-range motion estimates accumulate drift and the sensor repeatedly revisits earlier contacts. Scored on held-out episodes over four surface-texture families, from rich to weak texture, against a fixed frame-to-frame baseline. The mean errors measure overall accuracy, the tail errors catch isolated failures, and the false-relation rate checks that any claimed relation between frames is correct.

## relocalization_after_contact_loss

Establishes whether the system recovers a consistent pose after contact is interrupted (25 frames missing after every 100), when nothing short-range connects the new contact to earlier ones. Same metrics and families. The weak-texture episodes are where recovery is hardest; segments that are never related back to earlier contact carry large errors.
