# Final hardening report

Better tactile estimates now score higher with a resolved paired margin, and the changed answer-access, comparison-editing, duplicate-record and failure-omission attacks all lose. **One requested condition remains unmet:** exhaustive two-stage matching still beats the reference slightly. The 384-episode test establishes accuracy headroom, but its 400-frame instances do not establish the paper's coverage-set efficiency advantage. This report does not claim that all hardening requirements were met.

The completed combined audit and independent reference run are from job `248ff24f-f19` (exit 0). Full measurements, including every shortcut, are in [measurements.md](eval/test/hardening_results/measurements.md), [summary.json](eval/test/hardening_results/summary.json) and [the paired cohort](eval/test/hardening_results/after_cohort_test.json). Historical 40-episode results are preserved in [the preceding report](redteam/hardening/results/HARDENING_iteration11.md) and the `before_*` JSON files under `eval/test/hardening_results/`. The original 144-frame audit remains in `REDTEAM.md`.

## REVIEW.md: changes and verification

The review identified a load-dependent 900-second wall deadline and mixed, unresolved headroom. Both were addressed together with the major remaining shortcuts before running the combined audit.

- **CPU budget instead of wall deadline.** Each method runs on one CPU core with numerical-library threads fixed to one. The 7200 CPU-second episode budget counts the process group, including private child-process search; a CPU rlimit also applies. There is no elapsed-time deadline in the reference or evaluator path. Timing is evaluator-owned diagnostic information and is never ranked. The final independent reference used at most 7.21 CPU seconds per episode, the paired reference at most 8.94, and the better variant at most 10.02: all have a wide margin. These observations are budget checks, not speed scores.
- **Paired accuracy headroom.** Replace the fragile dense-tracking variant with an honest variant that improves revisit registration while retaining the reference's local tracker. Expand the same hidden distribution from 40 to 96, then 384 independent episodes (192 per experiment). All methods see the same observations. Expand public development from 8 to 24 episodes of comparable difficulty. The 96-episode aggregate interval still crossed zero; the 384-episode interval is entirely positive.
- **Runtime answer protection.** Commands run under a fail-closed Landlock filesystem policy. They can read public code/data/models and their supplied observation file, and write their current output directory. They cannot read hidden evaluator files, answer checkpoints, repository history or audit artifacts, or change comparison/scoring files. The method may supply an arbitrary procedure; it is not restricted to reference settings. Unsupported isolation fails the method rather than exposing answers. Previously exposed test seeds were replaced with private 128-bit seeds.
- **Raw-output-only scoring.** Remove scalar-result cache reads. Every error and constraint value is recomputed from raw poses and frame-pair relations against evaluator-owned truth. Method-written summaries, success flags, timing and scores are ignored. Baseline, test size, geometry tolerances, failure caps and operating points are fixed by `eval/`.
- **Strict complete failures.** Malformed, non-finite, impossible, duplicate or oversized outputs fail. More than 10% false relations in either experiment fails the entire run. Every failed or pending method receives all five worst values in both experiments: 90 deg, 30 mm, 90 deg, 30 mm, and false-loop excess 0.98. Missing registrations/artifacts become failed entries. The provisional and final score writes contain the complete matrix.

All filesystem-isolation, child-CPU accounting, malformed-output, discovery, complete-failure-matrix and raw-rescoring checks in `eval/test/check_contracts.py` passed in the job. The final independent reference and frozen baseline match the paired run exactly across all 20 scored values. The earlier 96-episode audit also found exact agreement between algorithm seeds 0 and 1. Fixed input noise, fixed seeds and single-thread execution eliminate the observed algorithm-seed spread; uncertainty below measures variation across instances instead.

The Python packages are pinned to the versions used in the completed run: NumPy 2.4.6, SciPy 1.17.1 and opencv-python-headless 4.13.0.92. The recorded Python version is 3.11.15. `scripts/run.sh` again runs `scripts/reproduce.sh` and validation, rather than the audit recovery workflow.

## Reproduction and reference before/after

The earlier hardening restored the actual paper procedure: NormalFlow's Eq. (1) Gauss–Newton alignment, 3000 deterministic high-curvature samples, height-based depth translation, signed filtered curvature, CCS 0.85/SCR 0.30, SIFT curvature proposals with more than eight RANSAC inliers, NormalFlow verification, contact-area coverage pruning, tracking sessions and fixed-covariance LM pose-graph optimisation. It removed extra height objectives, phase-correlation/ECC initialisers, forced endpoint/odometry loop fallbacks and special loop weights. This iteration does not change that reference procedure or its training method. The frozen frame-to-frame baseline is evaluator-owned.

The gym uses noisy synthetic 6DoF tactile observations, 160x120 at 0.1268 mm/px, and the paper's offline tracking schedule. It does not reproduce the RGB-to-gradient calibration stage, GTSAM backend implementation, physical-object dataset, reconstruction or online worker timing. Those scope limits are not claims of full-paper reproduction.

The old and final numbers use different hidden samples; they are reference regeneration checks, not evidence that the method itself improved.

| Measurement | Before: reviewed 40-episode test | After: independent 384-episode test |
|---|---:|---:|
| Reference continuous rotation / translation MAE | 1.438994 deg / 0.142290 mm | 0.569465 deg / 0.056820 mm |
| Reference contact-loss rotation / translation MAE | 2.150037 deg / 0.401101 mm | 1.173963 deg / 0.142607 mm |
| Baseline continuous rotation / translation MAE | 3.166536 deg / 0.700653 mm | 3.192370 deg / 0.713247 mm |
| Baseline contact-loss rotation / translation MAE | 11.451145 deg / 2.806024 mm | 9.008843 deg / 2.463979 mm |
| Reference accepted / false relations | 659 / 0 | 5231 / 0 |
| Reference normalized rank gain | 0 | 0 |

The reference beats the simple baseline on both scientific quantities and both experiments, in the paper's direction. Removing loop closure loses decisively. On the final public slice the reference is 0.641780 deg / 0.053569 mm (continuous) and 1.442548 deg / 0.192469 mm (contact loss), versus the baseline's 3.017720 deg / 0.666038 mm and 7.759547 deg / 2.451484 mm. Train and test use separate evaluator code, disjoint seeds, the same observation contract, parameter ranges, 400-frame scale and scoring quantities. The honest variants' improvement/loss directions agree across slices.

`scoring/scores_test.json` contains only the independent reference run and fixed baseline; `scores_train.json` and `scores.json` likewise contain only reference-run results. Shortcut and variant audit results are not official ranked entries. `reference.json` stores the regenerated scaled baseline/reference under `results`. The paper's reported numbers remain unchanged under `_paper_results` and `_paper_context`. No setup was tuned to match those numbers. Experiment weights remain 0.6 continuous / 0.4 contact loss, and coefficients remain 1.0 per MAE, 0.4 per p95, 0.5 for the constraint.

## Do better results score higher?

For each metric, the audit rank is

`weight * abs(coefficient) * direction * (value - reference) / population_std(attempts)`

summed across both experiments. Direction is +1 for higher-is-better and -1 otherwise; a zero standard deviation contributes zero. The final full cohort has 22 entries, including failures. The honest sensitivity cohort has six methods. A coefficient controls importance rather than units; its sign never reverses the metric's direction. Decimal gains from different cohorts are not directly comparable in magnitude.

| Variant | Before: full / honest gain on 40 episodes | Final: full / honest gain on 384 episodes | Final paired 95% gain interval | Final train gain |
|---|---:|---:|---:|---:|
| Reference | 0 / 0 | 0 / 0 | [0, 0] | 0 |
| Prior headroom: `session_chain_dense` | +0.597 / +0.557; training timed out | Superseded by revisit-only dense variant; not replayed | — | — |
| Prior headroom: `hybrid_local_loops` | -0.040 / +0.053; mixed error changes | Superseded by revisit-only dense variant; not replayed | — | — |
| Better: `hybrid_dense_loops` | New variant | **+0.01390 / +0.12291** | **[+0.00808, +0.02530]** | **+0.17377** |
| Exhaustive two-stage matching | +0.004 / +0.024 | +0.00250 / +0.01452 | [+0.00076, +0.00625] | +0.05138 |
| Weaker: no loop closure (`nf_kf`) | -2.190 / -3.882 | -0.94222 / -3.07566 | [-0.96560, -0.91356] | -3.53958 |
| Exhaustive NormalFlow only | -3.247 / -4.484 | -0.91123 / -2.47728 | [-0.93237, -0.88300] | -3.07994 |
| Fixed frame-to-frame baseline | -1.964 / -7.161 | -0.76691 / -6.19503 | [-0.80263, -0.73287] | -6.90020 |

Intervals use 512 whole-episode paired bootstrap draws, with identical resampled inputs for every method and reference and fixed full-cohort metric standard deviations. They include p95 recomputation, not a bootstrap of already-aggregated scores. At 96 episodes the new better variant's interval was [-0.00566, +0.23545]; enlarging the test resolved that uncertainty. These intervals describe this audit distribution, not all possible methods or a future ranking cohort's normalization.

`hybrid_dense_loops` improves **all eight error metrics**, so its improvement direction is independent of normalization by any positive finite scales. Continuous-contact rotation/translation MAE is 0.521953 deg / 0.046573 mm, versus 0.569465 / 0.056820. Contact-loss MAE is 0.727279 deg / 0.110052 mm, versus 1.173963 / 0.142607. It estimates 6220 unique relations, one false (below the fixed allowance); it receives no constraint advantage. Its p95 errors also improve in both experiments.

Paired episode-level differences (better minus reference, mean +/- SE; n=192 per experiment) are -0.04751 +/- 0.01257 deg and -0.01025 +/- 0.00339 mm in continuous contact, and -0.44668 +/- 0.14260 deg and -0.03256 +/- 0.01216 mm after contact loss. The baseline's corresponding rotation losses are +2.62290 +/- 0.11190 and +7.83488 +/- 0.27581 deg. Both the paper's effect and the demonstrated honest improvement exceed observed seed noise and paired uncertainty.

## Major shortcuts: fixes and scores

“Reviewed” means the 40-episode state entering this iteration; “original” means `REDTEAM.md`'s 144-frame gym. Final gains use the full 22-entry cohort above. A **failed** row is -7.34819 and has the complete worst-value matrix in both experiments; it is never an empty result. The three scored identity fallbacks are -2.04618. Their negative directions are robust, while their decimal magnitudes depend on cohort normalization.

| Attack | Before | Fix and final hidden-test result |
|---|---|---|
| Read hidden evaluator source at runtime | Reviewed **+1.000**, perfect poses | Deny hidden files/history/audit storage to method commands; refresh exposed keys. `sc_read_hidden_test`: **failed**, permission denied. |
| Copy visible labels | Original **+0.838**; reviewed -7.22 | Test truth and regeneration keys exist only under `eval/test/`; new inputs are rendered there. `sc_labels_copy`: unmatched public-data replay returns identity, **-2.04618**. |
| Replay public generator | Original **+0.838**; reviewed -5.38 | Public generator lacks hidden keys; runtime cannot discover them. `sc_generator_replay`: identity fallback, **-2.04618**. |
| Replace ground truth | Original **+0.838**; reviewed public edit -5.38 | Eval owns truth and its renderer; its files are inaccessible to the method. Changed test-file replacement attack: **failed**. |
| Duplicate reference loop records | Original **+0.626**; reviewed **0, tie** | Reject repeated unordered frame pairs, including reversed copies. Counts earn no rank credit. `sc_duplicate_loops`: **failed**. |
| Replace baseline/comparison | Original and reviewed **0, tie** | Frozen eval-owned baseline plus runtime write isolation. Changed baseline-file replacement attack: **failed**; independent baseline unchanged. |
| Hide unlisted/orphan method | Original absent from scores; reviewed worst | Discover all registrations/artifact directories from disk, without reading a train-score allowlist. `sc_orphan` and `sc_invalid`: **failed**, all metrics present. |
| Empty/missing/NaN poses | Original evaluator crashes with no score; reviewed worst | Shape, rigid-transform, finite-value checks and complete failure replacement. `sc_empty_predictions`, `sc_nan_predictions`: **failed**. |
| Impossible translation | Original -10.13 with unbounded normalization; reviewed worst | >1 m fails before scoring; scientific errors are bounded. `sc_impossible_translation`: **failed**. |
| NaN loop transforms | Original NaNs counted valid; reviewed worst | Validate every relation before geometric checks. `sc_nan_loops`: **failed**. |
| Forge method score/summary fields | Original -4.08; reviewed -5.38 | Ignore summaries and recompute raw outputs; runtime cannot overwrite official scores. Changed score-file writer `sc_forged_scores`: **failed**. |
| Forge scalar evaluation cache | Former scalar-cache path was trusted; no prior measured attack | Delete scalar cache reads; revalidate/rescore raw checkpoints only. `sc_metric_cache_forgery`: **failed**; changed truth alters recomputed scores in the contract check. |
| Good tracking with false constraints | Original -1.416; prior gate pooled experiments | Gate each experiment separately, then fail the whole run. `sc_false_constraint`: **failed** (1576/1576 false in continuous contact), worst everywhere. |
| Constant identity tracking | Original -4.081; reviewed -5.38 | No special rule needed: actual pose errors. `sc_constant`: **-2.04618**, well below reference. |
| NormalFlow-only all-keyframe brute force | Original exhaustive variant **0, tie**; reviewed -3.247 | Full 6DoF/noisy-gradient setting and independent contact-loss experiment expose failed relocalisation. Final **-0.91123**, not a paying baseline. |
| All-keyframe two-stage brute force | Reviewed **+0.004** | **Still open: +0.00250**, CI strictly positive; see below. |

The first two brute-force rows are different procedures. Losing NormalFlow-only brute force does not close all-keyframe SIFT-plus-NormalFlow search. The earlier report's statement that no brute force outranks the reference was too broad.

## Bounds, headroom and remaining gaps

Only `false_loop_excess` is at its best bound (0) for the reference in both experiments. All eight pose-error metrics are strictly above zero. The contact-loss experiment, added in the preceding hardening pass with weight 0.4, targets the paper's documented weak-texture/delayed-relocalisation failure. This iteration retains it and enlarges the paired test rather than adding a redundant experiment. The better variant improves every error, stays away from zero, passes the safety constraint and outranks the reference beyond uncertainty. The simple baseline stays clearly below it. Thus accuracy headroom is demonstrated; no tried simple rule reaches the bound.

**Unclosed brute-force requirement.** Exhaustive two-stage matching still outranks the reference and is below the best honest improvement. Increasing the number of independent 400-frame episodes resolves accuracy uncertainty but does not increase search complexity within an instance. It therefore does not meet the user's requirement to scale instances until exhaustive search stops paying. I did not validate a sufficiently long-scan experiment within this iteration's compute. This is a remaining test-design flaw for the coverage-set efficiency claim, not a closed shortcut or merely an indistinguishable honest alternative. No metric weight, reported work count or artificial setting restriction was used to conceal it. A future change needs substantially longer individual scans and a measured private-search budget while preserving an efficient improvement path.

Other limits left explicit:

- Reconstruction is unscored and optional. Omitting it still leaves tracking scores unchanged; there is no claim that this benchmark assesses the paper's reconstruction contribution. The original omission attack is consequently outside this tracking contract and was not replayed.
- A method may omit relation records entirely, as a different pose estimator need not expose a graph. The test checks reported relations against independent truth, but cannot audit unreported internal constraints or determine from a correct matrix alone how it was obtained. Fabricated relations and answer access remain prohibited and subject to the separate shortcut grader.
- Synthetic object geometry and motion priors can favor a suitably designed estimator. Identity and public-seed generator replay lose strongly; this is not evidence that every possible hand-written simulator prior has been eliminated. Transfer to real tactile data and very long scans is unestablished.
- CPU budgeting removes load-based deadlines; cross-hardware floating-point/version invariance is not claimed. The exact serialized rerun demonstrates reproducibility in the recorded environment.
- The filesystem policy protects the direct runtime read/write attacks tested here; it is not a claim of a general adversarial operating-system security proof. No leftover-process or modified-Python-environment defenses were added.

## Job recovery and packaging

Scheduler preemptions caused the first audit job to repeat work; the 96-episode job then completed. The first enlargement job was cancelled after ten preemptions repeatedly rerendered completed inputs. The final recovery changed execution/checkpointing only, not scientific settings, scoring formulas or the original full renderer. It prioritizes missing inference, skips observations when every needed raw prediction exists, and computes the exact original contact trajectory without sensor-noise buffers for rescoring. Bitwise truth-only/full-render equality was checked for all four families and both contact regimes before transfer.

Opt-in audit recovery stores raw poses/relations and optional evaluator-owned truth under `eval/test/resume/`. Its keys include source, runtime, method artifacts and instance configuration; reviewed source snapshots and SHA-256 manifests restrict the two recovery migrations. It restores no scored scalar or success verdict. Normal no-argument evaluation uses no resume cache. Independent final reference inference uses a separate namespace, so cohort predictions never substitute for that rerun. Completed official reference/baseline values match the cohort exactly. Test answers and anything that regenerates them remain under `eval/test/`, protected during method execution.

Generated raw predictions, truth caches, downloaded artifacts and phase markers are ignored. The default synthetic setup needs no pre-existing binary data; `scripts/download.sh` is self-contained and includes real public fetch commands for optional upstream artifacts. No committed runnable path references `shared/`. The container builds from `environment/`; `scripts/run.sh` restores reference-only end-to-end reproduction. The completed job passed `python validate.py`; final local structural, score-matrix, syntax and unchanged-paper-number checks are recorded in [package_checks.json](eval/test/hardening_results/package_checks.json). The milestone remains `core_claim`, not full-paper reproduction or complete hardening.
