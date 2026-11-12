# Research Direction

## Research Problem

Long-horizon 6DoF pose tracking from local tactile contact patches. Short-range registration is accurate but drifts, and contact breaks leave new contacts unrelated to earlier ones. The test rewards lower drift on continuous contact and better recovery after contact loss, under the constraint that asserted frame-pair relations are correct.

## Where there is room

The reference leaves error on the table in both experiments: drift between revisits on continuous contact, and episodes on low-texture surfaces where contact-loss recovery fails or is delayed and whole segments stay misplaced. Approaches that recover relations more reliably on weak texture, place unrecovered segments better, use the available relations more effectively, or register more precisely all show up directly in the metrics.

## Approach Scope

Any tactile-only estimator that consumes the same observations and writes the standard outputs: alternative registration, representations, relation search, optimisation, robust estimation or learned components trained on public data.

## Out of Bounds

- Reading or importing evaluator code, held-out configuration or ground truth.
- Hard-coding the simulator's generating process (seeds, trajectory family) instead of estimating from observations.
- Reporting fabricated or trajectory-derived frame-pair relations, or relations you did not estimate.
- Leaving unregistered artifacts in `checkpoints/` or editing evaluator, baseline or score files.
