# Problem Definition

## Research Question

How can a tactile-only perception system estimate object pose and reconstruct touched object surface geometry accurately over long horizons when each tactile observation covers only a small local patch and short-range tracking accumulates drift?

## Why It Matters

Robots often manipulate objects under occlusion or close contact, where cameras cannot reliably observe the contact geometry. A tactile long-horizon tracker can support in-hand manipulation, surface exploration, and object modeling using touch alone.

## Success Criteria

A successful system should produce low long-horizon 6DoF rotation and translation error, recover from drift when the sensor revisits previously touched regions, avoid false revisit links, and reconstruct a geometrically faithful fused touched surface. In this scaled synthetic benchmark, success means outperforming the fixed frame-to-frame tactile registration baseline on trajectory error, maintaining low false revisit rate, and producing a fused surface close to the known touched target surface.
