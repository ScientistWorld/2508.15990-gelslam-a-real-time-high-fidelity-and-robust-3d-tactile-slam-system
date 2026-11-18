# Hardening report (iteration 11)

**Outcome.** The test was rebuilt so that the reproduced method is the paper's GelSLAM (faithful NormalFlow and two-stage loop closure, no added fallbacks). The held-out episodes and their ground truth exist only in `eval/test/` and are rendered at test time, and every number is recomputed from raw poses and loop records. Better results now score higher and weaker ones lower, and every shortcut the red team ran through the old test now ties the reference or scores far below it. One shortcut is still open on purpose: reading the hidden evaluator's source at runtime. A known limitation: the honest improvements I found beat the reference by modest margins, a few standard errors on some metrics and not on others (details below).

Full numbers: `redteam/hardening/results/` (`final_scores_*.json`, `variants_*.json`, `shortcuts_test.json`, `rank_*.md|json`). Audit driver: `redteam/hardening/audit.sh` (variants in `variants.py`, shortcuts in `shortcuts.py`, rank arithmetic in `rank.py`). Earlier passes are kept for reference: `results/run1_20_episodes/` (first 20-episode test) and `results/run2_raw_false_loop_rate/` (before the false-loop metric change).

## What changed

| Problem (REDTEAM.md) | Fix |
|---|---|
| Test labels and the generator that recreates them were public (`data/synthetic_tracking/loop_patch.npz`, `make_trajectory`) | 40 held-out episodes (24 continuous-contact, 16 contact-loss) are defined only in `eval/test/evaluate_test.py`. They are rendered by an eval-owned copy of the simulator at test time and given to methods as observations only; ground truth never leaves the evaluator process. The public simulator and its 8 training episodes (`data/`) cannot reproduce them. |
| Evaluator read an editable dataset and scored pre-written artifacts | The method needs no training, so the hidden test **runs** each method on the hidden inputs through a `predict.json` command and scores what it writes. |
| Method roster came from editable `scores_train.json`; unlisted or failed methods were skipped | The test discovers every `checkpoints/**/predict.json`. Any artifact directory without one is scored as a failed method. There is no allowlist. |
| Failed or NaN runs wrote no scores; NaN loops counted as valid | Crash, timeout (15 min per episode, process-group kill), wrong shape, non-finite, non-rigid or impossible (>1 m) poses, unreadable or oversized loop files, or >10% false relations make the run **failed**: worst value in every metric of both experiments. A provisional worst-case score file is written before any method runs, and the final file is written atomically. |
| Loop counts were gameable (duplicates scored +0.63) | Raw counts are no longer scored. Loop records are deduplicated by frame pair, and malformed or non-finite records count as false. The constraint is `false_loop_excess` (false fraction above a 2% verification allowance) plus the 10% gate. |
| Baseline came from editable `baseline/` code | The evaluator owns a frozen NormalFlow frame-to-frame baseline (`eval/*/frozen_normalflow.py`), always scored as `normalflow`. |
| Per-episode errors unbounded (1e6 mm inflated the normalisation) | Per-frame errors are capped at 90° / 30 mm; translations above 1 m mark the run as failed. |
| Reproduction departed from the paper (LM with an extra height residual, 900 samples, phase-correlation/ECC initialisers, odometry-initialised loop fallback that produced all 4 loops, extra gates, SCR 0.35, ≥12 inliers, unfiltered abs-Laplacian curvature) | `method/gelslam_sim/` is a port of the released NormalFlow (Gauss-Newton on Eq. 1, 5-DoF + tz from heights, 3000 highest-curvature samples) and of GelSLAM's tracker (keyframes, sessions), coverage graph (0.2 mm²), two-stage loop detection (SIFT on the filtered signed curvature, >8 RANSAC inliers, NormalFlow verification), CCS 0.85 / SCR 0.3, and LM pose graph with fixed covariance and per-session priors. |
| One 144-frame stream; train/test were interleaved blocks of it; observations had noiseless normals | New simulator: four texture families, curved objects, 6DoF rolling motion, gel indentation, noisy gradients (sensor-fixed bias and pattern, per-frame gel distortion, pixel noise) and Poisson-integrated heights. 8 public training episodes; 40 held-out episodes with unpublished seeds. |
| Paper's efficiency/robustness claims untested; reference at the bound of the loop-rate metrics | New scored experiment `relocalization_after_contact_loss` (paper Fig. 11: 25 frames removed after every 100). This is where the paper's method falls short on weak texture. |

`scoring/reference.json`: the paper's Table IV numbers are kept unchanged under each experiment's `_paper_results` (they are on the real-data scale, not the gym's), and `results` now lists the reproduced reference and the eval-owned baseline on the held-out test. The primary *label* of `long_horizon_tracking` is `rotation_p95_deg`. Per-episode means are heavy-tailed: one unrecovered tracking loss puts a held-out episode at 21°, and without it the test mean is 0.58° vs 0.66° on train. That makes the mean MAE a poor slice-independent headline. Coefficients, and so the rank, are unchanged; MAE keeps the largest coefficient.

Weights changed from tracking 0.7 / loop-closure 0.3 to `long_horizon_tracking` 0.6 / `relocalization_after_contact_loss` 0.4. The old loop-closure experiment scored metadata (counts, loop-span errors that equalled the tracking error), not a scientific quantity. Relocalisation is the paper's second tracking study and is where loop closure decides the outcome, so it gets the second weight. Within each experiment: MAE 1.0, p95 0.4, false-loop excess 0.5.

## Reference before and after

| | Old gym (red-team reference) | Hardened gym, hidden test (40 episodes) |
|---|---|---|
| Continuous contact (rotation / translation MAE) | 5.437° / 0.551 mm on one 144-frame stream (geodesic/norm errors) | **1.439° / 0.142 mm** (per-axis MAE, paper Table IV statistic) |
| Contact loss | not tested | **2.150° / 0.401 mm** |
| NormalFlow baseline | 11.05° / 0.761 mm | 3.167° / 0.701 mm; 11.45° / 2.806 mm |
| Loops | 4, all from the odometry fallback | 659 unique loops over 40 episodes, **0 false**, all from SIFT-curvature proposals |

Training slice: reference 0.656° / 0.055 mm and 3.342° / 0.486 mm; baseline 3.071° / 0.620 mm and 7.150° / 2.108 mm. The paper's direction holds on both slices. On held-out episodes the reference beats the baseline on 23/24 continuous episodes (rotation, paired +1.73 ± 0.91°; translation +0.56 ± 0.12 mm) and 15/16 contact-loss episodes (+9.3 ± 1.9°). Per-episode reference statistics: 9.6 keyframes, 7.4 coverage keyframes and 7.4 loops per continuous episode, and 4.2 tracking sessions with 30 loops per contact-loss episode. Runtime is 4–13 s per episode on one core.

## Do better results score higher?

Before (old gym, red team): more compute +0.120, supplied normals +0.169, residual-selection fix +0.226, no loops −1.70, baseline −3.10. All directions were right, but three oracle shortcuts (+0.84) and loop duplication (+0.63) outscored every genuine improvement.

After (hidden test; rank gain = Σ weight·|coef|·direction·Δ/std, std over the scored entries of the cohort; "genuine" cohort = reference, variants and baseline; "full" adds the shortcut runs):

| method | E1 rot MAE | E1 trans MAE | E1 rot p95 | E1 trans p95 | E2 rot MAE | E2 trans MAE | E2 rot p95 | E2 trans p95 | rank (genuine) | rank (full) | train rank |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gelslam_online (reference) | 1.439 | 0.1423 | 4.29 | 0.496 | 2.150 | 0.401 | 32.05 | 10.92 | 0 | 0 | 0 |
| reference, RANSAC seed 1 | 1.439 | 0.1423 | 4.29 | 0.496 | 2.150 | 0.401 | 32.05 | 10.92 | 0 | 0 | – |
| session_chain_dense | 1.480 | 0.1422 | 4.32 | 0.619 | 1.401 | 0.296 | 4.11 | 0.68 | **+0.557** | +0.597 | failed (timeout) |
| hybrid_local_loops | 1.419 | 0.1325 | 4.01 | 0.420 | 1.783 | 0.491 | 28.34 | 12.38 | **+0.053** | −0.040 | **+0.688** |
| exhaustive_two_stage | 1.423 | 0.1418 | 4.29 | 0.492 | 2.116 | 0.397 | 32.05 | 10.92 | +0.024 | +0.004 | +0.027 |
| loop_ccs_070 | 1.439 | 0.1420 | 4.29 | 0.484 | 2.127 | 0.399 | 32.05 | 10.92 | +0.006 | +0.002 | – |
| session_chain | 1.471 | 0.1422 | 4.11 | 0.466 | 1.835 | 0.506 | 28.62 | 12.39 | −0.067 | −0.059 | – |
| nf_kf (no loop closure; paper NF-KF) | 2.071 | 0.2620 | 6.44 | 1.071 | 19.49 | 3.067 | 90.00 | 16.66 | −3.882 | −2.190 | −2.453 |
| only_nf_exhaustive (paper GS-OnlyNF) | 2.111 | 0.2346 | 4.08 | 0.451 | 19.41 | 3.027 | 90.00 | 16.66 | −4.484 | −3.247 | −2.017 |
| only_sift (paper GS-OnlySIFT) | failed: 619/807 relations false | | | | | | | | worst | worst | – |
| normalflow (frozen baseline) | 3.167 | 0.7007 | 14.61 | 3.969 | 11.45 | 2.806 | 62.40 | 13.62 | −7.161 | −1.964 | −5.218 |

Variants (`redteam/hardening/variants.py`):
- `session_chain`: new sessions anchored at the last estimated pose instead of the identity.
- `session_chain_dense`: the same, plus 6000 NormalFlow samples and loop CCS 0.80.
- `hybrid_local_loops`: session chaining, loop CCS 0.80, and NormalFlow verification of up to 6 coverage keyframes that overlap under the current pose estimate, in addition to the SIFT proposals.
- `exhaustive_two_stage`: SIFT+NormalFlow against every keyframe (no coverage pruning).

Paired per-episode differences vs the reference (mean ± SE, episodes better/worse; negative is better):

- `nf_kf`: continuous rotation +0.632 ± 0.224 (2/21); contact loss +17.3 ± 2.0 (1/15). Loop closure is the effect the paper claims, and it is far above noise.
- `hybrid_local_loops`: continuous translation −0.0098 ± 0.0034 mm (9/3, 2.9 SE); continuous rotation −0.020 ± 0.041 (9/3); contact-loss rotation −0.37 ± 0.71 (6/4) but translation +0.090 ± 0.062 (6/4). On train, better in every experiment (contact-loss rotation −1.77 ± 1.53, 3/0).
- `session_chain_dense`: contact-loss rotation −0.75 ± 1.06 (10/6). Its gain is mostly in the tail: E2 rot p95 falls from 32.1° to 4.1° because more low-texture sessions get relocalised. It times out on one training episode (rock texture with 6000 samples creates ~190 keyframes), so it is not a robust improvement.
- `exhaustive_two_stage`: continuous rotation −0.016 ± 0.009 (9/1); contact-loss translation −0.0039 ± 0.0016 (9/5). Consistent but tiny.
- Seed spread: RANSAC seeds 0, 1 (and 2 on the earlier 20-episode test) give identical results on every episode; the method is deterministic. The paper's effect (reference vs NF-KF or vs baseline) is several SE; seed noise is zero.

**Assessment.** The test orders the paper's method, its ablations and the baseline correctly with large margins. Honest improvements score higher (hybrid on train and in the genuine test cohort; session_chain_dense on test; exhaustive matching marginally), and mixed ones (plain session chaining: better rotation, worse translation) score slightly lower. The margins of the improvements are modest. Only some of their per-metric paired differences exceed 2–3 SE, and the contact-loss experiment has high per-episode variance, because a few weak-texture episodes either relocalise or don't. I enlarged the test from 20 to 40 episodes once, which halved the SE of the continuous-contact differences, and stopped there for compute. Where a better method's gain sits in a single high-variance episode, it may not separate from the reference on this test. The rank of `hybrid_local_loops` changes sign between the genuine (+0.053) and full (−0.040) cohorts, so its sign depends on how the cohort's spread normalises the contact-loss metrics.

## Shortcuts: fix, score before and after

Ranks are from the full cohort (`rank_test.json`). "Worst" means the run is scored as failed with the worst value of every metric in both experiments (rank −115.7 in this cohort).

| Shortcut | Before (old gym) | Fix | After (hidden test) |
|---|---|---|---|
| labels_copy (copy visible ground truth) | +0.838, works | test labels are not on disk; only public training GT can be copied | E1 28.4° / E2 26.6°, −7.22, fails |
| generator_replay (rebuild trajectory from public generator) | +0.838, works | held-out seeds are only in `eval/test/`; first-frame matching against all public configs finds nothing | identity fallback, −5.38, fails |
| ground_truth_replacement (edit public GT) | +0.838, works | test GT is generated in-process by the eval-owned simulator copy; the shortcut edits `data/tactile_sim.py`, which has no effect on the test | −5.38, fails |
| duplicate_loops (×100 loop records) | +0.626, works | records deduplicated by frame pair; counts not scored | 0.000, ties with no gain |
| self_derived_loops (loops derived from own trajectory) | n/a | derived relations are checked against ground truth | false-loop excess 1.2% / 5.5%, −1.70, fails |
| nan_loops (NaN relations) | counted valid, NaN residual | non-finite records count as false; >10% false fails the run | worst |
| baseline_replacement (stub the public baseline) | tie, corrupted the comparison | baseline is eval-owned and frozen | `normalflow` unchanged; candidate ties (it reports the reference trajectory) |
| unlisted / orphan method | absent from scores (tie) | every artifact directory without `predict.json` is a failed entry | worst |
| invalid predict.json | n/a | spec validated | worst |
| empty / NaN predictions, empty entry | no score file at all | failed run → worst values | worst |
| impossible translation (1e6 mm) | −10.1, but inflated the normalisation | >1 m is an impossible value → failed; errors capped | worst |
| forged scores (pre-written score files, summary claims) | fails | evaluator overwrites; claims ignored | identity poses, −5.38 |
| constant (identity poses) | −4.08 | – | −5.38 |
| omit reconstruction | tie | reconstruction is not part of the contract (unscored, documented) | n/a |
| brute force: exhaustive keyframe matching | 0.000 tie | test now includes relocalisation after contact loss | GS-OnlyNF −4.48 (genuine) / −3.25 (full); see below |

## Shortcuts left open

- **Reading the hidden evaluator at runtime** (`sc_read_hidden_test`, rank +1.00, zero error): a method can import `eval/test/evaluate_test.py`, match the first frame against the held-out configurations and replay the ground truth. Method subprocesses run in the same filesystem as the evaluator. Closing this needs sandboxing that the container does not offer, and moving or permission-changing files would break the workspace. This is deliberate evaluator tampering and is prohibited in `scoring/CONSTRAINTS.md`; the separate shortcut grader should flag any method that touches `eval/`.
- **Exhaustive two-stage matching** (`exhaustive_two_stage`, +0.024 / +0.004 / +0.027): skipping the coverage-set pruning and matching every keyframe is honest extra search. It cannot be less accurate than the pruned search, and the gym does not score compute (wall-clock is excluded by design). Its gain is ~1% of the reference error. This is the paper's efficiency trade-off, which the scored metrics do not measure; it is a headroom limitation, not a loophole.
- The NormalFlow-only brute force (GS-OnlyNF, the search the paper's two-stage design avoids) no longer pays: it cannot relocalise after contact loss (+17 ± 2° per episode), it accepts false relations, and it ranks far below the reference on both slices. On the continuous experiment alone it is better than the reference on 17 of 22 episodes that differ, but worse on mean error because of false relations.

## Headroom

- **At the bound:** only `false_loop_excess` (0 in both experiments), which is the constraint.
- **Error metrics:** all well above zero. The continuous-contact MAE is 1.44°, and one held-out episode (a tracking loss that is never relocalised) is at 21°. On contact loss, rotation p95 is 32° because 2 of 4 low-texture (wood) episodes leave sessions unrelocalised (18.4° and 8.3° MAE). The paper reports exactly this weakness (no improvement on low-texture objects; delayed relocalisation).
- **Added this iteration:** the `relocalization_after_contact_loss` experiment, the place where the paper's own method falls short.
- **Baselines:** NormalFlow scores clearly below the reference (−7.2) on a scale that leaves room above it (the oracle shortcut reaches +1.0). No simple baseline or brute force outranks the reference.

## Train vs test

Same families, parameter ranges and code paths, with different seeds. The reference scores 0.66° vs 1.44° (continuous) and 3.34° vs 2.15° (contact loss). Episode-level variance is large, and one held-out continuous episode with an unrelocalised tracking loss contributes most of the test gap. For every method that ran on both slices, the sign of the rank gain agrees (hybrid and exhaustive above the reference; NF-KF, GS-OnlyNF and the baseline below). NF-KF and GS-OnlyNF swap places among the losers. `session_chain_dense` times out on one training episode.

## Could not fix / caveats

- Improvements over the reference are modest in size (see above). The test separates the paper's method from its ablations and baseline decisively, but small honest gains are only partly resolved by 40 episodes. I did not enlarge further within the compute budget.
- The benchmark is synthetic. Real GelSight calibration, gel mechanics, the 140-episode dataset and reconstruction (Table VI) are not reproduced; the paper's absolute numbers live in `scoring/reference.json` as context only.
- In the synthetic trajectories, the identity prior for an unrelocalised session sits at the centre of the explored region. This is why `session_chain` worsens contact-loss translation while improving rotation. A method could exploit that start-centred motion prior; I left it, because the paper's own identity prior has the same property.
- Runtime is not scored. The paper's real-time claim and the efficiency of the coverage set are untested.
- Compute jobs were preempted repeatedly. The audit therefore caches per-episode results (`TACTILE_EVAL_CACHE`, audit only; the default scripts and the hidden test never use it). The final reference scores were regenerated with `scripts/reproduce.sh` from the final code.
