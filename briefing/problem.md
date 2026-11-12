# Problem Definition

## Research Question

How can a system that sees only a stream of local tactile contact patches (GelSight-style surface-gradient, height and contact-mask images) estimate the sensor's 6DoF pose relative to the object accurately over long horizons, including after contact is lost and re-established?

## Why It Matters

Robots often manipulate objects under occlusion or close contact, where cameras cannot observe the contact. A tactile-only long-horizon tracker supports in-hand manipulation, surface exploration and object scanning using touch alone. Each tactile observation covers only a few square millimetres, so estimates that compose short-range motions accumulate drift, and after a contact break nothing short-range relates the new contact to the earlier ones.

## Success Criteria

A successful system produces low long-horizon rotation and translation error relative to the first frame, keeps its tail errors small, recovers a consistent pose after contact interruptions, and never asserts relations between frames that are geometrically wrong. In this benchmark (a scaled synthetic substitute for the paper's real GelSight dataset), success means beating the fixed frame-to-frame registration baseline on the held-out episodes in both experiments without failing the false-relation constraint.
