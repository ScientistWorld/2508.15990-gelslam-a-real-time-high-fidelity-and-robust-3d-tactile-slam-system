# Scientist Constraints

These constraints define what future scientist agents must hold fixed when trying to improve this benchmark. The goal is to improve long-horizon tactile tracking and reconstruction behavior, not to win by changing the task into a different perception problem.

## Data

Use only the provided synthetic long-horizon tactile tracking and reconstruction benchmark and its fixed generation seed. Do not add real tactile datasets, rendered CAD assets, or hand-labeled revisit annotations beyond what the benchmark generator provides. The benchmark is deliberately scaled down from the paper's real dataset, so adding richer data would change the reproduction target. Train/test slice scores are diagnostics; the primary benchmark is the full fixed closed trajectory in `scoring/scores.json`.

## Inputs

Use the same synthetic tactile observation stream available to all methods. Do not use hidden generator state, future frames unavailable at the current timestep for online tracking, ground-truth pose, ground-truth revisit labels, or target reconstruction points as method inputs. Ground truth and target surfaces are for evaluation only.

## Baseline Comparison

Report the packaged frame-to-frame tactile registration baseline on the same fixed sequence whenever reporting an improved method. The central claim is relative to short-range tracking drift, so results without that comparison are incomplete.

## Evaluation

Use the fixed metrics: `rotation_mae_deg`, `translation_mae_mm`, `rotation_p95_deg`, `translation_p95_mm`, `terminal_rotation_error_deg`, `terminal_translation_error_mm`, `accepted_loops`, `valid_loops`, `valid_loop_rate`, `false_loop_rate`, `loop_span_rotation_mae_deg`, `loop_span_translation_mae_mm`, `loop_rotation_error_deg`, and `loop_translation_error_mm`. Do not remove `false_loop_rate`; it is the constraint metric that prevents trivial improvements by accepting excessive or incorrect revisits. Do not remove `valid_loops` or `valid_loop_rate`; together they prevent methods from satisfying the revisit target by abstaining from revisits or by accepting many low-quality candidates. Fused reconstruction artifacts are recorded as diagnostics in method artifacts, but they are not scored because the scaled benchmark has a different episode length and reconstruction target from the paper's real-data setting.

## Procedure

The submitted method must remain a tactile long-horizon tracking or reconstruction method. It may use any strategy that consumes the same tactile observation stream and produces the same artifact format. It must not replace the task with direct supervised trajectory regression from the whole sequence, offline smoothing using ground-truth-like future information, oracle reconstruction from the synthetic generator, or a non-tactile localization source.

## Compliance Checklist

- [ ] Uses only the provided synthetic tactile benchmark data and fixed seeds
- [ ] Does not use ground-truth pose or revisit labels as method inputs
- [ ] Reports the packaged frame-to-frame baseline on the same fixed sequence
- [ ] Reports all required metrics
- [ ] Keeps `false_loop_rate` as a constraint metric
- [ ] Stays within tactile tracking and reconstruction rather than switching to an unrelated sequence regression or oracle-localization paradigm
