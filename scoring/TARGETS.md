# Evaluation Targets

Every target corresponds to an experiment and metric in `scoring/reference.json` and is emitted for every method by `scripts/evaluate_test.sh` (ranked, 40 held-out episodes) and `scripts/evaluate_train.sh` (8 public episodes). The benchmark is a scaled synthetic substitute for the paper's real GelSight Mini data; reference.json keeps the paper's Table IV numbers, which are on a different scale.

## Primary: long_horizon_tracking (weight 0.6)

Continuous-contact tracking over 400-frame episodes (paper Table IV).

- **Primary metric:** `rotation_mae_deg` (lower is better, coefficient 1.0)
- `translation_mae_mm` (lower, 1.0)
- `rotation_p95_deg` (lower, 0.4)
- `translation_p95_mm` (lower, 0.4)
- Constraint: `false_loop_rate` (lower, 0.5)

## Secondary: relocalization_after_contact_loss (weight 0.4)

Tracking with three contact breaks per 400-frame episode (paper Section V-E, Fig. 11).

- **Primary metric:** `rotation_mae_deg` (lower, 1.0)
- `translation_mae_mm` (lower, 1.0)
- `rotation_p95_deg` (lower, 0.4)
- `translation_p95_mm` (lower, 0.4)
- Constraint: `false_loop_rate` (lower, 0.5)

## Constraint gate

A method whose reported frame-pair relations are more than 10% false over the whole test, or whose run fails (crash, timeout, malformed or impossible output), receives the worst value of every metric in both experiments.

## How to run

`bash scripts/evaluate_train.sh` during development; `bash scripts/evaluate_test.sh` (no arguments) for the held-out score. Register methods as described in `briefing/evaluation.md`.
