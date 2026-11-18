# Final hardening audit measurements

Rank gains use all ranked entries, including failures, for each metric standard deviation. The genuine-only column uses the honest cohort. Confidence intervals resample whole paired episodes (512 draws), holding the cohort normalization fixed. These are audit summaries; only official experiment results are ranked.

| Method | Status | E1 rot / trans MAE | E2 rot / trans MAE | Gain (all) | Gain (honest) | Paired gain 95% CI | Train gain |
|---|---|---:|---:|---:|---:|---:|---:|
| hybrid_dense_loops | scored | 0.4861 / 0.0429 | 0.8841 / 0.1799 | +0.03922 | +0.22089 | [-0.00566, +0.23545] | +0.17377 |
| exhaustive_two_stage | scored | 0.5529 / 0.0515 | 1.4866 / 0.1981 | +0.02188 | +0.04664 | [-0.00090, +0.15597] | +0.05138 |
| hybrid_local_loops | scored | 0.4897 / 0.0434 | 0.9220 / 0.1893 | +0.00921 | +0.16866 | [-0.04063, +0.23223] | +0.22459 |
| gelslam_online | scored | 0.5540 / 0.0517 | 1.6913 / 0.2231 | +0.00000 | +0.00000 | [+0.00000, +0.00000] | +0.00000 |
| reference_seed1 | scored | 0.5540 / 0.0517 | 1.6913 / 0.2231 | +0.00000 | +0.00000 | [+0.00000, +0.00000] | +0.00000 |
| session_chain_dense | scored | 0.5106 / 0.0524 | 1.0647 / 0.2270 | -0.05397 | -0.03236 | [-0.14697, +0.21931] | +0.19552 |
| normalflow | scored | 3.1564 / 0.6999 | 9.0191 / 2.2736 | -0.63736 | -6.89591 | [-0.73144, -0.33262] | -6.90020 |
| only_nf_exhaustive | scored | 0.6345 / 0.0550 | 18.2929 / 2.7988 | -0.78886 | -2.62304 | [-0.86267, -0.48210] | -3.07994 |
| nf_kf | scored | 1.0270 / 0.1205 | 18.3961 / 2.8113 | -0.82089 | -3.32422 | [-0.88912, -0.50985] | -3.53958 |
| sc_constant | scored | 20.9911 / 2.8675 | 20.8089 / 2.8755 | -1.84674 | -32.09888 | [-1.91566, -1.53756] | — |
| sc_generator_replay | scored | 20.9911 / 2.8675 | 20.8089 / 2.8755 | -1.84674 | -32.09888 | [-1.91566, -1.53756] | — |
| sc_labels_copy | scored | 20.9911 / 2.8675 | 20.8089 / 2.8755 | -1.84674 | -32.09888 | [-1.91566, -1.53756] | — |
| sc_baseline_replacement | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_duplicate_loops | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_empty_predictions | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_false_constraint | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_forged_scores | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_gt_replacement | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_impossible_translation | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_invalid | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_metric_cache_forgery | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_nan_loops | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_nan_predictions | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_orphan | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |
| sc_read_hidden_test | failed | 90.0000 / 30.0000 | 90.0000 / 30.0000 | -6.97719 | -180.68619 | failed | — |

Independent, serialized reference rerun: {'gelslam_online': 0.0, 'normalflow': 0.0}

Paired per-episode changes (variant minus reference; negative improves):

- **exhaustive_two_stage**: long_horizon_tracking:rotation_mae_deg: -0.00113 ± 0.00321 SE (8/10 better/worse, n=48); long_horizon_tracking:translation_mae_mm: -0.00017 ± 0.00053 SE (9/9 better/worse, n=48); relocalization_after_contact_loss:rotation_mae_deg: -0.20472 ± 0.19950 SE (23/19 better/worse, n=48); relocalization_after_contact_loss:translation_mae_mm: -0.02500 ± 0.02358 SE (30/12 better/worse, n=48)
- **hybrid_dense_loops**: long_horizon_tracking:rotation_mae_deg: -0.06792 ± 0.02807 SE (34/13 better/worse, n=48); long_horizon_tracking:translation_mae_mm: -0.00880 ± 0.00360 SE (37/10 better/worse, n=48); relocalization_after_contact_loss:rotation_mae_deg: -0.80725 ± 0.39960 SE (30/18 better/worse, n=48); relocalization_after_contact_loss:translation_mae_mm: -0.04322 ± 0.03637 SE (32/16 better/worse, n=48)
- **hybrid_local_loops**: long_horizon_tracking:rotation_mae_deg: -0.06434 ± 0.02793 SE (15/9 better/worse, n=48); long_horizon_tracking:translation_mae_mm: -0.00833 ± 0.00342 SE (18/6 better/worse, n=48); relocalization_after_contact_loss:rotation_mae_deg: -0.76931 ± 0.40093 SE (24/23 better/worse, n=48); relocalization_after_contact_loss:translation_mae_mm: -0.03382 ± 0.03763 SE (23/23 better/worse, n=48)
- **nf_kf**: long_horizon_tracking:rotation_mae_deg: +0.47295 ± 0.14739 SE (2/43 better/worse, n=48); long_horizon_tracking:translation_mae_mm: +0.06877 ± 0.01276 SE (2/43 better/worse, n=48); relocalization_after_contact_loss:rotation_mae_deg: +16.70485 ± 0.92049 SE (0/47 better/worse, n=48); relocalization_after_contact_loss:translation_mae_mm: +2.58819 ± 0.10445 SE (0/47 better/worse, n=48)
- **normalflow**: long_horizon_tracking:rotation_mae_deg: +2.60242 ± 0.27909 SE (0/48 better/worse, n=48); long_horizon_tracking:translation_mae_mm: +0.64818 ± 0.06006 SE (0/48 better/worse, n=48); relocalization_after_contact_loss:rotation_mae_deg: +7.32785 ± 0.57510 SE (2/46 better/worse, n=48); relocalization_after_contact_loss:translation_mae_mm: +2.05052 ± 0.11078 SE (1/47 better/worse, n=48)
- **only_nf_exhaustive**: long_horizon_tracking:rotation_mae_deg: +0.08046 ± 0.13754 SE (24/23 better/worse, n=48); long_horizon_tracking:translation_mae_mm: +0.00334 ± 0.00971 SE (27/20 better/worse, n=48); relocalization_after_contact_loss:rotation_mae_deg: +16.60157 ± 0.91809 SE (1/47 better/worse, n=48); relocalization_after_contact_loss:translation_mae_mm: +2.57568 ± 0.10610 SE (1/47 better/worse, n=48)
- **reference_seed1**: long_horizon_tracking:rotation_mae_deg: +0.00000 ± 0.00000 SE (0/0 better/worse, n=48); long_horizon_tracking:translation_mae_mm: +0.00000 ± 0.00000 SE (0/0 better/worse, n=48); relocalization_after_contact_loss:rotation_mae_deg: +0.00000 ± 0.00000 SE (0/0 better/worse, n=48); relocalization_after_contact_loss:translation_mae_mm: +0.00000 ± 0.00000 SE (0/0 better/worse, n=48)
- **session_chain_dense**: long_horizon_tracking:rotation_mae_deg: -0.04346 ± 0.01828 SE (38/10 better/worse, n=48); long_horizon_tracking:translation_mae_mm: +0.00066 ± 0.00397 SE (31/17 better/worse, n=48); relocalization_after_contact_loss:rotation_mae_deg: -0.62664 ± 0.44846 SE (33/15 better/worse, n=48); relocalization_after_contact_loss:translation_mae_mm: +0.00393 ± 0.05333 SE (35/13 better/worse, n=48)
