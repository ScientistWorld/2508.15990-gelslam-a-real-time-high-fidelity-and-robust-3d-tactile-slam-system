# Final hardening audit measurements

Rank gains use all ranked entries, including failures, for each metric standard deviation. The genuine-only column uses the honest cohort. Confidence intervals resample whole paired episodes (512 draws), holding the cohort normalization fixed. These are audit summaries; only official experiment results are ranked.

| Method | Status | E1 rot / trans MAE | E2 rot / trans MAE | Gain (all) | Gain (honest) | Paired gain 95% CI | Train gain |
|---|---|---:|---:|---:|---:|---:|---:|
| hybrid_dense_loops | scored | 0.5220 / 0.0466 | 0.7273 / 0.1101 | +0.01390 | +0.12291 | [+0.00808, +0.02530] | +0.17377 |
| exhaustive_two_stage | scored | 0.5649 / 0.0560 | 1.1127 / 0.1348 | +0.00250 | +0.01452 | [+0.00076, +0.00625] | +0.05138 |
| gelslam_online | scored | 0.5695 / 0.0568 | 1.1740 / 0.1426 | +0.00000 | +0.00000 | [+0.00000, +0.00000] | +0.00000 |
| normalflow | scored | 3.1924 / 0.7132 | 9.0088 / 2.4640 | -0.76691 | -6.19503 | [-0.80263, -0.73287] | -6.90020 |
| only_nf_exhaustive | scored | 0.6367 / 0.0835 | 17.5776 / 2.7594 | -0.91123 | -2.47728 | [-0.93237, -0.88300] | -3.07994 |
| nf_kf | scored | 1.0380 / 0.1482 | 17.6303 / 2.7663 | -0.94222 | -3.07566 | [-0.96560, -0.91356] | -3.53958 |
| sc_constant | scored | 20.8907 / 2.9185 | 20.3597 / 2.8717 | -2.04618 | -28.47986 | [-2.06535, -2.02029] | — |
| sc_generator_replay | scored | 20.8907 / 2.9185 | 20.3597 / 2.8717 | -2.04618 | -28.47986 | [-2.06535, -2.02029] | — |
| sc_labels_copy | scored | 20.8907 / 2.9185 | 20.3597 / 2.8717 | -2.04618 | -28.47986 | [-2.06535, -2.02029] | — |
| sc_baseline_replacement | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_duplicate_loops | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_empty_predictions | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_false_constraint | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_forged_scores | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_gt_replacement | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_impossible_translation | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_invalid | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_metric_cache_forgery | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_nan_loops | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_nan_predictions | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_orphan | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |
| sc_read_hidden_test | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -7.34819 | -155.72233 | failed | — |

Independent, serialized reference rerun: {'gelslam_online': 0.0, 'normalflow': 0.0}

Paired per-episode changes (variant minus reference; negative improves):

- **exhaustive_two_stage**: long_horizon_tracking:rotation_mae_deg: -0.00452 ± 0.00191 SE (50/33 better/worse, n=192); long_horizon_tracking:translation_mae_mm: -0.00079 ± 0.00033 SE (53/30 better/worse, n=192); relocalization_after_contact_loss:rotation_mae_deg: -0.06125 ± 0.04992 SE (104/56 better/worse, n=192); relocalization_after_contact_loss:translation_mae_mm: -0.00784 ± 0.00591 SE (118/42 better/worse, n=192)
- **hybrid_dense_loops**: long_horizon_tracking:rotation_mae_deg: -0.04751 ± 0.01257 SE (132/57 better/worse, n=192); long_horizon_tracking:translation_mae_mm: -0.01025 ± 0.00339 SE (141/48 better/worse, n=192); relocalization_after_contact_loss:rotation_mae_deg: -0.44668 ± 0.14260 SE (136/56 better/worse, n=192); relocalization_after_contact_loss:translation_mae_mm: -0.03256 ± 0.01216 SE (139/53 better/worse, n=192)
- **nf_kf**: long_horizon_tracking:rotation_mae_deg: +0.46854 ± 0.07564 SE (12/169 better/worse, n=192); long_horizon_tracking:translation_mae_mm: +0.09134 ± 0.02545 SE (7/174 better/worse, n=192); relocalization_after_contact_loss:rotation_mae_deg: +16.45630 ± 0.42371 SE (0/190 better/worse, n=192); relocalization_after_contact_loss:translation_mae_mm: +2.62370 ± 0.05788 SE (0/190 better/worse, n=192)
- **normalflow**: long_horizon_tracking:rotation_mae_deg: +2.62290 ± 0.11190 SE (0/192 better/worse, n=192); long_horizon_tracking:translation_mae_mm: +0.65643 ± 0.02932 SE (0/192 better/worse, n=192); relocalization_after_contact_loss:rotation_mae_deg: +7.83488 ± 0.27581 SE (6/186 better/worse, n=192); relocalization_after_contact_loss:translation_mae_mm: +2.32137 ± 0.07049 SE (3/189 better/worse, n=192)
- **only_nf_exhaustive**: long_horizon_tracking:rotation_mae_deg: +0.06726 ± 0.06830 SE (111/78 better/worse, n=192); long_horizon_tracking:translation_mae_mm: +0.02665 ± 0.02500 SE (127/62 better/worse, n=192); relocalization_after_contact_loss:rotation_mae_deg: +16.40365 ± 0.42437 SE (2/190 better/worse, n=192); relocalization_after_contact_loss:translation_mae_mm: +2.61677 ± 0.05849 SE (2/190 better/worse, n=192)
