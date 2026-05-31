# Problem Definition

## Research Question

How can a tactile-only perception system estimate object pose accurately over long horizons when each tactile observation covers only a small local surface patch and frame-to-frame tracking accumulates drift?

## Why It Matters

Robots often manipulate objects under occlusion or close contact, where cameras cannot reliably observe the contact geometry. A tactile long-horizon tracker can support in-hand manipulation, surface exploration, and object modeling using touch alone.

## Success Criteria

A successful system should produce low long-horizon rotation and translation error, recover from drift when the sensor revisits previously touched regions, avoid false loop closures, and keep its retained state within a practical range. In this scaled synthetic benchmark, success means outperforming the fixed frame-to-frame tactile registration baseline on trajectory error while maintaining low false loop rate.
